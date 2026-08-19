/*
 * OvaLens ESP32 Conveyor Actuator & Optical Candling Controller
 * Project: Foundation University OvaLens Capstone System
 * Target Board: ESP32 Dev Module (WROOM-32 / ESP32-S3)
 * Baud Rate: 115200
 */

#include <Arduino.h>
#include <ESP32Servo.h>

// ==============================================================================
// PIN DEFINITIONS
// ==============================================================================
#define PIN_OPTICAL_TRIGGER   14   // Optical IR proximity sensor (Active LOW / Interrupt)
#define PIN_SERVO_PWM         18   // High-Torque Servo / Solenoid (MG996R)
#define PIN_CANDLING_MOSFET   23   // 10W Cree LED Candling Light (PWM control)
#define PIN_STATUS_LED         2   // Onboard Blue Status LED

// ==============================================================================
// CONFIGURATION & DEBOUNCE
// ==============================================================================
#define SENSOR_DEBOUNCE_MS   600   // Optical sensor lockout window (prevents multi-trigger on 1 egg)
#define DEFAULT_PULSE_MS     250   // Default servo stroke duration
#define SERVO_IDLE_ANGLE       0   // Pass-through position (degrees)
#define SERVO_EJECT_ANGLE     60   // Reject/cull position (degrees)

// ==============================================================================
// GLOBAL STATE & TIMERS
// ==============================================================================
Servo ejectServo;
volatile unsigned long lastTriggerTime = 0;
volatile bool opticalTriggerFlag = false;

// Delayed actuation state
bool pendingActuation = false;
unsigned long scheduledActuationTime = 0;
unsigned long servoResetTime = 0;
bool servoActive = false;
unsigned int activePulseDuration = DEFAULT_PULSE_MS;

// ==============================================================================
// HARDWARE INTERRUPT SERVICE ROUTINE (ISR)
// ==============================================================================
void IRAM_ATTR onOpticalSensorTrigger() {
  unsigned long now = millis();
  if (now - lastTriggerTime > SENSOR_DEBOUNCE_MS) {
    lastTriggerTime = now;
    opticalTriggerFlag = true;
  }
}

// ==============================================================================
// SETUP
// ==============================================================================
void setup() {
  Serial.begin(115200);
  while (!Serial && millis() < 2000);

  // Pin Modes
  pinMode(PIN_OPTICAL_TRIGGER, INPUT_PULLUP);
  pinMode(PIN_STATUS_LED, OUTPUT);
  pinMode(PIN_CANDLING_MOSFET, OUTPUT);

  // Default Candling Light (Full ON)
  analogWrite(PIN_CANDLING_MOSFET, 255);

  // Attach Hardware Servo
  ESP32PWM::allocateTimer(0);
  ejectServo.setPeriodHertz(50); // Standard 50Hz servo
  ejectServo.attach(PIN_SERVO_PWM, 500, 2400);
  ejectServo.write(SERVO_IDLE_ANGLE);

  // Attach Optical Interrupt
  attachInterrupt(digitalPinToInterrupt(PIN_OPTICAL_TRIGGER), onOpticalSensorTrigger, FALLING);

  // Boot Blink
  digitalWrite(PIN_STATUS_LED, HIGH);
  delay(200);
  digitalWrite(PIN_STATUS_LED, LOW);

  Serial.println("STATUS:READY:OVALENS_ESP32_ACTUATOR_V2.0");
}

// ==============================================================================
// MAIN LOOP
// ==============================================================================
void loop() {
  unsigned long currentMillis = millis();

  // 1. Process Hardware Optical Sensor Interrupt
  if (opticalTriggerFlag) {
    opticalTriggerFlag = false;
    Serial.println("EVENT:EGG_DETECTED");
    digitalWrite(PIN_STATUS_LED, HIGH);
  }

  // 2. Process Delayed Actuation (Travel Time Δt)
  if (pendingActuation && currentMillis >= scheduledActuationTime) {
    pendingActuation = false;
    ejectServo.write(SERVO_EJECT_ANGLE);
    servoActive = true;
    servoResetTime = currentMillis + activePulseDuration;
    Serial.println("STATUS:EJECT_FIRED");
  }

  // 3. Reset Servo Back to Idle Position
  if (servoActive && currentMillis >= servoResetTime) {
    servoActive = false;
    ejectServo.write(SERVO_IDLE_ANGLE);
    digitalWrite(PIN_STATUS_LED, LOW);
    Serial.println("STATUS:SERVO_IDLE");
  }

  // 4. Process Incoming Serial Commands from Edge App
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if (cmd == "CMD:PING") {
      Serial.println("RESP:PONG");
    }
    else if (cmd.startsWith("CMD:EJECT:")) {
      // Format: CMD:EJECT:<delay_ms>:<pulse_ms>
      int firstColon = cmd.indexOf(':', 4);
      int secondColon = cmd.indexOf(':', firstColon + 1);

      unsigned long delayMs = 0;
      unsigned int pulseMs = DEFAULT_PULSE_MS;

      if (secondColon != -1) {
        delayMs = cmd.substring(firstColon + 1, secondColon).toInt();
        pulseMs = cmd.substring(secondColon + 1).toInt();
      } else {
        delayMs = cmd.substring(firstColon + 1).toInt();
      }

      scheduledActuationTime = currentMillis + delayMs;
      activePulseDuration = pulseMs > 0 ? pulseMs : DEFAULT_PULSE_MS;
      pendingActuation = true;

      Serial.print("RESP:ACK_SCHEDULED:");
      Serial.println(delayMs);
    }
    else if (cmd == "CMD:EJECT_NOW") {
      // Immediate manual override ejection
      ejectServo.write(SERVO_EJECT_ANGLE);
      servoActive = true;
      servoResetTime = currentMillis + DEFAULT_PULSE_MS;
      Serial.println("RESP:ACK_EJECT_NOW");
    }
    else if (cmd.startsWith("CMD:LIGHT:")) {
      // Format: CMD:LIGHT:<0-255>
      int val = cmd.substring(10).toInt();
      val = constrain(val, 0, 255);
      analogWrite(PIN_CANDLING_MOSFET, val);
      Serial.print("RESP:ACK_LIGHT:");
      Serial.println(val);
    }
    else if (cmd == "CMD:STATUS") {
      Serial.print("RESP:STATUS:OPTICAL=");
      Serial.print(digitalRead(PIN_OPTICAL_TRIGGER) == LOW ? "DETECTED" : "CLEAR");
      Serial.print(",SERVO=");
      Serial.println(servoActive ? "ACTIVE" : "IDLE");
    }
  }
}
