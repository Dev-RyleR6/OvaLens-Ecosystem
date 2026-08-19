"""
Thread-Safe Camera Frame Grabber
Continuously pulls frames from OpenCV VideoCapture into an atomic buffer to prevent hardware queue lag.
"""

import time
import threading
from typing import Optional, Tuple
import cv2
import numpy as np


class CameraGrabber:
    def __init__(self, camera_index: int = 0, width: int = 1280, height: int = 720, fps: int = 30):
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

    def start(self):
        """Initialize camera hardware and start continuous frame grabber thread."""
        if self._is_running:
            return

        self._open_camera()
        self._is_running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True, name="OvaLens-CameraThread")
        self._thread.start()

    def _open_camera(self):
        # Try DirectShow on Windows, default on Linux
        try:
            self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                self.cap = cv2.VideoCapture(self.camera_index)
        except Exception:
            self.cap = cv2.VideoCapture(self.camera_index)

        if self.cap and self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimum buffer to prevent lag
            self._is_mock_mode = False
        else:
            print(f"[WARN] Physical camera {self.camera_index} not detected. Enabling Synthetic Egg Generator.")
            self._is_mock_mode = True

    def _capture_loop(self):
        while self._is_running:
            if not self._is_mock_mode and self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    with self._lock:
                        self._latest_frame = frame
                    self._update_fps()
                else:
                    time.sleep(0.01)
            else:
                # Generate synthetic candling frame with a moving egg silhouette
                frame = self._generate_mock_candling_frame()
                with self._lock:
                    self._latest_frame = frame
                self._update_fps()
                time.sleep(1.0 / self.fps)

    def _update_fps(self):
        self._fps_count += 1
        now = time.time()
        if now - self._last_fps_time >= 1.0:
            self._current_fps = round(self._fps_count / (now - self._last_fps_time), 1)
            self._fps_count = 0
            self._last_fps_time = now

    def _generate_mock_candling_frame(self) -> np.ndarray:
        """Create a synthetic high-contrast duck egg candling image."""
        img = np.zeros((self.height, self.width, 3), dtype=np.uint8)

        # Candling ambient background glow
        cv2.circle(img, (self.width // 2, self.height // 2), 260, (15, 35, 80), -1)
        cv2.circle(img, (self.width // 2, self.height // 2), 180, (20, 60, 160), -1)

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

        # Text overlay
        cv2.putText(img, "OvaLens Synthetic Candling Stream", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)

        return img

    def get_latest_frame(self) -> Optional[np.ndarray]:
        """Return the most recent video frame atomically."""
        with self._lock:
            if self._latest_frame is not None:
                return self._latest_frame.copy()
            return None

    @property
    def current_fps(self) -> float:
        return self._current_fps

    @property
    def is_mock_mode(self) -> bool:
        return self._is_mock_mode

    def stop(self):
        """Safely release camera resources and stop thread."""
        self._is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        if self.cap and self.cap.isOpened():
            self.cap.release()
            self.cap = None
