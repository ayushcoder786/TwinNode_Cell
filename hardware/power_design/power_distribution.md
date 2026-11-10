# TwinNode Cell — Power Architecture & Safety Design

Industrial-grade power distribution schematic, grounding topology, and critical safety rules.

---

## 1. Power Topology Overview

```
 [4x AA Batteries] (4.8V - 6.0V Nominal)
         |
         +--------------------> [LM2596 Step-Down Buck Converter]
                                        | (Calibrate with DMM to EXACTLY 5.00V)
                                        |
       +--------------------------------+--------------------------------+
       |                                |                                |
  [L293D VCC2]                     [Servo V+]                      [HC-SR04 VCC]
  Pin 8 (Motor Power)              Red Wire (Power)                Pin 1 (5V VCC)
       |                                |                                |
       v                                v                                v
  [DC Motors]                      [Servo Motor]                   [Ultrasonic Transducer]
 (High Current: 300-800mA)       (Transient Peaks: 500mA)         (Steady: 15mA)

=========================== COMMON GROUND BUS ===========================
  Battery (-) === LM2596 GND === L293D (Pins 4,5) === Servo GND === HC-SR04 GND
                               === STM32 Node 1 GND === STM32 Node 2 GND === BSS138 GND
=========================================================================

 [Host PC USB Cable] --------> [STM32 Node 1 USB VCP] (3.3V Logic & VCP)
 [Host PC USB Cable] --------> [STM32 Node 2 USB VCP] (3.3V Logic & Debug)
```

---

## 2. Voltage Rails & Current Budget

| Power Rail | Voltage | Sourced By | Maximum Current | Powers |
|---|---|---|---|---|
| **Raw Battery Rail** | 4.8V - 6.4V | 4x AA Cells (Alkaline or NiMH) | ~2.5A discharge | LM2596 Buck Converter Input |
| **Regulated 5.0V Actuation Rail** | **5.00V ± 0.05V** | **LM2596 Buck Output** | **3.0A continuous** | L293D Motor VCC2, Servo V+, HC-SR04 VCC |
| **Node 1 MCU Logic Rail** | 3.3V Regulated | ST-LINK USB on Node 1 | 300mA | STM32F446RE Node 1 core and I/O |
| **Node 2 MCU Logic Rail** | 3.3V Regulated | ST-LINK USB on Node 2 | 300mA | STM32F446RE Node 2 core, LM35 VCC, BSS138 LV |

---

## 3. Critical Safety Rules & Engineering Warnings

> [!CAUTION]
> **RULE 1: NEVER POWER MOTORS OR SERVOS FROM STM32 5V PIN OR 3.3V PINS**  
> The onboard STM32 voltage regulator and USB ST-LINK power rail cannot supply inductive transient stall currents (which exceed 800mA). Powering motors directly from the microcontroller will cause thermal shutdown, voltage brownout resets, and permanent silicon damage. Always route motor power from the calibrated LM2596 5.0V rail.

> [!WARNING]
> **RULE 2: CALIBRATE LM2596 OUTPUT BEFORE CONNECTING ANY LOAD**  
> Before connecting the L293D, Servo, or HC-SR04, measure the LM2596 output with a digital multimeter (DMM). Turn the multi-turn trimpot counter-clockwise until the measured output is exactly **5.00V DC**. Connecting an uncalibrated buck converter may deliver up to 12V and destroy 5V components.

> [!IMPORTANT]
> **RULE 3: STRICT COMMON GROUND IS MANDATORY**  
> A common electrical reference ground (0V) must connect the negative battery terminal, LM2596 ground, L293D ground pins (4 & 5), Servo ground wire, HC-SR04 ground pin, and the GND pins of **BOTH** STM32 boards. Without a common ground, UART packet framing will corrupt, ADC measurements will float erratically, and logic levels will fail.

> [!IMPORTANT]
> **RULE 4: VOLTAGE COMPATIBILITY & LEVEL CONVERSION**  
> The STM32 operates on 3.3V logic. The HC-SR04 Ultrasonic sensor operates on 5V and emits a **5.0V Echo pulse**. While some STM32 pins are labeled 5V-tolerant in input floating mode, connecting 5V directly during reset, unconfigured state, or ADC configuration can destroy the input buffer. Always pass the Echo pulse through the **BSS138 4-Channel Logic Level Converter** (HV1 = 5V Echo, LV1 = 3.3V to PB9).

> [!TIP]
> **RULE 5: PHYSICAL EMERGENCY STOP RECOMMENDATION**  
> In industrial practice, a normally closed (NC) mechanical emergency-stop mushroom pushbutton should be wired in series with the battery positive feed to the LM2596 buck converter. Pressing this physical switch cuts power to all motors and actuators instantaneously, regardless of software state.
