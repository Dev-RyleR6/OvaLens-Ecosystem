# Changelog

All notable changes to the **OvaLens** Capstone Ecosystem will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Fixed
- **Firmware**: [TASK-NEW-FW-CYCLE-01] wait for detection readiness and servo settling (2026-10-02)
- **Firmware**: [TASK-NEW-FW-APP-01] preserve explicit egg/servo port assignments, add the COM5/COM7 hardware launcher, and display deployed controller status replies (2026-10-02).

### Added
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

