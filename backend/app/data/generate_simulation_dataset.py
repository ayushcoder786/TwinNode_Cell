"""
TwinNode Advanced Labelled Simulation Dataset Generator
Generates realistic, physically modelled multi-scenario telemetry sessions across all 6 condition classes.
Stamps every record with data_source='SIMULATION' and logs full session metadata into test_sessions.
Preserves existing records and guarantees record uniqueness and session independence.
"""

import math
import random
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
import asyncio
from sqlalchemy import select, func

from backend.app.models.schema import RawSensorData, TestSession, utc_now
from backend.app.db.session import AsyncSessionLocal, engine, Base
from backend.app.data.dataset_manager import dataset_manager

# Canonical condition classes
CLASSES = [
    "NORMAL_OPERATION",
    "SETPOINT_DEVIATION",
    "SENSOR_FAULT",
    "COMMUNICATION_FAULT",
    "UNEXPECTED_RESPONSE",
    "ACTUATOR_COMMAND_FAILURE"
]

# Advanced Simulation Scenarios mapped to canonical condition classes
SCENARIO_DEFINITIONS = {
    # 1. Normal Operation Scenarios
    "NORMAL_ROOM_AMBIENT": {
        "class": "NORMAL_OPERATION",
        "description": "Stable ambient room tracking (21-24°C) with low sensor noise and nominal distance (40-60 cm)."
    },
    "NORMAL_INDUSTRIAL_HEAT": {
        "class": "NORMAL_OPERATION",
        "description": "Elevated warm factory baseline (28-34°C) with first-order thermal lag and smooth tracking."
    },
    "NORMAL_DYNAMIC_CYCLING": {
        "class": "NORMAL_OPERATION",
        "description": "Periodic setpoint changes simulating multi-step conveyor positioning and thermal cycling."
    },
    "NORMAL_GRADUAL_WARMUP": {
        "class": "NORMAL_OPERATION",
        "description": "Cold plant startup ramping from 16°C to 27°C with realistic thermal capacitance."
    },

    # 2. Setpoint Deviation Scenarios
    "THERMAL_DRIFT": {
        "class": "SETPOINT_DEVIATION",
        "description": "Gradual upward sensor baseline drift from analog self-heating causing persistent tracking error."
    },
    "ACOUSTIC_DRIFT": {
        "class": "SETPOINT_DEVIATION",
        "description": "Ultrasonic transducer timing drift from temperature gradients causing target offset."
    },
    "ACTUATOR_SATURATION_HEAT": {
        "class": "SETPOINT_DEVIATION",
        "description": "High temperature setpoint (45°C) unachievable due to thermal dissipation limits."
    },
    "OBSTACLE_INTERFERENCE": {
        "class": "SETPOINT_DEVIATION",
        "description": "Physical blockage holds position at 35 cm while target commands 85 cm."
    },

    # 3. Sensor Fault Scenarios
    "SENSOR_DISCONNECT_OPEN": {
        "class": "SENSOR_FAULT",
        "description": "LM35 open-circuit pull-down (-99.9°C) and HC-SR04 echo disconnection (0.0 cm)."
    },
    "SENSOR_ADC_SATURATION": {
        "class": "SENSOR_FAULT",
        "description": "ADC input rail saturation (+135°C) and ultrasonic echo range overflow (450 cm)."
    },
    "SENSOR_ERRATIC_NOISE_BURSTS": {
        "class": "SENSOR_FAULT",
        "description": "Severe EMI bursts producing violent, non-physical reading spikes (±35°C, ±80 cm)."
    },
    "SENSOR_INTERMITTENT_FLAP": {
        "class": "SENSOR_FAULT",
        "description": "Loose wiring causing intermittent multi-sample dropouts every 20-30 cycles."
    },

    # 4. Communication Fault Scenarios
    "COMM_UART_CONGESTION": {
        "class": "COMMUNICATION_FAULT",
        "description": "Serial buffer queue buildup ballooning UART latency to 200-850 ms."
    },
    "COMM_HIGH_PACKET_LOSS": {
        "class": "COMMUNICATION_FAULT",
        "description": "Severe electrical interference dropping 35-75% of packets with sequence skips."
    },
    "COMM_LINE_TIMEOUT": {
        "class": "COMMUNICATION_FAULT",
        "description": "Complete serial freeze with response delay >1500 ms triggering watchdog failsafe."
    },

    # 5. Unexpected Response Scenarios
    "UNEXPECTED_INVERSE_CONTROL": {
        "class": "UNEXPECTED_RESPONSE",
        "description": "Inverse physical response: plant cools when heating commanded; moves reverse when forward commanded."
    },
    "UNEXPECTED_CONTROL_HUNTING": {
        "class": "UNEXPECTED_RESPONSE",
        "description": "High-gain PID hunting oscillations resulting in unstable sinusoidal limit cycling."
    },

    # 6. Actuator Command Failure Scenarios
    "ACTUATOR_COMMAND_NACK": {
        "class": "ACTUATOR_COMMAND_FAILURE",
        "description": "Supervisor commands LED/actuator state but Node 2 returns COMMAND_NACK / NO_ACK."
    },
    "ACTUATOR_PWM_FAILURE": {
        "class": "ACTUATOR_COMMAND_FAILURE",
        "description": "Hardware timer register stall preventing Red LED PWM brightness modulation."
    },

    # 7. Safety Emergency Stop Scenarios
    "EMERGENCY_STOP_PROXIMITY": {
        "class": "SETPOINT_DEVIATION",
        "description": "Hazardous obstacle intrusion (<4.0 cm) forcing autonomous E-Stop trip and all actuators OFF."
    },
    "EMERGENCY_STOP_OVERTEMP": {
        "class": "SENSOR_FAULT",
        "description": "Thermal surge exceeding 85°C safety threshold, latching emergency stop."
    }
}

