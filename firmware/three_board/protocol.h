// TASK-NEW-EDGE-3BOARD-01. Shared v3 envelope and fail-closed link guard.
#pragma once
#include "../sketches_only/protocol.h"

inline void prefix(uint32_t id) { if (id) Serial.printf("ID:%lu:", (unsigned long)id); }
inline void reply(uint32_t id, const char *message) { prefix(id); Serial.println(message); }

struct Protocol {
  const char *role;
  uint32_t lastId = 0, lastHeartbeat = 0;
  bool armed = false, fault = true;
  const char *faultCode = "STARTUP_ACK_REQUIRED";
  ovalens::Reader reader;
  explicit Protocol(const char *name): role(name) {}
  void boot() { Serial.printf("BOOT:%s_V3\nREADY:%s_V3:PROTOCOL=3\n", role, role); }
  bool consume(uint32_t id) {
    if (id && id <= lastId) { reply(id, "ERROR:ID_REUSED"); return false; }
    if (id) lastId = id;
    return true;
  }
  bool read(const char *cmd, uint32_t id) {
    if (strcmp(cmd, "PING") && strcmp(cmd, "HELLO") && strcmp(cmd, "STATUS")) return false;
    lastHeartbeat = millis(); armed = true;
    if (!strcmp(cmd, "PING")) { prefix(id); Serial.printf("PONG:%s\n", role); }
    if (!strcmp(cmd, "HELLO")) { prefix(id); Serial.printf("READY:%s_V3:PROTOCOL=3\n", role); }
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
  void fields(uint32_t id) {
    prefix(id); Serial.printf("FAULT:%s\n", fault ? faultCode : "NONE");
    prefix(id); Serial.printf("LAST_ID:%lu\n", (unsigned long)lastId);
  }
};

inline bool isStop(const char *cmd) {
  return !strcmp(cmd, "ESTOP") || !strcmp(cmd, "HALT") || !strcmp(cmd, "STOP");
}
