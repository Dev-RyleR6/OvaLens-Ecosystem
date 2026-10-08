// A4988 STEP2 DIR4. Egg board GPIO25 -> pause GPIO27; HIGH/broken wire holds.
#include <Arduino.h>
#include "../protocol.h"
constexpr uint8_t STEP_PIN = 2, DIR_PIN = 4, PAUSE_PIN = 27;
constexpr int32_t POSITION_LIMIT = 10000000;
constexpr bool INVERT_DIR = true;
Protocol protocol("CONVEYOR");
hw_timer_t *pulseTimer = nullptr;
portMUX_TYPE motionMux = portMUX_INITIALIZER_UNLOCKED;
volatile int32_t position = 0, target = 0;
volatile bool moving = false, stepHigh = false, pauseStop = false, watchdogTrip = false;
volatile uint32_t heartbeatAt = 0;
uint32_t halfPeriodUs = 3000, activeId = 0;
bool awaitingCompletion = false, referenced = false;

void ARDUINO_ISR_ATTR pulseTick() {
  portENTER_CRITICAL_ISR(&motionMux);
  if (stepHigh) {
    digitalWrite(STEP_PIN, LOW); stepHigh = false;
    if (position == target) moving = false;
  } else if (moving) {
    if (uint32_t(millis() - heartbeatAt) >= ovalens::LINK_TIMEOUT_MS) {
      moving = false; target = position; watchdogTrip = true;
    } else if (digitalRead(PAUSE_PIN) == HIGH) {
      moving = false; target = position; pauseStop = true;
    } else {
      digitalWrite(STEP_PIN, HIGH); stepHigh = true;
      position += target > position ? 1 : -1;
    }
  }
  portEXIT_CRITICAL_ISR(&motionMux);
}
void snapshot(int32_t &p, bool &busy) {
  portENTER_CRITICAL(&motionMux); p = position; busy = moving || stepHigh; portEXIT_CRITICAL(&motionMux);
}
void report(uint32_t id) {
  int32_t p; bool busy; snapshot(p, busy);
  prefix(id); Serial.printf("POSITION:%ld\n", long(p));
  prefix(id); Serial.printf("SPEED:%lu\n", (unsigned long)halfPeriodUs);
  prefix(id); Serial.printf("PAUSED:%d\n", digitalRead(PAUSE_PIN) == HIGH);
  prefix(id); Serial.printf("BUSY:%d\n", busy);
  prefix(id); Serial.printf("REFERENCE_VALID:%d\n", referenced);
  prefix(id); Serial.printf("ACTIVE_ID:%lu\n", (unsigned long)activeId);
  protocol.fields(id);
  prefix(id); Serial.printf("STATE:%s\n", protocol.fault ? "FAULT" : busy ? "MOVING" : digitalRead(PAUSE_PIN) == HIGH ? "PAUSED" : "IDLE");
}
void latchFault(const char *reason) {
  portENTER_CRITICAL(&motionMux); moving = false; target = position; pauseStop = false; portEXIT_CRITICAL(&motionMux);
  if (activeId) reply(activeId, "ERROR:MOVE_CANCELLED");
  activeId = 0; awaitingCompletion = false; referenced = false;
  protocol.fault = true; protocol.faultCode = reason; report(0);
}
void checkLink() {
  bool trip;
  portENTER_CRITICAL(&motionMux); trip = watchdogTrip; watchdogTrip = false; portEXIT_CRITICAL(&motionMux);
  if (trip || protocol.expired()) { protocol.armed = false; latchFault("LINK_TIMEOUT"); }
}
void moveTo(int32_t destination, uint32_t id) {
  int32_t p; bool busy; snapshot(p, busy);
  if (busy || awaitingCompletion) { reply(id, "ERROR:SYSTEM_BUSY"); return; }
  if (digitalRead(PAUSE_PIN) == HIGH) { reply(id, "ERROR:PAUSE_ACTIVE"); return; }
  if (destination < -POSITION_LIMIT || destination > POSITION_LIMIT) { reply(id, "ERROR:POSITION_LIMIT"); return; }
  bool forward = destination >= p;
  digitalWrite(DIR_PIN, (INVERT_DIR ? !forward : forward) ? HIGH : LOW);
  timerStop(pulseTimer); timerWrite(pulseTimer, 0);
  portENTER_CRITICAL(&motionMux);
  target = destination; moving = destination != position; pauseStop = false;
  portEXIT_CRITICAL(&motionMux);
  activeId = id; awaitingCompletion = true; timerStart(pulseTimer);
  reply(id, "OK:MOVE_ACCEPTED"); report(id);
}
void command(char *line) {
  uint32_t id; char *cmd;
  if (!ovalens::envelope(line, id, cmd)) { reply(0, "ERROR:INVALID_ENVELOPE"); return; }
  if (isStop(cmd)) {
    if (id > protocol.lastId) protocol.lastId = id;
    latchFault("EMERGENCY_STOP"); reply(id, "OK:ESTOP"); return;
  }
  if (!protocol.consume(id)) return;
  if (protocol.read(cmd, id)) {
    portENTER_CRITICAL(&motionMux); heartbeatAt = millis(); portEXIT_CRITICAL(&motionMux);
    report(id); return;
  }
  if (!protocol.authorize(id)) return;
  if (!pulseTimer) { reply(id, "ERROR:TIMER_INIT"); return; }
  int32_t p; bool busy; snapshot(p, busy);
  if (busy || awaitingCompletion) { reply(id, "ERROR:SYSTEM_BUSY"); return; }
  if (!strcmp(cmd, "ACK_FAULT")) {
    protocol.fault = false; reply(id, "OK:FAULT_ACKNOWLEDGED"); report(id); return;
  }
  if (!protocol.healthy(id)) return;
  if (!strcmp(cmd, "SETHOME")) {
    portENTER_CRITICAL(&motionMux); position = target = 0; portEXIT_CRITICAL(&motionMux);
    referenced = true; reply(id, "OK:HOME_SET"); report(id); return;
  }
  long value;
  if (!strncmp(cmd, "SPEED:", 6) && ovalens::integer(cmd + 6, 200, 5000, value)) {
    halfPeriodUs = value; timerAlarm(pulseTimer, halfPeriodUs, true, 0);
    reply(id, "OK:SPEED"); report(id); return;
  }
  if (!strncmp(cmd, "JOG:", 4) && ovalens::integer(cmd + 4, -100000, 100000, value) && value) {
    moveTo(p + value, id); return;
  }
  if (!strncmp(cmd, "ADVANCE:", 8) && ovalens::integer(cmd + 8, -100000, 100000, value) && value) {
    if (!referenced) { reply(id, "ERROR:REFERENCE_REQUIRED"); return; }
    moveTo(p + value, id); return;
  }
  reply(id, "ERROR:INVALID_COMMAND");
}
void setup() {
  pinMode(STEP_PIN, OUTPUT); digitalWrite(STEP_PIN, LOW);
  pinMode(DIR_PIN, OUTPUT); digitalWrite(DIR_PIN, INVERT_DIR ? HIGH : LOW);
  pinMode(PAUSE_PIN, INPUT_PULLUP);
  Serial.begin(115200); protocol.boot();
  pulseTimer = timerBegin(1000000);
  if (!pulseTimer) { protocol.faultCode = "TIMER_INIT"; report(0); return; }
  timerAttachInterrupt(pulseTimer, &pulseTick); timerAlarm(pulseTimer, halfPeriodUs, true, 0); report(0);
}
void loop() {
  checkLink();
  int32_t p; bool busy; snapshot(p, busy);
  if (awaitingCompletion && !busy) {
    uint32_t id = activeId; activeId = 0; awaitingCompletion = false;
    bool stopped;
    portENTER_CRITICAL(&motionMux); stopped = pauseStop; pauseStop = false; portEXIT_CRITICAL(&motionMux);
    reply(id, stopped ? "OK:EGG_STOPPED" : "OK:MOVE_DONE"); report(id);
  }
  for (int n = 0; n < 64 && Serial.available(); ++n) {
    checkLink(); int result = protocol.reader.feed(Serial.read());
    if (result < 0) reply(0, "ERROR:INVALID_LINE");
    else if (result > 0) command(protocol.reader.buffer);
  }
}
