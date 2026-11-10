"""
TwinNode Supervisor Service
Central coordinator for test bench execution, hardware/simulation data routing,
fault detection analysis, and real-time WebSocket distribution.
"""

import asyncio
import time
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Set
from fastapi import WebSocket
from sqlalchemy import select, update

from backend.app.core.config import settings
from backend.app.core.protocol import Packet, MsgType, FaultCode
from backend.app.models.schema import TestSession, TelemetryRecord, FaultEvent, NodeDiagnostic
from backend.app.db.session import AsyncSessionLocal
from backend.app.services.condition_engine import ConditionEngine
from backend.app.services.simulation_service import SimulationEngine
from backend.app.services.serial_service import SerialService
from backend.app.data.collector import collector
from backend.app.ml.predict import prediction_service
from backend.app.ml.hardware_ml_service import hardware_ml_service

class TwinNodeSupervisor:
    def __init__(self):
        self.simulation_mode = settings.DEFAULT_SIMULATION_MODE
        self.condition_engine = ConditionEngine()
        self.simulation_engine = SimulationEngine()
        self.serial_service = SerialService(
            on_packet_received=self._on_hardware_packet,
            on_telemetry_received=self._on_hardware_ascii_telemetry
        )
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        
        # Connected WebSocket clients
        self.active_websockets: Set[WebSocket] = set()
        
        # Test Session State
        self.active_test_id: int = 1001
        self.active_test_name: str = "BENCH_VALIDATION_01"
        self.test_status: str = "IDLE" # IDLE, RUNNING, PAUSED, STOPPED
        self.test_start_time: Optional[datetime] = None
        
        # Current Setpoints
        self.current_target = {
            "target_temp": 25.0,
            "target_dist": 25.0,
            "target_motor_speed": 0,
            "target_servo_angle": 90
        }
        
        # Actuator LED State (Node 2)
        # Note: Open-loop software command acknowledgment only.
        # Node 2 has no physical optical photodiode or current-sensing shunt.
        self.led_state = "GREEN_ON" # GREEN_ON, YELLOW_ON, RED_ON, ALL_OFF
        self.led_pwm_duty = 100 # 0 to 100%
        self.led_ack = "ACK_RECEIVED"
        self.led_feedback_mode = "OPEN_LOOP"
        self.led_feedback_type = "SOFTWARE_COMMAND_ACK"
        self.has_physical_optical_feedback = False
        
        # Latest ML Prediction Cache
        self.latest_prediction: Dict[str, Any] = {
            "predicted_label": "NORMAL_OPERATION",
            "confidence": 0.99,
            "anomaly_score": 0.01,
            "is_anomaly": False,
            "suggested_led": "GREEN_ON",
            "fault_type": "NOMINAL",
            "recommended_action": "System operating nominally.",
            "data_source": "SIMULATION"
        }
        
        # Latest Telemetry Snapshot
        self.latest_telemetry: Dict[str, Any] = {
            "timestamp": time.time(),
            "node1_status": "ONLINE",
            "node2_status": "ONLINE",
            "target_temp": 25.0,
            "actual_temp": 24.5,
            "target_dist": 25.0,
            "actual_dist": 25.0,
            "target_motor_speed": 0,
            "actual_motor_speed": 0,
            "target_servo_angle": 90,
            "actual_servo_angle": 90,
            "comm_latency_ms": 14.2,
            "fault_code": 0,
            "is_simulated": True,
            "led_state": "GREEN_ON",
            "led_feedback_mode": "OPEN_LOOP",
            "led_feedback_type": "SOFTWARE_COMMAND_ACK",
            "has_physical_optical_feedback": False,
            "data_source": "SIMULATION"
        }
        
        # Statistics
        self.sample_count = 0
        self.fault_count = 0
        self._loop_task: Optional[asyncio.Task] = None
        self._is_running = False

    def start_background_loop(self):
        if not self._is_running:
            self._is_running = True
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                self._loop = None
            asyncio.create_task(collector.start())
            self._loop_task = asyncio.create_task(self._supervision_loop())
            print("[Supervisor] Background supervision and data collector loops started.")

    async def register_websocket(self, websocket: WebSocket):
        await websocket.accept()
        self.active_websockets.add(websocket)
        # Send initial full state immediately
        init_state = {
            "type": "INIT_STATE",
            "simulation_mode": self.simulation_mode,
            "test_status": self.test_status,
            "active_test_id": self.active_test_id,
            "active_test_name": self.active_test_name,
            "current_target": self.current_target,
            "latest_telemetry": self.latest_telemetry,
            "latest_prediction": self.latest_prediction,
            "led_state": self.led_state,
            "led_feedback_mode": self.led_feedback_mode,
            "led_feedback_type": self.led_feedback_type,
            "has_physical_optical_feedback": self.has_physical_optical_feedback,
            "hardware_status": self.serial_service.get_status(),
            "active_faults": list(self.condition_engine.active_faults.values()),
            "active_profile": self.condition_engine.active_profile_name
        }
        await websocket.send_text(json.dumps(init_state))

    def unregister_websocket(self, websocket: WebSocket):
        self.active_websockets.discard(websocket)

    async def broadcast_ws(self, message: Dict[str, Any]):
        if not self.active_websockets:
            return
        msg_str = json.dumps(message)
        dead = []
        for ws in self.active_websockets:
            try:
                await ws.send_text(msg_str)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.active_websockets.discard(ws)

    def _on_hardware_ascii_telemetry(self, data: Dict[str, Any]):
        """Called by SerialService when ASCII telemetry DATA,TEMP=...,HUM=...,DIST=... arrives."""
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._process_hardware_telemetry_async(data),
                self._loop
            )

    async def _process_hardware_telemetry_async(self, data: Dict[str, Any]):
        """Asynchronously process physical STM32 telemetry with Layer 1 safety and Layer 2 ML."""
        now = data.get("timestamp", time.time())
        temp = data.get("temperature", 25.0)
        hum = data.get("humidity", 50.0)
        dist = data.get("distance", 50.0)
        raw_msg = data.get("raw_message", "")
        is_valid = data.get("sensor_validity", True)

        self.latest_telemetry = {
            "timestamp": now,
            "node1_status": "ONLINE",
            "node2_status": "ONLINE",
            "target_temp": self.current_target["target_temp"],
            "actual_temp": temp,
            "humidity": hum,
            "target_dist": self.current_target["target_dist"],
            "actual_dist": dist,
            "target_motor_speed": self.current_target["target_motor_speed"],
            "actual_motor_speed": 0,
            "target_servo_angle": self.current_target["target_servo_angle"],
            "actual_servo_angle": 90,
            "comm_latency_ms": round(data.get("rx_interval_ms", 10.0), 2),
            "fault_code": 0 if is_valid else 3,
            "raw_message": raw_msg,
            "sensor_validity": is_valid,
            "is_simulated": False,
            "data_source": "REAL_HARDWARE",
            "led_state": self.led_state,
            "led_feedback_mode": "OPEN_LOOP",
            "led_feedback_type": "SOFTWARE_COMMAND_ACK",
            "has_physical_optical_feedback": False
        }

        # 1. Condition recognition evaluation (Layer 1: Rule-Based)
        faults = self.condition_engine.evaluate(self.latest_telemetry, self.current_target)

        # 2. Real-Time ML Inference (Layer 2)
        ml_pred = await hardware_ml_service.predict_physical_telemetry(
            data,
            is_estop_latched=self.condition_engine.is_emergency_stop_latched
        )
        self.latest_prediction = ml_pred

        # 3. Automatic LED Command Dispatch (STM32 Node 2 Actuator Integration)
        if self.condition_engine.is_emergency_stop_latched:
            led_cmd = "LED:OFF"
            self.led_state = "ALL_OFF"
        else:
            led_cmd = ml_pred.get("suggested_led", "LED:GREEN")
            self.led_state = ml_pred.get("actuator_led_state", "GREEN_ON")

        self.latest_telemetry["led_state"] = self.led_state
        self.serial_service.send_led_command(led_cmd)

        # 4. Ingest Raw Sensor Data into Collector Service
        cond_label = faults[0].get("fault_code") if faults else ml_pred.get("predicted_label", "NORMAL_OPERATION")
        await collector.ingest_record(
            node_id=2,
            temperature=temp,
            humidity=hum,
            distance=dist,
            target_temperature=self.current_target.get("target_temp"),
            target_distance=self.current_target.get("target_dist"),
            test_id=self.active_test_id,
            response_delay_ms=10.0,
            uart_latency_ms=self.latest_telemetry.get("comm_latency_ms", 5.0),
            packet_sequence=self.sample_count,
            packet_loss=0.0,
            led_command=self.led_state,
            led_acknowledgement=self.serial_service.last_led_ack_status,
            operating_mode="RUNNING" if self.test_status == "RUNNING" else "STANDBY",
            condition_label=cond_label,
            data_source="REAL_HARDWARE",
            raw_message=raw_msg
        )

        if self.test_status == "RUNNING":
            self.sample_count += 1
            await self._record_telemetry(self.latest_telemetry)

        # 5. Broadcast live WebSocket update immediately
        ws_update = {
            "type": "TELEMETRY_UPDATE",
            "telemetry": self.latest_telemetry,
            "latest_prediction": self.latest_prediction,
            "led_state": self.led_state,
            "led_feedback_mode": self.led_feedback_mode,
            "led_feedback_type": self.led_feedback_type,
            "has_physical_optical_feedback": self.has_physical_optical_feedback,
            "hardware_status": self.serial_service.get_status(),
            "test_status": self.test_status,
            "active_faults": faults,
            "sample_count": self.sample_count,
            "active_test_id": self.active_test_id
        }
        await self.broadcast_ws(ws_update)

    def _on_hardware_packet(self, packet: Packet):
        """Called by SerialService background thread upon valid packet decode."""
        payload_dict = packet.parse_payload()
        if packet.msg_type == MsgType.TELEMETRY_DATA:
            now = time.time()
            self.latest_telemetry = {
                "timestamp": now,
                "node1_status": "ONLINE",
                "node2_status": "ONLINE",
                "target_temp": self.current_target["target_temp"],
                "actual_temp": payload_dict.get("actual_temp", 25.0),
                "target_dist": self.current_target["target_dist"],
                "actual_dist": payload_dict.get("actual_dist", 25.0),
                "target_motor_speed": self.current_target["target_motor_speed"],
                "actual_motor_speed": payload_dict.get("actual_motor_speed", 0),
                "target_servo_angle": self.current_target["target_servo_angle"],
                "actual_servo_angle": payload_dict.get("actual_servo_angle", 90),
                "comm_latency_ms": round((payload_dict.get("loop_time_us", 1000) / 1000.0), 2),
                "fault_code": int(payload_dict.get("fault_code", 0)),
                "is_simulated": False,
                "data_source": "REAL_HARDWARE"
            }

    async def _supervision_loop(self):
        """10Hz Real-Time Evaluation & Broadcast Loop."""
        while self._is_running:
            try:
                start_loop = time.time()

                if self.simulation_mode:
                    # Advance simulation
                    sim_data = self.simulation_engine.step()
                    if sim_data:
                        self.latest_telemetry = sim_data
                else:
                    # Hardware mode: check communication freshness
                    if not self.serial_service.is_connected:
                        self.latest_telemetry["node1_status"] = "OFFLINE"
                        self.latest_telemetry["node2_status"] = "OFFLINE"
                        self.led_state = "ALL_OFF"
                        self.latest_telemetry["led_state"] = "ALL_OFF"
                    else:
                        time_since_last_rx = time.time() - self.serial_service.last_rx_time
                        if time_since_last_rx > 2.0:
                            self.latest_telemetry["node2_status"] = "COMM_TIMEOUT"
                            self.led_state = "ALL_OFF"
                            self.latest_telemetry["led_state"] = "ALL_OFF"
                            self.serial_service.send_led_command("LED:OFF")

                # 1. Condition recognition evaluation (Layer 1: Rule-Based)
                faults = self.condition_engine.evaluate(self.latest_telemetry, self.current_target)
                primary_rule_fault = faults[0] if faults else None

                # 2. Real-Time ML Inference (Layer 2: Trained Pipeline + Anomaly Detection)
                src_label = "SIMULATION" if self.simulation_mode else "REAL_HARDWARE"
                inference_input = {
                    "temperature": self.latest_telemetry.get("actual_temp", 25.0),
                    "distance": self.latest_telemetry.get("actual_dist", 50.0),
                    "target_temperature": self.current_target.get("target_temp", 25.0),
                    "target_distance": self.current_target.get("target_dist", 50.0),
                    "uart_latency_ms": self.latest_telemetry.get("comm_latency_ms", 5.0),
                    "packet_loss": 0.0,
                    "response_delay_ms": 10.0,
                    "led_command": self.led_state,
                    "led_acknowledgement": self.led_ack,
                    "data_source": src_label
                }

                ml_pred = await prediction_service.predict_latest(
                    current_record=inference_input,
                    layer1_rule_fault=primary_rule_fault
                )
                self.latest_prediction = ml_pred

                # 3. LED Actuation Integration (Node 2)
                # Normal -> Green ON; Warning -> Yellow ON; Fault -> Red ON; E-Stop -> All OFF
                if self.condition_engine.is_emergency_stop_latched:
                    self.led_state = "ALL_OFF"
                else:
                    self.led_state = ml_pred.get("suggested_led", "GREEN_ON")

                self.latest_telemetry["led_state"] = self.led_state
                self.latest_telemetry["data_source"] = src_label

                # 4. Ingest Raw Sensor Data into Collector Service
                cond_label = primary_rule_fault.get("fault_code") if primary_rule_fault else ml_pred.get("predicted_label", "NORMAL_OPERATION")
                await collector.ingest_record(
                    node_id=2,
                    temperature=self.latest_telemetry.get("actual_temp"),
                    distance=self.latest_telemetry.get("actual_dist"),
                    target_temperature=self.current_target.get("target_temp"),
                    target_distance=self.current_target.get("target_dist"),
                    test_id=self.active_test_id,
                    response_delay_ms=10.0,
                    uart_latency_ms=self.latest_telemetry.get("comm_latency_ms", 5.0),
                    packet_sequence=self.sample_count,
                    packet_loss=0.0,
                    led_command=self.led_state,
                    led_acknowledgement=self.led_ack,
                    operating_mode="RUNNING" if self.test_status == "RUNNING" else "STANDBY",
                    condition_label=cond_label,
                    data_source=src_label
                )

                # If emergency stop triggered in engine, reflect in test status
                if self.condition_engine.is_emergency_stop_latched and self.test_status == "RUNNING":
                    self.test_status = "STOPPED"
                    self.current_target["target_motor_speed"] = 0
                    if self.simulation_mode:
                        self.simulation_engine.update_targets(self.current_target)
                    else:
                        # Send E-Stop command and packet over serial
                        self.serial_service.send_led_command("LED:OFF")
                        pkt = Packet.create_emergency_stop(seq_num=0, test_id=self.active_test_id, reason_code=1)
                        self.serial_service.send_packet(pkt)

                # Persist telemetry if test is currently RUNNING
                if self.test_status == "RUNNING":
                    self.sample_count += 1
                    await self._record_telemetry(self.latest_telemetry)

                # Broadcast live updates to WebSockets
                ws_update = {
                    "type": "TELEMETRY_UPDATE",
                    "telemetry": self.latest_telemetry,
                    "latest_prediction": self.latest_prediction,
                    "led_state": self.led_state,
                    "led_feedback_mode": self.led_feedback_mode,
                    "led_feedback_type": self.led_feedback_type,
                    "has_physical_optical_feedback": self.has_physical_optical_feedback,
                    "hardware_status": self.serial_service.get_status(),
                    "test_status": self.test_status,
                    "active_faults": faults,
                    "sample_count": self.sample_count,
                    "active_test_id": self.active_test_id
                }
                await self.broadcast_ws(ws_update)


                # Maintain 100ms cycle time (10Hz)
                elapsed = time.time() - start_loop
                sleep_time = max(0.01, 0.1 - elapsed)
                await asyncio.sleep(sleep_time)

            except Exception as e:
                print(f"[Supervisor] Loop error: {e}")
                await asyncio.sleep(0.5)

    async def _record_telemetry(self, data: Dict[str, Any]):
        try:
            async with AsyncSessionLocal() as session:
                rec = TelemetryRecord(
                    test_id=self.active_test_id,
                    node1_status=data.get("node1_status", "ONLINE"),
                    node2_status=data.get("node2_status", "ONLINE"),
                    target_temp=data.get("target_temp", 25.0),
                    actual_temp=data.get("actual_temp", 25.0),
                    target_dist=data.get("target_dist", 25.0),
                    actual_dist=data.get("actual_dist", 25.0),
                    target_motor_speed=data.get("target_motor_speed", 0),
                    actual_motor_speed=data.get("actual_motor_speed", 0),
                    target_servo_angle=data.get("target_servo_angle", 90),
                    actual_servo_angle=data.get("actual_servo_angle", 90),
                    comm_latency_ms=data.get("comm_latency_ms", 0.0),
                    fault_code=data.get("fault_code", 0),
                    is_simulated=data.get("is_simulated", True)
                )
                session.add(rec)
                await session.commit()
        except Exception as e:
            print(f"[Supervisor] DB Telemetry write error: {e}")

    # Control Commands
    def set_simulation_mode(self, enabled: bool):
        self.simulation_mode = enabled
        self.latest_telemetry["is_simulated"] = enabled
        print(f"[Supervisor] Mode switched to: {'SIMULATION' if enabled else 'HARDWARE'}")

    def update_setpoints(self, target: Dict[str, Any]):
        self.current_target.update(target)
        self.condition_engine.update_target(self.current_target)
        if self.simulation_mode:
            self.simulation_engine.update_targets(self.current_target)
        else:
            # Send setpoint packet to Node 1 via serial
            pkt = Packet.create_setpoint_cmd(
                seq_num=0,
                test_id=self.active_test_id,
                target_temp=self.current_target.get("target_temp", 25.0),
                target_dist=self.current_target.get("target_dist", 25.0),
                target_motor_speed=self.current_target.get("target_motor_speed", 0),
                target_servo_angle=self.current_target.get("target_servo_angle", 90)
            )
            self.serial_service.send_packet(pkt)

    async def start_test(self, name: str, profile: str, targets: Dict[str, Any]) -> int:
        self.active_test_id = int(time.time()) % 100000
        self.active_test_name = name or f"TEST_{self.active_test_id}"
        self.test_status = "RUNNING"
        self.sample_count = 0
        self.fault_count = 0
        self.test_start_time = datetime.now(timezone.utc)
        self.condition_engine.set_active_profile(profile)
        self.update_setpoints(targets)

        # Record in DB
        async with AsyncSessionLocal() as session:
            sess_obj = TestSession(
                test_id=self.active_test_id,
                name=self.active_test_name,
                profile=profile,
                status="RUNNING",
                start_time=self.test_start_time,
                config_json=targets
            )
            session.add(sess_obj)
            await session.commit()

        return self.active_test_id

    async def pause_test(self):
        if self.test_status == "RUNNING":
            self.test_status = "PAUSED"
            async with AsyncSessionLocal() as session:
                stmt = update(TestSession).where(TestSession.test_id == self.active_test_id).values(status="PAUSED")
                await session.execute(stmt)
                await session.commit()

    async def resume_test(self):
        if self.test_status == "PAUSED":
            self.test_status = "RUNNING"
            async with AsyncSessionLocal() as session:
                stmt = update(TestSession).where(TestSession.test_id == self.active_test_id).values(status="RUNNING")
                await session.execute(stmt)
                await session.commit()

    async def stop_test(self):
        self.test_status = "STOPPED"
        self.current_target["target_motor_speed"] = 0
        self.update_setpoints(self.current_target)
        
        async with AsyncSessionLocal() as session:
            stmt = update(TestSession).where(TestSession.test_id == self.active_test_id).values(
                status="COMPLETED",
                end_time=datetime.now(timezone.utc),
                total_samples=self.sample_count,
                total_faults=len(self.condition_engine.active_faults)
            )
            await session.execute(stmt)
            await session.commit()

    def reset_test(self):
        self.test_status = "IDLE"
        self.current_target = {
            "target_temp": 25.0,
            "target_dist": 25.0,
            "target_motor_speed": 0,
            "target_servo_angle": 90
        }
        self.sample_count = 0
        self.condition_engine.reset_faults()
        self.simulation_engine.clear_fault_injections()
        self.simulation_engine.update_targets(self.current_target)

    def emergency_stop(self) -> Dict[str, Any]:
        fault = self.condition_engine.trigger_emergency_stop()
        self.test_status = "STOPPED"
        self.current_target["target_motor_speed"] = 0
        self.update_setpoints(self.current_target)
        return fault

supervisor = TwinNodeSupervisor()
