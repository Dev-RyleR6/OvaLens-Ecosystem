# OvaLens System Diagrams & Architectural Schematics

This directory contains architectural blueprints, hardware wiring schematics, operational flowcharts, and database Entity-Relationship Diagrams (ERDs) for the **OvaLens** Capstone manuscript and defense presentation.

---

## 📁 Diagram Subdirectories

* [`architecture/`](file:///d:/Ryle_Gabotero/side_projects/Capstone/docs/diagrams/architecture): High-level monorepo topology, Input-Process-Output (IPO) framework, and DSRM research methodology.
* [`flowcharts/`](file:///d:/Ryle_Gabotero/side_projects/Capstone/docs/diagrams/flowcharts): System activity flowchart, candling inference flow, and diverter kinematics state machines.
* [`hardware_schematics/`](file:///d:/Ryle_Gabotero/side_projects/Capstone/docs/diagrams/hardware_schematics): ESP32 pinouts, relay connections, power rails, and optical beam-break sensor debouncing.
* [`database_erds/`](file:///d:/Ryle_Gabotero/side_projects/Capstone/docs/diagrams/database_erds): PostgreSQL 16 relational database schema and SQLite WAL edge data models.
* [`use_cases/`](file:///d:/Ryle_Gabotero/side_projects/Capstone/docs/diagrams/use_cases): UML Use Case diagrams, actor permissions, and operational scopes.

### 📊 Master Diagram Matrix

| Subsystem / Purpose | Editable Model (`.drawio`) | Interactive Browser View (`.html`) | Category |
| :--- | :--- | :--- | :--- |
| **Input-Process-Output (IPO) Matrix** | [`IPO_Academic_Final.drawio`](file:///d:/Ryle_Gabotero/side_projects/Capstone/docs/diagrams/architecture/IPO_Academic_Final.drawio) | [`IPO_Academic_Final.drawio.html`](file:///d:/Ryle_Gabotero/side_projects/Capstone/docs/diagrams/architecture/IPO_Academic_Final.drawio.html) | Conceptual Framework |
| **Research Methodology (DSRM + Agile)** | [`Methodology_Updated.drawio`](file:///d:/Ryle_Gabotero/side_projects/Capstone/docs/diagrams/architecture/Methodology_Updated.drawio) | [`Methodology_Updated.drawio.html`](file:///d:/Ryle_Gabotero/side_projects/Capstone/docs/diagrams/architecture/Methodology_Updated.drawio.html) | Methodology Architecture |
| **System Activity & Candling Flowchart** | [`Systemflow_chart_final.drawio`](file:///d:/Ryle_Gabotero/side_projects/Capstone/docs/diagrams/flowcharts/Systemflow_chart_final.drawio) | [`Systemflow_chart_final.drawio.html`](file:///d:/Ryle_Gabotero/side_projects/Capstone/docs/diagrams/flowcharts/Systemflow_chart_final.drawio.html) | Operational Logic |
| **Master UML Use Case Diagram** | [`OvaLens_Use_Case_Diagram.drawio`](file:///d:/Ryle_Gabotero/side_projects/Capstone/docs/diagrams/use_cases/OvaLens_Use_Case_Diagram.drawio) | [`OvaLens_Use_Case_Diagram.drawio.html`](file:///d:/Ryle_Gabotero/side_projects/Capstone/docs/diagrams/use_cases/OvaLens_Use_Case_Diagram.drawio.html) | Role & Permissions |

---

## 🏛️ 1. High-Level System Architecture Diagram

```mermaid
graph TD
    subgraph Physical_Conveyor["Physical Candling Sorter (Conveyor Lane 1)"]
        Egg["Duck Egg on Roller"]
        Strobe["High-Intensity Candling LED (GPIO 19)"]
        OptSensor["Optical Beam-Break Sensor (GPIO 14)"]
        ESP32["ESP32 IoT Microcontroller"]
        Servo["Pneumatic Diverter Flipper (GPIO 18)"]
        Cam["High-Speed Industrial Camera"]

        Egg -->|Breaks Beam| OptSensor
        OptSensor -->|Hardware Interrupt 600ms| ESP32
        ESP32 -->|Strobe Pulse| Strobe
        Strobe -->|Transillumination| Egg
        Egg -->|Photons| Cam
        ESP32 -->|Delta-t Actuation Delay| Servo
    end

    subgraph Edge_Node["Edge Computing Station (Raspberry Pi 5 / PC)"]
        Cam -->|DirectShow / V4L2 Frames| FrameGrabber["Thread 1: Frame Grabber"]
        FrameGrabber -->|Frame Queue| InferEngine["Thread 2: YOLOv8 ONNX FP16 Engine"]
        InferEngine -->|Accept / Reject Action| SerialWorker["Thread 3: ESP32 PySerial Worker"]
        SerialWorker -->|UART Command 115200| ESP32
        InferEngine -->|Scan DTO| LocalStore["Thread 4: SQLite WAL Local Store"]
        LocalStore -->|Async Batch Queue| SyncWorker["Sync Worker: Background HTTP REST"]
        InferEngine -->|GUI Stream| CTkUI["Main Thread: CustomTkinter 60 FPS UI"]
    end

    subgraph Cloud_Server["Central Hatchery Server (FastAPI + PostgreSQL 16)"]
        SyncWorker -->|POST /api/v1/scans/batch| FastAPIServer["FastAPI Backend Engine"]
        FastAPIServer -->|SQLAlchemy 2.0 ORM| PostgresDB[("PostgreSQL 16 Database")]
        FastAPIServer -->|PDF/CSV Reports| ReportEngine["Report Generator Service"]
    end

    subgraph Admin_Client["Hatchery Management Portal (React 18 + Vite)"]
        FastAPIServer -->|JSON REST API| ReactDashboard["Web Dashboard (Port 3000)"]
        ReactDashboard -->|Incubation Tray Matrix| OperatorView["Operator & Manager Devices"]
    end

    classDef primary fill:#800000,stroke:#5C0000,stroke-width:2px,color:#fff;
    classDef edge fill:#1E293B,stroke:#334155,stroke-width:2px,color:#38BDF8;
    classDef success fill:#15803D,stroke:#166534,stroke-width:2px,color:#fff;
    class FastAPIServer,ReactDashboard primary;
    class InferEngine,SyncWorker edge;
    class PostgresDB,LocalStore success;
```

---

## ⚙️ 2. Edge Multi-Threading & Synchronization Flowchart

```mermaid
sequenceDiagram
    autonumber
    participant Sensor as Optical Sensor (GPIO 14)
    participant ESP as ESP32 Microcontroller
    participant Camera as Camera / Frame Grabber
    participant ONNX as YOLOv8 ONNX FP16
    participant DB as SQLite WAL
    participant Backend as FastAPI Server

    Sensor->>ESP: Optical Beam Break Trigger
    ESP->>Camera: Trigger Pulse & Frame Capture
    Camera->>ONNX: Feed BGR Frame (640x640)
    Note over ONNX: Inference Time = 24.6 ms
    ONNX->>ESP: UART Command ('A'=Accept, 'R'=Reject)
    Note over ESP: Wait Delta-t = D / v (2,000 ms)
    ESP->>ESP: Actuate Pneumatic Servo (250 ms Pulse)
    ONNX->>DB: INSERT INTO local_scans (WAL Mode)
    Note over DB: Immediate write (<1 ms)
    DB-->>Backend: Background HTTP Sync (Every 5s or 50 scans)
    Backend-->>DB: ACK 200 OK (Mark Synced)
```
