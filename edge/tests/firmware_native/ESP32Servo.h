#pragma once
inline bool failServo = false;
struct ESP32PWM {
  static void allocateTimer(int) {}
};
struct Servo {
  bool connected = false;
  int requested = 90;
  void setPeriodHertz(int) {}
  void attach(int, int, int) { connected = !failServo; }
  bool attached() { return connected; }
  void write(int value) { requested = value; }
};
