// FC51 GPIO26 (LOW detected), SG90 GPIO32, hardware pause GPIO25 (HIGH holds).
#include <Arduino.h>
#include <ESP32Servo.h>
#include "../protocol.h"
constexpr uint8_t SENSOR_PIN = 26, SERVO_PIN = 32, PAUSE_PIN = 25;
constexpr uint32_t DETECT_CONFIRM_MS = 40, CLEAR_CONFIRM_MS = 350, SETTLE_MS = 500;
constexpr uint32_t DETECT_LOCKOUT_MS = 600;
Protocol protocol("EGG_CONTROLLER");
Servo gate;
int angle = 90, neutral = 90, fertile = 180, infertile = 120;
enum EggState { WAITING, HOLDING, CLEARING };
EggState eggState = WAITING;
bool paused = true, settling = false, detecting = false, clearing = false;
uint32_t detectAt = 0, clearAt = 0, movedAt = 0, activeId = 0, eggSequence = 0;
uint32_t lastDetectAt = 0;
bool detectedBefore = false, resetCompletionPending = false;
bool resetPending = false;
uint32_t resetRemaining = 0, resetTick = 0;

void pause(bool value) { paused = value; digitalWrite(PAUSE_PIN, value ? HIGH : LOW); }
void report(uint32_t id) {
  prefix(id); Serial.printf("ANGLE:%d\n", angle);
  prefix(id); Serial.printf("SENSOR:%d\n", digitalRead(SENSOR_PIN) == LOW);
  prefix(id); Serial.printf("PAUSED:%d\n", paused);
  prefix(id); Serial.printf("EGG_SEQ:%lu\n", (unsigned long)eggSequence);
  prefix(id); Serial.printf("BUSY:%d\n", settling);
  prefix(id); Serial.printf("FERTILE:%d\n", fertile);
  prefix(id); Serial.printf("INFERTILE:%d\n", infertile);
  prefix(id); Serial.printf("NEUTRAL:%d\n", neutral);
  prefix(id); Serial.printf("GATE_RESET_PENDING:%d\n", resetPending);
  protocol.fields(id);
  prefix(id); Serial.printf("STATE:%s\n", protocol.fault ? "FAULT" : eggState == WAITING ? "WAITING" : eggState == HOLDING ? "HOLDING" : "CLEARING");
}
void latchFault(const char *reason) {
  pause(true); resetPending = false; resetCompletionPending = false; settling = false;
  if (activeId) reply(activeId, "ERROR:SERVO_CANCELLED");
  activeId = 0; protocol.fault = true; protocol.faultCode = reason; report(0);
}
void setAngle(int requested, uint32_t id) {
  resetPending = false; resetCompletionPending = false; angle = requested; gate.write(angle);
  activeId = id; movedAt = millis(); settling = true;
  reply(id, "OK:SERVO_ACCEPTED"); report(id);
}
void command(char *line) {
  uint32_t id; char *cmd;
  if (!ovalens::envelope(line, id, cmd)) { reply(0, "ERROR:INVALID_ENVELOPE"); return; }
  if (isStop(cmd)) {
    if (id > protocol.lastId) protocol.lastId = id;
    latchFault("EMERGENCY_STOP"); reply(id, "OK:HOLDING"); return;
  }
  if (!protocol.consume(id)) return;
  if (protocol.read(cmd, id)) { report(id); return; }
  if (!protocol.authorize(id)) return;
  if (!gate.attached()) { reply(id, "ERROR:SERVO_ATTACH"); return; }
  if (!strcmp(cmd, "ACK_FAULT")) {
    if (settling) { reply(id, "ERROR:SYSTEM_BUSY"); return; }
    protocol.fault = false; reply(id, "OK:FAULT_ACKNOWLEDGED"); report(id); return;
  }
  if (!protocol.healthy(id)) return;
  if (!strcmp(cmd, "PAUSE")) { pause(true); reply(id, "OK:PAUSE"); report(id); return; }
  if (settling) { reply(id, "ERROR:SYSTEM_BUSY"); return; }
  if (!strcmp(cmd, "ARM")) {
    if (digitalRead(SENSOR_PIN) == LOW) { reply(id, "ERROR:SENSOR_BLOCKED"); return; }
    pause(true); eggState = WAITING; detecting = clearing = false;
    resetPending = false; reply(id, "OK:ARMED"); report(id); return;
  }
  if (!strcmp(cmd, "RESUME")) {
    if (eggState == HOLDING) { eggState = CLEARING; clearing = false; }
    pause(false); reply(id, "OK:RESUME"); report(id); return;
  }
  if (!strcmp(cmd, "RESET")) { setAngle(neutral, id); return; }
  if (!strcmp(cmd, "SORT:FERTILE")) { setAngle(fertile, id); return; }
  if (!strcmp(cmd, "SORT:INFERTILE")) { setAngle(infertile, id); return; }
  long value;
  if (!strncmp(cmd, "SERVO:", 6) && ovalens::integer(cmd + 6, 0, 180, value)) { setAngle(value, id); return; }
  int *preset = nullptr; const char *number = nullptr;
  if (!strncmp(cmd, "SET_FERTILE:", 12)) { preset = &fertile; number = cmd + 12; }
  else if (!strncmp(cmd, "SET_INFERTILE:", 14)) { preset = &infertile; number = cmd + 14; }
  else if (!strncmp(cmd, "SET_NEUTRAL:", 12)) { preset = &neutral; number = cmd + 12; }
  if (preset && ovalens::integer(number, 0, 180, value)) {
    *preset = value; reply(id, "OK:PRESET_SET"); report(id); return;
  }
  if (!strncmp(cmd, "GATE_RESET_DELAY:", 17) && ovalens::integer(cmd + 17, 1, 10000, value)) {
    resetPending = true; resetRemaining = value; resetTick = millis();
    reply(id, "OK:GATE_RESET_SCHEDULED"); report(id); return;
  }
  reply(id, "ERROR:INVALID_COMMAND");
}
void setup() {
  digitalWrite(PAUSE_PIN, HIGH); pinMode(PAUSE_PIN, OUTPUT); pause(true);
  pinMode(SENSOR_PIN, INPUT_PULLUP);
  Serial.begin(115200); protocol.boot();
  gate.setPeriodHertz(50); gate.attach(SERVO_PIN, 500, 2400);
  if (!gate.attached()) { protocol.faultCode = "SERVO_ATTACH"; report(0); return; }
  gate.write(neutral); movedAt = millis(); settling = true; report(0);
}
void loop() {
  if (protocol.expired()) latchFault("LINK_TIMEOUT");
  uint32_t now = millis();
  if (settling && uint32_t(now - movedAt) >= SETTLE_MS) {
    uint32_t id = activeId; activeId = 0; settling = false;
    reply(id, "OK:SERVO_DONE"); report(id);
    if (resetCompletionPending) {
      resetCompletionPending = false;
      Serial.printf("EVENT:GATE_RESET_DONE:%lu\n", (unsigned long)eggSequence);
    }
  }
  if (!protocol.fault && eggState == WAITING) {
    if (digitalRead(SENSOR_PIN) == LOW) {
      if (detectedBefore && uint32_t(now - lastDetectAt) < DETECT_LOCKOUT_MS) {
        latchFault("FEED_LOCKOUT");
      } else if (!detecting) { detecting = true; detectAt = now; }
      else if (uint32_t(now - detectAt) >= DETECT_CONFIRM_MS) {
        pause(true); eggState = HOLDING; detecting = false; ++eggSequence;
        lastDetectAt = now; detectedBefore = true;
        Serial.printf("EVENT:EGG_DETECTED:%lu\n", (unsigned long)eggSequence); report(0);
      }
    } else detecting = false;
  } else if (!protocol.fault && eggState == CLEARING) {
    if (digitalRead(SENSOR_PIN) == HIGH) {
      if (!clearing) { clearing = true; clearAt = now; }
      else if (uint32_t(now - clearAt) >= CLEAR_CONFIRM_MS) {
        eggState = WAITING; clearing = false;
        Serial.printf("EVENT:EGG_CLEARED:%lu\n", (unsigned long)eggSequence); report(0);
      }
    } else clearing = false;
  }
  // Optional service command counts only unpaused time and uses wrap-safe deltas.
  // Production routing uses conveyor positions instead of this timer.
  if (resetPending) {
    uint32_t elapsed = uint32_t(now - resetTick); resetTick = now;
    if (!paused) {
      if (elapsed >= resetRemaining) {
        resetPending = false; setAngle(neutral, 0);
        resetCompletionPending = true;
      } else resetRemaining -= elapsed;
    }
  }
  for (int n = 0; n < 64 && Serial.available(); ++n) {
    if (protocol.expired()) latchFault("LINK_TIMEOUT");
    int result = protocol.reader.feed(Serial.read());
    if (result < 0) reply(0, "ERROR:INVALID_LINE");
    else if (result > 0) command(protocol.reader.buffer);
  }
}
