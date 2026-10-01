#!/usr/bin/env python
"""
generate_checklist_excel.py — Creates an exhaustive, multi-tab Excel feature checklist
for the OvaLens Capstone Ecosystem, enumerating every backend endpoint, edge module,
dashboard page, firmware routine, and AI task.
"""

import sys
from io import TextIOWrapper
from typing import cast

if isinstance(sys.stdout, TextIOWrapper):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

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
    ws_dash = cast(Worksheet, wb.active)
    ws_dash.title = "Executive Overview"
    ws_dash.views.sheetView[0].showGridLines = True

    ws_dash.merge_cells("A1:H1")
    ws_dash["A1"] = "OVALENS: CAPSTONE MASTER FEATURE & ENDPOINT CHECKLIST"
    ws_dash["A1"].font = TITLE_FONT
    ws_dash["A1"].alignment = Alignment(vertical="center")

    ws_dash.merge_cells("A2:H2")
    ws_dash["A2"] = "Foundation University (CCS) • Team DevIn • DSRM + Agile Framework • Two-Tier Agent Architecture"
    ws_dash["A2"].font = SUBTITLE_FONT
    ws_dash["A2"].alignment = Alignment(vertical="center")

    kpis = [
        ("Total Items", "=COUNTA('Master Checklist'!A4:A150)", "B4:C4", "B5:C5"),
        ("Completed [Done]", '=COUNTIF(\'Master Checklist\'!H4:H150, "Done")', "D4:E4", "D5:E5"),
        ("In Progress", '=COUNTIF(\'Master Checklist\'!H4:H150, "In Progress")', "F4:G4", "F5:G5"),
        ("Pending Backlog", '=COUNTIF(\'Master Checklist\'!H4:H150, "Backlog")', "H4:I4", "H5:I5")
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

    ws_dash["A8"] = "Subsystem Domain"
    ws_dash["B8"] = "Scope & Description"
    ws_dash["C8"] = "Total Tasks"
    ws_dash["D8"] = "Done"
    ws_dash["E8"] = "Completion %"
    for col in ["A", "B", "C", "D", "E"]:
        ws_dash[f"{col}8"].font = HEADER_FONT
        ws_dash[f"{col}8"].fill = MAROON_FILL
        ws_dash[f"{col}8"].alignment = Alignment(horizontal="center", vertical="center")

    domain_summary = [
        ("Backend REST API", "All FastAPI routers: Auth, Batches, Scans, Analytics, Reports, Settings, Users", '=COUNTIF(\'Master Checklist\'!C4:C150, "Backend API")', '=COUNTIFS(\'Master Checklist\'!C4:C150, "Backend API", \'Master Checklist\'!H4:H150, "Done")', '=D9/C9'),
        ("Edge CV & Sorter App", "Camera grabber, YOLOv8 ONNX, SQLite WAL, cradle tracker, CustomTkinter 60 FPS", '=COUNTIF(\'Master Checklist\'!C4:C150, "Edge CV")', '=COUNTIFS(\'Master Checklist\'!C4:C150, "Edge CV", \'Master Checklist\'!H4:H150, "Done")', '=D10/C10'),
        ("Dashboard Web Portal", "React 18 + Vite + TS: Tray matrix, batches, analytics, user admin, audit logs", '=COUNTIF(\'Master Checklist\'!C4:C150, "Dashboard")', '=COUNTIFS(\'Master Checklist\'!C4:C150, "Dashboard", \'Master Checklist\'!H4:H150, "Done")', '=D11/C11'),
        ("Firmware & Hardware", "ESP32 Dev Module, optical interrupts, stepper indexed transport, servo diverters", '=COUNTIF(\'Master Checklist\'!C4:C150, "Firmware")', '=COUNTIFS(\'Master Checklist\'!C4:C150, "Firmware", \'Master Checklist\'!H4:H150, "Done")', '=D12/C12'),
        ("AI Model & Dataset", "3,000+ Itik Pinas dataset, 70/15/15 split, training, ONNX FP16 slim, benchmarks", '=COUNTIF(\'Master Checklist\'!C4:C150, "AI & Data")', '=COUNTIFS(\'Master Checklist\'!C4:C150, "AI & Data", \'Master Checklist\'!H4:H150, "Done")', '=D13/C13'),
        ("Research & Docs", "Capstone manuscript (Chapters 1-6), APA citations, thesis defense preparation", '=COUNTIF(\'Master Checklist\'!C4:C150, "Docs & Plan")', '=COUNTIFS(\'Master Checklist\'!C4:C150, "Docs & Plan", \'Master Checklist\'!H4:H150, "Done")', '=D14/C14')
    ]

    for idx, (dom, desc, tot, done, pct) in enumerate(domain_summary, start=9):
        ws_dash[f"A{idx}"] = dom
        ws_dash[f"B{idx}"] = desc
        ws_dash[f"C{idx}"] = tot
        ws_dash[f"D{idx}"] = done
        ws_dash[f"E{idx}"] = pct
        ws_dash[f"A{idx}"].font = BOLD_FONT
        ws_dash[f"B{idx}"].font = REGULAR_FONT
        ws_dash[f"C{idx}"].font = REGULAR_FONT
        ws_dash[f"D{idx}"].font = REGULAR_FONT
        ws_dash[f"E{idx}"].font = BOLD_FONT
        ws_dash[f"C{idx}"].alignment = Alignment(horizontal="center")
        ws_dash[f"D{idx}"].alignment = Alignment(horizontal="center")
        ws_dash[f"E{idx}"].alignment = Alignment(horizontal="center")
        ws_dash[f"E{idx}"].number_format = '0.0%'
        for col in ["A", "B", "C", "D", "E"]:
            ws_dash[f"{col}{idx}"].border = THIN_BORDER

    ws_dash["A17"] = "Global Automated Workflow Rules:"
    ws_dash["A17"].font = Font(name="Segoe UI", size=11, bold=True, color="800000")
    rules = [
        "1. Two-Tier Agent Architecture: Antigravity orchestrates, plans, audits, and commits; Codex implements features and tests.",
        "2. Automated Quality Gate: Every feature MUST pass backend pytest (13 tests), edge pytest (8 tests), and dashboard build.",
        "3. Automated Checklist Sync: Running 'python scripts/verify_and_commit.py --task <TASK_ID> -m \"...\"' marks the item Done here and in PROJECT_PLAN.md.",
        "4. Strict Architectural Tenets: Zero Firebase (100% FastAPI+PostgreSQL), offline SQLite WAL at edge, 3 biological classes, FU branding (#800000)."
    ]
    for r_idx, rule in enumerate(rules, start=18):
        ws_dash[f"A{r_idx}"] = rule
        ws_dash[f"A{r_idx}"].font = REGULAR_FONT

    # -------------------------------------------------------------------------
    # TAB 2: MASTER FEATURE CHECKLIST (EXHAUSTIVE ENUMERATION)
    # -------------------------------------------------------------------------
    ws_master = cast(Worksheet, wb.create_sheet(title="Master Checklist"))
    ws_master.views.sheetView[0].showGridLines = True

    headers = [
        "Task ID", "DSRM Phase", "Subsystem", "Feature / Endpoint",
        "Technical Specification & Acceptance Criteria", "Diagram Reference",
        "Role", "Status", "Priority", "Automated Test / Verification"
    ]
    
    ws_master.row_dimensions[3].height = 28
    for c_idx, h in enumerate(headers, start=1):
        cell = ws_master.cell(row=3, column=c_idx, value=h)
        cell.font = HEADER_FONT
        cell.fill = MAROON_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    items = [
        # --- DOCS & PLANNING ---
        ("TASK-DOC-01", "Phase 1: Planning", "Docs & Plan", "Authentic Manuscript Integration", "Parse DevIn (2026).md into Chapters 1-6 with 15 APA 7 citations and Title/Approval Sheet", "Manuscript 00-06", "Antigravity", "Done", "P0 - Critical", "docs/manuscript/*.md review"),
        ("TASK-DOC-02", "Phase 1: Planning", "Docs & Plan", "Import & Catalog Academic Diagrams", "Embed and convert IPO Matrix, DSRM Methodology, System Flowchart, and Use Case diagrams (.drawio & .html)", "All 4 Diagrams", "Antigravity", "Done", "P0 - Critical", "docs/diagrams catalog audit"),
        ("TASK-DOC-03", "Phase 1: Planning", "Docs & Plan", "Two-Tier Agent Workflow & Quality Gate", "Establish Antigravity + Codex partnership, PROJECT_PLAN.md, CHANGELOG.md, and verify_and_commit.py", "PROJECT_PLAN.md", "Antigravity", "Done", "P0 - Critical", "python scripts/verify_and_commit.py"),
        ("TASK-NEW-SCOPE-01", "Phase 4: Development", "Cross-System", "Day 10 Binary Domain Refactor", "Standardize backend, edge, dashboard, firmware, tests, and docs on Day 10 with FERTILE/INFERTILE outcomes", "System-wide contract", "Codex", "Done", "P0 - Critical", "pytest + npm.cmd run build"),

        # --- BACKEND REST API: AUTH & USERS ---
        ("TASK-BE-AUTH-01", "Phase 4C: Backend", "Backend API", "POST /api/v1/auth/login", "JWT authentication endpoint with bcrypt password verification and role extraction", "Use Case: Worker", "Codex", "Done", "P0 - Critical", "test_login_and_me"),
        ("TASK-BE-AUTH-02", "Phase 4C: Backend", "Backend API", "GET /api/v1/auth/me", "Retrieve current authenticated user profile, permissions, and active status", "Use Case: Worker", "Codex", "Done", "P0 - Critical", "test_login_and_me"),
        ("TASK-BE-AUTH-03", "Phase 4C: Backend", "Backend API", "POST /api/v1/auth/register", "Account registration endpoint with default Candling Worker role", "Use Case: Admin", "Codex", "Done", "P1 - High", "test_rbac_and_admin_security_protections"),
        ("TASK-BE-USR-01", "Phase 4C: Backend", "Backend API", "GET /api/v1/users", "List all system users with role filters (Worker, Supervisor, Admin)", "Use Case: Admin", "Codex", "Done", "P1 - High", "test_rbac_and_admin_security_protections"),
        ("TASK-BE-USR-02", "Phase 4C: Backend", "Backend API", "POST /api/v1/users", "Admin user creation endpoint with RBAC role assignment", "Use Case: Admin", "Codex", "Done", "P1 - High", "test_rbac_and_admin_security_protections"),
        ("TASK-BE-USR-03", "Phase 4C: Backend", "Backend API", "PATCH /api/v1/users/{id}/status", "Toggle user active/deactivated state to revoke credentials", "Use Case: Admin", "Codex", "Done", "P1 - High", "test_rbac_and_admin_security_protections"),
        ("TASK-BE-USR-04", "Phase 4C: Backend", "Backend API", "PATCH /api/v1/users/me/profile", "Allow authenticated user to update their display name and email", "Use Case: Worker", "Codex", "Done", "P2 - Medium", "test_user_profile_and_password_change_flow"),
        ("TASK-BE-USR-05", "Phase 4C: Backend", "Backend API", "PATCH /api/v1/users/me/password", "Secure password change with old password verification", "Use Case: Worker", "Codex", "Done", "P1 - High", "test_user_profile_and_password_change_flow"),

        # --- BACKEND REST API: BATCHES ---
        ("TASK-BE-BAT-01", "Phase 4C: Backend", "Backend API", "GET /api/v1/batches", "List incubation batches with status and genetic group filters", "Use Case: Supervisor", "Codex", "Done", "P0 - Critical", "test_list_batches"),
        ("TASK-BE-BAT-02", "Phase 4C: Backend", "Backend API", "GET /api/v1/batches/active", "Retrieve currently active incubator batches needing candling inspection", "Use Case: Supervisor", "Codex", "Done", "P0 - Critical", "test_list_batches"),
        ("TASK-BE-BAT-03", "Phase 4C: Backend", "Backend API", "POST /api/v1/batches", "Create new incubation batch specifying breed (Itim/Khaki/Kayumanggi) and egg count", "Use Case: Supervisor", "Codex", "Done", "P0 - Critical", "test_batch_analytics_and_milestones"),
        ("TASK-BE-BAT-04", "Phase 4C: Backend", "Backend API", "GET /api/v1/batches/{id}", "Get detailed batch record with tray matrix slots and current milestone", "Use Case: Supervisor", "Codex", "Done", "P0 - Critical", "test_batch_analytics_and_milestones"),
        ("TASK-BE-BAT-05", "Phase 4C: Backend", "Backend API", "GET /api/v1/batches/{id}/analytics", "Incubation analytics: fertility rate, mortality curve, penoy salvage total", "Use Case: Supervisor", "Codex", "Done", "P0 - Critical", "test_batch_analytics_and_milestones"),
        ("TASK-BE-BAT-06", "Phase 4C: Backend", "Backend API", "GET /api/v1/batches/{id}/forecast", "Hatch yield forecast based on the Day 10 fertility rate", "Use Case: Supervisor", "Codex", "Done", "P1 - High", "test_hatch_yield_forecast_and_backup_service"),
        ("TASK-BE-BAT-07", "Phase 4C: Backend", "Backend API", "PUT /api/v1/batches/{id}", "Update batch metadata, notes, and incubator chamber ID", "Use Case: Supervisor", "Codex", "Done", "P1 - High", "test_batch_analytics_and_milestones"),
        ("TASK-BE-BAT-08", "Phase 4C: Backend", "Backend API", "POST /api/v1/batches/{id}/advance-stage", "Advance lifecycle: Setting -> Day 10 -> Hatched -> Completed", "Use Case: Supervisor", "Codex", "Done", "P0 - Critical", "test_batch_analytics_and_milestones"),
        ("TASK-BE-BAT-09", "Phase 4C: Backend", "Backend API", "POST /api/v1/batches/{id}/finalize-hatch", "Close batch lifecycle and record final hatchling count on Day 28", "Use Case: Supervisor", "Codex", "Done", "P1 - High", "test_batch_analytics_and_milestones"),
        ("TASK-BE-BAT-10", "Phase 4C: Backend", "Backend API", "GET /api/v1/batches/{id}/summary", "Comprehensive batch summary DTO for compliance and audit archiving", "Use Case: Supervisor", "Codex", "Done", "P1 - High", "test_batch_analytics_and_milestones"),
        ("TASK-BE-BAT-11", "Phase 4C: Backend", "Backend API", "DELETE /api/v1/batches/{id}", "Soft-delete or purge batch (Admin only protection)", "Use Case: Admin", "Codex", "Done", "P2 - Medium", "test_rbac_and_admin_security_protections"),
        ("TASK-BE-BAT-12", "Phase 4C: Backend", "Backend API", "POST /api/v1/batches/check-milestones", "Automated background cron to flag batches reaching Day 10, 18, 25", "System Flowchart", "Codex", "Done", "P1 - High", "test_batch_analytics_and_milestones"),

        # --- BACKEND REST API: SESSIONS & SCANS ---
        ("TASK-BE-SES-01", "Phase 4C: Backend", "Backend API", "GET /api/v1/sessions", "List all active and completed edge candling sorting sessions", "Use Case: Worker", "Codex", "Done", "P0 - Critical", "test_api.py"),
        ("TASK-BE-SES-02", "Phase 4C: Backend", "Backend API", "POST /api/v1/sessions", "Start new candling session linked to batch and edge sorter device ID", "Use Case: Worker", "Codex", "Done", "P0 - Critical", "test_api.py"),
        ("TASK-BE-SES-03", "Phase 4C: Backend", "Backend API", "GET /api/v1/sessions/{id}", "Get Day 10 progress: total, fertile, and infertile counts", "Use Case: Worker", "Codex", "Done", "P0 - Critical", "test_api.py"),
        ("TASK-BE-SES-04", "Phase 4C: Backend", "Backend API", "PUT /api/v1/sessions/{id}/end", "Conclude candling session and trigger batch analytics recalculation", "Use Case: Worker", "Codex", "Done", "P0 - Critical", "test_api.py"),
        ("TASK-BE-SCN-01", "Phase 4C: Backend", "Backend API", "POST /api/v1/scans/sync", "Idempotent batch scan sync with ON CONFLICT (scan_id) DO NOTHING", "System Flowchart", "Codex", "Done", "P0 - Critical", "test_analytics_overview"),
        ("TASK-BE-SCN-02", "Phase 4C: Backend", "Backend API", "POST /api/v1/scans/upload-image", "Upload high-res candling frame image associated with scan ID", "System Flowchart", "Codex", "Done", "P1 - High", "test_api.py"),
        ("TASK-BE-SCN-03", "Phase 4C: Backend", "Backend API", "GET /api/v1/scans", "Query historical scans with batch_id, stage, class, date filters", "Use Case: Supervisor", "Codex", "Done", "P0 - Critical", "test_api.py"),
        ("TASK-BE-SCN-04", "Phase 4C: Backend", "Backend API", "GET /api/v1/scans/{id}", "Retrieve single scan record with confidence, bounding box, image URI", "Use Case: Supervisor", "Codex", "Done", "P1 - High", "test_api.py"),
        ("TASK-BE-SCN-05", "Phase 4C: Backend", "Backend API", "PATCH /api/v1/scans/{id}/override", "Human-in-the-loop classification override with audit trail logging", "System Flowchart Node 10", "Codex", "Done", "P0 - Critical", "test_human_in_the_loop_override_audit_logging"),

        # --- BACKEND REST API: ANALYTICS & REPORTS ---
        ("TASK-BE-ANL-01", "Phase 4C: Backend", "Backend API", "GET /api/v1/analytics/overview", "Aggregated hatchery statistics (total eggs, fertility rate, cull rate)", "Use Case: Supervisor", "Codex", "Done", "P0 - Critical", "test_analytics_overview"),
        ("TASK-BE-ANL-02", "Phase 4C: Backend", "Backend API", "GET /api/v1/analytics/breed-comparison", "Disaggregated analytics comparing IP-Itim vs IP-Khaki vs IP-Kayumanggi", "Methodology 3.1", "Codex", "Done", "P1 - High", "test_analytics_overview"),
        ("TASK-BE-ANL-03", "Phase 4C: Backend", "Backend API", "GET /api/v1/analytics/mortality-trends", "Longitudinal mortality tracking across batches and candling stages", "Use Case: Supervisor", "Codex", "Done", "P1 - High", "test_mortality_progression"),
        ("TASK-BE-ANL-04", "Phase 4C: Backend", "Backend API", "GET /api/v1/analytics/mortality-progression", "Day 10 cull analysis by breed", "Methodology 3.1", "Codex", "Done", "P1 - High", "test_mortality_progression"),
        ("TASK-BE-ANL-05", "Phase 4C: Backend", "Backend API", "GET /api/v1/analytics/economic-yield", "Day 10 Penoy salvage revenue (Count * P14.00) & thermal energy savings", "AGENTS.md Tenet 3", "Codex", "Done", "P0 - Critical", "test_analytics_economic_yield"),
        ("TASK-BE-REP-01", "Phase 4C: Backend", "Backend API", "GET /api/v1/reports/batch/{id}/csv", "Export CSV spreadsheet containing detailed scan log for batch", "Use Case: Supervisor", "Codex", "Done", "P1 - High", "test_pdf_and_csv_reports"),
        ("TASK-BE-REP-02", "Phase 4C: Backend", "Backend API", "GET /api/v1/reports/batch/{id}/pdf", "Generate official Foundation University formatted PDF compliance report", "Use Case: Supervisor", "Codex", "Done", "P0 - Critical", "test_pdf_and_csv_reports"),

        # --- BACKEND REST API: DEVICES, SETTINGS & AUDIT ---
        ("TASK-BE-DEV-01", "Phase 4C: Backend", "Backend API", "GET /api/v1/devices", "List registered edge sorter hardware rigs with online/offline status", "Use Case: Admin", "Codex", "Done", "P1 - High", "test_api.py"),
        ("TASK-BE-DEV-02", "Phase 4C: Backend", "Backend API", "POST /api/v1/devices/register", "Register new ESP32 / Raspberry Pi edge node with MAC & station ID", "Use Case: Admin", "Codex", "Done", "P1 - High", "test_api.py"),
        ("TASK-BE-DEV-03", "Phase 4C: Backend", "Backend API", "POST /api/v1/devices/{id}/heartbeat", "Edge node heartbeat ping transmitting status, temperature, and FPS", "Use Case: Admin", "Codex", "Done", "P1 - High", "test_api.py"),
        ("TASK-BE-SET-01", "Phase 4C: Backend", "Backend API", "GET /api/v1/settings", "Fetch system settings (penoy price P14, confidence threshold, sync interval)", "Use Case: Admin", "Codex", "Done", "P1 - High", "test_settings_endpoint"),
        ("TASK-BE-SET-02", "Phase 4C: Backend", "Backend API", "PUT /api/v1/settings", "Update system settings with admin validation", "Use Case: Admin", "Codex", "Done", "P1 - High", "test_settings_endpoint"),
        ("TASK-BE-SET-03", "Phase 4C: Backend", "Backend API", "POST /api/v1/settings/backups/create", "Trigger compressed JSON.GZ snapshot of PostgreSQL database", "AGENTS.md Tenet 1", "Codex", "Done", "P1 - High", "test_hatch_yield_forecast_and_backup_service"),
        ("TASK-BE-SET-04", "Phase 4C: Backend", "Backend API", "GET /api/v1/settings/backups", "List available database backup archive files", "Use Case: Admin", "Codex", "Done", "P2 - Medium", "test_hatch_yield_forecast_and_backup_service"),
        ("TASK-BE-SET-05", "Phase 4C: Backend", "Backend API", "GET /api/v1/settings/backups/{file}/download", "Secure endpoint to download encrypted database backup", "Use Case: Admin", "Codex", "Done", "P2 - Medium", "test_hatch_yield_forecast_and_backup_service"),
        ("TASK-BE-AUD-01", "Phase 4C: Backend", "Backend API", "GET /api/v1/audit_logs", "Query immutable system audit trail with user and timestamp filters", "Use Case: Admin", "Codex", "Done", "P0 - Critical", "test_human_in_the_loop_override_audit_logging"),

        # --- EDGE CV & OPERATOR APP ---
        ("TASK-EDGE-CAM-01", "Phase 4B: Edge App", "Edge CV", "Multi-Threaded Circular Frame Grabber", "Thread 1: OpenCV DirectShow/V4L2 continuous circular buffer drain", "AGENTS.md Edge", "Codex", "Done", "P0 - Critical", "test_camera_mock_generation_and_lifecycle"),
        ("TASK-EDGE-CAM-02", "Phase 4B: Edge App", "Edge CV", "Camera Disconnect Recovery & Mock Mode", "Auto-reconnect USB camera and generate mock frames for offline dev", "AGENTS.md Edge", "Codex", "Done", "P1 - High", "test_camera_mock_generation_and_lifecycle"),
        ("TASK-EDGE-AI-01", "Phase 4B: Edge App", "Edge CV", "ONNX Runtime FP16 Inference Engine", "Thread 2: ONNX Runtime execution provider running quantized YOLOv8", "System Flowchart Node 8", "Codex", "Done", "P0 - Critical", "test_inference_engine_and_latency_benchmark"),
        ("TASK-EDGE-AI-02", "Phase 4B: Edge App", "Edge CV", "Geometric Aspect-Ratio & Centering Gate", "Enforce 0.65 <= Aspect Ratio <= 1.45 to prevent classifying non-egg objects", "AGENTS.md Edge", "Codex", "Done", "P1 - High", "test_candling_heuristics_and_vascularization"),
        ("TASK-EDGE-AI-03", "Phase 4B: Edge App", "Edge CV", "Model Cache Warmup Routine", "Execute 3 dummy passes on startup to eliminate first-frame latency spikes", "AGENTS.md Edge", "Codex", "Done", "P1 - High", "test_inference_engine_and_latency_benchmark"),
        ("TASK-EDGE-HEU-01", "Phase 4B: Edge App", "Edge CV", "HSV Candling Luminance Analyzer", "Analyze internal light transmission across yolk/albumin regions", "System Flowchart Node 7", "Codex", "Done", "P1 - High", "test_candling_heuristics_and_vascularization"),
        ("TASK-EDGE-HEU-02", "Phase 4B: Edge App", "Edge CV", "Vascular Vein & Blood Ring Heuristics", "Auxiliary edge detector verifying spider blood veins vs necrotic ring", "System Flowchart Node 8", "Codex", "Done", "P1 - High", "test_candling_heuristics_and_vascularization"),
        ("TASK-EDGE-DB-01", "Phase 4B: Edge App", "Edge CV", "Local SQLite WAL Mode Store", "Thread 4: Local scan persistence with PRAGMA journal_mode = WAL;", "AGENTS.md Edge", "Codex", "Done", "P0 - Critical", "test_local_sqlite_wal_and_queue_diagnostics"),
        ("TASK-EDGE-DB-02", "Phase 4B: Edge App", "Edge CV", "Unsynced Scan FIFO Queue Manager", "Track unsynced scans and handle exponential backoff retry", "AGENTS.md Edge", "Codex", "Done", "P0 - Critical", "test_local_sqlite_wal_and_queue_diagnostics"),
        ("TASK-EDGE-SYN-01", "Phase 4B: Edge App", "Edge CV", "Background REST HTTP Sync Worker", "Non-blocking background HTTP client transmitting batches of 50 scans", "System Flowchart Node 13", "Codex", "Done", "P0 - Critical", "test_sync_worker_diagnostics"),
        ("TASK-EDGE-SYN-02", "Phase 4B: Edge App", "Edge CV", "Local CSV Session Exporter", "Emergency offline CSV exporter saving session records to local USB drive", "AGENTS.md Offline", "Codex", "Done", "P1 - High", "test_csv_session_export"),
        ("TASK-EDGE-SER-01", "Phase 4B: Edge App", "Edge CV", "PySerial ESP32 UART Driver", "Thread 3: Non-blocking serial worker communicating at 115200 baud", "System Flowchart Node 17", "Codex", "Done", "P0 - Critical", "test_esp32_serial_mock_and_motor_commands"),
        ("TASK-EDGE-SER-02", "Phase 4B: Edge App", "Edge CV", "Serial Mock Driver for Hardware-Free Dev", "Simulate ESP32 optical triggers and servo responses in unit tests", "AGENTS.md Firmware", "Codex", "Done", "P1 - High", "test_esp32_serial_mock_and_motor_commands"),
        ("TASK-EDGE-TRK-01", "Phase 4B: Edge App", "Edge CV", "Cradle Tracking FIFO Queue", "Maintain cradle queue mapping cradle_id from image station to sorting gate", "System Flowchart Node 5,11", "Codex", "Backlog", "P0 - Critical", "test_cradle_tracking_queue.py"),
        ("TASK-EDGE-TRK-02", "Phase 4B: Edge App", "Edge CV", "Conveyor Index Resynchronization Handler", "Pause conveyor and alert operator if physical cradle index drifts", "System Flowchart Node 15,16", "Codex", "Backlog", "P1 - High", "test_cradle_resync_handler.py"),
        ("TASK-EDGE-REV-01", "Phase 4B: Edge App", "Edge CV", "Manual Review Fallback State Machine", "Trigger manual review flag when confidence < 0.75 or egg uncentered", "System Flowchart Node 9,10", "Codex", "Backlog", "P0 - Critical", "test_manual_review_fallback.py"),
        ("TASK-EDGE-UI-01", "Phase 4B: Edge App", "Edge CV", "CustomTkinter 60 FPS Operator Desktop UI", "Main Thread: CustomTkinter operator GUI with Foundation University theme", "Use Case: Worker", "Codex", "Done", "P0 - Critical", "Desktop UI smoke launch"),
        ("TASK-EDGE-UI-02", "Phase 4B: Edge App", "Edge CV", "Live Candling Video Viewport", "Smooth video rendering canvas with overlay bounding box and class tag", "Use Case: Worker", "Codex", "Done", "P0 - Critical", "Desktop UI verification"),
        ("TASK-EDGE-UI-03", "Phase 4B: Edge App", "Edge CV", "Real-Time Session Statistics Counters", "Live counters for Fertile, Infertile, and Manual Review", "Use Case: Worker", "Codex", "Done", "P1 - High", "Desktop UI verification"),
        ("TASK-EDGE-UI-04", "Phase 4B: Edge App", "Edge CV", "Interactive Manual Override Dialog Modal", "Modal popup enabling operator to inspect flagged egg and confirm class", "System Flowchart Node 10", "Codex", "Backlog", "P0 - Critical", "Desktop UI modal test"),
        ("TASK-EDGE-UI-05", "Phase 4B: Edge App", "Edge CV", "Conveyor Pause & Emergency Stop Controls", "Instant physical rig pause and serial E-STOP command dispatch", "System Flowchart Node 16", "Codex", "Done", "P1 - High", "Desktop UI verification"),

        # --- DASHBOARD WEB PORTAL ---
        ("TASK-DASH-PG-01", "Phase 4D: Dashboard", "Dashboard", "LoginPage.tsx with JWT Auth", "Login view with Foundation University maroon branding and token persistence", "Use Case: Worker", "Codex", "Done", "P0 - Critical", "npm.cmd run build"),
        ("TASK-DASH-PG-02", "Phase 4D: Dashboard", "Dashboard", "OverviewPage.tsx Real-Time KPI Cards", "High-level summary of active batches, fertility %, and today's sorting volume", "Use Case: Supervisor", "Codex", "Done", "P0 - Critical", "npm.cmd run build"),
        ("TASK-DASH-PG-03", "Phase 4D: Dashboard", "Dashboard", "BatchesPage.tsx Lifecycle Management", "Table of all batches, Day 10 stage advancement, and hatch closure", "Use Case: Supervisor", "Codex", "Done", "P0 - Critical", "npm.cmd run build"),
        ("TASK-DASH-PG-04", "Phase 4D: Dashboard", "Dashboard", "ScanExplorerPage.tsx Visual Search", "Filterable grid of historical scan captures with image lightbox inspection", "Use Case: Supervisor", "Codex", "Done", "P1 - High", "npm.cmd run build"),
        ("TASK-DASH-PG-05", "Phase 4D: Dashboard", "Dashboard", "AnalyticsPage.tsx Multi-Chart Suite", "Recharts visualizer for mortality curves, breed comparisons, and Penoy revenue", "Use Case: Supervisor", "Codex", "Done", "P0 - Critical", "npm.cmd run build"),
        ("TASK-DASH-PG-06", "Phase 4D: Dashboard", "Dashboard", "RecordsPage.tsx Audit Archive", "Historical scan and session records table with one-click CSV/PDF download", "Use Case: Supervisor", "Codex", "Done", "P1 - High", "npm.cmd run build"),
        ("TASK-DASH-PG-07", "Phase 4D: Dashboard", "Dashboard", "DevicesPage.tsx Hardware Monitor", "Live cards showing connected Raspberry Pi and ESP32 sorter rigs", "Use Case: Admin", "Codex", "Done", "P1 - High", "npm.cmd run build"),
        ("TASK-DASH-PG-08", "Phase 4D: Dashboard", "Dashboard", "ModelsPage.tsx MLOps Registry", "View deployed YOLOv8 ONNX model version, latency benchmarks, thresholds", "Use Case: Admin", "Codex", "Done", "P1 - High", "npm.cmd run build"),
        ("TASK-DASH-PG-09", "Phase 4D: Dashboard", "Dashboard", "UsersPage.tsx User Administration", "Admin table for managing operator, supervisor, and administrator accounts", "Use Case: Admin", "Codex", "Done", "P0 - Critical", "npm.cmd run build"),
        ("TASK-DASH-PG-10", "Phase 4D: Dashboard", "Dashboard", "AuditLogsPage.tsx Security Trail", "Chronological table of all system events, login attempts, and overrides", "Use Case: Admin", "Codex", "Done", "P0 - Critical", "npm.cmd run build"),
        ("TASK-DASH-PG-11", "Phase 4D: Dashboard", "Dashboard", "SettingsPage.tsx System Configuration", "Configure Penoy price (P14), confidence thresholds, and DB backup downloads", "Use Case: Admin", "Codex", "Done", "P1 - High", "npm.cmd run build"),
        ("TASK-DASH-CP-01", "Phase 4D: Dashboard", "Dashboard", "Incubation Tray Matrix (42 Slots A1-F7)", "Interactive SVG grid showing physical incubator tray slot occupancy and status", "Use Case: Supervisor", "Codex", "Done", "P0 - Critical", "npm.cmd run build"),
        ("TASK-DASH-CP-02", "Phase 4D: Dashboard", "Dashboard", "Interactive Penoy Economic Calculator", "Widget computing Day 10 salvage income based on P14.00/egg price", "AGENTS.md Tenet 3", "Codex", "Done", "P1 - High", "npm.cmd run build"),
        ("TASK-DASH-CP-03", "Phase 4D: Dashboard", "Dashboard", "Breed Filter: IP-Itim, Khaki, Kayumanggi", "Dropdown to isolate metrics by pure line vs commercial hybrid", "Methodology 3.1", "Codex", "Done", "P1 - High", "npm.cmd run build"),
        ("TASK-DASH-CP-04", "Phase 4D: Dashboard", "Dashboard", "Day 10 Filter", "Filter analytics for the single Day 10 checkpoint", "Methodology 3.1", "Codex", "Done", "P1 - High", "npm.cmd run build"),
        ("TASK-DASH-CP-05", "Phase 4D: Dashboard", "Dashboard", "Dark / Light Mode Theme System", "TailwindCSS theme switcher with FU Maroon (#800000) accents", "AGENTS.md FU Brand", "Codex", "Done", "P2 - Medium", "npm.cmd run build"),

        # --- FIRMWARE & MECHANICAL RIG ---
        ("TASK-FW-INT-01", "Phase 4A: Firmware", "Firmware", "Optical Sensor Hardware Interrupt", "ESP32 GPIO 14 optical beam-break edge detection interrupt", "System Flowchart", "Codex", "Done", "P0 - Critical", "esp32_actuator.ino review"),
        ("TASK-FW-INT-02", "Phase 4A: Firmware", "Firmware", "600ms Hardware Optical Debounce Lockout", "Non-blocking timer lockout preventing false double-triggers on single egg", "AGENTS.md Firmware", "Codex", "Done", "P0 - Critical", "esp32_actuator.ino review"),
        ("TASK-FW-LED-01", "Phase 4A: Firmware", "Firmware", "Candling Strobe LED Driver Relay", "GPIO 19 strobe trigger synchronized with camera exposure", "System Flowchart Node 7", "Codex", "Done", "P1 - High", "esp32_actuator.ino review"),
        ("TASK-FW-SER-01", "Phase 4A: Firmware", "Firmware", "Non-Blocking Serial UART Command Parser", "Buffer incoming 115200 baud UART bytes without delay() calls", "AGENTS.md Firmware", "Codex", "Done", "P0 - Critical", "esp32_actuator.ino review"),
        ("TASK-FW-SER-02", "Phase 4A: Firmware", "Firmware", "Serial ACK / NACK Status Protocol", "Transmit acknowledgement packets upon command execution to edge driver", "System Flowchart Node 3", "Codex", "Backlog", "P1 - High", "Serial loopback test"),
        ("TASK-FW-STP-01", "Phase 4A: Firmware", "Firmware", "Stepper Pocket-Conveyor Transport Routine", "Indexed step timing to advance pocket conveyor one cradle at a time", "System Flowchart Node 6,14", "Codex", "Backlog", "P0 - Critical", "Firmware bench test"),
        ("TASK-FW-SRV-01", "Phase 4A: Firmware", "Firmware", "Servo Gate 1 (Fertile Release)", "Actuate servo diverter for Fertile eggs into cushioned incubation tray", "System Flowchart Node 18", "Codex", "Done", "P0 - Critical", "esp32_actuator.ino review"),
        ("TASK-FW-SRV-02", "Phase 4A: Firmware", "Firmware", "Servo Gate 2 (Infertile / Penoy Salvage)", "Actuate servo diverter for Day 10 Penoy salvage sale (@ P14.00)", "System Flowchart Node 19", "Codex", "Backlog", "P0 - Critical", "Firmware bench test"),
        ("TASK-FW-KIN-01", "Phase 4A: Firmware", "Firmware", "Kinematic Actuation Delay Timer", "Calculate Delta-t = D / v = 25cm / 12.5cm/s = 2000ms delay before servo firing", "Methodology 3.4", "Codex", "Done", "P0 - Critical", "esp32_actuator.ino review"),

        # --- AI MODEL & DATASET ---
        ("TASK-AI-DS-01", "Phase 2: Dataset", "AI & Data", "Dataset 70/15/15 Stratification Pipeline", "Partition 3,000+ candling images into 70% Train, 15% Val, 15% Test", "IPO Matrix / Meth", "Codex", "Backlog", "P0 - Critical", "test_dataset_stratification.py"),
        ("TASK-AI-DS-02", "Phase 2: Dataset", "AI & Data", "Whole-Egg YOLO Bounding Box Validator", "Verify YOLO darknet format [class_id, x, y, w, h] enclosing whole egg", "IPO Matrix", "Codex", "Backlog", "P1 - High", "test_annotation_bounds.py"),
        ("TASK-AI-DS-03", "Phase 2: Dataset", "AI & Data", "Candling Transillumination Augmentations", "HSV luminance jitter (V +/-20%) and +/-15 deg rotation pipeline", "Chapter 3.2", "Codex", "Backlog", "P2 - Medium", "test_augmentation_visuals.py"),
        ("TASK-AI-DS-04", "Phase 2: Dataset", "AI & Data", "Dataset Distribution Summary Exporter", "Generate automated Markdown and LaTeX tables of egg counts for manuscript", "Chapter 3.2", "Codex", "Backlog", "P2 - Medium", "export_dataset_table.py"),
        ("TASK-AI-TRN-01", "Phase 3: AI Vision", "AI & Data", "Ultralytics YOLOv8 Training Script", "Implement model training pipeline with CIoU + BCE + DFL loss functions", "Methodology 3.3", "Codex", "Backlog", "P1 - High", "train_yolov8.py smoke test"),
        ("TASK-AI-OPT-01", "Phase 3: AI Vision", "AI & Data", "ONNX FP16 Slim Export & Half-Precision Graph", "Convert PyTorch weights to ONNX FP16 slim graph for edge inference", "AGENTS.md Tenet 3", "Codex", "Done", "P0 - Critical", "export_onnx.py check"),
        ("TASK-AI-OPT-02", "Phase 3: AI Vision", "AI & Data", "Production Weights 'edge/models/weights/best.onnx'", "Verified production ONNX FP16 weights ready for edge execution", "AGENTS.md Tenet 3", "Codex", "Done", "P0 - Critical", "test_inference_engine_and_latency_benchmark"),
        ("TASK-AI-LAT-01", "Phase 3: AI Vision", "AI & Data", "Edge Inference Latency Benchmark (<=200ms)", "Benchmark inference latency ensuring <= 200 ms SLA on edge hardware", "Chapter 1 Objectives", "Codex", "Done", "P0 - Critical", "test_inference_engine_and_latency_benchmark"),
        ("TASK-AI-EVL-01", "Phase 3: AI Vision", "AI & Data", "Breed Subgroup Metric Evaluator", "Compute Precision, Recall, F1, mAP for IP-Itim, Khaki, and Kayumanggi", "IPO Matrix", "Codex", "Backlog", "P1 - High", "test_subgroup_metrics.py"),
        ("TASK-AI-EVL-02", "Phase 3: AI Vision", "AI & Data", "Day 10 Subgroup Metric Evaluator", "Compute Precision, Recall, F1, and mAP across Day 10 cohorts", "IPO Matrix", "Codex", "Backlog", "P1 - High", "test_subgroup_metrics.py"),
        ("TASK-AI-EVL-03", "Phase 3: AI Vision", "AI & Data", "2-Class Confusion Matrix & PR Curve Generator", "Generate Fertile/Infertile metrics for Chapter 4", "Chapter 4 Manuscript", "Codex", "Backlog", "P0 - Critical", "generate_confusion_matrix.py"),

        # --- INTEGRATION & EVALUATION ---
        ("TASK-INT-01", "Phase 5: Integration", "Integration", "End-to-End Sorting Pilot Simulation", "Simulate 50-egg continuous cycle: load -> index -> capture -> predict -> divert -> sync", "System Flowchart", "Antigravity / Codex", "Backlog", "P0 - Critical", "test_end_to_end_pilot.py"),
        ("TASK-INT-02", "Phase 5: Integration", "Integration", "Offline Network Replay Resilience Test", "Cut network; confirm 100% sorting at edge; reconnect and verify bulk replay", "AGENTS.md Offline", "Antigravity / Codex", "Backlog", "P0 - Critical", "test_offline_network_replay.py"),
        ("TASK-INT-03", "Phase 5: Integration", "Integration", "Cradle Position Jam Recovery Test", "Simulate mechanical index slip; verify conveyor pauses and resyncs", "System Flowchart Node 16", "Antigravity / Codex", "Backlog", "P1 - High", "test_cradle_resync_handler.py"),
        ("TASK-EVL-01", "Phase 6: Evaluation", "Evaluation", "Physical Sorting Accuracy Benchmark", "Run >= 100 physical duck egg trials to measure sorting accuracy rate", "Chapter 1 Objectives", "Antigravity", "Backlog", "P0 - Critical", "Physical trial tally sheet"),
        ("TASK-EVL-02", "Phase 6: Evaluation", "Evaluation", "System Throughput & Cycle Time Profiling", "Measure end-to-end cycle time per egg and throughput (eggs/min)", "Chapter 1 Objectives", "Antigravity", "Backlog", "P1 - High", "Kinematics benchmark report"),
        ("TASK-DEF-01", "Phase 7: Defense", "Defense Prep", "Manuscript Chapter 4 (Results & Discussion)", "Draft Chapter 4 using empirical metrics, confusion matrices, latency charts", "Chapter 4", "Antigravity", "Backlog", "P0 - Critical", "Manuscript peer review"),
        ("TASK-DEF-02", "Phase 7: Defense", "Defense Prep", "Manuscript Chapter 5 (Conclusions & Recommendations)", "Summarize findings, answer research questions 1-4, formulate recommendations", "Chapter 5", "Antigravity", "Backlog", "P0 - Critical", "Adviser review"),
        ("TASK-DEF-03", "Phase 7: Defense", "Deployment", "1-Click Docker Production Verification", "Verify docker-compose up for PostgreSQL 16, FastAPI backend, React dashboard", "docker-compose.yml", "Antigravity / Codex", "Done", "P0 - Critical", "docker-compose config test")
    ]

    for row_idx, item in enumerate(items, start=4):
        ws_master.row_dimensions[row_idx].height = 22
        for col_idx, val in enumerate(item, start=1):
            cell = ws_master.cell(row=row_idx, column=col_idx, value=val)
            cell.font = REGULAR_FONT
            cell.border = THIN_BORDER
            cell.alignment = Alignment(vertical="center")

            if col_idx in [1, 2, 7, 8, 9]:
                cell.alignment = Alignment(horizontal="center", vertical="center")

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

    for ws in [ws_dash, ws_master]:
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(cast(int, col[0].column))
            ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 52)

    ws_master.column_dimensions["A"].width = 18
    ws_master.column_dimensions["B"].width = 20
    ws_master.column_dimensions["C"].width = 16
    ws_master.column_dimensions["D"].width = 38
    ws_master.column_dimensions["E"].width = 52
    ws_master.column_dimensions["F"].width = 22
    ws_master.column_dimensions["G"].width = 16
    ws_master.column_dimensions["H"].width = 14
    ws_master.column_dimensions["I"].width = 16
    ws_master.column_dimensions["J"].width = 40

    out_path = r"d:\Ryle_Gabotero\side_projects\Capstone\docs\OvaLens_Capstone_Feature_Checklist.xlsx"
    wb.save(out_path)
    print(f"✅ Generated exhaustive Excel checklist with {len(items)} items: {out_path}")

if __name__ == "__main__":
    build_excel_checklist()
