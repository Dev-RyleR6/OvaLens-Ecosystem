# Changelog

All notable changes to the **OvaLens** Capstone Ecosystem will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Fixed
- **Edge**: [TASK-NEW-EDGE-RUNTIME-01] select project Python before loading packages (2026-10-08)
- **Dashboard**: [TASK-NEW-DASH-CLOSE-06] standardize close buttons across overlays (2026-10-07)
- **Dashboard**: [TASK-NEW-DASH-STATUS-05] unify incubation status across pages (2026-10-07)
- **Dashboard**: [TASK-NEW-DASH-CHART-04] align operational charts and badge semantics (2026-10-07)
- **Dashboard**: [TASK-NEW-DASH-TABLE-03] correct batch table layout and floating actions (2026-10-07)
- **Dashboard**: [TASK-NEW-DASH-RESP-01] improve responsive layouts and reconcile analytics (2026-10-07)
- **Dashboard**: [TASK-NEW-DASH-LIVE-01] restore analytics charts and edge app heartbeats (2026-10-07)
- **Dashboard**: [TASK-NEW-DASH-UX-01] improve operational UX and truthful telemetry (2026-10-07)
- **Edge**: [TASK-NEW-EDGE-FLOW-01] add single-click diagnostic flow, isolated correlated inference with deadlines, retryable finalization, target completion, consistent controls, and strict session/batch validation (2026-10-06).
- **Firmware**: [TASK-NEW-FW-DET-01] require sustained confident egg classification (2026-10-02)
- **Firmware**: [TASK-NEW-FW-CYCLE-01] set default stepper delay to 1000 microseconds (2026-10-02)
- **Firmware**: [TASK-NEW-FW-CYCLE-01] use 1000-step travel with midpoint servo blocking (2026-10-02)
- **Firmware**: [TASK-NEW-FW-CYCLE-01] wait for detection readiness and servo settling (2026-10-02)
- **Firmware**: [TASK-NEW-FW-APP-01] preserve explicit egg/servo port assignments, add the COM5/COM7 hardware launcher, and display deployed controller status replies (2026-10-02).

### Added
- **Edge**: [TASK-NEW-EDGE-SETUP-01] simplify default station setup (2026-10-08)
- **Edge**: [TASK-NEW-EDGE-3BOARD-01] integrate three-board candling rig (2026-10-08)
- **Edge**: [TASK-NEW-EDGE-UI-POLISH-01] improve operator typography and status performance (2026-10-07)
- **Edge**: [TASK-NEW-EDGE-CONTROL-01] integrate dual-board sorting and camera defaults (2026-10-07)
- **Dashboard**: [TASK-NEW-DASH-BRAND-02] refresh branding and incubation batch layout (2026-10-07)
- **Backend**: [TASK-NEW-BE-SCHEMA-01] align database schema contracts for manual reviews and metrics (2026-10-07)
- **Dashboard**: [TASK-NEW-DASH-LOGO-01] use supplied OvaLens logo (2026-10-07)
- **Edge**: launch operator app in full screen mode by default (2026-10-07)
- **Dashboard**: bundle and enforce plus jakarta sans font across all components (2026-10-06)
- **Edge App & Firmware**: [TASK-EDGE-TRK-01 / TASK-FW-STP-01] engineered event-driven ChamberController FSM, dedicated InferenceWorker thread, StartupConfigWindow pre-operation batch dialog, and ESP32 motor commands (2026-10-05).
- **Firmware**: [TASK-NEW-FW-CYCLE-01] add automatic stepper camera and servo cycle (2026-10-02)
- **Firmware**: [TASK-NEW-FW-DET-01] optimize operator workspace and add egg detection (2026-10-02)
- **Firmware**: [TASK-NEW-FW-APP-01] integrate egg and servo prototype controls (2026-10-02)
- **Workflow**: establish multi-agent orchestra and cross-agent communication protocols (2026-09-15)
- **Workflow**: [TASK-DOC-03] integrate automated task checklist and global agent protocol into workflow (2026-09-15)
- Created `PROJECT_PLAN.md` living task backlog mapped to Design Science Research Methodology (DSRM) and Agile iteration cycles.
- Integrated automated verification and conventional commit workflow (`scripts/verify_and_commit.py`).
- Added Input-Process-Output (IPO) academic matrix (`IPO_Academic_Final.drawio` & `.html`) to `docs/diagrams/architecture/`.
- Added 7-phase DSRM Research Methodology diagram (`Methodology_Updated.drawio` & `.html`) to `docs/diagrams/architecture/`.
- Added OvaLens Master System Activity Flowchart (`Systemflow_chart_final.drawio` & `.html`) to `docs/diagrams/flowcharts/`.
- Added Master UML Use Case Diagram (`OvaLens_Use_Case_Diagram.drawio` & `.html`) to `docs/diagrams/use_cases/`.
- Updated Capstone Manuscript Chapters 1, 2, 3, and References in `docs/manuscript/` with authentic proposal text and 15 APA 7th academic citations.

