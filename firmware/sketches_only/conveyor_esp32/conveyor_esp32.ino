// TASK-NEW-FW-SAFE-01. Arduino-ESP32 3.x, classic ESP32, A4988.
// EN is wired LOW: stopping pulses does not disable holding current.
#include <Arduino.h>
#include "../protocol.h"

constexpr uint8_t STEP_PIN = 2, DIR_PIN = 4;
constexpr uint8_t IR_PIN = 14; // Active-low beam break; confirm wiring before upload.
constexpr int32_t POSITION_LIMIT = 10000000;
hw_timer_t *pulseTimer = nullptr;
portMUX_TYPE motionMux = portMUX_INITIALIZER_UNLOCKED;
volatile int32_t position = 0, target = 0;
volatile bool moving = false, stepHigh = false, watchdogTrip = false;
volatile uint32_t lastHeartbeat = 0;
volatile bool linkArmed = false;
volatile bool irArmed = false, irPending = false, irReport = false, irOverflow = false;
volatile bool irSeen = false;
volatile uint32_t lastIrAt = 0;
volatile int32_t irPosition = 0, irOffset = 0;
int32_t chamber = 0, output = 0;
bool chamberSet = false, outputSet = false, referenced = false;
bool faultLatched = true, awaitingCompletion = false;
uint32_t halfPeriodUs = 1000, activeId = 0, lastId = 0;
const char *state = "IDLE";
const char *faultCode = "STARTUP_REFERENCE_REQUIRED";
ovalens::Reader reader;

void prefix(uint32_t id) { if (id) Serial.printf("ID:%lu:", (unsigned long)id); }
void reply(uint32_t id, const char *message) { prefix(id); Serial.println(message); }

void ARDUINO_ISR_ATTR chamberIr() {
  portENTER_CRITICAL_ISR(&motionMux);
  uint32_t now = millis();
  if (moving && irArmed && !irPending && !irReport &&
      (!irSeen || uint32_t(now - lastIrAt) >= 600)) {
    irSeen = true; lastIrAt = now; irPosition = position; irPending = true;
  }
  portEXIT_CRITICAL_ISR(&motionMux);
}

void ARDUINO_ISR_ATTR pulseTick() {
  portENTER_CRITICAL_ISR(&motionMux);
  if (irPending) {
    int32_t direction = target >= position ? 1 : -1;
    int32_t stopAt = position + direction * irOffset;
    if ((direction > 0 && stopAt > target) || (direction < 0 && stopAt < target)) {
      irOverflow = true; target = position; moving = false;
    } else {
      target = stopAt; moving = target != position;
    }
    irPending = false; irReport = true; irArmed = false;
  }
  if (stepHigh) {
    digitalWrite(STEP_PIN, LOW); stepHigh = false;
    if (position == target) moving = false;
  } else if (moving) {
    if (uint32_t(millis() - lastHeartbeat) >= ovalens::LINK_TIMEOUT_MS) {
      moving = false; target = position; watchdogTrip = true;
    } else {
      digitalWrite(STEP_PIN, HIGH); stepHigh = true;
      position += target > position ? 1 : -1;
    }
  }
  portEXIT_CRITICAL_ISR(&motionMux);
}

void snapshot(int32_t &p, bool &busy) {
  portENTER_CRITICAL(&motionMux);
  p = position; busy = moving || stepHigh;
  portEXIT_CRITICAL(&motionMux);
}

void report(uint32_t id) {
  int32_t p; bool busy; snapshot(p, busy);
  prefix(id); Serial.println("IR_CAPABLE:1");
  prefix(id); Serial.printf("IR_ACTIVE:%d\n", digitalRead(IR_PIN) == LOW);
  prefix(id); Serial.printf("IR_OFFSET:%ld\n", long(irOffset));
  prefix(id); Serial.printf("POSITION:%ld\n", long(p));
  prefix(id); Serial.printf("BUSY:%d\n", busy ? 1 : 0);
  prefix(id); Serial.printf("CHAMBER:%ld\n", long(chamber));
  prefix(id); Serial.printf("OUTPUT:%ld\n", long(output));
  prefix(id); Serial.printf("STATIONS_VALID:%d\n", chamberSet && outputSet);
  prefix(id); Serial.printf("SPEED:%lu\n", (unsigned long)halfPeriodUs);
  prefix(id); Serial.printf("REFERENCE_VALID:%d\n", referenced);
  prefix(id); Serial.printf("FAULT:%s\n", faultLatched ? faultCode : "NONE");
  prefix(id); Serial.printf("ACTIVE_ID:%lu\n", (unsigned long)activeId);
  prefix(id); Serial.printf("LAST_ID:%lu\n", (unsigned long)lastId);
  reply(id, "AUTO:0");
  prefix(id); Serial.printf("STATE:%s\n", faultLatched ? "FAULT" : (busy ? "MOVING" : state));
}

