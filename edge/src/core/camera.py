"""
Thread-Safe Camera Frame Grabber
Continuously pulls frames from OpenCV VideoCapture into an atomic buffer to prevent hardware queue lag.
Supports clean session on-demand start/stop lifecycle.
"""

import time
import threading
import sys
import queue
from concurrent.futures import Future
from dataclasses import dataclass
from typing import Optional, Tuple
import cv2
import numpy as np


@dataclass(frozen=True)
class CameraFrame:
    sequence: int
    captured_at: float
    settings_revision: int
    image: np.ndarray


class CameraGrabber:
    def __init__(self, camera_index: int = 0, width: int = 1280, height: int = 720, fps: int = 30,
                 allow_mock: bool = False):
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.fps = fps

        self.cap: Optional[cv2.VideoCapture] = None
        self._lock = threading.Lock()
        self._latest_frame: Optional[np.ndarray] = None
        self._is_running = False
        self._thread: Optional[threading.Thread] = None
        self._is_mock_mode = False
        self._fps_count = 0
        self._current_fps = 0.0
        self._last_fps_time = time.time()
        self._static_bg: Optional[np.ndarray] = None
        self.allow_mock = allow_mock
        self.last_error = None
        self._last_frame_at = 0.0
        self._sequence = 0
        self.settings_revision = 0
        self._requests = queue.Queue(maxsize=4)
        self.property_report = {}
        self.identity = ""
        self._discard_frames = 0
        self.initial_settings = None

    def _init_static_bg(self):
        """Pre-render darkroom candling aperture background once to minimize CPU cycles."""
        bg = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        cv2.circle(bg, (self.width // 2, self.height // 2), 260, (15, 35, 80), -1)
        cv2.circle(bg, (self.width // 2, self.height // 2), 180, (20, 60, 160), -1)
        self._static_bg = bg

    def start(self):
        """Open/read the camera on its worker; never silently substitute mock frames."""
        if self._is_running:
            return
        if self._thread and self._thread.is_alive():
            raise RuntimeError("Previous camera worker is still stopping")
        self.last_error = None
        self._is_running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True,
                                        name="OvaLens-CameraThread")
        self._thread.start()

    def _open_camera(self):
        if self.allow_mock:
            self._is_mock_mode = True
            self._init_static_bg()
            return
        backend = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_V4L2
        self.cap = cv2.VideoCapture(self.camera_index, backend)
        if not self.cap.isOpened():
            self.cap.release()
            self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            raise RuntimeError("Camera unavailable; check its index and USB connection")
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self._is_mock_mode = False
        self.identity = f"opencv:{self.camera_index}:{self.cap.getBackendName()}"

    def apply_settings(self, settings, timeout=10):
        """Called from an operation worker; only the capture thread touches VideoCapture."""
        future = Future()
        self._requests.put_nowait((settings, future))
        self.start()
        return future.result(timeout=timeout)

    def _apply_on_worker(self, settings):
        from .settings import EdgeSettings
        EdgeSettings(camera=settings).validate()
        if self.allow_mock:
            raise RuntimeError("Camera property tuning requires a real camera")
        if settings.index != self.camera_index:
            self.cap.release()
            self.camera_index = settings.index
            self.width, self.height, self.fps = settings.width, settings.height, settings.fps
            self._open_camera()
        if settings.identity and settings.identity != self.identity:
            raise RuntimeError("Camera identity changed; confirm this device before applying defaults")
        properties = {
            "width": cv2.CAP_PROP_FRAME_WIDTH, "height": cv2.CAP_PROP_FRAME_HEIGHT,
            "fps": cv2.CAP_PROP_FPS, "auto_exposure": cv2.CAP_PROP_AUTO_EXPOSURE,
            "autofocus": cv2.CAP_PROP_AUTOFOCUS, "auto_white_balance": cv2.CAP_PROP_AUTO_WB,
            "exposure": cv2.CAP_PROP_EXPOSURE, "gain": cv2.CAP_PROP_GAIN,
            "focus": cv2.CAP_PROP_FOCUS, "white_balance": cv2.CAP_PROP_WB_TEMPERATURE,
        }
        report = {}
        for name, prop in properties.items():
            requested = getattr(settings, name)
            try:
                accepted = self.cap.set(prop, requested) if requested is not None else None
                actual = self.cap.get(prop)
                verified = (accepted is True and np.isfinite(actual)
                            and abs(actual - requested) <= max(.01, abs(requested) * .01))
                report[name] = {"requested": requested, "actual": actual if np.isfinite(actual) else None,
                                "status": "verified readback" if verified else
                                "rejected / unsupported" if accepted is False else "unverified"}
            except (cv2.error, ValueError) as exc:
                report[name] = {"requested": requested, "actual": None, "status": str(exc)}
        self.width, self.height, self.fps = settings.width, settings.height, settings.fps
        self.property_report = report
        with self._lock:
            self.settings_revision += 1
            self._latest_frame = None
            self._last_frame_at = 0.0
        self._discard_frames = max(3, int(settings.fps * .3))
        return {"identity": self.identity, "properties": report, "revision": self.settings_revision}

    def snapshot(self, copy=True):
        with self._lock:
            if not self._is_running or self._latest_frame is None or time.monotonic() - self._last_frame_at > .5:
                return None
            return CameraFrame(self._sequence, self._last_frame_at, self.settings_revision,
                               self._latest_frame.copy() if copy else self._latest_frame)

    def _capture_loop(self):
        try:
            self._open_camera()
            if self.initial_settings is not None and self._requests.empty() and not self.allow_mock:
                self._apply_on_worker(self.initial_settings)
            while self._is_running:
                try:
                    settings, future = self._requests.get_nowait()
                except queue.Empty:
                    pass
                else:
                    if future.set_running_or_notify_cancel():
                        try:
                            future.set_result(self._apply_on_worker(settings))
                        except Exception as exc:
                            future.set_exception(exc)
                if self._is_mock_mode:
                    frame = self._generate_mock_candling_frame()
                    time.sleep(1 / max(1, self.fps))
                else:
                    ret, frame = self.cap.read()
                    if not ret or frame is None:
                        raise RuntimeError("Camera frame acquisition failed; reconnect before restarting")
                if self._discard_frames:
                    self._discard_frames -= 1
                    continue
                with self._lock:
                    self._latest_frame = frame
                    self._last_frame_at = time.monotonic()
                    self._sequence += 1
                self._update_fps()
        except Exception as exc:
            self.last_error = str(exc)
        finally:
            self._is_running = False
            if self.cap:
                self.cap.release()
                self.cap = None
            with self._lock:
                self._latest_frame = None
                self._last_frame_at = 0.0
            while not self._requests.empty():
                try:
                    _, future = self._requests.get_nowait()
                    future.set_exception(RuntimeError(self.last_error or "Camera stopped"))
                except queue.Empty:
                    break

    def _update_fps(self):
        self._fps_count += 1
        now = time.time()
        if now - self._last_fps_time >= 1.0:
            self._current_fps = round(self._fps_count / (now - self._last_fps_time), 1)
            self._fps_count = 0
            self._last_fps_time = now

    def _generate_mock_candling_frame(self) -> np.ndarray:
        """Create a synthetic high-contrast duck egg candling image using cached background."""
        if self._static_bg is not None:
            img = self._static_bg.copy()
        else:
            img = np.zeros((self.height, self.width, 3), dtype=np.uint8)

        # Draw egg silhouette in center
        t = time.time()
        offset_y = int(np.sin(t * 1.5) * 15)
        center = (self.width // 2, (self.height // 2) + offset_y)
        axes = (140, 190)

        # Egg body (warm amber glow)
        cv2.ellipse(img, center, axes, 0, 0, 360, (30, 140, 240), -1)

        # Embryo / blood spider veins
        cv2.circle(img, (center[0] - 20, center[1] - 15), 35, (10, 40, 160), -1)
        for angle in np.linspace(0, 2 * np.pi, 8):
            ex = int(center[0] - 20 + np.cos(angle) * 75)
            ey = int(center[1] - 15 + np.sin(angle) * 75)
            cv2.line(img, (center[0] - 20, center[1] - 15), (ex, ey), (15, 50, 180), 2)

        return img

    def get_latest_frame(self, copy: bool = False) -> Optional[np.ndarray]:
        """Return the most recent video frame atomically."""
        if not self._is_running:
            return None
        with self._lock:
            if self._latest_frame is not None and time.monotonic() - self._last_frame_at <= 0.5:
                return self._latest_frame.copy() if copy else self._latest_frame
            return None

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def current_fps(self) -> float:
        return self._current_fps if self._is_running else 0.0

    @property
    def is_mock_mode(self) -> bool:
        return self._is_mock_mode

    def calibrate_optical_tunnel(self) -> dict:
        """
        Pre-shift optical diagnostic routine.
        Analyzes candling aperture illumination, ambient baseline, and contrast.
        """
        frame = self.get_latest_frame(copy=True)
        if frame is None:
            return {
                "status": "UNAVAILABLE",
                "message": "No active video stream from camera aperture.",
                "mean_luminance": 0.0,
                "contrast_ratio": 0.0,
            }

        # Convert to HSV and evaluate V channel (Luminance)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        v_channel = hsv[:, :, 2]
        
        # Center aperture ROI (central 40% of frame)
        h, w = v_channel.shape
        cx1, cx2 = int(w * 0.3), int(w * 0.7)
        cy1, cy2 = int(h * 0.3), int(h * 0.7)
        center_roi = v_channel[cy1:cy2, cx1:cx2]
        
        center_mean = float(np.mean(center_roi))
        ambient_mean = float(np.mean(v_channel))
        contrast_ratio = round(center_mean / max(1.0, ambient_mean), 2)

        if center_mean < 45.0:
            status = "LOW_ILLUMINATION"
            message = "Candling LED intensity is low. Verify 10W high-power candler power supply."
        elif center_mean > 240.0:
            status = "OVEREXPOSED"
            message = "Aperture saturation detected. Lower exposure or increase optical diffuser distance."
        else:
            status = "OPTIMAL"
            message = f"Optical candling tunnel calibrated ({center_mean:.1f} lux center luminance, {contrast_ratio}x contrast ratio)."

        return {
            "status": status,
            "message": message,
            "mean_luminance": round(center_mean, 1),
            "ambient_luminance": round(ambient_mean, 1),
            "contrast_ratio": contrast_ratio,
        }

    def request_stop(self):
        """Immediate UI-safe cancellation; the worker owns handle release."""
        self._is_running = False

    def stop(self):
        """The capture worker owns its camera handle, including release."""
        self.request_stop()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        if self._thread and self._thread.is_alive():
            self.last_error = "Camera worker did not stop within one second"
        else:
            self._thread = None
        with self._lock:
            self._latest_frame = None
            self._last_frame_at = 0.0
        self._current_fps = 0.0
