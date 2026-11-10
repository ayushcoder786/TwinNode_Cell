# TwinNode Cell — Phase 1 Engineering Correction Report
**Distributed Sensing and Actuation Supervisor**  
**Engineering Audit Resolution: Software & ML Evaluation Defects**  
**Authoritative Reference:** [FINAL_ENGINEERING_AUDIT.md](file:///d:/College/Sem-4/TwinNode-Cell/FINAL_ENGINEERING_AUDIT.md)  
**Execution Timestamp:** 2026-10-31  

---

## Executive Summary

In accordance with [FINAL_ENGINEERING_AUDIT.md](file:///d:/College/Sem-4/TwinNode-Cell/FINAL_ENGINEERING_AUDIT.md), **Phase 1 Engineering Corrections** resolved the core software, preprocessing, splitting, and machine learning evaluation defects of the TwinNode Cell distributed supervisor before physical hardware commissioning.

### Key Milestones Achieved
1. **Task 1 — Preprocessing Bug Fixed & Tested:** `clean_dataset()` previously pruned records with `sensor_validity == False`, inadvertently discarding 74% of intentional `SENSOR_FAULT` records. The function now explicitly preserves `SENSOR_FAULT` samples while filtering spurious anomalies in nominal data. Raw records in the SQLite database remain pristine and unmutated. Automated tests confirm 100% survival.
2. **Task 2 — StratifiedGroupKFold Independent Session Splitting:** Implemented `session_train_val_test_split()` using `sklearn.model_selection.StratifiedGroupKFold` grouped by `test_id`. Achieved **0% session overlap** across Train (60 sessions, 10,691 samples), Validation (15 sessions, 2,740 samples), and Test (9 sessions, 3,094 samples), guaranteeing zero temporal leakage and strict multi-class representation across all six condition classes.
3. **Task 3 — Model Retraining & Invalidation of 99.50% Claim:** Retrained all supervised models (Random Forest, Decision Tree, Logistic Regression, SVM) and Isolation Forest across the full 6-class dataset ($N=16,525$). Evaluated each class individually with full confusion matrices. The invalid 99.50% headline claim has been removed from all UI views, dashboards, and reports; the true holdout test accuracy across unseen industrial sessions is **85.68% (Random Forest)** and **86.10% (Decision Tree)** with a Macro F1 of **0.829**.
4. **Task 4 — Open-Loop Actuator Status Correction:** Node 2's LED actuation monitoring has been corrected across backend telemetry, WebSocket messages, API endpoints, and the frontend React UI. It is now clearly labeled as `OPEN_LOOP` (`SOFTWARE_COMMAND_ACK`), acknowledging that Node 2 has no optical photodiode or current-sensing shunt and that telemetry reflects commanded GPIO state rather than physical photon emission.
5. **Task 5 — Verification & Build:** All **26 automated backend tests** pass (0 failures), and the Vite frontend production build compiles cleanly without errors.

---

## 1. Task 1: Fix Preprocessing & SENSOR_FAULT Preservation

### 1.1 Defect Analysis
The initial implementation of `clean_dataset()` in [backend/app/data/preprocessing.py](file:///d:/College/Sem-4/TwinNode-Cell/backend/app/data/preprocessing.py) performed the following unconditional filtering:
```python
# Flawed implementation
if filter_invalid and "sensor_validity" in clean_df.columns:
    clean_df = clean_df[clean_df["sensor_validity"] == True].copy()
```
Because the hardware/simulation validator marks out-of-bounds readings (`T > 85°C`, `D > 400cm`, `T < 0°C`) as `sensor_validity = False`, intentional sensor fault injections were filtered out during preprocessing. This starved the classifier of `SENSOR_FAULT` training data and artificially deflated model recall.

### 1.2 Code Corrections
[backend/app/data/preprocessing.py](file:///d:/College/Sem-4/TwinNode-Cell/backend/app/data/preprocessing.py) was updated with `preserve_sensor_faults=True`:
```python
def clean_dataset(
    df: pd.DataFrame,
    drop_duplicates: bool = True,
    impute_strategy: str = "median",
    filter_invalid: bool = True,
    preserve_sensor_faults: bool = True
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    # ...
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
```
- **Integrity of Raw Data:** The database table `raw_sensor_data` remains completely unchanged; filtering occurs exclusively downstream in the ML preprocessing pipeline.
- **Unit Test Proof:** Added `test_sensor_fault_records_survive_preprocessing()` in [tests/test_ml_pipeline.py](file:///d:/College/Sem-4/TwinNode-Cell/tests/test_ml_pipeline.py#L249). The test constructs nominal rows with invalid readings alongside `SENSOR_FAULT` rows with invalid readings, and asserts that 100% of `SENSOR_FAULT` records survive while spurious nominal errors are filtered out.

---

## 2. Task 2: Fix Dataset Splitting & StratifiedGroupKFold Implementation

### 2.1 Independent Session Distribution
The dataset in `twinnode.db` contains **16,525 unique records** spanning **84 independent sessions**:
- Bench baseline: Session 1001 (1,000 samples)
- Baseline scenarios: Sessions 2001–2018 (3,600 samples)
- Real hardware baseline: Sessions 9001, 9002 (2 samples)
- Multi-scenario expansion: Sessions 9003–9065 (11,923 samples)

### 2.2 StratifiedGroupKFold Architecture
To prevent spatial and temporal data leakage between adjacent time steps within the same test bench run, `session_train_val_test_split()` was implemented in [backend/app/data/preprocessing.py](file:///d:/College/Sem-4/TwinNode-Cell/backend/app/data/preprocessing.py#L169-L280) utilizing `sklearn.model_selection.StratifiedGroupKFold`:

```python
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
```

### 2.3 Partitioning Verification ($N = 16,525$)
| Partition | Independent Sessions | Sample Count | Percentage | Class Coverage |
| :--- | :--- | :--- | :--- | :--- |
| **Train** | 60 sessions | 10,691 | 64.7% | 6 / 6 classes (all >1,500 samples) |
| **Validation** | 15 sessions | 2,740 | 16.6% | 6 / 6 classes (all >350 samples) |
| **Holdout Test** | 9 sessions | 3,094 | 18.7% | 6 / 6 classes (all >330 samples) |
| **Total** | **84 sessions** | **16,525** | **100.0%** | **6 / 6 classes** |

- **Session Overlap:** **Strictly 0**. $\text{Train} \cap \text{Val} = \emptyset$, $\text{Train} \cap \text{Test} = \emptyset$, $\text{Val} \cap \text{Test} = \emptyset$.
- **Test Set Class Support:**
  - `NORMAL_OPERATION`: 1,324 samples
  - `ACTUATOR_COMMAND_FAILURE`: 399 samples
  - `SENSOR_FAULT`: 350 samples
  - `SETPOINT_DEVIATION`: 346 samples
  - `UNEXPECTED_RESPONSE`: 341 samples
  - `COMMUNICATION_FAULT`: 334 samples
- **Explicit Warning Mechanism:** When a condition class exists in fewer independent sessions than `n_splits`, the splitter raises an explicit explanation in `class_representation_warnings` stating why the class cannot be partitioned into all folds, rather than silently omitting it.
- **Unit Test Proof:** `test_stratified_group_kfold_session_split_all_six_classes()` in [tests/test_ml_pipeline.py](file:///d:/College/Sem-4/TwinNode-Cell/tests/test_ml_pipeline.py#L291) verifies zero session overlap, 6-class representation, and warning triggers.

---

## 3. Task 3: Retraining All Models & Evaluation

### 3.1 Revocation of the 99.50% Accuracy Claim
The previous claim of 99.50% Random Forest accuracy documented in early summaries was **invalid**. It arose because:
1. The test set was generated using a simple sequential split without session grouping, allowing adjacent time steps of the same scenario to appear in both training and test sets.
2. The old test slice contained only 3 of the 6 classes, with zero support for `SETPOINT_DEVIATION`, `SENSOR_FAULT`, and `COMMUNICATION_FAULT`.
3. All headline claims referencing 99.50% have been removed from the UI and documentation.

### 3.2 Retrained Model Benchmark Results
Evaluated on **3,094 unseen samples across 9 independent holdout sessions**:

| Algorithm | Type | Accuracy | Macro F1 | Weighted F1 | Macro Precision | Macro Recall | Inference Latency |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Decision Tree** | Supervised | **86.10%** | **0.8289** | **0.8441** | 91.94% | 80.93% | **0.007 ms** |
| **Random Forest** | Supervised | **85.68%** | **0.8290** | **0.8423** | 91.55% | 80.31% | **0.026 ms** |
| **SVM (Calibrated RBF)** | Supervised | **79.90%** | **0.7539** | **0.7621** | 93.03% | 72.40% | **0.626 ms** |
| **Logistic Regression** | Supervised | **78.96%** | **0.7400** | **0.7528** | 90.38% | 70.99% | **0.008 ms** |
| **Isolation Forest** | Unsupervised | **91.56%** | — | — | — | — | **0.500 ms** |

### 3.3 Random Forest Per-Class Classification Report (Holdout Test Sessions)
```
                          precision    recall  f1-score   support

ACTUATOR_COMMAND_FAILURE     0.9520    0.3484    0.5101       399
     COMMUNICATION_FAULT     1.0000    0.7605    0.8639       334
        NORMAL_OPERATION     0.8024    0.9970    0.8892      1324
            SENSOR_FAULT     0.7517    0.9257    0.8297       350
      SETPOINT_DEVIATION     1.0000    0.9277    0.9625       346
     UNEXPECTED_RESPONSE     0.9865    0.8592    0.9185       341

                accuracy                         0.8568      3094
               macro avg     0.9155    0.8031    0.8290      3094
            weighted avg     0.8797    0.8568    0.8423      3094
```

### 3.4 Random Forest 6×6 Confusion Matrix
Labels: `[ACTUATOR_COMMAND_FAILURE, COMMUNICATION_FAULT, NORMAL_OPERATION, SENSOR_FAULT, SETPOINT_DEVIATION, UNEXPECTED_RESPONSE]`

```
           Pred:   ACT_FAIL   COMM_FLT   NORM_OP   SENS_FLT   SETP_DEV   UNEXP_RSP
True:
ACT_FAIL             139          0       260          0          0           0
COMM_FLT               1        254        29         50          0           0
NORM_OP                0          0      1320          4          0           0
SENS_FLT               3          0        23        324          0           0
SETP_DEV               0          0         4         17        321           4
UNEXP_RSP              3          0         9         36          0         293
```

### 3.5 Top Predictive Features (Random Forest)
1. `target_temp_dev`: 23.05%
2. `target_dist_dev`: 18.25%
3. `rolling_dist_mean`: 12.26%
4. `rolling_temp_mean`: 11.14%
5. `latency_mean`: 7.55%
6. `packet_loss_rate`: 7.55%
7. `rolling_temp_std`: 7.13%
8. `sensor_stability_score`: 5.19%
9. `response_delay`: 3.65%
10. `led_mismatch`: 2.00%
11. `temp_rate_of_change`: 1.14%
12. `dist_rate_of_change`: 1.10%

---

## 4. Task 4: Correct Actuator Status Reporting

### 4.1 Physical Reality Audit
As established in [FINAL_ENGINEERING_AUDIT.md](file:///d:/College/Sem-4/TwinNode-Cell/FINAL_ENGINEERING_AUDIT.md):
- Node 2 drives LEDs on PB4 (Green), PB5 (Yellow), and PB6 (Red PWM) using `HAL_GPIO_WritePin` and TIM4 PWM.
- Node 2 has **no physical optical feedback sensors** (e.g., photoresistors or photodiodes) and **no current-sensing shunts**.
- Telemetry previously labeled "Actuator Feedback" was simply reflecting the commanded GPIO register state transmitted back over UART.

### 4.2 Software & UI Disclosures Implemented
1. **Supervisor Service ([backend/app/services/supervisor.py](file:///d:/College/Sem-4/TwinNode-Cell/backend/app/services/supervisor.py)):**
   - Added metadata fields: `"led_feedback_mode": "OPEN_LOOP"`, `"led_feedback_type": "SOFTWARE_COMMAND_ACK"`, `"has_physical_optical_feedback": False`.
   - Included in telemetry snapshots, initial WebSocket handshakes, and periodic telemetry broadcasts.
2. **REST API Endpoint ([backend/app/api/ml_endpoints.py](file:///d:/College/Sem-4/TwinNode-Cell/backend/app/api/ml_endpoints.py)):**
   - Updated `/api/ml/actuate-led` to return `"feedback_mode": "OPEN_LOOP"`, `"acknowledgement_type": "SOFTWARE_COMMAND_ACK"`, and `"has_physical_sensor_feedback": False` with an explicit disclosure note.
3. **Frontend Dashboard Views:**
   - **Live Predictions Page ([frontend/src/pages/ml/LivePredictionsPage.jsx](file:///d:/College/Sem-4/TwinNode-Cell/frontend/src/pages/ml/LivePredictionsPage.jsx)):** Replaced "Node 2 Actuator Feedback (Closed-loop)" with "Node 2 Actuator Status (OPEN-LOOP)" with an amber `OPEN_LOOP` indicator badge and an explanatory note.
   - **ML Overview Page ([frontend/src/pages/ml/MLOverviewPage.jsx](file:///d:/College/Sem-4/TwinNode-Cell/frontend/src/pages/ml/MLOverviewPage.jsx)):** Updated actuator card to display "Node 2 Actuator Status (OPEN-LOOP)" with explicit software acknowledgment labeling.
   - **Sidebar Component ([frontend/src/components/Sidebar.jsx](file:///d:/College/Sem-4/TwinNode-Cell/frontend/src/components/Sidebar.jsx)):** Labeled the quick status widget as `ACTUATOR (OPEN_LOOP)`.
   - **Data Preprocessing Page ([frontend/src/pages/ml/DataPreprocessingPage.jsx](file:///d:/College/Sem-4/TwinNode-Cell/frontend/src/pages/ml/DataPreprocessingPage.jsx)):** Updated feature descriptor to "LED Command Mismatch (Open-Loop)".

---

## 5. Task 5: Comprehensive Automated Testing & Build Status

### 5.1 Backend Pytest Execution
Command: `backend\venv\Scripts\python.exe -m pytest tests/ -v`  
Status: **26 PASSED, 0 FAILED** (Duration: 36.29s)

```
tests/test_api.py::test_health_endpoint PASSED                           [  3%]
tests/test_api.py::test_ports_endpoint PASSED                            [  7%]
tests/test_api.py::test_eq15_09_status_endpoint PASSED                   [ 11%]
tests/test_api.py::test_testbench_controls PASSED                        [ 15%]
tests/test_api.py::test_fault_injection_and_reports PASSED               [ 19%]
tests/test_condition_engine.py::test_condition_normal_operation PASSED   [ 23%]
tests/test_condition_engine.py::test_condition_sensor_out_of_range PASSED [ 26%]
tests/test_condition_engine.py::test_condition_sensor_disconnected PASSED [ 30%]
tests/test_condition_engine.py::test_condition_emergency_stop_latched PASSED [ 34%]
tests/test_condition_engine.py::test_eq15_09_pending_status PASSED       [ 38%]
tests/test_ml_pipeline.py::test_data_validator_bounds_and_duplicates PASSED [ 42%]
tests/test_ml_pipeline.py::test_feature_engineering_transformer PASSED   [ 46%]
tests/test_ml_pipeline.py::test_chronological_session_split PASSED       [ 50%]
tests/test_ml_pipeline.py::test_model_training_and_registry PASSED       [ 53%]
tests/test_ml_pipeline.py::test_isolation_forest_anomaly_detector PASSED [ 57%]
tests/test_ml_pipeline.py::test_prediction_service_and_safety_fusion PASSED [ 61%]
tests/test_ml_pipeline.py::test_ml_api_endpoints PASSED                  [ 65%]
tests/test_ml_pipeline.py::test_sensor_fault_records_survive_preprocessing PASSED [ 69%]
tests/test_ml_pipeline.py::test_stratified_group_kfold_session_split_all_six_classes PASSED [ 73%]
tests/test_ml_pipeline.py::test_model_save_reload_and_predict PASSED     [ 76%]
tests/test_protocol.py::test_crc16_calculation PASSED                    [ 80%]
tests/test_protocol.py::test_packet_setpoint_serialization_roundtrip PASSED [ 84%]
tests/test_protocol.py::test_packet_telemetry_serialization_roundtrip PASSED [ 88%]
tests/test_protocol.py::test_parser_corrupted_data_rejection PASSED      [ 92%]
tests/test_simulation.py::test_simulation_step PASSED                    [ 96%]
tests/test_simulation.py::test_simulation_fault_injection PASSED         [100%]
```

### 5.2 Frontend Production Build
Command: `npm run build` (via `cmd /c "npm run build"`)  
Status: **SUCCESS** (Duration: 14.46s)

```
vite v5.4.21 building for production...
transforming...
✓ 2299 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   1.36 kB │ gzip:   0.71 kB
dist/assets/index-C_EEAtSY.css   35.20 kB │ gzip:   6.46 kB
dist/assets/index-CCIG0F6b.js   748.48 kB │ gzip: 194.28 kB
✓ built in 14.46s
```

---

## 6. Summary Comparison: Audit Findings vs Phase 1 Resolution

| Audit Finding ([FINAL_ENGINEERING_AUDIT.md](file:///d:/College/Sem-4/TwinNode-Cell/FINAL_ENGINEERING_AUDIT.md)) | Pre-Correction Status | Phase 1 Corrected Status |
| :--- | :--- | :--- |
| **99.50% Accuracy Claim** | Unstratified 3-class slice; zero test samples for 3 classes. | Revoked. Evaluated on 9 holdout sessions across all 6 classes: **85.68% (Random Forest)**, **86.10% (Decision Tree)**. |
| **Preprocessing Pruning** | `clean_dataset()` deleted 74% of `SENSOR_FAULT` samples. | `preserve_sensor_faults=True` retains 100% of faults; verified via automated unit test. |
| **Data Leakage & Splitting** | Temporal data leakage from adjacent time steps across splits. | `StratifiedGroupKFold` on `test_id`: 0 session overlap, 0% leakage, all 6 classes represented. |
| **Actuator Status Reporting** | Misleadingly claimed "closed-loop physical feedback". | Corrected to `OPEN_LOOP` (`SOFTWARE_COMMAND_ACK`); explicit absence of optical/current sensors noted. |
| **Automated Test Coverage** | 23 tests; no tests for SENSOR_FAULT survival or group splitting. | 26 tests; dedicated tests for preprocessing, group splitting, and model reload. All passing. |

---

## 7. Next Steps Before Phase 2 (Hardware Commissioning)

Phase 1 software and ML evaluation corrections are complete. Before proceeding to physical hardware commissioning:
1. Connect STM32 Node 1 and Node 2 hardware via UART (TX/RX cross-connected, common GND).
2. Execute physical sensor calibration (LM35 ADC offset and HC-SR04 ultrasonic echo timing).
3. Gather an initial batch of real hardware baseline sessions ($N \ge 1,000$ samples across nominal and physical fault injections) to evaluate real-hardware ML generalization.
