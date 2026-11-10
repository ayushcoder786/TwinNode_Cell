"""
Database Models compatibility export.
Re-exports all SQLAlchemy ORM models from backend.app.models.schema.
"""

from backend.app.models.schema import (
    Base,
    utc_now,
    TestSession,
    TelemetryRecord,
    FaultEvent,
    NodeDiagnostic,
    RawSensorData,
    ProcessedSensorData,
    DatasetVersion,
    TrainingRun,
    ModelRegistry,
    ModelMetric,
    PredictionRecord,
    AnomalyEvent,
)

__all__ = [
    "Base",
    "utc_now",
    "TestSession",
    "TelemetryRecord",
    "FaultEvent",
    "NodeDiagnostic",
    "RawSensorData",
    "ProcessedSensorData",
    "DatasetVersion",
    "TrainingRun",
    "ModelRegistry",
    "ModelMetric",
    "PredictionRecord",
    "AnomalyEvent",
]
