/*
 * OvaLens Unified Single-ESP32 Candling & Conveyor Controller
 * Project: Foundation University OvaLens Capstone System
 * Architecture: Single ESP32 (Consolidated Stepper, Sorting Gate, IR & Lamp)
 * Target Board: ESP32 Dev Module (WROOM-32 / ESP32-S3)
 * Baud Rate: 115200
 */

#include <Arduino.h>
#include <ESP32Servo.h>
#include "protocol.h"

// ==============================================================================
// PIN DEFINITIONS
// ==============================================================================
constexpr uint8_t STEP_PIN    = 16;  // Stepper pulse (A4988 STEP)
constexpr uint8_t DIR_PIN     = 4;   // Stepper direction (A4988 DIR)
constexpr uint8_t ENABLE_PIN  = 17;  // Stepper enable (LOW=active, HIGH=silent sleep)
constexpr uint8_t SENSOR_PIN  = 26;  // Optical IR proximity sensor (Active LOW)
constexpr uint8_t SERVO_PIN   = 32;  // Sorting gate servo PWM
constexpr uint8_t LAMP_PIN    = 27;  // Candling lamp transistor / relay (Active HIGH)
constexpr uint8_t STATUS_LED  = 2;   // Onboard Blue Status LED

// Motion & Position Constants
constexpr int32_t POSITION_LIMIT = 10000000;
constexpr bool INVERT_DIR = true;

// Timing Constants
constexpr uint32_t DETECT_CONFIRM_MS   = 40;
constexpr uint32_t CLEAR_CONFIRM_MS    = 350;
constexpr uint32_t SETTLE_MS           = 500;
constexpr uint32_t DETECT_LOCKOUT_MS   = 600;
constexpr uint32_t AUTO_OFF_TIMEOUT_MS = 15000;

// ==============================================================================
// PROTOCOL & LINK SUPERVISION
// ==============================================================================
struct UnifiedProtocol {
  uint32_t lastId = 0, lastHeartbeat = 0;
  bool armed = false, fault = true;
  const char *faultCode = "STARTUP_ACK_REQUIRED";
  ovalens::Reader reader;

  void boot() {
    Serial.println("BOOT:UNIFIED_V3");
    Serial.println("READY:UNIFIED_V3:PROTOCOL=3");
  }

  bool consume(uint32_t id) {
    if (id && id <= lastId) { reply(id, "ERROR:ID_REUSED"); return false; }
    if (id) lastId = id;
    lastHeartbeat = millis(); armed = true;
    return true;
  }

  bool read(const char *cmd, uint32_t id) {
    if (strcmp(cmd, "PING") && strcmp(cmd, "HELLO") && strcmp(cmd, "STATUS")) return false;
    lastHeartbeat = millis(); armed = true;
    if (!strcmp(cmd, "PING")) { prefix(id); Serial.println("PONG:UNIFIED"); }
    if (!strcmp(cmd, "HELLO")) { prefix(id); Serial.println("READY:UNIFIED_V3:PROTOCOL=3"); }
    if (!strcmp(cmd, "STATUS") && id) reply(id, "OK:STATUS");
    return true;
  }

  bool authorize(uint32_t id) {
    if (!id) { reply(id, "ERROR:COMMAND_ID_REQUIRED"); return false; }
    if (!armed) { reply(id, "ERROR:HEARTBEAT_REQUIRED"); return false; }
    return true;
  }

  bool healthy(uint32_t id) {
    if (fault) { reply(id, "ERROR:FAULT_LATCHED"); return false; }
    return true;
  }

  bool expired() {
    if (armed && ovalens::expired(millis(), lastHeartbeat)) { armed = false; return true; }
    return false;
  }
} protocol;

// ==============================================================================
// HARDWARE DRIVER STATE
// ==============================================================================
// Stepper Driver State
hw_timer_t *pulseTimer = nullptr;
portMUX_TYPE motionMux = portMUX_INITIALIZER_UNLOCKED;
volatile int32_t position = 0, target = 0;
volatile bool moving = false, stepHigh = false, pauseStop = false, watchdogTrip = false;
volatile bool softwarePause = true;  // Replaces the physical pause wire!
volatile uint32_t heartbeatAt = 0;
uint32_t halfPeriodUs = 3000, activeMoveId = 0;
bool awaitingMoveCompletion = false, referenced = false;

