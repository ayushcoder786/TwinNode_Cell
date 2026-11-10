"""
TwinNode Real-Time ML Inference Service
Performs low-latency feature extraction, model inference, confidence scoring,
and 2-layer fault fusion (Layer 1: Rule-Based Safety + Layer 2: ML Model).
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import logging

from backend.app.db.session import AsyncSessionLocal
from backend.app.models.schema import PredictionRecord, AnomalyEvent, utc_now
from backend.app.ml.model_registry import model_registry

logger = logging.getLogger("twinnode.ml.predict")

# Recommended action guidance per operational condition
RECOMMENDED_ACTIONS = {
    "NORMAL_OPERATION": "No action needed. System operating within nominal envelope.",
    "SETPOINT_DEVIATION": "Verify thermal heater element and ultrasonic positioning path. Inspect for physical obstruction.",
    "SENSOR_FAULT": "Inspect LM35 ADC connection (PA0) and HC-SR04 ultrasonic echo/trigger wiring. Check for open-circuit or blind-zone limits.",
    "COMMUNICATION_FAULT": "Verify UART baud rate (115200 bps), check inter-node ground connection, inspect cable shielding for EMI.",
    "UNEXPECTED_RESPONSE": "Inspect sensor calibration curves and actuator mechanical linkage. Verify sensor directionality.",
    "ACTUATOR_COMMAND_FAILURE": "Check Node 2 LED driver circuit and GPIO lines (PB4, PB5, PB6). Verify power supply rail.",
    "PENDING_CONFIRMATION": "Condition EQ-15-09 triggered; awaiting formal engineering criteria sign-off.",
    "MODEL_NOT_TRAINED": "No trained active model found. Train a model in ML Studio before enabling real-time ML inference."
}

# LED mapping for Node 2 actuator integration
LED_MAPPING = {
    "NORMAL_OPERATION": "GREEN_ON",
    "SETPOINT_DEVIATION": "YELLOW_ON",
    "COMMUNICATION_FAULT": "YELLOW_ON",
    "SENSOR_FAULT": "RED_ON",
    "UNEXPECTED_RESPONSE": "RED_ON",
    "ACTUATOR_COMMAND_FAILURE": "RED_ON",
    "EMERGENCY_STOP": "ALL_OFF"
}

class PredictionService:
    """Real-time ML inference engine with sliding window feature history."""

    def __init__(self, history_size: int = 20):
        self.history_size = history_size
        self._history: List[Dict[str, Any]] = []
        self._last_prediction: Optional[Dict[str, Any]] = None

    def push_raw_reading(self, record: Dict[str, Any]):
        """Append latest reading to sliding window for rolling feature extraction."""
        self._history.append(record)
        if len(self._history) > self.history_size:
            self._history.pop(0)

    async def predict_latest(
        self,
        current_record: Optional[Dict[str, Any]] = None,
        layer1_rule_fault: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run inference on current sensor record.
        Fuses Layer 1 (Rule-based) with Layer 2 (ML model).
        """
        if current_record:
            self.push_raw_reading(current_record)

        if not self._history:
            return {
                "status": "NO_DATA",
                "predicted_label": "NO_DATA",
                "model_status": "WAITING_FOR_DATA"
            }

        # Check for active model
        model_id, pipeline, metadata = await model_registry.get_active_model()
        if pipeline is None:
            return {
                "status": "MODEL_NOT_TRAINED",
                "predicted_label": "MODEL_NOT_TRAINED",
                "confidence": 0.0,
                "anomaly_score": 0.0,
                "recommended_action": RECOMMENDED_ACTIONS["MODEL_NOT_TRAINED"],
                "suggested_led": "YELLOW_ON",
                "layer1_fault": layer1_rule_fault,
                "model_status": "NOT_TRAINED"
            }

        # Convert recent history to DataFrame for feature pipeline
        df_window = pd.DataFrame(self._history)
        latest_row_df = df_window.tail(1).copy()

        predicted_label = "NORMAL_OPERATION"
        confidence = 1.0
        anomaly_score = 0.0
        is_anomaly = False

        try:
            # 1. Pipeline Prediction
            estimator = pipeline.named_steps.get("classifier", pipeline.steps[-1][1])
            is_unsupervised = isinstance(estimator, type(None)) or "IsolationForest" in str(type(estimator))

            if is_unsupervised:
                X_feats = pipeline.named_steps["feature_engineer"].transform(latest_row_df)
                X_scaled = pipeline.named_steps["scaler"].transform(X_feats)
                raw_score = estimator.score_samples(X_scaled)[0]
                # Normalize 0.0 (nominal) to 1.0 (anomalous)
                anomaly_score = float(np.clip(1.0 - (raw_score + 0.8) / 0.6, 0.0, 1.0))
                is_anomaly = bool(estimator.predict(X_scaled)[0] == -1)
                predicted_label = "ANOMALY_DETECTED" if is_anomaly else "NORMAL_OPERATION"
                confidence = round(1.0 - anomaly_score if not is_anomaly else anomaly_score, 3)
            else:
                pred = pipeline.predict(latest_row_df)[0]
                predicted_label = str(pred)

                if hasattr(pipeline, "predict_proba"):
                    probas = pipeline.predict_proba(latest_row_df)[0]
                    confidence = round(float(np.max(probas)), 3)
                    # Anomaly score inverse of confidence
                    anomaly_score = round(float(1.0 - confidence), 3)
                else:
                    confidence = 0.95
                    anomaly_score = 0.05

                is_anomaly = (predicted_label != "NORMAL_OPERATION") or (anomaly_score > 0.6)

        except Exception as e:
            logger.error(f"Inference computation error: {e}", exc_info=True)
            return {
                "status": "INFERENCE_ERROR",
                "error": str(e),
                "predicted_label": "UNKNOWN",
                "confidence": 0.0
            }

        # 2. Layer 1 vs Layer 2 Fusion
        # Layer 1 Safety ALWAYS overrides ML
        suggested_led = LED_MAPPING.get(predicted_label, "GREEN_ON")
        fault_type = "NOMINAL"

        if layer1_rule_fault and layer1_rule_fault.get("fault_code") not in [None, 0, "NO_FAULT"]:
            rule_code = layer1_rule_fault.get("fault_code")
            if rule_code in ["EMERGENCY_STOP", 7]:
                suggested_led = "ALL_OFF"
                fault_type = "RULE_BASED_SAFETY_TRIP"
            elif rule_code == "EQ_15_09_TRIGGERED":
                fault_type = "RULE_BASED_FAULT (EQ-15-09 PENDING CONFIRMATION)"
            else:
                fault_type = "RULE_BASED_HARDWARE_FAULT"
                suggested_led = "RED_ON"
        elif is_anomaly or predicted_label != "NORMAL_OPERATION":
            fault_type = "ML_PREDICTED_FAULT"

        rec_action = RECOMMENDED_ACTIONS.get(predicted_label, "Inspect system telemetry.")

        result_payload = {
            "status": "SUCCESS",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model_id": model_id,
            "model_version": metadata.get("model_version", "1.0.0") if metadata else "1.0.0",
            "predicted_label": predicted_label,
            "confidence": confidence,
            "anomaly_score": anomaly_score,
            "is_anomaly": is_anomaly,
            "suggested_led": suggested_led,
            "fault_type": fault_type,
            "recommended_action": rec_action,
            "layer1_fault": layer1_rule_fault,
            "feature_snapshot": {
                "temp": float(latest_row_df.iloc[0].get("temperature", 0.0)),
                "dist": float(latest_row_df.iloc[0].get("distance", 0.0)),
                "uart_latency_ms": float(latest_row_df.iloc[0].get("uart_latency_ms", 0.0)),
                "data_source": str(latest_row_df.iloc[0].get("data_source", "SIMULATION"))
            }
        }

        self._last_prediction = result_payload
        return result_payload

    async def persist_prediction(self, pred_result: Dict[str, Any], test_id: Optional[int] = None):
        """Asynchronously log prediction to SQLite prediction_records table."""
        if pred_result.get("status") != "SUCCESS":
            return

        try:
            async with AsyncSessionLocal() as session:
                rec = PredictionRecord(
                    timestamp=utc_now(),
                    test_id=test_id,
                    model_id=pred_result.get("model_id", "UNKNOWN"),
                    predicted_label=pred_result.get("predicted_label", "UNKNOWN"),
                    confidence=pred_result.get("confidence"),
                    anomaly_score=pred_result.get("anomaly_score"),
                    is_anomaly=pred_result.get("is_anomaly", False),
                    data_source=pred_result.get("feature_snapshot", {}).get("data_source", "SIMULATION"),
                    features_used=pred_result.get("feature_snapshot")
                )
                session.add(rec)
                
                # If anomalous, also log AnomalyEvent
                if pred_result.get("is_anomaly"):
                    ae = AnomalyEvent(
                        timestamp=utc_now(),
                        test_id=test_id,
                        model_id=pred_result.get("model_id", "UNKNOWN"),
                        anomaly_score=pred_result.get("anomaly_score", 0.0),
                        threshold=0.65,
                        details=pred_result.get("feature_snapshot"),
                        suggested_action=pred_result.get("recommended_action")
                    )
                    session.add(ae)

                await session.commit()
        except Exception as e:
            logger.error(f"Error persisting prediction: {e}")

prediction_service = PredictionService()
