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
        # Enable WAL mode and memory cache pragmas for zero-lag high-throughput recording
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA cache_size = -8000;")       # 8MB memory cache
        conn.execute("PRAGMA mmap_size = 268435456;")     # 256MB memory map
        conn.execute("PRAGMA temp_store = MEMORY;")
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
            conn.execute("CREATE INDEX IF NOT EXISTS idx_scans_batch_seq ON local_scans(batch_id, sequence_number);")
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

    def get_unsynced_count(self) -> int:
        """Return total number of scans pending network synchronization."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM local_scans WHERE is_synced = 0;")
            return cursor.fetchone()[0]

    def mark_scans_synced(self, scan_ids: List[str]):
        """Mark a batch of scan UUIDs as successfully committed to central PostgreSQL."""
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

    def complete_session(self, session_id: str, ended_at: Optional[str] = None) -> Dict[str, Any]:
        """Finalize session metadata, commit counts, and execute SQLite WAL checkpoint."""
        if not ended_at:
            ended_at = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE local_sessions
                SET ended_at = ?
                WHERE session_id = ? AND (ended_at IS NULL OR ended_at = '');
            """, (ended_at, session_id))
            conn.commit()
            # Run a passive WAL checkpoint to flush pending transactions to disk safely
            try:
                conn.execute("PRAGMA wal_checkpoint(PASSIVE);")
            except Exception:
                pass
        return self.get_session_stats(session_id)

    def get_scans_by_batch(self, batch_id: str, limit: int = 300, class_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch scans for a batch with optional class filtering (FERTILE, INFERTILE, ABNORMAL)."""
        with self._get_connection() as conn:
            if class_filter and class_filter != "ALL":
                cursor = conn.execute("""
                    SELECT sequence_number, scan_id, batch_id, session_id, final_class, confidence, inference_ms, routing_action, scanned_at, is_synced
                    FROM local_scans
                    WHERE batch_id = ? AND final_class = ?
                    ORDER BY sequence_number DESC
                    LIMIT ?;
                """, (batch_id, class_filter, limit))
            else:
                cursor = conn.execute("""
                    SELECT sequence_number, scan_id, batch_id, session_id, final_class, confidence, inference_ms, routing_action, scanned_at, is_synced
                    FROM local_scans
                    WHERE batch_id = ?
                    ORDER BY sequence_number DESC
                    LIMIT ?;
                """, (batch_id, limit))
            return [dict(row) for row in cursor.fetchall()]

    def export_batch_csv(self, batch_id: str, class_filter: Optional[str] = None, output_dir: Optional[str] = None) -> str:
        """Export batch scans to CSV, optionally filtered by class."""
        import csv
        if output_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            output_dir = os.path.join(base_dir, "exports")
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filter_tag = f"_{class_filter.lower()}" if class_filter and class_filter != "ALL" else ""
        filename = f"OvaLens_{batch_id}{filter_tag}_{timestamp}.csv"
        filepath = os.path.join(output_dir, filename)

        scans = self.get_scans_by_batch(batch_id, limit=5000, class_filter=class_filter)
        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["#", "Scan ID", "Batch Code", "Classification", "Confidence", "Action", "Latency (ms)", "Timestamp (UTC)", "Server Synced"])
            for r in scans:
                writer.writerow([
                    r["sequence_number"],
                    r["scan_id"],
                    r["batch_id"],
                    r["final_class"],
                    f"{r['confidence']*100:.2f}%",
                    r["routing_action"],
                    r["inference_ms"],
                    r["scanned_at"],
                    "YES" if r["is_synced"] else "NO"
                ])
        return filepath

    def export_session_csv(self, session_id: str, output_dir: Optional[str] = None) -> str:
        """Generate a complete, timestamped CSV export report of an egg sorting run."""
        import csv
        if output_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            output_dir = os.path.join(base_dir, "exports")
        os.makedirs(output_dir, exist_ok=True)

        session_stats = self.get_session_stats(session_id)
        batch_id = session_stats.get("batch_id", "BATCH-UNKNOWN")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"OvaLens_Report_{batch_id}_{timestamp}.csv"
        filepath = os.path.join(output_dir, filename)

        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT sequence_number, scan_id, batch_id, final_class, confidence, routing_action, inference_ms, scanned_at, is_synced
                FROM local_scans
                WHERE session_id = ?
                ORDER BY sequence_number ASC;
            """, (session_id,))
            rows = cursor.fetchall()

        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["#", "Scan ID", "Batch Code", "Classification", "Confidence", "Action", "Latency (ms)", "Timestamp (UTC)", "Server Synced"])
            for r in rows:
                writer.writerow([
                    r["sequence_number"],
                    r["scan_id"],
                    r["batch_id"],
                    r["final_class"],
                    f"{r['confidence']*100:.2f}%",
                    r["routing_action"],
                    r["inference_ms"],
                    r["scanned_at"],
                    "YES" if r["is_synced"] else "NO"
                ])

        return filepath
