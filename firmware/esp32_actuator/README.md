# OvaLens ESP32 Conveyor Actuator & Optical Candling Controller

Firmware for the ESP32 microcontroller controlling the automated duck egg sorting gate and optical trigger sensor for the OvaLens Capstone system.

---

## 📌 Hardware Pinout & Wiring

| Component | ESP32 GPIO Pin | Function | Notes |
| :--- | :--- | :--- | :--- |
| **Optical IR Sensor (TCRT5000 / E18-D80NK)** | **GPIO 14** | Interrupt Trigger Input (Active LOW) | Internal pull-up enabled; 600ms hardware debounce |
| **Servo / Solenoid Kicker (MG996R)** | **GPIO 18** | Hardware PWM Output | 50Hz LEDC hardware timer |
| **Candling LED Lamp (10W Cree)** | **GPIO 23** | MOSFET Gate PWM | 0–255 software brightness control |
| **Status Diagnostic LED** | **GPIO 2** | Blue Onboard Indicator | Blinks on egg trigger & servo action |

---

## ⚡ Serial Command Protocol (115200 Baud)

| Serial Command | Microcontroller Response | Description |
| :--- | :--- | :--- |
| `CMD:PING` | `RESP:PONG` | Connection heartbeat |
| `CMD:EJECT:<delay_ms>:<pulse_ms>` | `RESP:ACK_SCHEDULED:<delay_ms>` | Schedules a delayed ejection stroke ($\Delta t = D/v$) |
| `CMD:EJECT_NOW` | `RESP:ACK_EJECT_NOW` | Fires servo immediately (manual override) |
| `CMD:LIGHT:<0-255>` | `RESP:ACK_LIGHT:<val>` | Sets candling lamp PWM brightness |
| `CMD:STATUS` | `RESP:STATUS:OPTICAL=...,SERVO=...` | Returns current sensor and actuator state |
| *(Hardware Event)* | `EVENT:EGG_DETECTED` | Emitted automatically when an egg trips the optical sensor |
