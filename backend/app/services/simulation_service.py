"""
TwinNode Simulation Engine
Accurately models dual-node distributed interaction, sensor physics, actuator slew,
and fault injection scenarios without physical hardware.
"""

import time
import math
import random
from typing import Dict, Any, Optional

class SimulationEngine:
    def __init__(self):
        self.is_running = True
        self.node1_online = True
        self.node2_online = True
        
        # State variables
        self.current_temp = 24.5
        self.current_dist = 25.0
        self.current_motor_speed = 0.0
        self.current_servo_angle = 90.0
        
        # Target setpoints
        self.target_temp = 25.0
        self.target_dist = 25.0
        self.target_motor_speed = 0
        self.target_servo_angle = 90
        
        # Fault injection flags
        self.fault_injections = {
            "disconnect_lm35": False,
            "disconnect_ultrasonic": False,
            "temp_out_of_range": False,
            "dist_out_of_range": False,
            "motor_stall": False,
            "servo_stall": False,
            "comm_drop": False,
            "latency_spike": False,
            "reverse_motor": False
        }
        
        self.last_update_time = time.time()
        self.seq_counter = 0
        self.packets_tx = 0
        self.packets_rx = 0

    def update_targets(self, targets: Dict[str, Any]):
        if "target_temp" in targets:
            self.target_temp = float(targets["target_temp"])
        if "target_dist" in targets:
            self.target_dist = float(targets["target_dist"])
        if "target_motor_speed" in targets:
            self.target_motor_speed = int(targets["target_motor_speed"])
        if "target_servo_angle" in targets:
            self.target_servo_angle = int(targets["target_servo_angle"])

    def set_fault_injection(self, fault_key: str, state: bool):
        if fault_key in self.fault_injections:
            self.fault_injections[fault_key] = state

    def clear_fault_injections(self):
        for k in self.fault_injections:
            self.fault_injections[k] = False

    def step(self) -> Optional[Dict[str, Any]]:
        """Advance physics and communication simulation by one time step."""
        now = time.time()
        dt = max(0.01, min(0.5, now - self.last_update_time))
        self.last_update_time = now
        
        self.seq_counter = (self.seq_counter + 1) & 0xFF
        self.packets_tx += 1
        
        # Simulate communication drop
        if self.fault_injections["comm_drop"]:
            self.node2_online = False
            return {
                "timestamp": now,
                "node1_status": "ONLINE",
                "node2_status": "OFFLINE_TIMEOUT",
                "target_temp": self.target_temp,
                "actual_temp": self.current_temp,
                "target_dist": self.target_dist,
                "actual_dist": self.current_dist,
                "target_motor_speed": self.target_motor_speed,
                "actual_motor_speed": int(round(self.current_motor_speed)),
                "target_servo_angle": self.target_servo_angle,
                "actual_servo_angle": int(round(self.current_servo_angle)),
                "comm_latency_ms": 2500.0,
                "fault_code": 5, # COMMUNICATION_TIMEOUT
                "is_simulated": True
            }

        self.node1_online = True
        self.node2_online = True
        self.packets_rx += 1
        
        # 1. Simulate Motor dynamics
        if self.fault_injections["motor_stall"]:
            self.current_motor_speed = 0.0
        elif self.fault_injections["reverse_motor"]:
            desired_speed = -float(self.target_motor_speed)
            self.current_motor_speed += (desired_speed - self.current_motor_speed) * min(1.0, dt * 5.0)
        else:
            desired_speed = float(self.target_motor_speed)
            # Motor inertia: first order response
            self.current_motor_speed += (desired_speed - self.current_motor_speed) * min(1.0, dt * 6.0)

        # 2. Simulate Servo dynamics
        if self.fault_injections["servo_stall"]:
            pass # Angle frozen
        else:
            desired_angle = float(self.target_servo_angle)
            max_servo_rate = 300.0 * dt # 300 deg/sec
            diff = desired_angle - self.current_servo_angle
            if abs(diff) <= max_servo_rate:
                self.current_servo_angle = desired_angle
            else:
                self.current_servo_angle += math.copysign(max_servo_rate, diff)

        # 3. Simulate Temperature dynamics (LM35)
        if self.fault_injections["disconnect_lm35"]:
            self.current_temp = 0.0 # 0V disconnect reading
        elif self.fault_injections["temp_out_of_range"]:
            self.current_temp = 115.4 # Dangerous runaway
        else:
            # Subtle thermal drift towards target if heat applied, plus small sensor noise
            thermal_tau = 10.0 # seconds
            noise = (random.random() - 0.5) * 0.1
            self.current_temp += ((self.target_temp - self.current_temp) / thermal_tau) * dt + noise

        # 4. Simulate Ultrasonic Distance (HC-SR04)
        if self.fault_injections["disconnect_ultrasonic"]:
            self.current_dist = 0.0 # Timeout / disconnected
        elif self.fault_injections["dist_out_of_range"]:
            self.current_dist = 480.0 # Exceeds 400cm max range
        else:
            # Distance correlates with motor driving cart toward or away from barrier
            # speed > 0 moves cart closer; speed < 0 moves cart away
            velocity_cm_per_s = (self.current_motor_speed / 100.0) * 15.0 # up to 15cm/s
            self.current_dist -= velocity_cm_per_s * dt
            # If distance approaches barrier, reflect or clamp
            if self.current_dist < 4.0:
                self.current_dist = 4.0
            elif self.current_dist > 180.0:
                self.current_dist = 180.0
            
            # Distance also has subtle ultrasonic reflection noise
            echo_noise = (random.random() - 0.5) * 0.2
            self.current_dist += echo_noise

        comm_latency = 12.0 + (random.random() * 8.0)
        if self.fault_injections["latency_spike"]:
            comm_latency = 650.0

        return {
            "timestamp": now,
            "node1_status": "ONLINE",
            "node2_status": "ONLINE",
            "target_temp": round(self.target_temp, 2),
            "actual_temp": round(self.current_temp, 2),
            "target_dist": round(self.target_dist, 1),
            "actual_dist": round(self.current_dist, 1),
            "target_motor_speed": self.target_motor_speed,
            "actual_motor_speed": int(round(self.current_motor_speed)),
            "target_servo_angle": self.target_servo_angle,
            "actual_servo_angle": int(round(self.current_servo_angle)),
            "comm_latency_ms": round(comm_latency, 1),
            "fault_code": 0,
            "is_simulated": True
        }
