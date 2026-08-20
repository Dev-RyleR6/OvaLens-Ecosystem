"""
Local SQLite Manager with Write-Ahead Logging (WAL) Mode
Ensures non-blocking, zero-latency local scan recording on the conveyor edge machine.
"""

import os
import sqlite3
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any


class LocalDatabaseManager:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            db_path = os.path.join(base_dir, "db", "local_scans.db")

        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        # Enable WAL mode for high-concurrency read/write
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS local_sessions (
                    session_id TEXT PRIMARY KEY,
                    batch_id TEXT NOT NULL,
                    device_id TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    operator_name TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    total_scanned INTEGER DEFAULT 0,
                    fertile_count INTEGER DEFAULT 0,
                    infertile_count INTEGER DEFAULT 0,
                    abnormal_count INTEGER DEFAULT 0,
                    avg_inference_ms REAL DEFAULT 0.0
                );
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS local_scans (
                    scan_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    batch_id TEXT NOT NULL,
                    sequence_number INTEGER NOT NULL,
                    final_class TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    inference_ms INTEGER NOT NULL,
                    routing_action TEXT NOT NULL,
                    image_path TEXT,
                    detections_json TEXT,
                    scanned_at TEXT NOT NULL,
                    is_synced INTEGER DEFAULT 0,
                    synced_at TEXT,
                    FOREIGN KEY (session_id) REFERENCES local_sessions(session_id)
                );
            """)

            conn.execute("CREATE INDEX IF NOT EXISTS idx_scans_sync ON local_scans(is_synced);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_scans_session ON local_scans(session_id);")
            conn.commit()

    def create_session(self, session_id: str, batch_id: str, device_id: str, stage: str, operator_name: str) -> Dict[str, Any]:
        started_at = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO local_sessions (session_id, batch_id, device_id, stage, operator_name, started_at)
                VALUES (?, ?, ?, ?, ?, ?);
            """, (session_id, batch_id, device_id, stage, operator_name, started_at))
            conn.commit()

        return {
            "session_id": session_id,
            "batch_id": batch_id,
            "device_id": device_id,
            "stage": stage,
            "operator_name": operator_name,
            "started_at": started_at
        }

    def record_scan(self, scan_id: str, session_id: str, batch_id: str, sequence_number: int,
                    final_class: str, confidence: float, inference_ms: int, routing_action: str,
                    detections: list, image_path: Optional[str] = None) -> Dict[str, Any]:
        scanned_at = datetime.now(timezone.utc).isoformat()
        det_json = json.dumps(detections)

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO local_scans (
                    scan_id, session_id, batch_id, sequence_number,
                    final_class, confidence, inference_ms, routing_action,
                    image_path, detections_json, scanned_at, is_synced
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0);
            """, (
                scan_id, session_id, batch_id, sequence_number,
                final_class, confidence, inference_ms, routing_action,
                image_path, det_json, scanned_at
            ))

            # Update session rollup counters
            col = "fertile_count" if final_class == "FERTILE" else ("infertile_count" if final_class == "INFERTILE" else "abnormal_count")
            conn.execute(f"""
                UPDATE local_sessions
                SET total_scanned = total_scanned + 1,
                    {col} = {col} + 1
                WHERE session_id = ?;
            """, (session_id,))
            conn.commit()

        return {
            "scan_id": scan_id,
            "sequence_number": sequence_number,
            "final_class": final_class,
            "confidence": confidence,
            "routing_action": routing_action,
            "inference_ms": inference_ms,
            "scanned_at": scanned_at
        }

    def get_uncommitted_scans(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch pending unsynced scans for the background network worker."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM local_scans
                WHERE is_synced = 0
                ORDER BY sequence_number ASC
                LIMIT ?;
            """, (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def mark_scans_synced(self, scan_ids: List[str]):
        """Mark a batch of scan UUIDs as successfully committed to the central PostgreSQL database."""
        if not scan_ids:
            return
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            placeholders = ",".join("?" * len(scan_ids))
            conn.execute(f"""
                UPDATE local_scans
                SET is_synced = 1, synced_at = ?
                WHERE scan_id IN ({placeholders});
            """, [now] + scan_ids)
            conn.commit()

    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM local_sessions WHERE session_id = ?;", (session_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return {}

    def get_recent_scans(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT scan_id, sequence_number, final_class, confidence, inference_ms, routing_action, scanned_at, is_synced
                FROM local_scans
                ORDER BY sequence_number DESC
                LIMIT ?;
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
