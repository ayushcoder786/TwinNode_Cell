"""
TwinNode External Dataset Preprocessor
Applies dataset-specific transformations, missing-value imputation,
outlier detection, categorical encoding, feature scaling, and feature engineering.
Strictly preserves raw downloaded files unchanged and writes processed copies separately.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler, LabelEncoder

BASE_DIR = Path(__file__).resolve().parent.parent.parent
EXTERNAL_ROOT = BASE_DIR / "datasets" / "external"
PROCESSED_ROOT = BASE_DIR / "datasets" / "processed"

class ExternalDatasetPreprocessor:
    """Preprocesses external public datasets into ML-ready formats."""

    def preprocess_dataset(
        self,
        dataset_id: str,
        filename: Optional[str] = None,
        impute_strategy: str = "median",
        scaler_type: str = "standard",
        drop_duplicates: bool = True,
        remove_outliers: bool = False,
        outlier_threshold: float = 3.0,
        target_column: Optional[str] = None,
        selected_features: Optional[List[str]] = None,
        output_format: str = "csv"
    ) -> Dict[str, Any]:
        """
        Loads raw downloaded file, performs preprocessing, and writes processed output
        into backend/datasets/processed/{dataset_id}/.
        """
        dataset_dir = EXTERNAL_ROOT / dataset_id
        if not dataset_dir.exists():
            raise FileNotFoundError(f"Raw dataset directory not found: {dataset_dir}")

        raw_files = [f for f in dataset_dir.glob("*") if f.is_file() and f.suffix.lower() in [".csv", ".parquet"]]
        if not raw_files:
            raise FileNotFoundError(f"No CSV or Parquet files in {dataset_dir}")

        target_file = raw_files[0]
        if filename:
            for f in raw_files:
                if f.name == filename:
                    target_file = f
                    break

        # 1. Load Data
        if target_file.suffix.lower() == ".parquet":
            df = pd.read_parquet(target_file)
        else:
            df = pd.read_csv(target_file, low_memory=False)

        # Strip whitespace and BOM from headers
        df.columns = [c.lstrip("\ufeff").strip() for c in df.columns]
        initial_len = len(df)

        # 2. Duplicate Detection & Handling
        dup_count = 0
        if drop_duplicates:
            dup_mask = df.duplicated()
            dup_count = int(dup_mask.sum())
            df = df[~dup_mask].copy()

        # 3. Target Label Resolution
        target_col = target_column
        if not target_col or target_col not in df.columns:
            candidates = ["label", "type", "attack", "condition_label", "Attack_label", "Attack_type", "Normal/Attack", "class"]
            for cand in candidates:
                matches = [c for c in df.columns if c.lower() == cand.lower()]
                if matches:
                    target_col = matches[0]
                    break
        if not target_col or target_col not in df.columns:
            target_col = df.columns[-1]

        # Separate targets before feature scaling
        y_series = df[target_col].copy()
        
        # 4. Feature Selection
        # Exclude metadata/identifiers/timestamps from numeric feature scaling
        exclude_cols = [target_col] + [
            c for c in df.columns if any(term in c.lower() for term in ["time", "date", "id", "ip", "src", "dst", "timestamp"])
        ]
        
        feature_cols = selected_features or [c for c in df.columns if c not in exclude_cols]
        X_df = df[feature_cols].copy()

        # 5. Missing Value Analysis & Imputation
        missing_summary = X_df.isnull().sum().to_dict()
        numeric_cols = X_df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = X_df.select_dtypes(include=["object", "category", "string", "str"]).columns.tolist()

        for c in numeric_cols:
            if impute_strategy == "mean":
                fill_val = X_df[c].mean()
            else:
                fill_val = X_df[c].median()
            X_df[c] = X_df[c].fillna(fill_val if not pd.isna(fill_val) else 0.0)

        for c in categorical_cols:
            mode_val = X_df[c].mode()[0] if len(X_df[c].mode()) > 0 else "UNKNOWN"
            X_df[c] = X_df[c].fillna(mode_val)

        # 6. Categorical Encoding
        encoding_maps = {}
        for c in categorical_cols:
            le = LabelEncoder()
            X_df[c] = le.fit_transform(X_df[c].astype(str))
            encoding_maps[c] = {str(cls_): int(idx) for idx, cls_ in enumerate(le.classes_)}

        # 7. Outlier Detection (Z-score)
        outlier_count = 0
        if remove_outliers and numeric_cols:
            z_scores = np.abs((X_df[numeric_cols] - X_df[numeric_cols].mean()) / (X_df[numeric_cols].std().replace(0, 1)))
            outlier_mask = (z_scores > outlier_threshold).any(axis=1)
            # Never remove rows if they are labeled as anomaly/attack to preserve legitimate fault records!
            is_nominal = y_series.astype(str).str.contains("0|normal|benign", case=False, regex=True)
            # Only remove outliers in nominal data
            removable_mask = outlier_mask & is_nominal
            outlier_count = int(removable_mask.sum())
            X_df = X_df[~removable_mask].copy()
            y_series = y_series[~removable_mask].copy()

        # 8. Feature Scaling
        if scaler_type == "minmax":
            scaler = MinMaxScaler()
        elif scaler_type == "robust":
            scaler = RobustScaler()
        else:
            scaler = StandardScaler()

        X_scaled_values = scaler.fit_transform(X_df)
        processed_features = pd.DataFrame(X_scaled_values, columns=X_df.columns, index=X_df.index)

        # 9. Feature Engineering (Domain specific IoT rates of change)
        temp_cols = [c for c in processed_features.columns if "temp" in c.lower()]
        if temp_cols:
            t_col = temp_cols[0]
            processed_features[f"{t_col}_rate"] = processed_features[t_col].diff().fillna(0.0)

        # 10. Re-assemble Processed Dataset
        processed_df = processed_features.copy()
        processed_df[target_col] = y_series
        processed_df["data_provenance"] = "PUBLIC_DATASET"

        # 11. Save to Processed Directory (Preserves Raw Data Unchanged)
        dest_dir = PROCESSED_ROOT / dataset_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        base_name = target_file.stem
        out_filename = f"{base_name}_processed.{output_format}"
        out_path = dest_dir / out_filename

        if output_format == "parquet":
            processed_df.to_parquet(out_path, index=False)
        else:
            processed_df.to_csv(out_path, index=False)

        # Save preprocessing recipe metadata
        meta_payload = {
            "dataset_id": dataset_id,
            "raw_file": target_file.name,
            "processed_file": out_filename,
            "initial_records": initial_len,
            "final_records": len(processed_df),
            "duplicates_removed": dup_count,
            "outliers_removed": outlier_count,
            "impute_strategy": impute_strategy,
            "scaler_type": scaler_type,
            "features_processed": list(X_df.columns),
            "target_column": target_col,
            "encoding_maps": encoding_maps,
            "class_distribution": processed_df[target_col].value_counts().to_dict(),
            "provenance": "PUBLIC_DATASET"
        }
        meta_path = dest_dir / f"{base_name}_meta.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta_payload, f, indent=2)

        return {
            "status": "COMPLETED",
            "dataset_id": dataset_id,
            "raw_filename": target_file.name,
            "processed_filename": out_filename,
            "processed_path": str(out_path),
            "initial_rows": initial_len,
            "final_rows": len(processed_df),
            "duplicates_removed": dup_count,
            "outliers_removed": outlier_count,
            "missing_summary": missing_summary,
            "scaler_type": scaler_type,
            "features": list(X_df.columns),
            "target_column": target_col,
            "class_distribution": meta_payload["class_distribution"],
            "provenance": "PUBLIC_DATASET"
        }

dataset_preprocessor = ExternalDatasetPreprocessor()
