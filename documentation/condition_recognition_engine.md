# TwinNode Cell — Condition Recognition & Fault Engine

The core supervisory differentiator of TwinNode Cell is its **Special Condition Recognition Engine**. Unlike simple SCADA monitors that display telemetry raw, TwinNode Cell compares physical setpoints against real-world feedback, tracking errors, settling times, and sensor health in real time.

---

## 1. Engine Architecture & Mathematical Criteria

Every 100ms, the engine evaluates incoming telemetry $(Y_t)$ against active target setpoints $(R_t)$ and historical timestamps:

$$\Delta T = |T_{\text{actual}} - T_{\text{target}}|$$
$$\Delta D = |D_{\text{actual}} - D_{\text{target}}|$$
$$\Delta M = |M_{\text{actual}} - M_{\text{target}}|$$
$$\Delta S = |S_{\text{actual}} - S_{\text{target}}|$$

---

## 2. Condition Rules & Threshold Specifications

### 1. Normal Operation (`NORMAL_OPERATION`)
- **Severity:** `OK` (Info)
- **Criteria:** All parameters reside within profile tolerance bands, sensor signals are valid, and bus latency remains under 500ms.
- **Action:** Continuous supervised logging.

### 2. Setpoint Deviation (`SETPOINT_DEVIATION`)
- **Severity:** `WARNING`
- **Criteria:** Measured parameter deviates beyond tolerance band for longer than the persistent duration threshold:
  - Temperature deviation $\Delta T > 3.0^\circ\text{C}$ for $t > 1500\text{ ms}$
  - Distance deviation $\Delta D > 4.0\text{ cm}$ for $t > 1500\text{ ms}$
  - Motor speed deviation $\Delta M > 10\%$ for $t > 1500\text{ ms}$
  - Servo angle deviation $\Delta S > 8^\circ$ for $t > 1500\text{ ms}$
- **Action:** Operator alert, persistent flag logged, test proceeds unless limits are breached.

### 3. Actuator Response Failure / Stall (`ACTUATOR_RESPONSE_FAILURE`)
- **Severity:** `CRITICAL`
- **Criteria:** Motor commanded to speed $> 30\%$ but measured/estimated speed remains $< 5\%$ after $t > 1200\text{ ms}$, OR servo commanded to angle $\Delta \theta > 20^\circ$ but actual angle remained static.
- **Action:** Latch alarm, trigger actuator de-energization, recommend mechanical inspection.

### 4. Sensor Value Out of Range (`SENSOR_OUT_OF_RANGE`)
- **Severity:** `WARNING`
- **Criteria:**
  - LM35 Temperature: $T < 2.0^\circ\text{C}$ or $T > 90.0^\circ\text{C}$
  - HC-SR04 Distance: $D < 2.0\text{ cm}$ or $D > 400.0\text{ cm}$
- **Action:** Raise out-of-range alarm, flag measurement as invalid.

### 5. Sensor Disconnection or Invalid Reading (`SENSOR_DISCONNECTED_OR_INVALID`)
- **Severity:** `CRITICAL`
- **Criteria:**
  - LM35 reading $\le 0.5^\circ\text{C}$ (indicating floating or grounded analog lead) OR $\ge 325.0\text{ mV}$ rail short.
  - HC-SR04 returning $0.0\text{ cm}$ or $999.0\text{ cm}$ timeout indicator.
- **Action:** Trip critical alarm, de-energize affected control loops.

### 6. Communication Timeout (`COMMUNICATION_TIMEOUT`)
- **Severity:** `CRITICAL`
- **Criteria:** No telemetry packet received from Node 2 for $t > 1500\text{ ms}$, or host serial drop $> 2500\text{ ms}$.
- **Action:** Autonomous Node 2 failsafe de-energization (PB6 PWM=0, PC6 Servo=90°), host dashboard alarm.

### 7. Unexpected Actuator Motion (`UNEXPECTED_RESPONSE`)
- **Severity:** `WARNING`
- **Criteria:** Motor commanded forward ($> +20\%$) but feedback indicates reverse rotation ($< -20\%$), or rapid direction oscillations.
- **Action:** Alert operator to inspect H-Bridge wiring polarity (IN1/IN2 on PB4/PB5).

### 8. Emergency Stop (`EMERGENCY_STOP`)
- **Severity:** `CRITICAL`
- **Criteria:** Hardware Pushbutton B1 (PC13) pressed, host dashboard Emergency Stop clicked, or safety trip latched.
- **Action:** Immediate PWM de-energization, latch state until explicit operator reset.

---

## 3. Condition EQ-15-09: Dedicated Specification Status

> [!IMPORTANT]
> **ENGINEERING NOTICE REGARDING CONDITION EQ-15-09**  
> **Status:** `PENDING_CONFIRMATION`  
> **Configuration File:** `backend/config/eq15_09_condition.json`  
> **Detector Module:** `backend/app/services/eq15_09_detector.py`  
>
> The exact physical criteria, trigger thresholds, and actuation sequence for engineering condition **EQ-15-09** have not yet been supplied by the engineering authority. Per system design requirements:
> 1. Physical detection criteria have NOT been invented or fabricated.
> 2. A dedicated, non-blocking configuration stub and evaluation hook are fully integrated.
> 3. The dashboard and API expose the condition's formal `PENDING_CONFIRMATION` state.
> 4. All other condition recognition, actuation, and sensing subsystems operate without interruption.
