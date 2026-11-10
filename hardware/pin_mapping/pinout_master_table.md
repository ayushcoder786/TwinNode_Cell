# TwinNode Cell — Master Pin Mapping Table

Comprehensive pinout guide for both STM32 NUCLEO-F446RE boards and external industrial components.

---

## 1. Node 1: Test Setpoint Generator (STM32 NUCLEO-F446RE)

| Physical Pin | STM32 MCU Pin | Function / Alternate | Connected To / Signal | Voltage Level | Notes |
|---|---|---|---|---|---|
| CN10-Pin 35 | **PA2** | USART2_TX (AF7) | ST-LINK USB VCP (TX to PC) | 3.3V Logic | Internal to Nucleo board |
| CN10-Pin 37 | **PA3** | USART2_RX (AF7) | ST-LINK USB VCP (RX from PC) | 3.3V Logic | Internal to Nucleo board |
| CN10-Pin 21 | **PA9** | USART1_TX (AF7) | **Node 2 PA10 (USART1_RX)** | 3.3V Logic | Cross-over UART TX |
| CN10-Pin 33 | **PA10** | USART1_RX (AF7) | **Node 2 PA9 (USART1_TX)** | 3.3V Logic | Cross-over UART RX |
| CN10-Pin 11 | **PA5** | GPIO Output | Green User LED LD2 | 3.3V Logic | Heartbeat Pulse |
| CN7-Pin 23 | **PC13** | GPIO Input | Blue Pushbutton B1 | 3.3V (Active LOW) | Local E-Stop Trigger |
| CN10-Pin 20 | **GND** | Ground | **Common System Ground** | 0V Reference | **MUST connect to Node 2 GND** |

---

## 2. Node 2: Sensing and Actuation Node (STM32 NUCLEO-F446RE)

| Physical Pin | STM32 MCU Pin | Function / Alternate | Connected To / Signal | Voltage Level | Notes |
|---|---|---|---|---|---|
| CN10-Pin 33 | **PA10** | USART1_RX (AF7) | **Node 1 PA9 (USART1_TX)** | 3.3V Logic | Cross-over UART RX |
| CN10-Pin 21 | **PA9** | USART1_TX (AF7) | **Node 1 PA10 (USART1_RX)** | 3.3V Logic | Cross-over UART TX |
| CN10-Pin 17 | **PB6** | TIM4_CH1 (AF2) | **L293D Pin 1 (EN1)** | 3.3V PWM (1kHz) | Motor Speed PWM |
| CN10-Pin 19 | **PB4** | GPIO Output | **L293D Pin 2 (IN1)** | 3.3V Logic | Motor Direction 1 |
| CN10-Pin 15 | **PB5** | GPIO Output | **L293D Pin 7 (IN2)** | 3.3V Logic | Motor Direction 2 |
| CN10-Pin 4 | **PC6** | TIM3_CH1 (AF2) | **Servo Signal (Orange/White)** | 3.3V PWM (50Hz) | 1.0ms - 2.0ms pulse |
| CN7-Pin 28 | **PA0** | ADC1_IN0 (Analog) | **LM35 Pin 2 (Vout)** | 0 - 1.0V Analog | 10.0 mV/°C |
| CN10-Pin 3 | **PB8** | GPIO Output | **HC-SR04 Trig Pin** | 3.3V (5V Tolerant) | 10µs trigger pulse |
| CN10-Pin 5 | **PB9** | GPIO Input | **BSS138 LV1 (Shifted Echo)** | 3.3V Logic | **DO NOT CONNECT 5V ECHO DIRECTLY** |
| CN10-Pin 11 | **PA5** | GPIO Output | Green User LED LD2 | 3.3V Logic | Safety/Comm status blinker |
| CN7-Pin 23 | **PC13** | GPIO Input | Blue Pushbutton B1 | 3.3V (Active LOW) | Local E-Stop Reset/Trip |
| CN7-Pin 18 | **+3.3V** | Power Out | **BSS138 LV pin & LM35 VCC** | 3.3V Regulated | Clean sensor logic power |
| CN10-Pin 20 | **GND** | Ground | **Common System Ground** | 0V Reference | Common Ground Rail |

---

## 3. L293D Motor Driver Pin Connections

| L293D Pin | Name | Connected To | Voltage | Purpose |
|---|---|---|---|---|
| Pin 1 | **1,2EN** | Node 2 **PB6** (TIM4_CH1) | 3.3V PWM | Speed modulation (0 - 100%) |
| Pin 2 | **1A (IN1)** | Node 2 **PB4** (GPIO) | 3.3V Logic | Direction polarity A |
| Pin 3 | **1Y (OUT1)** | DC Motor Terminal 1 | 0 - 5.0V | Motor drive phase |
| Pin 4, 5 | **GND** | Common Ground | 0V | Heat sink & logic ground |
| Pin 6 | **2Y (OUT2)** | DC Motor Terminal 2 | 0 - 5.0V | Motor drive phase |
| Pin 7 | **2A (IN2)** | Node 2 **PB5** (GPIO) | 3.3V Logic | Direction polarity B |
| Pin 8 | **VCC2 (Motor V+)** | **LM2596 Output (5.0V Rail)** | **5.0V High Current** | **NEVER power from STM32 5V** |
| Pin 16 | **VCC1 (Logic V+)** | STM32 Node 2 **5V or 3.3V** | 3.3V - 5.0V | Internal logic supply |

---

## 4. BSS138 4-Channel Logic Level Converter

| Pin | Connected To | Voltage | Notes |
|---|---|---|---|
| **LV** | STM32 Node 2 **3.3V** | 3.3V Reference | Low Voltage logic supply |
| **GND** | Common Ground | 0V Reference | Common ground |
| **HV** | LM2596 Output **5.0V** | 5.0V Reference | High Voltage supply |
| **LV1** | STM32 Node 2 **PB9** | 3.3V Input | Shifted Echo signal to STM32 |
| **HV1** | HC-SR04 **Echo Pin** | 5.0V Output | 5V ultrasonic return pulse |
