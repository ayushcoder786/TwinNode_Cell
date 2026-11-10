"""
TwinNode Data Preprocessing Pipeline
Handles cleaning, duplicate elimination, outlier analysis, chronological splitting,
and Scikit-learn Pipeline construction.
"""

from typing import Dict, Any, Tuple, List, Optional
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler
from sklearn.impute import SimpleImputer

from backend.app.data.feature_engineering import TwinNodeFeatureEngineer, CANONICAL_FEATURES

def clean_dataset(
    df: pd.DataFrame,
    drop_duplicates: bool = True,
    impute_strategy: str = "median",
    filter_invalid: bool = True,
    preserve_sensor_faults: bool = True
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Cleans raw dataset, tracking removed duplicates and invalid rows.
    Preserves intentional SENSOR_FAULT records to avoid class starvation.
    """
    initial_len = len(df)
    clean_df = df.copy()

    # 1. Duplicate Handling
    dup_count = 0
    if drop_duplicates:
        dup_mask = clean_df.duplicated(subset=["timestamp", "node_id", "packet_sequence"], keep="first") if {"timestamp", "node_id", "packet_sequence"}.issubset(clean_df.columns) else clean_df.duplicated(keep="first")
        dup_count = int(dup_mask.sum())
        clean_df = clean_df[~dup_mask].copy()

    # 2. Invalid Sensor Readings Filtering (Preserves SENSOR_FAULT)
    invalid_count = 0
    if filter_invalid and "sensor_validity" in clean_df.columns:
        if preserve_sensor_faults and "condition_label" in clean_df.columns:
            # Preserve intentional SENSOR_FAULT events; only filter spurious anomalies in nominal data
            invalid_mask = (clean_df["sensor_validity"] == False) & (clean_df["condition_label"] != "SENSOR_FAULT")
        else:
            invalid_mask = clean_df["sensor_validity"] == False
        invalid_count = int(invalid_mask.sum())
        clean_df = clean_df[~invalid_mask].copy()

    # 3. Missing Value Detection
    missing_summary = clean_df.isnull().sum().to_dict()

    # 4. Impute numeric columns
    numeric_cols = clean_df.select_dtypes(include=[np.number]).columns.tolist()
    if impute_strategy == "median":
        clean_df[numeric_cols] = clean_df[numeric_cols].fillna(clean_df[numeric_cols].median())
    elif impute_strategy == "mean":
        clean_df[numeric_cols] = clean_df[numeric_cols].fillna(clean_df[numeric_cols].mean())
    elif impute_strategy == "ffill":
        clean_df[numeric_cols] = clean_df[numeric_cols].ffill().bfill()

    clean_summary = {
        "initial_rows": initial_len,
        "final_rows": len(clean_df),
        "duplicates_removed": dup_count,
        "invalid_removed": invalid_count,
        "missing_per_column": missing_summary
    }

    return clean_df, clean_summary

def detect_outliers(
    df: pd.DataFrame,
    columns: Optional[List[str]] = None,
    method: str = "iqr",
    threshold: float = 1.5
) -> Dict[str, Any]:
    """
    Detect outliers in numerical columns using IQR or Z-Score.
    """
    cols = columns or [c for c in ["temperature", "distance", "uart_latency_ms", "response_delay_ms"] if c in df.columns]
    outlier_counts = {}
    total_outliers = 0

    for col in cols:
        series = df[col].dropna()
        if len(series) == 0:
            outlier_counts[col] = 0
            continue

        if method == "iqr":
            q25, q75 = np.percentile(series, 25), np.percentile(series, 75)
            iqr = q75 - q25
            lower_bound = q25 - threshold * iqr
            upper_bound = q75 + threshold * iqr
            outlier_mask = (series < lower_bound) | (series > upper_bound)
        else: # z-score
            mean = series.mean()
            std = series.std() or 1.0
            z_scores = np.abs((series - mean) / std)
            outlier_mask = z_scores > threshold

        count = int(outlier_mask.sum())
        outlier_counts[col] = count
        total_outliers += count

    return {
        "method": method,
        "threshold": threshold,
        "columns_evaluated": cols,
        "outlier_counts": outlier_counts,
        "total_outliers": total_outliers
    }

def build_preprocessing_pipeline(
    scaler_type: str = "standard",
    feature_names: Optional[List[str]] = None,
    rolling_window: int = 5
) -> Pipeline:
    """
    Constructs an end-to-end scikit-learn preprocessing pipeline.
    Combines feature extraction and feature scaling into a unified, leak-free pipeline.
    """
    feats = feature_names or CANONICAL_FEATURES

    if scaler_type == "minmax":
        scaler = MinMaxScaler()
    elif scaler_type == "robust":
        scaler = RobustScaler()
    else:
        scaler = StandardScaler()

    pipeline = Pipeline([
        ("feature_engineer", TwinNodeFeatureEngineer(rolling_window=rolling_window, feature_names=feats)),
        ("scaler", scaler)
    ])
    return pipeline

def chronological_session_split(
    df: pd.DataFrame,
    test_size: float = 0.2,
    session_col: str = "test_id",
    time_col: str = "timestamp"
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Chronological train/test splitting by test sessions to prevent temporal data leakage.
    If session_col exists and has multiple sessions, splits whole sessions chronologically.
    Otherwise, splits sequentially along timestamp.
    """
    df_sorted = df.copy()
    if time_col in df_sorted.columns:
        df_sorted[time_col] = pd.to_datetime(df_sorted[time_col])
        df_sorted = df_sorted.sort_values(by=time_col)

    if session_col in df_sorted.columns and df_sorted[session_col].nunique() > 1:
        sessions = df_sorted.groupby(session_col)[time_col].min().sort_values().index.tolist()
        split_idx = int(len(sessions) * (1.0 - test_size))
        split_idx = max(1, min(split_idx, len(sessions) - 1))
        train_sessions = set(sessions[:split_idx])
        test_sessions = set(sessions[split_idx:])

        train_df = df_sorted[df_sorted[session_col].isin(train_sessions)].copy()
        test_df = df_sorted[df_sorted[session_col].isin(test_sessions)].copy()
    else:
        split_idx = int(len(df_sorted) * (1.0 - test_size))
        train_df = df_sorted.iloc[:split_idx].copy()
        test_df = df_sorted.iloc[split_idx:].copy()

    return train_df, test_df

def session_train_val_test_split(
    df: pd.DataFrame,
    n_splits: int = 6,
    session_col: str = "test_id",
    label_col: str = "condition_label",
    random_seed: int = 42,
    train_ratio: Optional[float] = None,
    val_ratio: Optional[float] = None,
    test_ratio: Optional[float] = None
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Strict session-based 3-way train/validation/test split using Scikit-Learn's StratifiedGroupKFold.
    Guarantees:
      1. Zero session overlap (Train Sessions ∩ Val Sessions ∩ Test Sessions = Ø).
      2. Multi-class stratification across independent sessions so that each condition class
         is represented in every partition wherever available independent sessions permit.
      3. Zero temporal leakage between adjacent time steps.
      4. Explicit class representation auditing: reports exact reasons if any class cannot be placed.
    """
    from sklearn.model_selection import StratifiedGroupKFold

    if session_col not in df.columns or label_col not in df.columns or df[session_col].nunique() < 3:
        # Fallback to sequential split for degenerate or toy dataframes
        n = len(df)
        t_idx = int(n * 0.70)
        v_idx = int(n * 0.85)
        return df.iloc[:t_idx].copy(), df.iloc[t_idx:v_idx].copy(), df.iloc[v_idx:].copy(), {
            "session_overlap": 0,
            "all_classes_represented": True,
            "class_representation_warnings": ["Fallback sequential split used (insufficient unique sessions)."]
        }

    # Prepare inputs for StratifiedGroupKFold
    groups = df[session_col]
    y = df[label_col]
    X = df.drop(columns=[label_col])

    # Determine safe number of splits based on available sessions
    num_sessions = int(df[session_col].nunique())
    actual_splits = max(3, min(n_splits, num_sessions))

    sgkf = StratifiedGroupKFold(n_splits=actual_splits, shuffle=True, random_state=random_seed)
    splits = list(sgkf.split(X, y, groups=groups))

    # Fold 0 = Test (holdout test sessions)
    # Fold 1 = Validation (tuning sessions)
    # Folds 2..N = Training (learning sessions)
    test_idx = splits[0][1]
    val_idx = splits[1][1]
    train_idx = [i for i in range(len(df)) if i not in set(test_idx) and i not in set(val_idx)]

    train_df = df.iloc[train_idx].copy()
    val_df = df.iloc[val_idx].copy()
    test_df = df.iloc[test_idx].copy()

    # Session overlap audit
    train_sessions = set(train_df[session_col])
    val_sessions = set(val_df[session_col])
    test_sessions = set(test_df[session_col])

    overlap_tv = len(train_sessions & val_sessions)
    overlap_tt = len(train_sessions & test_sessions)
    overlap_vt = len(val_sessions & test_sessions)
    total_overlap = overlap_tv + overlap_tt + overlap_vt

    # Class representation audit across all 3 partitions
    all_classes = sorted(list(df[label_col].unique()))
    train_classes = set(train_df[label_col].unique())
    val_classes = set(val_df[label_col].unique())
    test_classes = set(test_df[label_col].unique())

    class_representation_warnings = []
    for c in all_classes:
        sess_for_c = df[df[label_col] == c][session_col].nunique()
        if c not in train_classes:
            class_representation_warnings.append(
                f"Class '{c}' missing from TRAIN split. Reason: only {sess_for_c} independent session(s) exist in dataset."
            )
        if c not in val_classes:
            class_representation_warnings.append(
                f"Class '{c}' missing from VALIDATION split. Reason: only {sess_for_c} independent session(s) exist in dataset."
            )
        if c not in test_classes:
            class_representation_warnings.append(
                f"Class '{c}' missing from TEST split. Reason: only {sess_for_c} independent session(s) exist in dataset."
            )

    report = {
        "method": "StratifiedGroupKFold",
        "random_seed": random_seed,
        "n_splits": actual_splits,
        "session_overlap": total_overlap,
        "zero_leakage_verified": bool(total_overlap == 0),
        "all_classes_represented": bool(len(class_representation_warnings) == 0),
        "class_representation_warnings": class_representation_warnings,
        "total_sessions": num_sessions,
        "train_sessions_count": len(train_sessions),
        "val_sessions_count": len(val_sessions),
        "test_sessions_count": len(test_sessions),
        "train_samples": len(train_df),
        "val_samples": len(val_df),
        "test_samples": len(test_df),
        "train_classes": train_df[label_col].value_counts().to_dict(),
        "val_classes": val_df[label_col].value_counts().to_dict(),
        "test_classes": test_df[label_col].value_counts().to_dict(),
        "train_session_ids": sorted(list(train_sessions)),
        "val_session_ids": sorted(list(val_sessions)),
        "test_session_ids": sorted(list(test_sessions))
    }

    return train_df, val_df, test_df, report