### Changed
- **Firmware**: [TASK-NEW-FW-INSTALL-01] install and verify three-board v3 builds (2026-10-08)
- **Edge**: [TASK-NEW-EDGE-DESIGN-02] focus operator design on camera and sorting (2026-10-07)
- **Dashboard**: [TASK-NEW-DASH-DESIGN-01] replace Plus Jakarta Sans with self-hosted IBM Plex Sans; unify controls, status badges, navigation and purposeful icons; adapt cards, tables and forms to available width; improve keyboard interactions, authenticated backup downloads and truthful candling records; preserve local batch-date instants and distinguish pending review from low confidence (2026-10-07).
- **Agents**: [TASK-NEW-AGENTS-IGNORE-01] ignore local AI tooling and unused logo copy (2026-10-07)
- **Dashboard**: improve ui/ux responsiveness and eliminate ai slop (2026-10-06)
- **Dashboard**: streamline web app into defense-ready 5-page portal; consolidate historical records into Batches and Analytics, prune mock MLOps ModelsPage and redundant AuditLogsPage, remove synthetic 42-slot tray matrix in favor of linear conveyor velocity telemetry, eliminate audio beeps, and convert financial simulator into data-driven Day 10 economic recovery model (2026-10-06).
- **System scope**: [TASK-NEW-SCOPE-01] standardize OvaLens on Day 10 candling with the strict `FERTILE`/`INFERTILE` class contract across backend, edge, dashboard, firmware, tests, and documentation (2026-09-30).
- **Data compatibility**: add one-way PostgreSQL and automatic edge SQLite migration paths that merge legacy `ABNORMAL` outcomes into `INFERTILE` before removing obsolete stages and counters (2026-09-30).

---

## [0.2.0] - 2026-03-14

### Added
- **Backend**: FastAPI REST API with Pydantic v2 schemas and SQLAlchemy 2.0 ORM.
- **Backend**: Idempotent scan ingestion (`POST /api/v1/scans/batch`) with `ON CONFLICT DO NOTHING`.
- **Backend**: Day 10 Penoy economic yield calculation service (₱14.00/egg salvage value).
- **Backend**: Automated PDF and CSV batch report generation with ReportLab and pandas.
- **Edge**: Multi-threaded CV engine (Frame Grabber, ONNX Inference, PySerial ESP32 worker, SQLite sync worker).
- **Edge**: Local SQLite WAL mode storage ensuring offline-first resilience.
- **Firmware**: ESP32 hardware interrupt on GPIO 14 with 600ms optical sensor debounce lockout.
- **Dashboard**: React 18 + Vite + TypeScript web portal with Foundation University theme tokens (`#800000`, `#357a38`).
- **Dashboard**: Interactive 42-slot Incubation Tray Matrix ($A1 \to F7$) and real-time mortality trend charts.
- **Testing**: Automated backend test suite (`tests/test_api.py`) with 13 passing unit and integration tests.
- **Testing**: Automated edge pipeline test suite (`tests/test_edge_pipeline.py`).

### Security
- Added JWT authentication and password hashing with bcrypt.
- Added Role-Based Access Control (RBAC) separating Candling Worker, Supervisor, and Administrator permissions.
- Protected database credentials and JWT secrets using Pydantic Settings and `.env` encapsulation.

---

## [0.1.0] - 2026-02-01

### Added
- Initial project conceptualization and Foundation University Capstone registration.
- YOLOv8 model evaluation for 3-class duck egg candling (`FERTILE`, `INFERTILE`, `ABNORMAL`).
- Monorepo structure initialization (`backend/`, `edge/`, `dashboard/`, `firmware/`, `docs/`).

