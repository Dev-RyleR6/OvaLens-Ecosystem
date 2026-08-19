"""
Background Network Sync Worker
Asynchronously synchronizes local SQLite egg scans to the central FastAPI / PostgreSQL backend.
"""

import time
import json
import threading
from typing import Optional, List, Dict, Any
import requests

from ..db.local_db import LocalDatabaseManager


class BackgroundSyncWorker:
    def __init__(self, db_manager: LocalDatabaseManager, api_base_url: str = "http://localhost:8000",
                 api_key: str = "dev-api-key-123", sync_interval_s: float = 3.0):
        self.db = db_manager
        self.api_base_url = api_base_url.rstrip("/")
        self.api_key = api_key
        self.sync_interval = sync_interval_s

        self._is_running = False
        self._thread: Optional[threading.Thread] = None
        self._is_online = False
        self._last_sync_time: Optional[float] = None
        self._total_synced = 0

    def start(self):
        """Start the background synchronization thread."""
        if self._is_running:
            return
        self._is_running = True
        self._thread = threading.Thread(target=self._sync_loop, daemon=True, name="OvaLens-SyncThread")
        self._thread.start()

    def _sync_loop(self):
        while self._is_running:
            try:
                self._perform_sync()
            except Exception as e:
                self._is_online = False
            time.sleep(self.sync_interval)

    def _perform_sync(self):
        uncommitted = self.db.get_uncommitted_scans(limit=50)
        if not uncommitted:
            # Still ping health to update online status
            self._check_health()
            return

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
            self.db.mark_scans_synced(scan_ids)
            self._is_online = True
            self._last_sync_time = time.time()
            self._total_synced += len(scan_ids)
        else:
            self._is_online = False

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
            return resp.status_code == 201
        except Exception:
            return False

    @property
    def is_online(self) -> bool:
        return self._is_online

    @property
    def total_synced(self) -> int:
        return self._total_synced

    def stop(self):
        self._is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
