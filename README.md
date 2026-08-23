# OvaLens — Automated Duck Egg Candling & Hatchery Management System

[![Capstone Project](https://img.shields.io/badge/Capstone-Foundation%20University-800000.svg)](https://foundationu.com)
[![Architecture](https://img.shields.io/badge/Repository-Central%20Monorepo-357a38.svg)]()
[![Model](https://img.shields.io/badge/YOLOv8-ONNX%20FP16-blue.svg)]()
[![Backend](https://img.shields.io/badge/FastAPI-PostgreSQL%2016-teal.svg)]()
[![Frontend](https://img.shields.io/badge/React%2018-Vite%20%2B%20TypeScript-61dafb.svg)]()
[![License](https://img.shields.io/badge/License-Apache%202.0-orange.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Automated%20Tests-11%2F11%20Passing-brightgreen.svg)]()

**OvaLens** is an automated, industrial-grade duck egg candling, fertility classification, and hatchery analytics ecosystem developed for Foundation University.

The system automates the inspection of duck eggs on a motorized conveyor belt, utilizing high-intensity candling LEDs, an optimized **YOLOv8** computer vision pipeline, **ESP32** millisecond-accurate mechanical sorting, a high-throughput **FastAPI + PostgreSQL** backend, and a modern **React Admin Dashboard**.

---

## 📚 Key Project Documentation

* 📖 **[Setup & Operations Manual](SETUP_AND_OPERATIONS.md)**: Full guide on prerequisites, installation, operating procedures, and troubleshooting.
* 🛡️ **[Code Review & Security Audit](CODE_REVIEW.md)**: Formal code review audit covering security, non-blocking edge concurrency, and test coverage.
* 🤖 **[Master AI & Developer Guidelines](AGENTS.md)**: Architecture tenets, negative constraints, Conventional Commits standard, and verification runbooks.
* 📜 **[Apache License 2.0](LICENSE)**: Institutional open-source license.

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
 │                                                   │ (JWT REST / HTTP API Proxy)                      │
 │   4. ADMIN WEB DASHBOARD                          ▼                                                  │
 │   (React 18 + Vite + TypeScript)      [Hatchery Manager & Audit Portal]                              │
 └──────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Monorepo Directory Structure

```
Capstone/
├── .agents/                      # AI Agent Customizations & Skills
│   └── skills/                   # git-workflow, code-reviewer, performance-auditor
│
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
│   │   ├── api/                  # Axios client & Mock fallback engine
│   │   ├── components/           # Navbar, Sidebar, StatCard, Badge, Modal, Timeline
│   │   ├── pages/                # Overview, Batches, ScanExplorer, Analytics, Devices
│   │   ├── types/                # TypeScript interfaces matching backend schemas
│   │   └── index.css             # TailwindCSS & Foundation University theme tokens
│   ├── Dockerfile
│   ├── nginx.conf
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
├── SETUP_AND_OPERATIONS.md       # Full Setup, Installation & Operator Manual
├── CODE_REVIEW.md                # Formal Code Review & Security Audit Report
├── AGENTS.md                     # Master AI developer rulebook & architectural guide
├── LICENSE                       # Apache License 2.0
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

---

## 🌐 Central REST API Architecture & Endpoints Reference

The FastAPI backend exposes versioned, high-throughput REST endpoints under `/api/v1` with full OpenAPI documentation at `http://localhost:8000/docs`.

### Security & Authentication Layers
1. **Machine Ingestion Auth (`X-API-Key`)**: Edge conveyor stations authenticate via the `X-API-Key` HTTP header.
2. **User Role-Based Access Control (`Bearer JWT`)**: Web dashboard users authenticate via signed JWT tokens with 3 security tiers:
   - **`ADMIN`**: Full user administration, system-wide configuration, and database maintenance.
   - **`MANAGER`**: Cohort creation, batch lifecycle advancement, settings updates, and audit report generation.
   - **`OPERATOR`**: Candling shift operations, live scan review, and human-in-the-loop classification overrides.
3. **Sliding-Window IP Rate Limiting**: `POST /api/v1/auth/login` limits failed login attempts to 10/min per IP to prevent brute-force attacks.

### Modular REST API Endpoints

```
/api/v1/
├── auth/
│   ├── POST /login                        # Authenticate user & issue JWT token (Rate-limited)
│   ├── GET  /me                           # Authoritative user profile verification (Bearer JWT)
│   └── POST /register                     # Register new user account (Admin only)
│
├── users/
│   ├── GET   /                            # List all operators & managers (Admin only)
│   ├── POST  /                            # Create user with bcrypt password hash (Admin only)
│   └── PATCH /{id}/status                 # Toggle user status with self-deactivation guard (Admin only)
│
├── batches/
│   ├── GET    /                           # List all batches with computed fertility & hatchability
│   ├── GET    /active                     # List active batches for Edge station selection
│   ├── POST   /                           # Create new incubation batch cohort (Manager/Admin)
│   ├── GET    /{id}                       # Get single batch record details
│   ├── GET    /{id}/analytics             # Deep batch analytics (Day 10 fertility, Penoy salvage ₱)
│   ├── PUT    /{id}                       # Update batch status & hatch counts (Manager/Admin)
│   ├── POST   /{id}/advance-stage         # Advance milestone (Day 10, Day 18, Day 25, Hatched) (Manager/Admin)
│   ├── POST   /{id}/finalize-hatch        # Finalize Day 28 harvest trial (Manager/Admin)
│   ├── DELETE /{id}                       # Archive/delete incubation batch (Manager/Admin)
│   └── POST   /check-milestones           # Automated milestone checker & alerts
│
├── scans/
│   ├── POST  /sync                        # Idempotent bulk scan ingestion from Edge (X-API-Key)
│   ├── POST  /upload-image                # Upload 1080p candling frame photo (X-API-Key)
│   ├── GET   /                            # List & filter candling scans by batch or class
│   ├── GET   /{id}                        # Get full scan record with JSONB bounding boxes
│   └── PATCH /{id}/override               # Human-in-the-Loop classification override (Bearer JWT)
│
├── sessions/
│   ├── GET /                              # List candling sessions by batch/stage
│   ├── POST /                             # Start active candling shift from Edge (X-API-Key)
│   ├── GET /{id}                          # Get session summary & class totals
│   └── PUT /{id}/end                      # Conclude candling shift & record end timestamp (X-API-Key)
│
├── devices/
│   ├── GET  /                             # List registered sorting conveyor stations (Bearer JWT)
│   ├── POST /register                     # Register or calibrate edge station (X-API-Key)
│   └── POST /{id}/heartbeat               # Edge machine telemetry ping (X-API-Key)
│
├── analytics/
│   ├── GET /overview                      # Overall facility KPIs (fertility, cull, hatch rates)
│   ├── GET /economic-yield                # Day-10 Penoy salvage revenue & power savings ROI
│   ├── GET /breed-comparison              # Commercial performance across duck breeds
│   ├── GET /mortality-trends              # Early vs mid vs late embryonic mortality breakdown
│   └── GET /mortality-progression         # 28-day developmental viability retention curve
│
├── audit-logs/
│   └── GET /                              # Immutable PostgreSQL audit trail logs (Manager/Admin)
│
├── settings/
│   ├── GET /                              # Get facility configuration & pricing parameters
│   └── PUT /                              # Update economic prices & AI thresholds (Manager/Admin)
│
└── reports/
    ├── GET /batch/{id}/csv                # Stream raw candling dataset CSV export
    └── GET /batch/{id}/pdf                # Generate official Foundation University PDF Certificate
```

---

## 🎨 Foundation University Brand Design Tokens

The Admin Web Dashboard and Edge GUI follow Foundation University's visual identity:

* **Primary Maroon**: `#800000` (Header bars, active tabs, primary buttons)
* **Dark Maroon**: `#5C0000` (Hover states, sidebar accents)
* **Agri-Green**: `#357a38` (Fertile indicator, positive yields, success badges)
* **Reject Red**: `#DC2626` (Infertile / Dead embryo indicator, alerts)
* **Infertile Amber**: `#D97706` (Penoy salvage badge)
* **Dark Slate Background**: `#0F172A` / **Card**: `#1E293B` / **Border**: `#334155`

---

## 🚀 Quickstart & Development Guide

### 1. Run the Complete Stack with Docker (1-Click)
```bash
docker compose up --build
# Dashboard: http://localhost:3000
# Backend API & Docs: http://localhost:8000/docs
# PostgreSQL: localhost:5432
```

### 2. Run React Admin Dashboard Locally
```bash
cd dashboard
npm install
npm run dev
# Dashboard running at http://localhost:5173
```

### 3. Run FastAPI Backend Locally
```bash
cd backend
python -m seed.seed_db --reset
python -m uvicorn app.main:app --reload --port 8000
```

### 4. Run Edge Operator GUI Locally
```bash
cd edge
python launcher.py
```

---

## 📝 Living Changelog & Architecture Evolution

### [2026-08-20] — Phase 3: React 18 + Vite + TypeScript Admin Web Dashboard
- **Scaffolded Modern Web Dashboard**:
  - React 18 + Vite + TypeScript + TailwindCSS + Recharts + Lucide Icons.
  - Complete Foundation University dark-mode aesthetic (`#800000` Maroon, `#357a38` Agri-Green, `#0F172A` Slate).
- **Core Management Views Built**:
  - `OverviewPage.tsx`: Executive KPI cards, breed fertility distribution charts, active batch timelines, and live scan feed.
  - `BatchesPage.tsx`: Full lifecycle management table, "Set New Batch" modal, and direct CSV/PDF report download links.
  - `ScanExplorerPage.tsx`: Dual Grid/Table viewer with synthetic candling frames, bounding box HUD, and JSONB inspection drawer.
  - `AnalyticsPage.tsx`: Interactive Day-10 Penoy Economic Salvage Yield Estimator (custom egg count $\times$ price simulator) and 28-day viability curves.
  - `DevicesPage.tsx`: Edge station IoT telemetry cards, conveyor calibration specs ($\Delta t = D/v$), and remote station ping.
- **Production Build & Containerization**:
  - Created `dashboard/Dockerfile` and `dashboard/nginx.conf` for 1-click Docker Compose deployment.
  - Verified bundle compilation (`tsc && vite build`) with zero errors.

### [2026-08-20] — Phase 2: Edge App CV Optimization & CustomTkinter Operator GUI
- **ONNX Runtime FP16 Model Export**:
  - Exported YOLOv8 weights (`best.pt`) to optimized ONNX Runtime model (`best.onnx` - 11.7 MB).
- **Decoupled Quad-Thread Edge Architecture**:
  - `src/core/camera.py`: DirectShow / V4L2 background grabber with single-frame atomic slot (zero buffer lag).
  - `src/core/inference.py`: Pluggable ONNX Runtime / PyTorch engine with candling heuristics ($0.65 \le \text{AR} \le 1.45$).
  - `src/iot/serial_driver.py`: Non-blocking ESP32 serial driver implementing delayed ejection strokes ($\Delta t = D/v$).
  - `src/db/local_db.py`: Embedded SQLite manager with WAL mode enabled.
  - `src/sync/sync_worker.py`: Background HTTP sync worker syncing to `POST /api/v1/scans/sync`.
  - `src/ui/app.py`: CustomTkinter 60 FPS operator desktop application with live HUD and manual override controls (`[SPACEBAR]` / `[R]`).
- **Automated Testing Suite**:
  - Built `edge/tests/test_edge_pipeline.py` (5/5 tests passed).

### [2026-08-20] — Phase 1: Transition to Central Monorepo & Standalone Capstone Ecosystem
- **Monorepo Structure Established**:
  - Unified root Git repository containing `edge/`, `backend/`, `dashboard/`, and `firmware/`.
  - Licensed under **Apache License 2.0**.
- **FastAPI Backend & Relational Schema**:
  - Modularized `backend/app/` (`core`, `models`, `schemas`, `api/v1`, `services`).
  - Built rich database seeder (`seed/seed_db.py`) and automated backend pytest suite (6/6 tests passed).
- **ESP32 Firmware**:
  - Created `firmware/esp32_actuator/esp32_actuator.ino` with hardware interrupt, 600ms optical debounce, and serial command protocol.
