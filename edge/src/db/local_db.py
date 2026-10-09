"""
Local SQLite Manager with Write-Ahead Logging (WAL) Mode
Ensures non-blocking, zero-latency local scan recording on the conveyor edge machine.
"""

import os
import sqlite3
import json
import math
import re
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
        conn.execute("PRAGMA foreign_keys = ON;")
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
                    manual_review_count INTEGER DEFAULT 0,
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

            session_columns = {r[1] for r in conn.execute("PRAGMA table_info(local_sessions);")}
            for column in ("end_synced_at", "sync_last_attempt_at", "sync_error"):
                if column not in session_columns:
                    conn.execute(f"ALTER TABLE local_sessions ADD COLUMN {column} TEXT;")
            scan_columns = {r[1] for r in conn.execute("PRAGMA table_info(local_scans);")}
            if "evidence_json" not in scan_columns:
                conn.execute("ALTER TABLE local_scans ADD COLUMN evidence_json TEXT;")
            # Metadata and photos have independent acknowledgements. Existing saved
            # photos automatically enter the outbox, including already-synced scans.
            for column in ("image_synced_at", "image_url", "image_sync_error", "image_last_attempt_at"):
                if column not in scan_columns:
                    conn.execute(f"ALTER TABLE local_scans ADD COLUMN {column} TEXT;")
            conn.execute("CREATE TABLE IF NOT EXISTS machine_journal (device_id TEXT PRIMARY KEY, state_json TEXT NOT NULL);")
            if "manual_review_count" not in session_columns:
                conn.execute("ALTER TABLE local_sessions ADD COLUMN manual_review_count INTEGER DEFAULT 0;")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_scans_sync ON local_scans(is_synced);")
            conn.execute("""CREATE INDEX IF NOT EXISTS idx_scan_image_outbox
                ON local_scans(image_last_attempt_at, scanned_at, scan_id)
                WHERE is_synced = 1 AND image_path IS NOT NULL AND image_synced_at IS NULL;""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_scans_session ON local_scans(session_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_scans_batch_seq ON local_scans(batch_id, sequence_number);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_scans_batch_class ON local_scans(batch_id, final_class, sequence_number);")
            self._migrate_legacy_contract(conn)
            conn.commit()

    @staticmethod
    def _migrate_legacy_contract(conn: sqlite3.Connection) -> None:
        """Normalize records from the retired domain contract before operation."""
        conn.execute("CREATE TABLE IF NOT EXISTS local_schema_migrations (version TEXT PRIMARY KEY);")
        if conn.execute("SELECT 1 FROM local_schema_migrations WHERE version = ?;",
                        ("two_class_v1",)).fetchone():
            return
        session_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(local_sessions);").fetchall()
        }
        if "abnormal_count" in session_columns:
            conn.execute("""
                UPDATE local_sessions
                SET infertile_count = infertile_count + abnormal_count,
                    stage = 'DAY_10';
            """)
            try:
                conn.execute("ALTER TABLE local_sessions DROP COLUMN abnormal_count;")
            except sqlite3.OperationalError:
                # Older SQLite versions may retain the unused legacy column.
                pass
        else:
            conn.execute("UPDATE local_sessions SET stage = 'DAY_10' WHERE stage <> 'DAY_10';")
        conn.execute("UPDATE local_scans SET final_class = 'INFERTILE' WHERE final_class = 'ABNORMAL';")
        conn.execute("INSERT INTO local_schema_migrations (version) VALUES (?);", ("two_class_v1",))

    def get_distinct_batches(self) -> List[Dict[str, Any]]:
        """Fetch all unique batches stored in local SQLite with scan counts and latest timestamp."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    batch_id,
                    COUNT(*) as total_scans,
                    SUM(CASE WHEN final_class = 'FERTILE' THEN 1 ELSE 0 END) as fertile_count,
                    SUM(CASE WHEN final_class = 'INFERTILE' THEN 1 ELSE 0 END) as infertile_count,
                    MAX(scanned_at) as last_scanned_at
                FROM local_scans
                GROUP BY batch_id
                ORDER BY last_scanned_at DESC;
            """)
            return [dict(row) for row in cursor.fetchall()]

    def get_scans_by_batch(self, batch_id: str, limit: Optional[int] = 300, class_filter: Optional[str] = None, search_query: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch scans for a batch or ALL batches with optional class and text filtering."""
        with self._get_connection() as conn:
            query = """
                SELECT sequence_number, scan_id, batch_id, session_id, final_class, confidence, inference_ms, routing_action, scanned_at,
                    (is_synced = 1 AND (COALESCE(image_path, '') = '' OR image_synced_at IS NOT NULL)) AS is_synced
                FROM local_scans
                WHERE 1=1
            """
            params: List[Any] = []

            if batch_id and batch_id != "ALL":
                query += " AND batch_id = ?"
                params.append(batch_id)

            if class_filter and class_filter != "ALL":
                query += " AND final_class = ?"
                params.append(class_filter)

            if search_query:
                clean_query = search_query.lstrip("#").strip()
                if clean_query.isdigit():
                    query += " AND sequence_number = ?"
                    params.append(int(clean_query))
                else:
                    query += " AND (scan_id LIKE ? OR final_class LIKE ?)"
                    params.extend([f"%{clean_query}%", f"%{clean_query}%"])

            query += " ORDER BY sequence_number DESC"
            if limit is not None:
                query += " LIMIT ?"
                params.append(limit)

            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def export_batch_csv(self, batch_id: str, class_filter: Optional[str] = None, output_dir: Optional[str] = None) -> str:
        """Export batch scans to CSV, optionally filtered by class."""
        import csv
        if output_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            output_dir = os.path.join(base_dir, "exports")
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_tag = self._filename_tag("ALL_BATCHES" if batch_id == "ALL" else batch_id)
        filter_tag = f"_{self._filename_tag(class_filter.lower())}" if class_filter and class_filter != "ALL" else ""
        filename = f"OvaLens_{batch_tag}{filter_tag}_{timestamp}.csv"
        filepath = os.path.join(output_dir, filename)

        scans = self.get_scans_by_batch(batch_id, limit=None, class_filter=class_filter)
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

    def create_session(self, session_id: str, batch_id: str, device_id: str, stage: str, operator_name: str) -> Dict[str, Any]:
        if stage != "DAY_10":
            raise ValueError("OvaLens supports only the DAY_10 candling stage.")
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

    def save_scan_image(self, scan_id, image):
        """Atomically persist the captured evidence before releasing its egg."""
        import cv2
        import tempfile
        scan_id = str(uuid.UUID(str(scan_id)))
        directory = os.path.join(os.path.dirname(self.db_path), "local_scans")
        os.makedirs(directory, exist_ok=True)
        ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 95])
        if not ok:
            raise OSError("Could not encode candling evidence")
        target = os.path.join(directory, scan_id + ".jpg")
        fd, temporary = tempfile.mkstemp(dir=directory, suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(encoded.tobytes())
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return target

    def record_scan(self, scan_id: str, session_id: str, batch_id: str, sequence_number: int,
                    final_class: str, confidence: float, inference_ms: int, routing_action: str,
                    detections: list, image_path: Optional[str] = None,
                    evidence: Optional[dict] = None) -> Dict[str, Any]:
        if final_class not in {"FERTILE", "INFERTILE"}:
            raise ValueError("final_class must be FERTILE or INFERTILE.")
        if (not isinstance(confidence, (int, float)) or not math.isfinite(confidence)
                or not 0 <= confidence <= 1):
            raise ValueError("confidence must be finite and between 0 and 1.")
        expected = "ACCEPT" if final_class == "FERTILE" else "REJECT"
        if routing_action not in {expected, "MANUAL_REVIEW"}:
            raise ValueError("routing action contradicts classification.")
        # Automatic cycles validate the configured (>=70%) threshold and stable
        # stopped evidence before this durable write. Diagnostics still use 75%.
        if confidence < 0.70 and routing_action != "MANUAL_REVIEW":
            raise ValueError("Low confidence requires MANUAL_REVIEW.")
        if type(sequence_number) is not int or sequence_number < 1 or type(inference_ms) is not int or inference_ms < 0:
            raise ValueError("Sequence and latency must be nonnegative integers (sequence >= 1).")
        scanned_at = datetime.now(timezone.utc).isoformat()
        det_json = json.dumps(detections)

        with self._get_connection() as conn:
            conn.execute("BEGIN IMMEDIATE;")
            session = conn.execute("SELECT batch_id, ended_at FROM local_sessions WHERE session_id = ?;",
                                   (session_id,)).fetchone()
            if session is None or session["batch_id"] != batch_id or session["ended_at"]:
                raise ValueError("Scan requires an open session with the same batch ID.")
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
            if evidence is not None:
                conn.execute("UPDATE local_scans SET evidence_json = ? WHERE scan_id = ?;",
                             (json.dumps(evidence, allow_nan=False), scan_id))
            col = ("manual_review_count" if routing_action == "MANUAL_REVIEW" else
                   "fertile_count" if final_class == "FERTILE" else "infertile_count")
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

    def save_machine_state(self, device_id: str, state: dict):
        with self._get_connection() as conn:
            conn.execute("INSERT INTO machine_journal(device_id, state_json) VALUES (?, ?) "
                         "ON CONFLICT(device_id) DO UPDATE SET state_json=excluded.state_json;",
                         (device_id, json.dumps(state, allow_nan=False)))
            conn.commit()

    def load_machine_state(self, device_id: str):
        with self._get_connection() as conn:
            row = conn.execute("SELECT state_json FROM machine_journal WHERE device_id=?;", (device_id,)).fetchone()
            return json.loads(row[0]) if row else None

    def get_pending_scan_sessions(self, limit=5):
        with self._get_connection() as conn:
            return [dict(row) for row in conn.execute("""
                SELECT s.* FROM local_sessions s WHERE EXISTS (
                    SELECT 1 FROM local_scans c WHERE c.session_id=s.session_id AND c.is_synced=0)
                ORDER BY s.sync_last_attempt_at, s.started_at, s.session_id LIMIT ?;
            """, (limit,))]

    def get_pending_session_ends(self, limit=5):
        with self._get_connection() as conn:
            return [dict(row) for row in conn.execute("""
                SELECT s.* FROM local_sessions s
                WHERE s.ended_at IS NOT NULL AND s.ended_at<>'' AND s.end_synced_at IS NULL
                  AND NOT EXISTS (SELECT 1 FROM local_scans c
                    WHERE c.session_id=s.session_id AND c.is_synced=0)
                ORDER BY s.sync_last_attempt_at, s.started_at, s.session_id LIMIT ?;
            """, (limit,))]

    def mark_session_sync_attempt(self, session_id, error=None):
        with self._get_connection() as conn:
            conn.execute("UPDATE local_sessions SET sync_last_attempt_at=?, sync_error=? WHERE session_id=?;",
                (datetime.now(timezone.utc).isoformat(), error, session_id))
            conn.commit()

    def mark_session_end_synced(self, session_id, ended_at):
        with self._get_connection() as conn:
            conn.execute("""UPDATE local_sessions SET end_synced_at=?, sync_error=NULL
                WHERE session_id=? AND ended_at=?;""",
                (datetime.now(timezone.utc).isoformat(), session_id, ended_at))
            conn.commit()

    def get_pending_session_end_count(self):
        with self._get_connection() as conn:
            return conn.execute("""SELECT COUNT(*) FROM local_sessions
                WHERE ended_at IS NOT NULL AND ended_at<>'' AND end_synced_at IS NULL;""").fetchone()[0]

    def get_uncommitted_scans(self, limit: int = 50, session_id=None) -> List[Dict[str, Any]]:
        """Fetch pending unsynced scans for the background network worker."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM local_scans
                WHERE is_synced = 0 AND (? IS NULL OR session_id=?)
                ORDER BY sequence_number ASC
                LIMIT ?;
            """, (session_id, session_id, limit))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_unsynced_count(self) -> int:
        """Count scans whose metadata or saved photo still needs acknowledgement."""
        with self._get_connection() as conn:
            cursor = conn.execute("""SELECT COUNT(*) FROM local_scans WHERE is_synced = 0
                OR (COALESCE(image_path, '') <> '' AND image_synced_at IS NULL);""")
            return cursor.fetchone()[0]

    def get_pending_scan_images(self, limit: int = 5) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            return [dict(row) for row in conn.execute("""
                SELECT * FROM local_scans WHERE is_synced = 1
                    AND image_path IS NOT NULL AND image_path <> '' AND image_synced_at IS NULL
                ORDER BY image_last_attempt_at, scanned_at, scan_id LIMIT ?;
            """, (limit,))]

    def mark_scan_image_attempt(self, scan_id: str, error: str):
        with self._get_connection() as conn:
            conn.execute("""UPDATE local_scans SET image_last_attempt_at = ?, image_sync_error = ?
                WHERE scan_id = ? AND image_synced_at IS NULL;""",
                (datetime.now(timezone.utc).isoformat(), error[:500], scan_id))

    def mark_scan_image_synced(self, scan_id: str, image_url: str):
        with self._get_connection() as conn:
            conn.execute("""UPDATE local_scans SET image_synced_at = ?, image_url = ?,
                image_sync_error = NULL WHERE scan_id = ?;""",
                (datetime.now(timezone.utc).isoformat(), image_url, scan_id))

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
                SELECT scan_id, sequence_number, final_class, confidence, inference_ms, routing_action, scanned_at,
                    (is_synced = 1 AND (COALESCE(image_path, '') = '' OR image_synced_at IS NOT NULL)) AS is_synced
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
        filename = f"OvaLens_Report_{self._filename_tag(batch_id)}_{timestamp}.csv"
        filepath = os.path.join(output_dir, filename)

        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT sequence_number, scan_id, batch_id, final_class, confidence, routing_action, inference_ms, scanned_at,
                    (is_synced = 1 AND (COALESCE(image_path, '') = '' OR image_synced_at IS NOT NULL)) AS is_synced
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

    @staticmethod
    def _filename_tag(value: str) -> str:
        """Keep identifiers in filenames from introducing directories."""
        return re.sub(r"[^A-Za-z0-9_-]", "_", str(value))[:100] or "UNKNOWN"
