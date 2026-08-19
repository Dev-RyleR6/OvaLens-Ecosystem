import customtkinter as ctk
import tkinter.font as tkfont
from tkinter import messagebox
import tkinter as tk
import cv2
from PIL import Image
import uuid
import time
import os
import threading
import serial
import json
import requests
import numpy as np
from datetime import datetime
from ultralytics import YOLO
try:
    import torch
    _TORCH_AVAILABLE = True
except ImportError:
    _TORCH_AVAILABLE = False

# Import updated local database manager
from db.local_db import LocalDatabaseManager

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

# ==============================================================================
# FOUNDATION UNIVERSITY BRAND PALETTE
# ==============================================================================
FU_MAROON       = "#800000"
FU_MAROON_DARK  = "#5C0000"
FU_WHITE        = "#FFFFFF"
FU_GRAY         = "#383838"
FU_AGRI_GREEN   = "#357a38"
FU_AGRI_GREEN_D = "#26592a"

BG_APP          = "#141414"
BG_PANEL        = "#1E1E1E"
BG_CARD         = "#262626"
BG_CARD_ALT     = "#2C2C2C"
BORDER_SUBTLE   = "#3A3A3A"
TEXT_PRIMARY    = FU_WHITE
TEXT_SECONDARY  = "#B7B7B7"
TEXT_MUTED      = "#7A7A7A"

COLOR_FERTILE   = FU_AGRI_GREEN
COLOR_INFERTILE = "#E67E22"
COLOR_ABNORMAL  = "#C0392B"
COLOR_IDLE      = "#5A5A5A"

MODEL_CONF_THRESHOLD = 0.80  # Raised from 0.45 to suppress weak false-positive predictions
MODEL_IOU_THRESHOLD = 0.80
ROI_MIN_CENTER_RATIO = 0.18
ROI_MAX_CENTER_RATIO = 0.82
ROI_MIN_BOX_RATIO = 0.12
ROI_MAX_BOX_RATIO = 0.90

# Egg geometry filter: duck eggs have a height/width aspect ratio between 0.65 and 1.45
# Detections outside this range (faces, hands, rectangular objects) are discarded
EGG_MIN_ASPECT_RATIO = 0.65
EGG_MAX_ASPECT_RATIO = 1.45

# Candling light intensity check: the average brightness (V channel in HSV) of the
# detection region must exceed this value to confirm an active candling lamp is present.
# Objects in normal ambient light (faces, backgrounds) will be below this threshold.
CANDLING_MIN_LUMINANCE = 120

RADIUS_CARD = 10
RADIUS_CHIP = 6
PAD = 16

# Set to False to disable saving JPEG scan images to disk (removes disk I/O latency)
ENABLE_IMAGE_STORAGE = False

IMAGE_STORAGE_DIR = "local_scans"
if ENABLE_IMAGE_STORAGE:
    os.makedirs(IMAGE_STORAGE_DIR, exist_ok=True)

# Networked servo controller address. Kept inline temporarily while hardware setup is being tested.
SERVO_IP = "http://192.168.137.46"
# Servo action cooldown to avoid repeated triggers on the same physical egg
SERVO_COOLDOWN_SECONDS = float(os.getenv("SERVO_COOLDOWN_SECONDS", "6"))
# Auto-scan interval in seconds (default 5s)
AUTO_SCAN_INTERVAL = float(os.getenv("AUTO_SCAN_INTERVAL", "5"))
# DirectShow cameras use negative exposure values; a lower value produces a darker
# image. Override this per camera with CAMERA_EXPOSURE if needed.
CAMERA_EXPOSURE = float(os.getenv("CAMERA_EXPOSURE", "-7"))

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
ENDPOINT_HEALTH = f"{API_BASE_URL}/api/v1/health"
ENDPOINT_SYNC_SCAN = f"{API_BASE_URL}/api/v1/scans/sync"
ENDPOINT_UPLOAD_IMAGE = f"{API_BASE_URL}/api/v1/scans/upload-image"
ENDPOINT_SESSION = f"{API_BASE_URL}/api/v1/sessions"
ENDPOINT_ACTIVE_BATCHES = f"{API_BASE_URL}/api/v1/batches/active"

API_KEY = os.getenv("API_KEY", "dev-api-key-123")   
HTTP_HEADERS = {"X-API-Key": API_KEY}


