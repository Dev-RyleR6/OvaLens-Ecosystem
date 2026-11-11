/*
 * OvaLens Unified Single-ESP32 Hardware Diagnostic Test
 * Board: ESP32 Dev Module
 * Baud Rate: 115200
 * 
 * Pinout:
 *   - Stepper STEP:   GPIO 16
 *   - Stepper DIR:    GPIO 4
 *   - Stepper ENABLE: GPIO 17 (LOW = Enabled, HIGH = Disabled/Silent)
 *   - IR Sensor:      GPIO 26 (Active LOW)
 *   - Servo Gate:     GPIO 32 (PWM)
 *   - Lamp Relay:     GPIO 27 (Active HIGH)
 *   - Status LED:     GPIO 2  (Onboard)
 */

#include <Arduino.h>
#include <ESP32Servo.h>

// ==========================================
// PIN CONFIGURATION
// ==========================================
const uint8_t PIN_STEP   = 16;
const uint8_t PIN_DIR    = 4;
const uint8_t PIN_ENABLE = 17; // Auto-sleep for silent idle!
const uint8_t PIN_IR     = 26;
const uint8_t PIN_SERVO  = 32;
const uint8_t PIN_LAMP   = 27;
const uint8_t PIN_LED    = 2;

Servo gateServo;
bool lampState = false;

// Print Interactive Test Menu
void printMenu() {
  Serial.println();
  Serial.println("==============================================");
  Serial.println("      OvaLens Single-ESP32 Hardware Test      ");
  Serial.println("==============================================");
  Serial.println(" [1] Toggle Lamp ON / OFF        (GPIO 27)");
  Serial.println(" [2] Test Servo Sorting Gate     (GPIO 32)");
  Serial.println(" [3] Live IR Sensor Test (10s)   (GPIO 26)");
  Serial.println(" [4] Jog Stepper Forward (100st) (GPIO 16, 4, 17)");
  Serial.println(" [5] Jog Stepper Reverse (100st) (GPIO 16, 4, 17)");
  Serial.println(" [?] Show this Menu again");
  Serial.println("==============================================");
  Serial.print("Enter your choice (1-5): ");
}

void setup() {
  Serial.begin(115200);
  while (!Serial && millis() < 2000);

  // Configure Pins
  pinMode(PIN_STEP, OUTPUT);
  pinMode(PIN_DIR, OUTPUT);
  pinMode(PIN_ENABLE, OUTPUT);
  pinMode(PIN_LAMP, OUTPUT);
  pinMode(PIN_LED, OUTPUT);
  pinMode(PIN_IR, INPUT_PULLUP);

  // Default initial states
  digitalWrite(PIN_STEP, LOW);
  digitalWrite(PIN_DIR, LOW);
  digitalWrite(PIN_ENABLE, HIGH); // HIGH = Disable coils (Silent idle!)
  digitalWrite(PIN_LAMP, LOW);
  digitalWrite(PIN_LED, LOW);

  // Configure Servo
  ESP32PWM::allocateTimer(0);
  gateServo.setPeriodHertz(50);
  gateServo.attach(PIN_SERVO, 500, 2400);
  gateServo.write(90); // Idle neutral position

  delay(200);
  Serial.println("\n[INIT] All pins configured with Silent Idle enabled.");
  printMenu();
}

// 1. Toggle Candling Lamp
void testLamp() {
  lampState = !lampState;
  digitalWrite(PIN_LAMP, lampState ? HIGH : LOW);
  digitalWrite(PIN_LED, lampState ? HIGH : LOW);
  
  Serial.println();
  Serial.print(">>> Lamp is now: ");
  if (lampState) {
    Serial.println("ON [HIGH]");
  } else {
    Serial.println("OFF [LOW]");
  }
}

// 2. Test Servo Movement
void testServo() {
  Serial.println();
  Serial.println(">>> Testing Servo Sorting Gate...");
  
  Serial.println(" -> Moving to Neutral (90 deg)...");
  gateServo.write(90);
  delay(1000);

  Serial.println(" -> Moving to Fertile Accept (180 deg)...");
  gateServo.write(180);
  delay(1000);

  Serial.println(" -> Moving to Infertile Reject (50 deg)...");
  gateServo.write(50);
  delay(1000);

  Serial.println(" -> Returning to Neutral (90 deg)...");
  gateServo.write(90);
  delay(500);

  Serial.println(">>> Servo Test Complete!");
}

// 3. Live IR Sensor Monitor
void testIRSensor() {
  Serial.println();
  Serial.println(">>> Starting 10-Second Live IR Sensor Readout.");
  Serial.println(">>> Wave your hand in front of the sensor now!");
  
  unsigned long endTime = millis() + 10000;
  int lastState = -1;

  while (millis() < endTime) {
    int currentState = digitalRead(PIN_IR);
    if (currentState != lastState) {
      lastState = currentState;
      if (currentState == LOW) {
        Serial.println(" [EVENT] EGG / OBJECT DETECTED! (Pin 26 = LOW)");
        digitalWrite(PIN_LED, HIGH);
      } else {
        Serial.println(" [EVENT] BEAM CLEAR (Pin 26 = HIGH)");
        digitalWrite(PIN_LED, LOW);
      }
    }
    delay(20);
  }
  
  digitalWrite(PIN_LED, lampState ? HIGH : LOW);
  Serial.println(">>> IR Sensor Test Finished.");
}

// 4 & 5. Jog Stepper Motor with Auto-Enable/Disable
void testStepper(bool forward, int steps = 100) {
  Serial.println();
  Serial.print(">>> Stepping Motor ");
  Serial.print(forward ? "FORWARD " : "REVERSE ");
  Serial.print(steps);
  Serial.println(" steps...");

  // Wake up driver (LOW = Enabled)
  digitalWrite(PIN_ENABLE, LOW);
  delay(5); // Allow charge pump to stabilize

  digitalWrite(PIN_DIR, forward ? HIGH : LOW);
  delayMicroseconds(50);

  // 100 steps with 2000us pulse half-period
  for (int i = 0; i < steps; i++) {
    digitalWrite(PIN_STEP, HIGH);
    delayMicroseconds(2000);
    digitalWrite(PIN_STEP, LOW);
    delayMicroseconds(2000);
  }

  // Sleep driver (HIGH = Disabled / Silent Idle)
  delay(10);
  digitalWrite(PIN_ENABLE, HIGH);

  Serial.println(">>> Stepper Move Done! Coils silenced.");
}

void loop() {
  if (Serial.available() > 0) {
    char key = Serial.read();
    
    // Ignore newline / carriage return
    if (key == '\r' || key == '\n') return;

    switch (key) {
      case '1':
        testLamp();
        break;
      case '2':
        testServo();
        break;
      case '3':
        testIRSensor();
        break;
      case '4':
        testStepper(true, 100);
        break;
      case '5':
        testStepper(false, 100);
        break;
      case '?':
      case 'h':
      case 'H':
        printMenu();
        return;
      default:
        Serial.print("\n[?] Unknown key '");
        Serial.print(key);
        Serial.println("'. Enter 1, 2, 3, 4, 5, or ?");
        break;
    }

    Serial.print("\nEnter choice (1-5 or ?): ");
  }
}
