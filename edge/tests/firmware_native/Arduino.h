// Host-only Arduino shim: exercises actual sketch logic without GPIO hardware.
#pragma once
#include <stdint.h>
#include <stdio.h>
#include <stdarg.h>
#define ARDUINO_ISR_ATTR
#define OUTPUT 1
#define HIGH 1
#define LOW 0
#define INPUT_PULLUP 2
#define INPUT 0
#define INPUT_PULLDOWN 4
#define FALLING 3
using portMUX_TYPE = int;
#define portMUX_INITIALIZER_UNLOCKED 0
#define portENTER_CRITICAL(x) ((void)(x))
#define portEXIT_CRITICAL(x) ((void)(x))
#define portENTER_CRITICAL_ISR(x) ((void)(x))
#define portEXIT_CRITICAL_ISR(x) ((void)(x))
inline uint32_t fakeMillis = 0;
inline int pinValues[64] = {};
inline uint32_t millis() { return fakeMillis; }
inline void pinMode(int pin, int mode) {
  if (mode == INPUT_PULLUP) pinValues[pin] = HIGH;
  else if (mode == INPUT_PULLDOWN) pinValues[pin] = LOW;
}
inline int digitalRead(int pin) { return pinValues[pin]; }
inline int digitalPinToInterrupt(int pin) { return pin; }
inline void attachInterrupt(int, void (*)(), int) {}
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
  struct ByteQueue {
    char bytes[65536] = {};
    unsigned head = 0, tail = 0;
    unsigned size() const { return tail - head; }
    void push_back(char c) { bytes[(tail++) % sizeof(bytes)] = c; }
    char front() const { return bytes[head % sizeof(bytes)]; }
    void pop_front() { ++head; }
  } input;
  void begin(int) {}
  int available() { return static_cast<int>(input.size()); }
  char read() { char c = input.front(); input.pop_front(); return c; }
  void println(const char *s) { ::printf("%s\n", s); }
  void printf(const char *format, ...) {
    va_list args; va_start(args, format); ::vprintf(format, args); va_end(args);
  }
};
inline SerialMock Serial;
