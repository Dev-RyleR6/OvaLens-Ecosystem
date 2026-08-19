# AGENTS.md — OvaLens AI Coding Assistant & Developer Guidelines

> **OvaLens** is an automated, industrial-grade duck egg candling, fertility classification, and hatchery analytics ecosystem developed as a Capstone project for **Foundation University**.

This document serves as the **Master Source of Truth & Architecture Guide** for any AI agent or software engineer working on the OvaLens codebase. Follow all rules, conventions, and architectural constraints documented here.

---

## 🏛 1. Core Architectural Constraints & Tenets

1. **Standalone Architecture (Zero External Hatchio/Firebase Dependencies)**:
   - OvaLens is a 100% self-contained system. **NEVER** re-introduce Firebase RTDB writers or Hatchio external synchronization bridges.
   - The central source of truth for the entire hatchery is the **FastAPI Backend + PostgreSQL 16 Database** in `backend/`.
2. **Central Monorepo Topology**:
   - Keep all code inside the root monorepo: `edge/`, `backend/`, `dashboard/`, and `firmware/`.
   - Never initialize nested `.git` repositories inside subdirectories.
3. **Biological Model Classes (Strict 3-Class Vision Model)**:
   - `FERTILE`: Active embryo with spider blood veins (Action: `ACCEPT`).
   - `INFERTILE`: Clear unfertilized yolk / "bugok" (Action: `REJECT`, Salvaged on Day 10 as Penoy @ ₱14).
   - `ABNORMAL`: Dead embryo, blood ring, corrupted yolk (Action: `REJECT`, Discarded early).
4. **Offline-First Edge Resilience**:
   - The Edge application MUST record every scan to local SQLite (with WAL mode enabled) before syncing over the network.
   - Network dropouts must never block or delay the physical conveyor belt sorting speed.
5. **Foundation University (FU) Brand Identity**:
   - **Primary Maroon**: `#800000` | **Dark Maroon**: `#5C0000`
   - **Agri-Green (Fertile/Success)**: `#357a38` | **Reject Red**: `#DC2626`
   - **Dark Theme Background**: `#0F172A` | **Card**: `#1E293B` | **Border**: `#334155`
   - **Light Theme Background**: `#F8FAFC` | **Card**: `#FFFFFF` | **Border**: `#E2E8F0`

---

## 📁 2. Monorepo Subsystems & Directory Responsibilities

```
Capstone/
├── backend/                      # Central FastAPI REST API & Database Engine
│   ├── app/                      # Clean modular application
│   │   ├── core/                 # Config (Pydantic Settings), DB engine, JWT auth, exceptions
│   │   ├── models/               # SQLAlchemy 2.0 declarative models (User, Device, Batch, Session, Scan)
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
│   ├── models/weights/           # YOLOv8 ONNX FP16 weights (best.onnx)
│   ├── src/
│   │   ├── core/                 # Camera frame grabber, ONNX inference, heuristics
│   │   ├── iot/                  # Non-blocking PySerial ESP32 driver
│   │   ├── db/                   # Local SQLite WAL database manager
│   │   ├── sync/                 # Background HTTP REST sync worker
│   │   └── ui/                   # CustomTkinter 60 FPS operator desktop interface
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
├── .gitignore                    # Master root gitignore
└── README.md                     # Master project documentation & living changelog
```

---

## 💻 3. Coding Conventions & Standards by Subsystem

### A. Backend (`backend/`)
- **Python Version**: 3.11+
- **Framework**: FastAPI with Pydantic v2 and SQLAlchemy 2.0.
- **Data Access**: Always use dependency injection (`db: Session = Depends(get_db)`).
- **Data Validation**: Pydantic schemas MUST use `model_config = ConfigDict(from_attributes=True)`. Avoid deprecated `class Config:`.
- **Idempotency**: All scan ingestion endpoints MUST use PostgreSQL `ON CONFLICT (scan_id) DO NOTHING` to safely absorb duplicate network packets.
- **Error Formatting**: Use `OvaLensAPIException` and RFC 7807 problem details JSON format.

