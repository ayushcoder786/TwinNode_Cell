"""
TwinNode Model Registry
Handles serialization, versioning, metadata logging, and activation of trained ML models.
Stores pipelines together with feature transformers in joblib format.
"""

import os
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
import joblib
from sqlalchemy import select, update, desc

from backend.app.db.session import AsyncSessionLocal
from backend.app.models.schema import ModelRegistry as ModelRegistryTable, ModelMetric, utc_now

MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "models"
SAVED_DIR = MODELS_DIR / "saved"
METADATA_DIR = MODELS_DIR / "metadata"

class ModelRegistry:
    """Manages ML model lifecycle, serialization, and active deployment pointer."""

    def __init__(self):
        SAVED_DIR.mkdir(parents=True, exist_ok=True)
        METADATA_DIR.mkdir(parents=True, exist_ok=True)
        self._cached_active_id: Optional[str] = None
        self._cached_active_pipeline = None
        self._cached_metadata: Optional[Dict[str, Any]] = None

    async def register_model(
        self,
        pipeline,
        model_id: str,
        model_name: str,
        algorithm: str,
        algorithm_type: str,
        dataset_version: str,
        metrics: Dict[str, Any],
        feature_list: List[str],
        hyperparameters: Dict[str, Any],
        is_active: bool = False
    ) -> Dict[str, Any]:
        """
        Serialize model pipeline via joblib, write metadata JSON,
        and insert into SQLite model registry.
        """
        artifact_path = SAVED_DIR / f"{model_id}.joblib"
        metadata_path = METADATA_DIR / f"{model_id}.json"

        # 1. Save pipeline (contains both preprocessor & classifier)
        joblib.dump(pipeline, artifact_path)

        # 2. Build metadata payload
        now_iso = datetime.now(timezone.utc).isoformat()
        metadata = {
            "model_id": model_id,
            "model_name": model_name,
            "model_version": "1.0.0",
            "algorithm": algorithm,
            "algorithm_type": algorithm_type,
            "training_date": now_iso,
            "dataset_version": dataset_version,
            "feature_list": feature_list,
            "hyperparameters": hyperparameters,
            "metrics": metrics,
            "artifact_path": str(artifact_path),
            "metadata_path": str(metadata_path)
        }

        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        # 3. Insert into Database
        async with AsyncSessionLocal() as session:
            if is_active:
                await session.execute(update(ModelRegistryTable).values(is_active=False))

            registry_entry = ModelRegistryTable(
                model_id=model_id,
                model_name=model_name,
                model_version="1.0.0",
                algorithm_type=algorithm_type,
                algorithm=algorithm,
                artifact_path=str(artifact_path),
                metadata_path=str(metadata_path),
                is_active=is_active,
                target_label="condition_label",
                feature_list=feature_list,
                accuracy=metrics.get("accuracy"),
                f1_score=metrics.get("f1_macro"),
                created_at=utc_now()
            )
            session.add(registry_entry)

            # Record detailed metrics
            metric_entry = ModelMetric(
                model_id=model_id,
                accuracy=metrics.get("accuracy", 0.0),
                precision_macro=metrics.get("precision_macro", 0.0),
                recall_macro=metrics.get("recall_macro", 0.0),
                f1_macro=metrics.get("f1_macro", 0.0),
                confusion_matrix=metrics.get("confusion_matrix"),
                classification_report=metrics.get("classification_report"),
                feature_importance=metrics.get("feature_importance"),
                inference_latency_ms=metrics.get("inference_latency_ms", 0.0),
                evaluation_date=utc_now()
            )
            session.add(metric_entry)
            await session.commit()

        if is_active:
            self._cached_active_id = model_id
            self._cached_active_pipeline = pipeline
            self._cached_metadata = metadata

        return metadata

    async def get_active_model(self) -> Tuple[Optional[str], Any, Optional[Dict[str, Any]]]:
        """Fetch currently active deployed model."""
        if self._cached_active_pipeline is not None and self._cached_active_id is not None:
            return self._cached_active_id, self._cached_active_pipeline, self._cached_metadata

        async with AsyncSessionLocal() as session:
            stmt = select(ModelRegistryTable).where(ModelRegistryTable.is_active == True).limit(1) # noqa
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()

            if not record:
                # Fallback to the latest trained model
                stmt2 = select(ModelRegistryTable).order_by(desc(ModelRegistryTable.created_at)).limit(1)
                res2 = await session.execute(stmt2)
                record = res2.scalar_one_or_none()

            if not record:
                return None, None, None

            # Load artifact
            if os.path.exists(record.artifact_path):
                pipeline = joblib.load(record.artifact_path)
                meta = {}
                if os.path.exists(record.metadata_path):
                    with open(record.metadata_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)

                self._cached_active_id = record.model_id
                self._cached_active_pipeline = pipeline
                self._cached_metadata = meta
                return record.model_id, pipeline, meta

        return None, None, None

    async def set_active_model(self, model_id: str) -> bool:
        """Activate a model by ID."""
        async with AsyncSessionLocal() as session:
            await session.execute(update(ModelRegistryTable).values(is_active=False))
            await session.execute(
                update(ModelRegistryTable).where(ModelRegistryTable.model_id == model_id).values(is_active=True)
            )
            await session.commit()

        # Invalidate cache
        self._cached_active_id = None
        self._cached_active_pipeline = None
        self._cached_metadata = None
        await self.get_active_model()
        return True

    async def load_model(self, model_id: str) -> Tuple[Optional[Any], Optional[Dict[str, Any]]]:
        """
        Reload a specific trained model pipeline and its metadata from disk by model_id.
        """
        artifact_path = SAVED_DIR / f"{model_id}.joblib"
        metadata_path = METADATA_DIR / f"{model_id}.json"

        if not artifact_path.exists():
            return None, None

        pipeline = joblib.load(artifact_path)
        metadata = {}
        if metadata_path.exists():
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)

        return pipeline, metadata

    async def list_models(self) -> List[Dict[str, Any]]:
        """List all models registered in the system."""
        async with AsyncSessionLocal() as session:
            stmt = select(ModelRegistryTable).order_by(desc(ModelRegistryTable.created_at))
            result = await session.execute(stmt)
            records = result.scalars().all()
            return [{
                "model_id": r.model_id,
                "model_name": r.model_name,
                "model_version": r.model_version,
                "algorithm_type": r.algorithm_type,
                "algorithm": r.algorithm,
                "is_active": r.is_active,
                "accuracy": r.accuracy,
                "f1_score": r.f1_score,
                "feature_list": r.feature_list,
                "created_at": r.created_at.isoformat() if r.created_at else None
            } for r in records]

model_registry = ModelRegistry()
