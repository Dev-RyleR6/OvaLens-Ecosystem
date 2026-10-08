#include "Arduino.h"
#include "ESP32Servo.h"
#include <stdlib.h>
#include <string.h>
#if defined(BOARD_CONVEYOR)
#include "../../../firmware/three_board/conveyor_esp32/conveyor_esp32.ino"
#elif defined(BOARD_EGG)
#include "../../../firmware/three_board/egg_controller_esp32/egg_controller_esp32.ino"
#else
#include "../../../firmware/three_board/light_controller_esp32/light_controller_esp32.ino"
#endif

int main(int argc, char **argv) {
  if (argc > 1 && !strcmp(argv[1], "fail-init")) {
#if defined(BOARD_CONVEYOR)
    failTimer = true;
#elif defined(BOARD_EGG)
    failServo = true;
#endif
  }
  setup();
  char line[65536];
  while (fgets(line, sizeof(line), stdin)) {
    line[strcspn(line, "\r\n")] = '\0';
    if (!strncmp(line, "CLOCK ", 6)) {
      fakeMillis = static_cast<uint32_t>(strtoull(line + 6, nullptr, 10));
      loop();
    } else if (!strncmp(line, "PIN ", 4)) {
      int pin, value;
      if (sscanf(line, "PIN %d %d", &pin, &value) == 2 && pin >= 0 && pin < 64) pinValues[pin] = value;
      loop();
    } else if (!strncmp(line, "TICKS ", 6)) {
#if defined(BOARD_CONVEYOR)
      int count = atoi(line + 6);
      for (int i = 0; i < count; ++i) { if (pulseTimer && timer.running) pulseTick(); loop(); }
#endif
    } else if (!strncmp(line, "SEND ", 5)) {
      for (const char *c = line + 5; *c; ++c) Serial.input.push_back(*c);
      Serial.input.push_back('\n');
      while (Serial.available()) loop();
      loop();
    }
  }
}
