# OvaLens — Automated Duck Egg Candling & Hatchery Management System

[![Capstone Project](https://img.shields.io/badge/Capstone-Foundation%20University-800000.svg)](https://foundationu.com)
[![Architecture](https://img.shields.io/badge/Repository-Central%20Monorepo-357a38.svg)]()
[![Model](https://img.shields.io/badge/YOLOv8-ONNX%20FP16-blue.svg)]()
[![Backend](https://img.shields.io/badge/FastAPI-PostgreSQL%2016-teal.svg)]()
[![Frontend](https://img.shields.io/badge/React%2018-Vite%20%2B%20TypeScript-61dafb.svg)]()

**OvaLens** is an automated, industrial-grade duck egg candling, fertility classification, and hatchery analytics ecosystem developed for Foundation University.

The system automates the inspection of duck eggs on a motorized conveyor belt, utilizing high-intensity candling LEDs, an optimized **YOLOv8** computer vision pipeline, **ESP32** millisecond-accurate mechanical sorting, a high-throughput **FastAPI + PostgreSQL** backend, and a modern **React Admin Dashboard**.

---

## 🏗 Ecosystem Monorepo Architecture

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   OVALENS SYSTEM ARCHITECTURE                                           │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘

 ┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                                   1. PHYSICAL CONVEYOR & IOT RIG                                      │
 │                                                                                                      │
 │   [Egg Infeed] ──► [Optical Sensor] ──► [Candling Tunnel (10W LED)] ──► [Diverter Gate (Servo)]     │
 │                           │                       │                              ▲                   │
 │                           │ Trigger               │ DirectShow / V4L2            │ Serial UART       │
 └───────────────────────────┼───────────────────────┼──────────────────────────────┼───────────────────┘
                             │                       │                              │
 ┌───────────────────────────┼───────────────────────┼──────────────────────────────┼───────────────────┐
 │                           ▼                       ▼                              │                   │
 │   2. EDGE CV STATION                  [Inference Engine (YOLOv8 ONNX FP16)] ─────┘                   │
 │   (Raspberry Pi 5 / PC)                           │                                                  │
 │                                                   ▼                                                  │
 │                                       [Local SQLite Store (WAL)]                                     │
 │                                                   │                                                  │
 │                                                   ▼ (Async Sync Worker: POST /api/v1/scans/sync)     │
 └───────────────────────────────────────────────────┼──────────────────────────────────────────────────┘
                                                     │
 ┌───────────────────────────────────────────────────┼──────────────────────────────────────────────────┐
 │                                                   ▼                                                  │
 │   3. CENTRAL HATCHERY BACKEND          [FastAPI REST API Server]                                     │
 │   (Production Server / Cloud)                     │                                                  │
 │                                                   ▼                                                  │
 │                                       [PostgreSQL 16 Engine]                                         │
 │                                                   ▲                                                  │
 └───────────────────────────────────────────────────┼──────────────────────────────────────────────────┘
                                                     │
 ┌───────────────────────────────────────────────────┼──────────────────────────────────────────────────┐
 │                                                   │ (JWT REST / SSE Analytics Stream)                │
 │   4. ADMIN WEB DASHBOARD                          ▼                                                  │
 │   (React 18 + Vite + TypeScript)      [Hatchery Manager & Audit Portal]                              │
 └──────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Monorepo Directory Structure

```
Capstone/
├── backend/                      # Central FastAPI REST API & Database Engine
│   ├── app/                      # Clean modular application
│   │   ├── core/                 # Config, DB engine, JWT auth, exceptions
│   │   ├── models/               # SQLAlchemy 2.0 models (User, Device, Batch, Session, Scan)
│   │   ├── schemas/              # Pydantic v2 DTOs (Request / Response validation)
│   │   ├── api/v1/endpoints/     # Modular routers (auth, devices, batches, sessions, scans, analytics, reports)
│   │   ├── services/             # Business logic (Batch state machine, PDF/CSV export, Analytics)
│   │   └── main.py               # FastAPI entry point, CORS, middlewares
│   ├── seed/seed_db.py           # Rich demo database seeder CLI for defense
│   ├── tests/test_api.py         # Automated pytest test suite
│   ├── Dockerfile
│   └── requirements.txt
│
├── edge/                         # Edge CV Application & Conveyor Controller
│   ├── models/                   # YOLOv8 ONNX FP16 weights & export tools
│   │   ├── export_onnx.py        # Automated PyTorch -> ONNX slim export script
│   │   └── weights/              # Production ONNX weights (best.onnx)
│   ├── src/
│   │   ├── core/                 # Camera frame grabber, ONNX inference, heuristics
│   │   ├── iot/                  # Non-blocking PySerial ESP32 driver
│   │   ├── db/                   # Local SQLite WAL database manager
│   │   ├── sync/                 # Background HTTP REST sync worker
│   │   └── ui/                   # CustomTkinter 60 FPS operator desktop interface
│   ├── tests/test_edge_pipeline.py # Automated edge unit & smoke tests
│   ├── launcher.py               # Edge entry point
│   └── requirements.txt
│
├── dashboard/                    # React 18 + Vite + TypeScript Admin Dashboard
│   ├── src/
│   │   ├── api/                  # Axios client & TanStack Query hooks
│   │   ├── components/           # Reusable UI widgets (Navbar, Cards, Modals, Tables)
│   │   ├── pages/                # Overview, Batches, ScanExplorer, Analytics, Devices
│   │   ├── store/                # Zustand global state (Auth, Settings)
│   │   ├── types/                # TypeScript interfaces matching backend schemas
│   │   └── styles/               # TailwindCSS & Foundation University theme tokens
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
│
├── firmware/                     # ESP32 IoT Microcontroller Source Code
│   └── esp32_actuator/
│       ├── esp32_actuator.ino    # Hardware interrupt, optical debounce, servo PWM timer
│       └── README.md             # Pinout wiring diagram & serial command specs
│
├── docker-compose.yml            # 1-Click PostgreSQL + Backend + Dashboard deployment
├── AGENTS.md                     # Master AI developer rulebook & architectural guide
├── .gitignore                    # Master root gitignore
└── README.md                     # Master project documentation & living changelog
```

---

## 🗄️ Relational Database Schema (PostgreSQL 16)

```
┌───────────────────┐       ┌─────────────────────────┐       ┌───────────────────────┐
│       users       │       │         batches         │◄──────│   candling_sessions   │
├───────────────────┤       ├─────────────────────────┤       ├───────────────────────┤
│ PK  user_id       │       │ PK  batch_id            │       │ PK  session_id        │
│     email         │       │     batch_code          │       │ FK  batch_id          │
│     role          │       │     breed               │       │ FK  device_id         │
│     hashed_pass   │       │     incubator_id        │       │     stage             │
└───────────────────┘       │     initial_egg_count   │       │     operator_name     │
                            │     current_stage       │       │     total_scanned     │
                            │     set_date            │       │     fertile_count     │
                            │     target_hatch_date   │       │     infertile_count   │
                            │     status              │       │     abnormal_count    │
                            └───────────┬─────────────┘       └───────────┬───────────┘
                                        │                                 │
                                        │     ┌─────────────────────┐     │
                                        └────►│      egg_scans      │◄────┘
                                              ├─────────────────────┤
                                              │ PK  scan_id         │
                                              │ FK  session_id      │
                                              │ FK  batch_id        │
                                              │     sequence_number │
                                              │     final_class     │ (FERTILE/INFERTILE/ABNORMAL)
                                              │     confidence      │
                                              │     inference_ms    │
                                              │     routing_action  │ (ACCEPT/REJECT)
                                              │     detections      │ (JSONB)
                                              │     image_url       │
                                              │     scanned_at      │
                                              └─────────────────────┘
                                                         │
                                              ┌──────────┴──────────┐
                                              │       devices       │
                                              ├─────────────────────┤
                                              │ PK  device_id       │
                                              │     device_name     │
                                              │     status          │
                                              │     conveyor_speed  │
                                              │     conveyor_dist   │
                                              │     servo_pulse_ms  │
                                              └─────────────────────┘
```

1. **`users`**: Authentication credentials, password hashes, and RBAC tiers (`ADMIN`, `MANAGER`, `OPERATOR`).
2. **`devices`**: Registered Edge sorting stations, telemetry heartbeats, and conveyor calibration ($D$, $v$, pulse duration).
3. **`batches`**: 28-day incubation batch tracking (`SETTING` $\to$ `DAY_10` $\to$ `DAY_18` $\to$ `DAY_25` $\to$ `HATCHED` $\to$ `COMPLETED`).
4. **`candling_sessions`**: Milestone candling runs (Day 10, Day 18, Day 25) with session aggregates and operator logs.
5. **`egg_scans`**: High-resolution scan records with monotonic sequence numbers, confidence scores, inference latency, JSONB YOLO bounding boxes, and image storage URLs.
6. **`audit_logs`**: Immutable audit logs tracking administrative actions, batch completions, and configuration changes.

---

## ⚙️ Anti-Duplication & Robustness Mechanisms

1. **Hardware Debounce**: ESP32 enforces a 600ms optical trigger lockout window to eliminate sensor oscillation and egg jitter.
2. **Client UUIDv4 & Monotonic Counters**: Edge mints a deterministic UUIDv4 (`scan_id`) and sequence number per scan.
3. **Atomic UPSERT Ingestion**: Backend executes `ON CONFLICT (scan_id) DO NOTHING`, ensuring idempotent retries after network dropouts.
4. **Power Loss Recovery**: Edge continuously records session state in SQLite WAL, allowing instant session resume upon reboot.

---

## 🎨 Foundation University Brand Design Tokens

The Admin Web Dashboard and Edge GUI follow Foundation University's visual identity:

* **Primary Maroon**: `#800000` (Header bars, active tabs, primary buttons)
* **Dark Maroon**: `#5C0000` (Hover states, sidebar accents)
* **Agri-Green**: `#357a38` (Fertile indicator, positive yields, success badges)
* **Reject Red**: `#DC2626` (Infertile / Dead embryo indicator, alerts)
* **Dark Slate Background**: `#0F172A` / **Card**: `#1E293B` / **Border**: `#334155`
* **Light Slate Background**: `#F8FAFC` / **Card**: `#FFFFFF` / **Border**: `#E2E8F0`

---

## 📝 Living Changelog & Architecture Evolution

### [2026-08-20] — Phase 2: Edge App CV Optimization & CustomTkinter Operator GUI
- **ONNX Runtime FP16 Model Export**:
  - Exported YOLOv8 weights (`best.pt`) to optimized ONNX Runtime model (`best.onnx` - 11.7 MB).
  - Implemented 3-pass warmup on initialization to eliminate first-frame latency spikes.
- **Decoupled Quad-Thread Edge Architecture**:
  - `src/core/camera.py`: DirectShow / V4L2 background grabber with single-frame atomic slot (zero buffer lag).
  - `src/core/inference.py`: Pluggable ONNX Runtime / PyTorch engine with candling heuristics and aspect ratio filtering ($0.65 \le \text{AR} \le 1.45$).
  - `src/iot/serial_driver.py`: Non-blocking ESP32 serial driver implementing delayed ejection strokes ($\Delta t = D/v$).
  - `src/db/local_db.py`: Embedded SQLite manager with WAL mode enabled.
  - `src/sync/sync_worker.py`: Background HTTP sync worker with exponential backoff syncing to `POST /api/v1/scans/sync`.
  - `src/ui/app.py`: High-performance CustomTkinter operator GUI with live HUD, real-time counters, audio chimes, and manual override keys (`[SPACEBAR]` / `[R]`).
- **Automated Testing Suite**:
  - Built `edge/tests/test_edge_pipeline.py` covering heuristics, camera mock generation, ONNX inference, SQLite WAL transactions, and serial mock (5/5 tests passed).

### [2026-08-20] — Phase 1: Transition to Central Monorepo & Standalone Capstone Ecosystem
- **Monorepo Structure Established**:
  - Unified root Git repository containing `edge/`, `backend/`, `dashboard/`, and `firmware/`.
  - Linked and pushed to GitHub remote `Dev-RyleR6/OvaLens-Ecosystem`.
- **FastAPI Backend & Relational Schema**:
  - Modularized `backend/app/` (`core`, `models`, `schemas`, `api/v1`, `services`).
  - Implemented 28-day batch state machine, idempotent scan sync, and PDF/CSV reporting.
  - Built rich database seeder (`seed/seed_db.py`) and automated backend pytest suite (6/6 tests passed).
- **ESP32 Firmware**:
  - Created `firmware/esp32_actuator/esp32_actuator.ino` with hardware interrupt, 600ms optical debounce, and serial command protocol.
