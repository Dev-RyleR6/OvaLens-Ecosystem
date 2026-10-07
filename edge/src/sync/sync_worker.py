"""
Background Network Sync Worker
Asynchronously synchronizes local SQLite egg scans to the central FastAPI / PostgreSQL backend.
"""

import time
import json
import threading
import os
from urllib.parse import quote
from typing import Optional, List, Dict, Any
import requests

from ..db.local_db import LocalDatabaseManager


class BackgroundSyncWorker:
    def __init__(self, db_manager: LocalDatabaseManager, api_base_url: str = "http://localhost:8000",
                 api_key: Optional[str] = None, sync_interval_s: float = 3.0,
                 device_id: Optional[str] = None, device_name: Optional[str] = None,
                 hardware_platform: str = "Edge workstation", model_version: str = "unknown"):
        self.db = db_manager
        self.api_base_url = api_base_url.rstrip("/")
        self.api_key = api_key or os.getenv("API_KEY", "")
        self.sync_interval = sync_interval_s

        self._is_running = False
        self._thread: Optional[threading.Thread] = None
        self._is_online = False
        self._last_sync_time: Optional[float] = None
        self._total_synced = 0
        self.last_error = None
        self._stop_event = threading.Event()
        self._registered_sessions = set()
        self.device_id = device_id
        self.device_name = device_name or device_id
        self.hardware_platform = hardware_platform
        self.model_version = model_version
        self.device_status = "ONLINE"
        self.heartbeat_error = None
        self._heartbeat_thread: Optional[threading.Thread] = None

    def start(self):
        """Start the background synchronization thread."""
        if self._is_running:
            return
        self._is_running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._sync_loop, daemon=True, name="OvaLens-SyncThread")
        self._thread.start()
        if self.device_id:
            self._heartbeat_thread = threading.Thread(
                target=self._heartbeat_loop, daemon=True, name="OvaLens-HeartbeatThread")
            self._heartbeat_thread.start()

    def _heartbeat_loop(self):
        # Independent of scan replay: a large offline backlog cannot starve liveness.
        while not self._stop_event.is_set():
            self._send_heartbeat()
            self._stop_event.wait(15.0)

    def _send_heartbeat(self):
        if not self.api_key or not self.device_id:
            self.heartbeat_error = "Device heartbeat requires API_KEY and DEVICE_ID."
            return
        headers = {"X-API-Key": self.api_key}
        url = f"{self.api_base_url}/api/v1/devices/{quote(self.device_id, safe='')}/heartbeat"
        try:
            response = requests.post(url, json={"status": self.device_status}, headers=headers, timeout=3.0)
            if response.status_code == 404:
                # Register only unknown devices; never overwrite saved calibration on restart.
                registration = requests.post(f"{self.api_base_url}/api/v1/devices/register", json={
                    "device_id": self.device_id, "device_name": self.device_name,
                    "hardware_platform": self.hardware_platform, "model_version": self.model_version,
                }, headers=headers, timeout=3.0)
                registration.raise_for_status()
                response = requests.post(url, json={"status": self.device_status}, headers=headers, timeout=3.0)
            response.raise_for_status()
            self.heartbeat_error = None
        except requests.RequestException as exc:
            self.heartbeat_error = f"Device heartbeat failed: {type(exc).__name__}."

    def _sync_loop(self):
        while self._is_running:
            try:
                self._perform_sync()
            except Exception as e:
                self._is_online = False
                self.last_error = f"Sync failed: {type(e).__name__}: {e}"
            self._stop_event.wait(self.sync_interval)

    def _perform_sync(self):
        if not self.api_key:
            self.last_error = "API_KEY is not configured; scans remain local."
            self._is_online = False
            return
        uncommitted = self.db.get_uncommitted_scans(limit=50)
        if not uncommitted:
            # Still ping health to update online status
            self._check_health()
            return
        session_id = uncommitted[0]["session_id"]
        # Keep each ingestion packet in one session; the backend rollup uses
        # the first session only. Preserve original batch/device/operator IDs.
        uncommitted = [r for r in uncommitted if r["session_id"] == session_id]
        if session_id not in self._registered_sessions:
            session = self.db.get_session_stats(session_id)
            if not session:
                self.last_error = "Local scan references a missing session; sync stopped."
                self._is_online = False
                return
            payload = {key: session[key] for key in (
                "session_id", "batch_id", "device_id", "stage", "operator_name", "started_at")}
            if not self.register_session(payload):
                return
            self._registered_sessions.add(session_id)

        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key
        }

        # Transform local SQLite records into backend ScanSyncPayload format
        payload_scans = []
        scan_ids = []

        for r in uncommitted:
            det_raw = r.get("detections_json")
            try:
                detections = json.loads(det_raw) if det_raw else []
            except Exception:
                detections = []

            payload_scans.append({
                "scan_id": r["scan_id"],
                "session_id": r["session_id"],
                "batch_id": r["batch_id"],
                "sequence_number": r["sequence_number"],
                "final_class": r["final_class"],
                "confidence": float(r["confidence"]),
                "inference_ms": int(r["inference_ms"]),
                "routing_action": r["routing_action"],
                "image_url": None,
                "detections": detections,
                "scanned_at": r["scanned_at"]
            })
            scan_ids.append(r["scan_id"])

        url = f"{self.api_base_url}/api/v1/scans/sync"
        resp = requests.post(url, json={"scans": payload_scans}, headers=headers, timeout=5.0)

        if resp.status_code == 200:
            acknowledgement = resp.json()
            received = acknowledgement.get("total_received")
            synced = acknowledgement.get("synced_count")
            duplicates = acknowledgement.get("duplicates_ignored")
            if (acknowledgement.get("status") != "success" or type(received) is not int or received != len(scan_ids)
                    or type(synced) is not int or type(duplicates) is not int
                    or synced < 0 or duplicates < 0 or synced + duplicates != len(scan_ids)):
                self.last_error = "Invalid sync acknowledgement; local scans retained."
                self._is_online = False
                return
            self.db.mark_scans_synced(scan_ids)
            self.last_error = None
            self._is_online = True
            self._last_sync_time = time.time()
            self._total_synced += len(scan_ids)
        else:
            self._is_online = False
            self.last_error = f"Scan sync rejected (HTTP {resp.status_code}); local scans retained."

    def _check_health(self):
        try:
            url = f"{self.api_base_url}/api/v1/health"
            resp = requests.get(url, timeout=2.0)
            self._is_online = (resp.status_code == 200)
        except Exception:
            self._is_online = False

    def fetch_active_batches(self) -> List[Dict[str, Any]]:
        """Fetch list of actively incubating batches from central server."""
        try:
            url = f"{self.api_base_url}/api/v1/batches/active"
            headers = {"X-API-Key": self.api_key}
            resp = requests.get(url, headers=headers, timeout=3.0)
            if resp.status_code == 200:
                return resp.json()
            return []
        except Exception:
            return []

    def register_session(self, session_data: Dict[str, Any]) -> bool:
        """Register newly started session with central backend."""
        try:
            url = f"{self.api_base_url}/api/v1/sessions"
            headers = {
                "Content-Type": "application/json",
                "X-API-Key": self.api_key
            }
            resp = requests.post(url, json=session_data, headers=headers, timeout=4.0)
            if resp.status_code in (200, 201):
                body = resp.json()
                if all(str(body.get(key)) == str(session_data[key])
                       for key in ("session_id", "batch_id", "device_id", "stage", "operator_name")):
                    return True
                self.last_error = "Session acknowledgement does not match local identity."
                self._is_online = False
                return False
            self.last_error = f"Session registration rejected (HTTP {resp.status_code})."
            self._is_online = False
            return False
        except Exception as exc:
            self.last_error = f"Session registration failed: {type(exc).__name__}."
            self._is_online = False
            return False

    @property
    def is_online(self) -> bool:
        return self._is_online

    @property
    def total_synced(self) -> int:
        return self._total_synced

    def stop(self):
        self._is_running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=1.0)
