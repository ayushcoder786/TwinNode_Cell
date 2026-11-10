import json
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
from backend.app.core.config import settings
from backend.app.services.eq15_09_detector import EQ1509Detector

class ConditionEngine:
    def __init__(self, profiles_path: Optional[Path] = None):
        self.profiles_path = profiles_path or settings.CONDITION_PROFILES_PATH
        self.profiles_data = self._load_profiles()
        self.active_profile_name = self.profiles_data.get("active_profile", "STANDARD_INDUSTRIAL")
        self.eq15_09_detector = EQ1509Detector()
        
        # State tracking for timing & persistent condition checks
        self.setpoint_change_time = time.time()
        self.last_target = {
            "target_temp": 25.0,
            "target_dist": 20.0,
            "target_motor_speed": 0,
            "target_servo_angle": 90
        }
        self.deviation_start_time: Optional[float] = None
        self.last_packet_time = time.time()
        self.active_faults: Dict[str, Dict[str, Any]] = {}
        self.is_emergency_stop_latched = False

    def _load_profiles(self) -> Dict[str, Any]:
        if self.profiles_path.exists():
            try:
                with open(self.profiles_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[ConditionEngine] Error loading profiles: {e}")
        return {"active_profile": "STANDARD_INDUSTRIAL", "profiles": {}}

    def save_profiles(self):
        try:
            with open(self.profiles_path, "w", encoding="utf-8") as f:
                json.dump(self.profiles_data, f, indent=2)
        except Exception as e:
            print(f"[ConditionEngine] Error saving profiles: {e}")

    def get_active_profile(self) -> Dict[str, Any]:
        profiles = self.profiles_data.get("profiles", {})
        return profiles.get(self.active_profile_name, {})

    def set_active_profile(self, profile_name: str) -> bool:
        if profile_name in self.profiles_data.get("profiles", {}):
            self.active_profile_name = profile_name
            self.profiles_data["active_profile"] = profile_name
            self.save_profiles()
            return True
        return False

    def trigger_emergency_stop(self, reason: str = "Operator Manual E-Stop") -> Dict[str, Any]:
        self.is_emergency_stop_latched = True
        fault = {
            "fault_code": "EMERGENCY_STOP",
            "severity": "CRITICAL",
            "title": "Emergency Stop Triggered",
            "description": f"Safety abort active: {reason}. All actuators commanded to halt.",
            "recommended_action": "Clear mechanical/electrical hazard, confirm area is safe, then click 'Reset Faults'.",
            "timestamp": time.time(),
            "is_acknowledged": False
        }
        self.active_faults["EMERGENCY_STOP"] = fault
        return fault

    def reset_faults(self) -> bool:
        self.is_emergency_stop_latched = False
        self.active_faults.clear()
        self.deviation_start_time = None
        return True

    def acknowledge_fault(self, fault_code: str) -> bool:
        if fault_code in self.active_faults:
            self.active_faults[fault_code]["is_acknowledged"] = True
            return True
        return False

    def update_target(self, new_target: Dict[str, Any]):
        # Detect significant target changes to reset actuator response timer
        motor_changed = abs(new_target.get("target_motor_speed", 0) - self.last_target.get("target_motor_speed", 0)) > 5
        servo_changed = abs(new_target.get("target_servo_angle", 90) - self.last_target.get("target_servo_angle", 90)) > 5
        
        if motor_changed or servo_changed:
            self.setpoint_change_time = time.time()

        self.last_target.update(new_target)

    def evaluate(self, telemetry: Dict[str, Any], target: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Evaluate full condition recognition rules against incoming telemetry and active setpoints.
        Returns a list of newly active or persistent faults.
        """
        now = time.time()
        self.last_packet_time = now
        profile = self.get_active_profile().get("conditions", {})
        detected_faults: List[Dict[str, Any]] = []

        # 1. Emergency Stop Check
        if self.is_emergency_stop_latched:
            detected_faults.append(self.active_faults.get("EMERGENCY_STOP", {
                "fault_code": "EMERGENCY_STOP",
                "severity": "CRITICAL",
                "title": "Emergency Stop Active",
                "description": "System in de-energized latch state.",
                "recommended_action": "Clear fault condition and reset system.",
                "timestamp": now,
                "is_acknowledged": False
            }))

        # 2. Sensor Disconnected / Invalid Reading
        sensor_discon_cfg = profile.get("SENSOR_DISCONNECTED_OR_INVALID", {})
        if sensor_discon_cfg.get("enabled", True):
            temp = telemetry.get("actual_temp", 25.0)
            dist = telemetry.get("actual_dist", 20.0)
            # LM35 disconnected usually reads near 0V (<1°C) or floating/saturated
            # HC-SR04 disconnected returns 0.0 cm or -1.0 cm
            is_temp_disconnected = (temp <= 0.5)
            is_dist_disconnected = (dist <= 0.0 or dist == 999.0)

            if is_temp_disconnected or is_dist_disconnected:
                fault = {
                    "fault_code": "SENSOR_DISCONNECTED_OR_INVALID",
                    "severity": sensor_discon_cfg.get("severity", "CRITICAL"),
                    "title": "Sensor Disconnection / Invalid Reading",
                    "description": (
                        f"Detected invalid reading. Temp: {temp:.1f}°C (disconnected if ≤0.5°C), "
                        f"Distance: {dist:.1f} cm (disconnected/timeout if ≤0cm or 999cm)."
                    ),
                    "recommended_action": sensor_discon_cfg.get("recommended_action", "Check sensor wiring and power."),
                    "timestamp": now,
                    "is_acknowledged": False
                }
                detected_faults.append(fault)
                self.active_faults["SENSOR_DISCONNECTED_OR_INVALID"] = fault
            else:
                self.active_faults.pop("SENSOR_DISCONNECTED_OR_INVALID", None)

        # 3. Sensor Out of Range
        range_cfg = profile.get("SENSOR_OUT_OF_RANGE", {})
        if range_cfg.get("enabled", True):
            thresholds = range_cfg.get("thresholds", {})
            temp = telemetry.get("actual_temp", 25.0)
            dist = telemetry.get("actual_dist", 20.0)

            t_min = thresholds.get("temperature_min_c", 2.0)
            t_max = thresholds.get("temperature_max_c", 90.0)
            d_min = thresholds.get("distance_min_cm", 2.0)
            d_max = thresholds.get("distance_max_cm", 400.0)

            out_of_range = False
            msg = []
            if temp < t_min or temp > t_max:
                out_of_range = True
                msg.append(f"Temperature {temp:.1f}°C outside [{t_min}, {t_max}]°C")
            if (dist < d_min or dist > d_max) and dist > 0: # 0 is handled by disconnect
                out_of_range = True
                msg.append(f"Distance {dist:.1f}cm outside [{d_min}, {d_max}]cm")

            if out_of_range:
                fault = {
                    "fault_code": "SENSOR_OUT_OF_RANGE",
                    "severity": range_cfg.get("severity", "WARNING"),
                    "title": "Sensor Value Out of Range",
                    "description": "; ".join(msg),
                    "recommended_action": range_cfg.get("recommended_action", "Inspect environment and targets."),
                    "timestamp": now,
                    "is_acknowledged": False
                }
                detected_faults.append(fault)
                self.active_faults["SENSOR_OUT_OF_RANGE"] = fault
            else:
                self.active_faults.pop("SENSOR_OUT_OF_RANGE", None)

        # 4. Setpoint Deviation
        dev_cfg = profile.get("SETPOINT_DEVIATION", {})
        if dev_cfg.get("enabled", True):
            th = dev_cfg.get("thresholds", {})
            t_tol = th.get("temperature_tolerance_c", 3.0)
            d_tol = th.get("distance_tolerance_cm", 4.0)
            m_tol = th.get("motor_speed_tolerance_pct", 10.0)
            s_tol = th.get("servo_angle_tolerance_deg", 8.0)
            persist_ms = th.get("persistent_duration_ms", 1500)

            temp_dev = abs(telemetry.get("actual_temp", 0) - target.get("target_temp", 0)) > t_tol
            dist_dev = abs(telemetry.get("actual_dist", 0) - target.get("target_dist", 0)) > d_tol
            motor_dev = abs(telemetry.get("actual_motor_speed", 0) - target.get("target_motor_speed", 0)) > m_tol
            servo_dev = abs(telemetry.get("actual_servo_angle", 0) - target.get("target_servo_angle", 0)) > s_tol

            has_deviation = temp_dev or dist_dev or motor_dev or servo_dev

            if has_deviation:
                if self.deviation_start_time is None:
                    self.deviation_start_time = now
                elif (now - self.deviation_start_time) * 1000.0 >= persist_ms:
                    fault = {
                        "fault_code": "SETPOINT_DEVIATION",
                        "severity": dev_cfg.get("severity", "WARNING"),
                        "title": "Setpoint Deviation Exceeded",
                        "description": (
                            f"System response failed to settle within tolerance after {persist_ms}ms. "
                            f"ΔT: {abs(telemetry.get('actual_temp',0) - target.get('target_temp',0)):.1f}°C, "
                            f"ΔDist: {abs(telemetry.get('actual_dist',0) - target.get('target_dist',0)):.1f}cm, "
                            f"ΔMotor: {abs(telemetry.get('actual_motor_speed',0) - target.get('target_motor_speed',0))}%, "
                            f"ΔServo: {abs(telemetry.get('actual_servo_angle',0) - target.get('target_servo_angle',0))}°."
                        ),
                        "recommended_action": dev_cfg.get("recommended_action", "Check mechanical linkages and loop tuning."),
                        "timestamp": now,
                        "is_acknowledged": False
                    }
                    detected_faults.append(fault)
                    self.active_faults["SETPOINT_DEVIATION"] = fault
            else:
                self.deviation_start_time = None
                self.active_faults.pop("SETPOINT_DEVIATION", None)

        # 5. Actuator Response Failure
        act_cfg = profile.get("ACTUATOR_RESPONSE_FAILURE", {})
        if act_cfg.get("enabled", True):
            th = act_cfg.get("thresholds", {})
            max_resp_ms = th.get("max_response_time_ms", 1200)
            elapsed_since_cmd_ms = (now - self.setpoint_change_time) * 1000.0

            # If commanded significant speed or angle, but actual is 0 or unmoved
            cmd_motor = target.get("target_motor_speed", 0)
            act_motor = telemetry.get("actual_motor_speed", 0)
            cmd_servo = target.get("target_servo_angle", 90)
            act_servo = telemetry.get("actual_servo_angle", 90)

            is_stalled = False
            stall_desc = ""
            if abs(cmd_motor) > 30 and abs(act_motor) < 5 and elapsed_since_cmd_ms > max_resp_ms:
                is_stalled = True
                stall_desc = f"Motor commanded to {cmd_motor}% but actual response is {act_motor}% after {elapsed_since_cmd_ms:.0f}ms."
            elif abs(cmd_servo - 90) > 20 and abs(act_servo - 90) < 3 and elapsed_since_cmd_ms > max_resp_ms:
                is_stalled = True
                stall_desc = f"Servo commanded to {cmd_servo}° but actual angle remained at {act_servo}° after {elapsed_since_cmd_ms:.0f}ms."

            if is_stalled:
                fault = {
                    "fault_code": "ACTUATOR_RESPONSE_FAILURE",
                    "severity": act_cfg.get("severity", "CRITICAL"),
                    "title": "Actuator Response Failure / Stall",
                    "description": stall_desc,
                    "recommended_action": act_cfg.get("recommended_action", "Inspect motor driver power and physical obstructions."),
                    "timestamp": now,
                    "is_acknowledged": False
                }
                detected_faults.append(fault)
                self.active_faults["ACTUATOR_RESPONSE_FAILURE"] = fault
            else:
                self.active_faults.pop("ACTUATOR_RESPONSE_FAILURE", None)

        # 6. Unexpected Response (e.g. reverse polarity or erratic direction)
        unexp_cfg = profile.get("UNEXPECTED_RESPONSE", {})
        if unexp_cfg.get("enabled", True):
            cmd_motor = target.get("target_motor_speed", 0)
            act_motor = telemetry.get("actual_motor_speed", 0)

            # Commanded forward (>20%) but moving backward (<-20%)
            is_reverse = (cmd_motor > 20 and act_motor < -20) or (cmd_motor < -20 and act_motor > 20)
            if is_reverse:
                fault = {
                    "fault_code": "UNEXPECTED_RESPONSE",
                    "severity": unexp_cfg.get("severity", "WARNING"),
                    "title": "Unexpected Actuator Motion",
                    "description": f"Motor moving in opposite direction to command: Cmd={cmd_motor}%, Act={act_motor}%.",
                    "recommended_action": unexp_cfg.get("recommended_action", "Verify motor polarity wiring on L293D."),
                    "timestamp": now,
                    "is_acknowledged": False
                }
                detected_faults.append(fault)
                self.active_faults["UNEXPECTED_RESPONSE"] = fault
            else:
                self.active_faults.pop("UNEXPECTED_RESPONSE", None)

        # 7. Check Communication Timeout
        comm_cfg = profile.get("COMMUNICATION_TIMEOUT", {})
        if comm_cfg.get("enabled", True):
            th = comm_cfg.get("thresholds", {})
            timeout_ms = th.get("inter_node_timeout_ms", 1500)
            # Handled also at connection supervisor level

        # 8. EQ-15-09 Evaluation (Non-blocking pending confirmation stub)
        eq_fault = self.eq15_09_detector.evaluate(telemetry, target)
        if eq_fault:
            detected_faults.append(eq_fault)
            self.active_faults["EQ_15_09"] = eq_fault

        return list(self.active_faults.values())
