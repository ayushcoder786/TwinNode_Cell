"""
TwinNode Exploratory Data Analysis (EDA) Engine
Computes comprehensive statistical summaries, correlation matrices,
frequency distributions, and data quality metrics.
"""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd

from backend.app.data.preprocessing import detect_outliers

class EDAAnalyzer:
    """Computes dataset statistical metrics and distribution profiles."""

    def analyze_dataframe(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate complete statistical overview of sensor dataset.
        """
        if df.empty:
            return {"error": "Dataset is empty", "total_samples": 0}

        total_samples = len(df)
        total_features = len(df.columns)
        
        # 1. Feature Types & Missing Data
        dtypes = {col: str(df[col].dtype) for col in df.columns}
        missing_counts = df.isnull().sum().to_dict()
        missing_pcts = {col: round(float(count / total_samples) * 100.0, 2) for col, count in missing_counts.items()}
        
        # 2. Duplicate Detection
        dup_count = int(df.duplicated().sum())

        # 3. Numeric Columns Summary
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        summary_stats = {}
        def safe_float(v, default=0.0):
            if v is None or pd.isna(v) or np.isneginf(v) or np.isposinf(v):
                return default
            return round(float(v), 3)

        for col in numeric_cols:
            series = df[col].dropna()
            if len(series) > 0:
                s_skew = series.skew() if len(series) > 2 else 0.0
                summary_stats[col] = {
                    "count": int(series.count()),
                    "mean": safe_float(series.mean()),
                    "std": safe_float(series.std()),
                    "min": safe_float(series.min()),
                    "p25": safe_float(np.percentile(series, 25)),
                    "median": safe_float(series.median()),
                    "p75": safe_float(np.percentile(series, 75)),
                    "max": safe_float(series.max()),
                    "skew": safe_float(s_skew, 0.0)
                }


        # 4. Correlation Matrix
        corr_matrix = {}
        target_corr_cols = [c for c in [
            "temperature", "distance", "target_temperature", "target_distance",
            "temperature_error", "distance_error", "uart_latency_ms", "packet_loss", "response_delay_ms"
        ] if c in df.columns]
        
        if len(target_corr_cols) > 1:
            corr_df = df[target_corr_cols].corr()
            corr_matrix = {
                "columns": target_corr_cols,
                "values": [[round(float(v), 3) if not np.isnan(v) else 0.0 for v in row] for row in corr_df.values]
            }

        # 5. Fault / Condition Class Distribution
        class_dist = {}
        if "condition_label" in df.columns:
            counts = df["condition_label"].value_counts()
            for label, count in counts.items():
                class_dist[str(label)] = {
                    "count": int(count),
                    "percentage": round(float(count / total_samples) * 100.0, 2)
                }

        # 6. Data Source Distribution
        data_source_dist = {}
        if "data_source" in df.columns:
            s_counts = df["data_source"].value_counts()
            for src, count in s_counts.items():
                data_source_dist[str(src)] = {
                    "count": int(count),
                    "percentage": round(float(count / total_samples) * 100.0, 2)
                }

        # 7. Distribution Histograms for Recharts UI
        histograms = {}
        for col in ["temperature", "distance", "uart_latency_ms"]:
            if col in df.columns:
                valid_data = df[col].dropna()
                if len(valid_data) > 0:
                    counts, bin_edges = np.histogram(valid_data, bins=15)
                    histograms[col] = [
                        {
                            "bin": f"{bin_edges[i]:.1f} - {bin_edges[i+1]:.1f}",
                            "count": int(counts[i]),
                            "mid": round(float((bin_edges[i] + bin_edges[i+1]) / 2.0), 2)
                        }
                        for i in range(len(counts))
                    ]

        # 8. Outlier Analysis
        outliers = detect_outliers(df, method="iqr", threshold=1.5)

        return {
            "total_samples": total_samples,
            "total_features": total_features,
            "duplicate_records": dup_count,
            "dtypes": dtypes,
            "missing_values": missing_counts,
            "missing_percentages": missing_pcts,
            "summary_statistics": summary_stats,
            "correlation_matrix": corr_matrix,
            "class_distribution": class_dist,
            "data_source_distribution": data_source_dist,
            "histograms": histograms,
            "outliers": outliers
        }

eda_analyzer = EDAAnalyzer()
