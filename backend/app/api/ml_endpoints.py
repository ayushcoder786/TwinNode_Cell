"""
TwinNode ML REST Endpoints
Provides model training, evaluation, real-time prediction, EDA, dataset management,
and model activation APIs.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import os
import shutil
from pathlib import Path
import pandas as pd
from sqlalchemy import select, desc, func

from backend.app.db.session import AsyncSessionLocal
from backend.app.models.schema import ModelRegistry, ModelMetric, PredictionRecord, AnomalyEvent, RawSensorData
from backend.app.data.dataset_manager import dataset_manager
from backend.app.data.collector import collector
from backend.app.eda.analysis import eda_analyzer
from backend.app.eda.visualizations import eda_visualizer, REPORTS_DIR
from backend.app.ml.train import train_model, SUPPORTED_ALGORITHMS
from backend.app.ml.model_registry import model_registry, SAVED_DIR
from backend.app.ml.predict import prediction_service
from backend.app.ml.clustering import TwinNodeClusteringAnalyzer

router = APIRouter(prefix="/ml", tags=["Machine Learning"])

# Request Models
class TrainRequest(BaseModel):
    algorithm: str = "RandomForest"
    dataset_version: Optional[str] = None
    features: Optional[List[str]] = None
    target_column: str = "condition_label"
    scaler_type: str = "standard"
    hyperparameters: Optional[Dict[str, Any]] = None
    model_name: Optional[str] = None
    set_active: bool = True

class PredictRequest(BaseModel):
    temperature: float
    distance: float
    target_temperature: Optional[float] = 25.0
    target_distance: Optional[float] = 50.0
    uart_latency_ms: Optional[float] = 5.0
    packet_loss: Optional[float] = 0.0
    response_delay_ms: Optional[float] = 10.0
    led_command: Optional[str] = "GREEN_ON"
    led_acknowledgement: Optional[str] = "ACK_RECEIVED"
    data_source: Optional[str] = "SIMULATION"

class LEDActuationRequest(BaseModel):
    state: str # GREEN_ON, YELLOW_ON, RED_ON, ALL_OFF
    pwm_duty_cycle: Optional[int] = 100 # 0 to 100%

# 1. Real-time Inference API
@router.post("/predict")
async def predict_sample(req: PredictRequest):
    """Run real-time inference on provided sensor features."""
    rec = req.model_dump()
    result = await prediction_service.predict_latest(current_record=rec)
    # Log prediction asynchronously
    await prediction_service.persist_prediction(result)
    return result

# 2. Model Training API
@router.post("/train")
async def start_training(req: TrainRequest):
    """Train a machine learning algorithm and register the serialized pipeline."""
    try:
        res = await train_model(
            algorithm=req.algorithm,
            dataset_version=req.dataset_version,
            features=req.features,
            target_column=req.target_column,
            scaler_type=req.scaler_type,
            hyperparameters=req.hyperparameters,
            model_name=req.model_name,
            set_active=req.set_active
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# 3. Model Registry & List
@router.get("/models")
async def get_models():
    """List all trained model checkpoints and active status."""
    return await model_registry.list_models()

@router.post("/models/activate/{model_id}")
async def activate_model(model_id: str):
    """Set model as active production model."""
    success = await model_registry.set_active_model(model_id)
    return {"status": "SUCCESS", "active_model_id": model_id}

@router.get("/models/download/{model_id}")
async def download_model_artifact(model_id: str):
    """Download serialized joblib artifact for a specific model."""
    path = SAVED_DIR / f"{model_id}.joblib"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Model artifact file not found.")
    return FileResponse(str(path), media_type="application/octet-stream", filename=f"{model_id}.joblib")

# 4. Metrics API
@router.get("/metrics")
async def get_model_metrics(model_id: Optional[str] = None):
    """Retrieve detailed evaluation metrics for active or specified model."""
    async with AsyncSessionLocal() as session:
        if model_id:
            stmt = select(ModelMetric).where(ModelMetric.model_id == model_id).order_by(desc(ModelMetric.evaluation_date)).limit(1)
        else:
            active_id, _, _ = await model_registry.get_active_model()
            if not active_id:
                return {"message": "No active model available"}
            stmt = select(ModelMetric).where(ModelMetric.model_id == active_id).order_by(desc(ModelMetric.evaluation_date)).limit(1)

        result = await session.execute(stmt)
        metric = result.scalar_one_or_none()
        if not metric:
            return {"message": "No metrics available for this model"}

        return {
            "model_id": metric.model_id,
            "accuracy": metric.accuracy,
            "precision_macro": metric.precision_macro,
            "recall_macro": metric.recall_macro,
            "f1_macro": metric.f1_macro,
            "confusion_matrix": metric.confusion_matrix,
            "classification_report": metric.classification_report,
            "feature_importance": metric.feature_importance,
            "inference_latency_ms": metric.inference_latency_ms,
            "evaluation_date": metric.evaluation_date.isoformat() if metric.evaluation_date else None
        }

# 5. Feature Importance API
@router.get("/feature-importance")
async def get_feature_importance(model_id: Optional[str] = None):
    """Retrieve normalized feature importance or weights of the model."""
    metrics_res = await get_model_metrics(model_id)
    return {
        "model_id": metrics_res.get("model_id"),
        "feature_importance": metrics_res.get("feature_importance", {})
    }

# 6. Predictions History API
@router.get("/predictions")
async def get_recent_predictions(limit: int = 50):
    """Fetch history of recent live predictions and anomaly scores."""
    async with AsyncSessionLocal() as session:
        stmt = select(PredictionRecord).order_by(desc(PredictionRecord.timestamp)).limit(limit)
        result = await session.execute(stmt)
        records = result.scalars().all()
        return [{
            "id": r.id,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            "model_id": r.model_id,
            "predicted_label": r.predicted_label,
            "confidence": r.confidence,
            "anomaly_score": r.anomaly_score,
            "is_anomaly": r.is_anomaly,
            "data_source": r.data_source,
            "features_used": r.features_used
        } for r in records]

# 7. Dataset Management APIs
@router.get("/dataset")
async def get_dataset_records(limit: int = 100, data_source: Optional[str] = None):
    """Retrieve raw dataset samples for dataset table viewer."""
    df = await dataset_manager.export_to_dataframe(limit=limit, data_source=data_source)
    summary = await collector.get_summary_stats()
    return {
        "summary": summary,
        "count": len(df),
        "records": df.to_dict(orient="records") if not df.empty else []
    }

@router.get("/dataset/versions")
async def list_dataset_versions():
    """List versioned dataset snapshots."""
    return await dataset_manager.list_versions()

@router.post("/dataset/snapshot")
async def snapshot_dataset(name: str = "Manual_Snapshot", description: str = ""):
    """Create a new versioned train/test dataset snapshot."""
    return await dataset_manager.create_dataset_version(name=name, description=description)

@router.post("/dataset/import")
async def import_csv_file(file: UploadFile = File(...), data_source: str = "SIMULATION"):
    """Upload and import a custom CSV sensor dataset."""
    dest_path = dataset_manager.RAW_DIR / f"upload_{file.filename}"
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    res = await dataset_manager.import_csv(str(dest_path), data_source_override=data_source)
    return res

@router.get("/dataset/export-csv")
async def export_dataset_csv(data_source: Optional[str] = None):
    """Export current dataset to CSV and download."""
    path = await dataset_manager.export_csv("dataset_export.csv", data_source=data_source)
    return FileResponse(path, media_type="text/csv", filename="twinnode_dataset.csv")

# 8. EDA APIs
@router.get("/eda/summary")
async def get_eda_summary():
    """Compute and return full statistical summary, correlation matrix and histograms."""
    df = await dataset_manager.export_to_dataframe(limit=5000)
    return eda_analyzer.analyze_dataframe(df)

@router.get("/eda/clustering")
async def get_clustering_analysis(n_clusters: int = 4):
    """Run K-Means clustering and PCA 2D projection on current dataset."""
    df = await dataset_manager.export_to_dataframe(limit=2000)
    analyzer = TwinNodeClusteringAnalyzer(n_clusters=n_clusters)
    return analyzer.fit_and_analyze(df)

@router.get("/eda/report-image")
async def get_eda_report_image():
    """Generate and return comprehensive multi-panel EDA chart as PNG."""
    df = await dataset_manager.export_to_dataframe(limit=2000)
    img_path = eda_visualizer.generate_full_eda_report_image(df)
    if not os.path.exists(img_path):
        raise HTTPException(status_code=500, detail="Failed to generate EDA report image.")
    return FileResponse(img_path, media_type="image/png", filename="twinnode_eda_summary.png")

# 9. LED Actuation Testing
@router.post("/actuate-led")
async def actuate_led_command(req: LEDActuationRequest):
    """Send LED command to Node 2 with safety compliance checks."""
    from backend.app.services.supervisor import supervisor
    # Safety Check: if emergency stopped, refuse manual activation
    if supervisor.condition_engine.is_emergency_stop_latched:
        raise HTTPException(status_code=403, detail="Cannot change LED state during EMERGENCY STOP.")

    # Forward to supervisor to dispatch to hardware / simulation
    supervisor.led_state = req.state
    supervisor.led_pwm_duty = req.pwm_duty_cycle
    return {
        "status": "COMMAND_DISPATCHED",
        "commanded_led": req.state,
        "pwm_duty": req.pwm_duty_cycle,
        "feedback_mode": "OPEN_LOOP",
        "acknowledgement_type": "SOFTWARE_COMMAND_ACK",
        "has_physical_sensor_feedback": False,
        "note": "Open-loop confirmation: indicates software command acknowledgment only, not physical optical/current feedback.",
        "safety_cleared": True
    }

# 10. Advanced Dataset Expansion & Quality APIs
class GenerateDatasetRequest(BaseModel):
    target_records: int = 16500
    random_seed: int = 42
    scenarios: Optional[List[str]] = None
    confirmed: bool = False

@router.get("/dataset/scenarios")
async def get_available_scenarios():
    """List all available physical simulation scenarios and their condition mappings."""
    from backend.app.data.generate_simulation_dataset import SCENARIO_DEFINITIONS
    return {
        "scenarios": [
            {
                "id": k,
                "class": v["class"],
                "description": v["description"]
            }
            for k, v in SCENARIO_DEFINITIONS.items()
        ]
    }

@router.get("/dataset/quality-report")
async def get_dataset_quality_report():
    """Run non-destructive 7-point data quality and integrity audit."""
    from backend.app.data.data_quality import data_quality_engine
    df = await dataset_manager.export_to_dataframe(limit=100000)
    return data_quality_engine.analyze_dataset_quality(df)

@router.get("/dataset/split-report")
async def get_dataset_split_report():
    """Generate session-based train/val/test split report with 0% session overlap verification."""
    from backend.app.data.preprocessing import clean_dataset, session_train_val_test_split
    raw_df = await dataset_manager.export_to_dataframe(limit=100000)
    if raw_df.empty:
        return {"error": "Dataset empty"}
    clean_df, _ = clean_dataset(raw_df, preserve_sensor_faults=True)
    _, _, _, report = session_train_val_test_split(
        clean_df,
        train_ratio=0.70,
        val_ratio=0.15,
        test_ratio=0.15,
        session_col="test_id",
        label_col="condition_label",
        random_seed=42
    )
    return report

@router.get("/dataset/detailed-stats")
async def get_dataset_detailed_stats():
    """Compute detailed dataset analytics for React ML Studio dashboard."""
    from backend.app.data.preprocessing import clean_dataset, session_train_val_test_split, detect_outliers
    df = await dataset_manager.export_to_dataframe(limit=100000)
    if df.empty:
        return {
            "total_records": 0, "simulation_records": 0, "real_hardware_records": 0,
            "condition_distribution": {}, "session_distribution": {}, "growth_timeline": [],
            "imbalance": {"ratio": 1.0, "is_balanced": True}, "quality": {},
            "split_sizes": {"train": 0, "val": 0, "test": 0}
        }

    total = len(df)
    sim_count = int((df["data_source"] == "SIMULATION").sum()) if "data_source" in df.columns else total
    real_count = int((df["data_source"] == "REAL_HARDWARE").sum()) if "data_source" in df.columns else 0

    # Condition distribution
    cond_counts = df["condition_label"].value_counts().to_dict() if "condition_label" in df.columns else {}
    cond_dist = {str(k): {"count": int(v), "pct": round(float(v / total) * 100.0, 2)} for k, v in cond_counts.items()}

    # Imbalance
    c_vals = list(cond_counts.values())
    imb_ratio = round(float(max(c_vals) / max(1, min(c_vals))), 2) if c_vals else 1.0

    # Session distribution
    sess_counts = df["test_id"].value_counts().to_dict() if "test_id" in df.columns else {}
    sess_dist = {str(k): int(v) for k, v in sorted(sess_counts.items(), key=lambda x: str(x[0]))}

    # Growth timeline (group by timestamp date)
    growth_timeline = []
    if "timestamp" in df.columns:
        df["dt_date"] = pd.to_datetime(df["timestamp"]).dt.strftime("%Y-%m-%d")
        daily = df.groupby("dt_date").size().sort_index()
        cumulative = 0
        for date_str, cnt in daily.items():
            cumulative += int(cnt)
            growth_timeline.append({
                "date": str(date_str),
                "count": int(cnt),
                "cumulative": cumulative
            })

    # Outliers
    outliers = detect_outliers(df)

    # Train / Val / Test split sizes
    clean_df, _ = clean_dataset(df, preserve_sensor_faults=True)
    train_df, val_df, test_df, split_rep = session_train_val_test_split(clean_df, random_seed=42)

    return {
        "total_records": total,
        "simulation_records": sim_count,
        "real_hardware_records": real_count,
        "condition_distribution": cond_dist,
        "session_distribution": sess_dist,
        "growth_timeline": growth_timeline,
        "imbalance": {
            "ratio": imb_ratio,
            "is_balanced": bool(imb_ratio <= 4.0),
            "max_class": max(cond_counts, key=cond_counts.get) if cond_counts else None,
            "min_class": min(cond_counts, key=cond_counts.get) if cond_counts else None
        },
        "quality": {
            "duplicate_records": int(df.duplicated(subset=["timestamp", "node_id", "packet_sequence"]).sum()) if {"timestamp", "node_id", "packet_sequence"}.issubset(df.columns) else int(df.duplicated().sum()),
            "missing_cells": int(df.isnull().sum().sum()),
            "invalid_sensor_readings": int((df["sensor_validity"] == False).sum()) if "sensor_validity" in df.columns else 0,
            "total_outliers": outliers.get("total_outliers", 0)
        },
        "split_sizes": {
            "train": len(train_df),
            "val": len(val_df),
            "test": len(test_df),
            "session_overlap": split_rep.get("session_overlap", 0)
        }
    }

@router.post("/dataset/generate-advanced")
async def generate_advanced_dataset(req: GenerateDatasetRequest):
    """
    Generate diverse physical simulation sessions across all 6 condition classes.
    Requires confirmed=True before database insertion to prevent accidental writes.
    """
    from backend.app.data.generate_simulation_dataset import populate_advanced_simulation_dataset
    from backend.app.models.schema import RawSensorData

    async with AsyncSessionLocal() as session:
        current_count = await session.scalar(select(func.count(RawSensorData.id))) or 0

    records_to_add = max(0, req.target_records - current_count)

    # Safety confirmation guard
    if not req.confirmed:
        return {
            "status": "CONFIRMATION_REQUIRED",
            "current_records": current_count,
            "target_records": req.target_records,
            "records_to_generate": records_to_add,
            "scenarios_selected": req.scenarios or "ALL_SCENARIOS",
            "random_seed": req.random_seed,
            "message": f"This action will generate approximately {records_to_add} unique simulation records across independent sessions. Please confirm execution."
        }

    # Execute generation
    res = await populate_advanced_simulation_dataset(
        target_total_records=req.target_records,
        random_seed=req.random_seed,
        selected_scenarios=req.scenarios
    )
    return res


