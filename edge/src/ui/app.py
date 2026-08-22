"""
OvaLens Operator Desktop GUI (CustomTkinter 60 FPS)
Foundation University Automated Duck Egg Candling & Conveyor Sorting System.
High-Contrast White Institutional Theme with Rich Accent Badges, Interactive Standby HUD, and Streamlined Controls.
"""

import os
import time
import uuid
import threading
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple

import cv2
import numpy as np
import tkinter as tk
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

        # Performance & Ergonomics State
        self.is_fullscreen = False
        self.show_crosshairs = True
        self._session_start_time: Optional[float] = None
        self._cached_container_w = 640
        self._cached_container_h = 480

        # Live Counters
        self.total_count = 0
        self.fertile_count = 0
        self.infertile_count = 0
        self.abnormal_count = 0

        # Window Configuration (Industrial Pro Gray Theme)
        self.title("OvaLens — Automated Duck Egg Candling System (Foundation University)")
        self.geometry("1280x860")
        self.minsize(1024, 720)
        ctk.set_appearance_mode("dark")
        self.configure(fg_color=FUTheme.BG_LIGHT)

        # Standard Window Exit Confirmation
        self.protocol("WM_DELETE_WINDOW", self.confirm_exit_dialog)

        # Setup UI Layout
        self._build_header()
        self._build_main_layout()
        self._build_footer()

        # Keyboard Accelerators & Operator Hotkeys
        self.bind("<space>", lambda event: self.trigger_candling_scan())
        self.bind("r", lambda event: self.trigger_manual_eject())
        self.bind("R", lambda event: self.trigger_manual_eject())
        self.bind("b", lambda event: self.open_batch_setup_dialog())
        self.bind("B", lambda event: self.open_batch_setup_dialog())
        self.bind("<F1>", lambda event: self.open_onboarding_guide())
        self.bind("h", lambda event: self.open_onboarding_guide())
        self.bind("H", lambda event: self.open_onboarding_guide())
        self.bind("<F11>", self.toggle_fullscreen)
        self.bind("c", self.toggle_crosshairs)
        self.bind("C", self.toggle_crosshairs)
        self.bind("s", lambda event: self.open_scan_history_modal())
        self.bind("S", lambda event: self.open_scan_history_modal())
        self.bind("<Escape>", lambda event: self.open_end_session_modal() if (self.is_session_active or self.camera.is_running) else None)

        # Start Standby Display & Status Loop
        self._render_standby_hud()
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
            corner_radius=6, padx=6, pady=2
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

        # Center: Interactive Active Batch Setup Button with High Contrast
        self.batch_btn = ctk.CTkButton(
            self.header_frame,
            text=f"📋 Batch: {self.current_batch_id}  ({self.current_stage})  ▾",
            font=(FUTheme.FONT_FAMILY, 12, "bold"),
            fg_color=FUTheme.PANEL_LIGHT_ALT,
            text_color=FUTheme.TEXT_PRIMARY,
            hover_color=FUTheme.PANEL_ACCENT,
            border_width=1,
            border_color=FUTheme.BORDER_DARK,
            command=self.open_batch_setup_dialog,
            height=36, corner_radius=8
        )
        self.batch_btn.pack(side="left", padx=(18, 8))

        # Quick Onboarding / Help Guide Button
        self.help_btn = ctk.CTkButton(
            self.header_frame,
            text="📘 Quick Guide [F1]",
            font=(FUTheme.FONT_FAMILY, 11, "bold"),
            fg_color=FUTheme.PANEL_LIGHT_ALT,
            text_color=FUTheme.TEXT_PRIMARY,
            hover_color=FUTheme.PANEL_ACCENT,
            border_width=1,
            border_color=FUTheme.BORDER,
            command=self.open_onboarding_guide,
            height=36, corner_radius=8
        )
        self.help_btn.pack(side="left", padx=4)

        # Fullscreen Kiosk Mode Button
        self.kiosk_btn = ctk.CTkButton(
            self.header_frame,
            text="⛶ Kiosk [F11]",
            font=(FUTheme.FONT_FAMILY, 11, "bold"),
            fg_color=FUTheme.PANEL_LIGHT_ALT,
            text_color=FUTheme.TEXT_SECONDARY,
            hover_color=FUTheme.PANEL_ACCENT,
            border_width=1,
            border_color=FUTheme.BORDER,
            command=self.toggle_fullscreen,
            height=36, corner_radius=8
        )
        self.kiosk_btn.pack(side="left", padx=4)

        # Right: Status Telemetry Badges
        right_container = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        right_container.pack(side="right", padx=18)

        self.fps_label = ctk.CTkLabel(
            right_container, text="FPS: 0.0", font=(FUTheme.FONT_FAMILY, 11, "bold"), text_color=FUTheme.TEXT_MUTED
        )
        self.fps_label.pack(side="left", padx=8)

        self.iot_status_badge = ctk.CTkLabel(
            right_container, text="ESP32: STANDBY", fg_color=FUTheme.PANEL_LIGHT_ALT,
            text_color=FUTheme.TEXT_SECONDARY, font=(FUTheme.FONT_FAMILY, 10, "bold"),
            corner_radius=4, padx=8, pady=3
        )
        self.iot_status_badge.pack(side="left", padx=4)

        self.net_status_badge = ctk.CTkLabel(
            right_container, text="SYNC: ONLINE", fg_color=FUTheme.FERTILE_GREEN_BG,
            text_color=FUTheme.FERTILE_GREEN_TEXT, font=(FUTheme.FONT_FAMILY, 10, "bold"),
            corner_radius=4, padx=8, pady=3
        )
        self.net_status_badge.pack(side="left", padx=4)

    def _center_window(self, dialog, width: int, height: int):
        """Center modal dialog relative to root window."""
        self.update_idletasks()
        rx = self.winfo_x()
        ry = self.winfo_y()
        rw = max(width, self.winfo_width())
        rh = max(height, self.winfo_height())
        x = rx + max(0, (rw - width) // 2)
        y = ry + max(0, (rh - height) // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")

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
            self.cycle_hud, text="CONVEYOR STANDBY — CLICK 'START AUTO SORTING' TO ACTIVATE",
            font=(FUTheme.FONT_FAMILY, 11, "bold"), text_color=FUTheme.TEXT_PRIMARY
        )
        self.cycle_status_label.pack(side="left")

        # Quick End Session Button on HUD Bar (dynamically revealed during active sessions)
        self.hud_cancel_btn = ctk.CTkButton(
            self.cycle_hud, text="⏹ End Session [ESC]", font=(FUTheme.FONT_FAMILY, 10, "bold"),
            fg_color="transparent", hover_color=FUTheme.ABNORMAL_RED_BG,
            text_color=FUTheme.TEXT_MUTED, border_width=1, border_color=FUTheme.BORDER,
            command=self.open_end_session_modal, height=26, width=135, corner_radius=6
        )
        # Note: Packed dynamically when session starts

        # Inner container with disabled propagation to lock video dimensions
        self.video_container = ctk.CTkFrame(self.left_panel, fg_color=FUTheme.DARKROOM_VIEWPORT, corner_radius=8)
        self.video_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.video_container.pack_propagate(False)

        def _on_video_resize(event):
            if event.width > 50 and event.height > 50:
                self._cached_container_w = event.width
                self._cached_container_h = event.height
        self.video_container.bind("<Configure>", _on_video_resize)

        # Video HUD Canvas (Native Tkinter Label for 60 FPS zero-overhead rendering)
        self.video_label = tk.Label(self.video_container, bg=FUTheme.DARKROOM_VIEWPORT, bd=0, highlightthickness=0)
        self.video_label.place(relx=0.5, rely=0.5, anchor="center")
        self._current_photo = None

        # Standby Overlay Container (rendered when camera is off)
        self.standby_frame = ctk.CTkFrame(self.video_container, fg_color="transparent")
        self.standby_frame.place(relx=0.5, rely=0.5, anchor="center")

        # Right Column: Controls & Live Analytics (Fixed width 440px)
        self.right_panel = ctk.CTkFrame(self.main_container, fg_color="transparent", width=440)
        self.right_panel.pack(side="right", fill="both", padx=(0, 0))
        self.right_panel.pack_propagate(False)

        # 1. Classification Result Banner (High Contrast Card)
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
            top_banner_row, text="Latency: -- ms", font=(FUTheme.FONT_FAMILY, 10, "bold"), text_color=FUTheme.TEXT_DIM
        )
        self.latency_label.pack(side="right")

        self.result_title = ctk.CTkLabel(
            self.result_banner, text="Ready for Auto Sorting",
            font=(FUTheme.FONT_FAMILY, 18, "bold"), text_color=FUTheme.TEXT_PRIMARY
        )
        self.result_title.pack(anchor="w", padx=16, pady=(2, 1))

        self.result_subtitle = ctk.CTkLabel(
            self.result_banner, text="Conveyor advances, pauses inside chamber, and auto-sorts",
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
            text_color=FUTheme.TEXT_PRIMARY
        )
        c_title.pack(side="left")

        self.progress_pct_label = ctk.CTkLabel(
            c_header, text="0.0% (0 / 500)", font=(FUTheme.FONT_FAMILY, 10, "bold"),
            text_color=FUTheme.TEXT_PRIMARY
        )
        self.progress_pct_label.pack(side="right")

        # Throughput Speedometer & Remaining ETA
        self.speed_eta_label = ctk.CTkLabel(
            c_header, text="⚡ Ready (Target: 500 eggs)", font=(FUTheme.FONT_FAMILY, 10, "bold"),
            text_color=FUTheme.TEXT_MUTED
        )
        self.speed_eta_label.pack(side="right", padx=(0, 12))

        # Progress Bar
        self.progress_bar = ctk.CTkProgressBar(
            counters_frame, height=7, corner_radius=4, fg_color=FUTheme.PANEL_LIGHT_ALT,
            progress_color=FUTheme.PRIMARY_MAROON
        )
        self.progress_bar.pack(fill="x", padx=16, pady=(0, 10))
        self.progress_bar.set(0.0)

        grid = ctk.CTkFrame(counters_frame, fg_color="transparent")
        grid.pack(fill="x", padx=10, pady=(0, 12))

        # 4 High-Contrast White Stat Tiles with Semantic Accent Card Fills
        self.box_total = self._create_stat_box(grid, "TOTAL SCANNED", f"0 / {self.target_egg_count}", 0, 0, accent_color=FUTheme.PRIMARY_MAROON, bg_color=FUTheme.PANEL_LIGHT_ALT)
        self.box_fertile = self._create_stat_box(grid, "FERTILE (ACCEPT)", "0 (0%)", 0, 1, accent_color=FUTheme.FERTILE_GREEN, bg_color=FUTheme.FERTILE_GREEN_CARD)
        self.box_infertile = self._create_stat_box(grid, "INFERTILE (PENOY)", "0", 1, 0, accent_color=FUTheme.INFERTILE_AMBER, bg_color=FUTheme.INFERTILE_AMBER_CARD)
        self.box_abnormal = self._create_stat_box(grid, "ABNORMAL (REJECT)", "0", 1, 1, accent_color=FUTheme.ABNORMAL_RED, bg_color=FUTheme.ABNORMAL_RED_CARD)

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
            text_color=FUTheme.TEXT_PRIMARY
        )
        log_title.pack(side="left")

        self.history_btn = ctk.CTkButton(
            log_header, text="🔍 Explorer [S]", font=(FUTheme.FONT_FAMILY, 10, "bold"),
            fg_color=FUTheme.PANEL_LIGHT_ALT, hover_color=FUTheme.PANEL_ACCENT,
            border_width=1, border_color=FUTheme.BORDER,
            text_color=FUTheme.TEXT_SECONDARY, command=self.open_scan_history_modal,
            height=24, width=110, corner_radius=6
        )
        self.history_btn.pack(side="right")

        # Compact Live Scans List Box
        self.log_textbox = ctk.CTkTextbox(
            log_frame, fg_color=FUTheme.PANEL_LIGHT_ALT, font=("Consolas", 10),
            text_color=FUTheme.TEXT_SECONDARY, corner_radius=8,
            border_width=1, border_color=FUTheme.BORDER
        )
        self.log_textbox.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.log_textbox.configure(state="disabled")

    def _render_standby_hud(self):
        """Build centered Standby Card in video viewport when camera is idle."""
        for child in self.standby_frame.winfo_children():
            child.destroy()

        card = ctk.CTkFrame(
            self.standby_frame, fg_color=FUTheme.PANEL_LIGHT, corner_radius=16,
            border_width=1, border_color=FUTheme.BORDER
        )
        card.pack(padx=24, pady=24)

        icon = ctk.CTkLabel(
            card, text="🥚", font=(FUTheme.FONT_FAMILY, 40)
        )
        icon.pack(pady=(20, 2))

        title = ctk.CTkLabel(
            card, text="CAMERA & AI VISION ON STANDBY",
            font=(FUTheme.FONT_FAMILY, 15, "bold"), text_color="#F8FAFC"
        )
        title.pack(pady=(0, 4))

        sub = ctk.CTkLabel(
            card,
            text=f"Batch: {self.current_batch_id}  •  Breed: {self.current_breed}  •  Stage: {self.current_stage}\nTarget: {self.target_egg_count} Eggs  •  Conveyor: Ready",
            font=(FUTheme.FONT_FAMILY, 11), text_color="#94A3B8", justify="center"
        )
        sub.pack(pady=(0, 14), padx=20)

        hint_box = ctk.CTkFrame(card, fg_color="#0F172A", corner_radius=8)
        hint_box.pack(padx=16, pady=(0, 16))

        hint = ctk.CTkLabel(
            hint_box,
            text="⚡ [SPACE] Single Candling Scan  •  [START AUTO SORTING] Continuous Conveyor  •  [ESC] Standby / Cancel",
            font=(FUTheme.FONT_FAMILY, 10, "bold"), text_color=FUTheme.TEXT_WHITE, padx=14, pady=6, justify="center"
        )
        hint.pack()

    def _create_stat_box(self, parent, label_text: str, val_text: str, row: int, col: int, accent_color: str, bg_color: str = None):
        card_bg = bg_color or FUTheme.PANEL_LIGHT_ALT
        f = ctk.CTkFrame(parent, fg_color=card_bg, corner_radius=10, border_width=1, border_color=FUTheme.BORDER)
        f.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")
        parent.grid_columnconfigure(col, weight=1)

        top_strip = ctk.CTkFrame(f, fg_color=accent_color, height=4, corner_radius=2)
        top_strip.pack(fill="x", side="top")

        lbl = ctk.CTkLabel(f, text=label_text, font=(FUTheme.FONT_FAMILY, 9, "bold"), text_color=FUTheme.TEXT_MUTED)
        lbl.pack(anchor="w", padx=10, pady=(6, 0))

        val = ctk.CTkLabel(f, text=val_text, font=(FUTheme.FONT_FAMILY, 16, "bold"), text_color=accent_color if accent_color != FUTheme.PRIMARY_MAROON else FUTheme.TEXT_PRIMARY)
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
            fg_color=FUTheme.PRIMARY_MAROON, hover_color=FUTheme.HOVER_MAROON,
            text_color=FUTheme.TEXT_WHITE, command=self.toggle_auto_session,
            width=190, height=42, corner_radius=8
        )
        self.session_btn.pack(side="left", padx=(14, 6), pady=13)

        # Single Trigger Scan Button (Manual Override)
        self.scan_btn = ctk.CTkButton(
            self.footer_frame, text="⚡ Single Scan [SPACE]", font=(FUTheme.FONT_FAMILY, 12, "bold"),
            fg_color=FUTheme.PANEL_LIGHT_ALT, hover_color=FUTheme.PANEL_ACCENT,
            border_width=1, border_color=FUTheme.BORDER_DARK,
            text_color=FUTheme.TEXT_PRIMARY, command=self.trigger_candling_scan,
            width=160, height=42, corner_radius=8
        )
        self.scan_btn.pack(side="left", padx=6, pady=13)

        # Dedicated Terminate / Cancel / End Session Button (hidden in Standby, visible when active)
        self.cancel_btn = ctk.CTkButton(
            self.footer_frame, text="⏹ End Session [ESC]", font=(FUTheme.FONT_FAMILY, 12, "bold"),
            fg_color=FUTheme.PANEL_LIGHT_ALT, hover_color=FUTheme.ABNORMAL_RED_BG,
            border_width=1, border_color=FUTheme.BORDER_DARK,
            text_color=FUTheme.TEXT_PRIMARY, command=self.open_end_session_modal,
            width=165, height=42, corner_radius=8
        )
        # Note: Packed dynamically when a session/camera is started

        # Manual Eject Button with High-Contrast Luminous Text
        self.eject_btn = ctk.CTkButton(
            self.footer_frame, text="⏏ Manual Eject [R]", font=(FUTheme.FONT_FAMILY, 12, "bold"),
            fg_color=FUTheme.ABNORMAL_RED_BG, hover_color=FUTheme.ABNORMAL_RED_HOVER,
            border_width=1, border_color=FUTheme.ABNORMAL_RED_BORDER,
            text_color=FUTheme.ABNORMAL_RED_TEXT, command=self.trigger_manual_eject,
            width=145, height=42, corner_radius=8
        )
        self.eject_btn.pack(side="left", padx=6, pady=13)

        # Batch Setup Quick Button
        self.batch_setup_btn = ctk.CTkButton(
            self.footer_frame, text="📋 Batch Setup", font=(FUTheme.FONT_FAMILY, 12, "bold"),
            fg_color=FUTheme.PANEL_LIGHT_ALT, hover_color=FUTheme.PANEL_ACCENT,
            border_width=1, border_color=FUTheme.BORDER_DARK,
            text_color=FUTheme.TEXT_PRIMARY, command=self.open_batch_setup_dialog,
            width=130, height=42, corner_radius=8
        )
        self.batch_setup_btn.pack(side="right", padx=(6, 14), pady=13)

        # Conveyor Settings Button
        self.settings_btn = ctk.CTkButton(
            self.footer_frame, text="⚙ Config", font=(FUTheme.FONT_FAMILY, 12),
            fg_color=FUTheme.PANEL_LIGHT_ALT, border_width=1, border_color=FUTheme.BORDER,
            text_color=FUTheme.TEXT_SECONDARY, hover_color=FUTheme.PANEL_ACCENT,
            command=self.open_calibration_dialog, width=100, height=42, corner_radius=8
        )
        self.settings_btn.pack(side="right", padx=6, pady=13)

    def _set_session_active_state(self, is_active: bool):
        """Dynamically show/hide cancel controls and toggle main session button appearance."""
        if is_active:
            # Reveal cancel buttons dynamically when active
            self.cancel_btn.pack(side="left", padx=6, pady=13, after=self.scan_btn)
            self.hud_cancel_btn.pack(side="right", padx=(0, 8), pady=5)
            if self.is_auto_cycle_running:
                self.session_btn.configure(
                    text="⏹ STOP AUTO SORTING", fg_color=FUTheme.ABNORMAL_RED,
                    hover_color=FUTheme.ABNORMAL_RED_HOVER
                )
        else:
            # Hide cancel buttons when in standby
            self.cancel_btn.pack_forget()
            self.hud_cancel_btn.pack_forget()
            self.session_btn.configure(
                text="▶ START AUTO SORTING", fg_color=FUTheme.PRIMARY_MAROON,
                hover_color=FUTheme.HOVER_MAROON
            )

    def open_end_session_modal(self, event=None):
        """Interactive End Session modal with run summary statistics and direct CSV export."""
        # If no scans recorded and camera is idle, instantly stop without prompt
        if self.total_count == 0 and not self.is_auto_cycle_running and not self.camera.is_running:
            self.stop_or_cancel_session()
            return

        # If automated conveyor is currently moving, pause conveyor motor while modal is open
        was_auto_running = self.is_auto_cycle_running
        if was_auto_running:
            self.iot.set_conveyor(False)

        dialog = ctk.CTkToplevel(self)
        dialog.title(f"End Candling Session — {self.current_batch_id}")
        dialog.geometry("560x630")
        dialog.configure(fg_color=FUTheme.BG_LIGHT)
        dialog.transient(self)
        dialog.grab_set()
        self._center_window(dialog, 560, 630)

        card = ctk.CTkFrame(dialog, fg_color=FUTheme.PANEL_LIGHT, corner_radius=12, border_width=1, border_color=FUTheme.BORDER)
        card.pack(fill="both", expand=True, padx=16, pady=16)

        # Header with Alert / Session Icon
        icon_row = ctk.CTkFrame(card, fg_color="transparent")
        icon_row.pack(fill="x", padx=16, pady=(16, 2))

        ctk.CTkLabel(
            icon_row, text="⏹ End Active Candling Session?",
            font=(FUTheme.FONT_FAMILY, 17, "bold"), text_color=FUTheme.TEXT_PRIMARY
        ).pack(side="left")

        ctk.CTkLabel(
            card,
            text=f"Batch: {self.current_batch_id}  •  Breed: {self.current_breed}  •  Stage: {self.current_stage}\nOperator: {self.operator_name}  •  Device: {self.device_id}",
            font=(FUTheme.FONT_FAMILY, 11), text_color=FUTheme.TEXT_MUTED, justify="left"
        ).pack(anchor="w", padx=16, pady=(2, 12))

        # Metrics Summary Grid
        grid = ctk.CTkFrame(card, fg_color="transparent")
        grid.pack(fill="x", padx=16, pady=(0, 12))
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        pct = (self.fertile_count / max(1, self.total_count)) * 100.0 if self.total_count > 0 else 0.0
        penoy_salvage_val = self.infertile_count * 14.00

        # Tile 1: Total Processed
        t1 = ctk.CTkFrame(grid, fg_color=FUTheme.PANEL_LIGHT_ALT, corner_radius=8, border_width=1, border_color=FUTheme.BORDER)
        t1.grid(row=0, column=0, padx=4, pady=4, sticky="nsew")
        ctk.CTkLabel(t1, text="TOTAL SCANNED", font=(FUTheme.FONT_FAMILY, 9, "bold"), text_color=FUTheme.TEXT_MUTED).pack(anchor="w", padx=10, pady=(6, 0))
        ctk.CTkLabel(t1, text=f"{self.total_count} / {self.target_egg_count} Eggs", font=(FUTheme.FONT_FAMILY, 15, "bold"), text_color=FUTheme.TEXT_PRIMARY).pack(anchor="w", padx=10, pady=(0, 6))

        # Tile 2: Fertile Embryos
        t2 = ctk.CTkFrame(grid, fg_color=FUTheme.FERTILE_GREEN_CARD, corner_radius=8, border_width=1, border_color=FUTheme.FERTILE_GREEN_BORDER)
        t2.grid(row=0, column=1, padx=4, pady=4, sticky="nsew")
        ctk.CTkLabel(t2, text="FERTILE (ACCEPT)", font=(FUTheme.FONT_FAMILY, 9, "bold"), text_color=FUTheme.FERTILE_GREEN_TEXT).pack(anchor="w", padx=10, pady=(6, 0))
        ctk.CTkLabel(t2, text=f"{self.fertile_count} ({pct:.1f}%)", font=(FUTheme.FONT_FAMILY, 15, "bold"), text_color=FUTheme.FERTILE_GREEN_TEXT).pack(anchor="w", padx=10, pady=(0, 6))

        # Tile 3: Penoy Salvage
        t3 = ctk.CTkFrame(grid, fg_color=FUTheme.INFERTILE_AMBER_CARD, corner_radius=8, border_width=1, border_color=FUTheme.INFERTILE_AMBER_BORDER)
        t3.grid(row=1, column=0, padx=4, pady=4, sticky="nsew")
        ctk.CTkLabel(t3, text="PENOY SALVAGE YIELD", font=(FUTheme.FONT_FAMILY, 9, "bold"), text_color=FUTheme.INFERTILE_AMBER_TEXT).pack(anchor="w", padx=10, pady=(6, 0))
        ctk.CTkLabel(t3, text=f"{self.infertile_count} eggs -> ₱{penoy_salvage_val:,.2f}", font=(FUTheme.FONT_FAMILY, 14, "bold"), text_color=FUTheme.INFERTILE_AMBER).pack(anchor="w", padx=10, pady=(0, 6))

        # Tile 4: Abnormal Culls
        t4 = ctk.CTkFrame(grid, fg_color=FUTheme.ABNORMAL_RED_CARD, corner_radius=8, border_width=1, border_color=FUTheme.ABNORMAL_RED_BORDER)
        t4.grid(row=1, column=1, padx=4, pady=4, sticky="nsew")
        ctk.CTkLabel(t4, text="ABNORMAL (REJECT)", font=(FUTheme.FONT_FAMILY, 9, "bold"), text_color=FUTheme.ABNORMAL_RED_TEXT).pack(anchor="w", padx=10, pady=(6, 0))
        ctk.CTkLabel(t4, text=f"{self.abnormal_count} Eggs", font=(FUTheme.FONT_FAMILY, 15, "bold"), text_color=FUTheme.ABNORMAL_RED).pack(anchor="w", padx=10, pady=(0, 6))

        # Direct CSV Export Section Box
        export_box = ctk.CTkFrame(card, fg_color=FUTheme.PANEL_LIGHT_ALT, corner_radius=10, border_width=1, border_color=FUTheme.BORDER)
        export_box.pack(fill="x", padx=16, pady=(0, 14))

        ctk.CTkLabel(
            export_box, text="💾 EXPORT SESSION RECORDS DIRECTLY TO CSV",
            font=(FUTheme.FONT_FAMILY, 10, "bold"), text_color=FUTheme.TEXT_PRIMARY
        ).pack(anchor="w", padx=14, pady=(10, 4))

        status_msg = ctk.CTkLabel(
            export_box, text="Save session log containing classification results, timestamps, and confidence scores.",
            font=(FUTheme.FONT_FAMILY, 10), text_color=FUTheme.TEXT_MUTED, justify="left"
        )
        status_msg.pack(anchor="w", padx=14, pady=(0, 8))

        def export_csv():
            try:
                path = self.db.export_session_csv(self.current_session_id)
                status_msg.configure(text=f"✓ Exported successfully: {os.path.basename(path)}", text_color=FUTheme.FERTILE_GREEN_TEXT)
                self._log(f"[EXPORT] CSV Report saved: {path}")
            except Exception as e:
                status_msg.configure(text=f"Export failed: {e}", text_color=FUTheme.ABNORMAL_RED_TEXT)

        ctk.CTkButton(
            export_box, text="📄 Export Records directly into CSV", fg_color=FUTheme.PRIMARY_MAROON,
            hover_color=FUTheme.HOVER_MAROON, text_color=FUTheme.TEXT_WHITE, font=(FUTheme.FONT_FAMILY, 12, "bold"),
            command=export_csv, height=36, corner_radius=8
        ).pack(fill="x", padx=14, pady=(0, 10))

        # Bottom Actions Row
        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 10))

        def confirm_end():
            dialog.destroy()
            self.stop_or_cancel_session()
            self._log(f"[OK] Session ended with {self.total_count} records saved.")

        def resume():
            dialog.destroy()
            if was_auto_running and self.is_auto_cycle_running:
                self.iot.set_conveyor(True)
                self._log("[INFO] Session resumed.")

        ctk.CTkButton(
            btn_row, text="⏹ Confirm & End Session", fg_color=FUTheme.ABNORMAL_RED_BG,
            hover_color=FUTheme.ABNORMAL_RED_HOVER, border_width=1, border_color=FUTheme.ABNORMAL_RED_BORDER,
            text_color=FUTheme.ABNORMAL_RED_TEXT, font=(FUTheme.FONT_FAMILY, 12, "bold"),
            command=confirm_end, height=40, corner_radius=8
        ).pack(side="left", fill="x", expand=True, padx=(0, 8))

        ctk.CTkButton(
            btn_row, text="↩ Resume Session", fg_color=FUTheme.PANEL_LIGHT_ALT,
            hover_color=FUTheme.PANEL_ACCENT, border_width=1, border_color=FUTheme.BORDER,
            text_color=FUTheme.TEXT_PRIMARY, font=(FUTheme.FONT_FAMILY, 12),
            command=resume, height=40, corner_radius=8, width=140
        ).pack(side="right")

    def stop_or_cancel_session(self):
        """
        Universal, Conflict-Free End Session Protocol:
        1. Signals auto-cycle loop cancellation event.
        2. Commands ESP32 hardware conveyor motor to stop immediately.
        3. Cleanly joins background cycle worker thread with timeout to avoid race conditions.
        4. Finalizes the local SQLite session (records ended_at & commits passive WAL checkpoint).
        5. Flushes pending synchronization payloads.
        6. Safely stops the OpenCV frame grabber hardware handle.
        7. Clears viewport and displays Standby HUD card.
        8. Restores UI controls and hides active session buttons.
        """
        # 1. Cancel running cycle thread & halt hardware motor
        if self.is_auto_cycle_running or self._stop_cycle_event.is_set():
            self._stop_cycle_event.set()
            self.iot.set_conveyor(False)
            if hasattr(self, "_auto_cycle_thread") and self._auto_cycle_thread and self._auto_cycle_thread.is_alive():
                try:
                    self._auto_cycle_thread.join(timeout=0.6)
                except Exception:
                    pass
            self.is_auto_cycle_running = False

        # 2. Finalize Session in Database
        if self.current_session_id:
            try:
                self.db.complete_session(self.current_session_id)
            except Exception as e:
                self._log(f"[DB] Session completion warning: {e}")

        # 3. Stop Camera Grabber
        if self.camera.is_running:
            self.camera.stop()

        # 4. Reset internal session flags
        self.is_session_active = False
        self._session_start_time = None

        # 5. Restore Viewport & HUD
        self.video_label.configure(image=None)
        self._render_standby_hud()
        self.standby_frame.place(relx=0.5, rely=0.5, anchor="center")
        self._update_cycle_hud("●", FUTheme.TEXT_MUTED, "CONVEYOR STANDBY — SESSION IDLE")
        self._set_session_active_state(False)
        self._log("[ACTION] End session protocol completed. System returned to Standby.")

    def _stop_auto_cycle(self):
        """Helper to cleanly stop automated cycle loop."""
        self.stop_or_cancel_session()

    def toggle_auto_session(self):
        """Toggle automated full conveyor sorting cycle with on-demand camera start."""
        if not self.is_session_active:
            # 1. Start Camera Stream On-Demand
            if not self.camera.is_running:
                self.camera.start()

            # Hide Standby Overlay Frame
            self.standby_frame.place_forget()

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

            # Record session start time for live throughput computation
            self._session_start_time = time.time()

            # Update UI state & reveal cancel button
            self._set_session_active_state(True)
            self._update_counters_ui()
            self._log(f"[*] AUTO SESSION STARTED: {self.current_session_id[:8]}... (Batch: {self.current_batch_id}, Target: {self.target_egg_count} eggs)")

            # Launch Automated Conveyor Cycle Worker Thread
            self._stop_cycle_event.clear()
            self._auto_cycle_thread = threading.Thread(target=self._auto_conveyor_cycle_loop, daemon=True, name="OvaLens-ConveyorCycle")
            self._auto_cycle_thread.start()
        else:
            # Stop Session & Release Camera
            self.stop_or_cancel_session()

        self._log(f"[OK] Auto sorting ended. Completed {self.total_count}/{self.target_egg_count} eggs.")

    def _auto_conveyor_cycle_loop(self):
        """
        Industrial Automated Conveyor State Machine:
        1. Motor Advances Conveyor
        2. Egg enters dark candling chamber (Conveyor Pauses for blur-free optical capture)
        3. AI Vision inference executes in worker thread (Zero UI lag)
        4. Servo diverter actuates if rejected; lets egg pass to incubator lane if fertile
        5. Automatically repeats until target batch count is satisfied
        """
        while self.is_auto_cycle_running and not self._stop_cycle_event.is_set():
            if self.total_count >= self.target_egg_count:
                self.after(0, self._on_batch_target_complete)
                break

            # PHASE 1: Motor Advance (Transport egg to candling aperture)
            self.after(0, lambda: self._update_cycle_hud("🟢", FUTheme.FERTILE_GREEN, f"CONVEYOR ADVANCING EGG #{self.total_count + 1} (120 EGGS/MIN)...", bg_color=FUTheme.FERTILE_GREEN_CARD))
            self.iot.set_conveyor(True)
            time.sleep(self.conveyor_advance_ms / 1000.0)

            if self._stop_cycle_event.is_set():
                break

            # PHASE 2: Chamber Entry & Stabilization Pause
            self.after(0, lambda: self._update_cycle_hud("🟡", FUTheme.INFERTILE_AMBER, f"EGG #{self.total_count + 1} IN CHAMBER — OPTICAL CANDLING", bg_color=FUTheme.INFERTILE_AMBER_CARD))
            self.iot.set_conveyor(False)
            time.sleep(self.chamber_pause_ms / 1000.0)

            if self._stop_cycle_event.is_set():
                break

            # PHASE 3: AI Candling Scan & Actuation in Background Thread
            self.after(0, lambda: self._update_cycle_hud("🔵", FUTheme.PRIMARY_MAROON, f"AI INFERENCE — SCANNING EGG #{self.total_count + 1}...", bg_color=FUTheme.PRIMARY_MAROON_BG))
            
            frame = self.camera.get_latest_frame(copy=True)
            if frame is not None:
                # Run neural net prediction asynchronously in this background thread
                result = self.engine.predict(frame)
                self.after(0, lambda res=result: self._process_scan_result(res))
            else:
                self.after(0, self.trigger_candling_scan)

            # Settle time between cycles
            time.sleep(0.35)

    def _on_batch_target_complete(self):
        self._stop_auto_cycle()
        self._update_cycle_hud("🏁", FUTheme.PRIMARY_MAROON, f"BATCH COMPLETE: ALL {self.target_egg_count} EGGS SORTED!", bg_color=FUTheme.PRIMARY_MAROON_BG)
        self._log(f"[COMPLETE] Batch {self.current_batch_id} fully scanned ({self.target_egg_count}/{self.target_egg_count} eggs).")
        self._play_completion_chime()
        self.open_batch_completion_modal()

    def _update_cycle_hud(self, dot_icon: str, dot_color: str, status_text: str, bg_color: str = None):
        hud_bg = bg_color or FUTheme.PANEL_LIGHT_ALT
        self.cycle_hud.configure(fg_color=hud_bg)
        self.cycle_status_dot.configure(text=dot_icon, text_color=dot_color)
        self.cycle_status_label.configure(text=status_text, text_color=dot_color if dot_color != FUTheme.TEXT_MUTED else FUTheme.TEXT_PRIMARY)

    def _process_scan_result(self, result: Dict[str, Any]):
        """Commit scan result to database, schedule physical actuator, and update telemetry on UI."""
        if not self.is_session_active:
            self.current_session_id = self.current_session_id or str(uuid.uuid4())
            self.is_session_active = True
            self._session_start_time = time.time()
            self.db.create_session(
                session_id=self.current_session_id,
                batch_id=self.current_batch_id,
                device_id=self.device_id,
                stage=self.current_stage,
                operator_name=self.operator_name
            )

        self.scan_sequence += 1
        scan_id = str(uuid.uuid4())

        final_cls = result["final_class"]
        conf = result["confidence"]
        action = result["routing_action"]
        lat_ms = result["inference_ms"]
        detections = result.get("detections", [])

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

    def trigger_candling_scan(self):
        """Perform instant snapshot inference on-demand (Manual Test Scan)."""
        if not self.camera.is_running:
            self.camera.start()
            self.standby_frame.place_forget()
            self._set_session_active_state(True)
            time.sleep(0.05)

        frame = self.camera.get_latest_frame(copy=True)
        if frame is None:
            return

        result = self.engine.predict(frame)
        self._process_scan_result(result)

    def trigger_manual_eject(self):
        """Fire servo kicker immediately with visual confirmation on UI."""
        self.iot.trigger_ejection_now()
        self.result_banner.configure(fg_color=FUTheme.ABNORMAL_RED_CARD, border_color=FUTheme.ABNORMAL_RED_BORDER)
        self.result_badge.configure(text="MANUAL EJECT", fg_color=FUTheme.ABNORMAL_RED_BG, text_color=FUTheme.ABNORMAL_RED_TEXT)
        self.result_title.configure(text="⏏ Manual Ejection Triggered", text_color=FUTheme.ABNORMAL_RED)
        self.result_subtitle.configure(text="Hardware servo diverter gate pulsed via ESP32 GPIO override")
        self._log("[ACTION] Manual Ejection Triggered.")

    def _update_result_banner(self, final_cls: str, conf: float, action: str, lat_ms: int):
        if final_cls == "FERTILE":
            card_bg = FUTheme.FERTILE_GREEN_CARD
            card_border = FUTheme.FERTILE_GREEN_BORDER
            badge_bg = FUTheme.FERTILE_GREEN_BG
            badge_text_color = FUTheme.FERTILE_GREEN_TEXT
            title_color = FUTheme.FERTILE_GREEN_TEXT
            title_text = f"🟢 FERTILE — ACCEPT ({conf*100:.1f}%)"
            sub_text = "Viable spider embryo network verified • Routed to setter tray"
        elif final_cls == "INFERTILE":
            card_bg = FUTheme.INFERTILE_AMBER_CARD
            card_border = FUTheme.INFERTILE_AMBER_BORDER
            badge_bg = FUTheme.INFERTILE_AMBER_BG
            badge_text_color = FUTheme.INFERTILE_AMBER_TEXT
            title_color = FUTheme.INFERTILE_AMBER
            title_text = f"🟡 INFERTILE — REJECT ({conf*100:.1f}%)"
            sub_text = "Clear unfertilized yolk • Diverted to Penoy salvage @ ₱14.00"
        else:
            card_bg = FUTheme.ABNORMAL_RED_CARD
            card_border = FUTheme.ABNORMAL_RED_BORDER
            badge_bg = FUTheme.ABNORMAL_RED_BG
            badge_text_color = FUTheme.ABNORMAL_RED_TEXT
            title_color = FUTheme.ABNORMAL_RED
            title_text = f"🔴 ABNORMAL — REJECT ({conf*100:.1f}%)"
            sub_text = "Dead embryo / Corrupted yolk • Ejected to cull bin"

        self.result_banner.configure(fg_color=card_bg, border_color=card_border)
        self.result_badge.configure(text=action, fg_color=badge_bg, text_color=badge_text_color)
        self.latency_label.configure(text=f"Latency: {lat_ms}ms")
        self.result_title.configure(text=title_text, text_color=title_color)
        self.result_subtitle.configure(text=sub_text)

    def _update_counters_ui(self):
        pct = (self.fertile_count / max(1, self.total_count)) * 100.0
        batch_pct = min(100.0, (self.total_count / max(1, self.target_egg_count)) * 100.0)

        # Update Progress Bar & Percentage
        self.progress_bar.set(batch_pct / 100.0)
        self.progress_pct_label.configure(text=f"{batch_pct:.1f}% ({self.total_count} / {self.target_egg_count})")

        # Compute Real-time Sorting Speed & Remaining ETA
        if self._session_start_time and self.total_count > 0:
            elapsed_sec = max(1.0, time.time() - self._session_start_time)
            rate_per_min = round((self.total_count / elapsed_sec) * 60.0, 1)
            remaining_eggs = max(0, self.target_egg_count - self.total_count)
            if rate_per_min > 0:
                eta_sec = int((remaining_eggs / rate_per_min) * 60.0)
                eta_str = f"{eta_sec // 60:02d}:{eta_sec % 60:02d}"
            else:
                eta_str = "--:--"
            self.speed_eta_label.configure(text=f"⚡ {rate_per_min:.0f} eggs/min  •  ETA: {eta_str}")
        else:
            self.speed_eta_label.configure(text=f"⚡ Ready (Target: {self.target_egg_count} eggs)")

        # Update Counter Tiles
        self.box_total.configure(text=f"{self.total_count} / {self.target_egg_count}")
        self.box_fertile.configure(text=f"{self.fertile_count} ({pct:.1f}%)")
        self.box_infertile.configure(text=str(self.infertile_count))
        self.box_abnormal.configure(text=str(self.abnormal_count))

    def _update_video_frame(self):
        """
        High-Performance Video Render Loop (~33 FPS).
        Uses atomic frame buffer and native Tkinter PhotoImage for zero-overhead GUI rendering.
        """
        if self.camera.is_running:
            frame = self.camera.get_latest_frame(copy=False)
            if frame is not None:
                # Copy only if drawing active annotations to avoid mutating grabber buffer
                if self.show_crosshairs or self._latest_detections:
                    disp_frame = frame.copy()
                else:
                    disp_frame = frame

                h, w = disp_frame.shape[:2]

                # 1. Draw Optical Candling Alignment Guide / Crosshairs (if enabled)
                if self.show_crosshairs:
                    cv2.circle(disp_frame, (w // 2, h // 2), 6, (0, 255, 0), -1)
                    cv2.line(disp_frame, (w // 2 - 25, h // 2), (w // 2 + 25, h // 2), (0, 255, 0), 1)
                    cv2.line(disp_frame, (w // 2, h // 2 - 25), (w // 2, h // 2 + 25), (0, 255, 0), 1)
                    cv2.ellipse(disp_frame, (w // 2, h // 2), (180, 240), 0, 0, 360, (0, 200, 255), 1)

                # 2. Draw Live AI Bounding Boxes & Classification Labels
                for det in self._latest_detections:
                    bbox = det.get("bbox", [])
                    cls_name = det.get("class", "FERTILE")
                    conf = det.get("confidence", 0.90)

                    if len(bbox) == 4:
                        xc, yc, bw, bh = bbox
                        x1 = int((xc - bw / 2) * w)
                        y1 = int((yc - bh / 2) * h)
                        x2 = int((xc + bw / 2) * w)
                        y2 = int((yc + bh / 2) * h)

                        if cls_name == "FERTILE":
                            box_bgr = (56, 122, 53)     # Agri-Green
                            label_str = f"FERTILE: {conf*100:.1f}%"
                        elif cls_name == "INFERTILE":
                            box_bgr = (6, 119, 217)     # Penoy Amber
                            label_str = f"INFERTILE (PENOY): {conf*100:.1f}%"
                        else:
                            box_bgr = (38, 38, 220)     # Reject Red
                            label_str = f"ABNORMAL: {conf*100:.1f}%"

                        cv2.rectangle(disp_frame, (x1, y1), (x2, y2), box_bgr, 2)
                        (tw, th), _ = cv2.getTextSize(label_str, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
                        cv2.rectangle(disp_frame, (x1, y1 - th - 8), (x1 + tw + 10, y1), box_bgr, -1)
                        cv2.putText(disp_frame, label_str, (x1 + 5, y1 - 4),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA)

                # 3. High-Speed Aspect Ratio Scaling
                rgb_frame = cv2.cvtColor(disp_frame, cv2.COLOR_BGR2RGB)

                container_w = max(100, self._cached_container_w)
                container_h = max(100, self._cached_container_h)

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
                photo = ImageTk.PhotoImage(image=pil_img)
                self.video_label.configure(image=photo)
                self._current_photo = photo

        self.after(30, self._update_video_frame)

    def _update_status_loop(self):
        # Update FPS
        self.fps_label.configure(text=f"FPS: {self.camera.current_fps:.1f}")

        # Update Network Sync Status & Offline Queue Count
        try:
            unsynced_count = self.db.get_unsynced_count()
        except Exception:
            unsynced_count = 0

        if self.sync_worker.is_online:
            if unsynced_count > 0:
                self.net_status_badge.configure(
                    text=f"SYNC: {unsynced_count} PENDING",
                    fg_color=FUTheme.INFERTILE_AMBER_BG,
                    text_color=FUTheme.INFERTILE_AMBER
                )
            else:
                self.net_status_badge.configure(
                    text="SYNC: ONLINE",
                    fg_color=FUTheme.FERTILE_GREEN_BG,
                    text_color=FUTheme.FERTILE_GREEN
                )
        else:
            self.net_status_badge.configure(
                text=f"SYNC: OFFLINE ({unsynced_count} WAL)",
                fg_color=FUTheme.PANEL_LIGHT_ALT,
                text_color=FUTheme.TEXT_MUTED
            )

        # Update ESP32 IoT Status
        if self.iot.is_connected:
            self.iot_status_badge.configure(text="ESP32: CONNECTED", fg_color=FUTheme.FERTILE_GREEN_BG, text_color=FUTheme.FERTILE_GREEN)
        else:
            self.iot_status_badge.configure(text="ESP32: STANDBY", fg_color=FUTheme.PANEL_LIGHT_ALT, text_color=FUTheme.TEXT_MUTED)

        self.after(1000, self._update_status_loop)

    def _log(self, message: str):
        """Append log line and maintain bounded history for smooth scrolling."""
        try:
            self.log_textbox.configure(state="normal")
            self.log_textbox.insert("end", f"{message}\n")
            line_count = int(self.log_textbox.index("end-1c").split(".")[0])
            if line_count > 200:
                self.log_textbox.delete("1.0", f"{line_count - 200}.0")
            self.log_textbox.see("end")
            self.log_textbox.configure(state="disabled")
        except Exception:
            pass

    def confirm_exit_dialog(self):
        """High-contrast modal confirmation prompt before stopping operations or shutting down."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Confirm Exit — OvaLens Operator")
        dialog.geometry("480x280")
        dialog.configure(fg_color=FUTheme.BG_LIGHT)
        dialog.transient(self)
        dialog.grab_set()
        self._center_window(dialog, 480, 280)

        card = ctk.CTkFrame(dialog, fg_color=FUTheme.PANEL_LIGHT, corner_radius=12, border_width=1, border_color=FUTheme.BORDER)
        card.pack(fill="both", expand=True, padx=16, pady=16)

        # Header with Warning Icon
        ctk.CTkLabel(
            card, text="⚠️  Exit OvaLens Operator System?",
            font=(FUTheme.FONT_FAMILY, 15, "bold"), text_color=FUTheme.TEXT_PRIMARY
        ).pack(pady=(16, 6))

        if self.is_session_active or self.is_auto_cycle_running:
            warning_box = ctk.CTkFrame(card, fg_color=FUTheme.INFERTILE_AMBER_BG, corner_radius=8)
            warning_box.pack(fill="x", padx=16, pady=(0, 10))
            ctk.CTkLabel(
                warning_box,
                text="⚡ ACTIVE SORTING SESSION IN PROGRESS\nConveyor motors will halt and remaining eggs stay safely queued.",
                font=(FUTheme.FONT_FAMILY, 10, "bold"), text_color=FUTheme.INFERTILE_AMBER_TEXT,
                justify="center", padx=10, pady=8
            ).pack()
            msg = "Local scans are saved to SQLite WAL.\nAre you sure you want to stop operations and exit?"
        else:
            msg = "All local database records are safely synchronized.\nAre you sure you want to close the operator station?"

        ctk.CTkLabel(
            card, text=msg, font=(FUTheme.FONT_FAMILY, 11),
            text_color=FUTheme.TEXT_MUTED, justify="center"
        ).pack(pady=(0, 16))

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 12))

        ctk.CTkButton(
            btn_row, text="↩ Return to App", fg_color=FUTheme.PANEL_LIGHT_ALT,
            hover_color=FUTheme.PANEL_ACCENT, border_width=1, border_color=FUTheme.BORDER_DARK,
            text_color=FUTheme.TEXT_PRIMARY, font=(FUTheme.FONT_FAMILY, 11, "bold"),
            command=dialog.destroy, width=160, height=38, corner_radius=8
        ).pack(side="left")

        def do_exit():
            dialog.destroy()
            print("\n[*] Shutting down OvaLens Edge Subsystems...")
            if self.camera.is_running:
                self.camera.stop()
            self.iot.stop()
            self.sync_worker.stop()
            self.destroy()
            print("[OK] Graceful shutdown complete.")

        ctk.CTkButton(
            btn_row, text="⏻ Exit System", fg_color=FUTheme.PRIMARY_MAROON,
            hover_color=FUTheme.HOVER_MAROON, text_color=FUTheme.TEXT_WHITE,
            font=(FUTheme.FONT_FAMILY, 12, "bold"), command=do_exit,
            width=160, height=38, corner_radius=8
        ).pack(side="right")

    def open_batch_setup_dialog(self):
        """Robust Modal for Batch creation, selection, and candling stage setup with Offline Format Builder."""
        if self.is_session_active:
            self._log("[WARN] Please stop the current active auto session before changing batch parameters.")

        dialog = ctk.CTkToplevel(self)
        dialog.title("Egg Batch & Candling Setup")
        dialog.geometry("520x660")
        dialog.configure(fg_color=FUTheme.BG_LIGHT)
        dialog.transient(self)
        dialog.grab_set()
        self._center_window(dialog, 520, 660)

        ctk.CTkLabel(
            dialog, text="Egg Batch & Candling Setup",
            font=(FUTheme.FONT_FAMILY, 16, "bold"), text_color=FUTheme.TEXT_PRIMARY
        ).pack(pady=(16, 2))
        ctk.CTkLabel(
            dialog, text="Select active batch from office or create one using the quick builder",
            font=(FUTheme.FONT_FAMILY, 11), text_color=FUTheme.TEXT_MUTED
        ).pack(pady=(0, 12))

        content = ctk.CTkFrame(dialog, fg_color=FUTheme.PANEL_LIGHT, corner_radius=12, border_width=1, border_color=FUTheme.BORDER)
        content.pack(fill="both", expand=True, padx=20, pady=(0, 14))

        # Mode Switcher (Quick Batch Builder vs Office Batches vs Custom)
        mode_var = ctk.StringVar(value="BUILDER")

        mode_segmented = ctk.CTkSegmentedButton(
            content, values=["⚡ Quick Batch Builder", "🌐 Saved Office Batches", "✏️ Custom Code"],
            selected_color=FUTheme.PRIMARY_MAROON, selected_hover_color=FUTheme.HOVER_MAROON,
            unselected_color=FUTheme.PANEL_LIGHT_ALT, unselected_hover_color=FUTheme.PANEL_ACCENT,
            text_color=FUTheme.TEXT_PRIMARY, font=(FUTheme.FONT_FAMILY, 11, "bold"), height=32
        )
        mode_segmented.set("⚡ Quick Batch Builder")
        mode_segmented.pack(fill="x", padx=16, pady=(12, 10))

        # Dynamic Container Frames
        builder_frame = ctk.CTkFrame(content, fg_color="transparent")
        server_frame = ctk.CTkFrame(content, fg_color="transparent")
        custom_frame = ctk.CTkFrame(content, fg_color="transparent")

        # 1. QUICK BATCH BUILDER CONTROLS
        # Current Year-Month default
        now = datetime.now()
        cur_year_month = now.strftime("%Y-%m")
        months_opts = [
            cur_year_month,
            now.replace(month=(now.month % 12) + 1 if now.month < 12 else 1).strftime("%Y-%m"),
            now.replace(month=max(1, now.month - 1)).strftime("%Y-%m"),
        ]

        ym_row = ctk.CTkFrame(builder_frame, fg_color="transparent")
        ym_row.pack(fill="x", pady=(0, 8))

        # Year-Month
        ym_col = ctk.CTkFrame(ym_row, fg_color="transparent")
        ym_col.pack(side="left", fill="x", expand=True, padx=(0, 4))
        ctk.CTkLabel(ym_col, text="Setting Month:", font=(FUTheme.FONT_FAMILY, 10, "bold"), text_color=FUTheme.TEXT_PRIMARY).pack(anchor="w", pady=(0, 2))
        ym_dropdown = ctk.CTkOptionMenu(
            ym_col, values=months_opts, fg_color=FUTheme.PANEL_LIGHT_ALT, text_color=FUTheme.TEXT_PRIMARY,
            button_color=FUTheme.PRIMARY_MAROON, button_hover_color=FUTheme.HOVER_MAROON,
            dropdown_fg_color=FUTheme.PANEL_LIGHT, dropdown_text_color=FUTheme.TEXT_PRIMARY, dropdown_hover_color=FUTheme.PANEL_ACCENT,
            height=34, corner_radius=8
        )
        ym_dropdown.set(cur_year_month)
        ym_dropdown.pack(fill="x")

        # Batch Number (Group #)
        batch_col = ctk.CTkFrame(ym_row, fg_color="transparent")
        batch_col.pack(side="right", fill="x", expand=True, padx=(4, 0))
        ctk.CTkLabel(batch_col, text="Batch #:", font=(FUTheme.FONT_FAMILY, 10, "bold"), text_color=FUTheme.TEXT_PRIMARY).pack(anchor="w", pady=(0, 2))
        batch_num_opts = [f"{i:02d}" for i in range(1, 13)]
        batch_num_dropdown = ctk.CTkOptionMenu(
            batch_col, values=batch_num_opts, fg_color=FUTheme.PANEL_LIGHT_ALT, text_color=FUTheme.TEXT_PRIMARY,
            button_color=FUTheme.PRIMARY_MAROON, button_hover_color=FUTheme.HOVER_MAROON,
            dropdown_fg_color=FUTheme.PANEL_LIGHT, dropdown_text_color=FUTheme.TEXT_PRIMARY, dropdown_hover_color=FUTheme.PANEL_ACCENT,
            height=34, corner_radius=8
        )
        batch_num_dropdown.set("01")
        batch_num_dropdown.pack(fill="x")

        # Breed Dropdown
        ctk.CTkLabel(builder_frame, text="Duck Breed:", font=(FUTheme.FONT_FAMILY, 10, "bold"), text_color=FUTheme.TEXT_PRIMARY).pack(anchor="w", pady=(2, 2))
        breed_map = {
            "KAY (Kayumanggi / Itik Pinas)": ("KAY", "KAYUMANGGI"),
            "ITM (Itim / Native Black)": ("ITM", "ITIM"),
            "KHK (Khaki Campbell Layer)": ("KHK", "KHAKI_CAMPBELL"),
            "PEK (Pekin Cherry Valley)": ("PEK", "PEKIN"),
            "MUS (Muscovy Pato)": ("MUS", "MUSCOVY"),
        }
        breed_builder_dropdown = ctk.CTkOptionMenu(
            builder_frame, values=list(breed_map.keys()), fg_color=FUTheme.PANEL_LIGHT_ALT, text_color=FUTheme.TEXT_PRIMARY,
            button_color=FUTheme.PRIMARY_MAROON, button_hover_color=FUTheme.HOVER_MAROON,
            dropdown_fg_color=FUTheme.PANEL_LIGHT, dropdown_text_color=FUTheme.TEXT_PRIMARY, dropdown_hover_color=FUTheme.PANEL_ACCENT,
            height=34, corner_radius=8
        )
        breed_builder_dropdown.set("KAY (Kayumanggi / Itik Pinas)")
        breed_builder_dropdown.pack(fill="x", pady=(0, 8))

        # Live Code Preview Box with Rich Light Maroon Color Fill & Green Status
        preview_frame = ctk.CTkFrame(
            builder_frame, fg_color=FUTheme.PRIMARY_MAROON_BG, corner_radius=10,
            border_width=1, border_color=FUTheme.PRIMARY_MAROON_BORDER
        )
        preview_frame.pack(fill="x", pady=(2, 10), ipady=4)

        p_top = ctk.CTkFrame(preview_frame, fg_color="transparent")
        p_top.pack(fill="x", padx=12, pady=(6, 0))
        ctk.CTkLabel(p_top, text="LIVE BATCH CODE:", font=(FUTheme.FONT_FAMILY, 9, "bold"), text_color=FUTheme.TEXT_MUTED).pack(side="left")
        ctk.CTkLabel(p_top, text="● READY FOR CONVEYOR", font=(FUTheme.FONT_FAMILY, 9, "bold"), text_color=FUTheme.FERTILE_GREEN).pack(side="right")

        preview_label = ctk.CTkLabel(preview_frame, text="BATCH-2026-08-KAY-01", font=(FUTheme.FONT_FAMILY, 16, "bold"), text_color=FUTheme.TEXT_PRIMARY)
        preview_label.pack(anchor="w", padx=12, pady=(0, 6))

        def update_preview(*args):
            ym = ym_dropdown.get()
            b_key = breed_builder_dropdown.get()
            b_code = breed_map.get(b_key, ("KAY", "KAYUMANGGI"))[0]
            b_num = batch_num_dropdown.get()
            preview_label.configure(text=f"BATCH-{ym}-{b_code}-{b_num}")

        ym_dropdown.configure(command=update_preview)
        breed_builder_dropdown.configure(command=update_preview)
        batch_num_dropdown.configure(command=update_preview)
        update_preview()

        # 2. SAVED OFFICE BATCHES CONTROLS
        ctk.CTkLabel(server_frame, text="Active Incubator Batches (from Office):", font=(FUTheme.FONT_FAMILY, 10, "bold"), text_color=FUTheme.TEXT_PRIMARY).pack(anchor="w", pady=(0, 2))
        server_dropdown = ctk.CTkOptionMenu(
            server_frame, values=["Loading active batches from server..."], fg_color=FUTheme.PANEL_LIGHT_ALT, text_color=FUTheme.TEXT_PRIMARY,
            button_color=FUTheme.PRIMARY_MAROON, button_hover_color=FUTheme.HOVER_MAROON,
            dropdown_fg_color=FUTheme.PANEL_LIGHT, dropdown_text_color=FUTheme.TEXT_PRIMARY, dropdown_hover_color=FUTheme.PANEL_ACCENT,
            height=36, corner_radius=8
        )
        server_dropdown.pack(fill="x", pady=(0, 10))

        server_batches_cache = []

        def fetch_server_batches():
            import urllib.request
            import json
            try:
                url = "http://localhost:8000/api/v1/batches"
                req = urllib.request.Request(url, headers={"User-Agent": "OvaLensEdge/2.0"})
                with urllib.request.urlopen(req, timeout=1.5) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode('utf-8'))
                        if isinstance(data, list) and len(data) > 0:
                            server_batches_cache.clear()
                            server_batches_cache.extend(data)
                            opts = [f"{b.get('batch_code', b.get('batch_id'))}  ({b.get('breed')}, {b.get('initial_egg_count', 500)} eggs)" for b in data]
                            server_dropdown.configure(values=opts)
                            server_dropdown.set(opts[0])
                            return
            except Exception:
                pass
            server_dropdown.configure(values=["(Offline — Use Format Builder tab)"])
            server_dropdown.set("(Offline — Use Format Builder tab)")

        threading.Thread(target=fetch_server_batches, daemon=True).start()

        # 3. CUSTOM CODE CONTROLS
        ctk.CTkLabel(custom_frame, text="Custom / Experimental Batch Code:", font=(FUTheme.FONT_FAMILY, 10, "bold"), text_color=FUTheme.TEXT_PRIMARY).pack(anchor="w", pady=(0, 2))
        custom_entry = ctk.CTkEntry(custom_frame, fg_color=FUTheme.PANEL_LIGHT_ALT, text_color=FUTheme.TEXT_PRIMARY, height=36)
        custom_entry.insert(0, self.current_batch_id)
        custom_entry.pack(fill="x", pady=(0, 10))

        # Mode visibility controller
        def on_mode_change(selected_mode):
            builder_frame.pack_forget()
            server_frame.pack_forget()
            custom_frame.pack_forget()
            if "Builder" in selected_mode:
                builder_frame.pack(fill="x", padx=16, pady=(0, 6))
            elif "Server" in selected_mode:
                server_frame.pack(fill="x", padx=16, pady=(0, 6))
            else:
                custom_frame.pack(fill="x", padx=16, pady=(0, 6))

        mode_segmented.configure(command=on_mode_change)
        builder_frame.pack(fill="x", padx=16, pady=(0, 6))

        # COMMON PARAMETERS: Candling Stage
        ctk.CTkLabel(content, text="Candling Stage:", font=(FUTheme.FONT_FAMILY, 10, "bold"), text_color=FUTheme.TEXT_PRIMARY).pack(anchor="w", padx=16, pady=(4, 2))
        stage_opts = [
            "DAY_10 (Primary Penoy Salvage @ ₱14.00)",
            "DAY_18 (Lockdown Hatcher Transfer)",
            "DAY_25 (Pipping Watch)",
            "DAY_7 (Initial Blood Ring Check)"
        ]
        stage_dropdown = ctk.CTkOptionMenu(
            content, values=stage_opts, fg_color=FUTheme.PANEL_LIGHT_ALT, text_color=FUTheme.TEXT_PRIMARY,
            button_color=FUTheme.PRIMARY_MAROON, button_hover_color=FUTheme.HOVER_MAROON,
            dropdown_fg_color=FUTheme.PANEL_LIGHT, dropdown_text_color=FUTheme.TEXT_PRIMARY, dropdown_hover_color=FUTheme.PANEL_ACCENT,
            height=34, corner_radius=8
        )
        for s in stage_opts:
            if self.current_stage in s:
                stage_dropdown.set(s)
                break
        stage_dropdown.pack(fill="x", padx=16, pady=(0, 8))

        # Target Quantity & Operator
        qty_row = ctk.CTkFrame(content, fg_color="transparent")
        qty_row.pack(fill="x", padx=16, pady=(0, 4))

        col1 = ctk.CTkFrame(qty_row, fg_color="transparent")
        col1.pack(side="left", fill="x", expand=True, padx=(0, 4))
        ctk.CTkLabel(col1, text="Total Eggs in Batch:", font=(FUTheme.FONT_FAMILY, 10, "bold"), text_color=FUTheme.TEXT_PRIMARY).pack(anchor="w", pady=(0, 2))
        qty_entry = ctk.CTkEntry(col1, fg_color=FUTheme.PANEL_LIGHT_ALT, text_color=FUTheme.TEXT_PRIMARY, height=34)
        qty_entry.insert(0, str(self.target_egg_count))
        qty_entry.pack(fill="x")

        col2 = ctk.CTkFrame(qty_row, fg_color="transparent")
        col2.pack(side="right", fill="x", expand=True, padx=(4, 0))
        ctk.CTkLabel(col2, text="Operator Name:", font=(FUTheme.FONT_FAMILY, 10, "bold"), text_color=FUTheme.TEXT_PRIMARY).pack(anchor="w", pady=(0, 2))
        op_entry = ctk.CTkEntry(col2, fg_color=FUTheme.PANEL_LIGHT_ALT, text_color=FUTheme.TEXT_PRIMARY, height=34)
        op_entry.insert(0, self.operator_name)
        op_entry.pack(fill="x")

        # Quantity Quick Preset Chips
        chips_frame = ctk.CTkFrame(content, fg_color="transparent")
        chips_frame.pack(fill="x", padx=16, pady=(0, 10))

        def set_preset_qty(q: int):
            qty_entry.delete(0, "end")
            qty_entry.insert(0, str(q))

        for q_label, q_val in [("500 (12 Trays)", 500), ("250 (6 Trays)", 250), ("100 Eggs", 100), ("42 (1 Tray)", 42)]:
            ctk.CTkButton(
                chips_frame, text=q_label, font=(FUTheme.FONT_FAMILY, 9, "bold"),
                fg_color=FUTheme.PANEL_LIGHT_ALT, text_color=FUTheme.TEXT_SECONDARY,
                hover_color=FUTheme.PANEL_ACCENT, border_width=1, border_color=FUTheme.BORDER,
                height=26, corner_radius=6, command=lambda v=q_val: set_preset_qty(v)
            ).pack(side="left", padx=(0, 4), expand=True, fill="x")

        def apply_batch():
            mode = mode_segmented.get()
            if "Builder" in mode:
                ym = ym_dropdown.get()
                b_key = breed_builder_dropdown.get()
                b_code, full_breed = breed_map.get(b_key, ("KAY", "KAYUMANGGI"))
                b_num = batch_num_dropdown.get()
                final_batch_id = f"BATCH-{ym}-{b_code}-{b_num}"
                final_breed = full_breed
            elif "Server" in mode:
                sel = server_dropdown.get()
                raw_code = sel.split(" ")[0]
                if raw_code.startswith("BATCH-"):
                    final_batch_id = raw_code
                    matched = next((b for b in server_batches_cache if b.get("batch_code") == raw_code or b.get("batch_id") == raw_code), None)
                    final_breed = matched.get("breed", "KAYUMANGGI") if matched else "KAYUMANGGI"
                else:
                    final_batch_id = self.current_batch_id
                    final_breed = self.current_breed
            else:
                final_batch_id = custom_entry.get().strip() or self.current_batch_id
                final_breed = self.current_breed

            raw_qty = qty_entry.get().strip()
            raw_op = op_entry.get().strip()
            raw_stage = stage_dropdown.get().split(" ")[0]

            try:
                parsed_qty = max(1, int(raw_qty))
            except ValueError:
                parsed_qty = 500

            self.current_batch_id = final_batch_id
            self.current_breed = final_breed
            self.current_stage = raw_stage
            self.target_egg_count = parsed_qty
            self.operator_name = raw_op or "Operator"

            if not self.is_session_active:
                self.total_count = 0
                self.fertile_count = 0
                self.infertile_count = 0
                self.abnormal_count = 0
                self._render_standby_hud()

            self.batch_btn.configure(text=f"📋 Batch: {self.current_batch_id}  ({self.current_stage})  ▾")
            self._update_counters_ui()
            self._log(f"[BATCH] Configured: {self.current_batch_id} | Breed: {self.current_breed} | Stage: {self.current_stage} | Target: {self.target_egg_count} eggs")
            dialog.destroy()

        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(0, 16))

        ctk.CTkButton(
            btn_row, text="Cancel", fg_color="transparent", border_width=1, border_color=FUTheme.BORDER,
            text_color=FUTheme.TEXT_MUTED, hover_color=FUTheme.PANEL_ACCENT, command=dialog.destroy,
            width=100, height=38
        ).pack(side="left")

        ctk.CTkButton(
            btn_row, text="Save & Set Active Batch", fg_color=FUTheme.PRIMARY_MAROON,
            hover_color=FUTheme.HOVER_MAROON, text_color=FUTheme.TEXT_WHITE,
            font=(FUTheme.FONT_FAMILY, 12, "bold"), command=apply_batch, height=38
        ).pack(side="right", fill="x", expand=True, padx=(10, 0))

    def open_onboarding_guide(self):
        """Interactive visual operator onboarding guide & hotkey reference modal."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("OvaLens Operator Quick Guide & Onboarding")
        dialog.geometry("600x680")
        dialog.configure(fg_color=FUTheme.BG_LIGHT)
        dialog.transient(self)
        dialog.grab_set()
        self._center_window(dialog, 600, 680)

        # Header
        hdr = ctk.CTkFrame(dialog, fg_color=FUTheme.PANEL_LIGHT, corner_radius=0, height=60, border_width=1, border_color=FUTheme.BORDER)
        hdr.pack(fill="x", side="top")

        ctk.CTkLabel(
            hdr, text="📘 OvaLens Operator Quick Guide",
            font=(FUTheme.FONT_FAMILY, 15, "bold"), text_color=FUTheme.TEXT_PRIMARY
        ).pack(side="left", padx=20, pady=16)

        # Scrollable / Structured Content
        content = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=14)

        # Step 1 Card: Batch Setup
        s1 = ctk.CTkFrame(content, fg_color=FUTheme.PANEL_LIGHT, corner_radius=10, border_width=1, border_color=FUTheme.BORDER)
        s1.pack(fill="x", pady=(0, 10))
        s1_hdr = ctk.CTkFrame(s1, fg_color=FUTheme.PRIMARY_MAROON, height=28, corner_radius=6)
        s1_hdr.pack(fill="x", padx=6, pady=6)
        ctk.CTkLabel(s1_hdr, text="STEP 1: SELECT OR CREATE BATCH CODE", font=(FUTheme.FONT_FAMILY, 11, "bold"), text_color=FUTheme.TEXT_WHITE).pack(side="left", padx=10)

        s1_body = ctk.CTkLabel(
            s1,
            text="• Online: Select active batch registered from the office dashboard.\n• Offline: Use the 100% Dropdown Quick Batch Builder (Month + Breed + Batch #).\n• Example batch code: BATCH-2026-08-KAY-01.",
            font=(FUTheme.FONT_FAMILY, 11), text_color=FUTheme.TEXT_PRIMARY, justify="left"
        )
        s1_body.pack(anchor="w", padx=14, pady=(2, 10))

        # Step 2 Card: Conveyor Sorting Loop
        s2 = ctk.CTkFrame(content, fg_color=FUTheme.PANEL_LIGHT, corner_radius=10, border_width=1, border_color=FUTheme.BORDER)
        s2.pack(fill="x", pady=(0, 10))
        s2_hdr = ctk.CTkFrame(s2, fg_color=FUTheme.FERTILE_GREEN, height=28, corner_radius=6)
        s2_hdr.pack(fill="x", padx=6, pady=6)
        ctk.CTkLabel(s2_hdr, text="STEP 2: AUTOMATED CANDLING & CONVEYOR SORTING", font=(FUTheme.FONT_FAMILY, 11, "bold"), text_color=FUTheme.TEXT_WHITE).pack(side="left", padx=10)

        s2_body = ctk.CTkLabel(
            s2,
            text="• Click [START AUTO SORTING] in footer to activate camera & motor.\n• Sorter advances eggs into the dark candling chamber at 120 eggs/min.\n• High-speed YOLOv8 ONNX model classifies embryo vitality in < 25ms.\n• Machine automatically stops and chimes when all target eggs are sorted.",
            font=(FUTheme.FONT_FAMILY, 11), text_color=FUTheme.TEXT_PRIMARY, justify="left"
        )
        s2_body.pack(anchor="w", padx=14, pady=(2, 10))

        # Step 3 Card: 3 Biological Actions
        s3 = ctk.CTkFrame(content, fg_color=FUTheme.PANEL_LIGHT, corner_radius=10, border_width=1, border_color=FUTheme.BORDER)
        s3.pack(fill="x", pady=(0, 10))
        s3_hdr = ctk.CTkFrame(s3, fg_color=FUTheme.INFERTILE_AMBER, height=28, corner_radius=6)
        s3_hdr.pack(fill="x", padx=6, pady=6)
        ctk.CTkLabel(s3_hdr, text="STEP 3: 3-CLASS SORTING & DIVERTER ACTIONS", font=(FUTheme.FONT_FAMILY, 11, "bold"), text_color=FUTheme.TEXT_WHITE).pack(side="left", padx=10)

        s3_body = ctk.CTkLabel(
            s3,
            text="🟢 FERTILE (Accept): Spider blood veins verified -> stays on tray to Day 18.\n🟡 INFERTILE (Reject): Clear yolk -> servo diverts to Penoy salvage @ ₱14.00.\n🔴 ABNORMAL (Reject): Dead embryo / blood ring -> ejected to cull bin.",
            font=(FUTheme.FONT_FAMILY, 11), text_color=FUTheme.TEXT_PRIMARY, justify="left"
        )
        s3_body.pack(anchor="w", padx=14, pady=(2, 10))

        # Step 4 Card: Keyboard Shortcuts
        s4 = ctk.CTkFrame(content, fg_color=FUTheme.PANEL_LIGHT, corner_radius=10, border_width=1, border_color=FUTheme.BORDER)
        s4.pack(fill="x", pady=(0, 10))
        s4_hdr = ctk.CTkFrame(s4, fg_color=FUTheme.PANEL_ACCENT, height=28, corner_radius=6)
        s4_hdr.pack(fill="x", padx=6, pady=6)
        ctk.CTkLabel(s4_hdr, text="⌨️ KEYBOARD SHORTCUTS & HARDWARE HOTKEYS", font=(FUTheme.FONT_FAMILY, 11, "bold"), text_color=FUTheme.TEXT_PRIMARY).pack(side="left", padx=10)

        s4_body = ctk.CTkLabel(
            s4,
            text="• [SPACEBAR]: Trigger Single Test Scan (Manual Candling)\n• [ESC] key: End Session (Run Summary & Direct CSV Export)\n• [S] key: Scan Explorer & Candling History\n• [R] key: Emergency Manual Servo Eject\n• [F11] key: Toggle Kiosk / Fullscreen Mode\n• [C] key: Toggle Optical Alignment Crosshairs\n• [B] key: Open Batch Setup Modal\n• [F1] / [H]: Open this Operator Quick Guide",
            font=(FUTheme.FONT_FAMILY, 11, "bold"), text_color=FUTheme.TEXT_PRIMARY, justify="left"
        )
        s4_body.pack(anchor="w", padx=14, pady=(2, 10))

        # Footer Button
        f_row = ctk.CTkFrame(dialog, fg_color="transparent")
        f_row.pack(fill="x", padx=20, pady=(0, 14))

        ctk.CTkButton(
            f_row, text="Got It! Close Guide", fg_color=FUTheme.PRIMARY_MAROON,
            hover_color=FUTheme.HOVER_MAROON, text_color=FUTheme.TEXT_WHITE,
            font=(FUTheme.FONT_FAMILY, 12, "bold"), command=dialog.destroy, height=38
        ).pack(fill="x")

    def open_calibration_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Conveyor Calibration & Cycle Timing")
        dialog.geometry("450x440")
        dialog.configure(fg_color=FUTheme.BG_LIGHT)
        dialog.transient(self)
        dialog.grab_set()
        self._center_window(dialog, 450, 440)

        ctk.CTkLabel(
            dialog, text="Conveyor & Sorting Cycle Calibration",
            font=(FUTheme.FONT_FAMILY, 15, "bold"), text_color=FUTheme.TEXT_PRIMARY
        ).pack(pady=(16, 10))

        # Speed
        ctk.CTkLabel(dialog, text="Conveyor Linear Speed (cm/s):", font=(FUTheme.FONT_FAMILY, 11), text_color=FUTheme.TEXT_MUTED).pack(anchor="w", padx=24)
        speed_entry = ctk.CTkEntry(dialog, fg_color=FUTheme.PANEL_LIGHT_ALT, text_color=FUTheme.TEXT_PRIMARY)
        speed_entry.insert(0, str(self.conveyor_speed_cm_s))
        speed_entry.pack(fill="x", padx=24, pady=(2, 8))

        # Chamber Pause
        ctk.CTkLabel(dialog, text="Chamber Candling Pause Duration (ms):", font=(FUTheme.FONT_FAMILY, 11), text_color=FUTheme.TEXT_MUTED).pack(anchor="w", padx=24)
        pause_entry = ctk.CTkEntry(dialog, fg_color=FUTheme.PANEL_LIGHT_ALT, text_color=FUTheme.TEXT_PRIMARY)
        pause_entry.insert(0, str(self.chamber_pause_ms))
        pause_entry.pack(fill="x", padx=24, pady=(2, 8))

        # Advance Duration
        ctk.CTkLabel(dialog, text="Egg Advance Transport Duration (ms):", font=(FUTheme.FONT_FAMILY, 11), text_color=FUTheme.TEXT_MUTED).pack(anchor="w", padx=24)
        adv_entry = ctk.CTkEntry(dialog, fg_color=FUTheme.PANEL_LIGHT_ALT, text_color=FUTheme.TEXT_PRIMARY)
        adv_entry.insert(0, str(self.conveyor_advance_ms))
        adv_entry.pack(fill="x", padx=24, pady=(2, 8))

        # Distance
        ctk.CTkLabel(dialog, text="Camera to Diverter Gate Distance (cm):", font=(FUTheme.FONT_FAMILY, 11), text_color=FUTheme.TEXT_MUTED).pack(anchor="w", padx=24)
        dist_entry = ctk.CTkEntry(dialog, fg_color=FUTheme.PANEL_LIGHT_ALT, text_color=FUTheme.TEXT_PRIMARY)
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

    def toggle_fullscreen(self, event=None):
        """Toggle borderless kiosk fullscreen for industrial touchscreens."""
        self.is_fullscreen = not self.is_fullscreen
        self.attributes("-fullscreen", self.is_fullscreen)
        if not self.is_fullscreen:
            self.geometry("1280x860")
        self._log(f"[UI] Kiosk Fullscreen Mode: {'ENABLED' if self.is_fullscreen else 'DISABLED'}")

    def toggle_crosshairs(self, event=None):
        """Toggle candling aperture optical crosshairs & alignment guide."""
        self.show_crosshairs = not self.show_crosshairs
        self._log(f"[UI] Chamber Alignment Optical Crosshairs: {'ENABLED' if self.show_crosshairs else 'DISABLED'}")

    def _play_completion_chime(self):
        """Acoustic audio tone alert for farm operators when sorting batch finishes."""
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass

    def open_batch_completion_modal(self):
        """Interactive Batch Completion Report dialog with 1-click local CSV export."""
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Batch Complete — {self.current_batch_id}")
        dialog.geometry("540x580")
        dialog.configure(fg_color=FUTheme.BG_LIGHT)
        dialog.transient(self)
        dialog.grab_set()
        self._center_window(dialog, 540, 580)

        card = ctk.CTkFrame(dialog, fg_color=FUTheme.PANEL_LIGHT, corner_radius=12, border_width=1, border_color=FUTheme.BORDER)
        card.pack(fill="both", expand=True, padx=16, pady=16)

        # Header with Trophy / Check Icon
        ctk.CTkLabel(
            card, text="🏁 Batch Sorting Completed!",
            font=(FUTheme.FONT_FAMILY, 17, "bold"), text_color=FUTheme.TEXT_PRIMARY
        ).pack(pady=(16, 2))

        ctk.CTkLabel(
            card, text=f"Batch: {self.current_batch_id}  •  Stage: {self.current_stage}  •  Operator: {self.operator_name}",
            font=(FUTheme.FONT_FAMILY, 11), text_color=FUTheme.TEXT_MUTED
        ).pack(pady=(0, 14))

        # Metrics Grid
        grid = ctk.CTkFrame(card, fg_color="transparent")
        grid.pack(fill="x", padx=16, pady=(0, 14))
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        pct = (self.fertile_count / max(1, self.total_count)) * 100.0
        penoy_salvage_val = self.infertile_count * 14.00

        # Tile 1: Total Processed
        t1 = ctk.CTkFrame(grid, fg_color=FUTheme.PANEL_LIGHT_ALT, corner_radius=8, border_width=1, border_color=FUTheme.BORDER)
        t1.grid(row=0, column=0, padx=4, pady=4, sticky="nsew")
        ctk.CTkLabel(t1, text="TOTAL SORTED", font=(FUTheme.FONT_FAMILY, 9, "bold"), text_color=FUTheme.TEXT_MUTED).pack(anchor="w", padx=10, pady=(6, 0))
        ctk.CTkLabel(t1, text=f"{self.total_count} Eggs (100%)", font=(FUTheme.FONT_FAMILY, 15, "bold"), text_color=FUTheme.TEXT_PRIMARY).pack(anchor="w", padx=10, pady=(0, 6))

        # Tile 2: Fertile Embryos
        t2 = ctk.CTkFrame(grid, fg_color=FUTheme.FERTILE_GREEN_CARD, corner_radius=8, border_width=1, border_color=FUTheme.FERTILE_GREEN_BORDER)
        t2.grid(row=0, column=1, padx=4, pady=4, sticky="nsew")
        ctk.CTkLabel(t2, text="FERTILE (ACCEPT)", font=(FUTheme.FONT_FAMILY, 9, "bold"), text_color=FUTheme.FERTILE_GREEN_TEXT).pack(anchor="w", padx=10, pady=(6, 0))
        ctk.CTkLabel(t2, text=f"{self.fertile_count} ({pct:.1f}%)", font=(FUTheme.FONT_FAMILY, 15, "bold"), text_color=FUTheme.FERTILE_GREEN_TEXT).pack(anchor="w", padx=10, pady=(0, 6))

        # Tile 3: Penoy Salvage
        t3 = ctk.CTkFrame(grid, fg_color=FUTheme.INFERTILE_AMBER_CARD, corner_radius=8, border_width=1, border_color=FUTheme.INFERTILE_AMBER_BORDER)
        t3.grid(row=1, column=0, padx=4, pady=4, sticky="nsew")
        ctk.CTkLabel(t3, text="PENOY SALVAGE YIELD", font=(FUTheme.FONT_FAMILY, 9, "bold"), text_color=FUTheme.INFERTILE_AMBER_TEXT).pack(anchor="w", padx=10, pady=(6, 0))
        ctk.CTkLabel(t3, text=f"{self.infertile_count} eggs -> ₱{penoy_salvage_val:,.2f}", font=(FUTheme.FONT_FAMILY, 14, "bold"), text_color=FUTheme.INFERTILE_AMBER).pack(anchor="w", padx=10, pady=(0, 6))

        # Tile 4: Abnormal Culls
        t4 = ctk.CTkFrame(grid, fg_color=FUTheme.ABNORMAL_RED_CARD, corner_radius=8, border_width=1, border_color=FUTheme.ABNORMAL_RED_BORDER)
        t4.grid(row=1, column=1, padx=4, pady=4, sticky="nsew")
        ctk.CTkLabel(t4, text="ABNORMAL (CULL)", font=(FUTheme.FONT_FAMILY, 9, "bold"), text_color=FUTheme.ABNORMAL_RED_TEXT).pack(anchor="w", padx=10, pady=(6, 0))
        ctk.CTkLabel(t4, text=f"{self.abnormal_count} Eggs", font=(FUTheme.FONT_FAMILY, 15, "bold"), text_color=FUTheme.ABNORMAL_RED).pack(anchor="w", padx=10, pady=(0, 6))

        # Export Status Toast
        status_msg = ctk.CTkLabel(card, text="", font=(FUTheme.FONT_FAMILY, 10, "bold"), text_color=FUTheme.FERTILE_GREEN_TEXT)
        status_msg.pack(pady=(0, 6))

        def export_csv():
            try:
                path = self.db.export_session_csv(self.current_session_id)
                status_msg.configure(text=f"✓ Report Exported to {os.path.basename(path)}", text_color=FUTheme.FERTILE_GREEN_TEXT)
                self._log(f"[EXPORT] CSV Report saved: {path}")
            except Exception as e:
                status_msg.configure(text=f"Export failed: {e}", text_color=FUTheme.ABNORMAL_RED_TEXT)

        # Export Button
        ctk.CTkButton(
            card, text="📄 Export Local CSV Report", fg_color=FUTheme.PANEL_LIGHT_ALT,
            hover_color=FUTheme.PANEL_ACCENT, border_width=1, border_color=FUTheme.BORDER_DARK,
            text_color=FUTheme.TEXT_PRIMARY, font=(FUTheme.FONT_FAMILY, 12, "bold"),
            command=export_csv, height=38, corner_radius=8
        ).pack(fill="x", padx=16, pady=(0, 8))

        # Bottom Row
        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 12))

        def start_next():
            dialog.destroy()
            self.open_batch_setup_dialog()

        ctk.CTkButton(
            btn_row, text="🔁 Setup Next Batch", fg_color=FUTheme.PRIMARY_MAROON,
            hover_color=FUTheme.HOVER_MAROON, text_color=FUTheme.TEXT_WHITE,
            font=(FUTheme.FONT_FAMILY, 12, "bold"), command=start_next,
            height=38, corner_radius=8
        ).pack(side="left", fill="x", expand=True, padx=(0, 6))

        ctk.CTkButton(
            btn_row, text="Done & Close", fg_color=FUTheme.PANEL_LIGHT_ALT,
            hover_color=FUTheme.PANEL_ACCENT, text_color=FUTheme.TEXT_SECONDARY,
            font=(FUTheme.FONT_FAMILY, 11), command=dialog.destroy,
            height=38, corner_radius=8, width=110
        ).pack(side="right")

    def open_scan_history_modal(self, event=None):
        """Interactive Scan History & Explorer modal with batch selector, live search, class filters, and CSV export."""
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Scan Explorer & History — Batch {self.current_batch_id}")
        dialog.geometry("780x700")
        dialog.configure(fg_color=FUTheme.BG_LIGHT)
        dialog.transient(self)
        dialog.grab_set()
        self._center_window(dialog, 780, 700)

        card = ctk.CTkFrame(dialog, fg_color=FUTheme.PANEL_LIGHT, corner_radius=12, border_width=1, border_color=FUTheme.BORDER)
        card.pack(fill="both", expand=True, padx=16, pady=16)

        # Header Row
        hdr = ctk.CTkFrame(card, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(14, 8))

        ctk.CTkLabel(
            hdr, text="🔍 Scan Explorer & Candling History",
            font=(FUTheme.FONT_FAMILY, 16, "bold"), text_color=FUTheme.TEXT_PRIMARY
        ).pack(side="left")

        # Current Batch State Management
        selected_batch = [self.current_batch_id]
        current_filter = ["ALL"]

        # Batch Selection & Search Bar
        control_bar = ctk.CTkFrame(card, fg_color=FUTheme.PANEL_LIGHT_ALT, corner_radius=8, border_width=1, border_color=FUTheme.BORDER)
        control_bar.pack(fill="x", padx=16, pady=(0, 10))

        ctk.CTkLabel(
            control_bar, text="BATCH:", font=(FUTheme.FONT_FAMILY, 10, "bold"),
            text_color=FUTheme.TEXT_MUTED
        ).pack(side="left", padx=(10, 4), pady=8)

        # Distinct Batches Query
        distinct_batches = self.db.get_distinct_batches()
        batch_ids = [b["batch_id"] for b in distinct_batches]
        if self.current_batch_id not in batch_ids:
            batch_ids.insert(0, self.current_batch_id)
        batch_options = batch_ids + (["ALL (All Batches)"] if len(batch_ids) > 1 else [])

        batch_dropdown = ctk.CTkOptionMenu(
            control_bar, values=batch_options, font=(FUTheme.FONT_FAMILY, 11, "bold"),
            fg_color=FUTheme.PRIMARY_MAROON, button_color=FUTheme.HOVER_MAROON,
            text_color=FUTheme.TEXT_WHITE, dropdown_fg_color=FUTheme.PANEL_LIGHT,
            dropdown_hover_color=FUTheme.PANEL_ACCENT, dropdown_text_color=FUTheme.TEXT_PRIMARY,
            height=30, width=220
        )
        batch_dropdown.set(self.current_batch_id)
        batch_dropdown.pack(side="left", padx=(0, 10), pady=6)

        # Live Search Field
        search_entry = ctk.CTkEntry(
            control_bar, placeholder_text="Search #Seq or Scan ID...",
            font=(FUTheme.FONT_FAMILY, 11), fg_color=FUTheme.PANEL_LIGHT,
            text_color=FUTheme.TEXT_PRIMARY, border_width=1, border_color=FUTheme.BORDER,
            height=30, width=200
        )
        search_entry.pack(side="right", padx=(0, 10), pady=6)

        # Filter Tabs & Live Stats Bar
        filter_row = ctk.CTkFrame(card, fg_color="transparent")
        filter_row.pack(fill="x", padx=16, pady=(0, 8))

        stats_summary_label = ctk.CTkLabel(
            filter_row, text="", font=(FUTheme.FONT_FAMILY, 10, "bold"),
            text_color=FUTheme.TEXT_MUTED
        )
        stats_summary_label.pack(side="right")

        tab_btns = {}
        tab_container = ctk.CTkFrame(filter_row, fg_color="transparent")
        tab_container.pack(side="left")

        # Scrollable table container
        table_container = ctk.CTkScrollableFrame(card, fg_color=FUTheme.PANEL_LIGHT_ALT, corner_radius=8)
        table_container.pack(fill="both", expand=True, padx=16, pady=(0, 10))

        # Status toast for CSV exports
        toast_label = ctk.CTkLabel(card, text="", font=(FUTheme.FONT_FAMILY, 10, "bold"), text_color=FUTheme.FERTILE_GREEN_TEXT)
        toast_label.pack(pady=(0, 4))

        def get_active_batch_id():
            val = batch_dropdown.get()
            if "ALL" in val:
                return "ALL"
            return val

        def update_tabs_and_stats():
            b_id = get_active_batch_id()
            all_b_scans = self.db.get_scans_by_batch(b_id, limit=5000, class_filter="ALL")
            n_tot = len(all_b_scans)
            n_fert = sum(1 for s in all_b_scans if s["final_class"] == "FERTILE")
            n_inf = sum(1 for s in all_b_scans if s["final_class"] == "INFERTILE")
            n_abn = sum(1 for s in all_b_scans if s["final_class"] == "ABNORMAL")
            fert_pct = (n_fert / max(1, n_tot)) * 100.0 if n_tot > 0 else 0.0

            stats_summary_label.configure(
                text=f"Total: {n_tot} • Fertile: {fert_pct:.1f}% • Penoy: ₱{n_inf*14:,.0f} • Cull: {n_abn}"
            )

            # Update tab label text
            if "ALL" in tab_btns:
                tab_btns["ALL"].configure(text=f"All ({n_tot})")
            if "FERTILE" in tab_btns:
                tab_btns["FERTILE"].configure(text=f"🟢 Fertile ({n_fert})")
            if "INFERTILE" in tab_btns:
                tab_btns["INFERTILE"].configure(text=f"🟡 Infertile ({n_inf})")
            if "ABNORMAL" in tab_btns:
                tab_btns["ABNORMAL"].configure(text=f"🔴 Abnormal ({n_abn})")

        def render_table(*args):
            for child in table_container.winfo_children():
                child.destroy()

            b_id = get_active_batch_id()
            flt = current_filter[0]
            query = search_entry.get().strip()
            scans = self.db.get_scans_by_batch(b_id, limit=250, class_filter=flt, search_query=query if query else None)

            if not scans:
                empty = ctk.CTkLabel(
                    table_container, text=f"No scans found matching filter '{flt}' (Batch: {b_id}).",
                    font=(FUTheme.FONT_FAMILY, 12), text_color=FUTheme.TEXT_MUTED
                )
                empty.pack(pady=40)
                return

            for s in scans:
                cls_name = s["final_class"]
                conf_pct = f"{s['confidence']*100:.1f}%"
                seq_num = s["sequence_number"]
                action = s["routing_action"]
                b_code = s["batch_id"]
                lat = f"{s['inference_ms']}ms"
                time_str = s["scanned_at"].split("T")[1][:8] if "T" in s["scanned_at"] else s["scanned_at"]

                if cls_name == "FERTILE":
                    badge_fg = FUTheme.FERTILE_GREEN_CARD
                    badge_border = FUTheme.FERTILE_GREEN_BORDER
                    badge_text = FUTheme.FERTILE_GREEN_TEXT
                    pill = "🟢 FERTILE"
                elif cls_name == "INFERTILE":
                    badge_fg = FUTheme.INFERTILE_AMBER_CARD
                    badge_border = FUTheme.INFERTILE_AMBER_BORDER
                    badge_text = FUTheme.INFERTILE_AMBER_TEXT
                    pill = "🟡 INFERTILE"
                else:
                    badge_fg = FUTheme.ABNORMAL_RED_CARD
                    badge_border = FUTheme.ABNORMAL_RED_BORDER
                    badge_text = FUTheme.ABNORMAL_RED_TEXT
                    pill = "🔴 ABNORMAL"

                row_card = ctk.CTkFrame(table_container, fg_color=FUTheme.PANEL_LIGHT, corner_radius=8, border_width=1, border_color=FUTheme.BORDER)
                row_card.pack(fill="x", pady=3, padx=4)

                # Col 1: Sequence #
                ctk.CTkLabel(
                    row_card, text=f"#{seq_num:03d}", font=(FUTheme.FONT_FAMILY, 11, "bold"),
                    text_color=FUTheme.TEXT_PRIMARY, width=45
                ).pack(side="left", padx=(10, 4), pady=7)

                # Col 2: Classification Badge Pill
                cls_lbl = ctk.CTkLabel(
                    row_card, text=pill, font=(FUTheme.FONT_FAMILY, 10, "bold"),
                    fg_color=badge_fg, text_color=badge_text, corner_radius=5, padx=8, pady=2
                )
                cls_lbl.pack(side="left", padx=4, pady=7)

                # Col 3: Batch Code Pill (if viewing ALL batches)
                if b_id == "ALL":
                    ctk.CTkLabel(
                        row_card, text=b_code, font=(FUTheme.FONT_FAMILY, 9, "bold"),
                        fg_color=FUTheme.PANEL_LIGHT_ALT, text_color=FUTheme.TEXT_MUTED,
                        corner_radius=4, padx=6, pady=2
                    ).pack(side="left", padx=4, pady=7)

                # Col 4: Confidence & Action
                ctk.CTkLabel(
                    row_card, text=f"Conf: {conf_pct}  •  {action}",
                    font=(FUTheme.FONT_FAMILY, 10), text_color=FUTheme.TEXT_SECONDARY
                ).pack(side="left", padx=8, pady=7)

                # Col 5 (Right): Time & Latency
                meta_txt = f"{time_str}  ({lat})"
                ctk.CTkLabel(
                    row_card, text=meta_txt, font=("Consolas", 10), text_color=FUTheme.TEXT_MUTED
                ).pack(side="right", padx=(4, 12), pady=7)

        def set_filter(flt: str):
            current_filter[0] = flt
            for k, btn in tab_btns.items():
                if k == flt:
                    btn.configure(fg_color=FUTheme.PRIMARY_MAROON, text_color=FUTheme.TEXT_WHITE)
                else:
                    btn.configure(fg_color=FUTheme.PANEL_LIGHT_ALT, text_color=FUTheme.TEXT_PRIMARY)
            render_table()

        def on_batch_change(new_val):
            update_tabs_and_stats()
            render_table()

        batch_dropdown.configure(command=on_batch_change)
        search_entry.bind("<KeyRelease>", lambda e: render_table())

        # Build Filter Tabs
        tabs_spec = [
            ("ALL", "All"),
            ("FERTILE", "🟢 Fertile"),
            ("INFERTILE", "🟡 Infertile"),
            ("ABNORMAL", "🔴 Abnormal"),
        ]

        for key, label in tabs_spec:
            btn = ctk.CTkButton(
                tab_container, text=label, font=(FUTheme.FONT_FAMILY, 10, "bold"),
                fg_color=FUTheme.PRIMARY_MAROON if key == "ALL" else FUTheme.PANEL_LIGHT_ALT,
                text_color=FUTheme.TEXT_WHITE if key == "ALL" else FUTheme.TEXT_PRIMARY,
                hover_color=FUTheme.HOVER_MAROON, height=28, corner_radius=6,
                command=lambda k=key: set_filter(k)
            )
            btn.pack(side="left", padx=(0, 6))
            tab_btns[key] = btn

        update_tabs_and_stats()
        render_table()

        # Bottom Actions / Export Toolbar
        b_bar = ctk.CTkFrame(card, fg_color="transparent")
        b_bar.pack(fill="x", padx=16, pady=(0, 10))

        def export_current():
            try:
                b_id = get_active_batch_id()
                flt = current_filter[0]
                path = self.db.export_batch_csv(b_id, class_filter=flt)
                toast_label.configure(text=f"✓ Exported {flt} scans to: {os.path.basename(path)}", text_color=FUTheme.FERTILE_GREEN_TEXT)
                self._log(f"[EXPORT] Filtered CSV saved: {path}")
            except Exception as e:
                toast_label.configure(text=f"Export error: {e}", text_color=FUTheme.ABNORMAL_RED_TEXT)

        def export_all():
            try:
                b_id = get_active_batch_id()
                path = self.db.export_batch_csv(b_id, class_filter="ALL")
                toast_label.configure(text=f"✓ Exported ALL batch scans to: {os.path.basename(path)}", text_color=FUTheme.FERTILE_GREEN_TEXT)
                self._log(f"[EXPORT] Complete batch CSV saved: {path}")
            except Exception as e:
                toast_label.configure(text=f"Export error: {e}", text_color=FUTheme.ABNORMAL_RED_TEXT)

        ctk.CTkButton(
            b_bar, text="📄 Export Current Filter (CSV)", fg_color=FUTheme.PRIMARY_MAROON,
            hover_color=FUTheme.HOVER_MAROON, text_color=FUTheme.TEXT_WHITE,
            font=(FUTheme.FONT_FAMILY, 11, "bold"), command=export_current, height=36, corner_radius=8
        ).pack(side="left", fill="x", expand=True, padx=(0, 6))

        ctk.CTkButton(
            b_bar, text="💾 Export Selected Batch (CSV)", fg_color=FUTheme.PANEL_LIGHT_ALT,
            hover_color=FUTheme.PANEL_ACCENT, border_width=1, border_color=FUTheme.BORDER_DARK,
            text_color=FUTheme.TEXT_PRIMARY, font=(FUTheme.FONT_FAMILY, 11, "bold"),
            command=export_all, height=36, corner_radius=8
        ).pack(side="left", fill="x", expand=True, padx=(0, 6))

        ctk.CTkButton(
            b_bar, text="Close", fg_color=FUTheme.PANEL_LIGHT_ALT, hover_color=FUTheme.PANEL_ACCENT,
            text_color=FUTheme.TEXT_SECONDARY, font=(FUTheme.FONT_FAMILY, 11),
            command=dialog.destroy, height=36, corner_radius=8, width=80
        ).pack(side="right")
