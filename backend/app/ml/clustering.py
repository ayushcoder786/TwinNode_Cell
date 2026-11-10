"""
TwinNode Unsupervised Clustering & Dimensionality Reduction
Implements K-Means clustering and PCA for unsupervised grouping and 2D visualization.
"""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score

from backend.app.data.feature_engineering import TwinNodeFeatureEngineer, CANONICAL_FEATURES

class TwinNodeClusteringAnalyzer:
    """Executes K-Means clustering and PCA projection on sensor records."""

    def __init__(self, n_clusters: int = 4, n_pca_components: int = 2):
        self.n_clusters = n_clusters
        self.n_pca_components = n_pca_components
        self.fe = TwinNodeFeatureEngineer()
        self.scaler = StandardScaler()
        self.kmeans: Optional[KMeans] = None
        self.pca: Optional[PCA] = None

    def fit_and_analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Transforms features, fits K-Means, applies PCA projection, and returns visualization payloads.
        """
        if len(df) < self.n_clusters:
            return {"error": "Not enough samples for clustering"}

        # 1. Feature Engineering & Scaling
        X_feats = self.fe.fit_transform(df)
        X_scaled = self.scaler.fit_transform(X_feats)

        # 2. K-Means Clustering
        self.kmeans = KMeans(n_clusters=self.n_clusters, random_state=42, n_init=10)
        cluster_labels = self.kmeans.fit_predict(X_scaled)
        
        sil_score = 0.0
        try:
            if len(df) <= 2000 and self.n_clusters > 1:
                sil_score = float(silhouette_score(X_scaled, cluster_labels))
        except Exception:
            pass

        # 3. PCA Dimensionality Reduction
        self.pca = PCA(n_components=self.n_pca_components)
        X_pca = self.pca.fit_transform(X_scaled)
        explained_var = [round(float(v), 4) for v in self.pca.explained_variance_ratio_]

        # 4. Assemble 2D Projection Points for React visualization (sample up to 500 for fast UI rendering)
        sample_size = min(500, len(df))
        indices = np.random.choice(len(df), sample_size, replace=False) if len(df) > sample_size else range(len(df))

        points = []
        for i in indices:
            pt = {
                "pc1": round(float(X_pca[i, 0]), 3),
                "pc2": round(float(X_pca[i, 1]), 3),
                "cluster": int(cluster_labels[i]),
                "temp": float(df.iloc[i].get("temperature", 0.0)),
                "dist": float(df.iloc[i].get("distance", 0.0)),
                "condition": str(df.iloc[i].get("condition_label", "UNKNOWN")),
                "data_source": str(df.iloc[i].get("data_source", "SIMULATION"))
            }
            points.append(pt)

        # Cluster breakdown
        cluster_counts = pd.Series(cluster_labels).value_counts().to_dict()
        cluster_summary = {
            f"Cluster_{k}": {
                "count": int(v),
                "percentage": round(float(v / len(df)) * 100.0, 1)
            }
            for k, v in cluster_counts.items()
        }

        return {
            "n_clusters": self.n_clusters,
            "inertia": round(float(self.kmeans.inertia_), 2),
            "silhouette_score": round(sil_score, 4),
            "explained_variance_ratio": explained_var,
            "total_variance_explained": round(sum(explained_var) * 100.0, 2),
            "cluster_summary": cluster_summary,
            "pca_projection_points": points
        }
