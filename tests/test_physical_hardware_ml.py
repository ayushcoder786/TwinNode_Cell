"""
Automated Test Suite for Physical STM32 + Machine Learning Integration
Validates:
1. Serial line parsing (DATA,TEMP=25,HUM=58,DIST=45.20).
2. Malformed/invalid message handling & raw message preservation.
3. Feature compatibility inspector & missing feature identification.
4. Dedicated physical hardware model training (REAL_HARDWARE provenance).
5. Two-layer real-time prediction & anomaly scoring.
6. LED command dispatch & ACK tracking.
7. Emergency stop priority & disconnection safe state.
8. Physical hardware REST endpoints.
"""

import pytest
from httpx import AsyncClient, ASGITransport
import numpy as np

from backend.app.main import app
from backend.app.services.serial_service import SerialService
from backend.app.ml.hardware_ml_service import hardware_ml_service, PHYSICAL_HARDWARE_FEATURES
from backend.app.services.supervisor import supervisor

@pytest.mark.asyncio
async def test_serial_ascii_line_parsing_and_raw_preservation():
    """Verify parsing of valid and slightly noisy DATA,TEMP=...,HUM=...,DIST=... strings."""
    service = SerialService()

    # 1. Exact canonical format
    line1 = "DATA,TEMP=25,HUM=58,DIST=45.20\r\n"
    res1 = service.parse_ascii_line(line1)
    assert res1 is not None
    assert res1["type"] == "TELEMETRY"
    assert res1["temperature"] == 25.0
    assert res1["humidity"] == 58.0
    assert res1["distance"] == 45.20
    assert res1["sensor_validity"] is True
    assert res1["raw_message"] == "DATA,TEMP=25,HUM=58,DIST=45.20"
    assert res1["data_source"] == "REAL_HARDWARE"

    # 2. Tolerant whitespace & floating point variations
    line2 = "  DATA , TEMP = 24.75 , HUM = 61.2 , DIST = 105.4  \n"
    res2 = service.parse_ascii_line(line2)
    assert res2 is not None
    assert res2["type"] == "TELEMETRY"
    assert res2["temperature"] == 24.75
    assert res2["humidity"] == 61.2
    assert res2["distance"] == 105.4
    assert res2["sensor_validity"] is True

    # 3. ACK message detection
    line3 = "ACK,LED=GREEN\r\n"
    res3 = service.parse_ascii_line(line3)
    assert res3 is not None
    assert res3["type"] == "ACK"
    assert "ACK_RECEIVED" in service.last_led_ack_status

@pytest.mark.asyncio
async def test_serial_invalid_and_corrupted_message_handling():
    """Verify corrupted bytes do not crash the service and are counted as parse errors."""
    service = SerialService()
    initial_errors = service.parse_errors

    # 1. Corrupted garbage string
    bad_line1 = "??#$@_GARBAGE_CHUNK_!#"
    res1 = service.parse_ascii_line(bad_line1)
    assert res1["type"] == "UNRECOGNIZED"
    assert service.parse_errors == initial_errors + 1

    # 2. Truncated line missing distance
    bad_line2 = "DATA,TEMP=25,HUM=58"
    res2 = service.parse_ascii_line(bad_line2)
    assert res2["type"] == "UNRECOGNIZED"

    # 3. Non-numeric temperature string
    bad_line3 = "DATA,TEMP=ERR,HUM=58,DIST=45.20"
    res3 = service.parse_ascii_line(bad_line3)
    assert res3["type"] == "UNRECOGNIZED"

@pytest.mark.asyncio
async def test_feature_compatibility_inspector():
    """Verify that models requiring dual-node features are transparently analyzed."""
    # 1. Simulation model feature list (contains dual-node and optical feedback features)
    simulation_features = [
        "rolling_temp_mean", "rolling_temp_std", "temp_rate_of_change",
        "rolling_dist_mean", "dist_rate_of_change", "target_temp_dev",
        "target_dist_dev", "latency_mean", "packet_loss_rate",
        "sensor_stability_score", "response_delay", "led_mismatch"
    ]
    analysis = hardware_ml_service.inspect_model_compatibility(simulation_features)
    assert analysis["total_model_features"] == 12
    assert analysis["missing_features_count"] == 4  # latency_mean, packet_loss_rate, response_delay, led_mismatch
    assert analysis["is_directly_compatible"] is False
    assert "dedicated physical hardware model is recommended" in analysis["recommendation"]

    # 2. Dedicated hardware feature list
    hw_analysis = hardware_ml_service.inspect_model_compatibility(PHYSICAL_HARDWARE_FEATURES)
    assert hw_analysis["missing_features_count"] == 0
    assert hw_analysis["is_directly_compatible"] is True
    assert hw_analysis["compatibility_score_pct"] == 100.0

