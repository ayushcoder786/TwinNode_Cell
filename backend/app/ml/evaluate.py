"""
TwinNode Model Evaluation Module
Computes comprehensive evaluation metrics, confusion matrix,
macro/weighted precision, recall, F1-score, and inference latency.
"""

import time
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report
)

def evaluate_classifier(
    pipeline,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    class_names: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Evaluates a trained classifier pipeline on holdout test data.
    Measures prediction latency and multi-class metrics without data leakage.
    """
    start_time = time.perf_counter()
    y_pred = pipeline.predict(X_test)
    total_time = (time.perf_counter() - start_time) * 1000.0 # ms
    latency_per_sample = total_time / max(1, len(X_test))

    unique_classes = sorted(list(set(y_test) | set(y_pred)))
    labels = class_names or unique_classes

    acc = float(accuracy_score(y_test, y_pred))
    prec_macro = float(precision_score(y_test, y_pred, average="macro", zero_division=0))
    rec_macro = float(recall_score(y_test, y_pred, average="macro", zero_division=0))
    f1_mac = float(f1_score(y_test, y_pred, average="macro", zero_division=0))
    f1_weighted = float(f1_score(y_test, y_pred, average="weighted", zero_division=0))

    cm = confusion_matrix(y_test, y_pred, labels=labels)
    cm_list = cm.tolist()

    report = classification_report(y_test, y_pred, labels=labels, output_dict=True, zero_division=0)

    # Extract feature importance if available in final estimator
    estimator = pipeline.named_steps.get("classifier", pipeline.steps[-1][1])
    feature_importance = {}
    
    # Check if feature names are accessible
    feature_engineer = pipeline.named_steps.get("feature_engineer")
    feat_names = getattr(feature_engineer, "feature_names", None) or [f"feat_{i}" for i in range(12)]

    if hasattr(estimator, "feature_importances_"):
        importances = estimator.feature_importances_
        for idx, score in enumerate(importances):
            name = feat_names[idx] if idx < len(feat_names) else f"feature_{idx}"
            feature_importance[name] = round(float(score), 4)
    elif hasattr(estimator, "coef_"):
        # For linear models like LogisticRegression / LinearSVC, use mean absolute coefficient across classes
        coef_mean = np.mean(np.abs(estimator.coef_), axis=0) if len(estimator.coef_.shape) > 1 else np.abs(estimator.coef_)
        for idx, score in enumerate(coef_mean):
            name = feat_names[idx] if idx < len(feat_names) else f"feature_{idx}"
            feature_importance[name] = round(float(score), 4)

    return {
        "accuracy": round(acc, 4),
        "precision_macro": round(prec_macro, 4),
        "recall_macro": round(rec_macro, 4),
        "f1_macro": round(f1_mac, 4),
        "f1_weighted": round(f1_weighted, 4),
        "test_samples": len(y_test),
        "labels": labels,
        "confusion_matrix": cm_list,
        "classification_report": report,
        "feature_importance": feature_importance,
        "inference_latency_ms": round(latency_per_sample, 3)
    }
