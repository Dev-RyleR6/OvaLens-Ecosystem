#include "Arduino.h"
#include <iostream>
#ifdef BOARD_CONVEYOR
#include "../../../firmware/sketches_only/conveyor_esp32/conveyor_esp32.ino"
#else
#include "ESP32Servo.h"
#include "../../../firmware/sketches_only/servo_esp32/servo_esp32.ino"
#endif

int main(int argc, char **argv) {
  if (argc > 1 && std::string(argv[1]) == "fail-init") {
#ifdef BOARD_CONVEYOR
    failTimer = true;
#else
    failServo = true;
#endif
  }
  setup();
  std::string line;
  while (std::getline(std::cin, line)) {
    if (line.rfind("CLOCK ", 0) == 0) {
      fakeMillis = static_cast<uint32_t>(std::stoull(line.substr(6)));
#ifdef BOARD_CONVEYOR
      if (pulseTimer && timer.running) pulseTick();
#endif
      loop();
    } else if (line.rfind("TICKS ", 0) == 0) {
#ifdef BOARD_CONVEYOR
      int count = std::stoi(line.substr(6));
      for (int i = 0; i < count; ++i) {
        if (pulseTimer && timer.running) pulseTick();
        loop();
      }
#endif
    } else if (line.rfind("SEND ", 0) == 0) {
      for (char c : line.substr(5)) Serial.input.push_back(c);
      Serial.input.push_back('\n');
      while (Serial.available()) loop();
      loop();
    }
  }
}
