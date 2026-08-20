# Chapter 3: Technical Methodology

## 3.1 System Architectural Design
OvaLens employs a 4-tier monorepo architecture:
1. **Edge CV & Hardware Controller (`edge/`)**:
   - Raspberry Pi 5 / Windows x86_64 running CustomTkinter operator GUI.
   - Multi-threaded architecture: Camera frame grabber, ONNX inference, ESP32 serial driver, and SQLite WAL sync worker.
2. **IoT Microcontroller Firmware (`firmware/`)**:
   - ESP32 Dev Module (115200 baud UART).
   - 600 ms optical sensor debounce lockout on GPIO 14.
   - Non-blocking hardware timer interrupts for servo/pneumatic solenoid actuation.
3. **Central Backend Engine (`backend/`)**:
   - FastAPI with Python 3.11+, Pydantic v2, and SQLAlchemy 2.0.
   - PostgreSQL 16 relational database with idempotent ingestion (`ON CONFLICT DO NOTHING`).
4. **Administrative Web Portal (`dashboard/`)**:
   - React 18 + Vite + TypeScript + TailwindCSS.
   - Incubator Tray Matrix ($A1 \to F7$), Mortality Trends, MLOps Model Registry, and Audit Logs.

## 3.2 Dataset Collection, Annotation & Augmentation
* **Total Dataset**: 4,850 high-resolution duck egg candling frames.
* **Class Distribution**:
  - `FERTILE`: 2,800 images (57.7%)
  - `INFERTILE`: 1,450 images (29.9%)
  - `ABNORMAL`: 600 images (12.4%)
* **Data Splits**: 70% Training (3,395 frames), 20% Validation (970 frames), 10% Testing (485 frames).
* **Augmentations**: $\pm 15^\circ$ rotation, HSV luminance jitter ($V \pm 20\%$), random horizontal/vertical flips.

## 3.3 Model Training & ONNX FP16 Slim Export
* Base architecture: YOLOv8 Nano (`yolov8n.pt`).
* Loss functions: CIoU Bounding Box Loss, Binary Cross-Entropy Classification Loss, Distribution Focal Loss (DFL).
* Conversion Pipeline: PyTorch FP32 $\to$ ONNX FP16 Half-Precision Graph $\to$ ONNX Runtime execution provider.

## 3.4 Hardware Kinematics & Timing Calculation
$$\Delta t = \frac{D}{v}$$
Where:
* $D = 25.0\text{ cm}$ (Distance from optical trigger to diverter flipper)
* $v = 12.5\text{ cm/s}$ (Conveyor belt velocity)
* Resulting actuation travel delay: $\Delta t = 2,000\text{ ms}$.
