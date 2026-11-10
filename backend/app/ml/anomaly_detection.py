"""
TwinNode Unsupervised Anomaly Detection Module
Uses Isolation Forest to detect anomalous sensor drift, erratic communications,
and unexpected operating dynamics without requiring pre-assigned failure labels.
"""

from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from backend.app.data.feature_engineering import TwinNodeFeatureEngineer, CANONICAL_FEATURES

class TwinNodeAnomalyDetector:
    """Isolation Forest pipeline for unsupervised anomaly identification."""

    def __init__(
        self,
        contamination: float = 0.08,
        n_estimators: int = 100,
        random_state: int = 42
    ):
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.random_state = random_state
        self.pipeline: Optional[Pipeline] = None
        self.threshold: float = 0.65

    def fit(self, X: pd.DataFrame):
        """Fit Isolation Forest pipeline on feature-engineered sensor telemetry."""
        self.pipeline = Pipeline([
            ("feature_engineer", TwinNodeFeatureEngineer()),
            ("scaler", StandardScaler()),
            ("isolation_forest", IsolationForest(
                n_estimators=self.n_estimators,
                contamination=self.contamination,
                random_state=self.random_state,
                n_jobs=-1
            ))
        ])
        self.pipeline.fit(X)
        return self

    def score_samples(self, X: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculates anomaly scores.
        Returns (is_anomaly_bool_array, normalized_anomaly_score_0_to_1).
        """
        if self.pipeline is None:
            raise ValueError("Anomaly detector has not been fitted.")

        iso_forest: IsolationForest = self.pipeline.named_steps["isolation_forest"]
        X_feats = self.pipeline.named_steps["feature_engineer"].transform(X)
        X_scaled = self.pipeline.named_steps["scaler"].transform(X_feats)

        # score_samples returns opposite of anomaly score (lower is more anomalous)
        raw_scores = iso_forest.score_samples(X_scaled)
        
        # Normalize into 0.0 (normal) to 1.0 (severely anomalous)
        # raw_scores typically range from -0.8 to -0.3
        norm_scores = np.clip(1.0 - (raw_scores + 0.8) / 0.6, 0.0, 1.0)
        predictions = iso_forest.predict(X_scaled) # -1 is anomaly, 1 is normal
        is_anomaly = predictions == -1

        return is_anomaly, norm_scores
