# STM32CubeMX Configuration Guide — Node 2 (Sensing and Actuation Node)

**Target Board:** STM32 NUCLEO-F446RE  
**MCU:** STM32F446RET6 (ARM Cortex-M4 @ 180 MHz)  
**Role:** L293D Motor Driver, Servo PWM Driver, LM35 ADC, HC-SR04 Ultrasonic Sensing  

---

## 1. Pinout & Peripheral Configuration

| Peripheral | Pin Name | Signal Function | Mode / Settings | Connected Device / Note |
|---|---|---|---|---|
| **RCC** | Standard | HSI (16MHz) + PLL | 180 MHz SysClk | Internal Oscillator |
| **USART1** | PA9 | USART1_TX | Asynchronous, 115200 8N1 | Cross to Node 1 PA10 (RX) |
| **USART1** | PA10 | USART1_RX | Asynchronous, 115200 8N1 | Cross to Node 1 PA9 (TX) |
| **TIM4** | PB6 | TIM4_CH1 | PWM Generation CH1 (1 kHz) | L293D Pin 1 (EN1) Motor Speed |
| **GPIO** | PB4 | GPIO_Output | Output Push-Pull, Low speed | L293D Pin 2 (IN1) Motor Dir |
| **GPIO** | PB5 | GPIO_Output | Output Push-Pull, Low speed | L293D Pin 7 (IN2) Motor Dir |
| **TIM3** | PC6 | TIM3_CH1 | PWM Generation CH1 (50 Hz) | Servo PWM Signal Wire |
| **ADC1** | PA0 | ADC1_IN0 | 12-Bit Single Conversion | LM35 Pin 2 (Vout analog) |
| **GPIO** | PB8 | GPIO_Output | Output Push-Pull | HC-SR04 Trig Pin |
| **GPIO** | PB9 | GPIO_Input | No Pull, Floating | HC-SR04 Echo Pin (via BSS138 LV side) |
| **GPIO** | PA5 | GPIO_Output | Output Push-Pull | Green User LED LD2 |
| **GPIO** | PC13 | GPIO_Input | No Pull, Active-Low | Blue User Button B1 (Local E-Stop) |

---

## 2. Timer PWM Configuration

### A. TIM4 (L293D Motor Speed PWM — 1 kHz)
- **Clock Source:** Internal Clock (APB1 Timers = 90 MHz)
- **Prescaler (PSC):** `89` (Timer Clock = 90 MHz / (89 + 1) = 1 MHz = 1 µs count)
- **Counter Mode:** Up
- **Period / Auto-reload (ARR):** `999` (Period = (999 + 1) * 1 µs = 1000 µs = 1 kHz)
- **Channel 1 Mode:** `PWM Generation CH1`
- **Pulse:** `0` (Initial 0% duty)
- **CH1 Polarity:** High

### B. TIM3 (Servo Position PWM — 50 Hz)
- **Clock Source:** Internal Clock (APB1 Timers = 90 MHz)
- **Prescaler (PSC):** `89` (Timer Clock = 1 MHz = 1 µs count)
- **Counter Mode:** Up
- **Period / Auto-reload (ARR):** `19999` (Period = (19999 + 1) * 1 µs = 20,000 µs = 20 ms = 50 Hz)
- **Channel 1 Mode:** `PWM Generation CH1`
- **Pulse:** `1500` (Center 90° = 1500 µs)
- **CH1 Polarity:** High

---

## 3. ADC1 (LM35 Temperature Sensor)

- **Resolution:** 12-bit (0 to 4095)
- **Data Alignment:** Right alignment
- **Scan Conversion Mode:** Disabled
- **Continuous Conversion Mode:** Disabled
- **Discontinuous Mode:** Disabled
- **Regular Channel 1:**
  - Channel: `Channel 0` (PA0)
  - Rank: `1`
  - Sampling Time: `84 Cycles`

---

## 4. Compilation in STM32CubeIDE

1. Under **Project Manager**: Toolchain `STM32CubeIDE`.
2. Generate Code.
3. Replace generated `main.c` and `main.h` with `firmware/node2_actuator_sensor/Core/Src/main.c` and `Inc/main.h`.
4. Copy `actuators.c`, `actuators.h`, `sensors.c`, `sensors.h`, `safety.c`, `safety.h`, `protocol.c`, `protocol.h`.
5. Flash via ST-LINK USB cable.
