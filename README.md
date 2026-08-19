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
 │                           ▼                       ▼ Frame Capture                │ Reject Command    │
 │                     ┌───────────────────────────────────┐                        │ (within Δt travel)│
 │                     │    ESP32 Hardware Controller      │────────────────────────┘                   │
 └─────────────────────┼───────────────────────────────────┼────────────────────────────────────────────┘
                       │                                   │
                       │ USB Serial UART (115200 Baud)     │
                       ▼                                   ▼
 ┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                                     2. OVALENS EDGE NODE                                              │
 │                              (PC Dev -> Raspberry Pi 4/5 Prod)                                        │
 │                                                                                                      │
 │  • Multithreaded Engine: Camera Grabber (Thread 1) | Inference Engine (Thread 2)                      │
 │                          Actuator Comms (Thread 3) | Local DB & Sync (Thread 4)                       │
 │  • YOLOv8 Optimization: PyTorch (Dev) -> ONNX Runtime FP16 / NCNN / ARM OpenVINO (RPi)                │
 │  • Heuristics: Geometric Aspect-Ratio Filter (0.65 - 1.45) + HSV Candling Luminance Check            │
 │  • Offline-First Cache: Local SQLite (WAL Mode) with auto-reconnect queue                            │
 │  • Operator GUI: CustomTkinter (Desktop) / Touchscreen with local live camera HUD                     │
 └───────────────────────────────────┬──────────────────────────────────────────────────────────────────┘
                                     │
                    HTTP REST Sync   │ Scan Records, Batch Summaries & Images
                    (X-API-Key Auth) │
                                     ▼
 ┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                                    3. CENTRAL BACKEND API                                             │
 │                                   (FastAPI + Async Uvicorn)                                          │
 │                                                                                                      │
 │  • /api/v1/auth          — Operator & Admin Authentication (JWT)                                     │
 │  • /api/v1/batches       — Incubation Batches (Setting -> Day 10 -> Day 18 -> Day 25 -> Hatched)    │
 │  • /api/v1/sessions      — Candling Sessions & Milestone Tracking                                    │
 │  • /api/v1/scans         — High-Throughput Scan Ingestion, Image Storage & Sync                       │
 │  • /api/v1/analytics     — Fertility %, Mortality Curves, Breed Yield & Penoy Salvage Revenue Engine │
 │  • /api/v1/devices       — Edge Node Heartbeat & Telemetry                                           │
 │  • /api/v1/reports       — Academic Defense & Hatchery PDF / CSV Exporter Engine                     │
 └───────────────────────────────────┬──────────────────────────────────▲───────────────────────────────┘
                                     │                                  │
                   Async SQLAlchemy  │                                  │ HTTPS REST
                   Connection Pool   ▼                                  │ (JWT Auth)
                       ┌──────────────────────────┐                     │
                       │   PostgreSQL 16 Engine   │                     │
                       │ (Relational Data + JSONB)│                     │
                       └──────────────────────────┘                     │
                                                                        │
 ┌──────────────────────────────────────────────────────────────────────┴───────────────────────────────┐
 │                                   4. OVALENS ADMIN DASHBOARD                                          │
 │                              (React 18 + Vite + TypeScript + Tailwind)                               │
 │                                                                                                      │
 │  • Foundation University Theme: Maroon (#800000), Dark Maroon (#5C0000), Agri-Green (#357a38)        │
 │  • Executive Dashboard: Total eggs scanned, fertility rates, active batches, cull rates               │
 │  • Batch Lifecycle Manager: 28-day duck egg incubation calendar, milestone alerts, hatch logger      │
 │  • Scan History Explorer: Multi-filter data grid, high-res candling photo modal with YOLO overlays   │
 │  • Analytics & Economic Predictor: Breed comparison, mortality curves, Day-10 Penoy salvage revenue  │
 │  • Hardware Station Manager: Edge device status, conveyor speed & latency telemetry                  │
 │  • PDF / CSV Exporter: One-click generation of defense reports and data tables                       │
 └──────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📦 Unified Monorepo Directory Structure

```
Capstone/ (Root Monorepo)
├── .github/                      # CI/CD workflows (backend-ci.yml, frontend-ci.yml)
├── edge/                         # Subproject 1: Edge CV Application & Operator GUI
│   ├── models/                   # YOLOv8 weights (ONNX FP16 / PyTorch)
│   ├── core/                     # Decoupled Camera grabber & inference engine
│   ├── iot/                      # PySerial ESP32 communication driver
│   ├── db/                       # Local SQLite WAL database manager
│   ├── ui/                       # CustomTkinter 60 FPS operator interface
│   ├── launcher.py               # Edge entry point
│   ├── requirements.txt
│   └── .env.example
│
├── backend/                      # Subproject 2: FastAPI Backend Engine
│   ├── app/                      # Modular FastAPI core (core, models, api, services)
│   ├── alembic/                  # Database schema migrations
│   ├── seed/                     # CLI demo data generator (seed_db.py)
│   ├── tests/                    # Pytest test suite
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── dashboard/                    # Subproject 3: React 18 + Vite + TS Admin Dashboard
│   ├── src/                      # Components, pages, hooks, api client, FU theme
│   ├── package.json
│   ├── tailwind.config.js
│   ├── Dockerfile
│   └── .env.example
│
├── firmware/                     # Subproject 4: ESP32 IoT Microcontroller Source Code
│   └── esp32_actuator/
│       ├── esp32_actuator.ino    # Hardware timer interrupt, optical debounce, servo PWM
│       └── README.md             # Pinout wiring diagram & serial command specs
│
├── docker-compose.yml            # 1-Click local/cloud deployment (Postgres + Backend + Web)
├── .gitignore                    # Master root gitignore
└── README.md                     # Master documentation & living changelog
```

---

## 🎯 Target Biological Classification

OvaLens is calibrated specifically for Philippine duck egg breeds (**Kayumanggi**, **Itim**, **Khaki**) across the standard 28-day incubation cycle:

| Class Label | Biological Definition | Actuator Action | Commercial Disposition |
| :--- | :--- | :--- | :--- |
| **`FERTILE`** | Active embryo with distinct spider-like blood vein vascularization | **ACCEPT** (Continues to setter tray) | Continues incubation to Day 28 |
| **`INFERTILE`** | Clear, unfertilized yolk with no embryo development ("Bugok") | **REJECT** (Diverted to cull chute) | Salvaged on Day 10 as commercial Penoy / Salted Egg (₱12–₱15) |
| **`ABNORMAL`** | Early dead embryo, blood ring, corrupted yolk, or ceased development | **REJECT** (Diverted to cull chute) | Discarded early to prevent bacterial explosion & contamination |

---

## 🗄 Consolidated PostgreSQL Database Schema

```
┌──────────┐ 1      * ┌──────────┐ 1      * ┌───────────────────┐ 1      * ┌───────────┐
│  users   ├─────────►│ batches  ├─────────►│ candling_sessions ├─────────►│ egg_scans │
└──────────┘          └──────────┘          └─────────▲─────────┘          └───────────┘
                                                      │ *
                                                      │ 1
                                            ┌─────────┴─────────┐
                                            │      devices      │
                                            └───────────────────┘
```

1. **`users`**: Authentication credentials, password hashes (`bcrypt`), and RBAC tiers (`ADMIN`, `MANAGER`, `OPERATOR`).
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

### [2026-08-20] — Transition to Central Monorepo & Standalone Capstone Ecosystem
- **Monorepo Structure Established**:
  - Unified root Git repository containing `edge/`, `backend/`, `dashboard/`, and `firmware/`.
  - Configured 5-Pillar robust engineering pipeline (Model Export, CI Testing, 1-Click Docker, ESP32 Firmware, Idempotent Sync).
- **Purged Legacy Code**:
  - Removed external `hatchio` project and Firebase RTDB dependencies.
- **Architected**:
  - **Mechanical Rig**: Conveyor-belt continuous feed with optical trigger and downstream ESP32 servo kicker ($\Delta t = D/v$).
  - **Vision Engine**: YOLOv8 exported to ONNX Runtime FP16 with quad-thread decoupled pipeline (30-40ms on Raspberry Pi 5).
  - **Database Engine**: Consolidated PostgreSQL 16 schema with JSONB detection storage, Alembic migrations, and comprehensive seeders.
  - **Backend API**: Modular FastAPI REST backend with JWT/API-Key auth, 28-day batch lifecycle state machine, and PDF/CSV reporting.
  - **Admin Dashboard**: React 18 + Vite + TypeScript + TailwindCSS with Foundation University theme, batch tracking, scan explorer, and Penoy economic salvage calculator.
- **Documented**: Master `README.md` and `implementation_plan.md` established as central sources of truth.
