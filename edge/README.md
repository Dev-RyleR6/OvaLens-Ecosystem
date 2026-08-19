# OvaLens Edge — Computer Vision Candling & Conveyor Controller

> **Subsystem**: `edge/`  
> **Platform**: Raspberry Pi 5 / Industrial Edge PC / Desktop  
> **License**: Apache License 2.0  

**OvaLens Edge** is an offline-first, real-time computer vision application designed to inspect duck eggs on a motorized conveyor, classify embryonic development using YOLOv8 ONNX FP16, and command millisecond-accurate mechanical sorting via an ESP32 microcontroller.

---

## 🌟 Key Subsystem Features

- **Decoupled Quad-Thread Concurrency**:
  - **Thread 1 (Camera Grabber)**: Continuous background frame consumer with single-frame atomic buffer (DirectShow / V4L2) eliminating video delay.
  - **Thread 2 (Inference Engine)**: Pluggable ONNX Runtime FP16 / PyTorch inference engine with 3-pass warmup and geometric candling heuristics ($0.65 \le \text{AR} \le 1.45$).
  - **Thread 3 (IoT Serial Driver)**: Non-blocking PySerial ESP32 driver with delayed ejection timer calculation ($\Delta t = D/v$).
  - **Thread 4 (Local Storage & Sync)**: SQLite WAL mode persistence with background HTTP REST sync worker (`POST /api/v1/scans/sync`).
- **CustomTkinter 60 FPS Desktop GUI**: Operator interface with real-time HUD, live camera overlay, Day-10 Penoy counter, and manual override triggers (`[SPACEBAR]` and `[R]`).
- **Graceful Hardware Fallbacks**: Automatically falls back to **Synthetic Candling Stream** and **Mock Actuator** if physical USB camera or ESP32 are disconnected.

---

## 📁 Directory Layout

```
edge/
├── models/                       # YOLOv8 weights & ONNX exporter
│   ├── weights/best.onnx         # 11.7 MB FP16 ONNX model
│   └── export_onnx.py            # Automated export script
├── src/
│   ├── core/
│   │   ├── camera.py             # Thread-safe DirectShow/V4L2 grabber
│   │   ├── heuristics.py         # Optical candling & AR heuristics
│   │   └── inference.py          # ONNX Runtime FP16 inference
│   ├── db/
│   │   └── local_db.py           # SQLite WAL manager
│   ├── iot/
│   │   └── serial_driver.py      # Non-blocking ESP32 PySerial driver
│   ├── sync/
│   │   └── sync_worker.py        # Background HTTP REST sync worker
│   └── ui/
│       ├── app.py                # CustomTkinter 60 FPS operator desktop GUI
│       └── theme.py              # Foundation University brand tokens
├── tests/
│   └── test_edge_pipeline.py     # Automated unit & smoke test suite
├── launcher.py                   # Clean entry point
└── requirements.txt              # Edge Python dependencies
```

---

## ⚙️ Setup & Execution

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment (`edge/.env`)
```ini
API_KEY=dev-api-key-123
API_BASE_URL=http://localhost:8000
DEVICE_ID=STATION-01-RP5
CAMERA_INDEX=0
SERIAL_PORT=COM3
SERIAL_BAUD=115200
CONVEYOR_SPEED_CM_S=12.50
CONVEYOR_DIST_CM=25.00
SERVO_PULSE_MS=250
```

### 3. Run Operator Desktop App
```bash
python launcher.py
```

### 4. Run Automated Tests
```bash
python -m pytest tests/test_edge_pipeline.py -v
```
