# Chapter 3: Technical Methodology

## 3.1 Research Framework & System Architecture

The study adopts the **Design Science Research Methodology (DSRM)** framework proposed by Peffers et al. (2007) integrated with an **Agile Development Cycle** (Beck et al., 2001) to iteratively design, implement, and evaluate **OvaLens**.

* Detailed Methodology Diagram: [`Methodology_Updated.drawio`](file:///d:/Ryle_Gabotero/side_projects/Capstone/docs/diagrams/architecture/Methodology_Updated.drawio) ([Interactive Viewer](file:///d:/Ryle_Gabotero/side_projects/Capstone/docs/diagrams/architecture/Methodology_Updated.drawio.html))
* Conceptual Framework (IPO): [`IPO_Academic_Final.drawio`](file:///d:/Ryle_Gabotero/side_projects/Capstone/docs/diagrams/architecture/IPO_Academic_Final.drawio) ([Interactive Viewer](file:///d:/Ryle_Gabotero/side_projects/Capstone/docs/diagrams/architecture/IPO_Academic_Final.drawio.html))
* Master System Flowchart: [`Systemflow_chart_final.drawio`](file:///d:/Ryle_Gabotero/side_projects/Capstone/docs/diagrams/flowcharts/Systemflow_chart_final.drawio) ([Interactive Viewer](file:///d:/Ryle_Gabotero/side_projects/Capstone/docs/diagrams/flowcharts/Systemflow_chart_final.drawio.html))
* Master Use Case Diagram: [`OvaLens_Use_Case_Diagram.drawio`](file:///d:/Ryle_Gabotero/side_projects/Capstone/docs/diagrams/use_cases/OvaLens_Use_Case_Diagram.drawio) ([Interactive Viewer](file:///d:/Ryle_Gabotero/side_projects/Capstone/docs/diagrams/use_cases/OvaLens_Use_Case_Diagram.drawio.html))

### The 7 Research Phases:
1. **Phase 1: Planning & Requirements** (*DSRM: Problem Identification & Objectives Definition*) — Define system specifications, examine manual candling bottlenecks, and establish hatchery requirements.
2. **Phase 2: Data Collection & Preparation** — Image acquisition across Day 10, 18, and 25 candling stages for pure lines (IP-Itim, IP-Khaki) and hybrid (IP-Kayumanggi); whole-egg bounding-box annotation; dataset preprocessing with 70/15/15 partitioning.
3. **Phase 3: YOLOv8 Model Development** (*DSRM: Design & Development*) — YOLOv8 configuration, hyperparameter tuning, transfer learning, and ONNX FP16 edge quantization.
4. **Phase 4: Hardware & Software Prototyping** (*DSRM: Design & Development*) — Construction of indexed pocket-conveyor, ESP32 firmware, camera geometry, desktop controller, and administrative dashboard.
5. **Phase 5: System Integration & Testing** (*DSRM: Demonstration*) — Synchronization of cradle indexing with inference results, optical interrupts, and servo sorting actuation.
6. **Phase 6: Evaluation & Refinement** (*DSRM: Evaluation*) — Rigorous evaluation of precision, recall, mAP, latency ($\le 200\text{ ms}$), sorting accuracy, and throughput, linked to an iterative refinement feedback loop.
7. **Phase 7: Deployment & Communication** (*DSRM: Communication*) — Final prototype presentation to Foundation University panel and stakeholder demonstration.

---

## 3.2 System Architectural Design

The physical and software architecture comprises four tightly coupled subsystems:
1. **Edge Candling & Conveyor Controller (`edge/`)**:
   - **Edge Processor**: Raspberry Pi 5 / PC running an offline-resilient Python controller.
   - **Computer Vision Pipeline**: Fixed-geometry industrial camera and ONNX Runtime execution provider running quantized YOLOv8 models ($\le 200\text{ ms}$ inference latency).
   - **Operator Desktop Application**: CustomTkinter interface running on the edge node for live inspection monitoring, real-time cradle tracking, manual review alerts, and local SQLite (WAL mode) logging.
2. **Electromechanical Transport & Actuation Mechanism (`firmware/`)**:
   - **Indexed Pocket-Conveyor**: Stepper motor-driven conveyor with individual cradle pockets ensuring steady transport and positional synchronization.
   - **Candling Chamber**: Enclosed optical chamber with high-intensity cold-LED transillumination strobe.
   - **IoT Controller (ESP32 Dev Module)**: Handles positional reference sensing (infrared optical beam-break interrupts) and actuates the binary sorting mechanism for Fertile and Infertile/Penoy destinations.
3. **Central Hatchery Management Engine (`backend/`)**:
   - **REST API**: FastAPI service utilizing Pydantic v2 schemas and SQLAlchemy 2.0 ORM.
   - **Central Database**: PostgreSQL 16 database storing multi-batch historical records, incubation tray mappings, and batch summary metrics.
   - **Idempotent Ingestion**: Handles network sync payloads from edge nodes with `ON CONFLICT DO NOTHING` guarantees.
4. **Administrative Web Portal (`dashboard/`)**:
   - **Web Dashboard**: React 18 + Vite + TypeScript + TailwindCSS administrative frontend.
   - **Hatchery Analytics**: Real-time batch statistics, egg-stage distributions (Day 10, 18, 25), incubation tray visualizations, and downloadable CSV/PDF audit reports.

---

## 3.3 Dataset Collection & Annotation Strategy

### Target Population & Research Setting
* **Hatchery Partner**: Academic-institution-owned research duck hatchery in Negros Oriental.
* **Genetic Groups**:
  1. **IP-Itim** (*Itik Pinas Itim* - pure line)
  2. **IP-Khaki** (*Itik Pinas Khaki* - pure line)
  3. **IP-Kayumanggi** (*Commercial hybrid* of male IP-Khaki and female IP-Itim)
* **Candling Checkpoint**:
  - **Day 10 only**: Fertility assessment and identification of non-fertile eggs for *penoy* salvage.

### Target Dataset Volume & Split
* **Target Sample Size**: $\ge 3,000$ locally collected, annotated duck egg candling frames.
* **Operational Classes**:
  * `FERTILE`: Continuing viable embryonic development with prominent spider vascularization or advanced embryo shadow.
  * `INFERTILE`: Any Day 10 egg that is not classified as fertile and is rejected for Penoy salvage.
* **Data Partitioning**: 70% Training, 15% Validation, and 15% Testing (stratified across genetic groups).
* **Annotation Format**: Whole-egg bounding box YOLO format (`[class_id, x_center, y_center, width, height]`), verifying presence and centering before classification.

---

## 3.3 Deep Learning Vision Pipeline

### Model Architecture
* **Backbone**: Ultralytics YOLOv8 (Nano / Small variant for edge efficiency).
* **Optimization & Quantization**: PyTorch weights trained with transfer learning, exported to ONNX FP16 half-precision graph for low-power edge inference.
* **Loss Functions**:
  * Complete Intersection over Union (CIoU) bounding box loss.
  * Binary Cross-Entropy (BCE) classification loss.
  * Distribution Focal Loss (DFL) for precise bounding-box boundary regression.

### Egg Verification & Decision Logic
1. Frame captured inside enclosed candling chamber during the indexed pause.
2. YOLOv8 detects whole egg bounding box. If no egg is detected or bounding box exceeds positional tolerance, system flags an **Invalid Capture**.
3. If confidence score $\ge \tau_{\text{threshold}}$ (e.g., 0.75), classification is accepted and associated with the current cradle index.
4. If confidence score $<\tau_{\text{threshold}}$, cradle status is flagged for **Manual Review**.

---

## 3.4 Electromechanical Kinematics & Cradle Tracking

```
[Loading Station] ---> [Candling Chamber (Stop & Image)] ---> [Infertile Diverter] ---> [Fertile Tray]
```

### Indexed Stepper Kinematics
* Primary stepper motor indexes each cradle step-by-step through the inspection lane.
* Sensor-to-actuator kinematic delay formula:
$$\Delta t = \frac{D_{\text{diverter}} - D_{\text{sensor}}}{v_{\text{conveyor}}}$$
Where:
* $D_{\text{diverter}} - D_{\text{sensor}} = 25.0\text{ cm}$
* $v_{\text{conveyor}} = 12.5\text{ cm/s}$
* Nominal actuation delay: $\Delta t = 2,000\text{ ms}$ (software tracked by cradle queue index).

### Sorting Routing
* **Fertile**: Retained on conveyor or gently slid onto cushioned incubation tray.
* **Infertile / Penoy**: Diverted to collection tray for Day 10 commercial food salvage (₱14.00/egg).
* **Manual Review**: Diverted to separate inspection lane or alerted on operator GUI when detection is uncertain.

---

## 3.5 System Evaluation Metrics

### Model Performance Metrics
* **Precision, Recall, F1-Score** per operational class (`FERTILE`, `INFERTILE`).
* **Mean Average Precision**: $\text{mAP}_{50}$ and $\text{mAP}_{50-95}$.
* **Inference Latency**: Single-frame inference latency ($\le 200\text{ ms}$ SLA target on Raspberry Pi).
* **Subgroup Reporting**: Performance broken down across:
  * Genetic lines: IP-Itim vs IP-Khaki vs IP-Kayumanggi.
  * Day 10 batches and genetic groups.

### System & Hardware Evaluation Metrics
* **Sorting Accuracy**: Percentage of physical eggs routed to the correct destination tray matching ground truth.
* **Cradle-Tracking Accuracy**: Preservation of egg identity and classification from imaging station to sorting gates.
* **Successful-Cycle Rate**: Proportion of uninterrupted cycles without mechanical jams or sensor misses.
* **Throughput**: Eggs processed per minute under continuous indexed operation.
* **Manual-Review Frequency**: Rate of low-confidence or anomalous captures requiring human operator intervention.
