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
6. **Open Source Institutional License**:
   - OvaLens is licensed under the **Apache License 2.0** (`LICENSE`).

---

## 📁 2. Monorepo Subsystems & Directory Responsibilities

```
Capstone/
├── .agents/                      # AI Agent Customizations & Skills
│   └── skills/                   # git-workflow, code-reviewer, performance-auditor
│
├── .github/                      # CI/CD Workflows
│   └── workflows/ci.yml          # Automated pytest & React build pipeline
│
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
├── SETUP_AND_OPERATIONS.md       # Complete installation & operator manual
├── CODE_REVIEW.md                # Security & quality audit report
├── AGENTS.md                     # Master AI developer rulebook & architectural guide
├── LICENSE                       # Apache License 2.0
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
- **UI Design**: Strictly adhere to the Foundation University theme tokens (Maroon `#800000`, Agri-Green `#357a38`, Slate backgrounds).

### D. Firmware (`firmware/`)
- **Microcontroller**: ESP32 Dev Module (115200 baud).
- **Timing**: Use hardware timer interrupts and non-blocking state machines. Never call `delay()` inside the main loop during active conveyor operation.
- **Debounce**: 600ms hardware optical sensor lockout window on GPIO 14.

---

## 🛠️ 4. AI Agent Skills & Tooling (`.agents/skills/`)

The repository includes specialized agent skills:

1. **`git-workflow`** ([`.agents/skills/git-workflow/SKILL.md`](file:///d:/Ryle_Gabotero/side_projects/Capstone/.agents/skills/git-workflow/SKILL.md)):
   - Feature branching rules (`feat/...`, `fix/...`, `refactor/...`).
   - Conventional Commits message standards.
   - GitHub CLI (`gh`) PR automation and merge protocol.
2. **`code-reviewer`** ([`.agents/skills/code-reviewer/SKILL.md`](file:///d:/Ryle_Gabotero/side_projects/Capstone/.agents/skills/code-reviewer/SKILL.md)):
   - Automated security audit (SQL injection defense, zero hardcoded secrets, RBAC).
   - Edge non-blocking concurrency and SQLite WAL verification.
   - Foundation University branding audits.
3. **`performance-auditor`** ([`.agents/skills/performance-auditor/SKILL.md`](file:///d:/Ryle_Gabotero/side_projects/Capstone/.agents/skills/performance-auditor/SKILL.md)):
   - ONNX Runtime vs PyTorch latency benchmarks ($\le 35$ms SLA).
   - FastAPI database connection pool optimization.
   - CustomTkinter 60 FPS and React render optimization.

---

## 📝 5. Automated Git Workflow & GitHub CLI (`gh`) Standard

All developers and AI assistants working on OvaLens MUST follow the standardized Git and GitHub CLI lifecycle:

### A. Feature Branching:
```bash
git checkout -b feat/<scope>-<description>
```

### B. Conventional Commits:
```
<type>(<scope>): <subject>

[optional body]
```
* **Types**: `feat` | `fix` | `refactor` | `perf` | `docs` | `test` | `chore`
* **Scopes**: `backend` | `edge` | `dashboard` | `firmware` | `agents` | `ci`

### C. GitHub CLI (`gh`) PR Automation:
```bash
# Push branch to remote
git push -u origin feat/<branch-name>

# Create Pull Request
gh pr create --title "feat(<scope>): <subject>" --body "<description>"

# Check CI test status
gh pr checks

# Merge once verified
gh pr merge --squash --delete-branch
```

---

## 🧪 6. Testing & Verification Runbook

Before submitting or opening a PR, run the following verification commands:

### 1. Test Backend API Suite
```bash
cd backend
python -m pytest tests/test_api.py -v
```

### 2. Test Edge CV Suite
```bash
cd edge
python -m pytest tests/test_edge_pipeline.py -v
```

### 3. Run FastAPI Dev Server Locally
```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
# OpenAPI Docs available at http://localhost:8000/docs
```

### 4. Build React Dashboard
```bash
cd dashboard
npm run build
```

---

## 🚫 7. Hard Don'ts (Negative Constraints)

1. ❌ **DO NOT** import or re-create `firebase_writer.py` or connect to Firebase RTDB.
2. ❌ **DO NOT** make blocking network requests on the main GUI thread of the Edge App.
3. ❌ **DO NOT** use raw SQLite database transactions without WAL mode (`PRAGMA journal_mode = WAL;`).
4. ❌ **DO NOT** commit `.env`, `*.db`, `node_modules/`, `local_scans/`, or bulky `*.pt` training checkpoints to Git.
5. ❌ **DO NOT** hardcode database passwords or API keys in source files; always read from environment variables via `Settings`.
