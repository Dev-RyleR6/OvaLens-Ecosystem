# Duck Egg Candling & Sorting Edge Platform — System Architecture & Handoff Guide

> **Project**: Automated Duck Egg Fertility Classifier & Sorter  
> **Repository Context**: Integration guide for Main Edge Application  
> **Date**: October 2026  

---

## 1. System Overview

This edge platform automates duck egg candling, AI fertility classification, and mechanical sorting. The physical system is orchestrated across **three ESP32 microcontrollers** and a **PC Edge Host**:

```
+-----------------------------------------------------------------------------------------+
|                                    PC EDGE HOST                                         |
|  - YOLO Model: weights/best_v3.pt (Classes: 0: Fertile, 1: Infertile)                   |
|  - Camera: USB External Inspection Camera (Index 1 / cv2.CAP_DSHOW / 1280x720)          |
|  - Host Orchestrator: yolo_prototype.py                                                 |
+-------------+-----------------------------+-----------------------------+---------------+
              | USB Serial                  | USB Serial                  | USB Serial
              | (115200 Baud)               | (115200 Baud)               | (115200 Baud)
              v                             v                             v
+---------------------------+ +---------------------------+ +---------------------------+
| ESP32 #1: STEPPER CONVEYOR| | ESP32 #2: EGG CONTROLLER  | | ESP32 #3: LIGHT CONTROLLER|
| - A4988 STEP Pin:  GPIO 2 | | - FC-51 IR Sensor:GPIO 26 | | - Relay / LED:   GPIO 27  |
| - A4988 DIR Pin:   GPIO 4 | | - SG90 Servo Gate:GPIO 32 | |   (Active HIGH: 1=ON, 0=OFF)|
| - Pause Input Pin: GPIO 27|<+ - Pause Output:   GPIO 25 | | - Safety Watchdog: 15s    |
+---------------------------+ (Low-Latency +--------------+ +---------------------------+
                               Hardware)
```

---

## 2. Hardware Pinout & Wiring Specifications

### 2.1 Direct Low-Latency Inter-Board Link
* **Egg Controller GPIO 25** is wired directly to **Conveyor Controller GPIO 27**.
* **Common Ground**: All 3 ESP32 boards share a common ground (`GND`) with the motor drivers and power supplies.
* **Working Principle**:
  - When the FC-51 sensor detects an egg in the candling chamber, the Egg Controller immediately asserts **GPIO 25 HIGH**.
  - On the Stepper Conveyor ESP32, the hardware timer interrupt (`pulseTick()`) reads GPIO 27 on every step pulse. If HIGH, it halts step pulses within **< 10 microseconds**.
  - Motor position, target count, and watchdog link remain fully preserved during the pause.

### 2.2 Board Pinout Table
| Board | Pin | Mode | Connected Component | Logic / Function |
| :--- | :--- | :--- | :--- | :--- |
| **Conveyor ESP32** | `GPIO 2` | OUTPUT | A4988 STEP Pin | Step pulses generated in hardware timer ISR |
| **Conveyor ESP32** | `GPIO 4` | OUTPUT | A4988 DIR Pin | Direction control (`INVERT_DIR = true`) |
| **Conveyor ESP32** | `GPIO 27`| INPUT | Egg Controller GPIO 25 | **HIGH = Pause**, **LOW = Run** |
| **Egg Controller** | `GPIO 26`| INPUT | FC-51 IR Sensor OUT | **LOW = Egg Detected**, **HIGH = Beam Clear** |
| **Egg Controller** | `GPIO 32`| OUTPUT | SG90 Servo Signal | 50Hz PWM, calibrated pulse span (500–2400 µs) |
| **Egg Controller** | `GPIO 25`| OUTPUT | Conveyor ESP32 GPIO 27 | Hardware pause interlock line |
| **Light Controller**| `GPIO 27`| OUTPUT | Relay / Transistor Driver | **HIGH = Candling Lamp ON**, **LOW = OFF** |

---

## 3. Serial Communication Protocols (115200 Baud)

All serial messages are single-line ASCII strings terminated by `\n`.