### B. Edge CV (`edge/`)
- **GUI Framework**: CustomTkinter running at a smooth 60 FPS.
- **Multi-Threaded Architecture**:
  - Thread 1: Camera Frame Grabber (OpenCV DirectShow/V4L2 continuous circular buffer drain).
  - Thread 2: Inference Engine (ONNX Runtime FP16 + HSV Candling Luminance + Geometric Aspect-Ratio $0.65 \le \text{AR} \le 1.45$).
  - Thread 3: Actuator / Serial Worker (Dispatches non-blocking commands to ESP32).
  - Thread 4: SQLite WAL Local Store & Async Background Sync Worker.
  - Main Thread: CustomTkinter operator GUI.
- **Engine Warmup**: Always execute 3 warmup dummy passes on startup to load model weights into L2/L3 cache and eliminate first-frame latency spikes.

### C. Dashboard (`dashboard/`)
- **Stack**: React 18 + Vite + TypeScript + TailwindCSS + Lucide Icons + Recharts.
- **Type Safety**: Strictly define TypeScript interfaces in `src/types/` mirroring backend Pydantic schemas.
- **State Management**: Use Zustand for auth & app settings; use TanStack Query for server state caching.
- **UI Design**: Strictly adhere to the Foundation University theme tokens (Maroon `#800000`, Agri-Green `#357a38`, Slate backgrounds).

### D. Firmware (`firmware/`)
- **Microcontroller**: ESP32 Dev Module (115200 baud).
- **Timing**: Use hardware timer interrupts and non-blocking state machines. Never call `delay()` inside the main loop during active conveyor operation.
- **Debounce**: 600ms hardware optical sensor lockout window on GPIO 14.

---

## 📝 4. Conventional Commits Standard

All Git commit messages in this repository MUST follow the **Conventional Commits** specification:

```
<type>(<optional scope>): <subject>

[optional body]
```

### Commit Types:
- `feat`: A new user-facing feature (e.g. `feat(backend): add Day 10 Penoy salvage revenue calculation`).
- `fix`: A bug fix (e.g. `fix(edge): resolve OpenCV frame queue buffer lag in DirectShow`).
- `refactor`: Code change that neither fixes a bug nor adds a feature (e.g. `refactor(backend): modularize API endpoints into v1 router`).
- `perf`: Performance improvements (e.g. `perf(edge): export YOLOv8 model to ONNX Runtime FP16`).
- `docs`: Documentation updates (e.g. `docs: update root README architecture diagrams`).
- `test`: Adding or modifying automated tests (e.g. `test(backend): add pytest cases for batch lifecycle`).
- `chore`: Build scripts, dependencies, or tool configurations (e.g. `chore: update root docker-compose.yml`).

---

## 🧪 5. Testing & Verification Runbook

Before submitting or committing changes, run the following verification commands:

### 1. Test Backend API Suite
```bash
cd backend
python -m pytest tests/test_api.py -v
```

### 2. Test Database Seeder
```bash
cd backend
python -m seed.seed_db --reset
```

### 3. Run FastAPI Dev Server Locally
```bash
cd backend
uvicorn app.main:app --reload --port 8000
# OpenAPI Docs available at http://localhost:8000/docs
```

### 4. Build React Dashboard (Once initialized)
```bash
cd dashboard
npm install
npm run build
```

---

## 🚫 6. Hard Don'ts (Negative Constraints)

1. ❌ **DO NOT** import or re-create `firebase_writer.py` or connect to Firebase RTDB.
2. ❌ **DO NOT** make blocking network requests on the main GUI thread of the Edge App.
3. ❌ **DO NOT** use raw SQLite database transactions without WAL mode (`PRAGMA journal_mode = WAL;`).
4. ❌ **DO NOT** commit `.env`, `*.db`, `node_modules/`, `local_scans/`, or bulky `*.pt` training checkpoints to Git.
5. ❌ **DO NOT** hardcode database passwords or API keys in source files; always read from environment variables via `Settings`.
