"""
TwinNode Data Quality & Integrity Engine
Performs comprehensive data quality audits without altering or deleting raw records.
Evaluates duplicates, missing values, sensor bounds, class balance, session continuity,
outliers, and provenance separation.
"""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd

from backend.app.data.validator import (
    LM35_MIN_TEMP_C, LM35_MAX_TEMP_C,
    HCSR04_MIN_DIST_CM, HCSR04_MAX_DIST_CM
)
from backend.app.data.preprocessing import detect_outliers

class DataQualityEngine:
    """Performs non-destructive quality audits across TwinNode datasets."""

    def analyze_dataset_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Run all 7 data quality checks across the provided DataFrame.
        Returns a comprehensive diagnostic report.
        """
        if df.empty:
            return {"error": "Dataset is empty", "total_records": 0}

        total_records = len(df)

        # 1. Duplicate Detection
        dup_exact = int(df.duplicated().sum())
        dup_subset_cols = [c for c in ["timestamp", "node_id", "packet_sequence", "test_id"] if c in df.columns]
        dup_semantic = int(df.duplicated(subset=dup_subset_cols).sum()) if len(dup_subset_cols) >= 2 else dup_exact
        flagged_duplicates = int(df["is_duplicate"].sum()) if "is_duplicate" in df.columns else 0

        duplicate_analysis = {
            "exact_row_duplicates": dup_exact,
            "semantic_key_duplicates": dup_semantic,
            "flagged_duplicate_records": flagged_duplicates,
            "duplicate_rate_pct": round((dup_semantic / total_records) * 100.0, 3)
        }

        # 2. Missing Value Analysis
        missing_counts = df.isnull().sum().to_dict()
        missing_pcts = {col: round(float(cnt / total_records) * 100.0, 2) for col, cnt in missing_counts.items()}
        total_missing_cells = sum(missing_counts.values())

        missing_value_analysis = {
            "total_missing_cells": total_missing_cells,
            "missing_cells_pct": round(float(total_missing_cells / (total_records * max(1, len(df.columns)))) * 100.0, 3),
            "missing_per_column": missing_counts,
            "missing_pct_per_column": missing_pcts
        }

        # 3. Invalid Sensor Reading Detection
        temp_bounds_violations = 0
        dist_bounds_violations = 0
        flagged_invalid_sensor = 0

        if "temperature" in df.columns:
            t = df["temperature"].dropna()
            temp_bounds_violations = int(((t < LM35_MIN_TEMP_C) | (t > LM35_MAX_TEMP_C)).sum())

        if "distance" in df.columns:
            d = df["distance"].dropna()
            dist_bounds_violations = int(((d < HCSR04_MIN_DIST_CM) | (d > HCSR04_MAX_DIST_CM)).sum())

        if "sensor_validity" in df.columns:
            flagged_invalid_sensor = int((df["sensor_validity"] == False).sum()) # noqa

        invalid_reading_analysis = {
            "temperature_bounds_limits": f"[{LM35_MIN_TEMP_C}°C, {LM35_MAX_TEMP_C}°C]",
            "temperature_violations": temp_bounds_violations,
            "distance_bounds_limits": f"[{HCSR04_MIN_DIST_CM}cm, {HCSR04_MAX_DIST_CM}cm]",
            "distance_violations": dist_bounds_violations,
            "flagged_sensor_invalid_rows": flagged_invalid_sensor,
            "sensor_fault_labeled_rows": int((df["condition_label"] == "SENSOR_FAULT").sum()) if "condition_label" in df.columns else 0
        }

        # 4. Class Distribution Analysis
        class_counts = {}
        imbalance_ratio = 1.0
        if "condition_label" in df.columns:
            c_series = df["condition_label"].value_counts()
            for label, count in c_series.items():
                class_counts[str(label)] = {
                    "count": int(count),
                    "percentage": round(float(count / total_records) * 100.0, 2)
                }
            if len(c_series) > 1 and c_series.min() > 0:
                imbalance_ratio = round(float(c_series.max() / c_series.min()), 2)

        class_distribution_analysis = {
            "total_classes": len(class_counts),
            "class_breakdown": class_counts,
            "imbalance_ratio_max_to_min": imbalance_ratio,
            "is_balanced": bool(imbalance_ratio <= 4.0)
        }

        # 5. Session-Level Data Validation
        session_col = "test_id" if "test_id" in df.columns else None
        session_analysis = {}
        if session_col:
            grouped = df.groupby(session_col)
            session_counts = grouped.size().to_dict()
            session_classes = grouped["condition_label"].agg(lambda x: x.mode()[0] if not x.empty else "UNKNOWN").to_dict() if "condition_label" in df.columns else {}

            session_lens = list(session_counts.values())
            session_analysis = {
                "total_sessions": len(session_counts),
                "min_session_samples": min(session_lens) if session_lens else 0,
                "max_session_samples": max(session_lens) if session_lens else 0,
                "avg_session_samples": round(float(np.mean(session_lens)), 1) if session_lens else 0,
                "session_ids": sorted(list(session_counts.keys())),
                "session_sample_counts": {str(k): int(v) for k, v in session_counts.items()},
                "session_dominant_classes": {str(k): str(v) for k, v in session_classes.items()}
            }

        # 6. Outlier Analysis
        outlier_analysis = detect_outliers(df, method="iqr", threshold=1.5)

        # 7. Data Provenance Validation
        provenance_analysis = {}
        if "data_source" in df.columns:
            p_counts = df["data_source"].value_counts().to_dict()
            real_count = int(p_counts.get("REAL_HARDWARE", 0))
            sim_count = int(p_counts.get("SIMULATION", 0))
            unidentified = int(total_records - real_count - sim_count)

            provenance_analysis = {
                "real_hardware_count": real_count,
                "real_hardware_pct": round(float(real_count / total_records) * 100.0, 3),
                "simulation_count": sim_count,
                "simulation_pct": round(float(sim_count / total_records) * 100.0, 3),
                "unidentified_source_count": unidentified,
                "strict_separation_verified": bool(unidentified == 0),
                "is_simulation_dominated": bool(sim_count > (real_count * 10))
            }

        return {
            "status": "COMPLETED",
            "total_records": total_records,
            "total_columns": len(df.columns),
            "duplicates": duplicate_analysis,
            "missing_values": missing_value_analysis,
            "invalid_sensor_readings": invalid_reading_analysis,
            "class_distribution": class_distribution_analysis,
            "session_validation": session_analysis,
            "outliers": outlier_analysis,
            "data_provenance": provenance_analysis
        }

data_quality_engine = DataQualityEngine()