### 3.1 Port Auto-Discovery Handshake
Sending `PING\n` to available USB serial ports automatically identifies the role of each board:
* Reply `PONG:CONVEYOR` $\to$ Stepper Conveyor Controller
* Reply `PONG:EGG_CONTROLLER` $\to$ Egg Controller
* Reply `PONG:LIGHT_CONTROLLER` $\to$ Candling Light Controller

---

### 3.2 Stepper Conveyor Controller

| Command | Direction | Description | Response / Behavior |
| :--- | :--- | :--- | :--- |
| `PING` | Host $\to$ ESP32 | Connection check | `PONG:CONVEYOR` |
| `SPEED:<us>` | Host $\to$ ESP32 | Set step half-period | Sets timer alarm (e.g. `SPEED:3000`, range 200–5000 µs) |
| `JOG:<steps>` | Host $\to$ ESP32 | Relative step movement | Moves relative by steps (e.g. `JOG:2500` or `JOG:-1500`) |
| `GOTO:<pos>` | Host $\to$ ESP32 | Move to absolute coordinate | Moves to absolute step position |
| `SETHOME` | Host $\to$ ESP32 | Zero current coordinate | Current position becomes step 0 |
| `HALT` | Host $\to$ ESP32 | Emergency stop | Halts step generation immediately |
| `STATUS` | Host $\to$ ESP32 | Query telemetry | Returns multi-line status block: |

```
POSITION:<int>
CHAMBER:<int>
OUTPUT:<int>
SPEED:<int>
BUSY:<0|1>
AUTO:0
STATE:<IDLE|MOVING|PAUSED|HALTED>
```

---

### 3.3 Egg Controller (Sensor & Servo)

#### Outgoing Events (ESP32 $\to$ Host):
* `READY:EGG_CONTROLLER` — Broadcast upon board boot / reset.
* `EGG_DETECTED` — Sent when an egg enters the candling chamber and GPIO 25 is asserted HIGH.
* `EGG_CLEARED` — Sent when the egg exits the chamber sensor beam and the re-arm timer completes.
* `GATE_RESET_DONE` — Sent when an auto-scheduled gate reset completes.

#### Incoming Commands (Host $\to$ ESP32):
| Command | Action | Output Response |
| :--- | :--- | :--- |
| `PING` | Connection test | `PONG:EGG_CONTROLLER` |
| `STATUS` | Query telemetry | Multi-line: `ANGLE:<deg>`, `SENSOR:<0/1>`, `PAUSED:<0/1>`, `STATE:<WAITING/HOLDING/CLEARING>` |
| `SERVO:180` or `SORT:FERTILE` | Move gate to **Fertile** angle (**180°**) | `OK:SORT_FERTILE` / `OK:SERVO` |
| `SERVO:120` or `SORT:INFERTILE`| Move gate to **Infertile** angle (**120°**) | `OK:SORT_INFERTILE` / `OK:SERVO` |
| `RESET` | Move gate to **Neutral** resting angle (**90°**) | `OK:RESET` |
| `SERVO:<deg>` | Move gate to explicit arbitrary angle (0–180°) | `OK:SERVO` |
| `RESUME` | Lower GPIO 25 to LOW (resumes stepper conveyor) | `OK:RESUME` |
| `PAUSE` | Raise GPIO 25 to HIGH (forces conveyor pause) | `OK:PAUSE` |
| `GATE_RESET_DELAY:<ms>` | Schedule automatic return to 90° after N ms | `OK:GATE_RESET_SCHEDULED` |

---

### 3.4 Candling Light Controller

| Command | Action | Output Response |
| :--- | :--- | :--- |
| `PING` | Connection check | `PONG:LIGHT_CONTROLLER` |
| `LIGHT_ON` or `ON` | Turn relay/lamp ON (GPIO 27 HIGH) | `OK:LIGHT_ON` |
| `LIGHT_OFF` or `OFF`| Turn relay/lamp OFF (GPIO 27 LOW) | `OK:LIGHT_OFF` |
| `STATUS` | Query illumination state | `LIGHT:1` (ON) or `LIGHT:0` (OFF) |

* **Safety Timeout**: If the light remains ON for longer than 15,000 ms without command, the firmware turns it OFF automatically (`WARN:AUTO_OFF_TIMEOUT`).

---

## 4. Edge Host Orchestration Sequence

