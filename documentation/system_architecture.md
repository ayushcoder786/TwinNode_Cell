# TwinNode Cell — System Architecture Documentation

**Project Title:** P15 — TwinNode Cell: Distributed Sensing and Actuation Supervisor  
**Classification:** Advanced Industrial IoT / Distributed Validation Instrument  

---

## 1. Executive Summary

TwinNode Cell is a distributed instrumentation and supervisory platform designed for dual-microcontroller industrial control, physical testing, and fault validation. Rather than operating as a conventional telemetry monitor, the system incorporates an autonomous condition-recognition engine that continuously compares commanded setpoints, expected physical responses, measured feedback, loop delays, and sensor integrity.

```
 +--------------------------------------------------------------------------+
 |                      WEB-BASED SCADA DASHBOARD                           |
 |      (React 18 + Vite + Tailwind CSS + Recharts + Lucide Icons)          |
 +-----------------------------------+--------------------------------------+
                                     | WebSocket (Live Telemetry & Alarms)
                                     | HTTP REST (Controls, Profiles, Reports)
                                     v
 +--------------------------------------------------------------------------+
 |                  BACKEND SUPERVISOR GATEWAY (FastAPI)                    |
 | - Real-Time Condition Recognition Engine                                 |
 | - Physics Simulation Engine / Hardware Serial Port Manager               |
 | - Asynchronous SQLite Database (SQLAlchemy + aiosqlite)                  |
 | - Automated CSV & PDF Report Generators (ReportLab)                      |
 +-----------------------------------+--------------------------------------+
                                     | USB Virtual COM Port (115200 Baud)
                                     | ST-LINK VCP (USART2 PA2/PA3)
                                     v
 +--------------------------------------------------------------------------+
 |                   NODE 1: TEST SETPOINT GENERATOR                        |
 |                     (STM32F446RE @ 180 MHz PLL)                          |
 | - Configurable Setpoint Generation (Temperature, Distance, Motor, Servo) |
 | - Binary Packet Framing with CRC16-CCITT & Sequence ACKs                 |
 | - Inter-Node Bus Supervisor & Telemetry Relayer                          |
 +-----------------------------------+--------------------------------------+
                                     | Inter-Node Cross-UART (USART1 115200)
                                     | Yellow: Node 1 PA9 (TX) -> Node 2 PA10 (RX)
                                     | Blue:   Node 2 PA9 (TX) -> Node 1 PA10 (RX)
                                     | Black:  Common GND Reference
                                     v
 +--------------------------------------------------------------------------+
 |                  NODE 2: SENSING AND ACTUATION NODE                      |
 |                     (STM32F446RE @ 180 MHz PLL)                          |
 | - L293D H-Bridge DC Motor Driver (TIM4_CH1 1kHz PWM, PB4/PB5 Direction) |
 | - Servo Angular Actuator (TIM3_CH1 50Hz PWM, 1.0ms - 2.0ms Pulse)        |
 | - LM35 Centigrade Analog Temperature Sensor (ADC1_IN0 PA0, 10mV/°C)      |
 | - HC-SR04 Ultrasonic Distance Sensor (PB8 Trig, PB9 Echo via Level Shift)|
 | - Autonomous Hardware Failsafe & Collision Trip Supervisor               |
 +--------------------------------------------------------------------------+
```

---

## 2. Distributed Responsibilities

### Node 1: Test Setpoint Generator
1. **Command Generation:** Staged and automated setpoints for temperature, proximity distance, DC motor speed/direction, and servo angle.
2. **Packet Formulation:** Encapsulates test commands into robust binary frames validated with CRC16-CCITT checksums.
3. **Bus Health Monitoring:** Tracks message sequence numbers, acknowledgment round-trips, and enforces an autonomous 1500ms timeout alarm if Node 2 fails to return telemetry.
4. **Host Interfacing:** Bridges high-speed binary bus packets to machine-parseable JSON streams over USB Virtual COM Port (VCP) to the host computer.

### Node 2: Sensing and Actuation Node
1. **Actuator Execution:** Modulates 1 kHz PWM for L293D motor speed, asserts PB4/PB5 direction logic, and generates 50 Hz PWM for precise servo angular positioning.
2. **Physical Data Acquisition:** Samples 12-bit ADC on PA0 with 8-sample moving average filtering for LM35 temperature, and triggers 10µs ultrasonic pings on PB8, timing the echo pulse on PB9 with microsecond hardware accuracy.
3. **Autonomous Safety Interlocking:** Immediately forces motor halt and centers servo if distance drops below 4.0 cm, temperature exceeds 85°C, or inter-node communications drop.
4. **Telemetry Response:** Returns complete sensor and actuator states along with local loop latency in microseconds back to Node 1.

---

## 3. Communication Protocol Specification

- **Start of Frame (SOF):** `0xAA 0x55` (2 bytes)
- **Length:** 1 byte (payload length, 0 to 32 bytes)
- **Message Type:** 1 byte (`0x01`=CMD_SETPOINT, `0x02`=TELEMETRY_DATA, `0x06`=EMERGENCY_STOP, etc.)
- **Sequence Number:** 1 byte rolling counter (`0` to `255`)
- **Test ID:** 2 bytes (uint16 little-endian)
- **Payload:** Variable length (10 bytes for setpoints, 12 bytes for telemetry)
- **Checksum:** 2 bytes CRC16-CCITT (polynomial `0x1021`, init `0xFFFF`)
- **End of Frame (EOF):** `0x0D 0x0A` (`\r\n`)
