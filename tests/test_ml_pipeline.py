"""
Comprehensive Automated Test Suite for TwinNode Machine Learning & Industrial IoT Pipeline.
Tests data validation, feature engineering, chronological splitting, model training,
joblib serialization, unsupervised anomaly detection, real-time prediction fusion, and REST endpoints.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timezone
import tempfile
import os
from pathlib import Path
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.data.validator import DataValidator
from backend.app.data.collector import DataCollectorService
from backend.app.data.feature_engineering import TwinNodeFeatureEngineer, CANONICAL_FEATURES
from backend.app.data.preprocessing import clean_dataset, chronological_session_split, detect_outliers, session_train_val_test_split
from backend.app.ml.train import train_model, get_algorithm_instance
from backend.app.ml.anomaly_detection import TwinNodeAnomalyDetector
from backend.app.ml.model_registry import model_registry
from backend.app.ml.predict import PredictionService
from backend.app.db.session import engine, Base

@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

# 1. Test Data Validator
def test_data_validator_bounds_and_duplicates():
    val = DataValidator()
    now = datetime.now(timezone.utc)

    # Valid reading
    is_valid, status, details = val.validate_reading(node_id=2, temp=25.0, dist=50.0, seq=1, test_id=101, timestamp=now)
    assert is_valid is True
    assert status == "VALID"
    assert details["is_duplicate"] is False

    # Out of bounds temperature
    is_valid, status, details = val.validate_reading(node_id=2, temp=150.0, dist=50.0, seq=2, test_id=101, timestamp=now)
    assert is_valid is False
    assert "OUT_OF_BOUNDS" in status

    # Out of bounds ultrasonic distance
    is_valid, status, details = val.validate_reading(node_id=2, temp=25.0, dist=500.0, seq=3, test_id=101, timestamp=now)
    assert is_valid is False
    assert "DISTANCE_OUT_OF_BOUNDS" in status

    # Duplicate detection
    is_valid, status, details = val.validate_reading(node_id=2, temp=25.0, dist=50.0, seq=1, test_id=101, timestamp=now)
    assert details["is_duplicate"] is True

# 2. Test Feature Engineer
def test_feature_engineering_transformer():
    fe = TwinNodeFeatureEngineer(rolling_window=3)
    sample_data = pd.DataFrame({
        "temperature": [25.0, 25.5, 26.0, 26.8, 27.5],
        "distance": [50.0, 49.5, 49.0, 48.0, 47.0],
        "target_temperature": [25.0, 25.0, 25.0, 25.0, 25.0],
        "target_distance": [50.0, 50.0, 50.0, 50.0, 50.0],
        "uart_latency_ms": [5.0, 5.2, 5.1, 5.5, 5.3],
        "packet_loss": [0.0, 0.0, 0.0, 0.0, 0.0],
        "response_delay_ms": [10.0, 10.0, 10.0, 10.0, 10.0],
        "led_command": ["GREEN_ON"] * 5,
        "led_acknowledgement": ["ACK_RECEIVED"] * 5
    })

    fe.fit(sample_data)
    transformed = fe.transform(sample_data)

    assert isinstance(transformed, pd.DataFrame)
    assert list(transformed.columns) == CANONICAL_FEATURES
    assert len(transformed) == len(sample_data)
    assert not transformed.isnull().values.any()
    assert (transformed["sensor_stability_score"] >= 0.0).all()
    assert (transformed["sensor_stability_score"] <= 100.0).all()

# 3. Test Chronological Splitting Without Data Leakage
def test_chronological_session_split():
    df = pd.DataFrame({
        "test_id": [101]*10 + [102]*10 + [103]*10 + [104]*10 + [105]*10,
        "timestamp": pd.date_range("2026-10-31 00:00:00", periods=50, freq="1s"),
        "temperature": np.random.uniform(20, 30, 50),
        "distance": np.random.uniform(30, 60, 50)
    })

    train_df, test_df = chronological_session_split(df, test_size=0.2, session_col="test_id")
    assert len(train_df) > 0
    assert len(test_df) > 0
    # Strict session separation: no session in test exists in train
    assert set(train_df["test_id"]).isdisjoint(set(test_df["test_id"]))
    # Train comes strictly before test in time
    assert train_df["timestamp"].max() <= test_df["timestamp"].min()

# 4. Test Model Training, Serialization, and Artifact Loading
@pytest.mark.asyncio
async def test_model_training_and_registry():
    # Train Decision Tree
    res = await train_model(
        algorithm="DecisionTree",
        model_name="Test_DecisionTree_Model",
        set_active=True
    )

    assert res["status"] == "COMPLETED"
    assert "metrics" in res
    assert res["metrics"]["accuracy"] >= 0.0
    assert res["metrics"]["inference_latency_ms"] >= 0.0

    # Verify model was registered and can be loaded
    active_id, pipeline, meta = await model_registry.get_active_model()
    assert active_id == res["model_id"]
    assert pipeline is not None
    assert meta["algorithm"] == "DecisionTree"

    # Verify inference on dummy test sample
    dummy_input = pd.DataFrame([{
        "temperature": 25.0,
        "distance": 50.0,
        "target_temperature": 25.0,
        "target_distance": 50.0,
        "uart_latency_ms": 5.0,
        "packet_loss": 0.0,
        "response_delay_ms": 10.0,
        "led_command": "GREEN_ON",
        "led_acknowledgement": "ACK_RECEIVED",
        "data_source": "SIMULATION"
    }])
    pred = pipeline.predict(dummy_input)
    assert len(pred) == 1
    assert isinstance(pred[0], str)

# 5. Test Unsupervised Anomaly Detection
def test_isolation_forest_anomaly_detector():
    normal_data = pd.DataFrame({
        "temperature": np.random.normal(25.0, 0.2, 100),
        "distance": np.random.normal(50.0, 0.5, 100),
        "target_temperature": [25.0] * 100,
        "target_distance": [50.0] * 100,
        "uart_latency_ms": np.random.normal(5.0, 0.5, 100),
        "packet_loss": [0.0] * 100,
        "response_delay_ms": [10.0] * 100,
        "led_command": ["GREEN_ON"] * 100,
        "led_acknowledgement": ["ACK_RECEIVED"] * 100
    })

    detector = TwinNodeAnomalyDetector(contamination=0.05)
    detector.fit(normal_data)

    # Extreme anomalous point
    anomalous_data = pd.DataFrame([{
        "temperature": 115.0,
        "distance": 0.0,
        "target_temperature": 25.0,
        "target_distance": 50.0,
        "uart_latency_ms": 800.0,
        "packet_loss": 60.0,
        "response_delay_ms": 900.0,
        "led_command": "RED_ON",
        "led_acknowledgement": "TIMEOUT"
    }])

    is_anomaly, score = detector.score_samples(anomalous_data)
    assert len(score) == 1
    assert score[0] >= 0.6 # High anomaly score for extreme spike

# 6. Test Real-Time Inference & Safety Priority
@pytest.mark.asyncio
async def test_prediction_service_and_safety_fusion():
    pred_svc = PredictionService()

    reading = {
        "temperature": 25.1,
        "distance": 49.8,
        "target_temperature": 25.0,
        "target_distance": 50.0,
        "uart_latency_ms": 5.0,
        "packet_loss": 0.0,
        "response_delay_ms": 10.0,
        "led_command": "GREEN_ON",
        "led_acknowledgement": "ACK_RECEIVED",
        "data_source": "SIMULATION"
    }

    # Test nominal prediction
    res = await pred_svc.predict_latest(current_record=reading, layer1_rule_fault=None)
    assert res["status"] == "SUCCESS"
    assert "suggested_led" in res

    # Test emergency stop override from Layer 1 safety
    e_stop_fault = {"fault_code": "EMERGENCY_STOP", "severity": "CRITICAL"}
    e_stop_res = await pred_svc.predict_latest(current_record=reading, layer1_rule_fault=e_stop_fault)
    assert e_stop_res["suggested_led"] == "ALL_OFF"
    assert "RULE_BASED_SAFETY_TRIP" in e_stop_res["fault_type"]

# 7. Test REST ML Endpoints
@pytest.mark.asyncio
async def test_ml_api_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # GET /api/ml/models
        res = await ac.get("/api/ml/models")
        assert res.status_code == 200
        models_list = res.json()
        assert isinstance(models_list, list)

        # GET /api/ml/metrics
        res_met = await ac.get("/api/ml/metrics")
        assert res_met.status_code == 200

        # POST /api/ml/predict
        pred_payload = {
            "temperature": 25.2,
            "distance": 49.5,
            "target_temperature": 25.0,
            "target_distance": 50.0,
            "uart_latency_ms": 4.5,
            "packet_loss": 0.0,
            "response_delay_ms": 10.0,
            "led_command": "GREEN_ON",
            "led_acknowledgement": "ACK_RECEIVED",
            "data_source": "SIMULATION"
        }
        res_pred = await ac.post("/api/ml/predict", json=pred_payload)
        assert res_pred.status_code == 200
        pred_data = res_pred.json()
        assert pred_data["status"] == "SUCCESS"
        assert "predicted_label" in pred_data

        # GET /api/ml/dataset
        res_ds = await ac.get("/api/ml/dataset?limit=5")
        assert res_ds.status_code == 200
        ds_data = res_ds.json()
        assert "summary" in ds_data
        assert "records" in ds_data

        # GET /api/ml/eda/summary
        res_eda = await ac.get("/api/ml/eda/summary")
        assert res_eda.status_code == 200
        eda_data = res_eda.json()
        assert "total_samples" in eda_data
        assert "class_distribution" in eda_data

# 8. Test Task 1: SENSOR_FAULT Survival in Preprocessing
def test_sensor_fault_records_survive_preprocessing():
    """
    Task 1: Verify that intentional SENSOR_FAULT samples survive clean_dataset()
    even when sensor_validity is False, while invalid readings from nominal
    operation are filtered out.
    """
    raw_df = pd.DataFrame({
        "timestamp": pd.date_range("2026-10-31 00:00:00", periods=6, freq="1s"),
        "node_id": [2, 2, 2, 2, 2, 2],
        "packet_sequence": [1, 2, 3, 4, 5, 6],
        "temperature": [25.0, 150.0, 150.0, 25.0, -99.0, 25.0],
        "distance": [50.0, 50.0, 50.0, 500.0, 50.0, 50.0],
        "sensor_validity": [True, False, False, False, False, True],
        "condition_label": [
            "NORMAL_OPERATION",        # Nominal valid -> KEEP
            "NORMAL_OPERATION",        # Nominal with invalid sensor -> FILTER OUT
            "SENSOR_FAULT",            # Intentional sensor fault with invalid sensor -> MUST PRESERVE
            "NORMAL_OPERATION",        # Nominal out of bounds distance -> FILTER OUT
            "SENSOR_FAULT",            # Intentional negative temp fault -> MUST PRESERVE
            "NORMAL_OPERATION"         # Nominal valid -> KEEP
        ]
    })

    cleaned_df, summary = clean_dataset(raw_df, filter_invalid=True, preserve_sensor_faults=True)

    # Both SENSOR_FAULT records must survive
    sensor_faults = cleaned_df[cleaned_df["condition_label"] == "SENSOR_FAULT"]
    assert len(sensor_faults) == 2
    assert (sensor_faults["sensor_validity"] == False).all()

    # The 2 invalid NORMAL_OPERATION records must be filtered out
    nominal_invalid = cleaned_df[(cleaned_df["condition_label"] == "NORMAL_OPERATION") & (cleaned_df["sensor_validity"] == False)]
    assert len(nominal_invalid) == 0

    # Total remaining rows: 2 nominal valid + 2 sensor faults = 4
    assert len(cleaned_df) == 4
    assert summary["invalid_removed"] == 2
    assert summary["final_rows"] == 4

# 9. Test Task 2: StratifiedGroupKFold Independent Session Splitting & 6-Class Coverage
def test_stratified_group_kfold_session_split_all_six_classes():
    """
    Task 2: Verify StratifiedGroupKFold partitions data by independent sessions (test_id)
    with strictly 0 session overlap and multi-class representation across all six condition classes.
    """
    classes = [
        "NORMAL_OPERATION",
        "SETPOINT_DEVIATION",
        "ACTUATOR_COMMAND_FAILURE",
        "SENSOR_FAULT",
        "COMMUNICATION_FAULT",
        "UNEXPECTED_RESPONSE"
    ]

    # Generate synthetic dataset across 18 independent sessions
    rows = []
    for sess_id in range(2001, 2019):
        c_idx = (sess_id - 2001) % len(classes)
        primary_cls = classes[c_idx]
        for seq in range(20):
            c = primary_cls if seq < 16 else "NORMAL_OPERATION"
            rows.append({
                "test_id": sess_id,
                "node_id": 2,
                "packet_sequence": seq,
                "timestamp": pd.Timestamp("2026-10-31") + pd.Timedelta(seconds=seq),
                "temperature": 25.0,
                "distance": 50.0,
                "target_temperature": 25.0,
                "target_distance": 50.0,
                "uart_latency_ms": 5.0,
                "packet_loss": 0.0,
                "response_delay_ms": 10.0,
                "sensor_validity": (c != "SENSOR_FAULT"),
                "led_command": "GREEN_ON",
                "led_acknowledgement": "ACK_RECEIVED",
                "condition_label": c
            })

    df = pd.DataFrame(rows)

    train_df, val_df, test_df, report = session_train_val_test_split(
        df,
        n_splits=6,
        session_col="test_id",
        label_col="condition_label",
        random_seed=42
    )

    # 1. Zero session overlap
    train_sess = set(train_df["test_id"])
    val_sess = set(val_df["test_id"])
    test_sess = set(test_df["test_id"])

    assert train_sess.isdisjoint(val_sess)
    assert train_sess.isdisjoint(test_sess)
    assert val_sess.isdisjoint(test_sess)
    assert report["session_overlap"] == 0
    assert report["zero_leakage_verified"] is True

    # 2. Check representation of classes in training
    for c in classes:
        assert c in train_df["condition_label"].values, f"Class {c} missing from train split"

    # 3. Test explicit reporting when a class is constrained to only 1 session
    constrained_df = df[~df["condition_label"].isin(["COMMUNICATION_FAULT"])].copy()
    one_session_cf = pd.DataFrame([{
        "test_id": 9999,
        "node_id": 2,
        "packet_sequence": 1,
        "timestamp": pd.Timestamp("2026-10-31"),
        "temperature": 25.0,
        "distance": 50.0,
        "target_temperature": 25.0,
        "target_distance": 50.0,
        "uart_latency_ms": 5.0,
        "packet_loss": 0.0,
        "response_delay_ms": 10.0,
        "sensor_validity": True,
        "led_command": "GREEN_ON",
        "led_acknowledgement": "ACK_RECEIVED",
        "condition_label": "COMMUNICATION_FAULT"
    }])
    constrained_df = pd.concat([constrained_df, one_session_cf], ignore_index=True)

    _, _, _, constr_report = session_train_val_test_split(
        constrained_df,
        n_splits=4,
        session_col="test_id",
        label_col="condition_label",
        random_seed=42
    )
    # Must report the exact reason instead of silently omitting
    assert len(constr_report["class_representation_warnings"]) > 0
    assert any("COMMUNICATION_FAULT" in w and "only 1 independent session" in w for w in constr_report["class_representation_warnings"])

# 10. Test Task 5: Model Save, Reload and Predict
@pytest.mark.asyncio
async def test_model_save_reload_and_predict():
    """
    Task 5: Test model serialization, saving to disk artifact, reloading, and inference.
    """
    res = await train_model(
        algorithm="RandomForest",
        model_name="Test_RF_Serialization",
        set_active=True
    )
    model_id = res["model_id"]

    # Verify artifact files exist on disk
    artifact_file = Path("backend/models/saved") / f"{model_id}.joblib"
    metadata_file = Path("backend/models/metadata") / f"{model_id}.json"
    assert artifact_file.exists()
    assert metadata_file.exists()

    # Reload model from disk via model_registry
    loaded_pipeline, loaded_meta = await model_registry.load_model(model_id)
    assert loaded_pipeline is not None
    assert loaded_meta["model_id"] == model_id
    assert loaded_meta["algorithm"] == "RandomForest"

    # Perform test prediction
    test_sample = pd.DataFrame([{
        "temperature": 25.0,
        "distance": 50.0,
        "target_temperature": 25.0,
        "target_distance": 50.0,
        "uart_latency_ms": 5.0,
        "packet_loss": 0.0,
        "response_delay_ms": 10.0,
        "led_command": "GREEN_ON",
        "led_acknowledgement": "ACK_RECEIVED",
        "data_source": "SIMULATION"
    }])
    pred = loaded_pipeline.predict(test_sample)
    assert len(pred) == 1
    assert pred[0] in [
        "NORMAL_OPERATION",
        "SETPOINT_DEVIATION",
        "ACTUATOR_COMMAND_FAILURE",
        "SENSOR_FAULT",
        "COMMUNICATION_FAULT",
        "UNEXPECTED_RESPONSE"
    ]

