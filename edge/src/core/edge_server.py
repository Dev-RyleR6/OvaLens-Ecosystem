"""
Edge Telemetry HTTP Server
Lightweight daemon server exposing real-time station diagnostics, hardware metrics,
and live camera snapshots to the web dashboard and backend without blocking edge sorting.
"""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import json
import os
import platform
import socket
import threading
import time
from typing import Any, Dict, Optional
import cv2

from .settings import EdgeSettings


def get_local_ip() -> str:
    """Resolve the host's LAN IPv4 address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class EdgeTelemetryHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress verbose terminal HTTP access logs
        pass

    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS, POST")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-API-Key")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        server: "EdgeTelemetryServer" = self.server  # type: ignore

        if self.path in ("/", "/api/device", "/status", "/api/telemetry"):
            telemetry = server.get_telemetry()
            body = json.dumps({"status": "ok", "device": telemetry}, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif self.path == "/health":
            body = json.dumps({
                "status": "ONLINE",
                "device_id": server.device_id,
                "timestamp": time.time(),
            }).encode("utf-8")
            self.send_response(200)
            self.send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif self.path == "/camera/snapshot":
            jpeg_bytes = server.get_snapshot_jpeg()
            if jpeg_bytes:
                self.send_response(200)
                self.send_cors_headers()
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.send_header("Content-Length", str(len(jpeg_bytes)))
                self.end_headers()
                self.wfile.write(jpeg_bytes)
            else:
                body = json.dumps({"error": "No camera frame available"}).encode("utf-8")
                self.send_response(503)
                self.send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        else:
            self.send_response(404)
            self.send_cors_headers()
            self.end_headers()


class EdgeTelemetryServer:
    def __init__(self, station=None, device_id: Optional[str] = None, host: str = "0.0.0.0",
                 port: int = 8008, camera=None, inference=None, db=None):
        self.station = station
        self.device_id = device_id or (station.device_id if station else os.getenv("DEVICE_ID", "STATION-01-RP5"))
        self.host = host
        self.port = port
        self.camera = camera or (station.camera if station else None)
        self.inference = inference or (station.inference if station else None)
        self.db = db or (station.db if station else None)
        self.start_time = time.time()
        self._httpd: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._is_running = False

    def start(self):
        """Start the HTTP server on a background daemon thread."""
        if self._is_running:
            return
        
        # Try requested port with fallback to next 5 ports if occupied
        bind_port = self.port
        for p in range(bind_port, bind_port + 6):
            try:
                self._httpd = ThreadingHTTPServer((self.host, p), EdgeTelemetryHandler)
                self.port = p
                break
            except OSError:
                continue

        if not self._httpd:
            print(f"[EDGE SERVER WARNING] Could not bind telemetry HTTP server on ports {bind_port}-{bind_port+5}")
            return

        self._httpd.get_telemetry = self.get_telemetry  # type: ignore
        self._httpd.get_snapshot_jpeg = self.get_snapshot_jpeg  # type: ignore
        self._httpd.device_id = self.device_id  # type: ignore

        self._is_running = True
        self._thread = threading.Thread(target=self._serve, daemon=True, name="OvaLens-EdgeTelemetryServer")
        self._thread.start()
        print(f"[EDGE SERVER] Telemetry API live at http://{get_local_ip()}:{self.port}/api/device")

    def _serve(self):
        try:
            self._httpd.serve_forever()
        except Exception:
            pass

    def stop(self):
        """Stop the HTTP server cleanly."""
        if not self._is_running:
            return
        self._is_running = False
        if self._httpd:
            try:
                self._httpd.shutdown()
                self._httpd.server_close()
            except Exception:
                pass
        self._httpd = None

    def get_edge_url(self) -> str:
        return f"http://{get_local_ip()}:{self.port}"

    def get_snapshot_jpeg(self) -> Optional[bytes]:
        """Grab the current camera frame and compress it to JPEG."""
        if not self.camera:
            return None
        try:
            frame = self.camera.snapshot(copy=False)
            if frame is None:
                return None
            success, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if success:
                return encoded.tobytes()
        except Exception:
            pass
        return None

    def get_telemetry(self) -> Dict[str, Any]:
        """Aggregate truthful, real-time edge telemetry."""
        station = self.station
        settings: EdgeSettings = station.settings if station else EdgeSettings()
        camera = self.camera or (station.camera if station else None)
        inference = self.inference or (station.inference if station else None)
        db = self.db or (station.db if station else None)

        # 1. Determine real Station Operational State
        status = "ONLINE"
        if station and getattr(station, "cycle", None) and station.cycle.is_running:
            status = "SCANNING"
        elif station and getattr(station, "calibrated", False):
            status = "READY"
        elif station and getattr(station, "settings_error", ""):
            status = "ERROR"

        # 2. Camera Telemetry
        camera_info = {
            "index": getattr(settings.camera, "index", 0),
            "identity": getattr(camera, "identity", "") or f"Camera #{getattr(settings.camera, 'index', 0)}",
            "resolution": f"{getattr(camera, 'width', 1280)}x{getattr(camera, 'height', 720)}",
            "fps": getattr(camera, "fps", 30),
            "is_mock": getattr(camera, "is_mock_mode", False),
            "status": "Connected" if camera and not camera.is_mock_mode and camera.snapshot(copy=False) is not None else ("Mock Mode" if camera and camera.is_mock_mode else "Disconnected"),
        }

        # 3. AI Model Telemetry
        engine = getattr(inference, "engine", None) if inference else None
        model_version = "YOLOv8n-ONNX"
        if engine:
            model_version = getattr(engine, "engine_type", "YOLOv8n-ONNX")
            if getattr(engine, "model_path", None):
                model_version = f"{os.path.basename(engine.model_path)} ({engine.engine_type})"

        ai_model_info = {
            "engine_type": getattr(engine, "engine_type", "ONNX Runtime FP16") if engine else "ONNX Runtime FP16",
            "model_version": model_version,
            "confidence_threshold": getattr(settings.detection, "confidence", 0.70),
            "sort_confidence": getattr(settings.detection, "sort_confidence", 0.70),
            "iou_threshold": getattr(settings.detection, "iou", 0.45),
            "warmup_complete": getattr(engine, "warmup_complete", True) if engine else False,
        }

        # 4. IoT Rig Hardware Telemetry
        rig_profile = getattr(settings, "rig_profile", "unified_v4")
        boards = getattr(station, "boards", None) if station else None
        ports_status = {}
        board_state: Dict[str, str] = {}

        if boards and hasattr(boards, "conveyor"):
            try:
                c_snap = boards.conveyor.snapshot()
                ports_status["conveyor"] = "CONNECTED" if c_snap.connected else "DISCONNECTED"
                if c_snap.telemetry:
                    board_state = {
                        "fault": str(c_snap.telemetry.get("FAULT", "NONE")),
                        "busy": str(c_snap.telemetry.get("BUSY", "0")),
                        "sensor": str(c_snap.telemetry.get("SENSOR", "0")),
                        "light": str(c_snap.telemetry.get("LIGHT", "0")),
                        "position": str(c_snap.telemetry.get("POSITION", "0")),
                        "reference_valid": str(c_snap.telemetry.get("REFERENCE_VALID", "0")),
                    }
            except Exception:
                ports_status["conveyor"] = "DISCONNECTED"
        else:
            ports_status["conveyor"] = "IDLE"

        if boards and hasattr(boards, "egg"):
            try:
                e_snap = boards.egg.snapshot()
                ports_status["servo"] = "CONNECTED" if e_snap.connected else "DISCONNECTED"
            except Exception:
                ports_status["servo"] = "DISCONNECTED"
        else:
            ports_status["servo"] = "IDLE"

        if boards and hasattr(boards, "light"):
            try:
                l_snap = boards.light.snapshot()
                ports_status["light"] = "CONNECTED" if l_snap.connected else "DISCONNECTED"
            except Exception:
                ports_status["light"] = "DISCONNECTED"
        else:
            ports_status["light"] = "IDLE"

        conveyor_port = getattr(settings, "conveyor_port", "") or "COM5"
        servo_port = "" if rig_profile == "unified_v4" else (getattr(settings, "servo_port", "") or "COM7")
        light_port = "" if rig_profile in ("unified_v4", "dual_v2") else (getattr(settings, "light_port", "") or "COM9")

        iot_rig_info = {
            "rig_profile": rig_profile,
            "conveyor_port": conveyor_port,
            "servo_port": servo_port,
            "light_port": light_port,
            "is_connected": boards is not None,
            "ports_status": ports_status,
            "holder_steps": getattr(settings.calibration, "holder_steps", 1000),
            "sorter_steps": getattr(settings.calibration, "sorter_steps", 367),
            "gate_clearance_steps": getattr(settings.calibration, "gate_clearance_steps", 50),
            "stepper_speed_us": getattr(settings.calibration, "speed_us", 3000),
            "settle_ms": getattr(settings.calibration, "settle_ms", 1500),
            "hold_ms": getattr(settings.calibration, "hold_ms", 300),
            "passage_ms": getattr(settings.calibration, "passage_ms", 500),
            "fertile_angle": getattr(settings.calibration, "fertile_angle", 180),
            "infertile_angle": settings.calibration.infertile_angle,
            "neutral_angle": getattr(settings.calibration, "neutral_angle", 90),
            "silent_idle_enabled": rig_profile == "unified_v4",
            "board_state": board_state,
        }

        # 5. Local Storage & Outbox
        unsynced_count = 0
        if db and hasattr(db, "get_unsynced_count"):
            try:
                unsynced_count = db.get_unsynced_count()
            except Exception:
                pass

        storage_info = {
            "unsynced_scans": unsynced_count,
            "mode": "SQLite WAL",
        }

        # 6. Active Operator / Batch info
        operator_info = {}
        if db and hasattr(db, "get_operator_state"):
            try:
                operator_info = db.get_operator_state() or {}
            except Exception:
                pass

        batch_prefs = {}
        if db and hasattr(db, "get_batch_preferences"):
            try:
                batch_prefs = db.get_batch_preferences() or {}
            except Exception:
                pass

        return {
            "device_id": self.device_id,
            "device_name": os.getenv("DEVICE_NAME", f"OvaLens Edge ({platform.node()})"),
            "hostname": platform.node(),
            "ip_address": get_local_ip(),
            "edge_url": self.get_edge_url(),
            "hardware_platform": f"{platform.system()} {platform.machine()}",
            "os_version": platform.platform(),
            "python_version": platform.python_version(),
            "status": status,
            "uptime_seconds": int(time.time() - self.start_time),
            "camera": camera_info,
            "ai_model": ai_model_info,
            "iot_rig": iot_rig_info,
            "storage": storage_info,
            "active_batch_code": batch_prefs.get("batch_code"),
            "active_operator": operator_info.get("full_name") or operator_info.get("name"),
            "timestamp": time.time(),
        }

