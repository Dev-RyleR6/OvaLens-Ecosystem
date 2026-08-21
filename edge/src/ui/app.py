"""
OvaLens Operator Desktop GUI (CustomTkinter 60 FPS)
Foundation University Automated Duck Egg Candling & Sorting Interface (Light Institutional Theme).
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

        # Window Configuration (Light Institutional Theme)
        self.title("OvaLens — Automated Duck Egg Candling System (Foundation University)")
        self.geometry("1280x820")
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

        # Center: Active Batch Badge
        self.batch_badge = ctk.CTkLabel(
            self.header_frame, text=f"Batch: {self.current_batch_id} • Stage: {self.current_stage}",
            fg_color=FUTheme.PANEL_LIGHT_ALT, text_color=FUTheme.TEXT_PRIMARY,
            font=(FUTheme.FONT_FAMILY, 12, "bold"), corner_radius=6, padx=14, pady=5
        )
        self.batch_badge.pack(side="left", padx=20)

        # Right: Status Telemetry Badges
        right_container = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        right_container.pack(side="right", padx=18)

        self.fps_label = ctk.CTkLabel(
            right_container, text="FPS: --", font=(FUTheme.FONT_FAMILY, 11, "bold"), text_color=FUTheme.TEXT_MUTED
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

        # Left Column: Live Candling Viewport (Fixed container to prevent infinite expansion bug)
        self.left_panel = ctk.CTkFrame(
            self.main_container, fg_color=FUTheme.PANEL_LIGHT, corner_radius=12,
            border_width=1, border_color=FUTheme.BORDER
        )
        self.left_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # Inner container with disabled propagation to strictly contain the video
        self.video_container = ctk.CTkFrame(self.left_panel, fg_color="#000000", corner_radius=8)
        self.video_container.pack(fill="both", expand=True, padx=10, pady=10)
        self.video_container.pack_propagate(False)

        # Video HUD Canvas
        self.video_label = ctk.CTkLabel(
            self.video_container, text="Initializing Camera Stream...",
            fg_color="#000000", text_color="#FFFFFF"
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
            self.result_banner, text="Ready for Scan",
            font=(FUTheme.FONT_FAMILY, 18, "bold"), text_color=FUTheme.TEXT_PRIMARY
        )
        self.result_title.pack(anchor="w", padx=16, pady=(2, 1))

        self.result_subtitle = ctk.CTkLabel(
            self.result_banner, text="Press [SPACE] or trigger optical sensor on conveyor",
            font=(FUTheme.FONT_FAMILY, 11), text_color=FUTheme.TEXT_MUTED
        )
        self.result_subtitle.pack(anchor="w", padx=16)

        # 2. Live Batch Counters Grid
        counters_frame = ctk.CTkFrame(
            self.right_panel, fg_color=FUTheme.PANEL_LIGHT, corner_radius=12,
            border_width=1, border_color=FUTheme.BORDER
        )
        counters_frame.pack(fill="x", pady=(0, 10))

        c_header = ctk.CTkFrame(counters_frame, fg_color="transparent")
        c_header.pack(fill="x", padx=16, pady=(12, 6))

        c_title = ctk.CTkLabel(
            c_header, text="SESSION METRICS", font=(FUTheme.FONT_FAMILY, 11, "bold"),
            text_color=FUTheme.TEXT_MUTED
        )
        c_title.pack(side="left")

        grid = ctk.CTkFrame(counters_frame, fg_color="transparent")
        grid.pack(fill="x", padx=10, pady=(0, 12))

        # 4 Clean Stat Tiles
        self.box_total = self._create_stat_box(grid, "TOTAL SCANNED", "0", 0, 0, accent_color=FUTheme.TEXT_PRIMARY)
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

        val = ctk.CTkLabel(f, text=val_text, font=(FUTheme.FONT_FAMILY, 16, "bold"), text_color=FUTheme.TEXT_PRIMARY)
        val.pack(anchor="w", padx=10, pady=(0, 6))
        return val

    def _build_footer(self):
        self.footer_frame = ctk.CTkFrame(
            self, fg_color=FUTheme.PANEL_LIGHT, corner_radius=0, height=68,
            border_width=1, border_color=FUTheme.BORDER
        )
        self.footer_frame.pack(side="bottom", fill="x")

        # Session Toggle Button (Outline / Secondary)
        self.session_btn = ctk.CTkButton(
            self.footer_frame, text="▶ Start Session", font=(FUTheme.FONT_FAMILY, 13, "bold"),
            fg_color="transparent", border_width=1, border_color=FUTheme.FERTILE_GREEN,
            text_color=FUTheme.FERTILE_GREEN, hover_color=FUTheme.FERTILE_GREEN_BG,
            command=self.toggle_session, width=170, height=40, corner_radius=8
        )
        self.session_btn.pack(side="left", padx=(18, 8), pady=14)

        # Trigger Scan Button (Primary Action)
        self.scan_btn = ctk.CTkButton(
            self.footer_frame, text="⚡ Trigger Scan  [SPACE]", font=(FUTheme.FONT_FAMILY, 13, "bold"),
            fg_color=FUTheme.PRIMARY_MAROON, hover_color=FUTheme.HOVER_MAROON,
            text_color=FUTheme.TEXT_WHITE, command=self.trigger_candling_scan,
            width=220, height=40, corner_radius=8
        )
        self.scan_btn.pack(side="left", padx=8, pady=14)

        # Manual Eject Button
        self.eject_btn = ctk.CTkButton(
            self.footer_frame, text="⏏ Manual Eject  [R]", font=(FUTheme.FONT_FAMILY, 12, "bold"),
            fg_color=FUTheme.PANEL_LIGHT_ALT, hover_color=FUTheme.ABNORMAL_RED_BG,
            text_color=FUTheme.TEXT_PRIMARY, command=self.trigger_manual_eject,
            width=170, height=40, corner_radius=8
        )
        self.eject_btn.pack(side="left", padx=8, pady=14)

        # Conveyor Settings Button
        self.settings_btn = ctk.CTkButton(
            self.footer_frame, text="⚙ Conveyor Config", font=(FUTheme.FONT_FAMILY, 12),
            fg_color="transparent", border_width=1, border_color=FUTheme.BORDER,
            text_color=FUTheme.TEXT_MUTED, hover_color=FUTheme.PANEL_LIGHT_ALT,
            command=self.open_calibration_dialog, width=140, height=40, corner_radius=8
        )
        self.settings_btn.pack(side="right", padx=18, pady=14)

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

            # Record in SQLite WAL
            self.db.create_session(
                session_id=self.current_session_id,
                batch_id=self.current_batch_id,
                device_id=self.device_id,
                stage=self.current_stage,
                operator_name=self.operator_name
            )

            # Register session with background sync worker
            self.sync_worker.register_session({
                "session_id": self.current_session_id,
                "batch_id": self.current_batch_id,
                "device_id": self.device_id,
                "stage": self.current_stage,
                "operator_name": self.operator_name,
                "started_at": datetime.now(timezone.utc).isoformat()
            })

            self.session_btn.configure(
                text="⏹ End Session", border_color=FUTheme.ABNORMAL_RED,
                text_color=FUTheme.ABNORMAL_RED, hover_color=FUTheme.ABNORMAL_RED_BG
            )
            self._log(f"[*] Session active: {self.current_session_id[:8]}... (Batch: {self.current_batch_id})")
        else:
            # End Session
            self.is_session_active = False
            self.session_btn.configure(
                text="▶ Start Session", border_color=FUTheme.FERTILE_GREEN,
                text_color=FUTheme.FERTILE_GREEN, hover_color=FUTheme.FERTILE_GREEN_BG
            )
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
            sub_text = "Embryo development active • Routed to Incubator"
        elif final_cls == "INFERTILE":
            badge_color = FUTheme.INFERTILE_AMBER
            title_text = f"INFERTILE — REJECT ({conf*100:.1f}%)"
            sub_text = "Penoy salvage candidate @ ₱14 • Diverted"
        else:
            badge_color = FUTheme.ABNORMAL_RED
            title_text = f"ABNORMAL — REJECT ({conf*100:.1f}%)"
            sub_text = "Corrupted yolk / Dead embryo • Ejected"

        self.result_badge.configure(text=action, fg_color=badge_color, text_color=FUTheme.TEXT_WHITE)
        self.latency_label.configure(text=f"Latency: {lat_ms}ms")
        self.result_title.configure(text=title_text)
        self.result_subtitle.configure(text=sub_text)

    def _update_counters_ui(self):
        pct = (self.fertile_count / max(1, self.total_count)) * 100.0
        self.box_total.configure(text=str(self.total_count))
        self.box_fertile.configure(text=f"{self.fertile_count} ({pct:.1f}%)")
        self.box_infertile.configure(text=str(self.infertile_count))
        self.box_abnormal.configure(text=str(self.abnormal_count))

    def _update_video_frame(self):
        """
        Optimized video render loop at ~30 FPS with strictly clamped aspect-ratio scaling.
        Avoids the infinite geometry expansion loop by using fixed container dimensions.
        """
        frame = self.camera.get_latest_frame()
        if frame is not None:
            # Candling crosshairs & aperture guidelines
            h, w = frame.shape[:2]
            cv2.circle(frame, (w // 2, h // 2), 5, (0, 255, 0), -1)
            cv2.ellipse(frame, (w // 2, h // 2), (180, 240), 0, 0, 360, (0, 200, 255), 1)

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Strictly measure container without feedback loop
            container_w = max(100, self.video_container.winfo_width())
            container_h = max(100, self.video_container.winfo_height())

            # Maintain 16:9 or frame aspect ratio within the container box
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

    def open_calibration_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Conveyor Calibration")
        dialog.geometry("420x360")
        dialog.configure(fg_color=FUTheme.BG_LIGHT)
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog, text="Conveyor Actuation Calibration",
            font=(FUTheme.FONT_FAMILY, 15, "bold"), text_color=FUTheme.TEXT_PRIMARY
        ).pack(pady=(16, 12))

        # Speed
        ctk.CTkLabel(
            dialog, text="Conveyor Linear Speed (cm/s):",
            font=(FUTheme.FONT_FAMILY, 11), text_color=FUTheme.TEXT_MUTED
        ).pack(anchor="w", padx=24)
        speed_entry = ctk.CTkEntry(dialog, fg_color=FUTheme.PANEL_LIGHT, text_color=FUTheme.TEXT_PRIMARY)
        speed_entry.insert(0, str(self.conveyor_speed_cm_s))
        speed_entry.pack(fill="x", padx=24, pady=(2, 10))

        # Distance
        ctk.CTkLabel(
            dialog, text="Camera to Diverter Gate Distance (cm):",
            font=(FUTheme.FONT_FAMILY, 11), text_color=FUTheme.TEXT_MUTED
        ).pack(anchor="w", padx=24)
        dist_entry = ctk.CTkEntry(dialog, fg_color=FUTheme.PANEL_LIGHT, text_color=FUTheme.TEXT_PRIMARY)
        dist_entry.insert(0, str(self.conveyor_dist_cm))
        dist_entry.pack(fill="x", padx=24, pady=(2, 10))

        # Servo Pulse Duration
        ctk.CTkLabel(
            dialog, text="Servo Kicker Pulse Duration (ms):",
            font=(FUTheme.FONT_FAMILY, 11), text_color=FUTheme.TEXT_MUTED
        ).pack(anchor="w", padx=24)
        pulse_entry = ctk.CTkEntry(dialog, fg_color=FUTheme.PANEL_LIGHT, text_color=FUTheme.TEXT_PRIMARY)
        pulse_entry.insert(0, str(self.servo_pulse_ms))
        pulse_entry.pack(fill="x", padx=24, pady=(2, 16))

        def save():
            try:
                self.conveyor_speed_cm_s = float(speed_entry.get())
                self.conveyor_dist_cm = float(dist_entry.get())
                self.servo_pulse_ms = int(pulse_entry.get())
                self._log(f"[CONFIG] Calibration updated: Speed={self.conveyor_speed_cm_s}cm/s, Dist={self.conveyor_dist_cm}cm, Pulse={self.servo_pulse_ms}ms")
                dialog.destroy()
            except ValueError:
                pass

        ctk.CTkButton(
            dialog, text="Save Settings", fg_color=FUTheme.PRIMARY_MAROON,
            hover_color=FUTheme.HOVER_MAROON, text_color=FUTheme.TEXT_WHITE, command=save
        ).pack(pady=10)
