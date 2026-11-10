from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, Text, JSON
from backend.app.db.session import Base

def utc_now():
    return datetime.now(timezone.utc)

class TestSession(Base):
    __tablename__ = "test_sessions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    test_id = Column(Integer, unique=True, index=True)
    name = Column(String(100), nullable=False)
    profile = Column(String(50), default="STANDARD_INDUSTRIAL")
    status = Column(String(20), default="IDLE") # IDLE, RUNNING, PAUSED, STOPPED, COMPLETED, ABORTED
    start_time = Column(DateTime, default=utc_now)
    end_time = Column(DateTime, nullable=True)
    config_json = Column(JSON, nullable=True)
    result_summary = Column(Text, nullable=True)
    total_samples = Column(Integer, default=0)
    total_faults = Column(Integer, default=0)

class TelemetryRecord(Base):
    __tablename__ = "telemetry_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, default=utc_now, index=True)
    test_id = Column(Integer, index=True)
    
    node1_status = Column(String(20), default="ONLINE")
    node2_status = Column(String(20), default="ONLINE")
    
    target_temp = Column(Float, nullable=False)
    actual_temp = Column(Float, nullable=False)
    
    target_dist = Column(Float, nullable=False)
    actual_dist = Column(Float, nullable=False)
    
    target_motor_speed = Column(Integer, nullable=False)
    actual_motor_speed = Column(Integer, nullable=False)
    
    target_servo_angle = Column(Integer, nullable=False)
    actual_servo_angle = Column(Integer, nullable=False)
    
    comm_latency_ms = Column(Float, default=0.0)
    fault_code = Column(Integer, default=0)
    is_simulated = Column(Boolean, default=False)

class FaultEvent(Base):
    __tablename__ = "fault_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, default=utc_now, index=True)
    test_id = Column(Integer, index=True, nullable=True)
    
    fault_code = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False) # INFO, WARNING, CRITICAL
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    recommended_action = Column(Text, nullable=False)
    
    is_acknowledged = Column(Boolean, default=False)
    ack_timestamp = Column(DateTime, nullable=True)

class NodeDiagnostic(Base):
    __tablename__ = "node_diagnostics"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    node_id = Column(Integer, unique=True, index=True)
    is_online = Column(Boolean, default=False)
    last_heartbeat = Column(DateTime, default=utc_now)
    packets_tx = Column(Integer, default=0)
    packets_rx = Column(Integer, default=0)
    crc_errors = Column(Integer, default=0)
    timeouts = Column(Integer, default=0)
    firmware_version = Column(String(20), default="1.0.0")

class RawSensorData(Base):
    __tablename__ = "raw_sensor_data"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, default=utc_now, index=True)
    node_id = Column(Integer, default=2, index=True)
    test_id = Column(Integer, index=True, nullable=True)
    
    temperature = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    distance = Column(Float, nullable=True)
    target_temperature = Column(Float, nullable=True)
    target_distance = Column(Float, nullable=True)
    
    temperature_error = Column(Float, nullable=True)
    distance_error = Column(Float, nullable=True)
    temperature_rate = Column(Float, nullable=True)
    distance_rate = Column(Float, nullable=True)
    
    response_delay_ms = Column(Float, default=0.0)
    uart_latency_ms = Column(Float, default=0.0)
    packet_sequence = Column(Integer, default=0)
    packet_loss = Column(Float, default=0.0)
    sensor_validity = Column(Boolean, default=True)
    
    led_command = Column(String(50), default="GREEN_ON")
    led_acknowledgement = Column(String(50), default="ACK_RECEIVED")
    operating_mode = Column(String(50), default="NORMAL")
    condition_label = Column(String(50), default="NORMAL_OPERATION", index=True)
    data_source = Column(String(20), default="SIMULATION", index=True) # REAL_HARDWARE or SIMULATION
    is_duplicate = Column(Boolean, default=False)
    raw_message = Column(String(255), nullable=True)