void halt() {
  portENTER_CRITICAL(&motionMux);
  moving = false; target = position;
  irArmed = irPending = irReport = false;
  portEXIT_CRITICAL(&motionMux);
  // Finish an already issued HIGH pulse; never start another pulse.
  if (awaitingCompletion) reply(activeId, "ERROR:MOVE_CANCELLED");
  awaitingCompletion = false; activeId = 0; state = "HALTED";
}

void latchFault(const char *code) {
  halt(); faultLatched = true; faultCode = code;
  referenced = chamberSet = outputSet = false;
  reply(0, code); report(0);
}

void checkLink() {
  bool tripped; uint32_t last; bool armed;
  portENTER_CRITICAL(&motionMux);
  tripped = watchdogTrip; watchdogTrip = false;
  last = lastHeartbeat; armed = linkArmed;
  portEXIT_CRITICAL(&motionMux);
  if (tripped || (armed && ovalens::expired(millis(), last))) {
    portENTER_CRITICAL(&motionMux); linkArmed = false; portEXIT_CRITICAL(&motionMux);
    latchFault("ERROR:LINK_TIMEOUT");
  }
}

void heartbeat() {
  portENTER_CRITICAL(&motionMux);
  lastHeartbeat = millis(); linkArmed = true;
  portEXIT_CRITICAL(&motionMux);
}

void moveTo(int32_t destination, uint32_t id, bool watchIr = false) {
  int32_t p; bool busy; snapshot(p, busy);
  if (busy || awaitingCompletion) { reply(id, "ERROR:SYSTEM_BUSY"); return; }
  if (destination < -POSITION_LIMIT || destination > POSITION_LIMIT) {
    reply(id, "ERROR:POSITION_LIMIT"); return;
  }
  digitalWrite(DIR_PIN, destination >= p ? HIGH : LOW);
  timerStop(pulseTimer); timerWrite(pulseTimer, 0);
  portENTER_CRITICAL(&motionMux);
  target = destination; moving = destination != position;
  irArmed = watchIr; irPending = irReport = irOverflow = false;
  portEXIT_CRITICAL(&motionMux);
  activeId = id; awaitingCompletion = true; state = "MOVING";
  timerStart(pulseTimer);
  reply(id, "OK:MOVE_ACCEPTED"); report(id);
}

