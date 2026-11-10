# Sensors Wiring Guide: LM35 & HC-SR04 with BSS138 Level Shifter

Comprehensive instructions for interfacing the LM35 precision analog temperature sensor and the HC-SR04 ultrasonic distance sensor with STM32 Node 2.

---

## 1. LM35 Precision Centigrade Temperature Sensor

### Pinout (Flat Face Toward You, Leads Pointing Down):
- **Pin 1 (Left):** `+Vs` (Power Supply)
- **Pin 2 (Center):** `Vout` (Analog Output Voltage)
- **Pin 3 (Right):** `GND` (Ground)

### Wiring Table:
| LM35 Pin | Connected To | Voltage Level | Notes |
|---|---|---|---|
| **Pin 1 (Vs)** | **LM2596 5.0V Rail** (or STM32 5V) | 5.0V DC | LM35 datasheet requires 4.0V - 30V. Powering from 5.0V ensures full spec compliance. Vout remains <1.5V (safe for 3.3V ADC). |
| **Pin 2 (Vout)** | STM32 Node 2 **PA0** (ADC1_IN0) | 0.0V to 1.0V Analog | Scale factor: 10.0 mV per °C (e.g., 250mV at 25°C) |
| **Pin 3 (GND)** | Common Ground Bus | 0V Reference | Common Ground |

---

## 2. HC-SR04 Ultrasonic Sensor with BSS138 Logic Level Converter

### Why the BSS138 Level Converter is Required:
The HC-SR04 requires 5.0V to power its ultrasonic transducers. Consequently, its **Echo output emits a 5.0V logic pulse**. Connecting this 5.0V signal directly to the STM32's 3.3V input buffer can cause CMOS latch-up, input leakage, or permanent silicon damage. The **BSS138 bidirectional level shifter** cleanly translates the 5.0V Echo down to safe 3.3V logic.

### Interconnection Schematic:
```
  [HC-SR04 Sensor]                [BSS138 Level Shifter]            [STM32 Node 2]
 
  Pin 1: VCC (5V) <-------------- LM2596 5.0V Rail
  Pin 2: Trig <--------------------------------------------------- PB8 (GPIO Output)
  Pin 3: Echo (5V) --------------> [HV1]        [LV1] ------------> PB9 (GPIO Input)
  Pin 4: GND <-------------------+ [GND]        [GND] +-----------> GND
                                 |                    |
                           (HV: 5.0V)            (LV: 3.3V)
                                 ^                    ^
                           LM2596 5V Rail       STM32 3.3V Pin
```

### Wiring Table:
| Component & Pin | Connects To | Voltage | Purpose |
|---|---|---|---|
| **HC-SR04 Pin 1 (VCC)** | LM2596 5.0V Output Rail | 5.0V DC | Ultrasonic transducer power |
| **HC-SR04 Pin 2 (Trig)** | STM32 Node 2 **PB8** | 3.3V Output | 10µs trigger pulse to initiate ping |
| **HC-SR04 Pin 3 (Echo)** | BSS138 **HV1** Pin | 5.0V Input | High-voltage 5V echo pulse |
| **BSS138 LV1 Pin** | STM32 Node 2 **PB9** | 3.3V Output | Level-shifted safe 3.3V echo pulse |
| **BSS138 HV Pin** | LM2596 5.0V Output Rail | 5.0V Reference | High side reference |
| **BSS138 LV Pin** | STM32 Node 2 **3.3V** Pin | 3.3V Reference | Low side reference |
| **BSS138 GND Pin** | Common Ground Bus | 0V Reference | Shared reference |
| **HC-SR04 Pin 4 (GND)** | Common Ground Bus | 0V Reference | Shared reference |

---

## 3. Alternative Voltage Divider (If BSS138 is Unavailable)
If the BSS138 module is unavailable, a 5V-to-3.3V resistor voltage divider can be used as an emergency alternative:
- **Resistor R1:** 2.2 kΩ (between HC-SR04 Echo and STM32 PB9)
- **Resistor R2:** 3.3 kΩ (between STM32 PB9 and GND)
- Output voltage = 5.0V * (3.3k / (2.2k + 3.3k)) = 5.0V * 0.6 = **3.0V** (safe 3.3V CMOS HIGH).
