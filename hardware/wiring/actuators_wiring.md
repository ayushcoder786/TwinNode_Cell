# Actuators Wiring Guide: L293D Motor Driver & Servo Motor

Step-by-step connection instructions for Node 2 controlling the L293D H-Bridge DC motor driver and servo motor.

---

## 1. L293D Dual H-Bridge Driver Hookup

```
               +-------------+
    (PWM) PB6 -| 1 (1,2EN) 16|- 5V (Logic VCC1 from STM32 or LM2596)
    (Dir) PB4 -| 2 (1A)    15|- (Unused 4A)
  Motor Lead 1 -| 3 (1Y)    14|- (Unused 4Y)
        GND ---| 4 (GND)   13|- GND
        GND ---| 5 (GND)   12|- GND
  Motor Lead 2 -| 6 (2Y)    11|- (Unused 3Y)
    (Dir) PB5 -| 7 (2A)    10|- (Unused 3A)
5V Buck Rail --| 8 (VCC2)   9|- (Unused 3,4EN)
               +-------------+
```

### Pin-by-Pin Wiring Steps:
1. **Pin 1 (1,2EN):** Connect to STM32 Node 2 pin **PB6** (TIM4_CH1 PWM).
2. **Pin 2 (1A / IN1):** Connect to STM32 Node 2 pin **PB4** (GPIO Output).
3. **Pin 7 (2A / IN2):** Connect to STM32 Node 2 pin **PB5** (GPIO Output).
4. **Pin 3 (1Y / OUT1):** Connect to DC Motor terminal 1.
5. **Pin 6 (2Y / OUT2):** Connect to DC Motor terminal 2.
6. **Pins 4 & 5 (GND):** Connect to Common Ground bus on the breadboard.
7. **Pin 8 (VCC2 - Motor Power):** Connect to **LM2596 Buck Converter 5.0V Output**.
8. **Pin 16 (VCC1 - Logic Power):** Connect to **5.0V Rail** (or STM32 Node 2 5V pin). L293D requires minimum 4.5V logic supply. STM32 3.3V GPIO inputs easily satisfy the 2.3V VIH threshold.

---

## 2. Servo Motor Hookup (SG90 / MG995)

| Servo Wire Color | Function | Connected To | Voltage Level |
|---|---|---|---|
| **Brown / Black** | Ground (GND) | Common Ground Bus on Breadboard | 0V Reference |
| **Red** | Power (V+) | **LM2596 Buck Converter 5.0V Output** | **5.0V Rail** (Do NOT connect to STM32 5V pin) |
| **Orange / Yellow / White** | Signal (PWM) | STM32 Node 2 pin **PC6** (TIM3_CH1) | 3.3V PWM (50 Hz, 1.0ms - 2.0ms pulse) |

---

## 3. Direction and Speed Logic Truth Table

| Target Speed (%) | PB6 (TIM4_CH1 PWM) | PB4 (IN1) | PB5 (IN2) | Motor Action |
|---|---|---|---|---|
| **0% (Halt)** | 0% Duty | LOW | LOW | Motor Braked / Neutral |
| **+10% to +100% (Forward)** | 10% to 100% Duty | **HIGH** | **LOW** | Clockwise (CW) Rotation |
| **-10% to -100% (Reverse)** | 10% to 100% Duty | **LOW** | **HIGH** | Counter-Clockwise (CCW) Rotation |
