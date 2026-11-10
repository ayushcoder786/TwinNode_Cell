"""
TwinNode Feature Engineering Module
Transforms raw sensor telemetry into high-value ML features.
Adheres strictly to Scikit-learn transformer interface to eliminate data leakage.
"""

from typing import List, Optional, Union
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

# Default canonical feature names used across ML models
CANONICAL_FEATURES = [
    "rolling_temp_mean",
    "rolling_temp_std",
    "temp_rate_of_change",
    "rolling_dist_mean",
    "dist_rate_of_change",
    "target_temp_dev",
    "target_dist_dev",
    "latency_mean",
    "packet_loss_rate",
    "sensor_stability_score",
    "response_delay",
    "led_mismatch"
]

class TwinNodeFeatureEngineer(BaseEstimator, TransformerMixin):
    """
    Scikit-learn compatible transformer for TwinNode sensor features.
    Computes rolling statistics, dynamic rate-of-change, target deviations,
    stability scores, and communication performance indicators.
    """

    def __init__(
        self,
        rolling_window: int = 5,
        feature_names: Optional[List[str]] = None
    ):
        self.rolling_window = rolling_window
        self.feature_names = feature_names or CANONICAL_FEATURES
        self.fitted_means_ = {}
        self.fitted_stds_ = {}

    def fit(self, X: Union[pd.DataFrame, np.ndarray], y=None):
        """Fit baseline statistics on training data only to avoid leakage."""
        df = self._ensure_dataframe(X)
        transformed = self._compute_features(df)
        
        # Learn reference statistics for fallback imputation
        for col in self.feature_names:
            if col in transformed.columns:
                self.fitted_means_[col] = float(transformed[col].mean()) if not pd.isna(transformed[col].mean()) else 0.0
                self.fitted_stds_[col] = float(transformed[col].std()) if not pd.isna(transformed[col].std()) else 1.0
            else:
                self.fitted_means_[col] = 0.0
                self.fitted_stds_[col] = 1.0
        return self

    def transform(self, X: Union[pd.DataFrame, np.ndarray]) -> pd.DataFrame:
        """Apply feature extraction and return DataFrame with canonical features."""
        df = self._ensure_dataframe(X)
        transformed = self._compute_features(df)

        # Impute any leading NaNs from rolling windows using fitted training means
        for col in self.feature_names:
            if col not in transformed.columns:
                transformed[col] = self.fitted_means_.get(col, 0.0)
            else:
                fallback_val = self.fitted_means_.get(col, 0.0)
                transformed[col] = transformed[col].fillna(fallback_val).replace([np.inf, -np.inf], fallback_val)

        return transformed[self.feature_names]

    def _ensure_dataframe(self, X: Union[pd.DataFrame, np.ndarray]) -> pd.DataFrame:
        if isinstance(X, pd.DataFrame):
            return X.copy()
        elif isinstance(X, np.ndarray):
            cols = [
                "temperature", "distance", "target_temperature", "target_distance",
                "uart_latency_ms", "packet_loss", "response_delay_ms",
                "led_command", "led_acknowledgement"
            ][:X.shape[1]]
            return pd.DataFrame(X, columns=cols)
        else:
            return pd.DataFrame(X)

    def _compute_features(self, df: pd.DataFrame) -> pd.DataFrame:
        out = pd.DataFrame(index=df.index)

        # 1. Temperature Features
        temp = df["temperature"] if "temperature" in df.columns else pd.Series(25.0, index=df.index)
        t_target = df["target_temperature"] if "target_temperature" in df.columns else temp

        out["rolling_temp_mean"] = temp.rolling(window=self.rolling_window, min_periods=1).mean()
        out["rolling_temp_std"] = temp.rolling(window=self.rolling_window, min_periods=1).std().fillna(0.0)
        
        # Temp rate of change (delta per sample or step)
        out["temp_rate_of_change"] = temp.diff().fillna(0.0)
        out["target_temp_dev"] = (temp - t_target).abs()

        # 2. Distance Features
        dist = df["distance"] if "distance" in df.columns else pd.Series(50.0, index=df.index)
        d_target = df["target_distance"] if "target_distance" in df.columns else dist

        out["rolling_dist_mean"] = dist.rolling(window=self.rolling_window, min_periods=1).mean()
        out["dist_rate_of_change"] = dist.diff().fillna(0.0)
        out["target_dist_dev"] = (dist - d_target).abs()

        # 3. Communication & Timing Features
        latency = df["uart_latency_ms"] if "uart_latency_ms" in df.columns else pd.Series(5.0, index=df.index)
        out["latency_mean"] = latency.rolling(window=self.rolling_window, min_periods=1).mean()

        pkt_loss = df["packet_loss"] if "packet_loss" in df.columns else pd.Series(0.0, index=df.index)
        out["packet_loss_rate"] = pkt_loss.rolling(window=self.rolling_window, min_periods=1).mean()

        resp_delay = df["response_delay_ms"] if "response_delay_ms" in df.columns else pd.Series(10.0, index=df.index)
        out["response_delay"] = resp_delay

        # 4. Sensor Stability Score (0.0 to 100.0)
        # Higher score = stable readings; penalty for high std, spike rates, and target dev
        t_penalty = out["rolling_temp_std"] * 5.0 + out["temp_rate_of_change"].abs() * 8.0
        d_penalty = out["dist_rate_of_change"].abs() * 0.5
        total_penalty = np.clip(t_penalty + d_penalty, 0.0, 100.0)
        out["sensor_stability_score"] = 100.0 - total_penalty

        # 5. LED Actuator Software Command Mismatch (OPEN-LOOP)
        # Note: Measures discrepancy between software command and UART protocol ACK.
        # Node 2 lacks physical optical feedback sensors or current-sensing shunts.
        if "led_command" in df.columns and "led_acknowledgement" in df.columns:
            cmd = df["led_command"].astype(str)
            ack = df["led_acknowledgement"].astype(str)
            mismatch = (
                ((cmd != "ALL_OFF") & (ack.str.contains("NO_ACK|TIMEOUT|ERROR|FAIL", case=False))) |
                ((cmd == "ALL_OFF") & (ack.str.contains("FAULT", case=False)))
            ).astype(int)
            out["led_mismatch"] = mismatch
        else:
            out["led_mismatch"] = 0

        return out