```mermaid
sequenceDiagram
    autonumber
    actor Egg as Duck Egg
    participant Conveyor as Conveyor ESP32 (A4988)
    participant EggCtrl as Egg Controller ESP32
    participant LightCtrl as Light Controller ESP32
    participant PC as PC Edge Application
    participant Camera as USB Camera (Idx 1)
    participant YOLO as YOLO Model (best_v3.pt)

    Note over Conveyor,Egg: Stepper moves belt forward (3000us)
    Egg->>EggCtrl: Enters Chamber (FC-51 LOW for >= 40ms)
    EggCtrl->>Conveyor: GPIO 25 HIGH -> GPIO 27 HIGH (Hardware Pause)
    Note over Conveyor: Stepper halts within < 10 us (zero PC lag)
    EggCtrl->>PC: Serial: 'EGG_DETECTED'
    
    PC->>LightCtrl: Serial: 'LIGHT_ON'
    Note over LightCtrl: Relay GPIO 27 HIGH (Candling Lamp ON)
    Note over PC,Camera: Wait Settle Delay (0.7s) - Vibration damps & auto-exposure locks
    
    PC->>Camera: Flush buffer (6x cap.grab()) & read sharp stationary frame
    Camera-->>PC: High-quality candled frame
    PC->>YOLO: Run inference (conf >= 0.30)
    YOLO-->>PC: Class: 'Fertile' or 'Infertile'
    
    alt Fertile Egg
        PC->>EggCtrl: Serial: 'SERVO:180' (Fertile Angle)
    else Infertile Egg
        PC->>EggCtrl: Serial: 'SERVO:120' (Infertile Angle)
    end
    Note over EggCtrl: SG90 moves to sorting gate angle
    
    Note over PC: Hold stationary for 1.5s (Visual UI check & image logging)
    PC->>LightCtrl: Serial: 'LIGHT_OFF'
    Note over LightCtrl: Relay GPIO 27 LOW (Candling Lamp OFF)
    
    PC->>EggCtrl: Serial: 'RESUME'
    EggCtrl->>Conveyor: GPIO 25 LOW -> GPIO 27 LOW
    Note over Conveyor: Stepper resumes moving; egg travels toward sorting gate
    
    Note over PC: Gate Delay expires (2.5s)
    PC->>EggCtrl: Serial: 'RESET'
    Note over EggCtrl: SG90 returns to Neutral (90°)
    
    Egg->>EggCtrl: Exits sensor beam (Continuous HIGH for >= 350ms)
    EggCtrl->>PC: Serial: 'EGG_CLEARED'
    Note over EggCtrl: System re-arms for next egg
```

---

## 5. Calibrated Operational Parameters

| Parameter | Calibrated Value | Engineering Rationale |
| :--- | :--- | :--- |
| **`FERTILE_ANGLE`** | **180°** | Deflects fertile egg into incubation tray chute |
| **`INFERTILE_ANGLE`** | **120°** | Deflects clear/infertile egg into table-egg bin |
| **`NEUTRAL_ANGLE`** | **90°** | Center closed resting position |
| **`STEPPER_SPEED`** | **3000 µs** | Step pulse half-period (reliable torque, zero stall) |
| **`INVERT_DIR`** | **`true`** | Forward travel direction of conveyor |
| **`SETTLE_DELAY`** | **0.7 s** | Damps mechanical vibration and allows webcam auto-exposure convergence under candling illumination |
| **`CAMERA_BUFFER_DRAIN`**| **6 frames** | Calling `cap.grab()` 6 times flushes stale buffered frames from the DirectShow driver pipe |
| **`HOLD_DELAY`** | **1.5 s** | Stationary hold in chamber after classification for operator HUD confirmation |
| **`GATE_PASS_DELAY`** | **2.5 s** | Travel time from chamber to gate before resetting servo to 90° |
| **`DETECT_CONFIRM_MS`**| **40 ms** | FC-51 continuous LOW debounce window |
| **`CLEAR_CONFIRM_MS`** | **350 ms** | FC-51 continuous HIGH clearance window (prevents double-triggering across egg shell curvature) |
| **`SERVO_PULSE_SPAN`** | **500–2400 µs** | Full 0°–180° physical stroke calibration for SG90 servo |

---

## 6. Complete Firmware Sketches

