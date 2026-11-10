# STM32CubeMX Configuration Guide — Node 1 (Test Setpoint Generator)

**Target Board:** STM32 NUCLEO-F446RE  
**MCU:** STM32F446RET6 (ARM Cortex-M4 @ 180 MHz, 512KB Flash, 128KB SRAM)  
**Role:** Supervisory Gateway, Test Sequence Generator, Telemetry Streamer  

---

## 1. Pinout & Peripheral Configuration

| Peripheral | Pin Name | Signal Function | Mode / Settings | Connected Device / Note |
|---|---|---|---|---|
| **RCC** | Standard | HSI (16MHz) + PLL | 180 MHz SysClk | Internal High-Speed Clock |
| **SYS** | PA13, PA14 | SWDIO, SWCLK | Serial Wire Debug | ST-LINK Debugger |
| **USART2** | PA2 | USART2_TX | Asynchronous, 115200 8N1 | ST-LINK VCP to PC Host |
| **USART2** | PA3 | USART2_RX | Asynchronous, 115200 8N1 | ST-LINK VCP to PC Host |
| **USART1** | PA9 | USART1_TX | Asynchronous, 115200 8N1 | Cross to Node 2 PA10 (RX) |
| **USART1** | PA10 | USART1_RX | Asynchronous, 115200 8N1 | Cross to Node 2 PA9 (TX) |
| **GPIO** | PA5 | GPIO_Output | Output Push-Pull, Low speed | Green LED LD2 (Heartbeat) |
| **GPIO** | PC13 | GPIO_Input | No Pull, Active-Low | Blue User Pushbutton B1 (E-Stop) |

---

## 2. Clock Configuration (Clock Tree)

1. Set **Input frequency (HSI)** to `16 MHz`.
2. Configure **PLL Source MUX** to `HSI`.
3. Set PLL multipliers and dividers:
   - `PLLM` = `16` (Input to VCO = 1 MHz)
   - `PLLN` = `360` (VCO clock = 360 MHz)
   - `PLLP` = `/2` (System Clock = 180 MHz)
4. Enable **Over-Drive** mode in Power Controller.
5. Set **AHB Prescaler** to `/1` (HCLK = 180 MHz).
6. Set **APB1 Prescaler** to `/4` (PCLK1 = 45 MHz, APB1 Timers = 90 MHz).
7. Set **APB2 Prescaler** to `/2` (PCLK2 = 90 MHz, APB2 Timers = 180 MHz).
8. Flash Latency: **5 Wait States (WS)**.

---

## 3. Peripheral Parameter Configuration

### A. USART1 (Inter-Node Bus)
- **Baud Rate:** `115200 Bits/s`
- **Word Length:** `8 Bits`
- **Parity:** `None`
- **Stop Bits:** `1`
- **NVIC Settings:** Enable `USART1 global interrupt` (Priority 1, Subpriority 0).

### B. USART2 (ST-LINK Virtual COM Port)
- **Baud Rate:** `115200 Bits/s`
- **Word Length:** `8 Bits`
- **Parity:** `None`
- **Stop Bits:** `1`
- **NVIC Settings:** Enable `USART2 global interrupt` (Priority 2, Subpriority 0).

---

## 4. Compilation in STM32CubeIDE

1. Under **Project Manager** in CubeMX:
   - Toolchain / IDE: Select `STM32CubeIDE`.
   - Check `Generate peripheral initialization as a pair of '.c/.h' files per peripheral`.
2. Click **Generate Code**.
3. Replace generated `main.c` and `main.h` with `firmware/node1_test_generator/Core/Src/main.c` and `Inc/main.h`.
4. Include `protocol.c`, `protocol.h`, `test_generator.c`, `test_generator.h`.
5. Build and Flash via ST-LINK USB cable.