def _make_http_session() -> requests.Session:
    """Create a persistent HTTP session with connection pooling and standard auth headers."""
    session = requests.Session()
    session.headers.update(HTTP_HEADERS)
    # Allow up to 4 concurrent connections per host for sync + health + batch workers
    adapter = requests.adapters.HTTPAdapter(
        pool_connections=2,
        pool_maxsize=4,
        max_retries=0,
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def resolve_font(preferred, fallback, size, weight="normal"):
    installed = set(tkfont.families())
    family = preferred if preferred in installed else fallback
    return ctk.CTkFont(family=family, size=size, weight=weight)


class FUHatcheryEdgeApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Foundation University — Duck Egg Fertility Classifier")
        self.geometry("1440x840")
        self.minsize(1180, 720)
        self.configure(fg_color=BG_APP)

        # Resolve typography
        self.F_UNIV_TITLE = resolve_font("Times New Roman", "Times New Roman", 19, "bold")
        self.F_HEADLINE   = resolve_font("Bebas Neue Pro", "Segoe UI", 15, "bold")
        self.F_BADGE      = resolve_font("Bebas Neue Pro", "Segoe UI", 30, "bold")
        self.F_SUBHEAD    = resolve_font("Helvetica Neue", "Segoe UI Semibold", 13, "bold")
        self.F_BODY       = resolve_font("Helvetica Neue", "Segoe UI", 12, "normal")
        self.F_BODY_SM    = resolve_font("Helvetica Neue", "Segoe UI", 11, "normal")
        self.F_MONO       = ctk.CTkFont(family="Consolas", size=11)

        # Database connection
        self.db = LocalDatabaseManager()

        # Serial Hardware Link (Handshake ping verification)
        self.serial_conn = None
        self.serial_ok = False
        try:
            import serial.tools.list_ports
            available_ports = [p.device for p in serial.tools.list_ports.comports()]
            
            # Check if COM3 exists and responds to hardware ping
            target_port = os.getenv("SERIAL_PORT", "COM3")
            if target_port in available_ports:
                conn = serial.Serial(target_port, 115200, timeout=0.5)
                time.sleep(0.2)
                conn.write(b"PING\n")
                time.sleep(0.2)
                response = conn.read_all().decode(errors="ignore").strip()
                
                # Device is OK if it responds or has incoming data buffer
                if response or conn.in_waiting > 0:
                    self.serial_conn = conn
                    self.serial_ok = True
                else:
                    # Phantom port driver opened but no active IoT board responded
                    conn.close()
                    self.serial_conn = None
                    self.serial_ok = False
            else:
                self.serial_ok = False
        except Exception:
            if self.serial_conn and getattr(self.serial_conn, "is_open", False):
                try:
                    self.serial_conn.close()
                except Exception:
                    pass
            self.serial_conn = None
            self.serial_ok = False

        # Model pipeline state
        self.model = None
        self.model_error = None
        try:
            self.model = YOLO("models/weights/best.pt")
            # Warmup: run a dummy inference so PyTorch allocates memory tensors now,
            # not on the user's first live scan (prevents first-scan latency spike).
            _dummy = np.zeros((320, 320, 3), dtype=np.uint8)
            if _TORCH_AVAILABLE:
                with torch.inference_mode():
                    self.model(_dummy, verbose=False)
            else:
                self.model(_dummy, verbose=False)
        except Exception as exc:
            self.model_error = str(exc)

        # Optical camera state (Try primary camera index 0 with DSHOW backend first, fallback safely)
        self.cap = None
        self.camera_error = None
        for cam_idx in [0, 1]:
            try:
                cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW)
                if cap.isOpened():
                    ret, test_frame = cap.read()
                    if ret and test_frame is not None:
                        self.cap = cap
                        break
                cap.release()
            except Exception:
                continue

        if self.cap is None:
            try:
                cap = cv2.VideoCapture(0)
                if cap.isOpened():
                    ret, test_frame = cap.read()
                    if ret and test_frame is not None:
                        self.cap = cap
                    else:
                        cap.release()
            except Exception:
                pass

        if self.cap is None:
            self.camera_error = "No available camera index could be opened."
        else:
            # Disable automatic exposure so the candling lamp does not cause the
            # camera to brighten the rest of the frame, then use a darker setting.
            try:
                self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
                self.cap.set(cv2.CAP_PROP_EXPOSURE, CAMERA_EXPOSURE)
                self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
            except Exception:
                pass

        self.is_session_active = False
        self.current_session_uuid = None
        self.current_batch_code = ""
        self.latest_raw_frame = None
        self.latest_annotated_frame = None
        self._cached_display_frame = None
        self.realtime_inference_interval = 0.25
        self._last_realtime_inference = 0.0
        self._inference_in_progress = False
        self._display_image_size = (860, 600)
        self.frame_lock = threading.Lock()
        # Shared persistent HTTP session — connection pool is thread-safe
        self._http_session = _make_http_session()

        self.count_fertile = 0
        self.count_infertile = 0
        self.count_abnormal = 0
        self.log_rows = []
        # Auto-scan control
        self.auto_scan_enabled = False
        self._auto_scan_thread = None
        # Servo cooldown prevents repeated endpoint hits for the same egg event
        self._last_servo_trigger = 0.0

        # Batch selector state
        self.active_batches = []          # List of batch dicts from API
        self.selected_batch_id = None     # Currently chosen batch ID (global/session state)
        self.is_manual_batch_mode = False
        self._manual_mode_forced_offline = False
        self._is_fetching_batches = False
        self._batch_fetch_lock = threading.Lock()
        self._toast_job = None

        self._is_closing = False
        self._video_feed_job = None
        self._clock_job = None

        # Build interface
        self._build_header()
        self._build_status_strip()
        self._build_main_content()
        self._start_video_worker()
        self.update_video_feed()

        # Fetch active batches from Central API on startup
        self._fetch_active_batches()

        # Background sync loop thread
        self.sync_thread = threading.Thread(target=self._background_sync_worker, daemon=True)
        self.sync_thread.start()

        # Background health loop thread
        self.health_thread = threading.Thread(target=self._background_health_worker, daemon=True)
        self.health_thread.start()

        self.protocol("WM_DELETE_WINDOW", self.on_close_request)

    # ------------------------------------------------------------------
    # HEADER & STATUS STRIP
    # ------------------------------------------------------------------
    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=FU_MAROON, corner_radius=0, height=64)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        text_col = ctk.CTkFrame(header, fg_color="transparent")
        text_col.pack(side="left", padx=(24, 0), pady=8)

        ctk.CTkLabel(
            text_col, text="FOUNDATION UNIVERSITY",
            font=self.F_UNIV_TITLE, text_color=FU_WHITE,
        ).pack(anchor="w")

        ctk.CTkLabel(
            text_col,
            text="College of Agriculture  ·  Duck Egg Fertility Classification System",
            font=self.F_BODY_SM, text_color="#E8CFCF",
        ).pack(anchor="w", pady=(2, 0))

        self.lbl_clock = ctk.CTkLabel(header, text="", font=self.F_BODY_SM, text_color="#E8CFCF")
        self.lbl_clock.pack(side="right", padx=24)
        self._tick_clock()

    def _tick_clock(self):
        if self._is_closing:
            return
        self.lbl_clock.configure(text=datetime.now().strftime("%A, %d %B %Y   %H:%M:%S"))
        self._clock_job = self.after(1000, self._tick_clock)

    def _build_status_strip(self):
        strip = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=0, height=34)
        strip.pack(fill="x", side="top")
        strip.pack_propagate(False)

        inner = ctk.CTkFrame(strip, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=24)

        cam_ok = self.cap is not None
        self._status_pill(inner, "CAMERA", cam_ok, note="unavailable")
        self._status_pill(inner, "MODEL", self.model is not None)
        self._status_pill(inner, "SERIAL LINK", self.serial_ok, note="not connected")

        self.lbl_cloud_status = ctk.CTkLabel(
            inner, text="●  CLOUD: CHECKING", font=self.F_BODY_SM, text_color=COLOR_IDLE
        )
        self.lbl_cloud_status.pack(side="left", padx=(0, 20))

        self.lbl_sync_pill = ctk.CTkLabel(
            inner, text="●  SYNC: 0 PENDING", font=self.F_BODY_SM, text_color=FU_AGRI_GREEN
        )
        self.lbl_sync_pill.pack(side="left", padx=(0, 20))

        self.lbl_session_pill = ctk.CTkLabel(
            inner, text="●  NO ACTIVE SESSION", font=self.F_BODY_SM, text_color=TEXT_MUTED
        )
        self.lbl_session_pill.pack(side="right")

    def _status_pill(self, parent, label, ok, note=None):
        color = FU_AGRI_GREEN if ok else COLOR_ABNORMAL
        text = f"●  {label}: {'OK' if ok else (note or 'OFFLINE').upper()}"
        ctk.CTkLabel(parent, text=text, font=self.F_BODY_SM, text_color=color).pack(
            side="left", padx=(0, 20)
        )

    # ------------------------------------------------------------------
    # MAIN LAYOUT & CONTROLS
    # ------------------------------------------------------------------
    def _build_main_content(self):
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=PAD, pady=PAD)
        container.grid_columnconfigure(0, weight=3)
        container.grid_columnconfigure(1, weight=0, minsize=360)
        container.grid_rowconfigure(0, weight=1)

        self._build_camera_panel(container)
        self._build_control_column(container)

    def _build_camera_panel(self, parent):
        panel = ctk.CTkFrame(parent, fg_color=BG_PANEL, corner_radius=RADIUS_CARD)
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, PAD))
        panel.grid_rowconfigure(1, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        header_row = ctk.CTkFrame(panel, fg_color="transparent")
        header_row.grid(row=0, column=0, sticky="ew", padx=PAD, pady=(PAD, 8))
        ctk.CTkLabel(
            header_row, text="LIVE CANDLING FEED", font=self.F_HEADLINE, text_color=TEXT_PRIMARY
        ).pack(side="left")
        self.lbl_feed_meta = ctk.CTkLabel(
            header_row, text="—", font=self.F_MONO, text_color=TEXT_MUTED
        )
        self.lbl_feed_meta.pack(side="right")

        video_wrap = ctk.CTkFrame(panel, fg_color="#0B0B0B", corner_radius=RADIUS_CARD)
        video_wrap.grid(row=1, column=0, sticky="nsew", padx=PAD, pady=(0, PAD))
        video_wrap.grid_rowconfigure(0, weight=1)
        video_wrap.grid_columnconfigure(0, weight=1)

        self.cam_label = ctk.CTkLabel(
            video_wrap, text="Initializing camera stream…",
            font=self.F_BODY, text_color=TEXT_MUTED,
        )
        self.cam_label.grid(row=0, column=0, sticky="nsew")

        ctk.CTkLabel(
            video_wrap, text="Align egg within frame center for stable detection",
            font=self.F_BODY_SM, text_color="#6E6E6E",
        ).grid(row=1, column=0, sticky="s", pady=(0, 8))

    def _build_control_column(self, parent):
        col = ctk.CTkScrollableFrame(
            parent, fg_color="transparent", scrollbar_button_color=BORDER_SUBTLE
        )
        col.grid(row=0, column=1, sticky="nsew")

        self._build_session_card(col)
        self._build_result_card(col)
        self._build_metrics_card(col)
        self._build_log_card(col)

    def _section_title(self, parent, text):
        ctk.CTkLabel(parent, text=text, font=self.F_HEADLINE, text_color=TEXT_SECONDARY).pack(
            anchor="w", pady=(0, 8)
        )

    def _card(self, parent, accent=None):
        card = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=RADIUS_CARD)
        if accent:
            ctk.CTkFrame(card, fg_color=accent, width=4, corner_radius=0).place(
                relx=0, rely=0, relheight=1
            )
        return card

    def _build_session_card(self, parent):
        self._section_title(parent, "SESSION SETUP")
        card = self._card(parent)
        card.pack(fill="x", pady=(0, 20))
        self.session_card_body = ctk.CTkFrame(card, fg_color="transparent")
        self.session_card_body.pack(fill="x", padx=(20, 16), pady=16)
        body = self.session_card_body

        # --- Toast notification bar (hidden by default) ---
        self.toast_frame = ctk.CTkFrame(body, fg_color="#3D2E00", corner_radius=RADIUS_CHIP, height=32)
        self.toast_label = ctk.CTkLabel(
            self.toast_frame, text="", font=self.F_BODY_SM, text_color="#FFCC00"
        )
        self.toast_label.pack(side="left", padx=(10, 4), pady=4)
        ctk.CTkButton(
            self.toast_frame, text="✕", width=24, height=24, font=self.F_BODY_SM,
            fg_color="transparent", hover_color="#5A4400", text_color="#FFCC00",
            command=self._dismiss_toast,
        ).pack(side="right", padx=(0, 4), pady=4)
        # toast_frame is NOT packed yet — _show_toast() will pack it

        # --- Batch selector label row ---
        batch_label_row = ctk.CTkFrame(body, fg_color="transparent")
        batch_label_row.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(
            batch_label_row, text="Active Batch", font=self.F_BODY_SM, text_color=TEXT_MUTED
        ).pack(side="left")
        self.lbl_batch_loading = ctk.CTkLabel(
            batch_label_row, text="", font=self.F_BODY_SM, text_color=TEXT_MUTED
        )
        self.lbl_batch_loading.pack(side="right")

        # --- Dropdown mode container ---
        self.batch_dropdown_frame = ctk.CTkFrame(body, fg_color="transparent")
        self.batch_dropdown_frame.pack(fill="x", pady=(0, 4))

        dropdown_row = ctk.CTkFrame(self.batch_dropdown_frame, fg_color="transparent")
        dropdown_row.pack(fill="x")
        dropdown_row.grid_columnconfigure(0, weight=1)

        self.batch_dropdown = ctk.CTkOptionMenu(
            dropdown_row, values=["Loading…"],
            font=self.F_BODY, height=36,
            fg_color=BG_CARD_ALT, button_color=FU_MAROON, button_hover_color=FU_MAROON_DARK,
            corner_radius=RADIUS_CHIP, command=self._on_batch_selected,
            dynamic_resizing=False,
        )
        self.batch_dropdown.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.btn_refresh = ctk.CTkButton(
            dropdown_row, text="⟳", width=36, height=36,
            font=self.F_SUBHEAD, fg_color=BG_CARD_ALT,
            hover_color=BORDER_SUBTLE, corner_radius=RADIUS_CHIP,
            border_color=BORDER_SUBTLE, border_width=1,
            command=self._refresh_batches,
        )
        self.btn_refresh.grid(row=0, column=1)

        # --- Manual mode container (hidden by default) ---
        self.batch_manual_frame = ctk.CTkFrame(body, fg_color="transparent")
        # NOT packed yet — _toggle_manual_mode() will swap

        self.entry_batch = ctk.CTkEntry(
            self.batch_manual_frame, placeholder_text="e.g. BATCH-2026-01",
            font=self.F_BODY, height=36, corner_radius=RADIUS_CHIP,
            fg_color=BG_CARD_ALT, border_color=BORDER_SUBTLE, border_width=1,
        )
        self.entry_batch.pack(fill="x")
        self.entry_batch.bind("<FocusOut>", self._validate_manual_batch_id)
        self.entry_batch.bind("<Return>", self._validate_manual_batch_id)

        # --- Toggle link (only visible when offline) ---
        self.lbl_toggle_mode = ctk.CTkLabel(
            body, text="⚠ Offline Sync — Enter Batch ID Manually", font=self.F_BODY_SM,
            text_color=COLOR_INFERTILE, cursor="hand2",
        )
        # Hidden by default when online — shown only on offline sync fallback
        self.lbl_toggle_mode.bind("<Button-1>", lambda e: self._toggle_manual_mode())

        # --- Breed & Stage row ---
        row = ctk.CTkFrame(body, fg_color="transparent")
        row.pack(fill="x", pady=(0, 12))
        row.grid_columnconfigure((0, 1), weight=1)

        col_a = ctk.CTkFrame(row, fg_color="transparent")
        col_a.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkLabel(col_a, text="Breed (Auto-synced)", font=self.F_BODY_SM, text_color=TEXT_MUTED).pack(anchor="w", pady=(0, 4))
        self.combo_breed = ctk.CTkOptionMenu(
            col_a, values=["KAYUMANGGI", "ITIM", "KHAKI"], font=self.F_BODY, height=34,
            fg_color=BG_CARD_ALT, button_color=FU_MAROON, button_hover_color=FU_MAROON_DARK,
            corner_radius=RADIUS_CHIP,
        )
        self.combo_breed.pack(fill="x")

        col_b = ctk.CTkFrame(row, fg_color="transparent")
        col_b.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        ctk.CTkLabel(col_b, text="Candling Stage", font=self.F_BODY_SM, text_color=TEXT_MUTED).pack(anchor="w", pady=(0, 4))
        self.combo_stage = ctk.CTkOptionMenu(
            col_b, values=["DAY_10", "DAY_18", "DAY_25"], font=self.F_BODY, height=34,
            fg_color=BG_CARD_ALT, button_color=FU_MAROON, button_hover_color=FU_MAROON_DARK,
            corner_radius=RADIUS_CHIP,
        )
        self.combo_stage.pack(fill="x")

        # --- Validation error label ---
        self.lbl_form_error = ctk.CTkLabel(
            body, text="", font=self.F_BODY_SM, text_color=COLOR_ABNORMAL
        )
        self.lbl_form_error.pack(anchor="w", pady=(0, 4))

        # --- Action buttons ---
        self.btn_session = ctk.CTkButton(
            body, text="START CANDLING SESSION", font=self.F_SUBHEAD,
            fg_color=FU_AGRI_GREEN, hover_color=FU_AGRI_GREEN_D,
            height=42, corner_radius=RADIUS_CHIP, command=self.toggle_session,
        )
        self.btn_session.pack(fill="x", pady=(4, 6))

        self.btn_scan = ctk.CTkButton(
            body, text="⚡ CANDLE EGG NOW", font=self.F_SUBHEAD,
            fg_color="#2E7D32", hover_color="#1B5E20", state="disabled",
            height=36, corner_radius=RADIUS_CHIP, command=self.process_single_egg
        )
        self.btn_scan.pack(fill="x")

        # Auto-scan toggle (when checked, will trigger a scan every 2s while session active)
        self.var_auto = tk.IntVar(value=0)
        self.chk_auto = ctk.CTkCheckBox(
            body, text=f"Auto-scan ({int(AUTO_SCAN_INTERVAL)}s)", variable=self.var_auto, command=self._toggle_auto_scan, state="disabled"
        )
        self.chk_auto.pack(anchor="w", pady=(8, 0))

    # ------------------------------------------------------------------
    # BATCH SELECTOR LOGIC
    # ------------------------------------------------------------------
    def _fetch_active_batches(self):
        """Threaded fetch of active batches from the Central API."""
        with self._batch_fetch_lock:
            if self._is_fetching_batches:
                return
            self._is_fetching_batches = True
        self.after(0, lambda: self.lbl_batch_loading.configure(text="Loading…"))
        threading.Thread(target=self._fetch_active_batches_worker, daemon=True).start()

    def _fetch_active_batches_worker(self):
        """Background worker: calls GET /api/v1/batches/active."""
        try:
            res = requests.get(ENDPOINT_ACTIVE_BATCHES, headers=HTTP_HEADERS, timeout=5)
            if res.status_code == 200:
                batches = res.json()
                self.after(0, self._on_batches_fetched, batches)
            else:
                self.after(0, self._on_batches_fetch_failed, f"Server returned {res.status_code}")
        except Exception as exc:
            self.after(0, self._on_batches_fetch_failed, str(exc))
        finally:
            with self._batch_fetch_lock:
                self._is_fetching_batches = False

    def _on_batches_fetched(self, batches):
        """Callback on main thread after successful API fetch."""
        self.lbl_batch_loading.configure(text="")
        self.active_batches = batches if isinstance(batches, list) else []

        if not self.active_batches:
            self._on_batches_fetch_failed("No active batches found")
            return

        # Hide manual input link and frame when online
        self.lbl_toggle_mode.pack_forget()
        self.batch_manual_frame.pack_forget()
        self.batch_dropdown_frame.pack(fill="x", pady=(0, 4))
        self.is_manual_batch_mode = False
        self._manual_mode_forced_offline = False

        # Lock manual breed/stage edits since they are auto-populated from Hatchio API
        self.combo_breed.configure(state="disabled")
        self.combo_stage.configure(state="disabled")

        display_values = []
        for b in self.active_batches:
            bid = b.get("batch_id", "???")
            breed = b.get("breed", "—")
            day = b.get("incubation_day", 0)
            display_values.append(f"{bid} - Breed: {breed} (Day {day})")

        self.batch_dropdown.configure(values=display_values)
        self.batch_dropdown.set(display_values[0])
        self._on_batch_selected(display_values[0])

    def _on_batches_fetch_failed(self, error_msg):
        """Callback on main thread after API fetch failure — fallback to manual mode."""
        self.lbl_batch_loading.configure(text="")
        self.active_batches = []

        # Enable manual inputs and breed/stage controls when offline
        self.combo_breed.configure(state="normal")
        self.combo_stage.configure(state="normal")

        if not self.is_manual_batch_mode:
            self._manual_mode_forced_offline = True
            self.batch_dropdown_frame.pack_forget()
            self.batch_manual_frame.pack(fill="x", pady=(0, 4))
            self.lbl_toggle_mode.configure(text="⚠ Offline Sync — Enter Batch ID Manually")
            self.lbl_toggle_mode.pack(anchor="w", pady=(4, 10))
            self.is_manual_batch_mode = True

        self._show_toast("⚠ Offline Sync: Enter Batch ID, Breed & Stage manually", duration_ms=8000)

    def _on_batch_selected(self, choice):
        """Parse the dropdown selection and auto-fill breed/stage."""
        if not self.active_batches or choice in ["Loading…", "No active batches"]:
            self.selected_batch_id = None
            return

        selected_id = None
        for b in self.active_batches:
            bid = b.get("batch_id", "???")
            breed = b.get("breed", "—")
            day = b.get("incubation_day", 0)
            display = f"{bid} - Breed: {breed} (Day {day})"
            if display == choice:
                selected_id = b.get("batch_id")
                break

        if selected_id is None:
            self.selected_batch_id = None
            return

        self.selected_batch_id = selected_id

        # Find matching batch dict and auto-fill breed/stage
        for b in self.active_batches:
            if b.get("batch_id") == selected_id:
                breed = str(b.get("breed", "")).upper()
                day = b.get("incubation_day", 0)

                known_breeds = ["KAYUMANGGI", "ITIM", "KHAKI"]
                if breed in known_breeds:
                    self.combo_breed.set(breed)
                else:
                    self.combo_breed.set("KAYUMANGGI")

                # Auto-fill stage from incubation_day
                if day is None or day <= 13:
                    stage_str = "DAY_10"
                elif day <= 21:
                    stage_str = "DAY_18"
                else:
                    stage_str = "DAY_25"
                self.combo_stage.set(stage_str)
                break

    def _toggle_manual_mode(self):
        """Toggle between dropdown selection and manual text input."""
        if self.is_manual_batch_mode:
            # Switch BACK to dropdown mode
            self.batch_manual_frame.pack_forget()
            self.batch_dropdown_frame.pack(fill="x", pady=(0, 4),
                                           before=self.lbl_toggle_mode)
            self.lbl_toggle_mode.configure(text="✏  Enter Batch ID Manually")
            self.is_manual_batch_mode = False
            self.selected_batch_id = None
            # Re-select first dropdown item if batches exist
            if self.active_batches:
                current = self.batch_dropdown.get()
                self._on_batch_selected(current)
        else:
            # Switch TO manual mode (user choice — not forced offline)
            self.batch_dropdown_frame.pack_forget()
            self.batch_manual_frame.pack(fill="x", pady=(0, 4),
                                         before=self.lbl_toggle_mode)
            self.lbl_toggle_mode.configure(text="⬅  Select from Active Batches")
            self.is_manual_batch_mode = True
            self._manual_mode_forced_offline = False
            self.selected_batch_id = None

    def _refresh_batches(self):
        """Re-fetch active batches from the API."""
        self._fetch_active_batches()

    def _show_toast(self, message, duration_ms=5000):
        """Show a non-blocking warning toast at the top of the session card."""
        if self._toast_job:
            try:
                self.after_cancel(self._toast_job)
            except Exception:
                pass
        self.toast_label.configure(text=message)
        self.toast_frame.pack(fill="x", pady=(0, 8), before=self.batch_dropdown_frame
                               if not self.is_manual_batch_mode else self.batch_manual_frame)
        self._toast_job = self.after(duration_ms, self._dismiss_toast)

    def _dismiss_toast(self):
        """Hide the toast notification bar."""
        self.toast_frame.pack_forget()
        if self._toast_job:
            try:
                self.after_cancel(self._toast_job)
            except Exception:
                pass
            self._toast_job = None

    def _validate_manual_batch_id(self, event=None):
        """Auto-trim, uppercase, strip invalid chars from manual batch entry."""
        raw = self.entry_batch.get()
        # Allow alphanumeric, hyphens, underscores only
        cleaned = "".join(c for c in raw.strip() if c.isalnum() or c in "-_").upper()
        if cleaned != raw:
            self.entry_batch.delete(0, "end")
            self.entry_batch.insert(0, cleaned)
        self.selected_batch_id = cleaned if cleaned else None

    def _build_result_card(self, parent):
        self._section_title(parent, "REAL-TIME RESULT")
        self.result_card = self._card(parent, accent=COLOR_IDLE)
        self.result_card.pack(fill="x", pady=(0, 20))
        body = ctk.CTkFrame(self.result_card, fg_color="transparent")
        body.pack(fill="x", padx=(20, 16), pady=16)

        top_row = ctk.CTkFrame(body, fg_color="transparent")
        top_row.pack(fill="x")
        self.lbl_class_badge = ctk.CTkLabel(
            top_row, text="SYSTEM READY", font=self.F_BADGE, text_color=TEXT_SECONDARY
        )
        self.lbl_class_badge.pack(side="left")

        self.lbl_conf_value = ctk.CTkLabel(
            top_row, text="—", font=self.F_HEADLINE, text_color=TEXT_MUTED
        )
        self.lbl_conf_value.pack(side="right", anchor="s")

        self.conf_bar = ctk.CTkProgressBar(
            body, height=6, corner_radius=3, progress_color=COLOR_IDLE, fg_color=BG_CARD_ALT
        )
        self.conf_bar.pack(fill="x", pady=(10, 6))
        self.conf_bar.set(0)

        self.lbl_details = ctk.CTkLabel(
            body, text="Confidence  —   ·   Latency  —", font=self.F_BODY_SM, text_color=TEXT_MUTED
        )
        self.lbl_details.pack(anchor="w")

        self.lbl_scan_debug = ctk.CTkLabel(
            body, text="", font=self.F_BODY_SM, text_color="#A2A2A2"
        )
        self.lbl_scan_debug.pack(anchor="w", pady=(8, 0))

    def _build_metrics_card(self, parent):
        self._section_title(parent, "SESSION METRICS")
        card = self._card(parent)
        card.pack(fill="x", pady=(0, 20))
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=(20, 16), pady=16)

        self.metric_rows = {}
        for key, label, color in [
            ("fertile", "Fertile", COLOR_FERTILE),
            ("infertile", "Infertile", COLOR_INFERTILE),
            ("abnormal", "Abnormal", COLOR_ABNORMAL),
        ]:
            row = ctk.CTkFrame(body, fg_color="transparent")
            row.pack(fill="x", pady=4)
            ctk.CTkFrame(row, fg_color=color, width=8, height=8, corner_radius=4).pack(
                side="left", padx=(0, 8)
            )
            ctk.CTkLabel(row, text=label, font=self.F_BODY, text_color=TEXT_SECONDARY).pack(side="left")
            val = ctk.CTkLabel(row, text="0", font=self.F_SUBHEAD, text_color=TEXT_PRIMARY)
            val.pack(side="right")
            self.metric_rows[key] = val

        ctk.CTkFrame(body, fg_color=BORDER_SUBTLE, height=1).pack(fill="x", pady=10)

        total_row = ctk.CTkFrame(body, fg_color="transparent")
        total_row.pack(fill="x")
        ctk.CTkLabel(total_row, text="Total processed", font=self.F_SUBHEAD, text_color=TEXT_PRIMARY).pack(side="left")
        self.lbl_total_cnt = ctk.CTkLabel(total_row, text="0", font=self.F_SUBHEAD, text_color=TEXT_PRIMARY)
        self.lbl_total_cnt.pack(side="right")

    def _build_log_card(self, parent):
        self._section_title(parent, "RECENT SCANS")
        card = self._card(parent)
        card.pack(fill="both", expand=True, pady=(0, 4))
        self.log_frame = ctk.CTkFrame(card, fg_color="transparent")
        self.log_frame.pack(fill="both", expand=True, padx=(20, 16), pady=16)

        self.lbl_log_empty = ctk.CTkLabel(
            self.log_frame, text="No scans yet this session.", font=self.F_BODY_SM, text_color=TEXT_MUTED
        )
        self.lbl_log_empty.pack(anchor="w")

    # ------------------------------------------------------------------
    # CORE EXECUTION PIPELINE
    # ------------------------------------------------------------------
    def _prepare_egg_roi(self, frame):
        """Return a tight center crop that isolates the candled egg region for inference."""
        h, w = frame.shape[:2]
        crop_w = max(200, int(w * 0.48))
        crop_h = max(160, int(h * 0.48))
        x1 = max(0, (w - crop_w) // 2)
        y1 = max(0, (h - crop_h) // 2)
        x2 = min(w, x1 + crop_w)
        y2 = min(h, y1 + crop_h)
        roi_frame = frame[y1:y2, x1:x2]
        return roi_frame, (x1, y1, x2, y2)

    def _remap_roi_detection_to_frame(self, box, roi_bounds, frame_shape):
        """Convert normalized YOLO detections from the cropped ROI back to original frame scale."""
        frame_h, frame_w = frame_shape[:2]
        x1, y1, x2, y2 = roi_bounds
        roi_w = max(1, x2 - x1)
        roi_h = max(1, y2 - y1)

        xywhn = box.xywhn[0].tolist()
        x_center = xywhn[0]
        y_center = xywhn[1]
        width = xywhn[2]
        height = xywhn[3]

        mapped_x = (x_center * roi_w) / float(frame_w) + (x1 / float(frame_w))
        mapped_y = (y_center * roi_h) / float(frame_h) + (y1 / float(frame_h))
        mapped_w = (width * roi_w) / float(frame_w)
        mapped_h = (height * roi_h) / float(frame_h)

        return [round(mapped_x, 4), round(mapped_y, 4), round(mapped_w, 4), round(mapped_h, 4)]

    def _box_is_egg_like(self, box, roi_frame_shape, conf, roi_frame=None):
        """
        Filter detections to keep only those that look like a candled duck egg.
        Checks:
          1. Minimum confidence threshold.
          2. Detection centered within the ROI (not edge fragments).
          3. Bounding box size within egg-like proportions.
          4. Egg oval aspect ratio (height/width between 0.65 and 1.45).
          5. Candling light luminance — average brightness of the detection crop
             must exceed CANDLING_MIN_LUMINANCE to confirm active lamp present.
        """
        roi_h, roi_w = roi_frame_shape[:2]
        x1, y1, x2, y2 = map(float, box.xyxy[0].tolist())
        box_w = max(1.0, x2 - x1)
        box_h = max(1.0, y2 - y1)
        center_x = (x1 + x2) / 2.0 / float(roi_w)
        center_y = (y1 + y2) / 2.0 / float(roi_h)
        box_w_ratio = box_w / float(roi_w)
        box_h_ratio = box_h / float(roi_h)

        # 1. Confidence gate
        if conf < MODEL_CONF_THRESHOLD:
            return False

        # 2. Must be centered in the ROI (not edge fragments)
        if center_x < ROI_MIN_CENTER_RATIO or center_x > ROI_MAX_CENTER_RATIO:
            return False
        if center_y < ROI_MIN_CENTER_RATIO or center_y > ROI_MAX_CENTER_RATIO:
            return False

        # 3. Bounding box size within expected egg area range
        if box_w_ratio < ROI_MIN_BOX_RATIO or box_w_ratio > ROI_MAX_BOX_RATIO:
            return False
        if box_h_ratio < ROI_MIN_BOX_RATIO or box_h_ratio > ROI_MAX_BOX_RATIO:
            return False

        # 4. Egg oval aspect ratio check — discard rectangles, faces, and elongated objects
        aspect_ratio = box_h / box_w
        if aspect_ratio < EGG_MIN_ASPECT_RATIO or aspect_ratio > EGG_MAX_ASPECT_RATIO:
            return False

        # 5. Candling light intensity check — verify active lamp illumination in detection crop
        if roi_frame is not None:
            try:
                ix1 = max(0, int(x1))
                iy1 = max(0, int(y1))
                ix2 = min(roi_w, int(x2))
                iy2 = min(roi_h, int(y2))
                crop = roi_frame[iy1:iy2, ix1:ix2]
                if crop.size > 0:
                    hsv_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
                    avg_brightness = float(hsv_crop[:, :, 2].mean())
                    if avg_brightness < CANDLING_MIN_LUMINANCE:
                        return False  # No bright candling light — likely ambient/face/background
            except Exception:
                pass  # If crop fails, don't reject on luminance

        return True

    def process_single_egg(self):
        """Executes YOLOv8 inference, extracts detections, logs to SQLite, and updates UI."""
        if not self.is_session_active or self.latest_raw_frame is None or self.model is None:
            return

        frame = self.latest_raw_frame.copy()
        roi_frame, roi_bounds = self._prepare_egg_roi(frame)

        # 1. Model Inference (wrapped in inference_mode to suppress gradient overhead)
        t0 = time.time()
        if _TORCH_AVAILABLE:
            with torch.inference_mode():
                results = self.model(
                    roi_frame,
                    verbose=False,
                    conf=MODEL_CONF_THRESHOLD,
                    iou=MODEL_IOU_THRESHOLD,
                )[0]
        else:
            results = self.model(
                roi_frame,
                verbose=False,
                conf=MODEL_CONF_THRESHOLD,
                iou=MODEL_IOU_THRESHOLD,
            )[0]
        latency_ms = int((time.time() - t0) * 1000)

        top_class = "INFERTILE"
        top_conf = 0.0
        detections = []
        top_model_box = None
        top_filtered_box = None

        for box in results.boxes:
            c_name = self._normalize_class_name(self.model.names[int(box.cls[0])])
            conf = float(box.conf[0])
            if conf > top_conf:
                top_conf = conf
                top_class = c_name
                top_model_box = {
                    "class_label": c_name,
                    "confidence": round(conf, 4),
                    "bbox": self._remap_roi_detection_to_frame(box, roi_bounds, frame.shape),
                }

            if self._box_is_egg_like(box, roi_frame.shape, conf, roi_frame=roi_frame):
                top_filtered_box = {
                    "class_label": c_name,
                    "confidence": round(conf, 4),
                    "bbox": self._remap_roi_detection_to_frame(box, roi_bounds, frame.shape),
                }

            detections.append({
                "class_label": c_name,
                "confidence": round(conf, 4),
                "bbox": self._remap_roi_detection_to_frame(box, roi_bounds, frame.shape),
            })

        detected = top_model_box is not None
        if not detected:
            self._apply_result_ui("NO EGG", 0.0, latency_ms)
            self.lbl_scan_debug.configure(text="Status: NO EGG · Not recorded")
            return

        top_conf = top_model_box["confidence"]
        if top_conf < MODEL_CONF_THRESHOLD:
            self._apply_result_ui("LOW CONFIDENCE", top_conf, latency_ms)
            self.lbl_scan_debug.configure(text=f"Status: LOW CONFIDENCE ({top_conf:.2f}) · Not recorded")
            return

        if top_filtered_box is not None:
            # Prefer the stricter egg-like filtered detection for logging details.
            top_class = top_filtered_box["class_label"]
            top_conf = top_filtered_box["confidence"]

        # 2. Routing Logic — serial motor command should move the egg path based on class
        routing_action = "ACCEPT" if top_class == "FERTILE" else "REJECT"
        if self.serial_conn and self.serial_ok:
            cmd = b"ROUTE_ACCEPT\n" if routing_action == "ACCEPT" else b"ROUTE_REJECT\n"
            self.serial_conn.write(cmd)

        # 3. Save Record in Local SQLite (image file saving is optional)
        scan_uuid = str(uuid.uuid4())
        if ENABLE_IMAGE_STORAGE:
            image_path = os.path.join(IMAGE_STORAGE_DIR, f"{scan_uuid}.jpg")
            cv2.imwrite(image_path, frame)
        else:
            image_path = ""

        self.db.insert_scan(
            scan_id=scan_uuid,
            session_id=self.current_session_uuid,
            breed_code=self.combo_breed.get(),
            image_path=image_path,
            final_class=top_class,
            confidence=top_conf,
            inference_ms=latency_ms,
            routing_action=routing_action,
            detections=detections
        )

        # 5. Refresh Dashboard UI
        scan_state = "DETECTED" if detected else "NO EGG"
        self.update_scan_ui_results(top_class, top_conf, latency_ms, scan_state)

        # 6. Trigger servo after metrics/UI are updated
        servo_ok = False
        try:
            servo_ok = self._actuate_servo_by_class(top_class)
        except Exception:
            pass
        if servo_ok:
            self.lbl_scan_debug.configure(text=f"Status: {scan_state} · Recorded · Servo OK")

    def _actuate_servo_by_class(self, class_name) -> bool:
        """Call the configured servo controller `/classify` endpoint with `?class=`.

        Mapping to device classes: 'fertile', 'infertile', 'abnormal'.
        Accepts `SERVO_IP` as either an IP/host (e.g. 192.168.137.193) or full URL
        (e.g. http://192.168.137.193). The final request will be: <base>/classify?class=<name>
        Returns True when the endpoint was successfully triggered.
        """
        if not SERVO_IP:
            return False

        now = time.time()
        if now - self._last_servo_trigger < SERVO_COOLDOWN_SECONDS:
            return False

        mapping = {
            "ABNORMAL": "abnormal",
            "FERTILE": "fertile",
            "INFERTILE": "infertile",
        }
        cls = mapping.get(class_name)
        if not cls:
            return False
        try:
            base = SERVO_IP
            if not base.startswith("http://") and not base.startswith("https://"):
                base = f"http://{base}"
            url = f"{base.rstrip('/')}/classify?class={cls}"
            # Non-blocking call with short timeout
            res = self._http_session.get(url, timeout=1)
            if res.status_code == 200:
                self._last_servo_trigger = now
                return True
            self.lbl_scan_debug.configure(text=f"Servo error: {res.status_code}")
            return False
        except Exception as exc:
            self.lbl_scan_debug.configure(text=f"Servo failed: {exc}")
            return False

    def _toggle_auto_scan(self):
        """Enable or disable the auto-scan worker. The checkbox UI calls this handler."""
        # Read desired state from the checkbox variable
        desired = bool(self.var_auto.get())
        self.auto_scan_enabled = desired
        if self.auto_scan_enabled and self.is_session_active:
            # start worker
            if not self._auto_scan_thread or not self._auto_scan_thread.is_alive():
                self._auto_scan_thread = threading.Thread(target=self._auto_scan_worker, daemon=True)
                self._auto_scan_thread.start()

    def _auto_scan_worker(self):
        """Background loop: schedule `process_single_egg` on the main thread every AUTO_SCAN_INTERVAL seconds."""
        while self.auto_scan_enabled and not self._is_closing:
            try:
                if not self.is_session_active:
                    time.sleep(0.5)
                    continue
                # schedule scan on main/UI thread
                self.after(0, self.process_single_egg)
            except Exception:
                pass
            time.sleep(max(0.5, AUTO_SCAN_INTERVAL))

    def _normalize_class_name(self, class_name):
        name = class_name.strip().upper()
        if name in ["FERTILE", "FER"]:
            return "FERTILE"
        if name in ["ABNORMAL", "ABN"]:
            return "ABNORMAL"
        return "INFERTILE"

    def _bbox_color_bgr(self, class_name):
        if class_name == "FERTILE":
            return (57, 255, 20)
        if class_name == "ABNORMAL":
            return (60, 60, 255)
        return (0, 112, 255)

    def _run_realtime_detection(self, frame):
        """Run inference and draw boxes. Safe to call from a worker thread."""
        annotated_frame = frame.copy()
        roi_frame, roi_bounds = self._prepare_egg_roi(frame)
        t0 = time.time()
        if _TORCH_AVAILABLE:
            with torch.inference_mode():
                results = self.model(
                    roi_frame,
                    verbose=False,
                    conf=MODEL_CONF_THRESHOLD,
                    iou=MODEL_IOU_THRESHOLD,
                )[0]
        else:
            results = self.model(
                roi_frame,
                verbose=False,
                conf=MODEL_CONF_THRESHOLD,
                iou=MODEL_IOU_THRESHOLD,
            )[0]
        latency_ms = int((time.time() - t0) * 1000)

        top_class = "INFERTILE"
        top_conf = 0.0
        if len(results.boxes) > 0:
            for box in results.boxes:
                c_name = self._normalize_class_name(self.model.names[int(box.cls[0])])
                conf = float(box.conf[0])
                if not self._box_is_egg_like(box, roi_frame.shape, conf, roi_frame=roi_frame):
                    continue

                if conf > top_conf:
                    top_conf = conf
                    top_class = c_name

                xyxy = box.xyxy[0].tolist()
                x1, y1, x2, y2 = map(float, xyxy)
                roi_x1, roi_y1, _, _ = roi_bounds
                map_x1 = int(round(x1 + roi_x1))
                map_y1 = int(round(y1 + roi_y1))
                map_x2 = int(round(x2 + roi_x1))
                map_y2 = int(round(y2 + roi_y1))

                color = self._bbox_color_bgr(c_name)
                cv2.rectangle(annotated_frame, (map_x1, map_y1), (map_x2, map_y2), color, 2)
                label = f"{c_name} {conf:.2f}"
                cv2.putText(
                    annotated_frame, label, (map_x1, max(map_y1 - 10, 0)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2, cv2.LINE_AA,
                )

        return annotated_frame, top_class, top_conf, latency_ms

    def _start_realtime_inference(self, frame):
        if self._inference_in_progress:
            return
        self._inference_in_progress = True
        frame_copy = frame.copy()
        threading.Thread(
            target=self._realtime_inference_worker,
            args=(frame_copy,),
            daemon=True,
        ).start()

    def _realtime_inference_worker(self, frame):
        try:
            annotated_frame, top_class, top_conf, latency_ms = self._run_realtime_detection(frame)
            self.after(
                0,
                lambda af=annotated_frame, tc=top_class, conf=top_conf, ms=latency_ms: self._apply_realtime_inference(
                    af, tc, conf, ms
                ),
            )
        except Exception:
            self.after(0, self._finish_realtime_inference)

    def _finish_realtime_inference(self):
        self._inference_in_progress = False

    def _apply_realtime_inference(self, annotated_frame, top_class, top_conf, latency_ms):
        try:
            if self._is_closing or not self.is_session_active:
                return
            self._cached_display_frame = annotated_frame
            self._apply_result_ui(top_class, top_conf, latency_ms)
        finally:
            self._inference_in_progress = False

    def _result_color(self, class_name):
        return {
            "FERTILE": COLOR_FERTILE,
            "INFERTILE": COLOR_INFERTILE,
            "ABNORMAL": COLOR_ABNORMAL,
        }.get(class_name, TEXT_SECONDARY)

    def _apply_result_ui(self, class_name, confidence, latency_ms):
        badge_color = self._result_color(class_name)
        self.lbl_class_badge.configure(text=class_name, text_color=badge_color)
        self.lbl_conf_value.configure(text=f"{confidence*100:.1f}%", text_color=badge_color)
        self.conf_bar.configure(progress_color=badge_color)
        self.conf_bar.set(max(0.0, min(1.0, confidence)))
        self.lbl_details.configure(
            text=f"Confidence  {confidence*100:.1f}%   ·   Latency  {latency_ms} ms"
        )
        self._set_result_accent(badge_color)

    def toggle_session(self):
        if not self.is_session_active:
            # Resolve batch code from the active input mode
            if self.is_manual_batch_mode:
                self._validate_manual_batch_id()
            batch_code = self.selected_batch_id

            if not batch_code:
                self.lbl_form_error.configure(text="Select or enter a batch code before starting.")
                return

            self.lbl_form_error.configure(text="")
            self.is_session_active = True
            self.current_session_uuid = str(uuid.uuid4())
            self.current_batch_code = batch_code

            self.db.create_session(
                session_id=self.current_session_uuid,
                batch_code=self.current_batch_code,
                breed_code=self.combo_breed.get(),
                stage=self.combo_stage.get()
            )

            threading.Thread(
                target=self._api_start_session,
                args=(self.current_session_uuid, self.current_batch_code, self.combo_breed.get(), self.combo_stage.get()),
                daemon=True
            ).start()

            self.btn_session.configure(
                text="END SESSION", fg_color=COLOR_ABNORMAL, hover_color="#8E2A20"
            )
            self.btn_scan.configure(state="normal")
            # Enable and start autoscan by default
            try:
                self.chk_auto.configure(state="normal")
                self.var_auto.set(1)
                self._toggle_auto_scan()
            except Exception:
                pass

            # Disable batch selection controls during session
            self.batch_dropdown.configure(state="disabled")
            self.btn_refresh.configure(state="disabled")
            self.entry_batch.configure(state="disabled")
            self.lbl_toggle_mode.configure(text_color=TEXT_MUTED)
            self.lbl_toggle_mode.unbind("<Button-1>")
            self.combo_breed.configure(state="disabled")
            self.combo_stage.configure(state="disabled")

            self.count_fertile = self.count_infertile = self.count_abnormal = 0
            self.log_rows = []
            self._cached_display_frame = None
            self._last_realtime_inference = 0.0
            self._refresh_log()
            self._update_counter_labels()

            self.lbl_session_pill.configure(
                text=f"●  SESSION ACTIVE — {batch_code}", text_color=FU_AGRI_GREEN
            )
        else:
            self.db.end_session(self.current_session_uuid)

            threading.Thread(
                target=self._api_end_session,
                args=(self.current_session_uuid,),
                daemon=True
            ).start()

            self.is_session_active = False
            self.current_session_uuid = None
            self.current_batch_code = ""
            self._cached_display_frame = None
            self._last_realtime_inference = 0.0
            self.btn_session.configure(
                text="START CANDLING SESSION", fg_color=FU_AGRI_GREEN, hover_color=FU_AGRI_GREEN_D
            )
            self.btn_scan.configure(state="disabled")
            # Ensure autoscan is stopped and checkbox disabled
            try:
                self.var_auto.set(0)
                self._toggle_auto_scan()
                self.chk_auto.configure(state="disabled")
            except Exception:
                pass

            # Re-enable batch selection controls
            self.batch_dropdown.configure(state="normal")
            self.btn_refresh.configure(state="normal")
            self.entry_batch.configure(state="normal")
            self.lbl_toggle_mode.configure(text_color=FU_AGRI_GREEN)
            self.lbl_toggle_mode.bind("<Button-1>", lambda e: self._toggle_manual_mode())
            self.combo_breed.configure(state="normal")
            self.combo_stage.configure(state="normal")

            self.lbl_class_badge.configure(text="SESSION ENDED", text_color=TEXT_SECONDARY)
            self._set_result_accent(COLOR_IDLE)
            self.lbl_session_pill.configure(text="●  NO ACTIVE SESSION", text_color=TEXT_MUTED)

    def _start_video_worker(self):
        if self._video_feed_job is not None:
            return
        self._video_feed_job = threading.Thread(target=self._video_worker_loop, daemon=True)
        self._video_feed_job.start()

    def _video_worker_loop(self):
        while not self._is_closing:
            if self.cap is None or not self.cap.isOpened():
                time.sleep(0.05)
                continue

            try:
                ret, frame = self.cap.read()
            except Exception:
                ret, frame = False, None

            if not ret or frame is None:
                time.sleep(0.01)
                continue

            # Store raw frame under lock (fast — just a copy + assignment)
            with self.frame_lock:
                self.latest_raw_frame = frame.copy()

            # Run YOLO inference OUTSIDE the lock so the GUI thread never stalls
            annotated_frame = frame.copy()
            if self.is_session_active and self.model is not None:
                try:
                    if _TORCH_AVAILABLE:
                        with torch.inference_mode():
                            results = self.model(
                                frame,
                                conf=MODEL_CONF_THRESHOLD,
                                iou=MODEL_IOU_THRESHOLD,
                                verbose=False,
                            )[0]
                    else:
                        results = self.model(
                            frame,
                            conf=MODEL_CONF_THRESHOLD,
                            iou=MODEL_IOU_THRESHOLD,
                            verbose=False,
                        )[0]
                    annotated_frame = results.plot()
                except Exception:
                    annotated_frame = frame.copy()

            # Store annotated frame under lock (fast — just assignment)
            with self.frame_lock:
                self.latest_annotated_frame = annotated_frame

            time.sleep(0.02)

    def update_video_feed(self):
        if self._is_closing:
            return

        if self.cap is None:
            self.cam_label.configure(
                image=None, text="Camera unavailable — check connection and restart the app."
            )
            self.lbl_feed_meta.configure(text="no camera")
            self._video_feed_job = self.after(500, self.update_video_feed)
            return

        with self.frame_lock:
            display_frame = self.latest_annotated_frame.copy() if self.latest_annotated_frame is not None else None
            raw_frame = self.latest_raw_frame.copy() if self.latest_raw_frame is not None else None

        if not self.is_session_active:
            display_frame = raw_frame

        if display_frame is not None:
            try:
                frame_rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                ctk_img = ctk.CTkImage(
                    light_image=img, dark_image=img, size=self._display_image_size
                )
                self.cam_label.configure(image=ctk_img, text="")
                self.cam_label.image = ctk_img
                h, w = display_frame.shape[:2]
                self.lbl_feed_meta.configure(text=f"{w}×{h}  ·  live")
            except Exception:
                self.lbl_feed_meta.configure(text="frame error")
        elif raw_frame is not None:
            try:
                frame_rgb = cv2.cvtColor(raw_frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                ctk_img = ctk.CTkImage(
                    light_image=img, dark_image=img, size=self._display_image_size
                )
                self.cam_label.configure(image=ctk_img, text="")
                self.cam_label.image = ctk_img
                h, w = raw_frame.shape[:2]
                self.lbl_feed_meta.configure(text=f"{w}×{h}  ·  live")
            except Exception:
                self.lbl_feed_meta.configure(text="frame error")
        else:
            self.lbl_feed_meta.configure(text="no signal")

        self._video_feed_job = self.after(16, self.update_video_feed)

    # ------------------------------------------------------------------
    # BACKGROUND API DAEMONS & CACHED UI UPDATES
    # ------------------------------------------------------------------
    def _api_start_session(self, session_id, batch_code, breed_code, stage):
        try:
            self._http_session.post(ENDPOINT_SESSION, json={
                "session_id": str(session_id),
                "batch_code": batch_code,
                "breed_code": breed_code,
                "stage": stage
            }, timeout=3)
        except Exception:
            pass

    def _api_end_session(self, session_id):
        try:
            ended_at = datetime.utcnow().isoformat()
            self._http_session.patch(f"{ENDPOINT_SESSION}/{session_id}", json={
                "ended_at": ended_at
            }, timeout=3)
        except Exception:
            pass

    def _background_health_worker(self):
        """Periodically polls the central API to update the online status indicator."""
        while not self._is_closing:
            try:
                res = self._http_session.get(ENDPOINT_HEALTH, timeout=3)
                if res.status_code == 200:
                    self.after(0, self._update_cloud_ui_pill, True)
                else:
                    self.after(0, self._update_cloud_ui_pill, False)
            except Exception:
                self.after(0, self._update_cloud_ui_pill, False)

            time.sleep(3)

    def _update_cloud_ui_pill(self, ok):
        color = FU_AGRI_GREEN if ok else COLOR_ABNORMAL
        text = "●  CLOUD: ONLINE" if ok else "●  CLOUD: OFFLINE"
        self.lbl_cloud_status.configure(text=text, text_color=color)

    def _background_sync_worker(self):
        """Background thread uploading offline SQLite records to Central API."""
        while not self._is_closing:
            try:
                pending_scans = self.db.get_pending_scans_for_sync(limit=10)
                
                if pending_scans:
                    for scan in pending_scans:
                        # Attempt to push record to central cloud API endpoint
                        try:
                            # Construct payload
                            payload = {
                                "scan_id": scan['scan_id'],
                                "session_id": scan['session_id'],
                                "batch_code": scan['batch_code'],
                                "stage": scan['stage'],
                                "breed_code": scan['breed_code'],
                                "final_class": scan['final_class'],
                                "confidence": scan['confidence'],
                                "inference_ms": scan['inference_ms'],
                                "routing_action": scan['routing_action'],
                                "scanned_at": scan['scanned_at'],
                                "detections": json.loads(scan['detections_json'])
                            }
                            
                            res = self._http_session.post(ENDPOINT_SYNC_SCAN, json=payload, timeout=5)
                            if res.status_code in [200, 201]:
                                img_path = scan['image_path']
                                if img_path and os.path.exists(img_path):
                                    with open(img_path, 'rb') as f:
                                        self._http_session.post(ENDPOINT_UPLOAD_IMAGE, files={'file': f}, data={'scan_id': str(scan['scan_id'])}, timeout=10)
                                self.db.mark_scan_synced(scan['scan_id'])
                            else:
                                self.db.mark_scan_failed(scan['scan_id'])

                        except Exception:
                            self.db.mark_scan_failed(scan['scan_id'])

                # Query remaining unpushed records
                updated_cnt = self.db.get_pending_count()
                
                # Update UI elements safely via Tkinter main loop
                self.after(0, self._update_sync_ui_pill, updated_cnt)

            except Exception:
                pass

            time.sleep(5)

    def _update_sync_ui_pill(self, pending_count):
        """Thread-safe UI update method for the sync pill status indicator."""
        sync_color = FU_AGRI_GREEN if pending_count == 0 else COLOR_INFERTILE
        self.lbl_sync_pill.configure(
            text=f"●  SYNC: {pending_count} PENDING", text_color=sync_color
        )

    # ------------------------------------------------------------------
    # CLEANUP & SHUTDOWN
    # ------------------------------------------------------------------
    def on_close_request(self):
        if self.is_session_active:
            proceed = messagebox.askyesno(
                title="End active session and quit?",
                message=(
                    f"A candling session for batch \"{self.current_batch_code}\" is active.\n\n"
                    "Closing now will terminate the session safely in SQLite.\n\n"
                    "Quit anyway?"
                ),
                icon="warning",
                default="no",
            )
        else:
            proceed = messagebox.askyesno(
                title="Quit application?",
                message="Close the Duck Egg Fertility Classifier?",
                default="no",
            )

        if proceed:
            self._shutdown()

    def _shutdown(self):
        self._is_closing = True

        if self.is_session_active and self.current_session_uuid:
            session_id = self.current_session_uuid
            self.db.end_session(session_id)
            threading.Thread(
                target=self._api_end_session,
                args=(session_id,),
                daemon=True,
            ).start()
            self.is_session_active = False

        for job in (self._video_feed_job, self._clock_job, self._toast_job):
            if job is not None:
                try:
                    self.after_cancel(job)
                except Exception:
                    pass

        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass

        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.close()
            except Exception:
                pass

        try:
            self._http_session.close()
        except Exception:
            pass

        try:
            self.destroy()
        except Exception:
            pass
        os._exit(0)

    def _set_result_accent(self, color):
        for child in self.result_card.winfo_children():
            if isinstance(child, ctk.CTkFrame) and str(child.cget("width")) == "4":
                child.configure(fg_color=color)

    def update_scan_ui_results(self, class_name, confidence, latency_ms, scan_state="DETECTED"):
        self._apply_result_ui(class_name, confidence, latency_ms)

        if class_name == "FERTILE":
            self.count_fertile += 1
        elif class_name == "INFERTILE":
            self.count_infertile += 1
        elif class_name == "ABNORMAL":
            self.count_abnormal += 1

        badge_color = self._result_color(class_name)
        self.log_rows.insert(
            0,
            (
                datetime.now().strftime("%H:%M:%S"),
                class_name,
                confidence,
                badge_color,
                scan_state,
            ),
        )
        self.log_rows = self.log_rows[:8]
        self._refresh_log()
        self._update_counter_labels()
        self.lbl_scan_debug.configure(text=f"Status: {scan_state} · Recorded")

    def _refresh_log(self):
        for child in self.log_frame.winfo_children():
            child.destroy()
        if not self.log_rows:
            ctk.CTkLabel(
                self.log_frame, text="No scans yet this session.",
                font=self.F_BODY_SM, text_color=TEXT_MUTED,
            ).pack(anchor="w")
            return
        for ts, cls, conf, color, state in self.log_rows:
            row = ctk.CTkFrame(self.log_frame, fg_color="transparent")
            row.pack(fill="x", pady=3)
            ctk.CTkFrame(row, fg_color=color, width=6, height=6, corner_radius=3).pack(
                side="left", padx=(0, 8)
            )
            ctk.CTkLabel(row, text=ts, font=self.F_MONO, text_color=TEXT_MUTED, width=64, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=cls.title(), font=self.F_BODY_SM, text_color=TEXT_SECONDARY, anchor="w").pack(
                side="left", padx=(4, 0)
            )
            ctk.CTkLabel(row, text=f"{conf*100:.0f}% {state}", font=self.F_BODY_SM, text_color=TEXT_MUTED).pack(side="right")

    def _update_counter_labels(self):
        self.metric_rows["fertile"].configure(text=str(self.count_fertile))
        self.metric_rows["infertile"].configure(text=str(self.count_infertile))
        self.metric_rows["abnormal"].configure(text=str(self.count_abnormal))
        total = self.count_fertile + self.count_infertile + self.count_abnormal
        self.lbl_total_cnt.configure(text=str(total))


if __name__ == "__main__":
    app = FUHatcheryEdgeApp()
    app.mainloop()