### 6.1 Stepper Conveyor ESP32 (`firmware/conveyor_esp32/conveyor_esp32.ino`)
```cpp
// ============================================================================
// Stepper Motor Conveyor Controller ESP32
// Hardware: A4988 Driver (STEP GPIO 2, DIR GPIO 4), Pause In GPIO 27
// ============================================================================
#include <Arduino.h>
#include <errno.h>
#include <stdlib.h>
#include <string.h>

constexpr uint8_t STEP_PIN = 2, DIR_PIN = 4;
#define EGG_CONTROL_PIN 27 // Input from Egg Controller GPIO 25 (HIGH = pause)
constexpr bool INVERT_DIR = true;
constexpr int32_t POSITION_LIMIT = 10000000;
constexpr uint32_t LINK_TIMEOUT_MS = 3000;

hw_timer_t *pulseTimer = nullptr;
portMUX_TYPE motionMux = portMUX_INITIALIZER_UNLOCKED;
volatile int32_t position = 0, target = 0;
volatile bool moving = false, stepHigh = false;
volatile uint32_t lastContact = 0;
volatile bool linkFault = false;
int32_t chamber = 0, output = 0;
bool chamberSet = false, outputSet = false;
uint32_t halfPeriodUs = 3000;
const char *state = "IDLE";
const char *endState = "IDLE";
bool awaitingCompletion = false;

void ARDUINO_ISR_ATTR pulseTick() {
  portENTER_CRITICAL_ISR(&motionMux);
  if (stepHigh) {
    digitalWrite(STEP_PIN, LOW);
    stepHigh = false;
    if (position == target) moving = false;
  } else if (moving) {
    if (digitalRead(EGG_CONTROL_PIN) == HIGH) {
      // Hardware pause active: preserve step count, direction, and watchdog
      lastContact = millis();
    } else if (uint32_t(millis() - lastContact) > LINK_TIMEOUT_MS) {
      moving = false;
      target = position;
      linkFault = true;
    } else {
      digitalWrite(STEP_PIN, HIGH);
      stepHigh = true;
      position += target > position ? 1 : -1;
    }
  }
  portEXIT_CRITICAL_ISR(&motionMux);
}

void snapshot(int32_t &p, bool &busy) {
  portENTER_CRITICAL(&motionMux);
  p = position;
  busy = moving || stepHigh;
  portEXIT_CRITICAL(&motionMux);
}

void report() {
  int32_t p; bool busy; snapshot(p, busy);
  bool paused = (digitalRead(EGG_CONTROL_PIN) == HIGH);
  Serial.printf("POSITION:%ld\nCHAMBER:%ld\nOUTPUT:%ld\nSPEED:%lu\nBUSY:%d\nAUTO:0\nSTATE:%s\n",
                long(p), long(chamber), long(output), (unsigned long)halfPeriodUs,
                busy ? 1 : 0, busy ? (paused ? "PAUSED" : "MOVING") : state);
}

void halt() {
  portENTER_CRITICAL(&motionMux);
  moving = false;
  target = position;
  portEXIT_CRITICAL(&motionMux);
  awaitingCompletion = false;
  state = "HALTED";
}

bool number(const char *s, long low, long high, long &value) {
  if (!*s || (*s != '-' && (*s < '0' || *s > '9'))) return false;
  errno = 0; char *end = nullptr;
  value = strtol(s, &end, 10);
  return errno != ERANGE && end != s && *end == '\0' && value >= low && value <= high;
}

void moveTo(int32_t destination, const char *finish) {
  int32_t p; bool busy; snapshot(p, busy);
  if (busy || awaitingCompletion) { Serial.println("ERROR:SYSTEM_BUSY"); return; }
  if (destination < -POSITION_LIMIT || destination > POSITION_LIMIT) {
    Serial.println("ERROR:POSITION_LIMIT"); return;
  }
  bool forward = (destination >= p);
  digitalWrite(DIR_PIN, (INVERT_DIR ? !forward : forward) ? HIGH : LOW);
  timerStop(pulseTimer);
  timerWrite(pulseTimer, 0);
  portENTER_CRITICAL(&motionMux);
  target = destination; moving = destination != position; linkFault = false;
  portEXIT_CRITICAL(&motionMux);
  endState = finish;
  awaitingCompletion = true;
  state = "MOVING";
  timerAlarm(pulseTimer, halfPeriodUs, true, 0);
}

void parseCommand(char *cmd) {
  lastContact = millis();
  if (!strcmp(cmd, "PING")) { Serial.println("PONG:CONVEYOR"); return; }
  if (!strcmp(cmd, "STATUS")) { report(); return; }
  if (!strcmp(cmd, "HALT")) { halt(); report(); return; }
  if (!strcmp(cmd, "SETHOME")) {
    int32_t p; bool busy; snapshot(p, busy);
    if (busy || awaitingCompletion) { Serial.println("ERROR:SYSTEM_BUSY"); return; }
    portENTER_CRITICAL(&motionMux); position = target = 0; portEXIT_CRITICAL(&motionMux);
    state = "IDLE"; report(); return;
  }
  if (!strcmp(cmd, "HOME")) { moveTo(0, "IDLE"); report(); return; }
  if (!strncmp(cmd, "SPEED:", 6)) {
    long us;
    if (number(cmd + 6, 200, 5000, us)) {
      halfPeriodUs = (uint32_t)us;
      timerAlarm(pulseTimer, halfPeriodUs, true, 0);
      report();
    } else Serial.println("ERROR:INVALID_ARGUMENT");
    return;
  }
  if (!strncmp(cmd, "JOG:", 4)) {
    long steps; int32_t p; bool busy; snapshot(p, busy);
    if (number(cmd + 4, -POSITION_LIMIT, POSITION_LIMIT, steps)) {
      moveTo(p + steps, "IDLE"); report();
    } else Serial.println("ERROR:INVALID_ARGUMENT");
    return;
  }
  if (!strncmp(cmd, "GOTO:", 5)) {
    long dest;
    if (number(cmd + 5, -POSITION_LIMIT, POSITION_LIMIT, dest)) {
      moveTo((int32_t)dest, "IDLE"); report();
    } else Serial.println("ERROR:INVALID_ARGUMENT");
    return;
  }
  Serial.println("ERROR:UNKNOWN_COMMAND");
}

void setup() {
  pinMode(STEP_PIN, OUTPUT); digitalWrite(STEP_PIN, LOW);
  pinMode(DIR_PIN, OUTPUT); digitalWrite(DIR_PIN, INVERT_DIR ? HIGH : LOW);
  pinMode(EGG_CONTROL_PIN, INPUT_PULLDOWN);

  Serial.begin(115200);
  lastContact = millis();

  pulseTimer = timerBegin(1000000);
  timerAttachInterrupt(pulseTimer, &pulseTick);
  timerAlarm(pulseTimer, halfPeriodUs, true, 0);

  Serial.println("READY:CONVEYOR");
  report();
}

void loop() {
  int32_t p; bool busy; snapshot(p, busy);
  if (awaitingCompletion && !busy) {
    awaitingCompletion = false;
    state = linkFault ? "FAULT" : endState;
    report();
  }
  static char buffer[64]; static size_t length = 0;
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\r') continue;
    if (c == '\n') {
      buffer[length] = '\0';
      if (length > 0) parseCommand(buffer);
      length = 0;
    } else if (length < sizeof(buffer) - 1) buffer[length++] = c;
  }
}
```

