# Inter-Node Communication Wiring Guide

This document details the hardware connection between Node 1 (Test Setpoint Generator) and Node 2 (Sensing and Actuation Node).

---

## 1. Physical Interconnect Diagram

```
 +-------------------------+                  +-------------------------+
 |   STM32 NUCLEO-F446RE   |                  |   STM32 NUCLEO-F446RE   |
 |         NODE 1          |                  |         NODE 2          |
 | (Test Setpoint Gen)     |                  | (Actuator & Sensor)     |
 |                         |                  |                         |
 |  [PA9 (USART1_TX)] -----+----------------->+ [PA10 (USART1_RX)]      |
 |                         |   Yellow Wire    |                         |
 |  [PA10 (USART1_RX)] <---+------------------+ [PA9 (USART1_TX)]       |
 |                         |   Blue Wire      |                         |
 |  [GND] -----------------+------------------+ [GND]                   |
 |                         |   Black Wire     |                         |
 +-------------------------+                  +-------------------------+
```

---

## 2. Wire Hookup Table

| Node 1 Physical Pin | Node 1 MCU Signal | Node 2 Physical Pin | Node 2 MCU Signal | Suggested Wire Color | Description |
|---|---|---|---|---|---|
| CN10 - Pin 21 | **PA9 (USART1_TX)** | CN10 - Pin 33 | **PA10 (USART1_RX)** | Yellow | Setpoint commands from Node 1 to Node 2 |
| CN10 - Pin 33 | **PA10 (USART1_RX)** | CN10 - Pin 21 | **PA9 (USART1_TX)** | Blue | Telemetry responses from Node 2 to Node 1 |
| CN10 - Pin 20 | **GND** | CN10 - Pin 20 | **GND** | Black | Shared reference ground for logic signals |

---

## 3. Communication Protocol Parameters

- **Interface:** Hardware USART1 (Asynchronous)
- **Baud Rate:** `115200 bps` (can be configured up to `921600 bps`)
- **Data Bits:** `8`
- **Parity:** `None`
- **Stop Bits:** `1`
- **Flow Control:** None (Software packet framing with CRC16-CCITT and sequence ACKs)
- **Wire Length:** Keep jumper wires under 30 cm (12 inches) to minimize capacitive loading and EMI interference.