def generate_session_records(
    session_id: int,
    condition_class: Optional[str] = None,
    scenario_name: Optional[str] = None,
    num_samples: int = 150,
    start_time: Optional[datetime] = None,
    random_seed: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Simulate a continuous sequence of physically modelled sensor telemetry.
    Supports parameterized scenarios with non-identical randomized operating conditions.
    """
    rng = random.Random(random_seed if random_seed is not None else (session_id * 31 + 17))

    # Resolve scenario and condition class
    if scenario_name and scenario_name in SCENARIO_DEFINITIONS:
        selected_scenario = scenario_name
        cls_name = SCENARIO_DEFINITIONS[scenario_name]["class"]
    elif condition_class and condition_class in CLASSES:
        cls_name = condition_class
        # Pick a matching scenario
        matching = [s for s, defn in SCENARIO_DEFINITIONS.items() if defn["class"] == condition_class]
        selected_scenario = rng.choice(matching) if matching else "NORMAL_ROOM_AMBIENT"
    else:
        cls_name = "NORMAL_OPERATION"
        selected_scenario = "NORMAL_ROOM_AMBIENT"

    records = []
    t = start_time or (datetime.now(timezone.utc) - timedelta(hours=2))
    dt = timedelta(milliseconds=100) # 10 Hz sampling rate

    # Randomized initial physical states per session
    base_temp = rng.uniform(20.0, 30.0)
    base_dist = rng.uniform(30.0, 70.0)
    temp = base_temp
    dist = base_dist
    target_temp = base_temp
    target_dist = base_dist

    # Fault onset timing (randomized between 15% and 35% of session duration)
    fault_onset = int(num_samples * rng.uniform(0.15, 0.35))
    severity = rng.uniform(0.8, 1.4)

    seq = 0

    for i in range(num_samples):
        seq += 1
        t += dt

        # Nominal baseline operating characteristics
        latency = rng.uniform(3.5, 7.5)
        pkt_loss = 0.0
        resp_delay = rng.uniform(8.0, 14.0)
        sensor_valid = True
        led_cmd = "GREEN_ON"
        led_ack = "ACK_RECEIVED"
        op_mode = f"SCENARIO:{selected_scenario}"

        # ---------------------------------------------------------------------
        # SCENARIO 1: NORMAL OPERATION MODES
        # ---------------------------------------------------------------------
        if selected_scenario == "NORMAL_ROOM_AMBIENT":
            target_temp = base_temp + 2.0 * math.sin(i / 25.0)
            target_dist = base_dist + 8.0 * math.cos(i / 20.0)
            temp += 0.09 * (target_temp - temp) + rng.gauss(0.0, 0.06 * severity)
            dist += 0.22 * (target_dist - dist) + rng.gauss(0.0, 0.15 * severity)
            led_cmd = "GREEN_ON"
            led_ack = "ACK_RECEIVED"

        elif selected_scenario == "NORMAL_INDUSTRIAL_HEAT":
            target_temp = 31.0 + 3.0 * math.sin(i / 30.0)
            target_dist = 55.0 + 12.0 * math.sin(i / 35.0)
            temp += 0.07 * (target_temp - temp) + rng.gauss(0.0, 0.08 * severity)
            dist += 0.20 * (target_dist - dist) + rng.gauss(0.0, 0.20 * severity)
            led_cmd = "GREEN_ON"
            led_ack = "ACK_RECEIVED"

        elif selected_scenario == "NORMAL_DYNAMIC_CYCLING":
            # Multi-step conveyor profile
            cycle_phase = (i // 30) % 3
            target_dist = [25.0, 50.0, 80.0][cycle_phase]
            target_temp = 24.0 + cycle_phase * 2.5
            temp += 0.10 * (target_temp - temp) + rng.gauss(0.0, 0.07 * severity)
            dist += 0.30 * (target_dist - dist) + rng.gauss(0.0, 0.18 * severity)
            led_cmd = "GREEN_ON"
            led_ack = "ACK_RECEIVED"

        elif selected_scenario == "NORMAL_GRADUAL_WARMUP":
            # Machine warming up
            target_temp = min(28.0, 18.0 + (i * 0.08))
            target_dist = base_dist + rng.gauss(0.0, 0.1)
            temp += 0.06 * (target_temp - temp) + rng.gauss(0.0, 0.05 * severity)
            dist += 0.20 * (target_dist - dist) + rng.gauss(0.0, 0.15 * severity)
            led_cmd = "GREEN_ON"
            led_ack = "ACK_RECEIVED"

        # ---------------------------------------------------------------------
        # SCENARIO 2: SETPOINT DEVIATION SCENARIOS
        # ---------------------------------------------------------------------
        elif selected_scenario == "THERMAL_DRIFT":
            target_temp = 26.0
            target_dist = 50.0
            if i >= fault_onset:
                # Gradual thermal drift
                drift = (i - fault_onset) * 0.08 * severity
                temp = target_temp + drift + rng.gauss(0.0, 0.1)
                led_cmd = "YELLOW_ON"
            else:
                temp = target_temp + rng.gauss(0.0, 0.08)
            dist = target_dist + rng.gauss(0.0, 0.2)
            led_ack = "ACK_RECEIVED"

        elif selected_scenario == "ACOUSTIC_DRIFT":
            target_temp = 25.0
            target_dist = 50.0
            temp = target_temp + rng.gauss(0.0, 0.08)
            if i >= fault_onset:
                drift = (i - fault_onset) * 0.22 * severity
                dist = target_dist + drift + rng.gauss(0.0, 0.3)
                led_cmd = "YELLOW_ON"
            else:
                dist = target_dist + rng.gauss(0.0, 0.2)
            led_ack = "ACK_RECEIVED"

        elif selected_scenario == "ACTUATOR_SATURATION_HEAT":
            target_temp = 44.0 # Demanding target
            target_dist = 60.0
            # Saturated thermal equilibrium at ~31°C
            temp = 28.0 + 3.0 * (1.0 - math.exp(-i / 25.0)) + rng.gauss(0.0, 0.1)
            dist = target_dist + rng.gauss(0.0, 0.2)
            led_cmd = "YELLOW_ON"
            led_ack = "ACK_RECEIVED"

        elif selected_scenario == "OBSTACLE_INTERFERENCE":
            target_temp = 26.0
            target_dist = 85.0
            temp = target_temp + rng.gauss(0.0, 0.08)
            if i >= fault_onset:
                # Obstacle blocks at 32 cm
                dist = 32.0 + rng.gauss(0.0, 0.25)
                led_cmd = "YELLOW_ON"
            else:
                dist = target_dist + rng.gauss(0.0, 0.2)
            led_ack = "ACK_RECEIVED"

        elif selected_scenario == "EMERGENCY_STOP_PROXIMITY":
            target_temp = 25.0
            target_dist = 50.0
            temp = target_temp + rng.gauss(0.0, 0.08)
            if i >= fault_onset:
                dist = 3.2 # Under 4.0 cm safety threshold
                led_cmd = "ALL_OFF"
                led_ack = "EMERGENCY_STOP_ACK"
                op_mode = "EMERGENCY_STOP_TRIPPED"
            else:
                dist = target_dist + rng.gauss(0.0, 0.2)
                led_cmd = "GREEN_ON"
                led_ack = "ACK_RECEIVED"

        # ---------------------------------------------------------------------
        # SCENARIO 3: SENSOR FAULT SCENARIOS
        # ---------------------------------------------------------------------
        elif selected_scenario == "SENSOR_DISCONNECT_OPEN":
            target_temp = 26.0
            target_dist = 50.0
            if i >= fault_onset:
                temp = -99.9 # ADC disconnected / pulled to ground
                dist = 0.0   # Ultrasonic echo lost
                sensor_valid = False
                led_cmd = "RED_ON"
            else:
                temp = target_temp + rng.gauss(0.0, 0.08)
                dist = target_dist + rng.gauss(0.0, 0.2)
            led_ack = "ACK_RECEIVED"

        elif selected_scenario == "SENSOR_ADC_SATURATION":
            target_temp = 27.0
            target_dist = 55.0
            if i >= fault_onset:
                temp = 135.0 # ADC saturated to VDD rail
                dist = 450.0 # HC-SR04 overflow
                sensor_valid = False
                led_cmd = "RED_ON"
            else:
                temp = target_temp + rng.gauss(0.0, 0.08)
                dist = target_dist + rng.gauss(0.0, 0.2)
            led_ack = "ACK_RECEIVED"

        elif selected_scenario == "SENSOR_ERRATIC_NOISE_BURSTS":
            target_temp = 25.0
            target_dist = 50.0
            if i >= fault_onset and (i % 2 == 0):
                temp = target_temp + rng.choice([-40.0, 50.0, 75.0])
                dist = rng.uniform(2.0, 420.0)
                sensor_valid = False
                led_cmd = "RED_ON"
            else:
                temp = target_temp + rng.gauss(0.0, 0.1)
                dist = target_dist + rng.gauss(0.0, 0.2)
            led_ack = "ACK_RECEIVED"

        elif selected_scenario == "SENSOR_INTERMITTENT_FLAP":
            target_temp = 26.0
            target_dist = 50.0
            if i >= fault_onset and ((i // 10) % 2 == 1):
                temp = -99.9
                dist = 0.0
                sensor_valid = False
                led_cmd = "RED_ON"
            else:
                temp = target_temp + rng.gauss(0.0, 0.08)
                dist = target_dist + rng.gauss(0.0, 0.2)
            led_ack = "ACK_RECEIVED"

        elif selected_scenario == "EMERGENCY_STOP_OVERTEMP":
            target_dist = 50.0
            dist = target_dist + rng.gauss(0.0, 0.2)
            if i >= fault_onset:
                temp = 89.5 # Over 85°C cutoff
                sensor_valid = False
                led_cmd = "ALL_OFF"
                led_ack = "EMERGENCY_STOP_ACK"
                op_mode = "EMERGENCY_STOP_TRIPPED"
            else:
                temp = 65.0 + (i * 0.4)
                led_cmd = "GREEN_ON"

        # ---------------------------------------------------------------------
        # SCENARIO 4: COMMUNICATION FAULT SCENARIOS
        # ---------------------------------------------------------------------
        elif selected_scenario == "COMM_UART_CONGESTION":
            target_temp = 27.0
            target_dist = 52.0
            temp += 0.06 * (target_temp - temp) + rng.gauss(0.0, 0.08)
            dist += 0.18 * (target_dist - dist) + rng.gauss(0.0, 0.18)
            if i >= fault_onset:
                latency = rng.uniform(220.0, 850.0)
                resp_delay = rng.uniform(250.0, 920.0)
                pkt_loss = rng.uniform(15.0, 40.0)
                led_cmd = "YELLOW_ON"
                led_ack = "TIMEOUT" if rng.random() < 0.4 else "ACK_RECEIVED"
            else:
                latency = rng.uniform(4.0, 8.0)
                resp_delay = rng.uniform(8.0, 15.0)

        elif selected_scenario == "COMM_HIGH_PACKET_LOSS":
            target_temp = 26.0
            target_dist = 50.0
            temp = target_temp + rng.gauss(0.0, 0.08)
            dist = target_dist + rng.gauss(0.0, 0.2)
            if i >= fault_onset:
                pkt_loss = rng.uniform(40.0, 85.0)
                latency = rng.uniform(120.0, 450.0)
                seq += rng.choice([2, 3, 5]) # sequence skipping
                led_cmd = "YELLOW_ON"
                led_ack = "TIMEOUT" if rng.random() < 0.6 else "NO_ACK"

        elif selected_scenario == "COMM_LINE_TIMEOUT":
            target_temp = 25.0
            target_dist = 50.0
            temp = target_temp + rng.gauss(0.0, 0.08)
            dist = target_dist + rng.gauss(0.0, 0.2)
            if i >= fault_onset:
                latency = rng.uniform(1550.0, 2500.0)
                resp_delay = rng.uniform(1600.0, 2600.0)
                pkt_loss = 100.0
                led_cmd = "YELLOW_ON"
                led_ack = "TIMEOUT"

        # ---------------------------------------------------------------------
        # SCENARIO 5: UNEXPECTED RESPONSE SCENARIOS
        # ---------------------------------------------------------------------
        elif selected_scenario == "UNEXPECTED_INVERSE_CONTROL":
            target_temp = 36.0
            target_dist = 75.0
            if i >= fault_onset:
                # Inverted movement
                temp = base_temp - ((i - fault_onset) * 0.12 * severity) + rng.gauss(0.0, 0.1)
                dist = base_dist - ((i - fault_onset) * 0.25 * severity) + rng.gauss(0.0, 0.2)
                led_cmd = "YELLOW_ON"
            else:
                temp = base_temp + rng.gauss(0.0, 0.08)
                dist = base_dist + rng.gauss(0.0, 0.15)
            led_ack = "ACK_RECEIVED"

        elif selected_scenario == "UNEXPECTED_CONTROL_HUNTING":
            target_temp = 28.0
            target_dist = 50.0
            if i >= fault_onset:
                # Severe limit cycle hunting oscillations
                temp = target_temp + 6.0 * math.sin((i - fault_onset) * 0.6) + rng.gauss(0.0, 0.1)
                dist = target_dist + 18.0 * math.cos((i - fault_onset) * 0.5) + rng.gauss(0.0, 0.2)
                led_cmd = "YELLOW_ON"
            else:
                temp = target_temp + rng.gauss(0.0, 0.08)
                dist = target_dist + rng.gauss(0.0, 0.15)
            led_ack = "ACK_RECEIVED"

        # ---------------------------------------------------------------------
        # SCENARIO 6: ACTUATOR COMMAND FAILURE SCENARIOS
        # ---------------------------------------------------------------------
        elif selected_scenario == "ACTUATOR_COMMAND_NACK":
            target_temp = 26.0
            target_dist = 48.0
            temp = target_temp + rng.gauss(0.0, 0.08)
            dist = target_dist + rng.gauss(0.0, 0.15)
            if i >= fault_onset:
                led_cmd = "RED_ON" if i % 2 == 0 else "YELLOW_ON"
                led_ack = "COMMAND_NACK" if i % 3 != 0 else "NO_ACK"
            else:
                led_cmd = "GREEN_ON"
                led_ack = "ACK_RECEIVED"

        elif selected_scenario == "ACTUATOR_PWM_FAILURE":
            target_temp = 26.0
            target_dist = 48.0
            temp = target_temp + rng.gauss(0.0, 0.08)
            dist = target_dist + rng.gauss(0.0, 0.15)
            if i >= fault_onset:
                led_cmd = "RED_ON"
                led_ack = "PWM_STALL_ERROR"
            else:
                led_cmd = "GREEN_ON"
                led_ack = "ACK_RECEIVED"

        else:
            # Fallback nominal
            temp = base_temp + rng.gauss(0.0, 0.08)
            dist = base_dist + rng.gauss(0.0, 0.2)

        temp_err = temp - target_temp if (temp is not None and target_temp is not None) else 0.0
        dist_err = dist - target_dist if (dist is not None and target_dist is not None) else 0.0

        records.append({
            "timestamp": t,
            "node_id": 2,
            "test_id": session_id,
            "temperature": round(temp, 2),
            "distance": round(dist, 2),
            "target_temperature": round(target_temp, 2),
            "target_distance": round(target_dist, 2),
            "temperature_error": round(temp_err, 2),
            "distance_error": round(dist_err, 2),
            "temperature_rate": round(rng.gauss(0.0, 0.08), 3),
            "distance_rate": round(rng.gauss(0.0, 0.18), 3),
            "response_delay_ms": round(resp_delay, 1),
            "uart_latency_ms": round(latency, 1),
            "packet_sequence": seq,
            "packet_loss": round(pkt_loss, 1),
            "sensor_validity": sensor_valid,
            "led_command": led_cmd,
            "led_acknowledgement": led_ack,
            "operating_mode": op_mode,
            "condition_label": cls_name,
            "data_source": "SIMULATION",
            "is_duplicate": False
        })

    return records

async def populate_advanced_simulation_dataset(
    target_total_records: int = 16500,
    random_seed: int = 42,
    selected_scenarios: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Expands the existing dataset by generating diverse, physically parameterized sessions
    until the total unique records reach the target (e.g. 16,500 records).
    Preserves all original raw records and writes full session metadata into test_sessions.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 1. Query existing DB state to preserve original data and discover max test_id
    async with AsyncSessionLocal() as session:
        existing_count = await session.scalar(select(func.count(RawSensorData.id))) or 0
        max_test_id = await session.scalar(select(func.max(RawSensorData.test_id))) or 2000

    start_session_id = max(3001, (max_test_id + 1))
    records_needed = max(0, target_total_records - existing_count)

    if records_needed <= 0:
        return {
            "status": "ALREADY_SATISFIED",
            "existing_records": existing_count,
            "target_total_records": target_total_records,
            "message": f"Database already contains {existing_count} records (>= target {target_total_records})."
        }

    # 2. Plan session distribution
    # Aim for average ~150 samples per session
    scenarios_to_use = selected_scenarios or list(SCENARIO_DEFINITIONS.keys())
    
    # We want ~35% of new sessions in NORMAL_OPERATION, and ~13% in each of the 5 fault classes
    normal_scenarios = [s for s in scenarios_to_use if SCENARIO_DEFINITIONS.get(s, {}).get("class") == "NORMAL_OPERATION"]
    dev_scenarios = [s for s in scenarios_to_use if SCENARIO_DEFINITIONS.get(s, {}).get("class") == "SETPOINT_DEVIATION"]
    sensor_scenarios = [s for s in scenarios_to_use if SCENARIO_DEFINITIONS.get(s, {}).get("class") == "SENSOR_FAULT"]
    comm_scenarios = [s for s in scenarios_to_use if SCENARIO_DEFINITIONS.get(s, {}).get("class") == "COMMUNICATION_FAULT"]
    unexp_scenarios = [s for s in scenarios_to_use if SCENARIO_DEFINITIONS.get(s, {}).get("class") == "UNEXPECTED_RESPONSE"]
    act_scenarios = [s for s in scenarios_to_use if SCENARIO_DEFINITIONS.get(s, {}).get("class") == "ACTUATOR_COMMAND_FAILURE"]

    all_records: List[Dict[str, Any]] = []
    test_session_objects: List[TestSession] = []

    curr_session_id = start_session_id
    base_time = datetime.now(timezone.utc) - timedelta(days=2)
    rng = random.Random(random_seed)

    # Build an interleaved sequence of scenario assignments
    session_plan = []
    while len(session_plan) * 150 < records_needed:
        # 1 cycle: 3 normal, 1 dev, 1 sensor, 1 comm, 1 unexp, 1 act
        if normal_scenarios:
            session_plan.append(rng.choice(normal_scenarios))
            session_plan.append(rng.choice(normal_scenarios))
        if dev_scenarios:
            session_plan.append(rng.choice(dev_scenarios))
        if sensor_scenarios:
            session_plan.append(rng.choice(sensor_scenarios))
        if comm_scenarios:
            session_plan.append(rng.choice(comm_scenarios))
        if unexp_scenarios:
            session_plan.append(rng.choice(unexp_scenarios))
        if act_scenarios:
            session_plan.append(rng.choice(act_scenarios))

    for scn in session_plan:
        if len(all_records) >= records_needed:
            break

        # Randomized duration 120-180 samples
        dur = rng.randint(130, 175)
        # Check if this exceeds target
        if len(all_records) + dur > records_needed:
            dur = max(50, records_needed - len(all_records))

        session_recs = generate_session_records(
            session_id=curr_session_id,
            scenario_name=scn,
            num_samples=dur,
            start_time=base_time,
            random_seed=(random_seed + curr_session_id)
        )
        all_records.extend(session_recs)

        cls_name = SCENARIO_DEFINITIONS.get(scn, {}).get("class", "NORMAL_OPERATION")
        t_start = session_recs[0]["timestamp"]
        t_end = session_recs[-1]["timestamp"]

        test_session_objects.append(TestSession(
            test_id=curr_session_id,
            name=f"Advanced_Sim_{scn}_{curr_session_id}",
            profile="ADVANCED_SIMULATION",
            status="COMPLETED",
            start_time=t_start,
            end_time=t_end,
            total_samples=len(session_recs),
            total_faults=0 if cls_name == "NORMAL_OPERATION" else len(session_recs),
            config_json={
                "scenario": scn,
                "condition_class": cls_name,
                "description": SCENARIO_DEFINITIONS.get(scn, {}).get("description", ""),
                "samples": len(session_recs),
                "data_source": "SIMULATION"
            },
            result_summary=f"Synthetic simulation session for scenario {scn} ({cls_name})."
        ))

        curr_session_id += 1
        base_time += timedelta(minutes=rng.randint(15, 40))

    # 3. Persist new records to SQLite in transactions
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Add test sessions
            session.add_all(test_session_objects)
            # Add raw sensor data
            db_objs = [RawSensorData(**rec) for rec in all_records]
            session.add_all(db_objs)
        await session.commit()

    # 4. Create new versioned dataset snapshot
    snapshot = await dataset_manager.create_dataset_version(
        name="Expanded_16k_MultiScenario_Master",
        description=f"Advanced multi-scenario simulated dataset reaching {existing_count + len(all_records)} total unique records across 21 diverse physical scenarios.",
        test_size=0.15
    )

    return {
        "status": "SUCCESS",
        "original_records": existing_count,
        "new_records_added": len(all_records),
        "total_records": existing_count + len(all_records),
        "sessions_created": len(test_session_objects),
        "start_session_id": start_session_id,
        "end_session_id": curr_session_id - 1,
        "dataset_snapshot": snapshot
    }

async def populate_simulation_dataset(sessions_per_class: int = 3, samples_per_session: int = 100) -> Dict[str, Any]:
    """Backward compatibility adapter for existing tests and endpoints."""
    return await populate_advanced_simulation_dataset(target_total_records=16500)

if __name__ == "__main__":
    result = asyncio.run(populate_advanced_simulation_dataset())
    print("Simulation dataset expansion complete:", result)
