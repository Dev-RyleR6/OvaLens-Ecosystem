// Shared bounded ASCII protocol; no Arduino dependencies or allocation.
#pragma once
#include <stdint.h>
#include <stddef.h>
#include <errno.h>
#include <stdlib.h>
#include <string.h>
namespace ovalens {
constexpr uint32_t LINK_TIMEOUT_MS = 3000;
inline bool integer(const char *s, long low, long high, long &value) {
  if (!s || !*s || (*s != '-' && (*s < '0' || *s > '9'))) return false;
  errno = 0; char *end = nullptr;
  value = strtol(s, &end, 10);
  return errno != ERANGE && end != s && !*end && value >= low && value <= high;
}
inline bool envelope(char *line, uint32_t &id, char *&command) {
  id = 0; command = line;
  if (*line != '@') return true;
  char *space = strchr(line, ' ');
  if (!space || !space[1]) return false;
  *space = '\0'; long parsed;
  if (!integer(line + 1, 1, 2147483647L, parsed)) return false;
  id = static_cast<uint32_t>(parsed); command = space + 1; return true;
}
struct Reader {
  char buffer[96] = {};
  size_t length = 0;
  bool invalid = false;
  // 0: incomplete; 1: complete command; -1: malformed/overlong line.
  int feed(char c) {
    if (c == '\r') return 0;
    if (c == '\n') {
      buffer[length] = '\0'; int result = invalid ? -1 : (length ? 1 : 0);
      length = 0; invalid = false; return result;
    }
    if (c < 32 || c > 126) invalid = true;
    else if (!invalid && length < sizeof(buffer) - 1) buffer[length++] = c;
    else invalid = true;
    return 0;
  }
};
inline bool expired(uint32_t now, uint32_t last) {
  return static_cast<uint32_t>(now - last) >= LINK_TIMEOUT_MS;
}
}
