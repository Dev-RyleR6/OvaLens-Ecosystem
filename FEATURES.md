# OvaLens Ecosystem — Complete Feature Guide & Technical Relevance

> **OvaLens** is an automated, industrial-grade duck egg candling, fertility classification, and hatchery analytics ecosystem developed for **Foundation University**.

This document details **what each feature does** across the **FastAPI Backend** and the **React Dashboard**, and **why it is relevant** for industrial duck hatchery operations, biological research, and academic Capstone defense.

---

## 📑 Table of Contents
1. [Backend Services & Core Logic (`backend/`)](#-1-backend-services--core-logic-backend)
   - [1.1 Cryptographic Auth & Sliding-Window Rate Limiter](#11-cryptographic-auth--sliding-window-rate-limiter)
   - [1.2 3-Tier Role-Based Access Control (RBAC) & Self-Lockout Defense](#12-3-tier-role-based-access-control-rbac--self-lockout-defense)
   - [1.3 28-Day Duck Incubation State Machine & Proactive Milestone Alerts](#13-28-day-duck-incubation-state-machine--proactive-milestone-alerts)
   - [1.4 Day 28 Biological Hatch Yield Forecast Engine](#14-day-28-biological-hatch-yield-forecast-engine)
   - [1.5 Idempotent Edge Ingestion (`ON CONFLICT DO NOTHING`)](#15-idempotent-edge-ingestion-on-conflict-do-nothing)
   - [1.6 Human-in-the-Loop Vision Override & Audit Trail](#16-human-in-the-loop-vision-override--audit-trail)
   - [1.7 Hatchery Economics: Day-10 Penoy Salvage & Power Savings](#17-hatchery-economics-day-10-penoy-salvage--power-savings)
   - [1.8 Automated Database Backup Service (Gzip Snapshots)](#18-automated-database-backup-service-gzip-snapshots)
   - [1.9 Dynamic PDF Research Audit Certificate & CSV Exporter](#19-dynamic-pdf-research-audit-certificate--csv-exporter)
2. [Dashboard UI Modules & Workflows (`dashboard/`)](#-2-dashboard-ui-modules--workflows-dashboard)
   - [2.1 Real-Time Overview & Live Candling Stream (`/`)](#21-real-time-overview--live-candling-stream-)
   - [2.2 Batch Lifecycle Management & Finalize Hatch Modal (`/batches`)](#22-batch-lifecycle-management--finalize-hatch-modal-batches)
   - [2.3 Scan Explorer with Dual View & Bounding Box HUD (`/scans`)](#23-scan-explorer-with-dual-view--bounding-box-hud-scans)
   - [2.4 Interactive Financial Simulator & Multi-Filter Analytics (`/analytics`)](#24-interactive-financial-simulator--multi-filter-analytics-analytics)
   - [2.5 Compliance Records & Certificate Download Hub (`/records`)](#25-compliance-records--certificate-download-hub-records)
   - [2.6 IoT Edge Station Health & Conveyor Calibration (`/devices`)](#26-iot-edge-station-health--conveyor-calibration-devices)
   - [2.7 AI Model Performance & Latency Benchmarks (`/models`)](#27-ai-model-performance--latency-benchmarks-models)
   - [2.8 User Administration & Operator Suspension Modal (`/users`)](#28-user-administration--operator-suspension-modal-users)
   - [2.9 Security Audit Trail & Severity Badges (`/logs`)](#29-security-audit-trail--severity-badges-logs)
   - [2.10 Facility Settings & Confirmation Modal (`/settings`)](#210-facility-settings--confirmation-modal-settings)
3. [Summary of Technical Relevance for Capstone Defense](#-3-summary-of-technical-relevance-for-capstone-defense)

---

## 🏛️ 1. Backend Services & Core Logic (`backend/`)

### 1.1 Cryptographic Auth & Sliding-Window Rate Limiter
* **What does it do?**
  - Secures the system with salted `bcrypt` password hashing and signed JSON Web Tokens (JWT).
  - Enforces a sliding-window rate limit on `/api/v1/auth/login` (restricts clients to a maximum of 10 failed login attempts per minute).
  - Automatically logs every login attempt (success or failure with IP address) to PostgreSQL audit logs.
* **How is it relevant?**
  - In a production agricultural facility or connected research lab, edge devices and web dashboards share a local network. Rate limiting prevents brute-force password cracking, and JWTs ensure session integrity across stateless HTTP requests.

---

### 1.2 3-Tier Role-Based Access Control (RBAC) & Self-Lockout Defense
* **What does it do?**
  - Enforces distinct permission levels across `ADMIN`, `MANAGER`, and `OPERATOR`.
  - Blocks operators from accessing sensitive endpoints (user management, database backups, price configuration).
  - Prevents an active administrator from suspending their own account (`HTTP 400 Bad Request`).
* **How is it relevant?**
  - Hatchery shift workers (operators) only need to run candling and view scans. Allowing operators to alter economic selling prices or delete users would create financial and operational risks. The self-lockout defense prevents accidental administrative lockout.

---

### 1.3 28-Day Duck Incubation State Machine & Proactive Milestone Alerts
* **What does it do?**
  - Manages the biological duck egg incubation timeline:
    $$\text{SETTING (Day 0)} \longrightarrow \text{DAY 10 (Candling)} \longrightarrow \text{DAY 18 (Lockdown/Hatcher)} \longrightarrow \text{DAY 25 (Piping)} \longrightarrow \text{HATCHED (Day 28)}$$
  - Proactively evaluates elapsed incubation days and raises actionable alarms when milestones are reached (e.g. *"CANDLING DUE: Day 10 Embryo Viability & Penoy Salvage"*).
* **How is it relevant?**
  - Duck eggs require strictly timed environmental shifts (temperature, humidity, turning). Missing Day 10 means infertile eggs rot inside the setter; missing Day 18 means eggs aren't moved to hatcher baskets before ducklings begin pipping. The state machine automates compliance and prevents human error.

---

### 1.4 Day 28 Biological Hatch Yield Forecast Engine
* **What does it do?**
  - Mathematical predictive engine that evaluates Day 10 detected fertility against breed-specific survival coefficients ($V_{\text{breed}}$: Kayumanggi $\approx 89\%$, Native Itim $\approx 84\%$, Khaki Campbell $\approx 86.5\%$).
  - Projects exact harvest numbers: $\text{Predicted Ducklings} = \lfloor \text{Set Count} \times (\text{Fertility Rate}) \times (V_{\text{breed}}) \rfloor$.
  - Automatically categorizes batch status into `OPTIMAL`, `WARNING`, or `CRITICAL` based on deviation from breed standards.
* **How is it relevant?**
  - Hatcheries typically have to wait until Day 28 to know how many ducklings will hatch. This engine provides an accurate forecast 18 days in advance, allowing managers to pre-sell ducklings to commercial buyers and detect incubator heater/humidity failures before the entire batch is lost.

---

### 1.5 Idempotent Edge Ingestion (`ON CONFLICT DO NOTHING`)
* **What does it do?**
  - Ingests batches of edge candling scans using PostgreSQL `ON CONFLICT (scan_id) DO NOTHING`.
* **How is it relevant?**
  - In agricultural facilities, Wi-Fi connections between conveyor belts and servers frequently drop. If the edge sync worker re-sends a packet upon reconnecting, PostgreSQL idempotently absorbs duplicates without corrupting total egg counts or skewing fertility calculations.

---

### 1.6 Human-in-the-Loop Vision Override & Audit Trail
* **What does it do?**
  - Allows an authorized operator to manually reclassify an egg (e.g., from `INFERTILE` to `FERTILE`) via `PATCH /api/v1/scans/{id}/override`.
  - Requires a mandatory justification note and automatically updates session totals and audit logs.
* **How is it relevant?**
  - No AI model is 100% infallible on unusual shell pigmentation or cracked shells. Human-in-the-loop validation gives operators final authority while maintaining a strict audit trail of every manual intervention.

---

### 1.7 Hatchery Economics: Day-10 Penoy Salvage & Power Savings
* **What does it do?**
  - Automatically calculates the financial cash recovery of unfertilized eggs:
    $$\text{Salvage Cash (₱)} = \text{Infertile Egg Count} \times \text{Penoy Market Price (₱14.00)}$$
  - Calculates thermal energy saved by removing infertile eggs 18 days before hatch:
    $$\text{Power Saved (kWh)} = \text{Infertile Eggs} \times 18\text{ days} \times 0.015\text{ kWh/day}$$
* **How is it relevant?**
  - In traditional Philippine duck hatcheries, infertile eggs candled on Day 10 are sold as *Penoy* (a popular commercial delicacy). If left in the incubator until Day 28, they rot, waste electricity, risk exploding, and lose 100% of their commercial food value. This feature proves the direct ROI of automated candling.

---

### 1.8 Automated Database Backup Service (Gzip Snapshots)
* **What does it do?**
  - Creates timestamped, gzip-compressed JSON snapshots of all 7 PostgreSQL tables with a single API call (`POST /api/v1/settings/backups/create`).
* **How is it relevant?**
  - Protects academic research datasets and commercial hatchery records against hardware failure, disk corruption, or accidental deletions.

---

### 1.9 Dynamic PDF Research Audit Certificate & CSV Exporter
* **What does it do?**
  - Compiles an official **Foundation University Candling Inspection & Research Audit Certificate** in PDF format using ReportLab.
  - Dynamically populates live batch metadata, candled fertility %, Penoy revenue, power saved, and official sign-off lines for the **Lead Researcher & Project Proponent** and **Hatchery Operations Supervisor**.
* **How is it relevant?**
  - Provides formal documentation for university compliance, thesis defense evaluation, buyer certification, and agricultural quality assurance.

---

## 💻 2. Dashboard UI Modules & Workflows (`dashboard/`)

### 2.1 Real-Time Overview & Live Candling Stream (`/`)
* **What does it do?**
  - Displays high-level KPI cards (Total Eggs Scanned, Average Fertility %, Penoy Salvaged, Hatched Count).
  - Shows an active batch timeline and a live stream of recently classified eggs.
* **How is it relevant?**
  - Gives hatchery supervisors an immediate bird's-eye view of active candling operations without navigating into complex sub-menus.

---

### 2.2 Batch Lifecycle Management & Finalize Hatch Modal (`/batches`)
* **What does it do?**
  - Tabulates all active and completed incubation cohorts.
  - Provides a 1-click **"Advance Stage"** button that validates incubation timeline transitions.
  - Includes a **Finalize Hatch Trial Modal** to input final hatched ducklings and calculate actual hatchability %.
* **How is it relevant?**
  - Eliminates manual whiteboard/paper tracking in the hatchery. Operators can see exactly which batch is due for candling, lockdown, or harvest today.

---

### 2.3 Scan Explorer with Dual View & Bounding Box HUD (`/scans`)
* **What does it do?**
  - Provides both a **Card Grid View** (displaying egg images) and a **Data Table View**.
  - Clicking any egg opens a deep inspection drawer showing YOLOv8 bounding boxes, class probabilities, HSV luminance levels, and inference latency (ms).
  - Includes the **Human-in-the-Loop Vision Override Modal**.
* **How is it relevant?**
  - Essential for researchers auditing AI performance, verifying edge cases, and demonstrating the accuracy of the YOLOv8 ONNX vision model during panel demonstrations.

---

### 2.4 Interactive Financial Simulator & Multi-Filter Analytics (`/analytics`)
* **What does it do?**
  - Features a multi-filter toolbar to isolate analytics by **Duck Breed** (Kayumanggi, Native Itim, Khaki Campbell), **Status**, or **Individual Batch**.
  - Displays the **Day 28 Biological Forecast Card** with predicted duckling counts, hatchability %, and advisory notes.
  - Includes an interactive **Financial Simulator** with real-time sliders to model Penoy price fluctuations (₱10 to ₱25/egg) and electric utility tariffs.
* **How is it relevant?**
  - Transforms raw classification numbers into actionable business intelligence. Hatchery owners can forecast revenue and optimize their commercial pricing models.

---

### 2.5 Compliance Records & Certificate Download Hub (`/records`)
* **What does it do?**
  - Central repository for all historical batch runs.
  - Provides 1-click buttons to download signed **PDF Certificates** and raw **CSV Datasets**.
* **How is it relevant?**
  - Allows researchers to export raw CSV datasets into statistical tools (SPSS, R, Python) for empirical Capstone thesis analysis.

---

### 2.6 IoT Edge Station Health & Conveyor Calibration (`/devices`)
* **What does it do?**
  - Monitors the connectivity status of edge candling units (Raspberry Pi 5 / PC / ESP32).
  - Displays conveyor belt speed ($v$), distance to diverter chute ($D$), and servo actuation timing ($\Delta t = D / v$).
* **How is it relevant?**
  - Ensures hardware synchronization between the optical camera and the physical diverter flap, preventing physical sorting jams.

---

### 2.7 AI Model Performance & Latency Benchmarks (`/models`)
* **What does it do?**
  - Displays model registry metadata (YOLOv8 ONNX FP16 weights, mAP@50 accuracy, and inference latencies $\le 35\text{ms}$).
* **How is it relevant?**
  - Demonstrates that the computer vision model satisfies real-time industrial conveyor throughput constraints ($\ge 60\text{ eggs/min}$).

---

### 2.8 User Administration & Operator Suspension Modal (`/users`)
* **What does it do?**
  - Allows administrators to invite new managers and operators.
  - Features an account suspension toggle protected by a **Confirmation Modal** with danger warnings.
* **How is it relevant?**
  - Protects station security by ensuring only certified personnel can operate the candling machinery or access hatchery records.

---

### 2.9 Security Audit Trail & Severity Badges (`/logs`)
* **What does it do?**
  - Displays a chronological, searchable log of all actions taken in the system, color-coded by severity (`INFO`, `WARNING`, `SECURITY`).
* **How is it relevant?**
  - Provides transparency and accountability. If a batch status is changed or a price is modified, supervisors can immediately see who performed the action, from what IP address, and at what timestamp.

---

### 2.10 Facility Settings & Confirmation Modal (`/settings`)
* **What does it do?**
  - Allows configuration of baseline Penoy selling price, duckling price, utility electricity rates, and vision confidence thresholds.
  - Any mutating economic price change opens a **Confirmation Modal** with a before-and-after diff preview ($P_{\text{old}} \to P_{\text{new}}$).
  - Includes the **1-Click Database Backup** button.
* **How is it relevant?**
  - Prevents accidental price changes from instantly distorting historical economic yield calculations facility-wide.

---

## 🎯 3. Summary of Technical Relevance for Capstone Defense

| Evaluation Area | How OvaLens Delivers | Key Supporting Features |
| :--- | :--- | :--- |
| **Academic Rigor & Innovation** | Combines edge AI computer vision with biological embryonic prediction models. | YOLOv8 ONNX FP16 engine, Breed Survival Math, Day 28 Yield Forecast. |
| **Agricultural & Economic Impact** | Solves the real-world problem of unfertilized egg waste in Philippine duck hatcheries. | Day 10 *Penoy* Salvage Calculator, Thermal Power Savings, Financial Simulator. |
| **Industrial Engineering Standards** | Multi-threaded edge concurrency, non-blocking serial communication, and idempotent sync. | CustomTkinter 60 FPS GUI, SQLite WAL mode, PostgreSQL `ON CONFLICT DO NOTHING`. |
| **Security & Data Integrity** | Enterprise RBAC, audit logging, rate limiting, and automated backups. | JWT Auth, Sliding-Window Limiter, Confirmation Modals, Gzip DB Backups. |
| **Institutional Compliance** | Official Foundation University reporting and certification. | ReportLab PDF Inspection Certificates with dynamic academic sign-offs. |
