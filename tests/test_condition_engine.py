import pytest
import time
from backend.app.services.condition_engine import ConditionEngine

def test_condition_normal_operation():
    engine = ConditionEngine()
    engine.reset_faults()
    
    target = {
        "target_temp": 25.0,
        "target_dist": 25.0,
        "target_motor_speed": 40,
        "target_servo_angle": 90
    }
    telemetry = {
        "actual_temp": 25.2,
        "actual_dist": 25.1,
        "actual_motor_speed": 39,
        "actual_servo_angle": 90,
        "comm_latency_ms": 15.0
    }
    
    faults = engine.evaluate(telemetry, target)
    assert len(faults) == 0

def test_condition_sensor_out_of_range():
    engine = ConditionEngine()
    engine.reset_faults()
    
    target = {"target_temp": 25.0, "target_dist": 25.0, "target_motor_speed": 0, "target_servo_angle": 90}
    
    # Over-temperature (115°C)
    telemetry = {
        "actual_temp": 115.0,
        "actual_dist": 25.0,
        "actual_motor_speed": 0,
        "actual_servo_angle": 90
    }
    faults = engine.evaluate(telemetry, target)
    fault_codes = [f["fault_code"] for f in faults]
    assert "SENSOR_OUT_OF_RANGE" in fault_codes

def test_condition_sensor_disconnected():
    engine = ConditionEngine()
    engine.reset_faults()
    
    target = {"target_temp": 25.0, "target_dist": 25.0, "target_motor_speed": 0, "target_servo_angle": 90}
    # LM35 reads 0.0V (0°C) or HC-SR04 reads 0.0cm
    telemetry = {
        "actual_temp": 0.0,
        "actual_dist": 0.0,
        "actual_motor_speed": 0,
        "actual_servo_angle": 90
    }
    faults = engine.evaluate(telemetry, target)
    fault_codes = [f["fault_code"] for f in faults]
    assert "SENSOR_DISCONNECTED_OR_INVALID" in fault_codes

def test_condition_emergency_stop_latched():
    engine = ConditionEngine()
    engine.reset_faults()
    
    engine.trigger_emergency_stop("Manual test abort")
    assert engine.is_emergency_stop_latched is True
    
    target = {"target_temp": 25.0, "target_dist": 25.0, "target_motor_speed": 0, "target_servo_angle": 90}
    telemetry = {"actual_temp": 25.0, "actual_dist": 25.0, "actual_motor_speed": 0, "actual_servo_angle": 90}
    
    faults = engine.evaluate(telemetry, target)
    assert any(f["fault_code"] == "EMERGENCY_STOP" for f in faults)

    engine.reset_faults()
    assert engine.is_emergency_stop_latched is False

def test_eq15_09_pending_status():
    engine = ConditionEngine()
    status_info = engine.eq15_09_detector.get_status_info()
    assert status_info["condition_id"] == "EQ-15-09"
    assert status_info["status"] == "PENDING_CONFIRMATION"
    assert status_info["enabled"] is False
