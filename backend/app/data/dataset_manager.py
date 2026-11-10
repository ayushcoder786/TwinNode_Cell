"""
TwinNode Dataset Manager
Manages raw & processed datasets, CSV import/export, dataset versioning,
and chronological dataset splits.
"""

import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
from sqlalchemy import select, and_, desc

from backend.app.db.session import AsyncSessionLocal
from backend.app.models.schema import RawSensorData, DatasetVersion, utc_now
from backend.app.data.preprocessing import clean_dataset, chronological_session_split

DATASETS_DIR = Path(__file__).resolve().parent.parent.parent / "datasets"
RAW_DIR = DATASETS_DIR / "raw"
PROCESSED_DIR = DATASETS_DIR / "processed"
TRAIN_DIR = DATASETS_DIR / "training"
TEST_DIR = DATASETS_DIR / "testing"

class DatasetManager:
    """Manages persistent datasets, CSV exports/imports, and version snapshots."""

    def __init__(self):
        for directory in [RAW_DIR, PROCESSED_DIR, TRAIN_DIR, TEST_DIR]:
            directory.mkdir(parents=True, exist_ok=True)

    async def export_to_dataframe(
        self,
        node_id: Optional[int] = None,
        test_id: Optional[int] = None,
        data_source: Optional[str] = None,
        condition_label: Optional[str] = None,
        limit: int = 50000
    ) -> pd.DataFrame:
        """Query raw sensor records from SQLite into a Pandas DataFrame."""
        async with AsyncSessionLocal() as session:
            stmt = select(RawSensorData)
            filters = []
            if node_id is not None:
                filters.append(RawSensorData.node_id == node_id)
            if test_id is not None:
                filters.append(RawSensorData.test_id == test_id)
            if data_source is not None:
                filters.append(RawSensorData.data_source == data_source.upper())
            if condition_label is not None:
                filters.append(RawSensorData.condition_label == condition_label)
            if filters:
                stmt = stmt.where(and_(*filters))

            stmt = stmt.order_by(RawSensorData.timestamp.asc()).limit(limit)
            result = await session.execute(stmt)
            records = result.scalars().all()

            if not records:
                return pd.DataFrame()

            data = [{
                "id": r.id,
                "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                "node_id": r.node_id,
                "test_id": r.test_id,
                "temperature": r.temperature,
                "distance": r.distance,
                "target_temperature": r.target_temperature,
                "target_distance": r.target_distance,
                "temperature_error": r.temperature_error,
                "distance_error": r.distance_error,
                "temperature_rate": r.temperature_rate,
                "distance_rate": r.distance_rate,
                "response_delay_ms": r.response_delay_ms,
                "uart_latency_ms": r.uart_latency_ms,
                "packet_sequence": r.packet_sequence,
                "packet_loss": r.packet_loss,
                "sensor_validity": r.sensor_validity,
                "led_command": r.led_command,
                "led_acknowledgement": r.led_acknowledgement,
                "operating_mode": r.operating_mode,
                "condition_label": r.condition_label,
                "data_source": r.data_source,
                "is_duplicate": r.is_duplicate
            } for r in records]

            return pd.DataFrame(data)

    async def export_csv(
        self,
        output_filename: str,
        node_id: Optional[int] = None,
        test_id: Optional[int] = None,
        data_source: Optional[str] = None
    ) -> str:
        """Export filtered data to CSV in datasets/raw/ directory."""
        df = await self.export_to_dataframe(node_id=node_id, test_id=test_id, data_source=data_source)
        file_path = RAW_DIR / output_filename
        df.to_csv(file_path, index=False)
        return str(file_path)

    async def import_csv(
        self,
        csv_path: str,
        data_source_override: Optional[str] = None
    ) -> Dict[str, Any]:
        """Import sensor data from a CSV file into SQLite with provenance tracking."""
        df = pd.read_csv(csv_path)
        required_cols = ["temperature", "distance"]
        if not all(col in df.columns for col in required_cols):
            raise ValueError(f"CSV must contain at least columns: {required_cols}")

        now = datetime.now(timezone.utc)
        imported_count = 0

        async with AsyncSessionLocal() as session:
            async with session.begin():
                for _, row in df.iterrows():
                    ts = row.get("timestamp")
                    if isinstance(ts, str):
                        try:
                            parsed_ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        except Exception:
                            parsed_ts = now
                    else:
                        parsed_ts = now

                    src = data_source_override or str(row.get("data_source", "SIMULATION")).upper()

                    record = RawSensorData(
                        timestamp=parsed_ts,
                        node_id=int(row.get("node_id", 2)),
                        test_id=int(row.get("test_id", 1001)) if pd.notna(row.get("test_id")) else None,
                        temperature=float(row["temperature"]) if pd.notna(row["temperature"]) else None,
                        distance=float(row["distance"]) if pd.notna(row["distance"]) else None,
                        target_temperature=float(row["target_temperature"]) if pd.notna(row.get("target_temperature")) else None,
                        target_distance=float(row["target_distance"]) if pd.notna(row.get("target_distance")) else None,
                        temperature_error=float(row["temperature_error"]) if pd.notna(row.get("temperature_error")) else None,
                        distance_error=float(row["distance_error"]) if pd.notna(row.get("distance_error")) else None,
                        temperature_rate=float(row["temperature_rate"]) if pd.notna(row.get("temperature_rate")) else 0.0,
                        distance_rate=float(row["distance_rate"]) if pd.notna(row.get("distance_rate")) else 0.0,
                        response_delay_ms=float(row.get("response_delay_ms", 0.0)),
                        uart_latency_ms=float(row.get("uart_latency_ms", 0.0)),
                        packet_sequence=int(row.get("packet_sequence", 0)),
                        packet_loss=float(row.get("packet_loss", 0.0)),
                        sensor_validity=bool(row.get("sensor_validity", True)),
                        led_command=str(row.get("led_command", "GREEN_ON")),
                        led_acknowledgement=str(row.get("led_acknowledgement", "ACK_RECEIVED")),
                        operating_mode=str(row.get("operating_mode", "NORMAL")),
                        condition_label=str(row.get("condition_label", "NORMAL_OPERATION")),
                        data_source=src,
                        is_duplicate=bool(row.get("is_duplicate", False))
                    )
                    session.add(record)
                    imported_count += 1
            await session.commit()

        return {"status": "SUCCESS", "records_imported": imported_count, "data_source": data_source_override or "PRESERVED"}

    async def create_dataset_version(
        self,
        name: str,
        description: str = "",
        test_size: float = 0.2
    ) -> Dict[str, Any]:
        """
        Snapshot current database into a versioned training/testing split dataset.
        Saves CSV artifacts and registers in DatasetVersion table.
        """
        df = await self.export_to_dataframe(limit=100000)
        if len(df) == 0:
            raise ValueError("No sensor data available in database to snapshot.")

        v_id = f"DS-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
        
        # Clean
        cleaned_df, clean_info = clean_dataset(df)
        
        # Chronological split
        train_df, test_df = chronological_session_split(cleaned_df, test_size=test_size)

        # File paths
        raw_path = RAW_DIR / f"{v_id}_raw.csv"
        train_path = TRAIN_DIR / f"{v_id}_train.csv"
        test_path = TEST_DIR / f"{v_id}_test.csv"

        df.to_csv(raw_path, index=False)
        train_df.to_csv(train_path, index=False)
        test_df.to_csv(test_path, index=False)

        real_count = int((df["data_source"] == "REAL_HARDWARE").sum()) if "data_source" in df.columns else 0
        sim_count = int((df["data_source"] == "SIMULATION").sum()) if "data_source" in df.columns else len(df)

        version_record = DatasetVersion(
            version_id=v_id,
            name=name,
            description=description,
            file_path=str(raw_path),
            total_samples=len(df),
            real_samples=real_count,
            sim_samples=sim_count,
            num_features=len(df.columns),
            split_strategy="CHRONOLOGICAL_BY_SESSION",
            train_count=len(train_df),
            test_count=len(test_df),
            created_at=utc_now()
        )

        async with AsyncSessionLocal() as session:
            session.add(version_record)
            await session.commit()

        return {
            "version_id": v_id,
            "name": name,
            "total_samples": len(df),
            "real_samples": real_count,
            "sim_samples": sim_count,
            "train_samples": len(train_df),
            "test_samples": len(test_df),
            "raw_file": str(raw_path),
            "train_file": str(train_path),
            "test_file": str(test_path)
        }

    async def list_versions(self) -> List[Dict[str, Any]]:
        """List all registered dataset versions."""
        async with AsyncSessionLocal() as session:
            stmt = select(DatasetVersion).order_by(desc(DatasetVersion.created_at))
            result = await session.execute(stmt)
            versions = result.scalars().all()
            return [{
                "version_id": v.version_id,
                "name": v.name,
                "description": v.description,
                "total_samples": v.total_samples,
                "real_samples": v.real_samples,
                "sim_samples": v.sim_samples,
                "train_count": v.train_count,
                "test_count": v.test_count,
                "created_at": v.created_at.isoformat() if v.created_at else None
            } for v in versions]

dataset_manager = DatasetManager()