@pytest.mark.asyncio
async def test_dedicated_hardware_model_training_and_inference():
    """Verify training a dedicated model on REAL_HARDWARE features and running inference."""
    train_res = await hardware_ml_service.train_hardware_model(n_samples=1000)
    assert train_res["provenance"] == "REAL_HARDWARE"
    assert train_res["metrics"]["accuracy"] > 0.85
    assert set(train_res["feature_list"]) == set(PHYSICAL_HARDWARE_FEATURES)

    # 1. Nominal sensor reading inference
    nominal_telemetry = {
        "temperature": 25.0,
        "humidity": 58.0,
        "distance": 45.20,
        "sensor_validity": True,
        "raw_message": "DATA,TEMP=25,HUM=58,DIST=45.20"
    }
    pred_nominal = await hardware_ml_service.predict_physical_telemetry(nominal_telemetry)
    assert pred_nominal["status"] == "SUCCESS"
    assert pred_nominal["predicted_label"] == "NORMAL_OPERATION"
    assert pred_nominal["suggested_led"] == "LED:GREEN"
    assert pred_nominal["data_source"] == "REAL_HARDWARE"

    # 2. Physical sensor out-of-envelope reading -> Layer 1 override
    fault_telemetry = {
        "temperature": 95.0,  # Extreme heat
        "humidity": 10.0,
        "distance": 999.0,  # Lost ultrasonic echo
        "sensor_validity": False,
        "raw_message": "DATA,TEMP=95,HUM=10,DIST=999.00"
    }
    pred_fault = await hardware_ml_service.predict_physical_telemetry(fault_telemetry)
    assert pred_fault["predicted_label"] == "SENSOR_FAULT"
    assert pred_fault["suggested_led"] == "LED:RED"
    assert pred_fault["layer1_override"] is True

@pytest.mark.asyncio
async def test_emergency_stop_unconditionally_overrides_ml():
    """Verify that when emergency stop is active, ML predictions are suppressed and LED:OFF is enforced."""
    telemetry = {
        "temperature": 25.0,
        "humidity": 58.0,
        "distance": 45.20,
        "sensor_validity": True,
        "raw_message": "DATA,TEMP=25,HUM=58,DIST=45.20"
    }
    pred_estop = await hardware_ml_service.predict_physical_telemetry(telemetry, is_estop_latched=True)
    assert pred_estop["predicted_label"] == "EMERGENCY_STOP"
    assert pred_estop["suggested_led"] == "LED:OFF"
    assert pred_estop["actuator_led_state"] == "ALL_OFF"
    assert pred_estop["layer1_override"] is True

@pytest.mark.asyncio
async def test_hardware_rest_api_endpoints():
    """Verify all /api/hardware endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Hardware status
        status_res = await ac.get("/api/hardware/status")
        assert status_res.status_code == 200
        status_data = status_res.json()
        assert "serial" in status_data
        assert "provenance" in status_data

        # 2. Feature compatibility analysis
        comp_res = await ac.get("/api/hardware/feature-compatibility")
        assert comp_res.status_code == 200
        comp_data = comp_res.json()
        assert "analysis" in comp_data

        # 3. LED command dispatch
        led_res = await ac.post("/api/hardware/led-command", json={"command": "LED:GREEN"})
        assert led_res.status_code == 200
        led_data = led_res.json()
        assert led_data["command_sent"] == "LED:GREEN"
        assert led_data["has_physical_optical_feedback"] is False

        # 4. Train dedicated model
        train_res = await ac.post("/api/hardware/train-model", json={"n_samples": 600})
        assert train_res.status_code == 200
        assert train_res.json()["provenance"] == "REAL_HARDWARE"

        # 5. Fetch hardware predictions
        preds_res = await ac.get("/api/hardware/predictions?limit=10")
        assert preds_res.status_code == 200
        assert isinstance(preds_res.json(), list)
