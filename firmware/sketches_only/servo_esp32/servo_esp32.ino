// TASK-NEW-FW-SAFE-01. Arduino-ESP32 3.x + ESP32Servo, SG90 GPIO18.
#include <Arduino.h>
#include <ESP32Servo.h>
#include "../protocol.h"

constexpr uint8_t SERVO_PIN = 18;
constexpr int MIN_PULSE_US = 1000, MAX_PULSE_US = 2000;
constexpr uint32_t SETTLE_MS = 500;
Servo gate;
int angle = 90, neutral = 90, fertile = 60, infertile = 120;
bool settling = false, faultLatched = true, linkArmed = false;
uint32_t movedAt = 0, lastHeartbeat = 0, activeId = 0, lastId = 0;
const char *state = "NEUTRAL";
const char *faultCode = "STARTUP_ACK_REQUIRED";
ovalens::Reader reader;

void prefix(uint32_t id) { if (id) Serial.printf("ID:%lu:", (unsigned long)id); }
void reply(uint32_t id, const char *message) { prefix(id); Serial.println(message); }
void report(uint32_t id) {
  prefix(id); Serial.printf("ANGLE:%d\n", angle);
  prefix(id); Serial.printf("FERTILE:%d\n", fertile);
  prefix(id); Serial.printf("INFERTILE:%d\n", infertile);
  prefix(id); Serial.printf("NEUTRAL:%d\n", neutral);
  prefix(id); Serial.printf("BUSY:%d\n", settling);
  prefix(id); Serial.printf("FAULT:%s\n", faultLatched ? faultCode : "NONE");
  prefix(id); Serial.printf("ACTIVE_ID:%lu\n", (unsigned long)activeId);
  prefix(id); Serial.printf("LAST_ID:%lu\n", (unsigned long)lastId);
  prefix(id); Serial.printf("STATE:%s\n", faultLatched ? "FAULT" : state);
}

void latchFault(const char *code) {
  if (activeId) reply(activeId, "ERROR:SERVO_CANCELLED");
  // Hold the last requested angle; do not reset a loaded gate on disconnect.
  settling = false; activeId = 0; faultLatched = true; faultCode = code;
  reply(0, code); report(0);
}
void checkLink() {
  if (linkArmed && ovalens::expired(millis(), lastHeartbeat)) {
    linkArmed = false; latchFault("ERROR:LINK_TIMEOUT");
  }
}
void setAngle(int requested, const char *newState, uint32_t id) {
  angle = requested; state = newState; gate.write(angle);
  movedAt = millis(); settling = true; activeId = id;
  reply(id, "OK:SERVO_ACCEPTED"); report(id);
}

void command(char *line) {
  uint32_t id; char *cmd;
  if (!ovalens::envelope(line, id, cmd)) { reply(0, "ERROR:INVALID_ENVELOPE"); return; }
  if (!strcmp(cmd, "ESTOP") || !strcmp(cmd, "HALT") || !strcmp(cmd, "STOP")) {
    if (id > lastId) lastId = id;
    latchFault("ERROR:EMERGENCY_STOP"); reply(id, "OK:HOLDING"); return;
  }
  if (id && id <= lastId) { reply(id, "ERROR:ID_REUSED"); return; }
  if (id) lastId = id;
  if (!strcmp(cmd, "STATUS") || !strcmp(cmd, "PING") || !strcmp(cmd, "HELLO")) {
    lastHeartbeat = millis(); linkArmed = true;
    if (!strcmp(cmd, "PING")) reply(id, "PONG:SERVO");
    else if (!strcmp(cmd, "HELLO")) reply(id, "READY:SERVO_V2:PROTOCOL=2");
    else report(id);
    return;
  }
  if (!id) { reply(0, "ERROR:COMMAND_ID_REQUIRED"); return; }
  if (!gate.attached()) { reply(id, "ERROR:SERVO_ATTACH"); return; }
  if (!linkArmed) { reply(id, "ERROR:HEARTBEAT_REQUIRED"); return; }
  if (!strcmp(cmd, "ACK_FAULT")) {
    if (settling) { reply(id, "ERROR:SYSTEM_BUSY"); return; }
    faultLatched = false; faultCode = "NONE";
    reply(id, "OK:FAULT_ACKNOWLEDGED"); report(id); return;
  }
  if (faultLatched) { reply(id, "ERROR:FAULT_LATCHED"); return; }
  if (settling) { reply(id, "ERROR:SYSTEM_BUSY"); return; }
  if (!strcmp(cmd, "RESET")) { setAngle(neutral, "NEUTRAL", id); return; }
  if (!strcmp(cmd, "SORT:FERTILE")) { setAngle(fertile, "FERTILE", id); return; }
  if (!strcmp(cmd, "SORT:INFERTILE")) { setAngle(infertile, "INFERTILE", id); return; }
  long value;
  if (!strncmp(cmd, "SERVO:", 6) && ovalens::integer(cmd + 6, 0, 180, value)) {
    setAngle(value, "MANUAL", id); return;
  }
  int *preset = nullptr; const char *number = nullptr;
  if (!strncmp(cmd, "SET_FERTILE:", 12)) { preset = &fertile; number = cmd + 12; }
  else if (!strncmp(cmd, "SET_INFERTILE:", 14)) { preset = &infertile; number = cmd + 14; }
  else if (!strncmp(cmd, "SET_NEUTRAL:", 12)) { preset = &neutral; number = cmd + 12; }
  if (preset && ovalens::integer(number, 0, 180, value)) {
    *preset = value; reply(id, "OK:PRESET_SET"); report(id); return;
  }
  reply(id, "ERROR:INVALID_COMMAND");
}

void setup() {
  Serial.begin(115200); gate.setPeriodHertz(50);
  gate.attach(SERVO_PIN, MIN_PULSE_US, MAX_PULSE_US);
  if (!gate.attached()) { faultCode = "SERVO_ATTACH"; reply(0, "ERROR:SERVO_ATTACH"); return; }
  // Boot may physically move the gate. Calibrate with linkage unloaded.
  gate.write(neutral); movedAt = millis(); settling = true;
  reply(0, "READY:SERVO_V2:PROTOCOL=2"); report(0);
}

void loop() {
  checkLink();
  if (settling && uint32_t(millis() - movedAt) >= SETTLE_MS) {
    uint32_t id = activeId; settling = false; activeId = 0;
    // Timed settling only; no physical angle or egg-delivery feedback.
    reply(id, "OK:SERVO_DONE"); report(id);
  }
  for (int n = 0; n < 64 && Serial.available(); ++n) {
    checkLink();
    int result = reader.feed(Serial.read());
    if (result < 0) reply(0, "ERROR:INVALID_LINE");
    else if (result > 0) command(reader.buffer);
  }
}