---

### 6.2 Egg Controller ESP32 (`firmware/egg_controller_esp32/egg_controller_esp32.ino`)
```cpp
// ============================================================================
// Egg Controller ESP32 — IR Sensor & SG90 Servo Gate Controller
// Hardware: FC-51 IR (GPIO 26), SG90 Servo (GPIO 32), Pause Out (GPIO 25)
// ============================================================================
#include <Arduino.h>
#include <ESP32Servo.h>
#include <stdlib.h>
#include <string.h>

#define SENSOR_PIN 26
#define SERVO_PIN 32
#define STEPPER_SIGNAL_PIN 25

constexpr int FERTILE_ANGLE = 180;
constexpr int INFERTILE_ANGLE = 120;
constexpr int NEUTRAL_ANGLE = 90;

constexpr unsigned long CLEAR_CONFIRM_MS = 350;
constexpr unsigned long DETECT_CONFIRM_MS = 40;

Servo sortingServo;
int currentAngle = NEUTRAL_ANGLE;

enum State { WAITING_FOR_EGG, HOLDING_IN_CHAMBER, WAITING_FOR_CLEAR };
State currentState = WAITING_FOR_EGG;
unsigned long clearStartTime = 0;
unsigned long detectStartTime = 0;
bool isPaused = false;

unsigned long gateResetAt = 0;
bool gateResetPending = false;

void report() {
  int sensor = digitalRead(SENSOR_PIN);
  const char *st = (currentState == WAITING_FOR_EGG) ? "WAITING" :
                   (currentState == HOLDING_IN_CHAMBER) ? "HOLDING" : "CLEARING";
  Serial.printf("ANGLE:%d\nSENSOR:%d\nPAUSED:%d\nSTATE:%s\n",
                currentAngle, sensor == LOW ? 1 : 0, isPaused ? 1 : 0, st);
}

void setServoAngle(int angle) {
  angle = constrain(angle, 0, 180);
  currentAngle = angle;
  sortingServo.write(angle);
}

void setPause(bool pause) {
  isPaused = pause;
  digitalWrite(STEPPER_SIGNAL_PIN, pause ? HIGH : LOW);
}

void parseCommand(char *cmd) {
  if (!strcmp(cmd, "PING")) { Serial.println("PONG:EGG_CONTROLLER"); return; }
  if (!strcmp(cmd, "STATUS")) { report(); return; }
  if (!strcmp(cmd, "SORT:FERTILE")) {
    setServoAngle(FERTILE_ANGLE);
    Serial.println("OK:SORT_FERTILE");
    return;
  }
  if (!strcmp(cmd, "SORT:INFERTILE")) {
    setServoAngle(INFERTILE_ANGLE);
    Serial.println("OK:SORT_INFERTILE");
    return;
  }
  if (!strcmp(cmd, "RESET")) {
    setServoAngle(NEUTRAL_ANGLE);
    gateResetPending = false;
    Serial.println("OK:RESET");
    return;
  }
  if (!strcmp(cmd, "RESUME")) {
    setPause(false);
    currentState = WAITING_FOR_CLEAR;
    clearStartTime = 0;
    Serial.println("OK:RESUME");
    return;
  }
  if (!strcmp(cmd, "PAUSE")) {
    setPause(true);
    Serial.println("OK:PAUSE");
    return;
  }
  if (!strncmp(cmd, "SERVO:", 6) || !strncmp(cmd, "ANGLE:", 6) || !strncmp(cmd, "SET:", 4)) {
    const char *p = strchr(cmd, ':');
    if (p) {
      setServoAngle(atoi(p + 1));
      Serial.println("OK:SERVO");
      return;
    }
  }
  if (isdigit(cmd[0])) {
    setServoAngle(atoi(cmd));
    Serial.println("OK:SERVO");
    return;
  }
  if (!strncmp(cmd, "GATE_RESET_DELAY:", 17)) {
    unsigned long delayMs = atol(cmd + 17);
    if (delayMs > 0) {
      gateResetAt = millis() + delayMs;
      gateResetPending = true;
      Serial.println("OK:GATE_RESET_SCHEDULED");
    }
    return;
  }
  Serial.println("ERROR:UNKNOWN_COMMAND");
}

void setup() {
  Serial.begin(115200);
  pinMode(STEPPER_SIGNAL_PIN, OUTPUT);
  setPause(false);

  pinMode(SENSOR_PIN, INPUT);

  // Full 0 to 180 degree pulse span (500us to 2400us)
  sortingServo.setPeriodHertz(50);
  sortingServo.attach(SERVO_PIN, 500, 2400);
  setServoAngle(NEUTRAL_ANGLE);

  Serial.println("READY:EGG_CONTROLLER");
  report();
}

void loop() {
  int sensorState = digitalRead(SENSOR_PIN);

  switch (currentState) {
    case WAITING_FOR_EGG:
      if (sensorState == LOW) {
        if (detectStartTime == 0) detectStartTime = millis();
        else if (millis() - detectStartTime >= DETECT_CONFIRM_MS) {
          setPause(true);
          currentState = HOLDING_IN_CHAMBER;
          detectStartTime = 0;
          Serial.println("EGG_DETECTED");
        }
      } else {
        detectStartTime = 0;
      }
      break;

    case HOLDING_IN_CHAMBER:
      // Stationary hold controlled by PC
      break;

    case WAITING_FOR_CLEAR:
      if (sensorState == HIGH) {
        if (clearStartTime == 0) clearStartTime = millis();
        else if (millis() - clearStartTime >= CLEAR_CONFIRM_MS) {
          currentState = WAITING_FOR_EGG;
          clearStartTime = 0;
          detectStartTime = 0;
          Serial.println("EGG_CLEARED");
        }
      } else {
        clearStartTime = 0;
      }
      break;
  }

  if (gateResetPending && millis() >= gateResetAt) {
    setServoAngle(NEUTRAL_ANGLE);
    gateResetPending = false;
    Serial.println("GATE_RESET_DONE");
  }

  static char buffer[64]; static size_t length = 0;
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\r') continue;
    if (c == '\n') {
      buffer[length] = '\0';
      if (length > 0) parseCommand(buffer);
      length = 0;
    } else if (length < sizeof(buffer) - 1) buffer[length++] = c;
  }
}
```

