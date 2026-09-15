#!/usr/bin/env python
"""
generate_checklist_excel.py — Creates a professional, styled Excel feature checklist
for the OvaLens Capstone Ecosystem based on authentic documentation and diagrams.
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

def build_excel_checklist():
    wb = openpyxl.Workbook()
    
    # Fonts & Colors (Foundation University Theme)
    MAROON_FILL = PatternFill(start_color="800000", end_color="800000", fill_type="solid")
    DARK_MAROON_FILL = PatternFill(start_color="5C0000", end_color="5C0000", fill_type="solid")
    GREEN_FILL = PatternFill(start_color="357A38", end_color="357A38", fill_type="solid")
    LIGHT_GRAY_FILL = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    ALT_ROW_FILL = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
    
    STATUS_DONE_FILL = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid") # soft green
    STATUS_IN_PROGRESS_FILL = PatternFill(start_color="FEF9C3", end_color="FEF9C3", fill_type="solid") # soft yellow
    STATUS_BACKLOG_FILL = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid") # soft slate
    
    STATUS_DONE_FONT = Font(name="Segoe UI", size=10, bold=True, color="166534")
    STATUS_IN_PROGRESS_FONT = Font(name="Segoe UI", size=10, bold=True, color="854D0E")
    STATUS_BACKLOG_FONT = Font(name="Segoe UI", size=10, bold=True, color="475569")
    
    HEADER_FONT = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    TITLE_FONT = Font(name="Segoe UI", size=16, bold=True, color="800000")
    SUBTITLE_FONT = Font(name="Segoe UI", size=10, italic=True, color="64748B")
    REGULAR_FONT = Font(name="Segoe UI", size=10, color="0F172A")
    BOLD_FONT = Font(name="Segoe UI", size=10, bold=True, color="0F172A")
    KPI_NUM_FONT = Font(name="Segoe UI", size=18, bold=True, color="800000")
    KPI_LABEL_FONT = Font(name="Segoe UI", size=9, bold=True, color="64748B")

    THIN_BORDER = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )

    # -------------------------------------------------------------------------
    # TAB 1: EXECUTIVE SUMMARY & DASHBOARD
    # -------------------------------------------------------------------------
    ws_dash = wb.active
    ws_dash.title = "Executive Overview"
    ws_dash.views.sheetView[0].showGridLines = True

    ws_dash.merge_cells("A1:H1")
    ws_dash["A1"] = "OVALENS: CAPSTONE FEATURE & IMPLEMENTATION CHECKLIST"
    ws_dash["A1"].font = TITLE_FONT
    ws_dash["A1"].alignment = Alignment(vertical="center")

    ws_dash.merge_cells("A2:H2")
    ws_dash["A2"] = "Automated Candling & Sorter System • Foundation University (CCS) • Team DevIn • Methodology: DSRM + Agile"
    ws_dash["A2"].font = SUBTITLE_FONT
    ws_dash["A2"].alignment = Alignment(vertical="center")

    # KPI Summary Cards
    kpis = [
        ("Total Features", "=COUNTA('Master Checklist'!A4:A50)", "B4:C4", "B5:C5"),
        ("Completed [Done]", '=COUNTIF(\'Master Checklist\'!H4:H50, "Done")', "D4:E4", "D5:E5"),
        ("In Progress", '=COUNTIF(\'Master Checklist\'!H4:H50, "In Progress")', "F4:G4", "F5:G5"),
        ("Pending Backlog", '=COUNTIF(\'Master Checklist\'!H4:H50, "Backlog")', "H4:I4", "H5:I5")
    ]
    for label, formula, cell_top, cell_bot in kpis:
        ws_dash.merge_cells(cell_top)
        ws_dash.merge_cells(cell_bot)
        top_left = cell_top.split(":")[0]
        bot_left = cell_bot.split(":")[0]
        ws_dash[top_left] = label
        ws_dash[top_left].font = KPI_LABEL_FONT
        ws_dash[top_left].alignment = Alignment(horizontal="center", vertical="center")
        ws_dash[top_left].fill = LIGHT_GRAY_FILL
        ws_dash[bot_left] = formula
        ws_dash[bot_left].font = KPI_NUM_FONT
        ws_dash[bot_left].alignment = Alignment(horizontal="center", vertical="center")
        ws_dash[bot_left].fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

    # DSRM Phase Progress Table
    ws_dash["A8"] = "DSRM Phase"
    ws_dash["B8"] = "Phase Description"
    ws_dash["C8"] = "Total Tasks"
    ws_dash["D8"] = "Done"
    ws_dash["E8"] = "Status"
    for col in ["A", "B", "C", "D", "E"]:
        ws_dash[f"{col}8"].font = HEADER_FONT
        ws_dash[f"{col}8"].fill = MAROON_FILL
        ws_dash[f"{col}8"].alignment = Alignment(horizontal="center", vertical="center")

    phases = [
        ("Phase 1", "Planning & Requirements (Problem ID, Scope, Authentic Docs)", '=COUNTIF(\'Master Checklist\'!B4:B50, "Phase 1*")', '=COUNTIFS(\'Master Checklist\'!B4:B50, "Phase 1*", \'Master Checklist\'!H4:H50, "Done")', "Complete (100%)"),
        ("Phase 2", "Data Collection & Preparation (70/15/15 Split, 3 Breeds, 3 Stages)", '=COUNTIF(\'Master Checklist\'!B4:B50, "Phase 2*")', '=COUNTIFS(\'Master Checklist\'!B4:B50, "Phase 2*", \'Master Checklist\'!H4:H50, "Done")', "Ready for Pipeline"),
        ("Phase 3", "YOLOv8 Vision Model & ONNX FP16 Slim Optimization (<=200ms)", '=COUNTIF(\'Master Checklist\'!B4:B50, "Phase 3*")', '=COUNTIFS(\'Master Checklist\'!B4:B50, "Phase 3*", \'Master Checklist\'!H4:H50, "Done")', "In Progress"),
        ("Phase 4A", "Firmware & Electromechanical Sorter (ESP32, Stepper, Servos)", '=COUNTIF(\'Master Checklist\'!B4:B50, "Phase 4A*")', '=COUNTIFS(\'Master Checklist\'!B4:B50, "Phase 4A*", \'Master Checklist\'!H4:H50, "Done")', "In Progress"),
        ("Phase 4B", "Edge CV Controller & Desktop UI (Cradle Tracking, WAL SQLite)", '=COUNTIF(\'Master Checklist\'!B4:B50, "Phase 4B*")', '=COUNTIFS(\'Master Checklist\'!B4:B50, "Phase 4B*", \'Master Checklist\'!H4:H50, "Done")', "In Progress"),
        ("Phase 4C", "Central Backend & Database (FastAPI, PostgreSQL 16, Penoy Calc)", '=COUNTIF(\'Master Checklist\'!B4:B50, "Phase 4C*")', '=COUNTIFS(\'Master Checklist\'!B4:B50, "Phase 4C*", \'Master Checklist\'!H4:H50, "Done")', "In Progress"),
        ("Phase 4D", "Web Admin Dashboard (React 18, Vite, Tray Matrix, MLOps)", '=COUNTIF(\'Master Checklist\'!B4:B50, "Phase 4D*")', '=COUNTIFS(\'Master Checklist\'!B4:B50, "Phase 4D*", \'Master Checklist\'!H4:H50, "Done")', "In Progress"),
        ("Phase 5", "System Integration & Sync Testing (Demonstration)", '=COUNTIF(\'Master Checklist\'!B4:B50, "Phase 5*")', '=COUNTIFS(\'Master Checklist\'!B4:B50, "Phase 5*", \'Master Checklist\'!H4:H50, "Done")', "Scheduled"),
        ("Phase 6", "Empirical Evaluation (Accuracy, Throughput, Confusion Matrix)", '=COUNTIF(\'Master Checklist\'!B4:B50, "Phase 6*")', '=COUNTIFS(\'Master Checklist\'!B4:B50, "Phase 6*", \'Master Checklist\'!H4:H50, "Done")', "Scheduled"),
        ("Phase 7", "Defense Communication & Docker Containerization", '=COUNTIF(\'Master Checklist\'!B4:B50, "Phase 7*")', '=COUNTIFS(\'Master Checklist\'!B4:B50, "Phase 7*", \'Master Checklist\'!H4:H50, "Done")', "Scheduled")
    ]

    for idx, (p_id, p_desc, p_tot, p_done, p_stat) in enumerate(phases, start=9):
        ws_dash[f"A{idx}"] = p_id
        ws_dash[f"B{idx}"] = p_desc
        ws_dash[f"C{idx}"] = p_tot
        ws_dash[f"D{idx}"] = p_done
        ws_dash[f"E{idx}"] = p_stat
        ws_dash[f"A{idx}"].font = BOLD_FONT
        ws_dash[f"B{idx}"].font = REGULAR_FONT
        ws_dash[f"C{idx}"].font = REGULAR_FONT
        ws_dash[f"D{idx}"].font = REGULAR_FONT
        ws_dash[f"E{idx}"].font = BOLD_FONT
        ws_dash[f"C{idx}"].alignment = Alignment(horizontal="center")
        ws_dash[f"D{idx}"].alignment = Alignment(horizontal="center")
        ws_dash[f"E{idx}"].alignment = Alignment(horizontal="center")
        for col in ["A", "B", "C", "D", "E"]:
            ws_dash[f"{col}{idx}"].border = THIN_BORDER

    # Roles & Partnership Summary Box
    ws_dash["A21"] = "Agent Partnership Workflow:"
    ws_dash["A21"].font = Font(name="Segoe UI", size=11, bold=True, color="800000")
    ws_dash["A22"] = "• Antigravity (Orchestrator): Defines architecture, task contracts, review gates, automated test execution, and Git commits."
    ws_dash["A23"] = "• Codex (Implementor): Implements features, writes unit tests, and satisfies technical contracts."
    ws_dash["A24"] = "• Automated Gatekeeper: python scripts/verify_and_commit.py enforces tests (backend + edge + dashboard) & updates CHANGELOG.md."
    for r in range(22, 25):
        ws_dash[f"A{r}"].font = REGULAR_FONT

    # -------------------------------------------------------------------------
    # TAB 2: MASTER FEATURE CHECKLIST
    # -------------------------------------------------------------------------
    ws_master = wb.create_sheet(title="Master Checklist")
    ws_master.views.sheetView[0].showGridLines = True

    headers = [
        "Task ID", "DSRM Phase", "Subsystem", "Feature / Component",
        "Technical Specification & Acceptance Criteria", "Diagram Reference",
        "Assigned Role", "Status", "Priority", "Automated Test / Verification"
    ]
    
    ws_master.row_dimensions[3].height = 28
    for c_idx, h in enumerate(headers, start=1):
        cell = ws_master.cell(row=3, column=c_idx, value=h)
        cell.font = HEADER_FONT
        cell.fill = MAROON_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    checklist_items = [
        # Phase 1
        ("TASK-101", "Phase 1: Planning", "Docs / Specs", "Authentic Capstone Manuscript Integration", "Parse DevIn (2026).md into Chapters 1, 2, 3, 6 with 15 APA 7 citations and official Title/Approval Sheet", "Manuscript 00-06", "Antigravity", "Done", "P0 - Critical", "docs/manuscript/*.md review"),
        ("TASK-102", "Phase 1: Planning", "Architecture", "Import & Catalog Academic Diagrams", "Embed and convert IPO Matrix, DSRM Methodology, System Flowchart, and Use Case diagrams (.drawio & .html)", "All 4 Diagrams", "Antigravity", "Done", "P0 - Critical", "docs/diagrams catalog audit"),
        ("TASK-103", "Phase 1: Planning", "Workflow", "Two-Tier Agent Workflow & Automated Quality Gate", "Establish Antigravity + Codex partnership, PROJECT_PLAN.md, CHANGELOG.md, and verify_and_commit.py", "PROJECT_PLAN.md", "Antigravity", "Done", "P0 - Critical", "python scripts/verify_and_commit.py"),

        # Phase 2
        ("TASK-201", "Phase 2: Dataset", "Data Pipeline", "Dataset Ingestion & Stratification Script", "Stratify raw candling dataset 70% Train, 15% Val, 15% Test across IP-Itim, IP-Khaki, IP-Kayumanggi and Day 10, 18, 25", "IPO Matrix / Meth", "Codex", "Backlog", "P1 - High", "test_dataset_stratification.py"),
        ("TASK-202", "Phase 2: Dataset", "Data Pipeline", "Whole-Egg YOLO Annotation Validator", "Verify YOLO darknet format [class_id, x_center, y_center, w, h] ensuring bounding box encloses full egg", "IPO Matrix", "Codex", "Backlog", "P1 - High", "test_annotation_bounds.py"),
        ("TASK-203", "Phase 2: Dataset", "Data Pipeline", "Augmentation Pipeline (HSV + Geometric)", "Apply +/-15 deg rotation, vertical/horizontal flips, and HSV luminance jitter to simulate candling transillumination", "Chapter 3.2", "Codex", "Backlog", "P2 - Medium", "test_augmentation_visuals.py"),
        ("TASK-204", "Phase 2: Dataset", "Data Pipeline", "Dataset Distribution Summary Exporter", "Generate automated Markdown and LaTeX tables of egg counts per breed/day for Chapter 3 & 4 manuscript", "Chapter 3.2", "Codex", "Backlog", "P2 - Medium", "python scripts/export_dataset_table.py"),

        # Phase 3
        ("TASK-301", "Phase 3: AI Vision", "Edge CV", "YOLOv8 Nano/Small Training Script", "Implement Ultralytics training pipeline with CIoU Bounding Box Loss, BCE Classification Loss, and DFL", "Methodology 3.3", "Codex", "Backlog", "P1 - High", "train_yolov8.py smoke test"),
        ("TASK-302", "Phase 3: AI Vision", "Edge CV", "ONNX FP16 Slim Export & Half-Precision Graph", "Convert PyTorch weights to ONNX FP16 slim graph with fixed input dimensions (640x640) for edge speedup", "AGENTS.md Tenet 3", "Codex", "In Progress", "test_inference_engine_and_latency_benchmark"),
        ("TASK-303", "Phase 3: AI Vision", "Edge CV", "Edge Latency Profiler (<=200ms SLA)", "Measure inference latency across 100 iterations on target hardware; enforce <= 200 ms SLA constraint", "System Flowchart", "Codex", "In Progress", "pytest test_edge_pipeline.py"),
        ("TASK-304", "Phase 3: AI Vision", "Edge CV", "Disaggregated Subgroup Evaluator", "Calculate Precision, Recall, F1, mAP50-95 broken down by genetic group (Itim/Khaki/Kayumanggi) and stage (Day 10/18/25)", "IPO Matrix", "Codex", "Backlog", "test_subgroup_metrics.py"),

        # Phase 4A - Firmware
        ("TASK-401", "Phase 4A: Firmware", "ESP32 IoT", "Optical Sensor Hardware Interrupt & Debounce", "Configure GPIO 14 with 600ms hardware optical beam-break debounce lockout window", "System Flowchart", "Codex", "Done", "P0 - Critical", "esp32_actuator.ino review"),
        ("TASK-402", "Phase 4A: Firmware", "ESP32 IoT", "Indexed Stepper Motor Pocket Transport Driver", "Control pocket-conveyor indexed movement with cradle-by-cradle pause at candling illumination station", "System Flowchart", "Codex", "Backlog", "P0 - Critical", "Firmware bench test"),
        ("TASK-403", "Phase 4A: Firmware", "ESP32 IoT", "Multi-Servo Sorter Gate Actuator", "Divert eggs to Fertile (cushioned tray), Infertile (Penoy salvage @ P14), and Abnormal (discard bin)", "System Flowchart", "Codex", "Backlog", "P0 - Critical", "test_esp32_serial_mock_and_motor_commands"),
        ("TASK-404", "Phase 4A: Firmware", "ESP32 IoT", "Non-Blocking UART Serial Protocol (115200)", "Implement non-blocking UART command parser with checksum and ACK/NACK responses", "AGENTS.md Firmware", "Codex", "In Progress", "test_esp32_serial_mock_and_motor_commands"),

        # Phase 4B - Edge CV & Controller
        ("TASK-405", "Phase 4B: Edge App", "Edge CV", "Multi-Threaded Concurrency Core", "Implement 4-thread non-blocking architecture: Frame Grabber, ONNX Inference, Serial Worker, SQLite Sync", "AGENTS.md Edge", "Codex", "Done", "P0 - Critical", "test_edge_pipeline.py (8/8 passed)"),
        ("TASK-406", "Phase 4B: Edge App", "Edge CV", "Local SQLite Store with WAL Mode", "Atomic local scan persistence before network sync; PRAGMA journal_mode = WAL;", "AGENTS.md Edge", "Codex", "Done", "P0 - Critical", "test_local_sqlite_wal_and_queue_diagnostics"),
        ("TASK-407", "Phase 4B: Edge App", "Edge CV", "Cradle Tracking & Queue Association", "Maintain FIFO cradle queue mapping physical cradle ID to image capture, prediction, and diverter timing", "System Flowchart", "Codex", "In Progress", "test_cradle_tracking_queue.py"),
        ("TASK-408", "Phase 4B: Edge App", "Edge CV", "Manual Review Fallback State Machine", "Flag low-confidence (<0.75) or invalid captures; prompt operator override or route to inspection lane", "System Flowchart", "Codex", "In Progress", "test_manual_review_fallback.py"),
        ("TASK-409", "Phase 4B: Edge App", "Edge CV", "CustomTkinter 60 FPS Operator Desktop UI", "Real-time inspection stream, live cradle status, session stats, manual review modal, and emergency stop", "Use Case: Worker", "Codex", "In Progress", "Desktop UI smoke run"),

        # Phase 4C - Backend & Database
        ("TASK-410", "Phase 4C: Backend", "REST API", "FastAPI Core & Declarative Database Models", "SQLAlchemy 2.0 declarative models for User, Device, Batch, Session, Scan with PostgreSQL 16 schema", "AGENTS.md Backend", "Codex", "Done", "P0 - Critical", "test_api.py (13/13 passed)"),
        ("TASK-411", "Phase 4C: Backend", "REST API", "Idempotent Batch Scan Ingestion Endpoint", "POST /api/v1/scans/batch with ON CONFLICT (scan_id) DO NOTHING to absorb duplicate sync packets safely", "AGENTS.md Backend", "Codex", "Done", "P0 - Critical", "test_api.py::test_analytics_overview"),
        ("TASK-412", "Phase 4C: Backend", "REST API", "Day 10 Penoy Economic Salvage Yield Calculator", "Calculate real-time salvaged revenue: Penoy Count * P14.00, energy saved from culled eggs, ROI metrics", "AGENTS.md Tenet 3", "Codex", "Done", "P1 - High", "test_analytics_economic_yield"),
        ("TASK-413", "Phase 4C: Backend", "REST API", "Automated PDF & CSV Report Generator", "Generate official batch compliance reports with ReportLab and pandas for hatchery management", "Use Case: Supervisor", "Codex", "Done", "P1 - High", "test_pdf_and_csv_reports"),
        ("TASK-414", "Phase 4C: Backend", "REST API", "RBAC Auth & Role Separation", "JWT authentication with Candling Worker, Hatchery Supervisor, and System Administrator privileges", "Use Case Diagram", "Codex", "Done", "P0 - Critical", "test_rbac_and_admin_security_protections"),

        # Phase 4D - Dashboard
        ("TASK-415", "Phase 4D: Dashboard", "Web Portal", "React 18 + Vite + TS Foundation University Setup", "TailwindCSS styling with Foundation University maroon (#800000) and agri-green (#357a38) theme tokens", "AGENTS.md FU Brand", "Codex", "Done", "P1 - High", "npm.cmd run build (Clean Build)"),
        ("TASK-416", "Phase 4D: Dashboard", "Web Portal", "Interactive 42-Slot Incubation Tray Matrix", "Visual representation of tray slots (A1 to F7) with color-coded biological states and tooltip inspection", "Use Case: Supervisor", "Codex", "Done", "P1 - High", "Dashboard UI verification"),
        ("TASK-417", "Phase 4D: Dashboard", "Web Portal", "Live Hatchery Overview & Real-Time Stats", "Aggregated fertility percentage, Day 10 salvage income, mortality rates, and batch comparison cards", "Use Case: Supervisor", "Codex", "In Progress", "Dashboard UI verification"),
        ("TASK-418", "Phase 4D: Dashboard", "Web Portal", "Genetic Line & Candling Stage Filter Suite", "Filter analytics by IP-Itim, IP-Khaki, IP-Kayumanggi and Day 10, Day 18, Day 25 candling milestones", "Methodology 3.1", "Codex", "In Progress", "Dashboard UI verification"),
        ("TASK-419", "Phase 4D: Dashboard", "Web Portal", "Edge Sorter Heartbeat & Device Manager", "Real-time monitoring of connected sorter rigs, serial connection status, and camera FPS diagnostics", "Use Case: Admin", "Codex", "Backlog", "P2 - Medium", "Dashboard UI verification"),
        ("TASK-420", "Phase 4D: Dashboard", "Web Portal", "Audit Logs & User Administration Console", "System Administrator view for user provisioning, permission assignment, and security audit log review", "Use Case: Admin", "Codex", "In Progress", "test_user_profile_and_password_change_flow"),

        # Phase 5 - Integration
        ("TASK-501", "Phase 5: Integration", "System Test", "End-to-End Sorting Pilot Simulation", "Simulate 50-egg continuous sorting cycle: load -> index -> capture -> ONNX predict -> divert -> sync", "System Flowchart", "Antigravity / Codex", "Backlog", "P0 - Critical", "test_end_to_end_pilot.py"),
        ("TASK-502", "Phase 5: Integration", "System Test", "Offline Network Disconnection Replay Test", "Cut network during sorting; confirm 100% sorting uninterrupted at edge; restore network & verify bulk replay", "AGENTS.md Offline", "Antigravity / Codex", "Backlog", "P0 - Critical", "test_offline_network_replay.py"),
        ("TASK-503", "Phase 5: Integration", "System Test", "Cradle Position Resync Fault Recovery Test", "Simulate mechanical index slip; verify conveyor pauses, triggers operator resync, and preserves egg identities", "System Flowchart", "Antigravity / Codex", "Backlog", "P1 - High", "test_cradle_resync_fault.py"),

        # Phase 6 - Evaluation
        ("TASK-601", "Phase 6: Evaluation", "Research Eval", "Physical Sorting Accuracy Benchmark", "Run >= 100 physical egg candling trials to measure percentage of eggs correctly routed to destination trays", "Chapter 1 Objectives", "Antigravity", "Backlog", "P0 - Critical", "Physical trial tally sheet"),
        ("TASK-602", "Phase 6: Evaluation", "Research Eval", "System Throughput & Cycle Time Benchmarking", "Measure end-to-end processing time per egg and overall throughput (eggs/minute) under continuous indexing", "Chapter 1 Objectives", "Antigravity", "Backlog", "P1 - High", "Kinematics benchmark report"),
        ("TASK-603", "Phase 6: Evaluation", "Research Eval", "Confusion Matrix & Manuscript Chapter 4 Data", "Generate 3-class confusion matrix, precision/recall curves, and ROC curves for Chapter 4 Results & Discussion", "Chapter 4 Manuscript", "Antigravity", "Backlog", "P0 - Critical", "generate_confusion_matrix.py"),

        # Phase 7 - Defense
        ("TASK-701", "Phase 7: Defense", "Defense Prep", "Manuscript Chapter 4 (Results & Discussion)", "Draft Chapter 4 using empirical metrics, confusion matrices, latency charts, and subgroup comparisons", "Chapter 4", "Antigravity", "Backlog", "P0 - Critical", "Manuscript peer review"),
        ("TASK-702", "Phase 7: Defense", "Defense Prep", "Manuscript Chapter 5 (Conclusions & Recommendations)", "Summarize findings, answer research questions 1-4, and formulate agricultural/engineering recommendations", "Chapter 5", "Antigravity", "Backlog", "P0 - Critical", "Adviser review"),
        ("TASK-703", "Phase 7: Defense", "Deployment", "1-Click Docker Production Packaging", "Verify docker-compose up for PostgreSQL 16, FastAPI backend, and React dashboard for live defense demo", "docker-compose.yml", "Antigravity / Codex", "In Progress", "docker-compose config test")
    ]

    for row_idx, item in enumerate(checklist_items, start=4):
        ws_master.row_dimensions[row_idx].height = 22
        for col_idx, val in enumerate(item, start=1):
            cell = ws_master.cell(row=row_idx, column=col_idx, value=val)
            cell.font = REGULAR_FONT
            cell.border = THIN_BORDER
            cell.alignment = Alignment(vertical="center")

            # Center-align specific columns
            if col_idx in [1, 2, 7, 8, 9]:
                cell.alignment = Alignment(horizontal="center", vertical="center")

            # Status styling
            if col_idx == 8:
                if val == "Done":
                    cell.fill = STATUS_DONE_FILL
                    cell.font = STATUS_DONE_FONT
                elif val == "In Progress":
                    cell.fill = STATUS_IN_PROGRESS_FILL
                    cell.font = STATUS_IN_PROGRESS_FONT
                else:
                    cell.fill = STATUS_BACKLOG_FILL
                    cell.font = STATUS_BACKLOG_FONT
            elif row_idx % 2 == 1:
                cell.fill = ALT_ROW_FILL

    # Auto-adjust column widths
    for ws in [ws_dash, ws_master]:
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 48)

    ws_master.column_dimensions["A"].width = 14
    ws_master.column_dimensions["B"].width = 20
    ws_master.column_dimensions["C"].width = 16
    ws_master.column_dimensions["D"].width = 36
    ws_master.column_dimensions["E"].width = 48
    ws_master.column_dimensions["F"].width = 22
    ws_master.column_dimensions["G"].width = 16
    ws_master.column_dimensions["H"].width = 14
    ws_master.column_dimensions["I"].width = 16
    ws_master.column_dimensions["J"].width = 38

    # -------------------------------------------------------------------------
    # TAB 3: SYSTEM FLOWCHART TRACEABILITY MATRIX
    # -------------------------------------------------------------------------
    ws_flow = wb.create_sheet(title="Flowchart Traceability")
    ws_flow.views.sheetView[0].showGridLines = True
    
    flow_headers = [
        "Step #", "Flowchart Node (Systemflow_chart_final)", "Subsystem",
        "Implementation Component", "Decision Logic / Action", "Status", "Responsible"
    ]
    for c_idx, h in enumerate(flow_headers, start=1):
        cell = ws_flow.cell(row=1, column=c_idx, value=h)
        cell.font = HEADER_FONT
        cell.fill = DARK_MAROON_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center")

    flow_steps = [
        ("1", "Open OvaLens Desktop Controller", "Edge UI", "src/ui/operator_app.py", "Desktop GUI initializes 60 FPS viewport and status monitors", "In Progress", "Codex"),
        ("2", "Set Batch, Stage, and Genetic Line", "Edge / Backend", "src/ui/modals/session_dialog.py", "Select Batch ID, Day 10/18/25, IP-Itim/Khaki/Kayumanggi", "In Progress", "Codex"),
        ("3", "Initialize System & Ready Check", "Firmware / Serial", "src/iot/esp32_driver.py", "ESP32 handshake, optical sensor zeroing, servo homing", "In Progress", "Codex"),
        ("4", "Load Egg into Available Cradle", "Hardware / Rig", "Mechanical Conveyor", "Manual placement of duck egg into individual cradle pocket", "Backlog", "Hardware Team"),
        ("5", "Assign Cradle ID to Egg Record", "Edge Tracking", "src/core/cradle_tracker.py", "FIFO cradle tracker allocates unique cradle_id and timestamp", "In Progress", "Codex"),
        ("6", "Index Cradle to Candling Position", "Firmware / Stepper", "firmware/esp32_actuator.ino", "Stepper motor indexes cradle into enclosed dark chamber", "Backlog", "Codex"),
        ("7", "Illuminate LED & Capture Frame", "Edge CV / Camera", "src/core/frame_grabber.py", "10W cold-LED strobe fires; camera captures transillumination image", "Done", "Codex"),
        ("8", "Detect Egg & Predict Class (YOLOv8)", "Edge AI", "src/core/inference_engine.py", "Whole-egg bounding box detection + Fertile/Infertile/Abnormal prediction", "Done", "Codex"),
        ("9", "Valid Classification Check?", "Edge Heuristics", "src/core/heuristics.py", "Check confidence >= 0.75 and egg centering. If not -> Flag for Review", "In Progress", "Codex"),
        ("10", "Flag for Manual Review / Override", "Edge UI", "src/ui/modals/review_modal.py", "Worker prompted with image; can override or accept classification", "In Progress", "Codex"),
        ("11", "Associate Class & Conf with Cradle ID", "Edge Tracking", "src/core/cradle_tracker.py", "Cradle state updated with validated class decision", "In Progress", "Codex"),
        ("12", "Save Scan Record Locally (SQLite WAL)", "Edge Store", "src/db/sqlite_manager.py", "Atomic local write to local_scans table before network transmission", "Done", "Codex"),
        ("13", "Background Sync to Backend & Web", "Edge Sync", "src/sync/http_sync_worker.py", "Async HTTP POST /api/v1/scans/batch with ON CONFLICT DO NOTHING", "Done", "Codex"),
        ("14", "Index Conveyor & Track Position", "Firmware / Stepper", "firmware/esp32_actuator.ino", "Cradle moves downstream toward segregation gates", "Backlog", "Codex"),
        ("15", "Cradle Tracking Synchronized Check?", "Edge / Firmware", "src/core/cradle_tracker.py", "Position sensor verifies cradle index matches expected step count", "Backlog", "Codex"),
        ("16", "Pause & Resync if Mismatched", "Firmware / UI", "src/iot/esp32_driver.py", "Conveyor halts; alert shown on operator UI to resolve misalignment", "Backlog", "Codex"),
        ("17", "Cradle Reaches Segregation Gate", "Firmware / Actuation", "firmware/esp32_actuator.ino", "Delta-t kinematic delay reached: D / v = 25cm / 12.5cm/s = 2000ms", "Done", "Codex"),
        ("18", "Actuate Gate: Fertile", "Firmware / Servo", "Servo Gate 1 (GPIO 18)", "Egg passes gently to incubation tray for continued development", "Done", "Codex"),
        ("19", "Actuate Gate: Infertile (Penoy)", "Firmware / Servo", "Servo Gate 2", "Egg diverted to Penoy collection tray for Day 10 salvage sale (@ P14.00)", "Done", "Codex"),
        ("20", "Actuate Gate: Abnormal (Discard)", "Firmware / Servo", "Servo Gate 3", "Egg diverted to discard bin to prevent bacterial bursting in incubator", "Done", "Codex"),
        ("21", "Record Outcome & Update Statistics", "Edge / Backend", "src/core/session_manager.py", "Increment session counts: Fertile, Infertile, Abnormal, Flagged", "Done", "Codex"),
        ("22", "Session Finalization & Batch Summary", "Backend / Dashboard", "backend/app/services/analytics.py", "Compute batch mortality curve, hatch forecast, and CSV/PDF export", "Done", "Codex")
    ]

    for r_idx, step in enumerate(flow_steps, start=2):
        ws_flow.row_dimensions[r_idx].height = 20
        for c_idx, val in enumerate(step, start=1):
            cell = ws_flow.cell(row=r_idx, column=c_idx, value=val)
            cell.font = REGULAR_FONT
            cell.border = THIN_BORDER
            cell.alignment = Alignment(vertical="center")
            if c_idx in [1, 6, 7]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            if c_idx == 6:
                if val == "Done":
                    cell.fill = STATUS_DONE_FILL
                    cell.font = STATUS_DONE_FONT
                elif val == "In Progress":
                    cell.fill = STATUS_IN_PROGRESS_FILL
                    cell.font = STATUS_IN_PROGRESS_FONT
                else:
                    cell.fill = STATUS_BACKLOG_FILL
                    cell.font = STATUS_BACKLOG_FONT
            elif r_idx % 2 == 1:
                cell.fill = ALT_ROW_FILL

    for col in ws_flow.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws_flow.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 46)

    # -------------------------------------------------------------------------
    # TAB 4: USE CASE TRACEABILITY MATRIX
    # -------------------------------------------------------------------------
    ws_uc = wb.create_sheet(title="Use Cases Traceability")
    ws_uc.views.sheetView[0].showGridLines = True

    uc_headers = [
        "Actor", "Inherits From", "Use Case / Function", "Subsystem",
        "Backend Endpoint / UI View", "Security / RBAC Permission", "Status"
    ]
    for c_idx, h in enumerate(uc_headers, start=1):
        cell = ws_uc.cell(row=1, column=c_idx, value=h)
        cell.font = HEADER_FONT
        cell.fill = MAROON_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center")

    use_cases = [
        ("Candling Worker", "None (Base)", "Log In / Authenticate User", "Auth / UI", "POST /api/v1/auth/login", "WORKER, SUPERVISOR, ADMIN", "Done"),
        ("Candling Worker", "None (Base)", "Manage Candling Session (Start/Pause/Stop)", "Edge Desktop UI", "src/ui/operator_app.py", "WORKER, SUPERVISOR, ADMIN", "In Progress"),
        ("Candling Worker", "None (Base)", "Monitor Live Video Feed", "Edge CV / UI", "src/ui/operator_app.py (60 FPS stream)", "WORKER, SUPERVISOR, ADMIN", "In Progress"),
        ("Candling Worker", "None (Base)", "View Session Statistics (Fertile/Infertile/Abnormal)", "Edge Desktop UI", "Session tally widget", "WORKER, SUPERVISOR, ADMIN", "Done"),
        ("Candling Worker", "None (Base)", "Review Flagged Classifications (Manual Override)", "Edge Desktop UI", "Review Modal + PUT /api/v1/scans/{id}/override", "WORKER, SUPERVISOR, ADMIN", "In Progress"),
        ("Hatchery Supervisor", "Candling Worker", "View Classification Analytics & Mortality Trends", "Dashboard", "GET /api/v1/analytics/overview", "SUPERVISOR, ADMIN", "Done"),
        ("Hatchery Supervisor", "Candling Worker", "Generate Automated Reports (PDF / CSV)", "Backend / Dashboard", "GET /api/v1/reports/batch/{id}/pdf", "SUPERVISOR, ADMIN", "Done"),
        ("Hatchery Supervisor", "Candling Worker", "View Hatchery Multi-Batch Overview", "Dashboard", "Overview Page / Analytics", "SUPERVISOR, ADMIN", "Done"),
        ("Hatchery Supervisor", "Candling Worker", "Manage Incubation Batches (Create/Edit/Close)", "Backend / Dashboard", "POST /api/v1/batches", "SUPERVISOR, ADMIN", "Done"),
        ("Hatchery Supervisor", "Candling Worker", "Review Historical Candling Records", "Backend / Dashboard", "GET /api/v1/scans?batch_id={id}", "SUPERVISOR, ADMIN", "Done"),
        ("Hatchery Supervisor", "Candling Worker", "Monitor Device Status & Sorter Rig Heartbeat", "Backend / Dashboard", "GET /api/v1/devices", "SUPERVISOR, ADMIN", "In Progress"),
        ("System Administrator", "Hatchery Supervisor", "Manage User Accounts (Create/Update/Role)", "Backend / Dashboard", "GET/POST /api/v1/admin/users", "ADMIN Only", "Done"),
        ("System Administrator", "Hatchery Supervisor", "View System Audit Logs & Override History", "Backend / Dashboard", "GET /api/v1/admin/audit-logs", "ADMIN Only", "Done"),
        ("System Administrator", "Hatchery Supervisor", "Configure System Settings (DB, sync, intervals)", "Backend / Dashboard", "GET/PUT /api/v1/settings", "ADMIN Only", "Done"),
        ("System Administrator", "Hatchery Supervisor", "Manage Model Deployment Settings (Weights/Threshold)", "Backend / Edge", "YOLOv8 ONNX config + threshold settings", "ADMIN Only", "In Progress")
    ]

    for r_idx, uc in enumerate(use_cases, start=2):
        ws_uc.row_dimensions[r_idx].height = 20
        for c_idx, val in enumerate(uc, start=1):
            cell = ws_uc.cell(row=r_idx, column=c_idx, value=val)
            cell.font = REGULAR_FONT
            cell.border = THIN_BORDER
            cell.alignment = Alignment(vertical="center")
            if c_idx in [1, 2, 6, 7]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            if c_idx == 7:
                if val == "Done":
                    cell.fill = STATUS_DONE_FILL
                    cell.font = STATUS_DONE_FONT
                else:
                    cell.fill = STATUS_IN_PROGRESS_FILL
                    cell.font = STATUS_IN_PROGRESS_FONT
            elif r_idx % 2 == 1:
                cell.fill = ALT_ROW_FILL

    for col in ws_uc.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws_uc.column_dimensions[col_letter].width = min(max(max_len + 3, 14), 48)

    # Save to file
    out_path = r"d:\Ryle_Gabotero\side_projects\Capstone\docs\OvaLens_Capstone_Feature_Checklist.xlsx"
    wb.save(out_path)
    print(f"✅ Successfully generated Excel checklist: {out_path}")

if __name__ == "__main__":
    build_excel_checklist()
