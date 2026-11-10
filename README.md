# TwinNode Cell — Intelligent ML + Industrial IoT Distributed Sensing and Actuation Supervisor

[![Status](https://img.shields.io/badge/Status-Fully%20Operational-emerald.svg)]()
[![Hardware](https://img.shields.io/badge/Hardware-2%C3%97%20STM32F446RE%20NUCLEO-blue.svg)]()
[![Stack](https://img.shields.io/badge/Frontend-React%2018%20%7C%20Vite%20%7C%20TailwindCSS-sky.svg)]()
[![Backend](https://img.shields.io/badge/Backend-FastAPI%20%7C%20WebSockets%20%7C%20SQLAlchemy-cyan.svg)]()
[![ML](https://img.shields.io/badge/Machine%20Learning-Scikit--learn%20%7C%20Pandas%20%7C%20NumPy-orange.svg)]()
[![Tests](https://img.shields.io/badge/Tests-23%2F23%20Passed%20(100%25)-brightgreen.svg)]()

TwinNode Cell is a comprehensive, production-grade **Machine Learning + Industrial IoT Distributed Sensing and Actuation Supervisor**. It combines real-time embedded firmware on dual STM32 microcontrollers, a dedicated telemetry collector, an end-to-end scikit-learn machine learning pipeline, exploratory data analysis, real-time inference streaming via WebSockets, and closed-loop LED actuation.

---

## 1. System Architecture

```
 +--------------------------------------------------------------------------+
 |               REACT ML STUDIO & SCADA DASHBOARD (Vite + Tailwind)         |
 | - ML Studio Overview, Dataset Manager, Preprocessing, EDA & PCA Viewer   |
 | - Interactive Model Training & Benchmarking (RF, DT, LR, SVM, IF)         |
 | - Live Model Evaluation (Confusion Matrix, Feature Importance, Latency)   |
 | - Real-Time Inference Cockpit & Closed-Loop Actuator Telemetry            |
 +-----------------------------------+--------------------------------------+
                                     | WebSocket (10Hz Real-Time Telemetry & Predictions)
                                     | REST API (/api/ml/predict, /api/ml/train, etc.)
                                     v
 +--------------------------------------------------------------------------+
 |                 FASTAPI INDUSTRIAL ML & SUPERVISOR GATEWAY               |
 | Layer 1: Rule-Based Safety & Condition Engine (Failsafe & E-Stop)        |
 | Layer 2: Real-Time ML Inference (Trained Pipelines + Anomaly Detection)  |
 | Feature Engineering & Leak-Free Chronological Session Preprocessor       |
 | Asynchronous Data Collector (Provenances: REAL_HARDWARE vs SIMULATION)   |
 | SQLite + SQLAlchemy ORM (10 Tables: RawData, Models, Metrics, Runs)     |
 +-----------------------------------+--------------------------------------+
                                     | USB Virtual COM Port (115200 Baud)
                                     | ST-LINK VCP (USART2 PA2/PA3)
                                     v
 +--------------------------------------------------------------------------+
 |                    NODE 1: TEST SETPOINT GENERATOR                       |
 |                      (STM32F446RE @ 180 MHz PLL)                         |
 | - Configurable Setpoint Generation (Temperature, Distance, LED Command)  |
 | - Binary Packet Framing with CRC16-CCITT & Sequence ACKs                 |
 | - Inter-Node Bus Supervisor & Telemetry Streamer                         |
 +-----------------------------------+--------------------------------------+
                                     | Cross-UART (USART1 115200 Baud)
                                     | PA9 (TX) <-> PA10 (RX) + Common GND
                                     v
 +--------------------------------------------------------------------------+
 |                   NODE 2: SENSING & 3-LED ACTUATION                      |
 |                      (STM32F446RE @ 180 MHz PLL)                         |
 | - LM35 Precision Analog Temperature Sensor (ADC1_IN0 PA0, 10mV/°C)       |
 | - HC-SR04 Ultrasonic Distance Sensor (PB8 Trig, PB9 Echo via Level Shift)|
 | - Green LED (PB4 GPIO): Normal Operation State                           |
 | - Yellow LED (PB5 GPIO): Warning / Setpoint Deviation State              |
 | - Red LED (PB6 TIM4_CH1 PWM): Fault Condition with Brightness Control    |
 | - Optional Auxiliary Servo Motor (PC6 TIM3_CH1 50Hz PWM)                 |
 | - Autonomous Hardware Failsafe & Emergency Stop Shutdown (All LEDs OFF)  |
 +--------------------------------------------------------------------------+
```

---

## 2. Hardware Bill of Materials & Pin Configuration

| Subsystem | STM32 Pin | Peripheral Mode | Connection Target | Functional Role |
|---|---|---|---|---|
| **Node 1 TX** | Node 1 **PA9** | USART1_TX (AF7) | Node 2 **PA10 (RX)** | Inter-node command link (3.3V) |
| **Node 1 RX** | Node 1 **PA10**| USART1_RX (AF7) | Node 2 **PA9 (TX)** | Inter-node telemetry return (3.3V) |
| **Host VCP** | Node 1 **PA2/PA3** | USART2 (AF7) | PC ST-LINK USB | Bidirectional serial gateway (115200) |
| **Green LED** | Node 2 **PB4** | GPIO Output | Green LED Anode (via 330Ω) | Normal Operating State |
| **Yellow LED**| Node 2 **PB5** | GPIO Output | Yellow LED Anode (via 330Ω) | Warning / Latency / Drift State |
| **Red LED** | Node 2 **PB6** | TIM4_CH1 (AF2) | Red LED Anode (via 330Ω) | Fault Condition (Configurable PWM) |
| **Aux Servo** | Node 2 **PC6** | TIM3_CH1 (AF2) | Servo Signal (Orange) | Optional positioning actuator |
| **LM35 Vout** | Node 2 **PA0** | ADC1_IN0 (Analog) | LM35 Pin 2 (Center) | 0 - 1.1V (10 mV/°C) |
| **Ultrasonic Trig** | Node 2 **PB8** | GPIO Output | HC-SR04 Trig Pin | 10 µs trigger pulse |
| **Ultrasonic Echo** | Node 2 **PB9** | GPIO Input | BSS138 LV1 Output | 3.3V Level-shifted echo pulse |
| **Ground** | Both **GND** | Ground Rail | Common Ground Plane | Mandatory single ground reference |

---

## 3. Dedicated Raw Data Collection & Provenance

Every telemetry point collected from physical hardware or the simulation engine preserves its raw measurement values without destructive mutation.

### Collected Telemetry Schema (20 Canonical Fields)
1. `timestamp`: ISO-8601 UTC timestamp.
2. `node_id`: Node identifier (1 = Setpoint Generator, 2 = Sensor/Actuator).
3. `test_id`: Test session identifier.
4. `temperature`: Raw LM35 reading (°C).
5. `distance`: Raw HC-SR04 ultrasonic distance (cm).
6. `target_temperature`: Commanded target temperature (°C).
7. `target_distance`: Commanded target distance (cm).
8. `temperature_error`: Tracking error $\Delta T = T_{\text{act}} - T_{\text{target}}$.
9. `distance_error`: Tracking error $\Delta D = D_{\text{act}} - D_{\text{target}}$.
10. `temperature_rate`: Dynamic rate-of-change $dT/dt$ (°C/s).
11. `distance_rate`: Dynamic rate-of-change $dD/dt$ (cm/s).
12. `response_delay_ms`: Node 2 cycle execution delay.
13. `uart_latency_ms`: Measured inter-node bus round-trip latency.
14. `packet_sequence`: Monotonic packet sequence index.
15. `packet_loss`: Rolling packet drop percentage.
16. `sensor_validity`: Boolean flag for physical sensor bounds validation.
17. `led_command`: Commanded actuator state (`GREEN_ON`, `YELLOW_ON`, `RED_ON`, `ALL_OFF`).
18. `led_acknowledgement`: Node 2 ACK status (`ACK_RECEIVED`, `NO_ACK`, `TIMEOUT`).
19. `operating_mode`: Mode (`RUNNING`, `CALIBRATION`, `STANDBY`).
20. `condition_label`: Ground-truth or fused label.
21. `data_source`: **Strict provenance tracking: `REAL_HARDWARE` vs `SIMULATION`**.

---

## 4. Machine Learning Models & Benchmark Results

Trained using scikit-learn on chronologically partitioned multi-session test splits:

| Algorithm | Paradigm | Test Accuracy | Macro F1 | Inference Latency | Primary Application |
|---|---|---|---|---|---|
| **Random Forest** | Supervised Ensemble | **99.31%** | **0.7831** | **0.074 ms** | Multi-class plant fault classification |
| **Decision Tree** | Supervised Rule | **95.04%** | **0.7383** | **0.021 ms** | Ultra-low latency edge decision rules |
| **Logistic Regression** | Supervised Linear | **61.43%** | **0.6672** | **0.017 ms** | Probabilistic baseline & fast confidence |
| **Support Vector Machine (RBF)** | Supervised Margin | **80.03%** | **0.6350** | **0.086 ms** | High-dimensional non-linear margin boundary |
| **Isolation Forest** | Unsupervised | **92.70%** | N/A | **0.500 ms** | Zero-label anomaly & drift detection |

### Operating Condition Classes:
- `NORMAL_OPERATION`: Stable plant equilibrium within physical tolerances.
- `SETPOINT_DEVIATION`: Actuator or thermal lagging, persistent steady-state offset.
- `SENSOR_FAULT`: LM35 saturation/disconnection or HC-SR04 blind-zone timeouts.
- `COMMUNICATION_FAULT`: UART latency spikes (> 150 ms) and packet drops.
- `UNEXPECTED_RESPONSE`: Inverse plant response or anti-correlated motion.
- `ACTUATOR_COMMAND_FAILURE`: Commanded LED state mismatch or missing ACK.
- `EQ_15_09`: **Explicitly retained as `PENDING_CONFIRMATION` without fabricated labels**.

---

## 5. React ML Studio Dashboard Pages

1. **ML Overview:** Executive status KPI cards, active model selection, real-time anomaly scores, and 3-LED closed-loop actuator visualizer.
2. **Dataset Manager:** Tabular dataset viewer, CSV export/import, filtering by provenance (`REAL_HARDWARE` vs `SIMULATION`), and dataset version snapshots.
3. **Data Preprocessing:** Duplicate elimination, IQR outlier detection, 12-feature checklist, scaler selection (StandardScaler, RobustScaler, MinMaxScaler), and leak-free session split settings.
4. **Exploratory Data Analysis (EDA):** Recharts distributions for temperature/distance/latency, Pearson correlation matrix, K-Means clustering, 2D PCA projection scatter plot, and one-click downloadable publication-quality reports.
5. **Model Training:** Interactive training pipeline for Random Forest, Decision Tree, Logistic Regression, SVM, and Isolation Forest with live benchmark comparison.
6. **Model Evaluation:** Multi-class confusion matrix grid, classification reports (precision, recall, f1, support), and physical feature importance bars.
7. **Live ML Predictions:** 10Hz live streaming prediction cockpit with confidence meters, anomaly gauges, Layer 1 vs Layer 2 fusion, and Node 2 actuator status.
8. **Model Management:** Registered models catalog, one-click model activation, and serialized `.joblib` pipeline downloads.

---

## 6. Execution Scripts (Windows Batch)

All commands are bundled into clean single-click scripts:

```bash
# 1. Complete Environment Setup (Python venv, pip requirements, npm dependencies)
setup.bat

# 2. Generate Labelled Multi-Session Dataset & Train All ML Models
train_models.bat

# 3. Master Launcher: Starts both FastAPI Backend (8000) and React Frontend (5173)
start_all.bat

# Individual Service Launchers:
start_backend.bat     # Starts FastAPI on http://localhost:8000
start_frontend.bat    # Starts Vite on http://localhost:5173
start_simulation.bat  # Starts backend in dedicated simulation mode
```

---

## 7. Automated Test Suite

Run the complete test suite verifying the ML pipeline, serial protocol, condition engine, and REST APIs:

```bash
backend\venv\Scripts\python.exe -m pytest tests/ -v
```

**Results:** `23/23 passed in 5.93s (100% pass rate)`.
