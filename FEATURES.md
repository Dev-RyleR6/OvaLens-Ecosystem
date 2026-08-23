# OvaLens Ecosystem — Complete Feature & Technical Specification

> **OvaLens** is an automated, industrial-grade duck egg candling, fertility classification, and hatchery analytics ecosystem developed for **Foundation University**.

This document serves as the **Master Feature Specification** detailing every capability, mathematical formula, security guard, and integration layer across the **Central FastAPI Backend** and the **React Admin Dashboard**.

---

## 📑 Table of Contents
1. [Backend Features & Services (`backend/`)](#-1-backend-features--services-backend)
   - [1.1 Authentication & Session Security (`/auth`)](#11-authentication--session-security-auth)
   - [1.2 User Administration & Access Control (`/users`)](#12-user-administration--access-control-users)
   - [1.3 Incubation Batch State Machine & Milestones (`/batches`)](#13-incubation-batch-state-machine--milestones-batches)
   - [1.4 Day 28 Biological Hatch Yield Forecast Engine (`/batches/{id}/forecast`)](#14-day-28-biological-hatch-yield-forecast-engine-batchesidforecast)
   - [1.5 Edge Scans & Idempotent Ingestion (`/scans`)](#15-edge-scans--idempotent-ingestion-scans)
   - [1.6 Candling Shift Management (`/sessions`)](#16-candling-shift-management-sessions)
   - [1.7 Edge Sorter Telemetry & Fleet Management (`/devices`)](#17-edge-sorter-telemetry--fleet-management-devices)
   - [1.8 Hatchery Analytics & Economics Engine (`/analytics`)](#18-hatchery-analytics--economics-engine-analytics)
   - [1.9 Automated Database Backup Engine (`/settings/backups`)](#19-automated-database-backup-engine-settingsbackups)
   - [1.10 Official Inspection Certificates & Dataset Exporters (`/reports`)](#110-official-inspection-certificates--dataset-exporters-reports)
   - [1.11 System Audit Trail & Security Compliance (`/audit-logs`)](#111-system-audit-trail--security-compliance-audit-logs)
2. [Dashboard Features & UI Modules (`dashboard/`)](#-2-dashboard-features--ui-modules-dashboard)
   - [2.1 Overview & Real-Time Operational Feed (`/`)](#21-overview--real-time-operational-feed-)
   - [2.2 Batch Lifecycle Management & Finalize Hatch Modal (`/batches`)](#22-batch-lifecycle-management--finalize-hatch-modal-batches)
   - [2.3 Scan Explorer & Human-in-the-Loop Vision Inspector (`/scans`)](#23-scan-explorer--human-in-the-loop-vision-inspector-scans)
   - [2.4 Hatchery Economics, Batch Filter & Forecast Card (`/analytics`)](#24-hatchery-economics-batch-filter--forecast-card-analytics)
   - [2.5 Compliance Records & Certificate Archive (`/records`)](#25-compliance-records--certificate-archive-records)
   - [2.6 Edge Station Fleet Health & Telemetry (`/devices`)](#26-edge-station-fleet-health--telemetry-devices)
   - [2.7 AI Vision Model Performance & Benchmarks (`/models`)](#27-ai-vision-model-performance--benchmarks-models)
   - [2.8 User Administration & Operator Suspension Modal (`/users`)](#28-user-administration--operator-suspension-modal-users)
   - [2.9 Security Audit Trail & Event Severity Categorization (`/logs`)](#29-security-audit-trail--event-severity-categorization-logs)
   - [2.10 Facility Settings, Economic Prices & Confirmation Modal (`/settings`)](#210-facility-settings-economic-prices--confirmation-modal-settings)
3. [Subsystem Integration Matrix](#-3-subsystem-integration-matrix)

---

## 🏛️ 1. Backend Features & Services (`backend/`)

The backend is built on **Python 3.11+ / FastAPI** with **SQLAlchemy 2.0 declarative models** and **PostgreSQL 16**.

### 1.1 Authentication & Session Security (`/auth`)
* **Cryptographic Password Hashing**: Passwords are encrypted using salted `bcrypt` algorithms (with fallback SHA-256 HMAC).
* **JWT Access Tokens**: Issues signed JSON Web Tokens encoding user subject, assigned role, expiration timestamp, and issuance time.
* **Sliding-Window IP Rate Limiting**: Protects `/api/v1/auth/login` against brute-force attacks by restricting clients to a maximum of 10 failed login attempts per 60-second window.
* **Authentication Audit Logging**: Automatically records every failed login attempt (`USER_LOGIN_FAILED` with client IP and reason) and successful login (`USER_LOGIN_SUCCESS`) into the immutable PostgreSQL audit log.

### 1.2 User Administration & Access Control (`/users`)
* **3-Tier Role-Based Access Control (RBAC)**:
  - `ADMIN`: Full user administration, facility price updates, and database maintenance.
  - `MANAGER`: Cohort creation, stage advancements, settings updates, and certificate generation.
  - `OPERATOR`: Candling shift execution, real-time scan inspection, and vision overrides.
* **Self-Deactivation Guard**: Prevents an active administrator from accidentally suspending their own account (`HTTP 400 Bad Request`).
* **Operator Account Status Toggling**: `PATCH /api/v1/users/{id}/status` instantly activates or revokes station/dashboard login credentials with audit trail logging.

### 1.3 Incubation Batch State Machine & Milestones (`/batches`)
* **28-Day Duck Incubation State Machine**:
  $$\text{SETTING (Day 0)} \longrightarrow \text{DAY 10 (Candling)} \longrightarrow \text{DAY 18 (Lockdown/Hatcher)} \longrightarrow \text{DAY 25 (Piping)} \longrightarrow \text{HATCHED (Day 28)}$$
* **Automated Due-Date Milestone Checker**: `POST /api/v1/batches/check-milestones` evaluates elapsed days ($\text{elapsed} = \text{now} - \text{set\_date}$) and raises proactive alerts:
  - *Day 10*: Candling Due (Embryo Viability & Penoy Salvage).
  - *Day 18*: Transfer Due (Lockdown into Hatcher Trays).
  - *Day 25*: Piping Watch (Final Hatch Preparation).
  - *Day 28*: Hatch Finalization Due.
* **Hatch Trial Finalization**: `POST /api/v1/batches/{id}/finalize-hatch` records actual hatched vs unhatched counts and stamps the batch as `COMPLETED`.

### 1.4 Day 28 Biological Hatch Yield Forecast Engine (`/batches/{id}/forecast`)
* **Biological Viability Retention Model**: Evaluates detected Day 10 fertility against breed-specific survival coefficients ($V_{\text{breed}}$: Kayumanggi $\approx 89.0\%$, Native Itim $\approx 84.0\%$, Khaki Campbell $\approx 86.5\%$).
* **Predictive Formulae**:
  $$\text{Predicted Hatched} = \left\lfloor \text{Initial Set Eggs} \times \left(\frac{\text{Detected Fertility}}{100}\right) \times \left(\frac{V_{\text{breed}}}{100}\right) \right\rfloor$$
  $$\text{Forecasted Revenue} = (\text{Penoy Count} \times P_{\text{penoy}}) + (\text{Predicted Hatched} \times P_{\text{duckling}})$$
* **Incubator Anomaly Diagnostics**:
  - `OPTIMAL`: Normal embryonic development trajectory.
  - `WARNING`: Detected fertility is $8\text{--}15\%$ below breed standard.
  - `CRITICAL`: Severe fertility drop ($> 15\%$), automatically triggering an alert to inspect setter temperature, humidity calibration, or breeder flock nutrition.

### 1.5 Edge Scans & Idempotent Ingestion (`/scans`)
* **Idempotent Ingestion**: `POST /api/v1/scans/sync` utilizes PostgreSQL `ON CONFLICT (scan_id) DO NOTHING`. Network packets duplicated over unreliable Wi-Fi are absorbed safely without creating duplicate database rows.
* **Human-in-the-Loop Vision Override**: `PATCH /api/v1/scans/{id}/override` allows an authorized operator to correct an AI misclassification with mandatory justification logging (`MANUAL_CLASSIFICATION_OVERRIDE`) and automatically recalculates parent candling session rollups.

### 1.6 Candling Shift Management (`/sessions`)
* **Edge Sorter Session Lifecycle**: Tracks `started_at`, `ended_at`, assigned `operator_name`, candling `stage`, total eggs scanned, and class distribution (`fertile_count`, `infertile_count`, `abnormal_count`).
* **Inference Speed Profiling**: Computes running average inference latency in milliseconds ($\le 35\text{ms}$).

### 1.7 Edge Sorter Telemetry & Fleet Management (`/devices`)
* **Machine Registration & Calibration**: Tracks hardware platform (Raspberry Pi 5 / PC), model weight version (`best.onnx`), conveyor belt speed ($v$), distance ($D$), and servo pulse duration.
* **Heartbeat Telemetry Ping**: `POST /api/v1/devices/{id}/heartbeat` keeps station online/offline statuses synchronized.

### 1.8 Hatchery Analytics & Economics Engine (`/analytics`)
* **Day-10 Penoy Salvage Cash Recovery**:
  $$\text{Penoy Salvage (₱)} = \text{Infertile Egg Count} \times P_{\text{penoy}}$$
* **Incubator Thermal Energy Savings**:
  $$\text{Energy Saved (kWh)} = \text{Infertile Eggs} \times 18\text{ remaining days} \times 0.015\text{ kWh/egg/day}$$
  $$\text{Electricity Savings (₱)} = \text{Energy Saved (kWh)} \times \text{Tariff Rate (₱/kWh)}$$
* **Mortality Progression Breakdown**: Traces early embryonic death (Day 10 blood rings), mid-incubation failure (Day 18), and dead-in-shell pipping mortality (Day 25).

### 1.9 Automated Database Backup Engine (`/settings/backups`)
* **Gzip Compressed Snapshots**: Serializes all relational models into timestamped, gzip-compressed archives stored in `backend/backups/ovalens_backup_*.json.gz`.
* **API Triggers**: `POST /api/v1/settings/backups/create` and `GET /api/v1/settings/backups` provide 1-click administrative backup creation.

### 1.10 Official Inspection Certificates & Dataset Exporters (`/reports`)
* **PDF Inspection Certificate**: `GET /api/v1/reports/batch/{id}/pdf` dynamically compiles an official **Foundation University Candling Inspection & Research Audit Certificate** featuring:
  - Batch metadata, duck breed, incubator unit, and target hatch dates.
  - Candled fertility rate % and final hatchability rate %.
  - Penoy economic cash recovery and thermal power savings.
  - Multi-session operator candling logs with inference latencies.
  - Official sign-off blocks stamped with the **Lead Researcher & Project Proponent** and **Hatchery Operations Supervisor**.
* **CSV Dataset Export**: `GET /api/v1/reports/batch/{id}/csv` streams the complete raw candling dataset including UUIDs, YOLOv8 confidence scores, and bounding boxes.

### 1.11 System Audit Trail & Security Compliance (`/audit-logs`)
* **Immutable Event Log**: Captures user logins, batch creations, stage advancements, settings updates, user status toggles, and manual classification overrides.
* **Dynamic Severity Derivation**: Assigns `INFO`, `WARNING`, or `SECURITY` severity tags to events based on risk.

---

## 💻 2. Dashboard Features & UI Modules (`dashboard/`)

The dashboard is built on **React 18 + Vite + TypeScript + TailwindCSS + Lucide Icons + Recharts + TanStack Query**.

### 2.1 Overview & Real-Time Operational Feed (`/`)
* **Executive KPI Cards**: Real-time counters for Total Eggs Candled, Average Fertility Rate %, Penoy Salvaged Count, and Hatched Ducklings.
* **Duck Breed Fertility Comparison Chart**: Visual bar charts comparing commercial performance of Kayumanggi vs Native Itim vs Khaki Campbell.
* **Active Batch Milestones**: Status timeline showing current incubation stages across all active incubators.
* **Live Inspection Activity Feed**: Visual stream of recent candled eggs with classification tags, timestamps, and confidence scores.

### 2.2 Batch Lifecycle Management & Finalize Hatch Modal (`/batches`)
* **Comprehensive Batch Table**: Displays batch code, duck breed, incubator unit, initial egg count, elapsed days, and current status.
* **Stage Progression Action**: 1-click stage advancement (`Advance Stage`) with state machine validation.
* **Finalize Hatch Trial Modal** ([`FinalizeHatchModal.tsx`](file:///d:/Ryle_Gabotero/side_projects/Capstone/dashboard/src/components/FinalizeHatchModal.tsx)): Asks for actual hatched and unhatched counts, computes final hatchability %, and updates the batch.
* **1-Click Certificate & Dataset Downloads**: Direct links to stream official ReportLab PDF certificates and CSV datasets.

### 2.3 Scan Explorer & Human-in-the-Loop Vision Inspector (`/scans`)
* **Dual View Modes**: Switch seamlessly between **Card Grid View** (showing high-res egg candling frames) and **Data Table View**.
* **Multi-Parameter Filter Toolbar**: Filter scans by biological class (`FERTILE`, `INFERTILE`, `ABNORMAL`), batch ID, and date.
* **Vision Inspection Drawer**: Deep inspection HUD displaying YOLOv8 bounding box coordinates, HSV luminance levels, and camera exposure.
* **Human-in-the-Loop Override Modal** ([`HumanInTheLoopOverrideModal.tsx`](file:///d:/Ryle_Gabotero/side_projects/Capstone/dashboard/src/components/HumanInTheLoopOverrideModal.tsx)): Allows operators to override classifications with mandatory justification notes, logged directly to PostgreSQL.

### 2.4 Hatchery Economics, Batch Filter & Forecast Card (`/analytics`)
* **Multi-Filter Batch Toolbar**: Narrow analytics facility-wide or select individual batches with secondary **Duck Breed** and **Status** filters.
* **Day 28 Biological Forecast Card** ([`BatchForecastCard.tsx`](file:///d:/Ryle_Gabotero/side_projects/Capstone/dashboard/src/components/BatchForecastCard.tsx)): Displays predicted duckling harvest count, estimated hatchability %, Penoy cash recovery, and automated incubator advisory notices.
* **Interactive Financial Salvage Simulator**: Real-time sliders allowing hatchery managers to simulate custom Penoy market prices (₱10 to ₱25/egg) and utility electricity tariffs.
* **28-Day Embryo Viability Curve**: Recharts area visualization of early, mid, and late embryonic mortality progression.

### 2.5 Compliance Records & Certificate Archive (`/records`)
* **Institutional Archive**: Central hub for completed incubation trials and historical batch performance.
* **PDF & CSV Export Actions**: Instantly generate and download signed inspection certificates.

### 2.6 Edge Station Fleet Health & Telemetry (`/devices`)
* **Station Fleet Cards**: Displays edge hardware platform, connection health, local IP address, and active ONNX weight versions.
* **Conveyor Calibration Parameters**: Displays mechanical timing ($\Delta t = D / v$) and optical sensor debounce lockout settings.

### 2.7 AI Vision Model Performance & Benchmarks (`/models`)
* **Model Registry**: Tracks YOLOv8 ONNX model releases, FP16 quantization benchmarks, mAP@50 accuracy, and inference latencies.

### 2.8 User Administration & Operator Suspension Modal (`/users`)
* **Personnel Management**: Admin interface to create new operator/manager credentials.
* **Account Suspension Confirmation Prompt** ([`ConfirmationModal.tsx`](file:///d:/Ryle_Gabotero/side_projects/Capstone/dashboard/src/components/ui/ConfirmationModal.tsx)): Prevents accidental operator lockout during active candling shifts with a structured danger confirmation modal.

### 2.9 Security Audit Trail & Event Severity Categorization (`/logs`)
* **Live Audit Explorer**: Searchable event logs showing operator name, event action, entity type, IP address, and timestamp.
* **Severity Badging**: Color-coded badges for `INFO`, `WARNING`, and `SECURITY` events.

### 2.10 Facility Settings, Economic Prices & Confirmation Modal (`/settings`)
* **Economic Valuation Settings**: Configure market selling prices for Day-10 Penoy (₱/egg), Day-28 Ducklings (₱/duckling), and Electricity Tariff (₱/kWh).
* **Vision Confidence Threshold Slider**: Set minimum AI confidence threshold ($80\%\text{--}99\%$).
* **Price Change Confirmation Prompt**: Displays an interactive parameter diff box ($P_{\text{old}} \to P_{\text{new}}$) warning the manager of immediate financial yield calculation updates before committing.
* **1-Click Database Backup Trigger**: Admin button to trigger automated PostgreSQL snapshots.

---

## 🔗 3. Subsystem Integration Matrix

| Subsystem | Port / Protocol | Auth Mechanism | Primary Purpose |
| :--- | :--- | :--- | :--- |
| **Physical Sorter (`firmware/`)** | `115200 baud UART` | Hardware Interrupt | Detects egg arrival, fires diverter servo within calculated $\Delta t$. |
| **Edge CV (`edge/`)** | `DirectShow / V4L2` | Local SQLite WAL | 60 FPS frame grabber, ONNX FP16 inference, CustomTkinter operator GUI. |
| **Sync Worker (`edge/src/sync/`)** | `HTTP POST /api/v1/scans/sync` | `X-API-Key` Header | Asynchronously syncs local SQLite scans to central PostgreSQL. |
| **Central Backend (`backend/`)** | `HTTP Port 8000` | `Bearer JWT` / `X-API-Key` | Central business logic, forecast engine, ReportLab PDF generator, PostgreSQL 16. |
| **Admin Dashboard (`dashboard/`)** | `HTTP Port 3000 / 5173` | `Bearer JWT` | Executive analytics, batch management, certificate export, and settings. |
