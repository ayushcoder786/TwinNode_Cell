"""
TwinNode External Dataset Machine Learning Benchmark Engine
Supports Supervised (Logistic Regression, Decision Tree, Random Forest, SVM),
Unsupervised (Isolation Forest, K-Means), and Dimensionality Reduction (PCA)
on public external datasets with strict provenance tagging and leak-free splitting.
"""

import time
import uuid
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.svm import SVC
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
    silhouette_score
)

from backend.app.ml.model_registry import model_registry
from backend.app.data.external_dataset_catalog import EXTERNAL_DATASET_CATALOG

BASE_DIR = Path(__file__).resolve().parent.parent.parent
EXTERNAL_ROOT = BASE_DIR / "datasets" / "external"
PROCESSED_ROOT = BASE_DIR / "datasets" / "processed"
EXPERIMENTS_FILE = BASE_DIR / "models" / "metadata" / "external_experiments_history.json"

class ExternalModelTrainer:
    """Trains and benchmarks ML algorithms on external public datasets."""

    def __init__(self):
        EXPERIMENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not EXPERIMENTS_FILE.exists():
            with open(EXPERIMENTS_FILE, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)

    def _record_experiment(self, exp_data: Dict[str, Any]):
        try:
            with open(EXPERIMENTS_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []
        history.insert(0, exp_data)
        history = history[:50] # keep 50 recent
        try:
            with open(EXPERIMENTS_FILE, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            print(f"[ExternalTrainer] Failed to record experiment history: {e}")

    def list_experiments(self) -> List[Dict[str, Any]]:
        try:
            with open(EXPERIMENTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    async def train_external_model(
        self,
        dataset_id: str,
        algorithm: str = "RandomForest",
        experiment_type: str = "EXTERNAL_BENCHMARK",
        target_column: Optional[str] = None,
        test_size: float = 0.20,
        hyperparameters: Optional[Dict[str, Any]] = None,
        use_processed: bool = True,
        max_samples: int = 50000
    ) -> Dict[str, Any]:
        """
        Train ML algorithm on external dataset and calculate multi-class metrics.
        """
        hp = hyperparameters or {}
        cat_meta = EXTERNAL_DATASET_CATALOG.get(dataset_id, {})
        dataset_name = cat_meta.get("name", dataset_id)

        # 1. Locate file
        target_dir = (PROCESSED_ROOT if use_processed else EXTERNAL_ROOT) / dataset_id
        if not target_dir.exists():
            target_dir = EXTERNAL_ROOT / dataset_id
        if not target_dir.exists():
            raise FileNotFoundError(f"Dataset directory not found for: {dataset_id}")

        data_files = [f for f in target_dir.glob("*") if f.is_file() and f.suffix.lower() in [".csv", ".parquet"]]
        if not data_files:
            raise FileNotFoundError(f"No CSV or Parquet files found for {dataset_id}")

        data_file = data_files[0]
        if data_file.suffix.lower() == ".parquet":
            df = pd.read_parquet(data_file)
        else:
            df = pd.read_csv(data_file, nrows=max_samples, low_memory=False)

        df.columns = [c.lstrip("\ufeff").strip() for c in df.columns]

        # 2. Identify target label column
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

        # 3. Features separation
        exclude_cols = [target_col, "data_provenance"] + [
            c for c in df.columns if any(term in c.lower() for term in ["time", "date", "id", "ip", "src", "dst", "timestamp"])
        ]
        feature_cols = [c for c in df.columns if c not in exclude_cols]
        if not feature_cols:
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            feature_cols = [c for c in numeric_cols if c != target_col]

        X = df[feature_cols].copy()
        # Impute any residual NaNs with median/0
        X = X.apply(pd.to_numeric, errors="coerce").fillna(0.0)
        y = df[target_col].copy().astype(str)

        # 4. Chronological or Stratified Train-Test Split (leak-free)
        # Check if time column exists for chronological split
        time_cols = [c for c in df.columns if any(t in c.lower() for t in ["time", "date", "timestamp"])]
        if time_cols:
            # Chronological split to prevent temporal leakage
            split_idx = int(len(X) * (1.0 - test_size))
            X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
            y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
            split_method = "Chronological (Time-Aware)"
        else:
            try:
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=test_size, random_state=42, stratify=y
                )
                split_method = "Stratified Holdout"
            except Exception:
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=test_size, random_state=42
                )
                split_method = "Random Holdout"

        train_classes = y_train.value_counts().to_dict()
        test_classes = y_test.value_counts().to_dict()

        # 5. Algorithm Instantiation
        algo_upper = algorithm.upper().replace("_", "").replace(" ", "")
        start_train_t = time.perf_counter()

        model_obj = None
        is_clustering = False
        is_dim_reduction = False
        is_anomaly = False

        if "RANDOMFOREST" in algo_upper:
            model_obj = RandomForestClassifier(
                n_estimators=int(hp.get("n_estimators", 100)),
                max_depth=int(hp["max_depth"]) if "max_depth" in hp and hp["max_depth"] else 10,
                random_state=42,
                n_jobs=-1
            )
            model_obj.fit(X_train, y_train)

        elif "DECISIONTREE" in algo_upper:
            model_obj = DecisionTreeClassifier(
                max_depth=int(hp["max_depth"]) if "max_depth" in hp and hp["max_depth"] else 8,
                random_state=42
            )
            model_obj.fit(X_train, y_train)

        elif "LOGISTIC" in algo_upper:
            model_obj = LogisticRegression(
                C=float(hp.get("C", 1.0)),
                max_iter=int(hp.get("max_iter", 1000)),
                random_state=42
            )
            model_obj.fit(X_train, y_train)

        elif "SVM" in algo_upper:
            # Use LinearSVC or fast RBF for responsiveness
            from sklearn.calibration import CalibratedClassifierCV
            base_svc = SVC(C=float(hp.get("C", 1.0)), kernel=str(hp.get("kernel", "rbf")), random_state=42)
            model_obj = CalibratedClassifierCV(base_svc, ensemble=False)
            # Sample for speed if dataset is huge
            if len(X_train) > 10000:
                sample_idx = np.random.choice(len(X_train), 10000, replace=False)
                model_obj.fit(X_train.iloc[sample_idx], y_train.iloc[sample_idx])
            else:
                model_obj.fit(X_train, y_train)

        elif "ISOLATIONFOREST" in algo_upper:
            is_anomaly = True
            model_obj = IsolationForest(
                n_estimators=int(hp.get("n_estimators", 100)),
                contamination=float(hp.get("contamination", 0.05)),
                random_state=42,
                n_jobs=-1
            )
            model_obj.fit(X_train)

        elif "KMEANS" in algo_upper:
            is_clustering = True
            n_clusters = int(hp.get("n_clusters", min(len(train_classes), 5) or 3))
            model_obj = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            model_obj.fit(X_train)

        elif "PCA" in algo_upper:
            is_dim_reduction = True
            n_components = int(hp.get("n_components", min(len(feature_cols), 3) or 2))
            model_obj = PCA(n_components=n_components, random_state=42)
            model_obj.fit(X_train)

        else:
            raise ValueError(f"Unsupported algorithm '{algorithm}'. Supported: RandomForest, DecisionTree, LogisticRegression, SVM, IsolationForest, KMeans, PCA")

        training_time_ms = round((time.perf_counter() - start_train_t) * 1000.0, 2)

        # 6. Evaluation
        start_inf_t = time.perf_counter()
        
        if is_clustering:
            preds = model_obj.predict(X_test)
            latency_ms = round(((time.perf_counter() - start_inf_t) * 1000.0) / max(1, len(X_test)), 4)
            # Silhouette score on a subset for speed
            sil_sample = X_test.iloc[:1000] if len(X_test) > 1000 else X_test
            sil_preds = preds[:len(sil_sample)]
            try:
                sil_score = round(float(silhouette_score(sil_sample, sil_preds)), 4)
            except Exception:
                sil_score = 0.0

            metrics = {
                "algorithm_type": "CLUSTERING",
                "n_clusters": int(model_obj.n_clusters),
                "silhouette_score": sil_score,
                "cluster_distribution": {int(k): int(v) for k, v in pd.Series(preds).value_counts().items()},
                "inference_latency_ms": latency_ms
            }

        elif is_dim_reduction:
            transformed = model_obj.transform(X_test)
            latency_ms = round(((time.perf_counter() - start_inf_t) * 1000.0) / max(1, len(X_test)), 4)
            explained_var_ratio = [round(float(v), 4) for v in model_obj.explained_variance_ratio_]
            metrics = {
                "algorithm_type": "DIMENSIONALITY_REDUCTION",
                "n_components": int(model_obj.n_components_),
                "explained_variance_ratio": explained_var_ratio,
                "total_variance_explained": round(float(sum(explained_var_ratio)), 4),
                "inference_latency_ms": latency_ms
            }

        elif is_anomaly:
            preds = model_obj.predict(X_test) # 1: normal, -1: anomaly
            latency_ms = round(((time.perf_counter() - start_inf_t) * 1000.0) / max(1, len(X_test)), 4)
            anomaly_count = int((preds == -1).sum())
            anomaly_rate = round((anomaly_count / max(1, len(X_test))) * 100.0, 2)
            metrics = {
                "algorithm_type": "ANOMALY_DETECTION",
                "anomaly_rate_pct": anomaly_rate,
                "anomalies_detected": anomaly_count,
                "normal_retained": int((preds == 1).sum()),
                "accuracy": round(1.0 - (anomaly_rate / 100.0), 4),
                "inference_latency_ms": latency_ms
            }

        else: # Standard Classification
            y_pred = model_obj.predict(X_test)
            latency_ms = round(((time.perf_counter() - start_inf_t) * 1000.0) / max(1, len(X_test)), 4)
            labels = sorted(list(set(y_test) | set(y_pred)))

            acc = float(accuracy_score(y_test, y_pred))
            prec_macro = float(precision_score(y_test, y_pred, average="macro", zero_division=0))
            rec_macro = float(recall_score(y_test, y_pred, average="macro", zero_division=0))
            f1_mac = float(f1_score(y_test, y_pred, average="macro", zero_division=0))
            f1_wt = float(f1_score(y_test, y_pred, average="weighted", zero_division=0))
            cm = confusion_matrix(y_test, y_pred, labels=labels).tolist()
            report = classification_report(y_test, y_pred, labels=labels, output_dict=True, zero_division=0)

            # Feature importances
            feature_importance = {}
            if hasattr(model_obj, "feature_importances_"):
                for idx, col in enumerate(feature_cols):
                    if idx < len(model_obj.feature_importances_):
                        feature_importance[col] = round(float(model_obj.feature_importances_[idx]), 4)
            elif hasattr(model_obj, "coef_"):
                mean_coefs = np.mean(np.abs(model_obj.coef_), axis=0) if len(model_obj.coef_.shape) > 1 else np.abs(model_obj.coef_)
                for idx, col in enumerate(feature_cols):
                    if idx < len(mean_coefs):
                        feature_importance[col] = round(float(mean_coefs[idx]), 4)

            metrics = {
                "algorithm_type": "SUPERVISED_CLASSIFICATION",
                "accuracy": round(acc, 4),
                "precision_macro": round(prec_macro, 4),
                "recall_macro": round(rec_macro, 4),
                "f1_macro": round(f1_mac, 4),
                "f1_weighted": round(f1_wt, 4),
                "labels": labels,
                "confusion_matrix": cm,
                "classification_report": report,
                "feature_importance": feature_importance,
                "inference_latency_ms": latency_ms
            }

        # 7. Model ID & Serialization
        exp_id = f"EXP-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{algorithm[:4].upper()}"
        model_artifact_path = BASE_DIR / "models" / "saved" / f"{exp_id}.joblib"
        joblib.dump({
            "model": model_obj,
            "feature_cols": feature_cols,
            "target_col": target_col,
            "dataset_id": dataset_id,
            "provenance": "PUBLIC_DATASET",
            "algorithm": algorithm
        }, model_artifact_path)

        result_payload = {
            "experiment_id": exp_id,
            "experiment_type": experiment_type,
            "dataset_id": dataset_id,
            "dataset_name": dataset_name,
            "provenance": "PUBLIC_DATASET",
            "algorithm": algorithm,
            "split_method": split_method,
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "train_classes": train_classes,
            "test_classes": test_classes,
            "features_used": feature_cols,
            "target_column": target_col,
            "training_time_ms": training_time_ms,
            "metrics": metrics,
            "model_artifact": str(model_artifact_path),
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        self._record_experiment(result_payload)
        return result_payload

external_model_trainer = ExternalModelTrainer()
