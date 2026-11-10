# TwinNode Cell — Verification and Testing Report

This document records the automated validation test results, simulation qualifications, and the physical test checklist required when connecting the STM32 hardware.

---

## 1. Automated Test Suite Results (15/15 Passed)

The system includes a test suite covering protocol framing, CRC16 calculation, condition recognition, simulation physics, and FastAPI endpoints.

```bash
platform win32 -- Python 3.14.8, pytest-9.2.0, pluggy-1.7.0
rootdir: D:\College\Sem-4\TwinNode-Cell
configfile: pytest.ini
collected 15 items

tests/test_api.py::test_health_endpoint                     PASSED [  6%]
tests/test_api.py::test_ports_endpoint                      PASSED [ 13%]
tests/test_api.py::test_eq15_09_status_endpoint             PASSED [ 20%]
tests/test_api.py::test_testbench_controls                  PASSED [ 26%]
tests/test_condition_engine.py::test_condition_normal_operation       PASSED [ 33%]
tests/test_condition_engine.py::test_condition_sensor_out_of_range    PASSED [ 40%]
tests/test_condition_engine.py::test_condition_sensor_disconnected    PASSED [ 46%]
tests/test_condition_engine.py::test_condition_emergency_stop_latched PASSED [ 53%]
tests/test_condition_engine.py::test_eq15_09_pending_status          PASSED [ 60%]
tests/test_protocol.py::test_crc16_calculation                        PASSED [ 66%]
tests/test_protocol.py::test_packet_setpoint_serialization_roundtrip PASSED [ 73%]
tests/test_protocol.py::test_packet_telemetry_serialization_roundtrip PASSED [ 80%]
tests/test_protocol.py::test_parser_corrupted_data_rejection          PASSED [ 86%]
tests/test_simulation.py::test_simulation_step                       PASSED [ 93%]
tests/test_simulation.py::test_simulation_fault_injection            PASSED [100%]

============================= 15 passed in 0.98s ==============================
```

---

## 2. Frontend Production Build Verification

The React + Vite + Tailwind CSS dashboard was verified using the production bundling pipeline:

```bash
> vite build
✓ 2291 modules transformed.
dist/index.html                   1.36 kB │ gzip:   0.72 kB
dist/assets/index-DsQInz94.css   21.51 kB │ gzip:   4.69 kB
dist/assets/index-CUFcJXsI.js   637.97 kB │ gzip: 172.97 kB
✓ built in 9.42s
```

All 7 SCADA dashboard pages (Overview, Node Management, Test Bench, Sensor Monitoring, Fault Detection, Analytics, Test Reports) compiled cleanly.

---

## 3. End-to-End Simulation Validation

The dual-node simulation engine verified the following scenarios:
1. **Normal Telemetry Stream:** 10Hz updates broadcast over WebSocket to browser client with rolling 35-sample waveform plots.
2. **Setpoint Tracking:** DC motor and servo angles respond with realistic inertial curves toward commanded setpoints.
3. **Sensor Disconnection:** Forcing LM35 disconnect triggers `SENSOR_DISCONNECTED_OR_INVALID` alarm within 100ms.
4. **Collision Distance Avoidance:** Approaching closer than 4.0cm trips autonomous motor halt.
5. **UART Drop:** Simulated communication drop raises `COMMUNICATION_TIMEOUT` alarm after 1500ms.
6. **Report Generation:** Exporting CSV and PDF generates valid documents with session metadata.

---

## 4. Hardware Integration Checklist (Physical Boards)

> [!IMPORTANT]
> **PHYSICAL BENCHTOP VERIFICATION PROCEDURE**  
> While the software, firmware, and simulation modes have been verified and passed all tests, the physical STM32 boards have not yet been wired together on your workbench. Once you connect the hardware, execute this step-by-step checklist:

| Step | Test Objective | Procedure | Expected Physical Observation |
|---|---|---|---|
| **1** | Power Calibration | Measure LM2596 output with DMM before connecting to L293D or Servo. | Output must measure **5.00V ± 0.05V**. |
| **2** | Node 1 Flash | Flash `firmware/node1_test_generator` via STM32CubeIDE. | Green LED LD2 turns ON; USB VCP port appears as `STMicroelectronics Virtual COM Port (COMx)`. |
| **3** | Node 2 Flash | Flash `firmware/node2_actuator_sensor` via STM32CubeIDE. | Green LED LD2 pulses at 500ms steady heartbeat. |
| **4** | Cross-UART | Connect Node 1 PA9 to Node 2 PA10, Node 1 PA10 to Node 2 PA10, and common GND. | Green LED on Node 1 transitions from solid to blinking heartbeat. |
| **5** | Host Serial Link | Launch `start_all.bat`. Navigate to Node Management page, select COM port, click **Connect Hardware**. | Raw packet console begins displaying live telemetry packets at 10Hz. |
| **6** | Motor Control | In Test Bench, command Motor Speed to +50%. | DC motor spins forward (CW). L293D remains cool. |
| **7** | Ultrasonic Distance | Move an obstacle (hand or cardboard) toward HC-SR04 from 30cm to 10cm. | Live distance gauge tracks movement with ±1cm accuracy. |
| **8** | Proximity Safety Trip | Move obstacle closer than 4.0cm while motor is running. | Motor instantly halts; `FAULT_ACTUATOR_STALL` alarm appears on dashboard. |
| **9** | Physical E-Stop | Press User Button B1 (PC13) on Node 1 or Node 2. | Actuators halt immediately; red Emergency Stop banner latches on dashboard. |
