"""
OvaLens Operator Desktop GUI (CustomTkinter 60 FPS)
Foundation University Automated Duck Egg Candling & Sorting Interface.
"""

import os
import time
import uuid
import threading
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

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

        # Conveyor Calibration Defaults
        self.conveyor_speed_cm_s = 12.50
        self.conveyor_dist_cm = 25.00
        self.servo_pulse_ms = 250

        # Session State
        self.current_session_id: Optional[str] = None
        self.current_batch_id: str = "BATCH-2026-08-KAY-01"
        self.current_stage: str = "DAY_10"
        self.operator_name: str = "Pedro Penduko"
        self.is_session_active: bool = False
        self.scan_sequence: int = 0

        # Live Counters
        self.total_count = 0
        self.fertile_count = 0
        self.infertile_count = 0
        self.abnormal_count = 0

        # Window Config
        self.title("OvaLens — Automated Duck Egg Candling & Sorting (Foundation University)")
        self.geometry("1280x800")
        self.minsize(1024, 700)
        ctk.set_appearance_mode("dark")

        self.configure(fg_color=FUTheme.BG_DARK)

        # Setup UI Components
        self._build_header()
        self._build_main_layout()
        self._build_footer()

        # Keyboard Shortcuts
        self.bind("<space>", lambda event: self.trigger_candling_scan())
        self.bind("r", lambda event: self.trigger_manual_eject())
        self.bind("R", lambda event: self.trigger_manual_eject())

        # Start Video Rendering Loop
        self._update_video_frame()
        self._update_status_loop()

    def _build_header(self):
        self.header_frame = ctk.CTkFrame(self, fg_color=FUTheme.PANEL_DARK, corner_radius=0, height=65)
        self.header_frame.pack(side="top", fill="x")

        # Left: University & Project Brand
        brand_container = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        brand_container.pack(side="left", padx=20, pady=10)

        badge = ctk.CTkLabel(brand_container, text=" FU ", fg_color=FUTheme.PRIMARY_MAROON,
                             text_color=FUTheme.TEXT_PRIMARY, font=(FUTheme.FONT_FAMILY, 14, "bold"),
                             corner_radius=4)
        badge.pack(side="left", padx=(0, 10))

        title = ctk.CTkLabel(brand_container, text="OvaLens Edge Operator",
                             font=(FUTheme.FONT_FAMILY, 18, "bold"), text_color=FUTheme.TEXT_PRIMARY)
        title.pack(side="left")

        # Center: Active Batch Info Badge
        self.batch_badge = ctk.CTkLabel(self.header_frame, text=f"Batch: {self.current_batch_id} ({self.current_stage})",
                                        fg_color=FUTheme.DARK_MAROON, text_color=FUTheme.TEXT_PRIMARY,
                                        font=(FUTheme.FONT_FAMILY, 13, "bold"), corner_radius=6, padx=14, pady=4)
        self.batch_badge.pack(side="left", padx=30)

        # Right: Network & Station Indicators
        right_container = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        right_container.pack(side="right", padx=20)

        self.fps_label = ctk.CTkLabel(right_container, text="FPS: 0.0", font=(FUTheme.FONT_FAMILY, 12), text_color=FUTheme.TEXT_MUTED)
        self.fps_label.pack(side="left", padx=10)

        self.iot_status_badge = ctk.CTkLabel(right_container, text="ESP32: MOCK", fg_color=FUTheme.PANEL_DARK_ALT,
                                            font=(FUTheme.FONT_FAMILY, 11, "bold"), corner_radius=4, padx=8, pady=2)
        self.iot_status_badge.pack(side="left", padx=6)

        self.net_status_badge = ctk.CTkLabel(right_container, text="SYNC: ONLINE", fg_color=FUTheme.FERTILE_GREEN,
                                            font=(FUTheme.FONT_FAMILY, 11, "bold"), corner_radius=4, padx=8, pady=2)
        self.net_status_badge.pack(side="left", padx=6)

    def _build_main_layout(self):
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=16, pady=12)

        # Left Column: Live Candling Feed HUD (60% width)
        self.left_panel = ctk.CTkFrame(self.main_container, fg_color=FUTheme.PANEL_DARK, corner_radius=10)
        self.left_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # Video HUD Canvas
        self.video_label = ctk.CTkLabel(self.left_panel, text="Initializing Camera Stream...",
                                       fg_color="#000000", corner_radius=8)
        self.video_label.pack(fill="both", expand=True, padx=12, pady=12)

        # Right Column: Controls & Live Analytics (40% width)
        self.right_panel = ctk.CTkFrame(self.main_container, fg_color="transparent", width=420)
        self.right_panel.pack(side="right", fill="both", padx=(0, 0))

        # 1. Last Classification Result Banner
        self.result_banner = ctk.CTkFrame(self.right_panel, fg_color=FUTheme.PANEL_DARK, corner_radius=10, height=110)
        self.result_banner.pack(fill="x", pady=(0, 10))
        self.result_banner.pack_propagate(False)

        self.result_title = ctk.CTkLabel(self.result_banner, text="STANDBY / READY",
                                         font=(FUTheme.FONT_FAMILY, 24, "bold"),
                                         text_color=FUTheme.TEXT_MUTED)
        self.result_title.pack(pady=(18, 4))

        self.result_subtitle = ctk.CTkLabel(self.result_banner, text="Press [SPACEBAR] or trip optical sensor to candle",
                                           font=(FUTheme.FONT_FAMILY, 12), text_color=FUTheme.TEXT_MUTED)
        self.result_subtitle.pack()

        # 2. Live Batch Counters Grid
        counters_frame = ctk.CTkFrame(self.right_panel, fg_color=FUTheme.PANEL_DARK, corner_radius=10)
        counters_frame.pack(fill="x", pady=(0, 10), padx=0)

        c_title = ctk.CTkLabel(counters_frame, text="LIVE SESSION STATISTICS", font=(FUTheme.FONT_FAMILY, 12, "bold"), text_color=FUTheme.TEXT_MUTED)
        c_title.pack(anchor="w", padx=16, pady=(12, 8))

        grid = ctk.CTkFrame(counters_frame, fg_color="transparent")
        grid.pack(fill="x", padx=12, pady=(0, 12))

        # Box 1: Total Scanned
        self.box_total = self._create_stat_box(grid, "TOTAL", "0", FUTheme.PANEL_DARK_ALT, 0, 0)
        # Box 2: Fertile
        self.box_fertile = self._create_stat_box(grid, "FERTILE (ACCEPT)", "0 (0%)", FUTheme.FERTILE_GREEN, 0, 1)
        # Box 3: Infertile
        self.box_infertile = self._create_stat_box(grid, "INFERTILE (PENOY)", "0", FUTheme.INFERTILE_AMBER, 1, 0)
        # Box 4: Abnormal
        self.box_abnormal = self._create_stat_box(grid, "ABNORMAL (DEAD)", "0", FUTheme.ABNORMAL_RED, 1, 1)

        # 3. Recent Scans Log
        log_frame = ctk.CTkFrame(self.right_panel, fg_color=FUTheme.PANEL_DARK, corner_radius=10)
        log_frame.pack(fill="both", expand=True, pady=(0, 0))

        log_title = ctk.CTkLabel(log_frame, text="RECENT CONVEYOR SCANS", font=(FUTheme.FONT_FAMILY, 12, "bold"), text_color=FUTheme.TEXT_MUTED)
        log_title.pack(anchor="w", padx=16, pady=(10, 4))

        self.log_textbox = ctk.CTkTextbox(log_frame, fg_color=FUTheme.BG_DARK, text_color=FUTheme.TEXT_PRIMARY,
                                          font=("Consolas", 11), activate_scrollbars=True)
        self.log_textbox.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.log_textbox.configure(state="disabled")

    def _create_stat_box(self, parent, label_text: str, val_text: str, bg_color: str, row: int, col: int):
        f = ctk.CTkFrame(parent, fg_color=bg_color, corner_radius=8)
        f.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")
        parent.grid_columnconfigure(col, weight=1)

        lbl = ctk.CTkLabel(f, text=label_text, font=(FUTheme.FONT_FAMILY, 10, "bold"), text_color=FUTheme.TEXT_PRIMARY)
        lbl.pack(anchor="w", padx=10, pady=(6, 0))

        val = ctk.CTkLabel(f, text=val_text, font=(FUTheme.FONT_FAMILY, 16, "bold"), text_color=FUTheme.TEXT_PRIMARY)
        val.pack(anchor="w", padx=10, pady=(0, 6))
        return val

    def _build_footer(self):
        self.footer_frame = ctk.CTkFrame(self, fg_color=FUTheme.PANEL_DARK, corner_radius=0, height=70)
        self.footer_frame.pack(side="bottom", fill="x")

        # Session Toggle Button
        self.session_btn = ctk.CTkButton(
            self.footer_frame, text="▶ START CANDLING SESSION", font=(FUTheme.FONT_FAMILY, 14, "bold"),
            fg_color=FUTheme.FERTILE_GREEN, hover_color=FUTheme.FERTILE_GREEN_HOVER,
            command=self.toggle_session, width=220, height=42
        )
        self.session_btn.pack(side="left", padx=20, pady=14)

        # Trigger Scan Button
        self.scan_btn = ctk.CTkButton(
            self.footer_frame, text="⚡ TRIGGER SCAN [SPACEBAR]", font=(FUTheme.FONT_FAMILY, 13, "bold"),
            fg_color=FUTheme.PRIMARY_MAROON, hover_color=FUTheme.HOVER_MAROON,
            command=self.trigger_candling_scan, width=230, height=42
        )
        self.scan_btn.pack(side="left", padx=10, pady=14)

        # Manual Eject Button
        self.eject_btn = ctk.CTkButton(
            self.footer_frame, text="⏏ MANUAL EJECT [R]", font=(FUTheme.FONT_FAMILY, 13, "bold"),
            fg_color=FUTheme.ABNORMAL_RED, hover_color=FUTheme.ABNORMAL_RED_HOVER,
            command=self.trigger_manual_eject, width=180, height=42
        )
        self.eject_btn.pack(side="left", padx=10, pady=14)

        # Conveyor Settings Button
        self.settings_btn = ctk.CTkButton(
            self.footer_frame, text="⚙ Conveyor Config", font=(FUTheme.FONT_FAMILY, 12),
            fg_color=FUTheme.PANEL_DARK_ALT, command=self.open_calibration_dialog, width=140, height=42
        )
        self.settings_btn.pack(side="right", padx=20, pady=14)

    def toggle_session(self):
        if not self.is_session_active:
            # Start Session
            self.current_session_id = str(uuid.uuid4())
            self.is_session_active = True
            self.scan_sequence = 0
            self.total_count = 0
            self.fertile_count = 0
            self.infertile_count = 0
            self.abnormal_count = 0

            # Record in SQLite
            self.db.create_session(
                session_id=self.current_session_id,
                batch_id=self.current_batch_id,
                device_id=self.device_id,
                stage=self.current_stage,
                operator_name=self.operator_name
            )

            # Sync session creation to backend
            self.sync_worker.register_session({
                "session_id": self.current_session_id,
                "batch_id": self.current_batch_id,
                "device_id": self.device_id,
                "stage": self.current_stage,
                "operator_name": self.operator_name,
                "started_at": datetime.now(timezone.utc).isoformat()
            })

            self.session_btn.configure(text="⏹ STOP SESSION", fg_color=FUTheme.ABNORMAL_RED, hover_color=FUTheme.ABNORMAL_RED_HOVER)
            self._log(f"[*] Session started: {self.current_session_id[:8]}... for {self.current_batch_id}")
        else:
            # End Session
            self.is_session_active = False
            self.session_btn.configure(text="▶ START CANDLING SESSION", fg_color=FUTheme.FERTILE_GREEN, hover_color=FUTheme.FERTILE_GREEN_HOVER)
            self._log(f"[OK] Session ended. Scanned {self.total_count} total eggs.")

    def trigger_candling_scan(self):
        """Perform instant snapshot inference and trigger conveyor actuator if rejected."""
        frame = self.camera.get_latest_frame()
        if frame is None:
            return

        if not self.is_session_active:
            self.toggle_session()

        self.scan_sequence += 1
        scan_id = str(uuid.uuid4())

        # Run AI Model Inference
        result = self.engine.predict(frame)
        final_cls = result["final_class"]
        conf = result["confidence"]
        action = result["routing_action"]
        lat_ms = result["inference_ms"]
        detections = result["detections"]

        # If rejected (INFERTILE or ABNORMAL), schedule ESP32 conveyor kicker
        if action == "REJECT":
            # Travel delay: Δt = (Distance / Speed) * 1000 ms
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
            color = FUTheme.FERTILE_GREEN
            text = f"FERTILE — ACCEPT ({conf*100:.1f}%)"
            sub = f"Embryo active • Latency: {lat_ms}ms • Routed to Incubator"
        elif final_cls == "INFERTILE":
            color = FUTheme.INFERTILE_AMBER
            text = f"INFERTILE — REJECT ({conf*100:.1f}%)"
            sub = f"Penoy cull • Latency: {lat_ms}ms • Diverter actuated"
        else:
            color = FUTheme.ABNORMAL_RED
            text = f"ABNORMAL — REJECT ({conf*100:.1f}%)"
            sub = f"Corrupted yolk / Dead embryo • Latency: {lat_ms}ms • Culled"

        self.result_banner.configure(fg_color=color)
        self.result_title.configure(text=text, text_color=FUTheme.TEXT_PRIMARY)
        self.result_subtitle.configure(text=sub, text_color=FUTheme.TEXT_PRIMARY)

    def _update_counters_ui(self):
        pct = (self.fertile_count / max(1, self.total_count)) * 100.0
        self.box_total.configure(text=str(self.total_count))
        self.box_fertile.configure(text=f"{self.fertile_count} ({pct:.1f}%)")
        self.box_infertile.configure(text=str(self.infertile_count))
        self.box_abnormal.configure(text=str(self.abnormal_count))

    def _update_video_frame(self):
        frame = self.camera.get_latest_frame()
        if frame is not None:
            # Draw candling center aperture guidelines
            h, w = frame.shape[:2]
            cv2.circle(frame, (w // 2, h // 2), 6, (0, 255, 0), -1)
            cv2.ellipse(frame, (w // 2, h // 2), (180, 240), 0, 0, 360, (0, 255, 255), 1)

            # Convert BGR to RGB PIL Image
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            target_w = self.video_label.winfo_width()
            target_h = self.video_label.winfo_height()

            if target_w > 10 and target_h > 10:
                resized = cv2.resize(rgb_frame, (target_w, target_h))
            else:
                resized = cv2.resize(rgb_frame, (640, 480))

            pil_img = Image.fromarray(resized)
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(pil_img.width, pil_img.height))
            self.video_label.configure(image=ctk_img, text="")

        # Refresh at 30 FPS (~33ms)
        self.after(33, self._update_video_frame)

    def _update_status_loop(self):
        # Update FPS
        self.fps_label.configure(text=f"FPS: {self.camera.current_fps:.1f}")

        # Update Network Status
        if self.sync_worker.is_online:
            self.net_status_badge.configure(text="SYNC: ONLINE", fg_color=FUTheme.FERTILE_GREEN)
        else:
            self.net_status_badge.configure(text="SYNC: OFFLINE", fg_color=FUTheme.PANEL_DARK_ALT)

        # Update IoT Status
        if self.iot.is_connected:
            self.iot_status_badge.configure(text="ESP32: CONNECTED", fg_color=FUTheme.FERTILE_GREEN)
        else:
            self.iot_status_badge.configure(text="ESP32: MOCK", fg_color=FUTheme.PANEL_DARK_ALT)

        self.after(1000, self._update_status_loop)

    def _log(self, message: str):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", f"{message}\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def open_calibration_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Conveyor Calibration & Hardware Settings")
        dialog.geometry("450x380")
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="Conveyor & Actuator Settings", font=(FUTheme.FONT_FAMILY, 16, "bold")).pack(pady=(16, 12))

        # Speed
        ctk.CTkLabel(dialog, text="Conveyor Belt Linear Speed (cm/s):").pack(anchor="w", padx=24)
        speed_entry = ctk.CTkEntry(dialog)
        speed_entry.insert(0, str(self.conveyor_speed_cm_s))
        speed_entry.pack(fill="x", padx=24, pady=(2, 10))

        # Distance
        ctk.CTkLabel(dialog, text="Camera to Diverter Gate Distance (cm):").pack(anchor="w", padx=24)
        dist_entry = ctk.CTkEntry(dialog)
        dist_entry.insert(0, str(self.conveyor_dist_cm))
        dist_entry.pack(fill="x", padx=24, pady=(2, 10))

        # Servo Pulse Duration
        ctk.CTkLabel(dialog, text="Servo Kicker Pulse Duration (ms):").pack(anchor="w", padx=24)
        pulse_entry = ctk.CTkEntry(dialog)
        pulse_entry.insert(0, str(self.servo_pulse_ms))
        pulse_entry.pack(fill="x", padx=24, pady=(2, 16))

        def save():
            try:
                self.conveyor_speed_cm_s = float(speed_entry.get())
                self.conveyor_dist_cm = float(dist_entry.get())
                self.servo_pulse_ms = int(pulse_entry.get())
                self._log(f"[CONFIG] Updated: Speed={self.conveyor_speed_cm_s}cm/s, Dist={self.conveyor_dist_cm}cm, Pulse={self.servo_pulse_ms}ms")
                dialog.destroy()
            except ValueError:
                pass

        ctk.CTkButton(dialog, text="Save Calibration", fg_color=FUTheme.PRIMARY_MAROON, command=save).pack(pady=10)
