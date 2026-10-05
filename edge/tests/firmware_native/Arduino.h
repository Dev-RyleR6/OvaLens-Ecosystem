// Host-only Arduino shim: exercises actual sketch logic without GPIO hardware.
#pragma once
#include <cstdint>
#include <cstdio>
#include <cstdarg>
#include <deque>
#include <string>
#define ARDUINO_ISR_ATTR
#define OUTPUT 1
#define HIGH 1
#define LOW 0
using portMUX_TYPE = int;
#define portMUX_INITIALIZER_UNLOCKED 0
#define portENTER_CRITICAL(x) ((void)(x))
#define portEXIT_CRITICAL(x) ((void)(x))
#define portENTER_CRITICAL_ISR(x) ((void)(x))
#define portEXIT_CRITICAL_ISR(x) ((void)(x))
inline uint32_t fakeMillis = 0;
inline int pinValues[64] = {};
inline uint32_t millis() { return fakeMillis; }
inline void pinMode(int, int) {}
inline void digitalWrite(int pin, int value) { pinValues[pin] = value; }
struct hw_timer_t { bool running = true; };
inline hw_timer_t timer;
inline bool failTimer = false;
inline hw_timer_t *timerBegin(uint32_t) { return failTimer ? nullptr : &timer; }
inline void timerAttachInterrupt(hw_timer_t *, void (*)()) {}
inline void timerAlarm(hw_timer_t *, uint32_t, bool, uint64_t) {}
inline void timerStop(hw_timer_t *t) { t->running = false; }
inline void timerStart(hw_timer_t *t) { t->running = true; }
inline void timerWrite(hw_timer_t *, uint64_t) {}
struct SerialMock {
  std::deque<char> input;
  void begin(int) {}
  int available() { return static_cast<int>(input.size()); }
  char read() { char c = input.front(); input.pop_front(); return c; }
  void println(const char *s) { std::printf("%s\n", s); }
  void printf(const char *format, ...) {
    va_list args; va_start(args, format); std::vprintf(format, args); va_end(args);
  }
};
inline SerialMock Serial;