---

### 6.3 Light Controller ESP32 (`firmware/light_controller_esp32/light_controller_esp32.ino`)
```cpp
// ============================================================================
// Candling Lamp Relay Controller ESP32
// Hardware: Relay Signal GPIO 27 (HIGH = ON, LOW = OFF)
// ============================================================================
#include <Arduino.h>
#include <string.h>

#define RELAY_PIN 27

constexpr unsigned long AUTO_OFF_TIMEOUT_MS = 15000;
unsigned long lightTurnedOnAt = 0;
bool lightIsOn = false;

void setLight(bool on) {
  lightIsOn = on;
  digitalWrite(RELAY_PIN, on ? HIGH : LOW);
  if (on) {
    lightTurnedOnAt = millis();
    Serial.println("OK:LIGHT_ON");
  } else {
    Serial.println("OK:LIGHT_OFF");
  }
}

void parseCommand(char *cmd) {
  if (!strcmp(cmd, "PING")) { Serial.println("PONG:LIGHT_CONTROLLER"); return; }
  if (!strcmp(cmd, "STATUS")) { Serial.printf("LIGHT:%d\n", lightIsOn ? 1 : 0); return; }
  if (!strcmp(cmd, "LIGHT_ON") || !strcmp(cmd, "ON")) { setLight(true); return; }
  if (!strcmp(cmd, "LIGHT_OFF") || !strcmp(cmd, "OFF")) { setLight(false); return; }
  Serial.println("ERROR:UNKNOWN_COMMAND");
}

void setup() {
  digitalWrite(RELAY_PIN, LOW);
  pinMode(RELAY_PIN, OUTPUT);
  lightIsOn = false;

  Serial.begin(115200);
  Serial.println("READY:LIGHT_CONTROLLER");
}

void loop() {
  if (lightIsOn && millis() - lightTurnedOnAt >= AUTO_OFF_TIMEOUT_MS) {
    setLight(false);
    Serial.println("WARN:AUTO_OFF_TIMEOUT");
  }

  static char buffer[64]; static size_t length = 0;
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\r') continue;
    if (c == '\n') {
      buffer[length] = '\0';
      if (length > 0) parseCommand(buffer);
      length = 0;
    } else if (length < sizeof(buffer) - 1) buffer[length++] = c;
  }
}
```

---

## 7. Python Edge Host Integration Checklist

When integrating these subsystems into your production edge application:
1. **Background Serial Threads**: Always wrap each serial connection in a thread-safe worker (e.g. `SerialWorker` with an asynchronous queue) so incoming hardware events (`EGG_DETECTED`) are processed without GUI latency.
2. **Camera Buffer Flushing**: Always execute `for _ in range(6): cap.grab()` before reading the still frame for inference. This eliminates motion blur by purging buffered frames captured while the conveyor was in transit.
3. **Triple-Port Auto-Detection**: Use the `PING` handshake to detect and connect the 3 boards dynamically to prevent port misassignment when USB cables are swapped.
4. **Failsafe Resets**: Always bind cleanup handlers to reset the sorting servo to `90°`, turn the candling light `OFF`, and lower the pause line (`RESUME`) on application exit or unexpected error.