class ProcessedSensorData(Base):
    __tablename__ = "processed_sensor_data"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    raw_id = Column(Integer, nullable=True, index=True)
    timestamp = Column(DateTime, default=utc_now, index=True)
    test_id = Column(Integer, index=True, nullable=True)
    
    rolling_temp_mean = Column(Float, nullable=True)
    rolling_temp_std = Column(Float, nullable=True)
    temp_rate_of_change = Column(Float, nullable=True)
    rolling_dist_mean = Column(Float, nullable=True)
    dist_rate_of_change = Column(Float, nullable=True)
    target_temp_dev = Column(Float, nullable=True)
    target_dist_dev = Column(Float, nullable=True)
    latency_mean = Column(Float, nullable=True)
    packet_loss_rate = Column(Float, nullable=True)
    sensor_stability_score = Column(Float, nullable=True)
    response_delay = Column(Float, nullable=True)
    led_mismatch = Column(Integer, default=0)
    
    condition_label = Column(String(50), default="NORMAL_OPERATION", index=True)
    data_source = Column(String(20), default="SIMULATION")

class DatasetVersion(Base):
    __tablename__ = "dataset_versions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    version_id = Column(String(50), unique=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    file_path = Column(String(255), nullable=False)
    total_samples = Column(Integer, default=0)
    real_samples = Column(Integer, default=0)
    sim_samples = Column(Integer, default=0)
    num_features = Column(Integer, default=0)
    split_strategy = Column(String(50), default="CHRONOLOGICAL_BY_SESSION")
    train_count = Column(Integer, default=0)
    test_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=utc_now)

class TrainingRun(Base):
    __tablename__ = "training_runs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    run_id = Column(String(50), unique=True, index=True)
    model_name = Column(String(100), nullable=False)
    algorithm = Column(String(50), nullable=False)
    dataset_version = Column(String(50), nullable=False)
    status = Column(String(20), default="RUNNING") # RUNNING, COMPLETED, FAILED
    hyperparameters = Column(JSON, nullable=True)
    feature_list = Column(JSON, nullable=True)
    training_samples = Column(Integer, default=0)
    test_samples = Column(Integer, default=0)
    start_time = Column(DateTime, default=utc_now)
    end_time = Column(DateTime, nullable=True)
    training_time_ms = Column(Float, default=0.0)
    metrics_json = Column(JSON, nullable=True)

class ModelRegistry(Base):
    __tablename__ = "model_registry"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    model_id = Column(String(50), unique=True, index=True)
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(20), default="1.0.0")
    algorithm_type = Column(String(50), default="SUPERVISED") # SUPERVISED or UNSUPERVISED
    algorithm = Column(String(50), nullable=False)
    artifact_path = Column(String(255), nullable=False)
    metadata_path = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=False)
    target_label = Column(String(50), default="condition_label")
    feature_list = Column(JSON, nullable=False)
    accuracy = Column(Float, nullable=True)
    f1_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=utc_now)

class ModelMetric(Base):
    __tablename__ = "model_metrics"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    model_id = Column(String(50), index=True)
    run_id = Column(String(50), nullable=True)
    accuracy = Column(Float, default=0.0)
    precision_macro = Column(Float, default=0.0)
    recall_macro = Column(Float, default=0.0)
    f1_macro = Column(Float, default=0.0)
    confusion_matrix = Column(JSON, nullable=True)
    classification_report = Column(JSON, nullable=True)
    feature_importance = Column(JSON, nullable=True)
    inference_latency_ms = Column(Float, default=0.0)
    evaluation_date = Column(DateTime, default=utc_now)

class PredictionRecord(Base):
    __tablename__ = "prediction_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, default=utc_now, index=True)
    test_id = Column(Integer, nullable=True, index=True)
    model_id = Column(String(50), index=True)
    raw_record_id = Column(Integer, nullable=True)
    predicted_label = Column(String(50), nullable=False)
    confidence = Column(Float, nullable=True)
    anomaly_score = Column(Float, nullable=True)
    is_anomaly = Column(Boolean, default=False)
    data_source = Column(String(20), default="SIMULATION")
    features_used = Column(JSON, nullable=True)

class AnomalyEvent(Base):
    __tablename__ = "anomaly_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, default=utc_now, index=True)
    test_id = Column(Integer, nullable=True, index=True)
    model_id = Column(String(50), index=True)
    anomaly_score = Column(Float, nullable=False)
    threshold = Column(Float, nullable=False)
    details = Column(JSON, nullable=True)
    suggested_action = Column(Text, nullable=True)
    is_acknowledged = Column(Boolean, default=False)

