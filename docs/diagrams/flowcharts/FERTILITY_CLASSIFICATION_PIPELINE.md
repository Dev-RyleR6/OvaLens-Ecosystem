# Fertility Classification & Conveyor Actuation Pipeline

> **Subsystem**: `edge/` + `firmware/` + `backend/` + `dashboard/`  
> **Source Draw.io File**: [`Flowchart-5 - Fertility Classification Pipeline.drawio.svg`](file:///d:/Ryle_Gabotero/side_projects/Capstone/docs/diagrams/flowcharts/Flowchart-5%20-%20Fertility%20Classification%20Pipeline.drawio.svg)  
> **Institution**: Foundation University  

---

## 🔄 Mermaid Flowchart Diagram

```mermaid
flowchart TD
    START([Start / Select Active Batch]) --> S1[Egg Placed on Conveyor Belt\nv = 12.5 cm/s]
    S1 --> S2[Optical IR Sensor Detects Egg\nGPIO 14 with 600 ms lockout debounce]
    S2 --> S3[Bottom High-Lumen Candling Illumination\n& Camera Frame Capture]
    S3 --> S4[YOLOv8 ONNX FP16 Inference <= 35 ms\n+ HSV & Aspect Ratio Heuristic Validation]
    
    subgraph "Offline-First Logging & Central Sync"
        S4 --> L1[(Local SQLite WAL Store\nis_synced = 0)]
        L1 --> L2[Background Sync Worker Thread\nBatch HTTP POST /api/v1/scans/sync]
        L2 --> L3[(PostgreSQL 16 Central DB\nON CONFLICT DO NOTHING)]
        L3 --> L4[React 18 Dashboard Live Feed & Analytics]
    end

    S4 --> D1{Classification Result: FERTILE?}
    
    %% FERTILE PATH
    D1 -- Yes --> F1[Both Servo Diverters Remain Retracted\nEgg passes straight through]
    F1 --> F2[Egg Continues Downstream along Conveyor]
    F2 --> F3[Low-Shock Delivery to\nFertile Incubation Tray]
    
    %% NOT FERTILE PATH
    D1 -- No --> D2{Classification Result: INFERTILE?}
    
    %% INFERTILE PATH
    D2 -- Yes --> I1[ESP32 Actuates Left Servo Diverter\nExtend left arm at Δt = 2,000 ms]
    I1 --> I2[Egg Continues Downstream along Conveyor]
    I2 --> I3[Left-Side Deflection down Chute to\nDay-10 Penoy Salvage Tray PHP 14/egg]
    
    %% ABNORMAL PATH
    D2 -- No (ABNORMAL) --> A1[ESP32 Actuates Right Servo Diverter\nExtend right arm at Δt = 2,000 ms]
    A1 --> A2[Egg Continues Downstream along Conveyor]
    A2 --> A3[Right-Side Deflection down Chute to\nAbnormal / Early Discard Bin]
    
    %% MERGE
    F3 --> LOOP{More eggs in queue?}
    I3 --> LOOP
    A3 --> LOOP
    
    LOOP -- Yes --> S1
    LOOP -- No --> END([Batch Candling Session Complete])

    classDef fertile fill:#E8F5E9,stroke:#2E7D32,stroke-width:2px;
    classDef infertile fill:#FFF8E1,stroke:#F9A825,stroke-width:2px;
    classDef abnormal fill:#FFEBEE,stroke:#C62828,stroke-width:2px;
    classDef decision fill:#E3F2FD,stroke:#1565C0,stroke-width:2px;
    classDef sync fill:#F3E5F5,stroke:#6A1B9A,stroke-width:2px;

    class F1,F2,F3 fertile;
    class I1,I2,I3 infertile;
    class A1,A2,A3 abnormal;
    class D1,D2 decision;
    class L1,L2,L3,L4 sync;
```

---

## 📋 Summary of Pipeline Stages

1. **Egg Intake & Hardware Trigger**:
   - Duck eggs travel along the conveyor belt at continuous velocity ($v = 12.5\text{ cm/s}$).
   - An optical IR sensor triggers a hardware interrupt on the **ESP32** (GPIO 14 with a 600 ms lockout debounce).

2. **Computer Vision & Heuristic Inference**:
   - High-speed camera captures the bottom-candled egg frame.
   - **ONNX Runtime FP16** executes YOLOv8 inference in $\le 35\text{ms}$.
   - Geometric aspect-ratio ($0.65 \le \text{AR} \le 1.45$) and HSV candling luminance heuristics validate the egg boundary.

3. **Offline-First Resilience**:
   - The scan event is immediately committed to **Local SQLite in WAL mode** (`is_synced = 0`).
   - The [`BackgroundSyncWorker`](file:///d:/Ryle_Gabotero/side_projects/Capstone/edge/src/sync/sync_worker.py) thread polls and pushes uncommitted scans every 3 seconds to the central **FastAPI + PostgreSQL 16** backend (`ON CONFLICT (scan_id) DO NOTHING`), updating local state to `is_synced = 1`.

4. **3-Way Sorting Actuation ($\Delta t = D/v = 2,000\text{ ms}$)**:
   - **`FERTILE`**: Both servo diverters remain retracted $\rightarrow$ straight pass into the **Fertile Incubation Tray**.
   - **`INFERTILE`**: ESP32 actuates the left servo diverter $\rightarrow$ deflected into the **Day-10 Penoy Salvage Chute (₱14)**.
   - **`ABNORMAL`**: ESP32 actuates the right servo diverter $\rightarrow$ deflected into the **Early Discard Bin**.