// Sorting Gate & IR Sensor State
Servo gate;
int angle = 90, neutral = 90, fertile = 180, infertile = 135;
enum EggState { WAITING, HOLDING, CLEARING };
EggState eggState = WAITING;
bool settling = false, detecting = false, clearing = false;
uint32_t detectAt = 0, clearAt = 0, movedAt = 0, activeServoId = 0, eggSequence = 0;
uint32_t lastDetectAt = 0;
bool detectedBefore = false, resetCompletionPending = false;
bool resetPending = false;
uint32_t resetRemaining = 0, resetTick = 0;

// Candling Lamp State
bool lightOn = false;
uint32_t lightAt = 0;

// ==============================================================================
// STEPPER HARDWARE TIMER ISR
// ==============================================================================
void ARDUINO_ISR_ATTR pulseTick() {
  portENTER_CRITICAL_ISR(&motionMux);
  if (stepHigh) {
    digitalWrite(STEP_PIN, LOW);
    stepHigh = false;
    if (position == target) {
      moving = false;
      digitalWrite(ENABLE_PIN, HIGH); // Silent sleep when target reached
    }
  } else if (moving) {
    if (uint32_t(millis() - heartbeatAt) >= ovalens::LINK_TIMEOUT_MS) {
      moving = false; target = position; watchdogTrip = true;
      digitalWrite(ENABLE_PIN, HIGH);
    } else if (softwarePause) {
      // Internal software pause triggered by IR arrival or explicit PAUSE command!
      moving = false; target = position; pauseStop = true;
      // Keep ENABLE_PIN LOW during pause so the egg doesn't slip in the cradle
    } else {
      digitalWrite(ENABLE_PIN, LOW);
      digitalWrite(STEP_PIN, HIGH);
      stepHigh = true;
      position += target > position ? 1 : -1;
    }
  }
  portEXIT_CRITICAL_ISR(&motionMux);
}

void snapshotMotion(int32_t &p, bool &busy) {
  portENTER_CRITICAL(&motionMux);
  p = position;
  busy = moving || stepHigh;
  portEXIT_CRITICAL(&motionMux);
}

// ==============================================================================
// TELEMETRY & REPORTING
// ==============================================================================
void report(uint32_t id) {
  int32_t p; bool busyMotion;
  snapshotMotion(p, busyMotion);

  prefix(id); Serial.printf("POSITION:%ld\n", long(p));
  prefix(id); Serial.printf("SPEED:%lu\n", (unsigned long)halfPeriodUs);
  prefix(id); Serial.printf("PAUSED:%d\n", softwarePause);
  prefix(id); Serial.printf("BUSY:%d\n", busyMotion || settling);
  prefix(id); Serial.printf("REFERENCE_VALID:%d\n", referenced);
  prefix(id); Serial.printf("ACTIVE_ID:%lu\n", (unsigned long)activeMoveId);
  prefix(id); Serial.printf("ANGLE:%d\n", angle);
  prefix(id); Serial.printf("SENSOR:%d\n", digitalRead(SENSOR_PIN) == LOW);
  prefix(id); Serial.printf("EGG_SEQ:%lu\n", (unsigned long)eggSequence);
  prefix(id); Serial.printf("FERTILE:%d\n", fertile);
  prefix(id); Serial.printf("INFERTILE:%d\n", infertile);
  prefix(id); Serial.printf("NEUTRAL:%d\n", neutral);
  prefix(id); Serial.printf("LIGHT:%d\n", lightOn);
  prefix(id); Serial.printf("GATE_RESET_PENDING:%d\n", resetPending);
  prefix(id); Serial.printf("FAULT:%s\n", protocol.fault ? protocol.faultCode : "NONE");
  prefix(id); Serial.printf("LAST_ID:%lu\n", (unsigned long)protocol.lastId);

  // STATE is the final line of the report. PAUSED independently reports transport hold.
  const char *stateStr = protocol.fault ? "FAULT"
                       : busyMotion     ? "MOVING"
                       : settling       ? "SETTLING"
                       : eggState == WAITING  ? "WAITING"
                       : eggState == HOLDING  ? "HOLDING"
                       : "CLEARING";
  prefix(id); Serial.printf("STATE:%s\n", stateStr);
}

void setLamp(bool on) {
  lightOn = on;
  digitalWrite(LAMP_PIN, on ? HIGH : LOW);
  digitalWrite(STATUS_LED, on ? HIGH : LOW);
  if (on) lightAt = millis();
}

