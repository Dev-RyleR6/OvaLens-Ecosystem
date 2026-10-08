#include <Arduino.h>
#include "../protocol.h"
constexpr uint8_t RELAY_PIN = 27;
constexpr uint32_t AUTO_OFF_TIMEOUT_MS = 15000;
Protocol protocol("LIGHT_CONTROLLER");
bool lightOn = false;
uint32_t lightAt = 0;
void off() { lightOn = false; digitalWrite(RELAY_PIN, LOW); }
void report(uint32_t id) {
  prefix(id); Serial.printf("LIGHT:%d\n", lightOn);
  prefix(id); Serial.println("BUSY:0"); protocol.fields(id);
  prefix(id); Serial.printf("STATE:%s\n", protocol.fault ? "FAULT" : lightOn ? "ON" : "OFF");
}
void latchFault(const char *reason) { off(); protocol.fault = true; protocol.faultCode = reason; report(0); }
void command(char *line) {
  uint32_t id; char *cmd;
  if (!ovalens::envelope(line, id, cmd)) { reply(0, "ERROR:INVALID_ENVELOPE"); return; }
  if (isStop(cmd) || (!id && (!strcmp(cmd, "LIGHT_OFF") || !strcmp(cmd, "OFF")))) {
    if (id > protocol.lastId) protocol.lastId = id;
    latchFault("EMERGENCY_STOP"); reply(id, "OK:LIGHT_OFF"); return;
  }
  if (!protocol.consume(id)) return;
  if (protocol.read(cmd, id)) { report(id); return; }
  if (!protocol.authorize(id)) return;
  if (!strcmp(cmd, "ACK_FAULT")) {
    protocol.fault = false; reply(id, "OK:FAULT_ACKNOWLEDGED"); report(id); return;
  }
  // Off remains available during a fault; it cannot restart transport.
  if (!strcmp(cmd, "LIGHT_OFF") || !strcmp(cmd, "OFF")) {
    off(); reply(id, "OK:LIGHT_OFF"); report(id); return;
  }
  if (!protocol.healthy(id)) return;
  if (!strcmp(cmd, "LIGHT_ON") || !strcmp(cmd, "ON")) {
    digitalWrite(RELAY_PIN, HIGH); lightOn = true; lightAt = millis();
    reply(id, "OK:LIGHT_ON"); report(id); return;
  }
  reply(id, "ERROR:INVALID_COMMAND");
}
void setup() {
  digitalWrite(RELAY_PIN, LOW); pinMode(RELAY_PIN, OUTPUT); off();
  Serial.begin(115200); protocol.boot(); report(0);
}
void loop() {
  if (protocol.expired()) latchFault("LINK_TIMEOUT");
  if (lightOn && uint32_t(millis() - lightAt) >= AUTO_OFF_TIMEOUT_MS) {
    latchFault("LIGHT_AUTO_OFF_TIMEOUT"); reply(0, "WARN:AUTO_OFF_TIMEOUT");
  }
  for (int n = 0; n < 64 && Serial.available(); ++n) {
    if (protocol.expired()) latchFault("LINK_TIMEOUT");
    int result = protocol.reader.feed(Serial.read());
    if (result < 0) reply(0, "ERROR:INVALID_LINE");
    else if (result > 0) command(protocol.reader.buffer);
  }
}
