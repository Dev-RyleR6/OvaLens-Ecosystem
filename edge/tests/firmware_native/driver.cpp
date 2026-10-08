#include "Arduino.h"
#include <stdlib.h>
#include <string.h>
#ifdef BOARD_CONVEYOR
#include "../../../firmware/sketches_only/conveyor_esp32/conveyor_esp32.ino"
#else
#include "ESP32Servo.h"
#include "../../../firmware/sketches_only/servo_esp32/servo_esp32.ino"
#endif

int main(int argc, char **argv) {
  if (argc > 1 && !strcmp(argv[1], "fail-init")) {
#ifdef BOARD_CONVEYOR
    failTimer = true;
#else
    failServo = true;
#endif
  }
  setup();
  char line[65536];
  while (fgets(line, sizeof(line), stdin)) {
    line[strcspn(line, "\r\n")] = '\0';
    if (!strncmp(line, "CLOCK ", 6)) {
      fakeMillis = static_cast<uint32_t>(strtoull(line + 6, nullptr, 10));
#ifdef BOARD_CONVEYOR
      if (pulseTimer && timer.running) pulseTick();
#endif
      loop();
    } else if (!strcmp(line, "IR")) {
#ifdef BOARD_CONVEYOR
      pinValues[IR_PIN] = LOW; chamberIr();
#endif
    } else if (!strcmp(line, "IR_CLEAR")) {
#ifdef BOARD_CONVEYOR
      pinValues[IR_PIN] = HIGH;
#endif
    } else if (!strncmp(line, "TICKS ", 6)) {
#ifdef BOARD_CONVEYOR
      int count = atoi(line + 6);
      for (int i = 0; i < count; ++i) {
        if (pulseTimer && timer.running) pulseTick();
        loop();
      }
#endif
    } else if (!strncmp(line, "SEND ", 5)) {
      for (const char *c = line + 5; *c; ++c) Serial.input.push_back(*c);
      Serial.input.push_back('\n');
      while (Serial.available()) loop();
      loop();
    }
  }
}
