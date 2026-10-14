"""
Background Network Sync Worker
Asynchronously synchronizes local SQLite egg scans to the central FastAPI / PostgreSQL backend.
"""

import time
import json
import threading
import os
import hashlib
from pathlib import Path
from datetime import datetime
from uuid import UUID
from urllib.parse import quote
from typing import Optional, List, Dict, Any
import requests

from ..db.local_db import LocalDatabaseManager
from ..core.batches import BATCH_FIELDS, same_batch


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
        self.pending_session_ends = 0
        self.pending_batches = 0
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
        errors = []
        self._sync_batches()
        if self.last_error:
            errors.append(self.last_error)
        pending = self.db.get_pending_scan_sessions(limit=5)
        if not pending:
            self._check_health()
        for session in pending:
            if self._stop_event.is_set():
                break
            session_id = session["session_id"]
            self.db.mark_session_sync_attempt(session_id)
            self.last_error = None
            try:
                self._sync_scan_records(session_id)
            except Exception as exc:
                self._is_online = False
                self.last_error = f"Scan sync failed: {type(exc).__name__}; saved locally for retry."
            if self.last_error:
                self.db.mark_session_sync_attempt(session_id, self.last_error)
                errors.append(self.last_error)
        self.last_error = None
        self._sync_images()
        if self.last_error:
            errors.append(self.last_error)
        self.last_error = None
        self._sync_session_ends()
        if self.last_error:
            errors.append(self.last_error)
        self.last_error = " | ".join(dict.fromkeys(errors)) or None
        self.pending_session_ends = self.db.get_pending_session_end_count()
        self.pending_batches = self.db.get_pending_batch_count()

    def _sync_batches(self):
        errors = []
        for batch in self.db.get_pending_batches(limit=5):
            if self._stop_event.is_set():
                break
            batch_id = batch["batch_id"]
            self.db.mark_batch_attempt(batch_id)
            blocked = None
            try:
                payload = {key: batch[key] for key in (*BATCH_FIELDS, "device_id", "operator_name")}
                response = requests.post(f"{self.api_base_url}/api/v1/batches/register", json=payload,
                    headers={"X-API-Key": self.api_key}, timeout=4.0)
                if response.status_code == 409:
                    blocked = True
                    raise ValueError(f"Batch {batch['batch_code']} conflicts with a backend record. Saved scans retained; ask a manager to check the batch details.")
                if response.status_code != 200:
                    raise ValueError(f"Batch {batch['batch_code']} registration rejected (HTTP {response.status_code}); saved locally for retry.")
                acknowledgement = response.json()
                try:
                    matches = isinstance(acknowledgement, dict) and same_batch(batch, acknowledgement)
                except (ValueError, TypeError):
                    matches = False
                if not matches:
                    blocked = True
                    raise ValueError(f"Batch {batch['batch_code']} acknowledgement does not match saved details.")
                self.db.mark_batch_attempt(batch_id, synced=True)
                self._is_online, self._last_sync_time = True, time.time()
            except Exception as exc:
                if isinstance(exc, requests.RequestException):
                    self._is_online = False
                    error = f"Batch {batch['batch_code']} registration failed: {type(exc).__name__}; saved locally for retry."
                else:
                    error = str(exc)
                self.db.mark_batch_attempt(batch_id, error, blocked=blocked)
                errors.append(error)
        self.last_error = " | ".join(dict.fromkeys(errors)) or None

    def _sync_scan_records(self, session_id=None):
        uncommitted = self.db.get_uncommitted_scans(limit=50, session_id=session_id)
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

    def _sync_images(self):
        """Replay a bounded durable photo outbox, independently of conveyor work."""
        failures = 0
        for row in self.db.get_pending_scan_images(limit=5):
            if self._stop_event.is_set():
                break
            scan_id = row["scan_id"]
            try:
                canonical_id = str(UUID(scan_id))
                expected = (Path(self.db.db_path).parent / "local_scans" / (canonical_id + ".jpg")).resolve()
                path = Path(row["image_path"]).resolve()
                if path != expected:
                    raise ValueError("Photo path does not match its scan ID")
                with path.open("rb") as stream:
                    data = stream.read(10 * 1024 * 1024 + 1)
                if not data or len(data) > 10 * 1024 * 1024:
                    raise ValueError("Saved photo is empty or exceeds 10 MiB")
                digest = hashlib.sha256(data).hexdigest()
                response = requests.post(f"{self.api_base_url}/api/v1/scans/upload-image",
                    headers={"X-API-Key": self.api_key}, data={"scan_id": scan_id},
                    files={"file": (canonical_id + ".jpg", data, "image/jpeg")}, timeout=5.0)
                if response.status_code != 200:
                    raise ValueError(f"Photo upload rejected (HTTP {response.status_code})")
                ack = response.json()
                image_url = f"/storage/{canonical_id}.jpg"
                if (ack.get("status") != "success" or ack.get("scan_id") != scan_id
                        or ack.get("image_url") != image_url or ack.get("sha256") != digest
                        or ack.get("size_bytes") != len(data)):
                    raise ValueError("Invalid photo acknowledgement")
                self.db.mark_scan_image_synced(scan_id, image_url)
                self._last_sync_time = time.time()
            except (OSError, ValueError, requests.RequestException) as exc:
                if isinstance(exc, requests.RequestException):
                    self._is_online = False
                failures += 1
                self.db.mark_scan_image_attempt(scan_id, str(exc))
        if failures:
            self.last_error = f"{failures} scan photo upload(s) pending; saved locally for retry."

    @staticmethod
    def _session_payload(session):
        return {key: session[key] for key in (
            "session_id", "batch_id", "device_id", "stage", "operator_name", "started_at")}

    def _sync_session_ends(self):
        """Replay closed runs, including pre-upgrade runs, after every scan is acknowledged."""
        errors = []
        for session in self.db.get_pending_session_ends(limit=5):
            if self._stop_event.is_set():
                break
            session_id = session["session_id"]
            self.db.mark_session_sync_attempt(session_id)
            self.last_error = None
            try:
                if session_id not in self._registered_sessions:
                    if not self.register_session(self._session_payload(session)):
                        raise RuntimeError(self.last_error)
                    self._registered_sessions.add(session_id)
                response = requests.put(f"{self.api_base_url}/api/v1/sessions/{session_id}/end",
                    json={"ended_at": session["ended_at"]}, headers={"X-API-Key": self.api_key}, timeout=4.0)
                if response.status_code != 200:
                    if response.status_code == 404:
                        self._registered_sessions.discard(session_id)
                    raise ValueError(f"Session completion rejected (HTTP {response.status_code})")
                body = response.json()
                expected = self._session_payload(session)
                matches = all(str(body.get(key)) == str(expected[key]) for key in (
                    "session_id", "batch_id", "device_id", "stage", "operator_name"))
                if (not matches or type(body.get("total_scanned")) is not int
                        or body["total_scanned"] != session["total_scanned"]
                        or datetime.fromisoformat(body.get("ended_at") or "") != datetime.fromisoformat(session["ended_at"])):
                    raise ValueError("Session completion acknowledgement does not match local records")
                self.db.mark_session_end_synced(session_id, session["ended_at"])
                self._last_sync_time = time.time()
            except Exception as exc:
                if isinstance(exc, requests.RequestException):
                    self._is_online = False
                    error = f"Session completion failed: {type(exc).__name__}; saved locally for retry."
                else:
                    error = str(exc)
                self.db.mark_session_sync_attempt(session_id, error)
                errors.append(error)
        self.last_error = " | ".join(dict.fromkeys(errors)) or None

    def _check_health(self):
        try:
            url = f"{self.api_base_url}/api/v1/health"
            resp = requests.get(url, timeout=2.0)
            self._is_online = (resp.status_code == 200)
            if self._is_online:
                self.last_error = None
        except Exception:
            self._is_online = False

    def fetch_active_batches(self) -> List[Dict[str, Any]]:
        """Refresh the offline cache; local pending batches and legacy references remain selectable."""
        try:
            url = f"{self.api_base_url}/api/v1/batches/active"
            headers = {"X-API-Key": self.api_key}
            resp = requests.get(url, headers=headers, timeout=3.0)
            if resp.status_code == 200:
                self.db.cache_batches(resp.json())
        except Exception:
            pass
        return self.db.list_available_batches()

    def register_session(self, session_data: Dict[str, Any]) -> bool:
        """Register newly started session with central backend."""
        try:
            batch = self.db.get_local_batch(session_data["batch_id"])
            if batch is not None and batch["synced_at"] is None:
                self.last_error = batch["sync_error"] or f"Batch {batch['batch_code']} saved locally; registration pending."
                return False
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
            self.last_error = (f"Batch {session_data['batch_id']} is missing on the backend (HTTP 404). "
                "Complete its details in Edge > Batch setup, or create it in Dashboard > Batches with this exact code. Sync retries automatically."
                if resp.status_code == 404 else f"Session registration rejected (HTTP {resp.status_code}).")
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