void latchFault(const char *reason) {
  portENTER_CRITICAL(&motionMux);
  moving = false; target = position; pauseStop = false;
  softwarePause = true;
  portEXIT_CRITICAL(&motionMux);

  digitalWrite(ENABLE_PIN, HIGH); // Silence coils on fault
  setLamp(false);

  resetPending = false; resetCompletionPending = false; settling = false;
  if (activeMoveId) reply(activeMoveId, "ERROR:MOVE_CANCELLED");
  if (activeServoId) reply(activeServoId, "ERROR:SERVO_CANCELLED");
  activeMoveId = 0; activeServoId = 0;
  awaitingMoveCompletion = false; referenced = false;

  protocol.fault = true;
  protocol.faultCode = reason;
  report(0);
}

void checkLink() {
  bool trip;
  portENTER_CRITICAL(&motionMux); trip = watchdogTrip; watchdogTrip = false; portEXIT_CRITICAL(&motionMux);
  if (trip || protocol.expired()) {
    protocol.armed = false;
    latchFault("LINK_TIMEOUT");
  }
}

void setServoAngle(int requested, uint32_t id) {
  resetPending = false; resetCompletionPending = false;
  angle = requested;
  gate.write(angle);
  activeServoId = id;
  movedAt = millis();
  settling = true;
  reply(id, "OK:SERVO_ACCEPTED");
  report(id);
}

void moveTo(int32_t destination, uint32_t id) {
  int32_t p; bool busy;
  snapshotMotion(p, busy);
  if (busy || awaitingMoveCompletion) { reply(id, "ERROR:SYSTEM_BUSY"); return; }
  if (softwarePause) { reply(id, "ERROR:PAUSE_ACTIVE"); return; }
  if (destination < -POSITION_LIMIT || destination > POSITION_LIMIT) { reply(id, "ERROR:POSITION_LIMIT"); return; }

  bool forward = destination >= p;
  digitalWrite(DIR_PIN, (INVERT_DIR ? !forward : forward) ? HIGH : LOW);
  timerStop(pulseTimer); timerWrite(pulseTimer, 0);

  portENTER_CRITICAL(&motionMux);
  heartbeatAt = millis();
  target = destination;
  moving = destination != position;
  pauseStop = false;
  if (moving) digitalWrite(ENABLE_PIN, LOW); // Energize stepper driver
  portEXIT_CRITICAL(&motionMux);

  activeMoveId = id;
  awaitingMoveCompletion = true;
  timerStart(pulseTimer);

  reply(id, "OK:MOVE_ACCEPTED");
  report(id);
}

