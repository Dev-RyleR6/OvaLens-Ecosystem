"""
OvaLens Operator Desktop GUI (CustomTkinter 60 FPS)
Foundation University Automated Duck Egg Candling & Conveyor Sorting System.
FU slate operator interface with readable typography and persistent safety controls.
"""

import os
import time
import uuid
import threading
import queue
import math
from functools import wraps
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
from ..core.chamber_controller import ChamberController, ChamberState
from ..core.background_jobs import BackgroundJobs
from ..core.inference_worker import InferenceWorker
from ..core.realtime_detector import RealtimeDetectionWorker
from ..core.operator_flow import OperatorState, validate_batch_config
from ..iot.serial_driver import ESP32SerialDriver
from ..db.local_db import LocalDatabaseManager
from ..sync.sync_worker import BackgroundSyncWorker
from .station_settings import StationSettingsWindow


def _building_dialog(method):
    """Defer shutdown during Tk's reentrant dialog-construction callbacks."""
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        if self._closing:
            return
        self._dialog_build_depth = getattr(self, "_dialog_build_depth", 0) + 1
        try:
            return method(self, *args, **kwargs)
        finally:
            self._dialog_build_depth -= 1
    return wrapped


class OvaLensOperatorApp(ctk.CTk):
    def __init__(self, camera: CameraGrabber, engine: InferenceEngine,
                 iot: ESP32SerialDriver, db: LocalDatabaseManager,
                 sync_worker: BackgroundSyncWorker,
                 chamber: Optional[ChamberController] = None,
                 inference_worker: Optional[Any] = None,
                 device_id: str = "STATION-01-RP5",
                 startup_config: Optional[Dict[str, Any]] = None,
                 fullscreen: bool = True, station=None):
        super().__init__()

        self.camera = camera
        self.station = station
        self.engine = engine
        self.iot = iot
        self.db = db
        self.sync_worker = sync_worker
        self.chamber = chamber
        self.inference_worker = inference_worker
        self._operator_state = OperatorState.READY
        self._pending_prediction = None
        self._inference_request_id = None
        self._pending_finalization_id = None
        self._finalization_failed = False
        self._diagnostics_complete = False
        self.device_id = device_id
        self._ui_events = queue.Queue()
        self._closing = False
        self._operation_generation = 0
        self._scan_busy = False
        self._stopping = False
        self.simulation = bool((startup_config or {}).get("simulation", False))

        # Operational parameters from startup config
        cfg = startup_config or {}
        self.conveyor_speed_cm_s  = float(cfg.get("conveyor_speed_cm_s", 12.50))
        self.conveyor_dist_cm     = float(cfg.get("conveyor_dist_cm", 25.00))
        self.servo_pulse_ms       = int(cfg.get("servo_pulse_ms", 250))
        self.display_result_ms    = int(cfg.get("display_result_ms", 1200))
        self.chamber_pause_ms     = int(cfg.get("chamber_pause_ms", 150))       # Settle time inside chamber
        self.conveyor_advance_ms  = int(cfg.get("conveyor_advance_ms", 900))     # Advance time between eggs

        # Batch & Session Configuration (from startup config)
        self.current_session_id: Optional[str] = None
        self.current_batch_id: str = str(cfg.get("batch_id", "BATCH-2026-08-KAY-01"))
        self.current_breed: str = str(cfg.get("breed", "KAYUMANGGI"))
        self.current_stage: str = str(cfg.get("stage", "DAY_10"))
        self.target_egg_count: int = int(cfg.get("egg_count", 500))
        self.incubator_id: str = "INCUBATOR-A1"
        self.operator_name: str = str(cfg.get("operator", "Pedro Penduko"))
        self.is_session_active: bool = False
        self.is_auto_cycle_running: bool = False
        self.scan_sequence: int = 0

        # Automated Cycle Threading
        self._auto_cycle_thread: Optional[threading.Thread] = None
        self._chamber_thread: Optional[threading.Thread] = None
        self._stop_cycle_event = threading.Event()

        # Live Real-time Inference Cache
        self._latest_detections: List[Dict[str, Any]] = []
        self._last_live_infer_time = 0.0
        self._last_scan_result_time = 0.0

        # Performance & Ergonomics State
        self.is_fullscreen = bool((startup_config or {}).get("fullscreen", fullscreen))
        self.show_crosshairs = True
        self._session_start_time: Optional[float] = None
        self._cached_container_w = 640
        self._cached_container_h = 480

        # Live Counters
        self.total_count = 0
        self.fertile_count = 0
        self.infertile_count = 0
        self.review_count = 0

        # Wire ChamberController callbacks if provided
        if self.chamber is not None:
            self.chamber.on_state_change = lambda s, c, t: self._ui_events.put(lambda: self._on_chamber_state_change(s, c, t))
            self.chamber.on_scan_result = lambda r: self._ui_events.put(lambda: self._on_chamber_scan_result(r))
            self.chamber.on_batch_complete = lambda c: self._ui_events.put(lambda: self._on_batch_complete_callback(c))
            self.chamber.on_jam_detected = lambda: self._ui_events.put(self._on_jam_detected)

        # Window Configuration (Industrial Pro Gray Theme)
        self.title("OvaLens — Automated Duck Egg Candling System (Foundation University)")
        self.geometry("1280x860")
        self.minsize(1024, 720)
        ctk.set_appearance_mode("dark")
        self.configure(fg_color=FUTheme.BG_LIGHT)
        if self.is_fullscreen:
            try:
                self.attributes("-fullscreen", True)
            except Exception:
                try:
                    self.state("zoomed")
                except Exception:
                    pass

        # Standard Window Exit Confirmation
        self.protocol("WM_DELETE_WINDOW", self.confirm_exit_dialog)

        # Setup UI Layout
        self._build_header()
        self._build_footer()
        self._build_main_layout()
        self._jobs = BackgroundJobs()
        if self.inference_worker is None:
            self.inference_worker = InferenceWorker(self.engine)
            self.inference_worker.start()
        self.realtime_detector = RealtimeDetectionWorker(self.camera, self.inference_worker)
        self.realtime_detector.start()

        # Keyboard Accelerators & Operator Hotkeys
        self.bind("<space>", self._scan_shortcut)
        self.bind("r", self._stop_shortcut)
        self.bind("R", self._stop_shortcut)
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
        self._drain_operation_events()
        self._set_operation_state(OperatorState.READY, "READY — USE CONFIG TO PREPARE THE SORTING STATION")

        # Auto-start operation if invoked with startup configuration
        if startup_config is not None:
            self.after(500, self._auto_start_from_config)


    def _drain_operation_events(self):
        if self._closing:
            return
        try:
            self._jobs.drain()
            self._drain_predictions()
            self._poll_station()
            for _ in range(16):
                try:
                    callback = self._ui_events.get_nowait()
                except queue.Empty:
                    break
                callback()
        except Exception as exc:
            self._log("[UI ERROR] " + str(exc))
        finally:
            if not self._closing:
                self.after(30, self._drain_operation_events)

    def shutdown(self):
        """Wait asynchronously for queued commits/cleanup before destroying Tk."""
        if self._closing:
            return
        if getattr(self, "_dialog_build_depth", 0):
            self.after(50, self.shutdown)
            return
        self.stop_or_cancel_session()
        self._closing = True
        self._operation_generation += 1
        done = threading.Event()
        deadline = time.monotonic() + 5.0
        def cleanup():
            try:
                for resource in (getattr(self, "station", None), getattr(self, "realtime_detector", None), self.inference_worker,
                                 self.chamber, self.iot, self.sync_worker, self.camera):
                    if resource:
                        try:
                            resource.stop()
                        except Exception as exc:
                            print(f"[SHUTDOWN WARNING] {type(resource).__name__}: {exc}")
            finally:
                self._jobs.close()
                done.set()
        try:
            self._jobs.submit(cleanup, lambda _: None, lambda _: None)
        except (queue.Full, RuntimeError):
            threading.Thread(target=cleanup, daemon=True).start()
        def poll():
            try:
                self._jobs.drain()
            except Exception as exc:
                print("[SHUTDOWN WARNING] Completion callback failed: " + str(exc))
            if done.is_set() or time.monotonic() >= deadline:
                if not done.is_set():
                    print("[SHUTDOWN WARNING] Worker cleanup timed out; interrupted sessions require review.")
                if self._finalization_failed:
                    print("[SHUTDOWN WARNING] Local session was not finalized; reconciliation required.")
                self.destroy()
            else:
                self.after(50, poll)
        self.after(50, poll)


    def _export_report(self, work, label):
        def saved(path):
            self._log("[EXPORT] CSV saved: " + path)
            if label.winfo_exists():
                label.configure(text="Saved: " + os.path.basename(path),
                                text_color=FUTheme.FERTILE_GREEN_TEXT)
        def failed(message):
            self._log("[EXPORT ERROR] " + message)
            if label.winfo_exists():
                label.configure(text="Export failed: " + message,
                                text_color=FUTheme.REJECT_RED_TEXT)
        try:
            self._jobs.submit(work, saved, failed)
        except (queue.Full, RuntimeError) as exc:
            failed(str(exc))

    def _scan_shortcut(self, event):
        # Typing in a dialog or editable field must never start a scan.
        if event.widget.winfo_toplevel() is not self or self.grab_current() is not None:
            return
        if isinstance(event.widget, (tk.Entry, tk.Text, tk.Spinbox)):
            return
        self.trigger_candling_scan()
        return "break"

    def _stop_shortcut(self, event):
        if event.widget.winfo_toplevel() is not self or isinstance(event.widget, (tk.Entry, tk.Text, tk.Spinbox)):
            return
        self.trigger_manual_eject()
        return "break"

    def _set_operation_state(self, state, message):
        self._operator_state = state
        color = (FUTheme.INFERTILE_AMBER if state in
                 {OperatorState.REVIEW, OperatorState.ERROR, OperatorState.RECOVERY}
                 else FUTheme.TEXT_MUTED)
        self._update_cycle_hud("●", color, message)
        self._set_session_active_state(self.is_session_active or self._scan_busy or self._stopping)

    def _drain_predictions(self):
        try:
            result = self.inference_worker.result_queue.get_nowait()
        except queue.Empty:
            return
        pending = self._pending_prediction
        if pending is None or result.get("request_id") != pending["id"]:
            return
        self._pending_prediction = None
        self._inference_request_id = None
        if pending["generation"] != self._operation_generation or self._closing or self._stopping:
            return
        if time.monotonic() >= pending["deadline"]:
            self._scan_failed("Inference timed out; result discarded.", OperatorState.REVIEW)
            return
        self._process_scan_result(result)

    def _scan_failed(self, message, state=OperatorState.ERROR):
        self._scan_busy = False
        self._latest_detections = []
        detector = getattr(self, "realtime_detector", None)
        if detector:
            detector.resume()
        self.result_title.configure(text="No scan recorded")
        self.result_badge.configure(text=state.value)
        self.result_subtitle.configure(text=message)
        self._set_operation_state(state, message)
        self._log("[" + state.value + "] " + message)

    def _build_header(self):
        self.header_frame = ctk.CTkFrame(
            self, fg_color=FUTheme.PANEL_LIGHT, corner_radius=0, height=64,
            border_width=1, border_color=FUTheme.BORDER
        )
        self.header_frame.pack(side="top", fill="x")

        navigation = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        navigation.pack(fill="x")

        # Left: University & Project Brand
        brand_container = ctk.CTkFrame(navigation, fg_color="transparent")
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
            font=(FUTheme.FONT_FAMILY, FUTheme.FONT_HEADING, "bold"), text_color=FUTheme.TEXT_PRIMARY
        )
        title.pack(anchor="w")

        subtitle = ctk.CTkLabel(
            title_box, text="Foundation University • Team DevIn",
            font=(FUTheme.FONT_FAMILY, 12), text_color=FUTheme.TEXT_MUTED
        )
        subtitle.pack(anchor="w")

        # Center: Interactive Active Batch Setup Button with High Contrast
        self.batch_btn = ctk.CTkButton(
            navigation,
            text=f"Batch: {self.current_batch_id}  ({self.current_stage})  ▾",
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
            navigation,
            text="Guide [F1]", width=100,
            font=(FUTheme.FONT_FAMILY, 12, "bold"),
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
            navigation,
            text="Windowed [F11]" if self.is_fullscreen else "Kiosk [F11]", width=128,
            font=(FUTheme.FONT_FAMILY, 12, "bold"),
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
        right_container.pack(fill="x", padx=18, pady=(0, 8))

        self.fps_label = ctk.CTkLabel(
            right_container, text="FPS: 0.0", font=(FUTheme.FONT_FAMILY, 12, "bold"), text_color=FUTheme.TEXT_MUTED
        )
        self.fps_label.pack(side="right", padx=8)

        self.iot_status_badge = ctk.CTkLabel(
            right_container, text="ESP32: STANDBY", fg_color=FUTheme.PANEL_LIGHT_ALT,
            text_color=FUTheme.TEXT_SECONDARY, font=(FUTheme.FONT_FAMILY, 12, "bold"),
            corner_radius=4, padx=8, pady=3
        )
        self.iot_status_badge.pack(side="left", padx=4)

        self.net_status_badge = ctk.CTkLabel(
            right_container, text="SYNC: ONLINE", fg_color=FUTheme.FERTILE_GREEN_BG,
            text_color=FUTheme.FERTILE_GREEN_TEXT, font=(FUTheme.FONT_FAMILY, 12, "bold"),
            corner_radius=4, padx=8, pady=3
        )
        self.net_status_badge.pack(side="left", padx=4)

    def _center_window(self, dialog, width: int, height: int):
        """Center modal dialog relative to root window and clamp to screen bounds."""
        self.update_idletasks()
        rx = self.winfo_x()
        ry = self.winfo_y()
        rw = max(width, self.winfo_width())
        rh = max(height, self.winfo_height())

        # Clamp dimensions to prevent modal overflowing lower-res screens / Raspberry Pi touchscreens
        target_w = min(width, max(320, self.winfo_width() - 24))
        target_h = min(height, max(300, self.winfo_height() - 32))

        x = rx + max(0, (rw - target_w) // 2)
        y = ry + max(0, (rh - target_h) // 2)
        dialog.geometry(f"{target_w}x{target_h}+{x}+{y}")
        dialog.minsize(min(target_w, 360), min(target_h, 280))
        self._animate_modal_open(dialog)

    def _animate_modal_open(self, dialog, duration_ms: int = 150):
        """Smooth alpha fade-in for CustomTkinter dialogs."""
        try:
            dialog.attributes("-alpha", 0.0)
            steps = 6
            step_time = max(15, duration_ms // steps)
            for i in range(1, steps + 1):
                alpha = i / steps
                dialog.after(i * step_time, lambda a=alpha: dialog.winfo_exists() and dialog.attributes("-alpha", a))
        except Exception:
            pass

    def _animate_modal_close(self, dialog, on_close=None, duration_ms: int = 140):
        """Smooth alpha fade-out before destroying dialog."""
        try:
            steps = 5
            step_time = max(15, duration_ms // steps)
            for i in range(steps):
                alpha = 1.0 - (i / steps)
                dialog.after(i * step_time, lambda a=alpha: dialog.winfo_exists() and dialog.attributes("-alpha", a))

            def finalize():
                if on_close:
                    try:
                        on_close()
                    except Exception:
                        pass
                if dialog.winfo_exists():
                    dialog.destroy()

            dialog.after(duration_ms, finalize)
        except Exception:
            if on_close:
                on_close()
            if dialog.winfo_exists():
                dialog.destroy()

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
        self.cycle_hud = ctk.CTkFrame(self.left_panel, fg_color=FUTheme.PANEL_LIGHT_ALT, height=60, corner_radius=8)
        self.cycle_hud.pack(fill="x", padx=10, pady=(10, 6))
        self.cycle_hud.pack_propagate(False)

        self.cycle_status_dot = ctk.CTkLabel(
            self.cycle_hud, text="●", font=(FUTheme.FONT_FAMILY, 14, "bold"), text_color=FUTheme.TEXT_MUTED
        )
        self.cycle_status_dot.pack(side="left", padx=(12, 6))

        self.cycle_status_label = ctk.CTkLabel(
            self.cycle_hud, text="Conveyor standby — validate the station in Settings",
            font=(FUTheme.FONT_FAMILY, 13, "bold"), text_color=FUTheme.TEXT_PRIMARY
        )
        self.cycle_status_label.configure(wraplength=340, justify="left", anchor="w")
        self.cycle_status_label.pack(side="left", fill="both", expand=True, padx=(0, 8))

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

        # Right column leaves enough room for the viewport at 1024px.
        self.right_panel = ctk.CTkFrame(self.main_container, fg_color=FUTheme.PANEL_LIGHT, width=400,
                                       corner_radius=12, border_width=1, border_color=FUTheme.BORDER)
        self.right_panel.pack(side="right", fill="both", padx=(0, 0))
        self.right_panel.pack_propagate(False)

        # 1. Classification Result Banner (High Contrast Card)
        self.result_banner = ctk.CTkFrame(
            self.right_panel, fg_color="transparent", corner_radius=0, height=118,
            border_width=0, border_color=FUTheme.BORDER
        )
        self.result_banner.pack(fill="x", padx=8, pady=(8, 6))
        ctk.CTkFrame(self.right_panel, height=1, corner_radius=0, fg_color=FUTheme.BORDER).pack(fill="x", padx=16)
        self.result_banner.pack_propagate(False)

        top_banner_row = ctk.CTkFrame(self.result_banner, fg_color="transparent")
        top_banner_row.pack(fill="x", padx=16, pady=(14, 2))

        self.result_badge = ctk.CTkLabel(
            top_banner_row, text="STANDBY", font=(FUTheme.FONT_FAMILY, 12, "bold"),
            fg_color=FUTheme.PANEL_LIGHT_ALT, text_color=FUTheme.TEXT_MUTED,
            corner_radius=4, padx=8, pady=2
        )
        self.result_badge.pack(side="left")

        self.latency_label = ctk.CTkLabel(
            top_banner_row, text="Latency: -- ms", font=(FUTheme.FONT_FAMILY, 12, "bold"), text_color=FUTheme.TEXT_DIM
        )
        self.latency_label.pack(side="right")

        self.result_title = ctk.CTkLabel(
            self.result_banner, text="Ready for Manual Diagnostics",
            font=(FUTheme.FONT_FAMILY, 18, "bold"), text_color=FUTheme.TEXT_PRIMARY
        )
        self.result_title.configure(wraplength=360, justify="left", font=(FUTheme.FONT_FAMILY, 17, "bold"))
        self.result_title.pack(anchor="w", padx=16, pady=(2, 1))

        self.result_subtitle = ctk.CTkLabel(
            self.result_banner, text="Single Scan checks the camera; Settings prepares automatic sorting",
            font=(FUTheme.FONT_FAMILY, 13), text_color=FUTheme.TEXT_MUTED
        )
        self.result_subtitle.configure(wraplength=360, justify="left")
        self.result_subtitle.pack(anchor="w", padx=16)

        # 2. Live Batch Counters & Progress Panel
        counters_frame = ctk.CTkFrame(
            self.right_panel, fg_color="transparent", corner_radius=0, border_width=0
        )
        counters_frame.pack(fill="x", pady=(0, 10))

        c_header = ctk.CTkFrame(counters_frame, fg_color="transparent")
        c_header.pack(fill="x", padx=16, pady=(8, 4))

        c_title = ctk.CTkLabel(
            c_header, text="Batch progress", height=22, font=(FUTheme.FONT_FAMILY, 13, "bold"),
            text_color=FUTheme.TEXT_PRIMARY
        )
        c_title.pack(side="left")

        self.progress_pct_label = ctk.CTkLabel(
            c_header, text="0.0%", height=22, font=(FUTheme.FONT_FAMILY, 12, "bold"),
            text_color=FUTheme.TEXT_PRIMARY
        )
        self.progress_pct_label.pack(side="right")

        # Throughput Speedometer & Remaining ETA
        self.speed_eta_label = ctk.CTkLabel(
            c_header, text="", height=22, font=(FUTheme.FONT_FAMILY, 12, "bold"),
            text_color=FUTheme.TEXT_MUTED
        )
        self.speed_eta_label.pack(side="left", padx=(12, 0))

        # Progress Bar
        self.progress_bar = ctk.CTkProgressBar(
            counters_frame, height=7, corner_radius=4, fg_color=FUTheme.PANEL_LIGHT_ALT,
            progress_color=FUTheme.PRIMARY_MAROON
        )
        self.progress_bar.pack(fill="x", padx=16, pady=(0, 10))
        self.progress_bar.set(0.0)

        grid = ctk.CTkFrame(counters_frame, fg_color="transparent")
        grid.pack(fill="x", padx=10, pady=(0, 8))

        # Aligned count rows keep the record readable without decorative tiles.
        self.box_total = self._create_count_row(grid, "Scanned", f"0 / {self.target_egg_count}", 0, FUTheme.TEXT_PRIMARY)
        self.box_fertile = self._create_count_row(grid, "Fertile / accept", "0 (0%)", 1, FUTheme.FERTILE_GREEN_TEXT)
        self.box_infertile = self._create_count_row(grid, "Infertile / penoy", "0", 2, FUTheme.INFERTILE_AMBER_TEXT)
        self.box_review = self._create_count_row(grid, "Manual review", "0", 3, FUTheme.TEXT_PRIMARY)

        ctk.CTkFrame(self.right_panel, height=1, corner_radius=0, fg_color=FUTheme.BORDER).pack(fill="x", padx=16)

        # 3. Recent Scans Log
        log_frame = ctk.CTkFrame(
            self.right_panel, fg_color="transparent", corner_radius=0, border_width=0
        )
        log_frame.pack(fill="both", expand=True)

        log_header = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_header.pack(fill="x", padx=16, pady=(10, 4))

        log_title = ctk.CTkLabel(
            log_header, text="Recent activity", font=(FUTheme.FONT_FAMILY, 13, "bold"),
            text_color=FUTheme.TEXT_PRIMARY
        )
        log_title.pack(side="left")

        self.history_btn = ctk.CTkButton(
            log_header, text="History [S]", font=(FUTheme.FONT_FAMILY, 12, "bold"),
            fg_color=FUTheme.PANEL_LIGHT_ALT, hover_color=FUTheme.PANEL_ACCENT,
            border_width=1, border_color=FUTheme.BORDER,
            text_color=FUTheme.TEXT_SECONDARY, command=self.open_scan_history_modal,
            height=24, width=110, corner_radius=6
        )
        self.history_btn.pack(side="right")

        # Compact Live Scans List Box
        self.log_textbox = ctk.CTkTextbox(
            log_frame, fg_color=FUTheme.PANEL_LIGHT, font=(FUTheme.FONT_FAMILY, 13),
            text_color=FUTheme.TEXT_SECONDARY, corner_radius=8,
            border_width=0
        )
        self.log_textbox.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        self.log_textbox.configure(state="disabled")

    def _render_standby_hud(self):
        """Explain camera setup directly in the idle viewport."""
        for child in self.standby_frame.winfo_children():
            child.destroy()

        # The camera well is the empty-state surface; no nested floating card.
        ctk.CTkLabel(self.standby_frame, text="Camera on standby",
                     font=(FUTheme.FONT_FAMILY, 22, "bold"),
                     text_color=FUTheme.TEXT_PRIMARY).pack(padx=24, pady=(16, 8))
        ctk.CTkLabel(self.standby_frame, text="Open Settings to prepare the camera\nand validate the sorting station.",
                     font=(FUTheme.FONT_FAMILY, 14), text_color=FUTheme.TEXT_SECONDARY,
                     justify="center").pack(padx=24, pady=(0, 16))
        ctk.CTkLabel(self.standby_frame, text="SPACE  Single scan     F1  Operator guide",
                     font=(FUTheme.FONT_FAMILY, 12), text_color=FUTheme.TEXT_MUTED).pack(padx=20, pady=(0, 16))

    def _create_count_row(self, parent, label_text: str, value_text: str, row: int, color: str):
        parent.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(parent, text=label_text, anchor="w",
                     font=(FUTheme.FONT_FAMILY, 14), text_color=FUTheme.TEXT_SECONDARY).grid(
                         row=row, column=0, sticky="w", padx=6, pady=1)
        value = ctk.CTkLabel(parent, text=value_text, anchor="e",
                             font=(FUTheme.FONT_FAMILY, 20, "bold"), text_color=color)
        value.grid(row=row, column=1, sticky="e", padx=6, pady=1)
        return value

    def _build_footer(self):
        self.station_strip = ctk.CTkFrame(self, fg_color=FUTheme.PANEL_LIGHT, corner_radius=0)
        self.station_strip.pack(side="bottom", fill="x")
        self.station_status = ctk.CTkLabel(self.station_strip, text="Boards disconnected | Camera idle", anchor="w", wraplength=950, justify="left", font=(FUTheme.FONT_FAMILY, 13), text_color=FUTheme.TEXT_SECONDARY)
        self.station_status.pack(fill="x", padx=16, pady=(8, 4))
        review_row = self.review_row = ctk.CTkFrame(self.station_strip, fg_color="transparent")
        ctk.CTkLabel(review_row, text="Operator review", font=(FUTheme.FONT_FAMILY, 12), text_color=FUTheme.TEXT_MUTED).pack(side="left", padx=4)
        self.review_buttons = []
        for label, classification in (("Confirm fertile", "FERTILE"), ("Confirm infertile", "INFERTILE"), ("Confirm empty", "EMPTY")):
            button = ctk.CTkButton(review_row, text=label, width=145, height=34, font=(FUTheme.FONT_FAMILY, 13, "bold"), state="disabled",
                fg_color=FUTheme.PRIMARY_MAROON, command=lambda c=classification: self._resolve_station_review(c))
            button.pack(side="right", padx=4, pady=4)
            self.review_buttons.append(button)
        self.footer_frame = ctk.CTkFrame(
            self, fg_color=FUTheme.PANEL_LIGHT, corner_radius=0, height=68,
            border_width=1, border_color=FUTheme.BORDER
        )
        self.footer_frame.pack(side="bottom", fill="x")

        # Automated Cycle Button (Starts Camera & Sorting Loop)
        self.session_btn = ctk.CTkButton(
            self.footer_frame, text="Start sorting", font=(FUTheme.FONT_FAMILY, 13, "bold"),
            fg_color=FUTheme.PRIMARY_MAROON, hover_color=FUTheme.HOVER_MAROON,
            text_color=FUTheme.TEXT_WHITE, command=self.toggle_auto_session,
            width=155, height=44, corner_radius=8
        )
        self.session_btn.pack(side="left", padx=(14, 6), pady=13)

        # Single Trigger Scan Button (Manual Override)
        self.scan_btn = ctk.CTkButton(
            self.footer_frame, text="Single Scan [SPACE]", font=(FUTheme.FONT_FAMILY, 14, "bold"),
            fg_color=FUTheme.PANEL_LIGHT_ALT, hover_color=FUTheme.PANEL_ACCENT,
            border_width=1, border_color=FUTheme.BORDER_DARK,
            text_color=FUTheme.TEXT_PRIMARY, command=self.trigger_candling_scan,
            width=160, height=44, corner_radius=8
        )
        self.scan_btn.pack(side="left", padx=6, pady=13)

        # Dedicated Terminate / Cancel / End Session Button (hidden in Standby, visible when active)
        self.cancel_btn = ctk.CTkButton(
            self.footer_frame, text="End Session [ESC]", font=(FUTheme.FONT_FAMILY, 14, "bold"),
            fg_color=FUTheme.PANEL_LIGHT_ALT, hover_color=FUTheme.REJECT_RED_BG,
            border_width=1, border_color=FUTheme.BORDER_DARK,
            text_color=FUTheme.TEXT_PRIMARY, command=self.open_end_session_modal,
            width=155, height=44, corner_radius=8
        )
        # Note: Packed dynamically when a session/camera is started

        # Manual Eject Button with High-Contrast Luminous Text
        self.eject_btn = ctk.CTkButton(
            self.footer_frame, text="STOP [R]", font=(FUTheme.FONT_FAMILY, 14, "bold"),
            fg_color=FUTheme.REJECT_RED, hover_color=FUTheme.REJECT_RED_HOVER,
            border_width=1, border_color=FUTheme.REJECT_RED_BORDER,
            text_color=FUTheme.TEXT_WHITE, command=self.trigger_manual_eject,
            width=100, height=44, corner_radius=8
        )
        self.eject_btn.pack(side="left", padx=6, pady=13)

        # Batch Setup Quick Button
        self.batch_setup_btn = ctk.CTkButton(
            self.footer_frame, text="Batch setup", font=(FUTheme.FONT_FAMILY, 14, "bold"),
            fg_color=FUTheme.PANEL_LIGHT_ALT, hover_color=FUTheme.PANEL_ACCENT,
            border_width=1, border_color=FUTheme.BORDER_DARK,
            text_color=FUTheme.TEXT_PRIMARY, command=self.open_batch_setup_dialog,
            width=110, height=44, corner_radius=8
        )
        self.batch_setup_btn.pack(side="right", padx=(6, 14), pady=13)

        # Conveyor Settings Button
        self.settings_btn = ctk.CTkButton(
            self.footer_frame, text="Settings", font=(FUTheme.FONT_FAMILY, 14),
            fg_color=FUTheme.PANEL_LIGHT_ALT, border_width=1, border_color=FUTheme.BORDER,
            text_color=FUTheme.TEXT_SECONDARY, hover_color=FUTheme.PANEL_ACCENT,
            command=self.open_calibration_dialog, width=100, height=42, corner_radius=8
        )
        self.settings_btn.pack(side="right", padx=6, pady=13)

    def _set_session_active_state(self, is_active: bool):
        """Refresh controls from pending work and local session identity."""
        is_active = is_active or self.current_session_id is not None
        station = getattr(self, "station", None)
        cycle = station.cycle if station is not None else None
        signature = (is_active, self.current_session_id, self.is_auto_cycle_running,
                     self._scan_busy, self._stopping, self._closing,
                     self._pending_finalization_id, self._finalization_failed,
                     bool(self.inference_worker.busy), self._diagnostics_complete,
                     cycle.session_id if cycle is not None else None)
        if signature == getattr(self, "_controls_signature", None):
            return
        self._controls_signature = signature
        if is_active:
            # Reveal cancel buttons dynamically when active
            self.cancel_btn.pack(side="left", padx=6, pady=13, after=self.scan_btn)
            if self.is_auto_cycle_running:
                self.session_btn.configure(
                    text="Stop sorting", fg_color=FUTheme.REJECT_RED,
                    hover_color=FUTheme.REJECT_RED_HOVER
                )
        else:
            # Hide cancel buttons when in standby
            self.cancel_btn.pack_forget()
            self.session_btn.configure(
                text="Start sorting", fg_color=FUTheme.PRIMARY_MAROON,
                hover_color=FUTheme.HOVER_MAROON
            )
        blocked = self._pending_finalization_id is not None or self._finalization_failed
        state = "disabled" if is_active or self._scan_busy or self._stopping or blocked else "normal"
        self.batch_setup_btn.configure(state=state)
        self.settings_btn.configure(state=state)
        station = getattr(self, "station", None)
        automatic_session = station is not None and station.cycle is not None and self.current_session_id == station.cycle.session_id
        busy = self._scan_busy or self._stopping or self._closing or self.inference_worker.busy or self.is_auto_cycle_running or automatic_session
        self.session_btn.configure(state="disabled" if self._scan_busy or self._stopping or blocked or (is_active and not self.is_auto_cycle_running) else "normal")
        self.scan_btn.configure(state="disabled" if busy or blocked or self._diagnostics_complete else "normal",
                                text="Working…" if self._scan_busy else "Single Scan [SPACE]")
        self.cancel_btn.configure(state="disabled" if self._stopping else "normal",
                                  text="Retry Finalization" if blocked else "End Session [ESC]")
        if blocked:
            self.cancel_btn.pack(side="left", padx=6, pady=13, after=self.scan_btn)

    @_building_dialog
    def open_end_session_modal(self, event=None):
        """Interactive End Session modal with run summary statistics and direct CSV export."""
        if self._pending_finalization_id or self._finalization_failed:
            self.stop_or_cancel_session()
            return
        if self._scan_busy or self._stopping:
            self.stop_or_cancel_session()
            return
        # If no scans recorded and camera is idle, instantly stop without prompt
        if self.total_count == 0 and not self.is_auto_cycle_running and not self.camera.is_running:
            self.stop_or_cancel_session()
            return

        # If automated conveyor is currently moving, pause conveyor motor while modal is open
        was_auto_running = self.is_auto_cycle_running
        if was_auto_running:
            self.chamber.stop() if self.chamber else None

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

        pct = (self.fertile_count / max(1, self.fertile_count + self.infertile_count)) * 100.0 if self.total_count > 0 else 0.0
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

        # Tile 4: Manual review fallback
        t4 = ctk.CTkFrame(grid, fg_color=FUTheme.PANEL_LIGHT_ALT, corner_radius=8, border_width=1, border_color=FUTheme.BORDER)
        t4.grid(row=1, column=1, padx=4, pady=4, sticky="nsew")
        ctk.CTkLabel(t4, text="MANUAL REVIEW", font=(FUTheme.FONT_FAMILY, 9, "bold"), text_color=FUTheme.TEXT_MUTED).pack(anchor="w", padx=10, pady=(6, 0))
        ctk.CTkLabel(t4, text=f"{self.review_count} Eggs", font=(FUTheme.FONT_FAMILY, 15, "bold"), text_color=FUTheme.TEXT_PRIMARY).pack(anchor="w", padx=10, pady=(0, 6))

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
            session_id = self.current_session_id or getattr(self, "_last_session_id", None)
            if not session_id:
                status_msg.configure(text="No recorded session to export.")
                return
            self._export_report(lambda: self.db.export_session_csv(session_id), status_msg)

        ctk.CTkButton(
            export_box, text="📄 Export Records directly into CSV", fg_color=FUTheme.PRIMARY_MAROON,
            hover_color=FUTheme.HOVER_MAROON, text_color=FUTheme.TEXT_WHITE, font=(FUTheme.FONT_FAMILY, 12, "bold"),
            command=export_csv, height=36, corner_radius=8
        ).pack(fill="x", padx=14, pady=(0, 10))

        # Bottom Actions Row
        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 10))

        def confirm_end():
            self._animate_modal_close(
                dialog,
                on_close=lambda: (
                    self.stop_or_cancel_session(),
                    self._log(f"[OK] Session ended with {self.total_count} records saved.")
                )
            )

        def resume():
            def do_resume():
                if was_auto_running and self.is_auto_cycle_running:
                    self._log("[BLOCKED] Sorting cannot resume before station validation.")
                    self._log("[INFO] Session resumed.")
            self._animate_modal_close(dialog, on_close=do_resume)

        ctk.CTkButton(
            btn_row, text="⏹ Confirm & End Session", fg_color=FUTheme.REJECT_RED_BG,
            hover_color=FUTheme.REJECT_RED_HOVER, border_width=1, border_color=FUTheme.REJECT_RED_BORDER,
            text_color=FUTheme.REJECT_RED_TEXT, font=(FUTheme.FONT_FAMILY, 12, "bold"),
            command=confirm_end, height=40, corner_radius=8
        ).pack(side="left", fill="x", expand=True, padx=(0, 8))

        ctk.CTkButton(
            btn_row, text="↩ Resume Session", fg_color=FUTheme.PANEL_LIGHT_ALT,
            hover_color=FUTheme.PANEL_ACCENT, border_width=1, border_color=FUTheme.BORDER,
            text_color=FUTheme.TEXT_PRIMARY, font=(FUTheme.FONT_FAMILY, 12),
            command=resume, height=40, corner_radius=8, width=140
        ).pack(side="right")

    def stop_or_cancel_session(self):
        """Keep failed finalization retryable; cancel predictions independently of storage."""
        if self._stopping:
            return
        station = getattr(self, "station", None)
        if station and station.active:
            station.halt()
        self._operation_generation += 1
        self._pending_prediction = self._inference_request_id = None
        self._scan_busy = False
        self._stopping = True
        self._stop_cycle_event.set()
        if self.chamber:
            self.chamber.stop()
        self.is_auto_cycle_running = False
        self.is_session_active = False

        # 1. Immediately turn off camera capture to stop preview stream
        try:
            request_stop = getattr(self.camera, "request_stop", None)
            if callable(request_stop):
                request_stop()
            else:
                self.camera.stop()
        except Exception:
            pass

        # 2. Immediately pause & clear real-time detector and tracker
        detector = getattr(self, "realtime_detector", None)
        if detector:
            detector.pause()
            if hasattr(detector, "clear"):
                detector.clear()

        # 3. Immediately clear all detections and blank out the camera preview
        self._latest_detections = []
        self._last_scan_result_time = 0.0
        self._current_photo = None
        try:
            self.video_label.configure(image="")
        except Exception:
            pass

        # 4. Display the Standby HUD cleanly over the dark viewport
        self._render_standby_hud()
        self.standby_frame.place(relx=0.5, rely=0.5, anchor="center")

        session_id = self._pending_finalization_id or self.current_session_id
        self._pending_finalization_id = session_id
        self._set_operation_state(OperatorState.STOPPING, "STOPPING - FINALIZING LOCAL RECORDS")

        def finish():
            if callable(getattr(self.camera, "request_stop", None)):
                self.camera.stop()
            if station and station.cycle and station.cycle.active:
                station.cycle._thread.join(timeout=5)
                if station.cycle.active:
                    raise RuntimeError("Sorting worker is still stopping; retry finalization")
            # Cancellation before the first queued write can legitimately leave
            # no local session. A database read error still enters recovery.
            if session_id and self.db.get_session_stats(session_id):
                return self.db.complete_session(session_id)
            return {}

        def finished(stats):
            self._stopping = False
            if session_id and stats:
                self._last_session_id = session_id
                # Recover counts even if Stop invalidated the UI callback of a
                # scan that had already committed to SQLite.
                self.total_count = stats["total_scanned"]
                self.fertile_count = stats["fertile_count"]
                self.infertile_count = stats["infertile_count"]
                self.review_count = stats["manual_review_count"]
                self._update_counters_ui()
            self.current_session_id = self._pending_finalization_id = None
            self._finalization_failed = False
            self._session_start_time = None
            self._set_operation_state(OperatorState.COMPLETE if self._diagnostics_complete else OperatorState.READY,
                                      "DIAGNOSTIC TARGET REACHED" if self._diagnostics_complete else "STOPPED - LOCAL RECORDS FINALIZED")
            automatic = station is not None and station.cycle is not None and station.cycle.session_id == session_id
            self._log("[STOPPED] " + ("Local session finalized." if stats else "No pending local session.")
                      + (" Gate passage is timed; inspect the output trays." if automatic else " Physical sorting was not performed."))
            if self._diagnostics_complete and not self._closing and self.grab_current() is None:
                self.after(0, self.open_batch_completion_modal)

        def failed(error):
            self._stopping = False
            self._finalization_failed = True
            # Preserve identity so Retry cannot abandon an unfinished session.
            self._set_operation_state(OperatorState.RECOVERY, "FINALIZATION FAILED - RETRY END SESSION")
            self._log("[STORAGE ERROR] Session finalization failed: " + error)
        try:
            self._jobs.submit(finish, finished, failed)
        except (queue.Full, RuntimeError) as exc:
            failed(str(exc))

    def _stop_auto_cycle(self):
        """Helper to cleanly stop automated cycle loop."""
        self.stop_or_cancel_session()

    def _resolve_station_review(self, classification):
        if self.station and self.station.cycle:
            try:
                self.station.cycle.resolve_review(classification)
                for button in self.review_buttons:
                    button.configure(state="disabled")
            except ValueError as exc:
                self._log("[REVIEW] " + str(exc))

    def _poll_station(self):
        station = getattr(self, "station", None)
        if station is None:
            return
        now = time.monotonic()
        self._ui_tick_ms = (now - getattr(self, "_last_station_poll", now)) * 1000
        self._last_station_poll = now
        boards = station.boards
        parts = []
        if boards:
            for link in (boards.conveyor, boards.servo):
                state = link.snapshot()
                status = state.error or state.telemetry.get("FAULT", "identifying")
                parts.append(f"{link.role}: {status if state.connected else 'disconnected'}")
            parts.append("IR: " + boards.conveyor.snapshot().telemetry.get("IR_ACTIVE", "unknown"))
        else:
            parts.append("Boards disconnected")
        parts.append("Camera: " + (self.camera.last_error or ("ready" if self.camera.is_running else "idle")))
        label = " | ".join(parts)
        if label != getattr(self, "_last_station_label", None):
            self.station_status.configure(text=label)
            self._last_station_label = label
        cycle = station.cycle
        if cycle is None:
            return
        status = cycle.status
        result = cycle.latest_result
        if result and result["scan_id"] != getattr(self, "_last_station_scan", None):
            self._last_station_scan = result["scan_id"]
            self._update_result_banner(result["final_class"], result["confidence"], result["routing_action"], result.get("inference_ms", 0))
            self.result_subtitle.configure(text=f"Holder {result['holder']} saved locally; routing is tracked and gate passage is timed.")
        key = (cycle.session_id, status["state"], status.get("holder"), status.get("reason"))
        if key != getattr(self, "_last_cycle_status", None):
            self._last_cycle_status = key
            message = f"{status['state']} | Holder {status.get('holder', 0)} | {status.get('reason', '')}"
            self._update_cycle_hud("●", FUTheme.INFERTILE_AMBER if status["state"] in {"MANUAL_REVIEW", "RECOVERY_REQUIRED"} else FUTheme.TEXT_PRIMARY, message)
            if status["state"] == "MANUAL_REVIEW":
                self.review_row.pack(fill="x", padx=12, pady=(0, 8))
            else:
                self.review_row.pack_forget()
            for button in self.review_buttons:
                button.configure(state="normal" if status["state"] == "MANUAL_REVIEW" else "disabled")
            self._log("[CYCLE] " + message)
        if self.current_session_id == cycle.session_id and not getattr(self, "_station_stats_pending", False) and now - getattr(self, "_station_stats_at", 0) >= .5:
            self._station_stats_at = now
            self._station_stats_pending = True
            session_id = cycle.session_id
            def updated(stats):
                self._station_stats_pending = False
                if self.current_session_id != session_id or not stats:
                    return
                self.total_count = self.scan_sequence = stats["total_scanned"]
                self.fertile_count, self.infertile_count, self.review_count = stats["fertile_count"], stats["infertile_count"], stats["manual_review_count"]
                self._update_counters_ui()
            def failed(message):
                self._station_stats_pending = False
                self._log("[STORAGE] " + message)
            try:
                self._jobs.submit(lambda: self.db.get_session_stats(session_id), updated, failed)
            except (queue.Full, RuntimeError) as exc:
                failed(str(exc))
        if status["state"] in {"COMPLETE", "RECOVERY_REQUIRED"} and not getattr(self, "_station_terminal_seen", False):
            self._station_terminal_seen = True
            self.is_auto_cycle_running = False
            if status["state"] == "COMPLETE":
                # Let End Session reconcile the final counters and release local identity.
                self._log(f"[COMPLETE] {cycle.count} saved scans; {cycle.routed} timed gate passages. End session to review totals.")
            else:
                self._log("[RECOVERY] Stop/finalize this session, inspect holders, then reconnect and validate setup.")
            self._set_session_active_state(True)

    def toggle_auto_session(self):
        """Only the inspected dual-board service can initiate physical motion."""
        if self.is_session_active or self.is_auto_cycle_running:
            self.stop_or_cancel_session()
            return
        if not self.station or self.simulation:
            self._log("[BLOCKED] Real camera and validated dual-board station required.")
            return
        if self.grab_current() is not None or self._scan_busy or self._stopping or self.current_session_id:
            self._log("[BLOCKED] Close settings and finish the current session first.")
            return
        try:
            validate_batch_config(self.current_batch_id, self.operator_name, self.target_egg_count, self.current_stage)
            cycle = self.station.start_cycle(self.current_batch_id, self.target_egg_count, self.operator_name)
        except Exception as exc:
            self._log("[BLOCKED] " + str(exc))
            return
        self.current_session_id = cycle.session_id
        self.is_session_active = self.is_auto_cycle_running = True
        self._station_terminal_seen = False
        self.realtime_detector.pause()
        self.total_count = self.fertile_count = self.infertile_count = self.review_count = self.scan_sequence = 0
        self._session_start_time = time.time()
        self._diagnostics_complete = False
        self.standby_frame.place_forget()
        self._log("[STARTED] Automatic holder tracking; scans are committed locally before advance.")
        self._set_session_active_state(True)

    def _auto_conveyor_cycle_loop(self):
        raise RuntimeError("The legacy timed conveyor cycle is disabled.")

    def _on_batch_target_complete(self):
        # A retired controller callback is not proof of completed physical work.
        if self.total_count < self.target_egg_count or self._diagnostics_complete:
            return
        self._diagnostics_complete = True
        self.stop_or_cancel_session()

    def _auto_start_from_config(self):
        self._log("[READY] Batch configuration loaded. No motion starts automatically.")
        if self.simulation:
            self._log("[SIMULATION] Preview only: no hardware commands or saved scans.")
        else:
            self._log("[READY] Use a manual camera scan to check classification. "
                      "Open Settings for both boards, camera defaults and station validation.")

    def _on_chamber_state_change(self, state: str, current: int, total: int):
        """ChamberController state callback — updates the cycle HUD (runs on main thread via after())."""
        hud_map = {
            ChamberState.MOTOR_ADVANCE:  ("🟢", FUTheme.FERTILE_GREEN,    f"CONVEYOR ADVANCING — EGG #{current} OF {total}", FUTheme.FERTILE_GREEN_CARD),
            ChamberState.STABILIZING:    ("🟡", FUTheme.INFERTILE_AMBER,  f"EGG #{current} IN CHAMBER — STABILIZING ({self.chamber_pause_ms}ms)", FUTheme.INFERTILE_AMBER_CARD),
            ChamberState.AI_SCAN:        ("🔵", FUTheme.PRIMARY_MAROON,   f"AI SCANNING EGG #{current}...", FUTheme.PRIMARY_MAROON_BG),
            ChamberState.DISPLAYING:     ("🔵", FUTheme.PRIMARY_MAROON,   f"RESULT DISPLAYED — EGG #{current}", FUTheme.PRIMARY_MAROON_BG),
            ChamberState.ACTUATING:      ("⚡", FUTheme.INFERTILE_AMBER,  f"ACTUATING SERVO — EGG #{current}", FUTheme.INFERTILE_AMBER_CARD),
            ChamberState.ADVANCE_NEXT:   ("🟢", FUTheme.FERTILE_GREEN,    f"EGG #{current} DONE — ADVANCING NEXT", FUTheme.FERTILE_GREEN_CARD),
            ChamberState.COMPLETE:       ("🏁", FUTheme.PRIMARY_MAROON,   "CONTROLLER FINISHED - VERIFY LOCAL RECORDS", FUTheme.PRIMARY_MAROON_BG),
            ChamberState.EMERGENCY_STOP: ("🔴", FUTheme.REJECT_RED,       "⚠ JAM DETECTED — CONVEYOR HALTED", FUTheme.REJECT_RED_BG),
            ChamberState.STANDBY:        ("●",  FUTheme.TEXT_MUTED,       "CONVEYOR STANDBY — SESSION IDLE", FUTheme.PANEL_LIGHT_ALT),
        }
        icon, color, text, bg = hud_map.get(state, ("●", FUTheme.TEXT_MUTED, state, FUTheme.PANEL_LIGHT_ALT))
        self._update_cycle_hud(icon, color, text, bg_color=bg)

    def _on_chamber_scan_result(self, result: dict):
        """ChamberController scan result callback — records to DB and updates UI (main thread)."""
        self._process_scan_result(result)

    def _on_batch_complete_callback(self, count: int):
        """ChamberController batch complete callback (main thread)."""
        self._on_batch_target_complete()

    def _on_jam_detected(self):
        """ChamberController jam timeout callback (main thread)."""
        self.is_auto_cycle_running = False
        self._log("[WARN] ⚠ JAM DETECTED: No egg arrived within 30 seconds. Conveyor halted.")
        self._show_jam_alert_modal()

    def _show_jam_alert_modal(self):
        """Show a jam alert modal prompting operator to check the conveyor."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("⚠ Conveyor Jam Detected")
        dialog.geometry("480x260")
        dialog.configure(fg_color=FUTheme.BG_LIGHT)
        dialog.transient(self)
        dialog.grab_set()
        self._center_window(dialog, 480, 260)

        card = ctk.CTkFrame(dialog, fg_color=FUTheme.PANEL_LIGHT, corner_radius=12, border_width=1, border_color=FUTheme.BORDER)
        card.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(card, text="⚠ Conveyor Jam Detected",
                     font=(FUTheme.FONT_FAMILY, 16, "bold"), text_color=FUTheme.REJECT_RED).pack(pady=(18, 6))
        ctk.CTkLabel(card,
                     text=f"No egg was detected in the candling chamber within 30 seconds.\nConveyor motor has been halted automatically.\n\nPlease check for physical obstructions, then restart the session.\n\nScans completed: {self.total_count} / {self.target_egg_count}",
                     font=(FUTheme.FONT_FAMILY, 11), text_color=FUTheme.TEXT_MUTED, justify="center").pack(pady=(0, 18))

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 12))

        def resume():
            self._animate_modal_close(dialog, on_close=self.toggle_auto_session)

        ctk.CTkButton(btn_row, text="↩ Resume Sorting", fg_color=FUTheme.PRIMARY_MAROON,
                      hover_color=FUTheme.HOVER_MAROON, text_color=FUTheme.TEXT_WHITE,
                      font=(FUTheme.FONT_FAMILY, 12, "bold"), command=resume, height=38, corner_radius=8
                      ).pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(btn_row, text="End Session", fg_color=FUTheme.PANEL_LIGHT_ALT,
                      hover_color=FUTheme.REJECT_RED_BG, border_width=1, border_color=FUTheme.BORDER,
                      text_color=FUTheme.TEXT_PRIMARY, font=(FUTheme.FONT_FAMILY, 11),
                      command=lambda: self._animate_modal_close(dialog, on_close=self.stop_or_cancel_session),
                      height=38, corner_radius=8, width=130).pack(side="right")

    def _update_cycle_hud(self, dot_icon: str, dot_color: str, status_text: str, bg_color: str = None):
        hud_bg = bg_color or FUTheme.PANEL_LIGHT_ALT
        signature = (dot_icon, dot_color, status_text, hud_bg)
        if signature == getattr(self, "_hud_signature", None):
            return
        self._hud_signature = signature
        self.cycle_hud.configure(fg_color=hud_bg)
        self.cycle_status_dot.configure(text=dot_icon, text_color=dot_color)
        self.cycle_status_label.configure(text=status_text, text_color=dot_color if dot_color != FUTheme.TEXT_MUTED else FUTheme.TEXT_PRIMARY)

    def _process_scan_result(self, result):
        """Persist a manual diagnostic scan on a worker; never actuate from a UI callback."""
        if self._closing or self._stopping:
            return
        final_cls = result.get("final_class")
        conf = result.get("confidence", 0.0)
        if (final_cls not in {"FERTILE", "INFERTILE"} or not isinstance(conf, (int, float))
                or not math.isfinite(conf) or not 0 <= conf <= 1 or not result.get("detections")):
            self._scan_failed("No trustworthy egg classification: "
                              + result.get("error_code", "EGG_NOT_CONFIRMED"), OperatorState.REVIEW)
            return
        action = "MANUAL_REVIEW" if conf < 0.75 else ("ACCEPT" if final_cls == "FERTILE" else "REJECT")
        latency = result.get("inference_ms", 0)
        if not isinstance(latency, int) or latency < 0:
            self._scan_failed("Invalid inference latency; scan was not saved.")
            return

        # Immediate real-time visual feedback
        self._latest_detections = result.get("detections", [])
        self._last_scan_result_time = time.monotonic()
        detector = getattr(self, "realtime_detector", None)
        if detector:
            detector.resume()

        if self.simulation or self.camera.is_mock_mode or not str(result.get("engine", "")).startswith("ONNX"):
            self._scan_busy = False
            self._update_result_banner(final_cls, conf, "PREVIEW_ONLY", latency)
            self._set_operation_state(OperatorState.READY, "PREVIEW ONLY - NO SCAN RECORDED")
            self._log("[PREVIEW] Simulated/fallback results are not saved or routed.")
            return
        generation = self._operation_generation
        new_session = self.current_session_id is None
        if new_session:
            self.scan_sequence = self.total_count = self.fertile_count = self.infertile_count = self.review_count = 0
        session_id = self.current_session_id or str(uuid.uuid4())
        self.current_session_id = session_id
        batch_id, sequence = self.current_batch_id, self.scan_sequence + 1
        device_id, stage, operator = self.device_id, self.current_stage, self.operator_name
        scan_id = str(uuid.uuid4())
        self._set_operation_state(OperatorState.SAVING, "SAVING SCAN - WAITING FOR LOCAL COMMIT")

        def work():
            if generation != self._operation_generation:
                return None
            if not self.db.get_session_stats(session_id):
                self.db.create_session(session_id, batch_id, device_id, stage, operator)
            if generation != self._operation_generation:
                return None
            return self.db.record_scan(scan_id, session_id, batch_id, sequence,
                                       final_cls, conf, latency, action, result["detections"])

        def saved(record):
            if generation != self._operation_generation or record is None:
                return
            self._scan_busy = False
            self.scan_sequence = sequence
            self.is_session_active = True
            self._session_start_time = self._session_start_time or time.time()
            self.total_count += 1
            if action == "MANUAL_REVIEW":
                self.review_count += 1
            elif final_cls == "FERTILE":
                self.fertile_count += 1
            else:
                self.infertile_count += 1
            self._latest_detections = result["detections"]
            self._last_scan_result_time = time.monotonic()
            self._set_session_active_state(True)
            self._update_counters_ui()
            self._update_result_banner(final_cls, conf, action, latency)
            self._log(f"#{sequence:03d} | {final_cls} | {conf:.1%} | {action} | saved locally; not physically routed")
            self._set_operation_state(OperatorState.REVIEW if action == "MANUAL_REVIEW" else OperatorState.READY,
                                      "SCAN SAVED - MANUAL REVIEW REQUIRED" if action == "MANUAL_REVIEW" else "SCAN SAVED - READY FOR NEXT DIAGNOSTIC")
            if self.total_count >= self.target_egg_count:
                self._diagnostics_complete = True
                self.stop_or_cancel_session()

        def failed(message):
            if generation != self._operation_generation:
                return
            # A session may have been created before record_scan failed. Reuse it
            # rather than creating the same session again on the next attempt.
            self._scan_failed("Scan was not recorded. Retry after resolving storage error: " + message)
        try:
            self._jobs.submit(work, saved, failed)
        except (queue.Full, RuntimeError) as exc:
            failed(str(exc))

    def trigger_candling_scan(self):
        """One click waits for a fresh camera frame, then starts bounded inference."""
        if self._closing or self._scan_busy or self._stopping or self.is_auto_cycle_running:
            return
        station = getattr(self, "station", None)
        if station and station.cycle and self.current_session_id == station.cycle.session_id:
            self._log("[BLOCKED] End the automatic session before starting manual diagnostics.")
            return
        if self._pending_finalization_id or self._finalization_failed:
            self._log("[BLOCKED] Retry session finalization before another scan.")
            return
        if self._diagnostics_complete:
            self._log("[COMPLETE] Diagnostic target reached. Configure a new batch to continue.")
            return
        if self.inference_worker.busy:
            self._log("[WAIT] Previous inference is still running; no additional scan queued.")
            return
        if self.grab_current() is not None:
            self._log("[BLOCKED] Close the dialog before scanning.")
            return
        self._scan_busy = True
        detector = getattr(self, "realtime_detector", None)
        if detector and detector.latest_detection:
            self._latest_detections = [detector.latest_detection]
            detector.pause()
        else:
            self._latest_detections = []
        self.result_title.configure(text="Waiting for a fresh camera frame")
        self.result_badge.configure(text="PENDING")
        self.result_subtitle.configure(text="No result recorded yet")
        self._set_operation_state(OperatorState.CAMERA_STARTING, "STARTING CAMERA - WAITING FOR FRESH FRAME")
        try:
            if not self.camera.is_running:
                self.camera.start()
            self.standby_frame.place_forget()
        except Exception as exc:
            self._scan_failed("Camera could not start: " + str(exc))
            return
        generation = self._operation_generation
        self._await_scan_frame(generation, time.monotonic() + 3.0)

    def _await_scan_frame(self, generation, deadline):
        if generation != self._operation_generation or self._closing or self._stopping:
            return
        if time.monotonic() >= deadline:
            self._scan_failed("Camera timed out. Check the camera, then retry Scan.")
            return
        if self.camera.last_error:
            self._scan_failed("Camera unavailable: " + self.camera.last_error)
            return
        frame = self.camera.get_latest_frame(copy=True)
        if frame is None:
            self.after(50, lambda: self._await_scan_frame(generation, deadline))
            return
        request_id = str(uuid.uuid4())
        self._pending_prediction = {"id": request_id, "generation": generation,
                                    "deadline": time.monotonic() + 2.0}
        self._inference_request_id = request_id
        self._set_operation_state(OperatorState.CLASSIFYING, "CLASSIFYING - NO RECORD SAVED YET")
        self.result_title.configure(text="Classifying camera snapshot")
        try:
            self.inference_worker.submit(frame, request_id)
        except (queue.Full, RuntimeError) as exc:
            self._pending_prediction = self._inference_request_id = None
            self._scan_failed("Inference unavailable: " + str(exc))
            return
        self.after(2000, lambda: self._prediction_timeout(request_id, generation))

    def _prediction_timeout(self, request_id, generation):
        if (self._closing or generation != self._operation_generation
                or self._inference_request_id != request_id):
            return
        self._pending_prediction = self._inference_request_id = None
        self._scan_failed("Inference timed out. Wait for the model to finish before retrying.",
                          OperatorState.REVIEW)

    def trigger_manual_eject(self):
        station = getattr(self, "station", None)
        if station:
            station.halt()
        self._log("[STOP] Stop requested on both boards. Inspect the rig before recovery.")

    def _update_result_banner(self, final_cls: str, conf: float, action: str, lat_ms: int):
        if final_cls == "FERTILE":
            card_bg = FUTheme.FERTILE_GREEN_CARD
            card_border = FUTheme.FERTILE_GREEN_BORDER
            badge_bg = FUTheme.FERTILE_GREEN_BG
            badge_text_color = FUTheme.FERTILE_GREEN_TEXT
            title_color = FUTheme.FERTILE_GREEN_TEXT
            title_text = f"FERTILE — ACCEPT ({conf*100:.1f}%)"
            sub_text = "Fertile prediction recorded • physical route not confirmed"
        else:
            card_bg = FUTheme.INFERTILE_AMBER_CARD
            card_border = FUTheme.INFERTILE_AMBER_BORDER
            badge_bg = FUTheme.INFERTILE_AMBER_BG
            badge_text_color = FUTheme.INFERTILE_AMBER_TEXT
            title_color = FUTheme.INFERTILE_AMBER
            title_text = f"INFERTILE — REJECT ({conf*100:.1f}%)"
            sub_text = "Infertile prediction recorded • physical route not confirmed"

        if action in {"MANUAL_REVIEW", "PREVIEW_ONLY"}:
            title_text = f"{action.replace('_', ' ')} ({conf:.1%})"
            sub_text = "Inspect the egg manually; no physical route was requested."
            card_bg, card_border = FUTheme.INFERTILE_AMBER_CARD, FUTheme.INFERTILE_AMBER_BORDER
            badge_bg, badge_text_color = FUTheme.INFERTILE_AMBER_BG, FUTheme.INFERTILE_AMBER_TEXT
            title_color = FUTheme.INFERTILE_AMBER

        self.result_banner.configure(fg_color=card_bg, border_color=card_border)
        self.result_badge.configure(text=action, fg_color=badge_bg, text_color=badge_text_color)
        self.latency_label.configure(text=f"Latency: {lat_ms}ms")
        self.result_title.configure(text=title_text, text_color=title_color)
        self.result_subtitle.configure(text=sub_text)

    def _update_counters_ui(self):
        pct = (self.fertile_count / max(1, self.fertile_count + self.infertile_count)) * 100.0
        batch_pct = min(100.0, (self.total_count / max(1, self.target_egg_count)) * 100.0)

        # Update Progress Bar & Percentage
        self.progress_bar.set(batch_pct / 100.0)
        self.progress_pct_label.configure(text=f"{batch_pct:.1f}%")

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
            self.speed_eta_label.configure(text=f"{rate_per_min:.0f}/min · ETA {eta_str}")
        else:
            self.speed_eta_label.configure(text="")

        # Update Counter Tiles
        total_text = f"{self.total_count} / {self.target_egg_count}"
        fertile_text = f"{self.fertile_count} ({pct:.1f}%)"
        for widget, text in ((self.box_total, total_text), (self.box_fertile, fertile_text)):
            widget.configure(text=text, font=(FUTheme.FONT_FAMILY,
                             18 if len(text) > 12 else 20, "bold"))
        self.box_infertile.configure(text=str(self.infertile_count))
        self.box_review.configure(text=str(self.review_count))

    def _get_active_display_detections(self) -> List[Dict[str, Any]]:
        """
        Returns active detections for real-time viewport visualization.
        Priority:
        1. Actively scanning / locked target during single scan.
        2. Recent single scan result (within 1.5s).
        3. Real-time background detection & tracking on live video.
        """
        if getattr(self, "_stopping", False) or not getattr(self.camera, "is_running", False):
            return []

        if getattr(self, "_scan_busy", False):
            if getattr(self, "_latest_detections", None):
                return [{**d, "is_scanning": True} for d in self._latest_detections]
            detector = getattr(self, "realtime_detector", None)
            if detector and detector.latest_detection:
                return [{**detector.latest_detection, "is_scanning": True}]
            return []

        # Fresh completed single scan: display result briefly (1.5s)
        last_scan_time = getattr(self, "_last_scan_result_time", 0.0)
        if getattr(self, "_latest_detections", None) and (time.monotonic() - last_scan_time < 1.5):
            return self._latest_detections

        # Active real-time background detection & tracking
        detector = getattr(self, "realtime_detector", None)
        if detector and detector.latest_detection:
            return [detector.latest_detection]

        # No active detection: return empty list (prevents freezing/sticking)
        return []

    def _update_video_frame(self):
        """
        Render fresh camera frames only; actual cadence depends on camera and PC.
        """
        if self._closing:
            return
        try:
            if getattr(self.camera, "is_running", False) and not getattr(self, "_stopping", False):
                snapshot = self.camera.snapshot(copy=False)
                frame = snapshot.image if snapshot else None
                if frame is not None:
                    render_key = (snapshot.sequence, self._cached_container_w, self._cached_container_h)
                    if render_key == getattr(self, "_last_render_key", None):
                        return
                    self._last_render_key = render_key
                    h, w = frame.shape[:2]

                    # 1. Compute optimal viewport dimensions with cached container
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

                    # 2. Optimized Downsampling: Resize BGR frame first (reduces pixel processing by 4x-6x)
                    disp_frame = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_LINEAR)

                    # 3. Draw Optical Candling Alignment Guide / Crosshairs (if enabled)
                    if self.show_crosshairs:
                        cx, cy = target_w // 2, target_h // 2
                        cv2.circle(disp_frame, (cx, cy), 5, (0, 255, 0), -1, cv2.LINE_AA)
                        cv2.line(disp_frame, (cx - 20, cy), (cx + 20, cy), (0, 255, 0), 1, cv2.LINE_AA)
                        cv2.line(disp_frame, (cx, cy - 20), (cx, cy + 20), (0, 255, 0), 1, cv2.LINE_AA)

                    # 4. Draw Real-time AI Bounding Boxes & Classification Labels
                    active_detections = self._get_active_display_detections()
                    for det in active_detections:
                        bbox = det.get("bbox", [])
                        cls_name = det.get("class", "FERTILE")
                        conf = det.get("confidence", 0.90)
                        is_scanning = det.get("is_scanning", False)

                        if len(bbox) == 4:
                            xc, yc, bw, bh = bbox
                            x1 = max(0, int((xc - bw / 2.0) * target_w))
                            y1 = max(0, int((yc - bh / 2.0) * target_h))
                            x2 = min(target_w - 1, int((xc + bw / 2.0) * target_w))
                            y2 = min(target_h - 1, int((yc + bh / 2.0) * target_h))

                            if is_scanning:
                                box_bgr = (0, 215, 255)       # Gold / Amber scan lock
                                label_str = "SCANNING..."
                            elif cls_name == "FERTILE":
                                box_bgr = (56, 122, 53)       # Agri-Green
                                label_str = f"FERTILE: {conf*100:.1f}%"
                            else:
                                box_bgr = (6, 119, 217)       # Penoy Amber
                                label_str = f"INFERTILE: {conf*100:.1f}%"

                            # High-visibility bounding box with industrial corner brackets
                            cv2.rectangle(disp_frame, (x1, y1), (x2, y2), box_bgr, 1, cv2.LINE_AA)

                            corner_len = max(6, min(16, int(min(x2 - x1, y2 - y1) * 0.2)))
                            # Top-Left corner
                            cv2.line(disp_frame, (x1, y1), (x1 + corner_len, y1), box_bgr, 2, cv2.LINE_AA)
                            cv2.line(disp_frame, (x1, y1), (x1, y1 + corner_len), box_bgr, 2, cv2.LINE_AA)
                            # Top-Right corner
                            cv2.line(disp_frame, (x2, y1), (x2 - corner_len, y1), box_bgr, 2, cv2.LINE_AA)
                            cv2.line(disp_frame, (x2, y1), (x2, y1 + corner_len), box_bgr, 2, cv2.LINE_AA)
                            # Bottom-Left corner
                            cv2.line(disp_frame, (x1, y2), (x1 + corner_len, y2), box_bgr, 2, cv2.LINE_AA)
                            cv2.line(disp_frame, (x1, y2), (x1, y2 - corner_len), box_bgr, 2, cv2.LINE_AA)
                            # Bottom-Right corner
                            cv2.line(disp_frame, (x2, y2), (x2 - corner_len, y2), box_bgr, 2, cv2.LINE_AA)
                            cv2.line(disp_frame, (x2, y2), (x2, y2 - corner_len), box_bgr, 2, cv2.LINE_AA)

                            # Pill badge header
                            (tw, th), _ = cv2.getTextSize(label_str, cv2.FONT_HERSHEY_SIMPLEX, 0.48, 1)
                            badge_y1 = max(0, y1 - th - 6)
                            badge_y2 = y1
                            badge_x2 = min(target_w, x1 + tw + 8)
                            cv2.rectangle(disp_frame, (x1, badge_y1), (badge_x2, badge_y2), box_bgr, -1)
                            cv2.putText(disp_frame, label_str, (x1 + 4, badge_y2 - 3),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 1, cv2.LINE_AA)

                    # 5. Fast color conversion on downscaled frame
                    rgb_frame = cv2.cvtColor(disp_frame, cv2.COLOR_BGR2RGB)
                    pil_img = Image.fromarray(rgb_frame)
                    photo = ImageTk.PhotoImage(image=pil_img)
                    self.video_label.configure(image=photo)
                    self._current_photo = photo
            else:
                # Camera turned off or session ending / on standby: clear viewport completely
                if self._current_photo is not None:
                    self._current_photo = None
                    try:
                        self.video_label.configure(image="")
                    except Exception:
                        pass

        except Exception as exc:
            self._log("[PREVIEW ERROR] " + str(exc))
        finally:
            if not self._closing:
                self.after(16, self._update_video_frame)

    def _update_status_loop(self):
        if self._closing:
            return
        self.sync_worker.device_status = "SCANNING" if self._scan_busy or self.is_auto_cycle_running else "ONLINE"
        self._set_session_active_state(self.is_session_active or self._scan_busy or self._stopping)
        self.fps_label.configure(text=f"FPS: {self.camera.current_fps:.1f}")
        if not getattr(self, "_queue_count_pending", False):
            self._queue_count_pending = True
            def updated(count):
                self._queue_count_pending = False
                self._unsynced_count = count
            def failed(message):
                self._queue_count_pending = False
                self._unsynced_count = None
                self._log("[STORAGE ERROR] Queue status unavailable: " + message)
            try:
                self._jobs.submit(self.db.get_unsynced_count, updated, failed)
            except (queue.Full, RuntimeError):
                self._queue_count_pending = False
        count = getattr(self, "_unsynced_count", None)
        error = self.sync_worker.last_error or self.sync_worker.heartbeat_error
        if error:
            text, color = "SYNC: ATTENTION", FUTheme.INFERTILE_AMBER
            if error != getattr(self, "_last_sync_error", None):
                self._log("[SYNC] " + error)
        elif count is None:
            text, color = "SYNC: QUEUE UNKNOWN", FUTheme.INFERTILE_AMBER
        elif self.sync_worker.is_online:
            text, color = f"SYNC: ONLINE ({count} PENDING)", FUTheme.FERTILE_GREEN_TEXT
        else:
            text, color = f"SYNC: OFFLINE ({count} PENDING)", FUTheme.TEXT_MUTED
        self._last_sync_error = error
        self.net_status_badge.configure(text=text, fg_color=FUTheme.PANEL_LIGHT_ALT,
                                        text_color=color)
        station = getattr(self, "station", None)
        ready = station is not None and (station.calibrated or station.active)
        self.iot_status_badge.configure(text="SORTER: ACTIVE" if station and station.active else "SORTER: VALIDATED" if ready else "SORTER: NOT VALIDATED",
                                        fg_color=FUTheme.PANEL_LIGHT_ALT,
                                        text_color=FUTheme.FERTILE_GREEN_TEXT if ready else FUTheme.INFERTILE_AMBER)
        if self.camera.last_error and self.camera.last_error != getattr(self, "_last_camera_error", None):
            self._log("[CAMERA ERROR] " + self.camera.last_error)
        self._last_camera_error = self.camera.last_error
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

    @_building_dialog
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
                text="ACTIVE DIAGNOSTIC SESSION\nPending local writes will finish before shutdown.",
                font=(FUTheme.FONT_FAMILY, 10, "bold"), text_color=FUTheme.INFERTILE_AMBER_TEXT,
                justify="center", padx=10, pady=8
            ).pack()
            msg = "Local scans are saved to SQLite WAL.\nAre you sure you want to stop operations and exit?"
        else:
            msg = "Local records remain saved; unsynced records are retained.\nAre you sure you want to close the operator station?"

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
            command=lambda: self._animate_modal_close(dialog), width=160, height=38, corner_radius=8
        ).pack(side="left")

        def do_exit():
            def actual_shutdown():
                print("\n[*] Shutting down OvaLens Edge Subsystems...")
                self.shutdown()
                print("[INFO] Waiting for shutdown cleanup.")
            self._animate_modal_close(dialog, on_close=actual_shutdown)

        ctk.CTkButton(
            btn_row, text="⏻ Exit System", fg_color=FUTheme.PRIMARY_MAROON,
            hover_color=FUTheme.HOVER_MAROON, text_color=FUTheme.TEXT_WHITE,
            font=(FUTheme.FONT_FAMILY, 12, "bold"), command=do_exit,
            width=160, height=38, corner_radius=8
        ).pack(side="right")

    @_building_dialog
    def open_batch_setup_dialog(self):
        """Robust Modal for Batch creation, selection, and candling stage setup with Offline Format Builder."""
        if self.current_session_id or self.is_session_active or self._scan_busy or self._stopping or self._finalization_failed:
            self._log("[BLOCKED] Finish the current session before changing batch parameters.")
            return

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


        def apply_server_batches(data):
            if not dialog.winfo_exists():
                return
            if data:
                server_batches_cache[:] = data
                opts = [f"{b.get('batch_code', b.get('batch_id'))} ({b.get('breed')})" for b in data]
            else:
                opts = ["(Offline — Use Format Builder tab)"]
            server_dropdown.configure(values=opts)
            server_dropdown.set(opts[0])

        def fetch_server_batches():
            data = self.sync_worker.fetch_active_batches()
            self._ui_events.put(lambda: apply_server_batches(data))

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
        stage_opts = ["DAY_10 (Primary Penoy Salvage @ ₱14.00)"]
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

        validation_error = ctk.CTkLabel(content, text="", text_color=FUTheme.REJECT_RED_TEXT,
                                       wraplength=420)
        validation_error.pack(fill="x", padx=16, pady=4)

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
                final_batch_id, raw_op, parsed_qty = validate_batch_config(
                    final_batch_id, raw_op, raw_qty, raw_stage)
            except ValueError as exc:
                validation_error.configure(text=str(exc))
                return

            self.current_batch_id = final_batch_id
            self.current_breed = final_breed
            self.current_stage = raw_stage
            self.target_egg_count = parsed_qty
            self.operator_name = raw_op
            self._diagnostics_complete = False
            self.scan_sequence = 0

            if not self.is_session_active:
                self.total_count = 0
                self.fertile_count = 0
                self.infertile_count = 0
                self.review_count = 0
                self._render_standby_hud()

            self.batch_btn.configure(text=f"Batch: {self.current_batch_id}  ({self.current_stage})  ▾")
            self._update_counters_ui()
            self._set_operation_state(OperatorState.READY, "BATCH CONFIGURED - READY FOR MANUAL DIAGNOSTICS")
            self._log(f"[BATCH] Configured: {self.current_batch_id} | Breed: {self.current_breed} | Stage: {self.current_stage} | Target: {self.target_egg_count} eggs")
            self._animate_modal_close(dialog)

        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(0, 16))

        ctk.CTkButton(
            btn_row, text="Cancel", fg_color="transparent", border_width=1, border_color=FUTheme.BORDER,
            text_color=FUTheme.TEXT_MUTED, hover_color=FUTheme.PANEL_ACCENT,
            command=lambda: self._animate_modal_close(dialog),
            width=100, height=38
        ).pack(side="left")

        ctk.CTkButton(
            btn_row, text="Save & Set Active Batch", fg_color=FUTheme.PRIMARY_MAROON,
            hover_color=FUTheme.HOVER_MAROON, text_color=FUTheme.TEXT_WHITE,
            font=(FUTheme.FONT_FAMILY, 12, "bold"), command=apply_batch, height=38
        ).pack(side="right", fill="x", expand=True, padx=(10, 0))

    @_building_dialog
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
            text="• Apply camera settings, inspect calibration, then click Start sorting.\n• Use Settings to identify both boards and validate measured holder geometry.\n• The conveyor stops for fresh, stable Day 10 classification.\n• After the target is recorded, tracked eggs drain through the timed sorting gate.",
            font=(FUTheme.FONT_FAMILY, 11), text_color=FUTheme.TEXT_PRIMARY, justify="left"
        )
        s2_body.pack(anchor="w", padx=14, pady=(2, 10))

        # Step 3 Card: 3 Biological Actions
        s3 = ctk.CTkFrame(content, fg_color=FUTheme.PANEL_LIGHT, corner_radius=10, border_width=1, border_color=FUTheme.BORDER)
        s3.pack(fill="x", pady=(0, 10))
        s3_hdr = ctk.CTkFrame(s3, fg_color=FUTheme.INFERTILE_AMBER, height=28, corner_radius=6)
        s3_hdr.pack(fill="x", padx=6, pady=6)
        ctk.CTkLabel(s3_hdr, text="STEP 3: BINARY SORTING & DIVERTER ACTIONS", font=(FUTheme.FONT_FAMILY, 11, "bold"), text_color=FUTheme.TEXT_WHITE).pack(side="left", padx=10)

        s3_body = ctk.CTkLabel(
            s3,
            text="FERTILE (Accept): Day 10 embryo viability verified -> remains in incubation.\nINFERTILE (Reject): Non-fertile Day 10 result -> diverted to Penoy salvage @ ₱14.00.\n⚪ MANUAL REVIEW: Low confidence (< 75%) or synchronization error -> operator review.",
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
            text="• [SPACEBAR]: Trigger Single Test Scan (Manual Candling)\n• [ESC] key: End Session (Run Summary & Direct CSV Export)\n• [S] key: Scan Explorer & Candling History\n• [R] key: Stop both controllers\n• [F11] key: Toggle Kiosk / Fullscreen Mode\n• [C] key: Toggle Optical Alignment Crosshairs\n• [B] key: Open Batch Setup Modal\n• [F1] / [H]: Open this Operator Quick Guide",
            font=(FUTheme.FONT_FAMILY, 11, "bold"), text_color=FUTheme.TEXT_PRIMARY, justify="left"
        )
        s4_body.pack(anchor="w", padx=14, pady=(2, 10))

        # Footer Button
        f_row = ctk.CTkFrame(dialog, fg_color="transparent")
        f_row.pack(fill="x", padx=20, pady=(0, 14))

        ctk.CTkButton(
            f_row, text="Got It! Close Guide", fg_color=FUTheme.PRIMARY_MAROON,
            hover_color=FUTheme.HOVER_MAROON, text_color=FUTheme.TEXT_WHITE,
            font=(FUTheme.FONT_FAMILY, 12, "bold"),
            command=lambda: self._animate_modal_close(dialog), height=38
        ).pack(fill="x")

    @_building_dialog
    def open_calibration_dialog(self):
        if self.current_session_id or self.is_session_active or self._scan_busy or self._stopping or self._finalization_failed:
            self._log("[BLOCKED] Stop the session before editing calibration.")
            return
        if getattr(self, "station", None) is not None:
            StationSettingsWindow(self)
            return
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
                speed = float(speed_entry.get())
                pause = int(pause_entry.get())
                advance = int(adv_entry.get())
                distance = float(dist_entry.get())
                if (not math.isfinite(speed) or not math.isfinite(distance)
                        or speed <= 0 or distance <= 0 or pause < 0 or advance <= 0):
                    raise ValueError("Calibration requires finite positive distances/speed and valid timings.")
                self.conveyor_speed_cm_s = speed
                self.chamber_pause_ms = pause
                self.conveyor_advance_ms = advance
                self.conveyor_dist_cm = distance
                self._log(f"[CONFIG] Updated: Speed={self.conveyor_speed_cm_s}cm/s, Pause={self.chamber_pause_ms}ms, Advance={self.conveyor_advance_ms}ms")
                self._animate_modal_close(dialog)
            except ValueError as exc:
                self._log("[CONFIG ERROR] " + str(exc))

        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack(fill="x", padx=24, pady=10)

        ctk.CTkButton(
            btn_row, text="Cancel", fg_color="transparent", border_width=1, border_color=FUTheme.BORDER,
            text_color=FUTheme.TEXT_MUTED, hover_color=FUTheme.PANEL_ACCENT,
            command=lambda: self._animate_modal_close(dialog), width=100, height=36
        ).pack(side="left")

        ctk.CTkButton(
            btn_row, text="Save Calibration", fg_color=FUTheme.PRIMARY_MAROON,
            hover_color=FUTheme.HOVER_MAROON, text_color=FUTheme.TEXT_WHITE, command=save, height=36
        ).pack(side="right", fill="x", expand=True, padx=(10, 0))

    def toggle_fullscreen(self, event=None):
        """Toggle borderless kiosk fullscreen for industrial touchscreens."""
        self.is_fullscreen = not self.is_fullscreen
        try:
            self.attributes("-fullscreen", self.is_fullscreen)
        except Exception:
            try:
                self.state("zoomed" if self.is_fullscreen else "normal")
            except Exception:
                pass
        if not self.is_fullscreen:
            self.geometry("1280x860")
        if hasattr(self, "kiosk_btn") and self.kiosk_btn.winfo_exists():
            self.kiosk_btn.configure(
                text="Windowed [F11]" if self.is_fullscreen else "Kiosk [F11]"
            )
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

    @_building_dialog
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
            card, text="Diagnostic Target Reached",
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

        pct = (self.fertile_count / max(1, self.fertile_count + self.infertile_count)) * 100.0
        penoy_salvage_val = self.infertile_count * 14.00

        # Tile 1: Total Processed
        t1 = ctk.CTkFrame(grid, fg_color=FUTheme.PANEL_LIGHT_ALT, corner_radius=8, border_width=1, border_color=FUTheme.BORDER)
        t1.grid(row=0, column=0, padx=4, pady=4, sticky="nsew")
        ctk.CTkLabel(t1, text="SCANS RECORDED", font=(FUTheme.FONT_FAMILY, 9, "bold"), text_color=FUTheme.TEXT_MUTED).pack(anchor="w", padx=10, pady=(6, 0))
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

        # Tile 4: Manual review fallback
        t4 = ctk.CTkFrame(grid, fg_color=FUTheme.PANEL_LIGHT_ALT, corner_radius=8, border_width=1, border_color=FUTheme.BORDER)
        t4.grid(row=1, column=1, padx=4, pady=4, sticky="nsew")
        ctk.CTkLabel(t4, text="MANUAL REVIEW", font=(FUTheme.FONT_FAMILY, 9, "bold"), text_color=FUTheme.TEXT_MUTED).pack(anchor="w", padx=10, pady=(6, 0))
        ctk.CTkLabel(t4, text=f"{self.review_count} Eggs", font=(FUTheme.FONT_FAMILY, 15, "bold"), text_color=FUTheme.TEXT_PRIMARY).pack(anchor="w", padx=10, pady=(0, 6))

        # Export Status Toast
        status_msg = ctk.CTkLabel(card, text="", font=(FUTheme.FONT_FAMILY, 10, "bold"), text_color=FUTheme.FERTILE_GREEN_TEXT)
        status_msg.pack(pady=(0, 6))

        def export_csv():
            session_id = self.current_session_id or getattr(self, "_last_session_id", None)
            if not session_id:
                status_msg.configure(text="No recorded session to export.")
                return
            self._export_report(lambda: self.db.export_session_csv(session_id), status_msg)

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
            self._animate_modal_close(dialog, on_close=self.open_batch_setup_dialog)

        ctk.CTkButton(
            btn_row, text="🔁 Setup Next Batch", fg_color=FUTheme.PRIMARY_MAROON,
            hover_color=FUTheme.HOVER_MAROON, text_color=FUTheme.TEXT_WHITE,
            font=(FUTheme.FONT_FAMILY, 12, "bold"), command=start_next,
            height=38, corner_radius=8
        ).pack(side="left", fill="x", expand=True, padx=(0, 6))

        ctk.CTkButton(
            btn_row, text="Done & Close", fg_color=FUTheme.PANEL_LIGHT_ALT,
            hover_color=FUTheme.PANEL_ACCENT, text_color=FUTheme.TEXT_SECONDARY,
            font=(FUTheme.FONT_FAMILY, 11), command=lambda: self._animate_modal_close(dialog),
            height=38, corner_radius=8, width=110
        ).pack(side="right")

    @_building_dialog
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
        batch_ids = [self.current_batch_id]
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
        def apply_batches(batches):
            if not dialog.winfo_exists():
                return
            ids = [b["batch_id"] for b in batches]
            if self.current_batch_id not in ids:
                ids.insert(0, self.current_batch_id)
            batch_dropdown.configure(values=ids + (["ALL (All Batches)"] if len(ids) > 1 else []))
        try:
            self._jobs.submit(self.db.get_distinct_batches, apply_batches,
                              lambda error: self._log("[HISTORY ERROR] " + error))
        except (queue.Full, RuntimeError):
            self._log("[HISTORY ERROR] Background queue unavailable; retry shortly.")


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
            if val == "ALL (All Batches)":
                return "ALL"
            return val

        def update_tabs_and_stats(all_b_scans):
            n_tot = len(all_b_scans)
            n_fert = sum(1 for s in all_b_scans if s["final_class"] == "FERTILE" and s["routing_action"] == "ACCEPT")
            n_inf = sum(1 for s in all_b_scans if s["final_class"] == "INFERTILE" and s["routing_action"] == "REJECT")
            fert_pct = (n_fert / max(1, n_fert + n_inf)) * 100.0 if n_tot > 0 else 0.0

            stats_summary_label.configure(
                text=f"Latest {n_tot} scans • Fertile: {fert_pct:.1f}% • Potential Penoy: ₱{n_inf*14:,.0f}"
            )

            # Update tab label text
            if "ALL" in tab_btns:
                tab_btns["ALL"].configure(text=f"All ({n_tot})")
            if "FERTILE" in tab_btns:
                tab_btns["FERTILE"].configure(text=f"🟢 Fertile ({n_fert})")
            if "INFERTILE" in tab_btns:
                tab_btns["INFERTILE"].configure(text=f"🟡 Infertile ({n_inf})")

        history_generation = [0]
        def render_table(*args):
            history_generation[0] += 1
            generation = history_generation[0]
            b_id, flt = get_active_batch_id(), current_filter[0]
            query = search_entry.get().strip()
            def read():
                return (self.db.get_scans_by_batch(b_id, limit=5000, class_filter="ALL"),
                        self.db.get_scans_by_batch(b_id, limit=50, class_filter=flt,
                                                  search_query=query or None))
            def apply(data):
                if not dialog.winfo_exists() or generation != history_generation[0]:
                    return
                update_tabs_and_stats(data[0])
                draw_table(data[1], b_id, flt)
            try:
                self._jobs.submit(read, apply, lambda error: self._log("[HISTORY ERROR] " + error))
            except (queue.Full, RuntimeError) as exc:
                self._log("[HISTORY ERROR] " + str(exc))

        def draw_table(scans, b_id, flt):
            for child in table_container.winfo_children():
                child.destroy()

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
                    pill = "FERTILE"
                else:
                    badge_fg = FUTheme.INFERTILE_AMBER_CARD
                    badge_border = FUTheme.INFERTILE_AMBER_BORDER
                    badge_text = FUTheme.INFERTILE_AMBER_TEXT
                    pill = "INFERTILE"

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
            render_table()

        batch_dropdown.configure(command=on_batch_change)
        search_entry.bind("<KeyRelease>", lambda e: render_table())

        # Build Filter Tabs
        tabs_spec = [
            ("ALL", "All"),
            ("FERTILE", "🟢 Fertile"),
            ("INFERTILE", "🟡 Infertile"),
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

        render_table()

        # Bottom Actions / Export Toolbar
        b_bar = ctk.CTkFrame(card, fg_color="transparent")
        b_bar.pack(fill="x", padx=16, pady=(0, 10))

        def export_current():
            b_id, flt = get_active_batch_id(), current_filter[0]
            self._export_report(lambda: self.db.export_batch_csv(b_id, class_filter=flt), toast_label)

        def export_all():
            b_id = get_active_batch_id()
            self._export_report(lambda: self.db.export_batch_csv(b_id, class_filter="ALL"), toast_label)

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
            command=lambda: self._animate_modal_close(dialog), height=36, corner_radius=8, width=80
        ).pack(side="right")