void command(char *line) {
  uint32_t id; char *cmd;
  if (!ovalens::envelope(line, id, cmd)) { reply(0, "ERROR:INVALID_ENVELOPE"); return; }
  // Stops always execute, including repeated IDs. Other tagged requests consume
  // an increasing ID even when rejected. Never retry a movement blindly.
  bool stop = !strcmp(cmd, "HALT") || !strcmp(cmd, "STOP");
  bool emergency = !strcmp(cmd, "ESTOP");
  if (stop || emergency) {
    if (id > lastId) lastId = id;
    if (emergency) latchFault("ERROR:EMERGENCY_STOP"); else halt();
    reply(id, emergency ? "OK:ESTOP" : "OK:HALTED"); report(id); return;
  }
  if (id && id <= lastId) { reply(id, "ERROR:ID_REUSED"); return; }
  if (id) lastId = id;
  if (!strcmp(cmd, "STATUS") || !strcmp(cmd, "PING") || !strcmp(cmd, "HELLO")) {
    heartbeat();
    if (!strcmp(cmd, "PING")) reply(id, "PONG:CONVEYOR");
    else if (!strcmp(cmd, "HELLO")) reply(id, "READY:CONVEYOR_V2:PROTOCOL=2");
    else report(id);
    return;
  }
  if (!id) { reply(0, "ERROR:COMMAND_ID_REQUIRED"); return; }
  if (!pulseTimer) { reply(id, "ERROR:TIMER_INIT"); return; }
  if (!linkArmed) { reply(id, "ERROR:HEARTBEAT_REQUIRED"); return; }
  int32_t p; bool busy; snapshot(p, busy);
  if (!strcmp(cmd, "ACK_FAULT")) {
    if (busy) { reply(id, "ERROR:SYSTEM_BUSY"); return; }
    faultLatched = false; faultCode = "NONE"; state = "IDLE";
    reply(id, "OK:FAULT_ACKNOWLEDGED"); report(id); return;
  }
  if (faultLatched) { reply(id, "ERROR:FAULT_LATCHED"); return; }
  if (busy || awaitingCompletion) { reply(id, "ERROR:SYSTEM_BUSY"); return; }
  if (!strcmp(cmd, "SETHOME")) {
    portENTER_CRITICAL(&motionMux); position = 0; target = 0; portEXIT_CRITICAL(&motionMux);
    referenced = true; chamberSet = outputSet = false; chamber = output = 0;
    state = "HOME"; reply(id, "OK:HOME_SET"); report(id); return;
  }
  long value;
  if (!strncmp(cmd, "IR_OFFSET:", 10) && ovalens::integer(cmd + 10, 0, 99999, value)) {
    irOffset = value; reply(id, "OK:IR_CONFIG"); report(id); return;
  }
  if (!strncmp(cmd, "INDEX:", 6) && ovalens::integer(cmd + 6, -100000, 100000, value)) {
    if (!referenced) { reply(id, "ERROR:REFERENCE_REQUIRED"); return; }
    if (value == 0) { reply(id, "ERROR:INVALID_COMMAND"); return; }
    moveTo(p + value, id, true); return;
  }
  if (!strncmp(cmd, "SPEED:", 6) && ovalens::integer(cmd + 6, 200, 5000, value)) {
    halfPeriodUs = value; timerAlarm(pulseTimer, halfPeriodUs, true, 0);
    reply(id, "OK:SPEED"); report(id); return;
  }
  // Manual alignment jog is allowed after acknowledgement before SETHOME.
  if (!strncmp(cmd, "JOG:", 4) && ovalens::integer(cmd + 4, -100000, 100000, value)) {
    moveTo(p + value, id); return;
  }
  bool home = !strcmp(cmd, "HOME"), setChamber = !strcmp(cmd, "SETCHAMBER");
  bool setOutput = !strcmp(cmd, "SETOUTPUT"), toChamber = !strcmp(cmd, "GOTO:CHAMBER");
  bool toOutput = !strcmp(cmd, "GOTO:OUTPUT");
  bool test = !strncmp(cmd, "TEST:", 5) && ovalens::integer(cmd + 5, 1, 100000, value);
  if (!(home || setChamber || setOutput || toChamber || toOutput || test)) {
    reply(id, "ERROR:INVALID_COMMAND"); return;
  }
  if (!referenced) { reply(id, "ERROR:REFERENCE_REQUIRED"); return; }
  if (home) { moveTo(0, id); return; }
  if (setChamber || setOutput) {
    if (setChamber) { chamber = p; chamberSet = true; }
    else { output = p; outputSet = true; }
    reply(id, "OK:STATION_SET"); report(id); return;
  }
  if (toChamber || toOutput) {
    if (!(toChamber ? chamberSet : outputSet)) { reply(id, "ERROR:STATION_NOT_SET"); return; }
    moveTo(toChamber ? chamber : output, id); return;
  }
  if (p != 0) { reply(id, "ERROR:TEST_REQUIRES_HOME"); return; }
  moveTo(value, id);
}

void setup() {
  pinMode(STEP_PIN, OUTPUT); digitalWrite(STEP_PIN, LOW);
  pinMode(DIR_PIN, OUTPUT); digitalWrite(DIR_PIN, LOW);
  pinMode(IR_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(IR_PIN), chamberIr, FALLING);
  Serial.begin(115200);
  reply(0, "BOOT:CONVEYOR_V2");
  pulseTimer = timerBegin(1000000);
  if (!pulseTimer) { faultCode = "TIMER_INIT"; reply(0, "ERROR:TIMER_INIT"); return; }
  timerAttachInterrupt(pulseTimer, &pulseTick);
  timerAlarm(pulseTimer, halfPeriodUs, true, 0);
  reply(0, "READY:CONVEYOR_V2:PROTOCOL=2"); report(0);
}

void loop() {
  checkLink();
  bool event, overflow; int32_t eventPosition;
  portENTER_CRITICAL(&motionMux);
  event = irReport; irReport = false;
  overflow = irOverflow; irOverflow = false; eventPosition = irPosition;
  portEXIT_CRITICAL(&motionMux);
  if (event) {
    prefix(activeId); Serial.printf("EVENT:IR:%ld\n", long(eventPosition));
  }
  if (overflow) latchFault("ERROR:IR_OFFSET_EXCEEDS_MOVE");
  int32_t p; bool busy; snapshot(p, busy);
  if (awaitingCompletion && !busy) {
    uint32_t id = activeId;
    awaitingCompletion = false; activeId = 0; state = "IDLE";
    irArmed = false;
    reply(id, "OK:MOVE_DONE"); report(id);
  }
  for (int n = 0; n < 64 && Serial.available(); ++n) {
    checkLink();
    int result = reader.feed(Serial.read());
    if (result < 0) reply(0, "ERROR:INVALID_LINE");
    else if (result > 0) command(reader.buffer);
  }
}