// ==============================================================================
// COMMAND DISPATCHER
// ==============================================================================
void command(char *line) {
  uint32_t id; char *cmd;
  if (!ovalens::envelope(line, id, cmd)) { reply(0, "ERROR:INVALID_ENVELOPE"); return; }

  // ESTOP / Emergency Halt
  if (isStop(cmd)) {
    if (id > protocol.lastId) protocol.lastId = id;
    latchFault("EMERGENCY_STOP");
    reply(id, "OK:ESTOP");
    return;
  }

  if (!protocol.consume(id)) return;
  portENTER_CRITICAL(&motionMux); heartbeatAt = millis(); portEXIT_CRITICAL(&motionMux);

  // Read-only queries (PING, HELLO, STATUS)
  if (protocol.read(cmd, id)) { report(id); return; }

  if (!protocol.authorize(id)) return;

  // Fault Acknowledgment
  if (!strcmp(cmd, "ACK_FAULT")) {
    if (settling) { reply(id, "ERROR:SYSTEM_BUSY"); return; }
    protocol.fault = false;
    reply(id, "OK:FAULT_ACKNOWLEDGED");
    report(id);
    return;
  }

  // Safe Off actions available during fault
  if (!strcmp(cmd, "LIGHT_OFF") || !strcmp(cmd, "OFF")) {
    setLamp(false);
    reply(id, "OK:LIGHT_OFF");
    report(id);
    return;
  }

  if (!protocol.healthy(id)) return;

  // 1. Lamp Commands
  if (!strcmp(cmd, "LIGHT_ON") || !strcmp(cmd, "ON")) {
    setLamp(true);
    reply(id, "OK:LIGHT_ON");
    report(id);
    return;
  }

  // 2. Pause & Transport Control Commands
  if (!strcmp(cmd, "PAUSE")) {
    portENTER_CRITICAL(&motionMux); softwarePause = true; portEXIT_CRITICAL(&motionMux);
    reply(id, "OK:PAUSE");
    report(id);
    return;
  }

  if (!strcmp(cmd, "ARM")) {
    if (digitalRead(SENSOR_PIN) == LOW) { reply(id, "ERROR:SENSOR_BLOCKED"); return; }
    portENTER_CRITICAL(&motionMux); softwarePause = true; portEXIT_CRITICAL(&motionMux);
    eggState = WAITING; detecting = clearing = false; resetPending = false;
    reply(id, "OK:ARMED");
    report(id);
    return;
  }

  if (!strcmp(cmd, "RESUME")) {
    if (eggState == HOLDING) { eggState = CLEARING; clearing = false; }
    portENTER_CRITICAL(&motionMux); softwarePause = false; portEXIT_CRITICAL(&motionMux);
    reply(id, "OK:RESUME");
    report(id);
    return;
  }

  // 3. Stepper Motion Commands
  if (!strcmp(cmd, "SETHOME")) {
    portENTER_CRITICAL(&motionMux); position = target = 0; portEXIT_CRITICAL(&motionMux);
    referenced = true;
    reply(id, "OK:HOME_SET");
    report(id);
    return;
  }

  long value;
  if (!strncmp(cmd, "SPEED:", 6) && ovalens::integer(cmd + 6, 200, 5000, value)) {
    halfPeriodUs = value;
    timerAlarm(pulseTimer, halfPeriodUs, true, 0);
    reply(id, "OK:SPEED");
    report(id);
    return;
  }

  if (!strncmp(cmd, "JOG:", 4) && ovalens::integer(cmd + 4, -100000, 100000, value) && value) {
    int32_t p; bool busy; snapshotMotion(p, busy);
    moveTo(p + value, id);
    return;
  }

  if (!strncmp(cmd, "ADVANCE:", 8) && ovalens::integer(cmd + 8, -100000, 100000, value) && value) {
    if (!referenced) { reply(id, "ERROR:REFERENCE_REQUIRED"); return; }
    int32_t p; bool busy; snapshotMotion(p, busy);
    moveTo(p + value, id);
    return;
  }

  // 4. Sorting Gate Servo Commands
  if (settling) { reply(id, "ERROR:SYSTEM_BUSY"); return; }

  if (!strcmp(cmd, "RESET")) { setServoAngle(neutral, id); return; }
  if (!strcmp(cmd, "SORT:FERTILE")) { setServoAngle(fertile, id); return; }
  if (!strcmp(cmd, "SORT:INFERTILE")) { setServoAngle(infertile, id); return; }

  if (!strncmp(cmd, "SERVO:", 6) && ovalens::integer(cmd + 6, 0, 180, value)) {
    setServoAngle(value, id);
    return;
  }

  int *preset = nullptr; const char *number = nullptr;
  if (!strncmp(cmd, "SET_FERTILE:", 12)) { preset = &fertile; number = cmd + 12; }
  else if (!strncmp(cmd, "SET_INFERTILE:", 14)) { preset = &infertile; number = cmd + 14; }
  else if (!strncmp(cmd, "SET_NEUTRAL:", 12)) { preset = &neutral; number = cmd + 12; }
  if (preset && ovalens::integer(number, 0, 180, value)) {
    *preset = value;
    reply(id, "OK:PRESET_SET");
    report(id);
    return;
  }

  if (!strncmp(cmd, "GATE_RESET_DELAY:", 17) && ovalens::integer(cmd + 17, 1, 10000, value)) {
    resetPending = true; resetRemaining = value; resetTick = millis();
    reply(id, "OK:GATE_RESET_SCHEDULED");
    report(id);
    return;
  }

  reply(id, "ERROR:INVALID_COMMAND");
}

// ==============================================================================
// SETUP
// ==============================================================================
void setup() {
  pinMode(STEP_PIN, OUTPUT); digitalWrite(STEP_PIN, LOW);
  pinMode(DIR_PIN, OUTPUT); digitalWrite(DIR_PIN, INVERT_DIR ? HIGH : LOW);
  pinMode(ENABLE_PIN, OUTPUT); digitalWrite(ENABLE_PIN, HIGH); // Silent on boot
  pinMode(SENSOR_PIN, INPUT_PULLUP);
  pinMode(LAMP_PIN, OUTPUT); digitalWrite(LAMP_PIN, LOW);
  pinMode(STATUS_LED, OUTPUT); digitalWrite(STATUS_LED, LOW);

  Serial.begin(115200);
  protocol.boot();

  // Initialize Stepper Hardware Timer
  pulseTimer = timerBegin(1000000); // 1MHz base timer clock
  if (!pulseTimer) {
    protocol.faultCode = "TIMER_INIT";
    report(0);
    return;
  }
  timerAttachInterrupt(pulseTimer, &pulseTick);
  timerAlarm(pulseTimer, halfPeriodUs, true, 0);

  // Initialize Servo Gate
  ESP32PWM::allocateTimer(0);
  gate.setPeriodHertz(50);
  gate.attach(SERVO_PIN, 500, 2400);
  if (!gate.attached()) {
    protocol.faultCode = "SERVO_ATTACH";
    report(0);
    return;
  }
  gate.write(neutral);
  movedAt = millis();
  settling = true;

  report(0);
}

