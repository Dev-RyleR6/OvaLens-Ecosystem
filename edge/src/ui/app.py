"""
OvaLens Operator Desktop GUI (CustomTkinter 60 FPS)
Foundation University Automated Duck Egg Candling & Conveyor Sorting System.
On-Demand Camera Lifecycle + Real-Time Live AI Bounding Box & Class Detection Overlays.
"""

import os
import time
import uuid
import threading
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple

import cv2
import numpy as np
from PIL import Image, ImageTk
import customtkinter as ctk

from .theme import FUTheme
from ..core.camera import CameraGrabber
from ..core.inference import InferenceEngine
from ..iot.serial_driver import ESP32SerialDriver
from ..db.local_db import LocalDatabaseManager
from ..sync.sync_worker import BackgroundSyncWorker


class OvaLensOperatorApp(ctk.CTk):
    def __init__(self, camera: CameraGrabber, engine: InferenceEngine,
                 iot: ESP32SerialDriver, db: LocalDatabaseManager,
                 sync_worker: BackgroundSyncWorker, device_id: str = "STATION-01-RP5"):
        super().__init__()

        self.camera = camera
        self.engine = engine
        self.iot = iot
        self.db = db
        self.sync_worker = sync_worker
        self.device_id = device_id

        # Conveyor & Chamber Timing Defaults
        self.conveyor_speed_cm_s = 12.50
        self.conveyor_dist_cm = 25.00
        self.servo_pulse_ms = 250
        self.chamber_pause_ms = 350       # Time conveyor pauses inside chamber for blur-free candling
        self.conveyor_advance_ms = 900     # Time conveyor moves between consecutive eggs

        # Batch & Session Configuration
        self.current_session_id: Optional[str] = None
        self.current_batch_id: str = "BATCH-2026-08-KAY-01"
        self.current_breed: str = "KAYUMANGGI"
        self.current_stage: str = "DAY_10"
        self.target_egg_count: int = 500
        self.incubator_id: str = "INCUBATOR-A1"
        self.operator_name: str = "Pedro Penduko"
        self.is_session_active: bool = False
        self.is_auto_cycle_running: bool = False
        self.scan_sequence: int = 0

        # Automated Cycle Threading
        self._auto_cycle_thread: Optional[threading.Thread] = None
        self._stop_cycle_event = threading.Event()

        # Live Real-time Inference Cache
        self._latest_detections: List[Dict[str, Any]] = []
        self._last_live_infer_time = 0.0

        # Live Counters
        self.total_count = 0
        self.fertile_count = 0
        self.infertile_count = 0
        self.abnormal_count = 0

        # Window Configuration (Light Institutional Theme)
        self.title("OvaLens — Automated Duck Egg Candling System (Foundation University)")
        self.geometry("1280x850")
        self.minsize(1024, 720)
        ctk.set_appearance_mode("light")
        self.configure(fg_color=FUTheme.BG_LIGHT)

        # Setup UI Layout
        self._build_header()
        self._build_main_layout()
        self._build_footer()

        # Keyboard Accelerators
        self.bind("<space>", lambda event: self.trigger_candling_scan())
        self.bind("r", lambda event: self.trigger_manual_eject())
        self.bind("R", lambda event: self.trigger_manual_eject())

        # Start Video & Telemetry Loops
        self._update_video_frame()
        self._update_status_loop()

    def _build_header(self):
        self.header_frame = ctk.CTkFrame(
            self, fg_color=FUTheme.PANEL_LIGHT, corner_radius=0, height=64,
            border_width=1, border_color=FUTheme.BORDER
        )
        self.header_frame.pack(side="top", fill="x")

        # Left: University & Project Brand
        brand_container = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        brand_container.pack(side="left", padx=18, pady=10)

        badge = ctk.CTkLabel(
            brand_container, text=" FU ", fg_color=FUTheme.PRIMARY_MAROON,
            text_color=FUTheme.TEXT_WHITE, font=(FUTheme.FONT_FAMILY, 13, "bold"),
            corner_radius=6, padx=4, pady=2
        )
        badge.pack(side="left", padx=(0, 10))

        title_box = ctk.CTkFrame(brand_container, fg_color="transparent")
        title_box.pack(side="left")

        title = ctk.CTkLabel(
            title_box, text="OvaLens Edge Operator",
            font=(FUTheme.FONT_FAMILY, 15, "bold"), text_color=FUTheme.TEXT_PRIMARY
        )
        title.pack(anchor="w")

        subtitle = ctk.CTkLabel(
            title_box, text="Foundation University • Team DevIn",
            font=(FUTheme.FONT_FAMILY, 10), text_color=FUTheme.TEXT_MUTED
        )
        subtitle.pack(anchor="w")

        # Center: Interactive Active Batch Setup Button
        self.batch_btn = ctk.CTkButton(
            self.header_frame,
            text=f"📋 Batch: {self.current_batch_id}  ({self.current_stage})  ▾",
            font=(FUTheme.FONT_FAMILY, 12, "bold"),
            fg_color=FUTheme.PANEL_LIGHT_ALT,
            text_color=FUTheme.TEXT_PRIMARY,
            hover_color=FUTheme.BORDER,
            border_width=1,
            border_color=FUTheme.BORDER,
            command=self.open_batch_setup_dialog,
            height=34, corner_radius=6
        )
        self.batch_btn.pack(side="left", padx=20)

        # Right: Status Telemetry Badges
        right_container = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        right_container.pack(side="right", padx=18)

        self.fps_label = ctk.CTkLabel(
            right_container, text="FPS: 0.0", font=(FUTheme.FONT_FAMILY, 11, "bold"), text_color=FUTheme.TEXT_MUTED
        )
        self.fps_label.pack(side="left", padx=8)

        self.iot_status_badge = ctk.CTkLabel(
            right_container, text="ESP32: STANDBY", fg_color=FUTheme.PANEL_LIGHT_ALT,
            text_color=FUTheme.TEXT_PRIMARY, font=(FUTheme.FONT_FAMILY, 10, "bold"),
            corner_radius=4, padx=8, pady=3
        )
        self.iot_status_badge.pack(side="left", padx=4)

        self.net_status_badge = ctk.CTkLabel(
            right_container, text="SYNC: ONLINE", fg_color=FUTheme.FERTILE_GREEN,
            text_color=FUTheme.TEXT_WHITE, font=(FUTheme.FONT_FAMILY, 10, "bold"),
            corner_radius=4, padx=8, pady=3
        )
        self.net_status_badge.pack(side="left", padx=4)

    def _build_main_layout(self):
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=16, pady=12)

        # Left Column: Live Candling Viewport & Conveyor Status HUD
        self.left_panel = ctk.CTkFrame(
            self.main_container, fg_color=FUTheme.PANEL_LIGHT, corner_radius=12,
            border_width=1, border_color=FUTheme.BORDER
        )
        self.left_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # Top of Left Panel: Live Automated Cycle State Indicator
        self.cycle_hud = ctk.CTkFrame(self.left_panel, fg_color=FUTheme.PANEL_LIGHT_ALT, height=36, corner_radius=8)
        self.cycle_hud.pack(fill="x", padx=10, pady=(10, 6))
        self.cycle_hud.pack_propagate(False)

        self.cycle_status_dot = ctk.CTkLabel(
            self.cycle_hud, text="●", font=(FUTheme.FONT_FAMILY, 12, "bold"), text_color=FUTheme.TEXT_MUTED
        )
        self.cycle_status_dot.pack(side="left", padx=(12, 6))

        self.cycle_status_label = ctk.CTkLabel(
            self.cycle_hud, text="CAMERA & CONVEYOR STANDBY — CLICK 'START AUTO SORTING' TO ACTIVATE",
            font=(FUTheme.FONT_FAMILY, 11, "bold"), text_color=FUTheme.TEXT_PRIMARY
        )
        self.cycle_status_label.pack(side="left")

        # Inner container with disabled propagation to lock video dimensions
        self.video_container = ctk.CTkFrame(self.left_panel, fg_color="#0F172A", corner_radius=8)
        self.video_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.video_container.pack_propagate(False)

        # Video HUD Canvas
        self.video_label = ctk.CTkLabel(
            self.video_container,
            text="📷 CAMERA IN STANDBY\n\nClick 'START AUTO SORTING' to activate live video stream\nand real-time YOLOv8 egg classification",
            font=(FUTheme.FONT_FAMILY, 13, "bold"),
            fg_color="#0F172A", text_color=FUTheme.TEXT_MUTED
        )
        self.video_label.place(relx=0.5, rely=0.5, anchor="center")

        # Right Column: Controls & Live Analytics (Fixed width 440px)
        self.right_panel = ctk.CTkFrame(self.main_container, fg_color="transparent", width=440)
        self.right_panel.pack(side="right", fill="both", padx=(0, 0))
        self.right_panel.pack_propagate(False)

        # 1. Classification Result Banner
        self.result_banner = ctk.CTkFrame(
            self.right_panel, fg_color=FUTheme.PANEL_LIGHT, corner_radius=12, height=105,
            border_width=1, border_color=FUTheme.BORDER
        )
        self.result_banner.pack(fill="x", pady=(0, 10))
        self.result_banner.pack_propagate(False)

        top_banner_row = ctk.CTkFrame(self.result_banner, fg_color="transparent")
        top_banner_row.pack(fill="x", padx=16, pady=(14, 2))

        self.result_badge = ctk.CTkLabel(
            top_banner_row, text="STANDBY", font=(FUTheme.FONT_FAMILY, 10, "bold"),
            fg_color=FUTheme.PANEL_LIGHT_ALT, text_color=FUTheme.TEXT_MUTED,
            corner_radius=4, padx=8, pady=2
        )
        self.result_badge.pack(side="left")

        self.latency_label = ctk.CTkLabel(
            top_banner_row, text="Latency: -- ms", font=(FUTheme.FONT_FAMILY, 10), text_color=FUTheme.TEXT_DIM
        )
        self.latency_label.pack(side="right")

        self.result_title = ctk.CTkLabel(
            self.result_banner, text="Ready for Auto Sorting",
            font=(FUTheme.FONT_FAMILY, 18, "bold"), text_color=FUTheme.TEXT_PRIMARY
        )
        self.result_title.pack(anchor="w", padx=16, pady=(2, 1))

        self.result_subtitle = ctk.CTkLabel(
            self.result_banner, text="Conveyor automatically advances, pauses inside chamber, and sorts",
            font=(FUTheme.FONT_FAMILY, 11), text_color=FUTheme.TEXT_MUTED
        )
        self.result_subtitle.pack(anchor="w", padx=16)

        # 2. Live Batch Counters & Progress Panel
        counters_frame = ctk.CTkFrame(
            self.right_panel, fg_color=FUTheme.PANEL_LIGHT, corner_radius=12,
            border_width=1, border_color=FUTheme.BORDER
        )
        counters_frame.pack(fill="x", pady=(0, 10))

        c_header = ctk.CTkFrame(counters_frame, fg_color="transparent")
        c_header.pack(fill="x", padx=16, pady=(12, 4))

        c_title = ctk.CTkLabel(
            c_header, text="BATCH PROGRESS & METRICS", font=(FUTheme.FONT_FAMILY, 11, "bold"),
            text_color=FUTheme.TEXT_MUTED
        )
        c_title.pack(side="left")

        self.progress_pct_label = ctk.CTkLabel(
            c_header, text="0.0% (0 / 500)", font=(FUTheme.FONT_FAMILY, 10, "bold"),
            text_color=FUTheme.PRIMARY_MAROON
        )
        self.progress_pct_label.pack(side="right")

        # Progress Bar
        self.progress_bar = ctk.CTkProgressBar(
            counters_frame, height=6, corner_radius=3, fg_color=FUTheme.PANEL_LIGHT_ALT,
            progress_color=FUTheme.PRIMARY_MAROON
        )
        self.progress_bar.pack(fill="x", padx=16, pady=(0, 10))
        self.progress_bar.set(0.0)

        grid = ctk.CTkFrame(counters_frame, fg_color="transparent")
        grid.pack(fill="x", padx=10, pady=(0, 12))

        # 4 Clean Stat Tiles
        self.box_total = self._create_stat_box(grid, "TOTAL SCANNED", f"0 / {self.target_egg_count}", 0, 0, accent_color=FUTheme.TEXT_PRIMARY)
        self.box_fertile = self._create_stat_box(grid, "FERTILE (ACCEPT)", "0 (0%)", 0, 1, accent_color=FUTheme.FERTILE_GREEN)
        self.box_infertile = self._create_stat_box(grid, "INFERTILE (PENOY)", "0", 1, 0, accent_color=FUTheme.INFERTILE_AMBER)
        self.box_abnormal = self._create_stat_box(grid, "ABNORMAL (REJECT)", "0", 1, 1, accent_color=FUTheme.ABNORMAL_RED)

        # 3. Recent Scans Log
        log_frame = ctk.CTkFrame(
            self.right_panel, fg_color=FUTheme.PANEL_LIGHT, corner_radius=12,
            border_width=1, border_color=FUTheme.BORDER
        )
        log_frame.pack(fill="both", expand=True)

        log_header = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_header.pack(fill="x", padx=16, pady=(10, 4))

        log_title = ctk.CTkLabel(
            log_header, text="RECENT SCANS LOG", font=(FUTheme.FONT_FAMILY, 11, "bold"),
            text_color=FUTheme.TEXT_MUTED
        )
        log_title.pack(side="left")

        self.log_textbox = ctk.CTkTextbox(
            log_frame, fg_color=FUTheme.PANEL_LIGHT_ALT, text_color=FUTheme.TEXT_PRIMARY,
            font=("Consolas", 11), activate_scrollbars=True, corner_radius=8
        )
        self.log_textbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.log_textbox.configure(state="disabled")

    def _create_stat_box(self, parent, label_text: str, val_text: str, row: int, col: int, accent_color: str):
        f = ctk.CTkFrame(parent, fg_color=FUTheme.PANEL_LIGHT_ALT, corner_radius=8)
        f.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")
        parent.grid_columnconfigure(col, weight=1)

        top_strip = ctk.CTkFrame(f, fg_color=accent_color, height=3, corner_radius=2)
        top_strip.pack(fill="x", side="top")

        lbl = ctk.CTkLabel(f, text=label_text, font=(FUTheme.FONT_FAMILY, 9, "bold"), text_color=FUTheme.TEXT_MUTED)
        lbl.pack(anchor="w", padx=10, pady=(6, 0))

        val = ctk.CTkLabel(f, text=val_text, font=(FUTheme.FONT_FAMILY, 15, "bold"), text_color=FUTheme.TEXT_PRIMARY)
        val.pack(anchor="w", padx=10, pady=(0, 6))
        return val

    def _build_footer(self):
        self.footer_frame = ctk.CTkFrame(
            self, fg_color=FUTheme.PANEL_LIGHT, corner_radius=0, height=68,
            border_width=1, border_color=FUTheme.BORDER
        )
        self.footer_frame.pack(side="bottom", fill="x")

        # Automated Cycle Button (Starts Camera & Sorting Loop)
        self.session_btn = ctk.CTkButton(
            self.footer_frame, text="▶ START AUTO SORTING", font=(FUTheme.FONT_FAMILY, 13, "bold"),
            fg_color=FUTheme.FERTILE_GREEN, hover_color=FUTheme.FERTILE_GREEN_HOVER,
            text_color=FUTheme.TEXT_WHITE, command=self.toggle_auto_session,
            width=210, height=42, corner_radius=8
        )
        self.session_btn.pack(side="left", padx=(18, 8), pady=13)

        # Single Trigger Scan Button (Manual Override)
        self.scan_btn = ctk.CTkButton(
            self.footer_frame, text="⚡ Single Scan [SPACE]", font=(FUTheme.FONT_FAMILY, 12, "bold"),
            fg_color=FUTheme.PRIMARY_MAROON, hover_color=FUTheme.HOVER_MAROON,
            text_color=FUTheme.TEXT_WHITE, command=self.trigger_candling_scan,
            width=180, height=42, corner_radius=8
        )
        self.scan_btn.pack(side="left", padx=8, pady=13)

        # Manual Eject Button
        self.eject_btn = ctk.CTkButton(
            self.footer_frame, text="⏏ Manual Eject [R]", font=(FUTheme.FONT_FAMILY, 12, "bold"),
            fg_color=FUTheme.PANEL_LIGHT_ALT, hover_color=FUTheme.ABNORMAL_RED_BG,
            text_color=FUTheme.TEXT_PRIMARY, command=self.trigger_manual_eject,
            width=150, height=42, corner_radius=8
        )
        self.eject_btn.pack(side="left", padx=8, pady=13)

        # Batch Setup Quick Button
        self.batch_setup_btn = ctk.CTkButton(
            self.footer_frame, text="📋 Batch Setup", font=(FUTheme.FONT_FAMILY, 12, "bold"),
            fg_color=FUTheme.PANEL_LIGHT_ALT, hover_color=FUTheme.BORDER,
            text_color=FUTheme.TEXT_PRIMARY, command=self.open_batch_setup_dialog,
            width=130, height=42, corner_radius=8
        )
        self.batch_setup_btn.pack(side="right", padx=(8, 18), pady=13)

        # Conveyor Settings Button
        self.settings_btn = ctk.CTkButton(
            self.footer_frame, text="⚙ Conveyor Config", font=(FUTheme.FONT_FAMILY, 12),
            fg_color="transparent", border_width=1, border_color=FUTheme.BORDER,
            text_color=FUTheme.TEXT_MUTED, hover_color=FUTheme.PANEL_LIGHT_ALT,
            command=self.open_calibration_dialog, width=140, height=42, corner_radius=8
        )
        self.settings_btn.pack(side="right", padx=8, pady=13)

    def toggle_auto_session(self):
        """Toggle automated full conveyor sorting cycle with on-demand camera start."""
        if not self.is_session_active:
            # 1. Start Camera Stream On-Demand
            if not self.camera.is_running:
                self.camera.start()

            # 2. Start New Session & Auto Conveyor Cycle
            self.current_session_id = str(uuid.uuid4())
            self.is_session_active = True
            self.is_auto_cycle_running = True
            self.scan_sequence = 0
            self.total_count = 0
            self.fertile_count = 0
            self.infertile_count = 0
            self.abnormal_count = 0

            # Record in SQLite WAL
            self.db.create_session(
                session_id=self.current_session_id,
                batch_id=self.current_batch_id,
                device_id=self.device_id,
                stage=self.current_stage,
                operator_name=self.operator_name
            )

            # Sync session creation to FastAPI backend
            self.sync_worker.register_session({
                "session_id": self.current_session_id,
                "batch_id": self.current_batch_id,
                "device_id": self.device_id,
                "stage": self.current_stage,
                "operator_name": self.operator_name,
                "started_at": datetime.now(timezone.utc).isoformat()
            })

            # Update UI state
            self.session_btn.configure(
                text="⏹ STOP AUTO SORTING", fg_color=FUTheme.ABNORMAL_RED,
                hover_color=FUTheme.ABNORMAL_RED_HOVER
            )
            self._update_counters_ui()
            self._log(f"[*] AUTO SESSION STARTED: {self.current_session_id[:8]}... (Batch: {self.current_batch_id}, Target: {self.target_egg_count} eggs)")

            # Launch Automated Conveyor Cycle Worker Thread
            self._stop_cycle_event.clear()
            self._auto_cycle_thread = threading.Thread(target=self._auto_conveyor_cycle_loop, daemon=True, name="OvaLens-ConveyorCycle")
            self._auto_cycle_thread.start()
        else:
            # Stop Session & Release Camera
            self._stop_auto_cycle()

    def _stop_auto_cycle(self):
        self.is_session_active = False
        self.is_auto_cycle_running = False
        self._stop_cycle_event.set()
        self.iot.set_conveyor(False)

        # Stop Camera Stream on Session End
        if self.camera.is_running:
            self.camera.stop()

        self.session_btn.configure(
            text="▶ START AUTO SORTING", fg_color=FUTheme.FERTILE_GREEN,
            hover_color=FUTheme.FERTILE_GREEN_HOVER
        )
        self._update_cycle_hud("●", FUTheme.TEXT_MUTED, "CAMERA & CONVEYOR STANDBY — SESSION IDLE")
        self.video_label.configure(
            image=None,
            text="📷 CAMERA IN STANDBY\n\nClick 'START AUTO SORTING' to activate live video stream\nand real-time YOLOv8 egg classification"
        )
        self._log(f"[OK] Auto sorting ended. Completed {self.total_count}/{self.target_egg_count} eggs.")

    def _auto_conveyor_cycle_loop(self):
        """
        Industrial Automated Conveyor State Machine:
        1. Motor Advances Conveyor
        2. Egg enters dark candling chamber (Conveyor Pauses for blur-free optical capture)
        3. AI Vision inference executes
        4. Servo diverter actuates if rejected; lets egg pass to incubator lane if fertile
        5. Automatically repeats until target batch count is satisfied
        """
        while self.is_auto_cycle_running and not self._stop_cycle_event.is_set():
            if self.total_count >= self.target_egg_count:
                self.after(0, lambda: self._on_batch_target_complete())
                break

            # PHASE 1: Motor Advance (Transport egg to candling aperture)
            self.after(0, lambda: self._update_cycle_hud("🟢", FUTheme.FERTILE_GREEN, f"CONVEYOR ADVANCING EGG #{self.total_count + 1}..."))
            self.iot.set_conveyor(True)
            time.sleep(self.conveyor_advance_ms / 1000.0)

            if self._stop_cycle_event.is_set():
                break

            # PHASE 2: Chamber Entry & Stabilization Pause
            self.after(0, lambda: self._update_cycle_hud("🟡", FUTheme.INFERTILE_AMBER, f"EGG #{self.total_count + 1} IN CHAMBER — PAUSED FOR CANDLING"))
            self.iot.set_conveyor(False)
            time.sleep(self.chamber_pause_ms / 1000.0)

            if self._stop_cycle_event.is_set():
                break

            # PHASE 3: AI Candling Scan & Actuation
            self.after(0, lambda: self._update_cycle_hud("🔵", FUTheme.PRIMARY_MAROON, f"AI INFERENCE — SCANNING EGG #{self.total_count + 1}..."))
            self.after(0, self.trigger_candling_scan)

            # Settle time between cycles
            time.sleep(0.4)

    def _on_batch_target_complete(self):
        self._stop_auto_cycle()
        self._update_cycle_hud("🏁", FUTheme.FERTILE_GREEN, f"BATCH COMPLETE: ALL {self.target_egg_count} EGGS SORTED!")
        self._log(f"[COMPLETE] Batch {self.current_batch_id} fully scanned ({self.target_egg_count}/{self.target_egg_count} eggs).")

    def _update_cycle_hud(self, dot_icon: str, dot_color: str, status_text: str):
        self.cycle_status_dot.configure(text=dot_icon, text_color=dot_color)
        self.cycle_status_label.configure(text=status_text)

    def trigger_candling_scan(self):
        """Perform instant snapshot inference and trigger conveyor actuator if rejected."""
        # Ensure camera is running if triggered manually in single scan
        if not self.camera.is_running:
            self.camera.start()
            time.sleep(0.1)

        frame = self.camera.get_latest_frame()
        if frame is None:
            return

        if not self.is_session_active:
            self.current_session_id = self.current_session_id or str(uuid.uuid4())
            self.is_session_active = True
            self.db.create_session(
                session_id=self.current_session_id,
                batch_id=self.current_batch_id,
                device_id=self.device_id,
                stage=self.current_stage,
                operator_name=self.operator_name
            )

        self.scan_sequence += 1
        scan_id = str(uuid.uuid4())

        # Run AI Model Inference (YOLOv8 + ONNX Runtime)
        result = self.engine.predict(frame)
        final_cls = result["final_class"]
        conf = result["confidence"]
        action = result["routing_action"]
        lat_ms = result["inference_ms"]
        detections = result["detections"]

        # Cache detections for live overlay
        self._latest_detections = detections

        # If rejected, schedule ESP32 conveyor kicker
        if action == "REJECT":
            delay_ms = max(50, int((self.conveyor_dist_cm / max(1.0, self.conveyor_speed_cm_s)) * 1000))
            self.iot.schedule_ejection(delay_ms, self.servo_pulse_ms)

        # Record scan to local SQLite WAL
        self.db.record_scan(
            scan_id=scan_id,
            session_id=self.current_session_id,
            batch_id=self.current_batch_id,
            sequence_number=self.scan_sequence,
            final_class=final_cls,
            confidence=conf,
            inference_ms=lat_ms,
            routing_action=action,
            detections=detections
        )

        # Update Counters
        self.total_count += 1
        if final_cls == "FERTILE":
            self.fertile_count += 1
        elif final_cls == "INFERTILE":
            self.infertile_count += 1
        else:
            self.abnormal_count += 1

        self._update_counters_ui()
        self._update_result_banner(final_cls, conf, action, lat_ms)
        self._log(f"#{self.scan_sequence:03d} | {final_cls:<9} | {conf*100:5.1f}% | {action:<6} | {lat_ms}ms")

    def trigger_manual_eject(self):
        """Fire servo kicker immediately."""
        self.iot.trigger_ejection_now()
        self._log("[ACTION] Manual Ejection Triggered.")

    def _update_result_banner(self, final_cls: str, conf: float, action: str, lat_ms: int):
        if final_cls == "FERTILE":
            badge_color = FUTheme.FERTILE_GREEN
            title_text = f"FERTILE — ACCEPT ({conf*100:.1f}%)"
            sub_text = "Embryo active • Routed along incubator conveyor"
        elif final_cls == "INFERTILE":
            badge_color = FUTheme.INFERTILE_AMBER
            title_text = f"INFERTILE — REJECT ({conf*100:.1f}%)"
            sub_text = "Penoy cull @ ₱14 • Servo diverter gate actuated"
        else:
            badge_color = FUTheme.ABNORMAL_RED
            title_text = f"ABNORMAL — REJECT ({conf*100:.1f}%)"
            sub_text = "Dead embryo / Corrupted yolk • Ejected to cull bin"

        self.result_badge.configure(text=action, fg_color=badge_color, text_color=FUTheme.TEXT_WHITE)
        self.latency_label.configure(text=f"Latency: {lat_ms}ms")
        self.result_title.configure(text=title_text)
        self.result_subtitle.configure(text=sub_text)

    def _update_counters_ui(self):
        pct = (self.fertile_count / max(1, self.total_count)) * 100.0
        batch_pct = min(100.0, (self.total_count / max(1, self.target_egg_count)) * 100.0)

        # Update Progress Bar & Percentage
        self.progress_bar.set(batch_pct / 100.0)
        self.progress_pct_label.configure(text=f"{batch_pct:.1f}% ({self.total_count} / {self.target_egg_count})")

        # Update Counter Tiles
        self.box_total.configure(text=f"{self.total_count} / {self.target_egg_count}")
        self.box_fertile.configure(text=f"{self.fertile_count} ({pct:.1f}%)")
        self.box_infertile.configure(text=str(self.infertile_count))
        self.box_abnormal.configure(text=str(self.abnormal_count))

    def _update_video_frame(self):
        """
        Live video render loop at ~30 FPS with dynamic AI bounding box & classification overlays.
        Only grabs and renders active camera frames when a session is in progress.
        """
        if self.camera.is_running:
            frame = self.camera.get_latest_frame()
            if frame is not None:
                h, w = frame.shape[:2]

                # Run live detection if not recently computed (every ~100ms)
                now = time.time()
                if now - self._last_live_infer_time > 0.10:
                    infer_res = self.engine.predict(frame)
                    self._latest_detections = infer_res.get("detections", [])
                    self._last_live_infer_time = now

                # 1. Draw Centering Aperture Guidelines
                cv2.circle(frame, (w // 2, h // 2), 5, (0, 255, 0), -1)
                cv2.ellipse(frame, (w // 2, h // 2), (180, 240), 0, 0, 360, (0, 200, 255), 1)

                # 2. Draw Live AI Bounding Boxes & Classification Labels
                for det in self._latest_detections:
                    bbox = det.get("bbox", [])
                    cls_name = det.get("class", "FERTILE")
                    conf = det.get("confidence", 0.90)

                    if len(bbox) == 4:
                        # Convert normalized [xc, yc, w, h] to pixel coordinates [x1, y1, x2, y2]
                        xc, yc, bw, bh = bbox
                        x1 = int((xc - bw / 2) * w)
                        y1 = int((yc - bh / 2) * h)
                        x2 = int((xc + bw / 2) * w)
                        y2 = int((yc + bh / 2) * h)

                        # Color Palette
                        if cls_name == "FERTILE":
                            box_bgr = (56, 122, 53)     # Agri-Green
                            label_str = f"FERTILE: {conf*100:.1f}%"
                        elif cls_name == "INFERTILE":
                            box_bgr = (6, 119, 217)     # Penoy Amber
                            label_str = f"INFERTILE (PENOY): {conf*100:.1f}%"
                        else:
                            box_bgr = (38, 38, 220)     # Reject Red
                            label_str = f"ABNORMAL: {conf*100:.1f}%"

                        # Draw Bounding Box Rectangle
                        cv2.rectangle(frame, (x1, y1), (x2, y2), box_bgr, 2)

                        # Draw Pill Label Header
                        (tw, th), _ = cv2.getTextSize(label_str, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
                        cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 10, y1), box_bgr, -1)
                        cv2.putText(frame, label_str, (x1 + 5, y1 - 4),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA)

                # 3. Letterbox scale and display inside CTk video container
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                container_w = max(100, self.video_container.winfo_width())
                container_h = max(100, self.video_container.winfo_height())

                frame_aspect = w / max(1, h)
                container_aspect = container_w / max(1, container_h)

                if container_aspect > frame_aspect:
                    target_h = container_h
                    target_w = int(target_h * frame_aspect)
                else:
                    target_w = container_w
                    target_h = int(target_w / frame_aspect)

                target_w = max(160, min(target_w, container_w))
                target_h = max(120, min(target_h, container_h))

                resized = cv2.resize(rgb_frame, (target_w, target_h), interpolation=cv2.INTER_LINEAR)
                pil_img = Image.fromarray(resized)
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(target_w, target_h))
                self.video_label.configure(image=ctk_img, text="")

        self.after(33, self._update_video_frame)

    def _update_status_loop(self):
        # Update FPS
        self.fps_label.configure(text=f"FPS: {self.camera.current_fps:.1f}")

        # Update Network Sync Status
        if self.sync_worker.is_online:
            self.net_status_badge.configure(text="SYNC: ONLINE", fg_color=FUTheme.FERTILE_GREEN)
        else:
            self.net_status_badge.configure(text="SYNC: OFFLINE", fg_color=FUTheme.PANEL_LIGHT_ALT)

        # Update ESP32 IoT Status
        if self.iot.is_connected:
            self.iot_status_badge.configure(text="ESP32: CONNECTED", fg_color=FUTheme.FERTILE_GREEN)
        else:
            self.iot_status_badge.configure(text="ESP32: STANDBY", fg_color=FUTheme.PANEL_LIGHT_ALT)

        self.after(1000, self._update_status_loop)

    def _log(self, message: str):
        """Append log line and maintain bounded history."""
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", f"{message}\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def open_batch_setup_dialog(self):
        """Robust Modal for Batch creation, selection, and candling stage setup."""
        if self.is_session_active:
            self._log("[WARN] Please stop the current active auto session before changing batch parameters.")

        dialog = ctk.CTkToplevel(self)
        dialog.title("Egg Batch & Candling Setup")
        dialog.geometry("480x560")
        dialog.configure(fg_color=FUTheme.BG_LIGHT)
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog, text="Egg Batch & Candling Setup",
            font=(FUTheme.FONT_FAMILY, 16, "bold"), text_color=FUTheme.TEXT_PRIMARY
        ).pack(pady=(18, 4))
        ctk.CTkLabel(
            dialog, text="Select duck breed, candling stage, and initial egg quantity",
            font=(FUTheme.FONT_FAMILY, 11), text_color=FUTheme.TEXT_MUTED
        ).pack(pady=(0, 16))

        content = ctk.CTkFrame(dialog, fg_color=FUTheme.PANEL_LIGHT, corner_radius=12, border_width=1, border_color=FUTheme.BORDER)
        content.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        # 1. Batch Code / Identifier
        batch_header = ctk.CTkFrame(content, fg_color="transparent")
        batch_header.pack(fill="x", padx=16, pady=(14, 2))
        ctk.CTkLabel(batch_header, text="Batch Code / Identifier:", font=(FUTheme.FONT_FAMILY, 11, "bold"), text_color=FUTheme.TEXT_PRIMARY).pack(side="left")

        batch_entry = ctk.CTkEntry(content, fg_color=FUTheme.PANEL_LIGHT_ALT, text_color=FUTheme.TEXT_PRIMARY, height=36)
        batch_entry.insert(0, self.current_batch_id)
        batch_entry.pack(fill="x", padx=16, pady=(0, 10))

        # 2. Duck Breed Selection
        ctk.CTkLabel(content, text="Duck Breed:", font=(FUTheme.FONT_FAMILY, 11, "bold"), text_color=FUTheme.TEXT_PRIMARY).pack(anchor="w", padx=16, pady=(4, 2))
        breed_opts = ["KAYUMANGGI (Itik Pinas)", "PEKIN (Cherry Valley)", "MUSCOVY (Pato)", "KHAKI_CAMPBELL (Layer)"]
        breed_dropdown = ctk.CTkOptionMenu(
            content, values=breed_opts, fg_color=FUTheme.PANEL_LIGHT_ALT, text_color=FUTheme.TEXT_PRIMARY,
            button_color=FUTheme.BORDER, button_hover_color=FUTheme.PRIMARY_MAROON, height=36
        )
        for b in breed_opts:
            if self.current_breed in b:
                breed_dropdown.set(b)
                break
        breed_dropdown.pack(fill="x", padx=16, pady=(0, 10))

        # 3. Candling Stage
        ctk.CTkLabel(content, text="Candling Stage:", font=(FUTheme.FONT_FAMILY, 11, "bold"), text_color=FUTheme.TEXT_PRIMARY).pack(anchor="w", padx=16, pady=(4, 2))
        stage_opts = ["DAY_7 (Initial Blood Ring Check)", "DAY_10 (Primary Penoy Salvage)", "DAY_14 (Mid Embryo Vitality)", "DAY_18 (Pre-Hatcher Transfer)"]
        stage_dropdown = ctk.CTkOptionMenu(
            content, values=stage_opts, fg_color=FUTheme.PANEL_LIGHT_ALT, text_color=FUTheme.TEXT_PRIMARY,
            button_color=FUTheme.BORDER, button_hover_color=FUTheme.PRIMARY_MAROON, height=36
        )
        for s in stage_opts:
            if self.current_stage in s:
                stage_dropdown.set(s)
                break
        stage_dropdown.pack(fill="x", padx=16, pady=(0, 10))

        # 4. Target Egg Quantity & Operator Row
        qty_row = ctk.CTkFrame(content, fg_color="transparent")
        qty_row.pack(fill="x", padx=16, pady=(4, 12))

        col1 = ctk.CTkFrame(qty_row, fg_color="transparent")
        col1.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkLabel(col1, text="Total Eggs in Batch:", font=(FUTheme.FONT_FAMILY, 11, "bold"), text_color=FUTheme.TEXT_PRIMARY).pack(anchor="w", pady=(0, 2))
        qty_entry = ctk.CTkEntry(col1, fg_color=FUTheme.PANEL_LIGHT_ALT, text_color=FUTheme.TEXT_PRIMARY, height=36)
        qty_entry.insert(0, str(self.target_egg_count))
        qty_entry.pack(fill="x")

        col2 = ctk.CTkFrame(qty_row, fg_color="transparent")
        col2.pack(side="right", fill="x", expand=True, padx=(6, 0))
        ctk.CTkLabel(col2, text="Operator Name:", font=(FUTheme.FONT_FAMILY, 11, "bold"), text_color=FUTheme.TEXT_PRIMARY).pack(anchor="w", pady=(0, 2))
        op_entry = ctk.CTkEntry(col2, fg_color=FUTheme.PANEL_LIGHT_ALT, text_color=FUTheme.TEXT_PRIMARY, height=36)
        op_entry.insert(0, self.operator_name)
        op_entry.pack(fill="x")

        def apply_batch():
            raw_batch = batch_entry.get().strip()
            raw_qty = qty_entry.get().strip()
            raw_op = op_entry.get().strip()
            raw_breed = breed_dropdown.get().split(" ")[0]
            raw_stage = stage_dropdown.get().split(" ")[0]

            if not raw_batch:
                return

            try:
                parsed_qty = max(1, int(raw_qty))
            except ValueError:
                parsed_qty = 500

            self.current_batch_id = raw_batch
            self.current_breed = raw_breed
            self.current_stage = raw_stage
            self.target_egg_count = parsed_qty
            self.operator_name = raw_op or "Operator"

            if not self.is_session_active:
                self.total_count = 0
                self.fertile_count = 0
                self.infertile_count = 0
                self.abnormal_count = 0

            self.batch_btn.configure(text=f"📋 Batch: {self.current_batch_id}  ({self.current_stage})  ▾")
            self._update_counters_ui()
            self._log(f"[BATCH] Configured: {self.current_batch_id} | Breed: {self.current_breed} | Stage: {self.current_stage} | Target: {self.target_egg_count} eggs")
            dialog.destroy()

        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(0, 16))

        ctk.CTkButton(
            btn_row, text="Cancel", fg_color="transparent", border_width=1, border_color=FUTheme.BORDER,
            text_color=FUTheme.TEXT_MUTED, hover_color=FUTheme.PANEL_LIGHT_ALT, command=dialog.destroy,
            width=100, height=38
        ).pack(side="left")

        ctk.CTkButton(
            btn_row, text="Save & Set Active Batch", fg_color=FUTheme.PRIMARY_MAROON,
            hover_color=FUTheme.HOVER_MAROON, text_color=FUTheme.TEXT_WHITE,
            font=(FUTheme.FONT_FAMILY, 12, "bold"), command=apply_batch, height=38
        ).pack(side="right", fill="x", expand=True, padx=(10, 0))

    def open_calibration_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Conveyor Calibration & Cycle Timing")
        dialog.geometry("450x440")
        dialog.configure(fg_color=FUTheme.BG_LIGHT)
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog, text="Conveyor & Sorting Cycle Calibration",
            font=(FUTheme.FONT_FAMILY, 15, "bold"), text_color=FUTheme.TEXT_PRIMARY
        ).pack(pady=(16, 10))

        # Speed
        ctk.CTkLabel(dialog, text="Conveyor Linear Speed (cm/s):", font=(FUTheme.FONT_FAMILY, 11), text_color=FUTheme.TEXT_MUTED).pack(anchor="w", padx=24)
        speed_entry = ctk.CTkEntry(dialog, fg_color=FUTheme.PANEL_LIGHT, text_color=FUTheme.TEXT_PRIMARY)
        speed_entry.insert(0, str(self.conveyor_speed_cm_s))
        speed_entry.pack(fill="x", padx=24, pady=(2, 8))

        # Chamber Pause
        ctk.CTkLabel(dialog, text="Chamber Candling Pause Duration (ms):", font=(FUTheme.FONT_FAMILY, 11), text_color=FUTheme.TEXT_MUTED).pack(anchor="w", padx=24)
        pause_entry = ctk.CTkEntry(dialog, fg_color=FUTheme.PANEL_LIGHT, text_color=FUTheme.TEXT_PRIMARY)
        pause_entry.insert(0, str(self.chamber_pause_ms))
        pause_entry.pack(fill="x", padx=24, pady=(2, 8))

        # Advance Duration
        ctk.CTkLabel(dialog, text="Egg Advance Transport Duration (ms):", font=(FUTheme.FONT_FAMILY, 11), text_color=FUTheme.TEXT_MUTED).pack(anchor="w", padx=24)
        adv_entry = ctk.CTkEntry(dialog, fg_color=FUTheme.PANEL_LIGHT, text_color=FUTheme.TEXT_PRIMARY)
        adv_entry.insert(0, str(self.conveyor_advance_ms))
        adv_entry.pack(fill="x", padx=24, pady=(2, 8))

        # Distance
        ctk.CTkLabel(dialog, text="Camera to Diverter Gate Distance (cm):", font=(FUTheme.FONT_FAMILY, 11), text_color=FUTheme.TEXT_MUTED).pack(anchor="w", padx=24)
        dist_entry = ctk.CTkEntry(dialog, fg_color=FUTheme.PANEL_LIGHT, text_color=FUTheme.TEXT_PRIMARY)
        dist_entry.insert(0, str(self.conveyor_dist_cm))
        dist_entry.pack(fill="x", padx=24, pady=(2, 14))

        def save():
            try:
                self.conveyor_speed_cm_s = float(speed_entry.get())
                self.chamber_pause_ms = int(pause_entry.get())
                self.conveyor_advance_ms = int(adv_entry.get())
                self.conveyor_dist_cm = float(dist_entry.get())
                self._log(f"[CONFIG] Updated: Speed={self.conveyor_speed_cm_s}cm/s, Pause={self.chamber_pause_ms}ms, Advance={self.conveyor_advance_ms}ms")
                dialog.destroy()
            except ValueError:
                pass

        ctk.CTkButton(
            dialog, text="Save Calibration", fg_color=FUTheme.PRIMARY_MAROON,
            hover_color=FUTheme.HOVER_MAROON, text_color=FUTheme.TEXT_WHITE, command=save
        ).pack(pady=10)
