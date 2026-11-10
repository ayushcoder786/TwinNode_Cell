"""
TwinNode External Dataset Inspector
Analyzes schema, dimensions, missingness, duplicates, class distribution,
sampling intervals, and sensor units for downloaded or imported external datasets.
"""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd

from backend.app.data.external_dataset_catalog import EXTERNAL_DATASET_CATALOG

BASE_DIR = Path(__file__).resolve().parent.parent.parent
EXTERNAL_ROOT = BASE_DIR / "datasets" / "external"
PROCESSED_ROOT = BASE_DIR / "datasets" / "processed"

class ExternalDatasetInspector:
    """Performs deep inspection of external datasets without mutating raw data."""

    def find_dataset_files(self, dataset_id: str, is_processed: bool = False) -> List[Path]:
        target_dir = (PROCESSED_ROOT if is_processed else EXTERNAL_ROOT) / dataset_id
        if not target_dir.exists():
            return []
        
        valid_extensions = [".csv", ".parquet", ".txt"]
        files = [
            f for f in target_dir.glob("*")
            if f.is_file() and f.suffix.lower() in valid_extensions and not f.name.endswith(".part")
        ]
        return sorted(files, key=lambda x: x.stat().st_size, reverse=True)

    def inspect_file(
        self,
        dataset_id: str,
        filename: Optional[str] = None,
        is_processed: bool = False,
        sample_limit: int = 100000
    ) -> Dict[str, Any]:
        """
        Inspect specified file or primary file in dataset folder.
        Generates comprehensive inspection report.
        """
        catalog_meta = EXTERNAL_DATASET_CATALOG.get(dataset_id, {})
        files = self.find_dataset_files(dataset_id, is_processed=is_processed)

        if not files:
            raise FileNotFoundError(f"No valid data files found in {'processed' if is_processed else 'external'} directory for '{dataset_id}'.")

        target_file = None
        if filename:
            for f in files:
                if f.name == filename:
                    target_file = f
                    break
        if not target_file:
            target_file = files[0]

        file_size_bytes = target_file.stat().st_size
        file_size_mb = round(file_size_bytes / (1024 * 1024), 2)

        # Load dataframe (handles csv and parquet)
        if target_file.suffix.lower() == ".parquet":
            df = pd.read_parquet(target_file)
        else:
            # Handle UTF-8 with BOM or standard
            df = pd.read_csv(target_file, nrows=sample_limit, low_memory=False)

        # Remove leading BOM from column names if present
        df.columns = [c.lstrip("\ufeff").strip() for c in df.columns]

        total_rows = len(df)
        total_cols = len(df.columns)
        total_cells = total_rows * total_cols

        # Missing values & duplicate analysis
        missing_per_col = df.isnull().sum().to_dict()
        total_missing = int(sum(missing_per_col.values()))
        missing_pct = round((total_missing / max(1, total_cells)) * 100.0, 2)
        duplicate_count = int(df.duplicated().sum())

        # Column schema analysis
        columns_detail = []
        for col in df.columns:
            s = df[col]
            dtype_str = str(s.dtype)
            num_missing = int(missing_per_col[col])
            col_missing_pct = round((num_missing / max(1, total_rows)) * 100.0, 2)
            n_unique = int(s.nunique())
            
            # Category inference
            col_type = "numeric"
            if pd.api.types.is_numeric_dtype(s):
                col_type = "numeric"
            elif pd.api.types.is_datetime64_any_dtype(s) or any(t in col.lower() for t in ["time", "date"]):
                col_type = "datetime"
            elif n_unique < 20 or pd.api.types.is_string_dtype(s) or pd.api.types.is_object_dtype(s):
                col_type = "categorical"

            # Sample values
            sample_vals = [str(x) for x in s.dropna().iloc[:3].tolist()]

            columns_detail.append({
                "column_name": col,
                "data_type": dtype_str,
                "inferred_type": col_type,
                "non_null_count": int(s.count()),
                "missing_count": num_missing,
                "missing_percentage": col_missing_pct,
                "unique_values_count": n_unique,
                "sample_values": sample_vals
            })

        # Target label discovery and class distribution
        target_candidates = ["label", "type", "attack", "condition_label", "Attack_label", "Attack_type", "Normal/Attack", "class"]
        found_target_col = None
        for cand in target_candidates:
            matches = [c for c in df.columns if c.lower() == cand.lower()]
            if matches:
                found_target_col = matches[0]
                break

        class_distribution = {}
        target_name = found_target_col or (df.columns[-1] if total_cols > 0 else "unknown")
        if target_name in df.columns:
            counts = df[target_name].value_counts(dropna=False).to_dict()
            class_distribution = {
                str(k): {
                    "count": int(v),
                    "percentage": round((int(v) / max(1, total_rows)) * 100.0, 2)
                }
                for k, v in counts.items()
            }

        # Sampling frequency / interval estimation
        sampling_frequency = "Unknown / Irregular"
        time_cols = [c for c in df.columns if any(term in c.lower() for term in ["time", "timestamp", "date"])]
        if time_cols:
            try:
                # Try parsing first time column
                sample_t = pd.to_datetime(df[time_cols[0]].dropna().iloc[:1000], errors="coerce")
                valid_t = sample_t.dropna().sort_values()
                if len(valid_t) > 10:
                    diffs = valid_t.diff().dropna().dt.total_seconds()
                    median_diff = diffs.median()
                    if median_diff > 0:
                        sampling_frequency = f"~{median_diff:.2f} seconds ({1.0/median_diff:.2f} Hz)"
            except Exception:
                pass

        # Inferred sensor units from catalog
        known_units = catalog_meta.get("sensor_units", {})
        sensor_units = {}
        for col in df.columns:
            for k, u in known_units.items():
                if k.lower() in col.lower():
                    sensor_units[col] = u

        # Generate summary description
        return {
            "dataset_id": dataset_id,
            "dataset_name": catalog_meta.get("name", dataset_id),
            "provenance": catalog_meta.get("provenance", "PUBLIC_DATASET"),
            "category": catalog_meta.get("category", "Public IoT Dataset"),
            "license": catalog_meta.get("license", "Open / Research Use"),
            "official_url": catalog_meta.get("official_url"),
            "filename": target_file.name,
            "file_path": str(target_file),
            "file_size_bytes": file_size_bytes,
            "file_size_mb": file_size_mb,
            "is_processed_copy": is_processed,
            "total_records": total_rows,
            "total_columns": total_cols,
            "total_missing_cells": total_missing,
            "missing_percentage": missing_pct,
            "duplicate_records": duplicate_count,
            "columns": columns_detail,
            "target_column": target_name,
            "class_distribution": class_distribution,
            "sampling_frequency": sampling_frequency,
            "sensor_units": sensor_units,
            "priority_telemetry": catalog_meta.get("priority_telemetry", []),
            "suitability_note": catalog_meta.get("suitability", "General ML evaluation.")
        }

    def preview_data(
        self,
        dataset_id: str,
        filename: Optional[str] = None,
        is_processed: bool = False,
        limit: int = 25
    ) -> Dict[str, Any]:
        """Return top N records as JSON dictionary for dashboard preview."""
        files = self.find_dataset_files(dataset_id, is_processed=is_processed)
        if not files:
            return {"columns": [], "records": [], "total_records": 0}

        target_file = files[0]
        if filename:
            for f in files:
                if f.name == filename:
                    target_file = f
                    break

        if target_file.suffix.lower() == ".parquet":
            df = pd.read_parquet(target_file)
        else:
            df = pd.read_csv(target_file, nrows=limit, low_memory=False)

        df.columns = [c.lstrip("\ufeff").strip() for c in df.columns]
        
        # Replace NaN / inf with None for valid JSON serialization
        clean_df = df.replace([np.inf, -np.inf], None).fillna("")
        
        return {
            "dataset_id": dataset_id,
            "filename": target_file.name,
            "columns": list(df.columns),
            "records": clean_df.to_dict(orient="records"),
            "preview_limit": limit
        }

dataset_inspector = ExternalDatasetInspector()