// ==============================================================================
// MAIN LOOP
// ==============================================================================
void loop() {
  checkLink();
  uint32_t now = millis();

  // 1. Lamp Auto-Off Safety Watchdog (15s)
  if (lightOn && uint32_t(now - lightAt) >= AUTO_OFF_TIMEOUT_MS) {
    latchFault("LIGHT_AUTO_OFF_TIMEOUT");
    reply(0, "WARN:AUTO_OFF_TIMEOUT");
  }

  // 2. Stepper Move Completion Monitoring
  int32_t p; bool busyMotion;
  snapshotMotion(p, busyMotion);
  if (awaitingMoveCompletion && !busyMotion) {
    uint32_t id = activeMoveId; activeMoveId = 0; awaitingMoveCompletion = false;
    bool stopped;
    portENTER_CRITICAL(&motionMux); stopped = pauseStop; pauseStop = false; portEXIT_CRITICAL(&motionMux);
    reply(id, stopped ? "OK:EGG_STOPPED" : "OK:MOVE_DONE");
    report(id);
  }

  // 3. Servo Settle Completion Monitoring
  if (settling && uint32_t(now - movedAt) >= SETTLE_MS) {
    uint32_t id = activeServoId; activeServoId = 0; settling = false;
    reply(id, "OK:SERVO_DONE");
    report(id);
    if (resetCompletionPending) {
      resetCompletionPending = false;
      Serial.printf("EVENT:GATE_RESET_DONE:%lu\n", (unsigned long)eggSequence);
    }
  }

  // 4. Optical IR Arrival & Departure State Machine
  if (!protocol.fault && eggState == WAITING) {
    if (digitalRead(SENSOR_PIN) == LOW) {
      if (detectedBefore && uint32_t(now - lastDetectAt) < DETECT_LOCKOUT_MS) {
        latchFault("FEED_LOCKOUT");
      } else if (!detecting) {
        detecting = true; detectAt = now;
      } else if (uint32_t(now - detectAt) >= DETECT_CONFIRM_MS) {
        // Egg detected: engage software pause instantly
        portENTER_CRITICAL(&motionMux); softwarePause = true; portEXIT_CRITICAL(&motionMux);
        eggState = HOLDING; detecting = false; ++eggSequence;
        lastDetectAt = now; detectedBefore = true;
        Serial.printf("EVENT:EGG_DETECTED:%lu\n", (unsigned long)eggSequence);
        report(0);
      }
    } else {
      detecting = false;
    }
  } else if (!protocol.fault && eggState == CLEARING) {
    if (digitalRead(SENSOR_PIN) == HIGH) {
      if (!clearing) {
        clearing = true; clearAt = now;
      } else if (uint32_t(now - clearAt) >= CLEAR_CONFIRM_MS) {
        eggState = WAITING; clearing = false;
        Serial.printf("EVENT:EGG_CLEARED:%lu\n", (unsigned long)eggSequence);
        report(0);
      }
    } else {
      clearing = false;
    }
  }

  // 5. Gate Reset Delay Handling
  if (resetPending) {
    uint32_t elapsed = uint32_t(now - resetTick); resetTick = now;
    if (!softwarePause) {
      if (elapsed >= resetRemaining) {
        resetPending = false; setServoAngle(neutral, 0);
        resetCompletionPending = true;
      } else {
        resetRemaining -= elapsed;
      }
    }
  }

  // 6. Serial Ingestion
  for (int n = 0; n < 64 && Serial.available(); ++n) {
    if (protocol.expired()) latchFault("LINK_TIMEOUT");
    int result = protocol.reader.feed(Serial.read());
    if (result < 0) reply(0, "ERROR:INVALID_LINE");
    else if (result > 0) command(protocol.reader.buffer);
  }
}

