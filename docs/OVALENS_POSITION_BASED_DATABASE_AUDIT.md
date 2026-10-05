# Position-Based Operation: Database Audit and Migration Plan

Task: `TASK-NEW-EDGE-POS-SPEC-01`

Scope: source-schema audit only. No live PostgreSQL connection, local database opening, migration, deletion, or record cleanup was performed.

## Recommendation

Retain PostgreSQL as the central hatchery source of truth and SQLite WAL as the offline edge store. Revise the schemas through versioned migrations; a database reset is unnecessary. Back up and inspect actual records before deciding whether any demo data should be archived.

## Source findings

| Source | Finding | Required change |
| --- | --- | --- |
| `backend/app/models/scan.py`, `backend/app/schemas/scan.py` | RoutingAction accepts ACCEPT/REJECT only; final_class and confidence are required. | Add MANUAL_REVIEW as a routing action. Represent unknown classification explicitly without adding a third model class. |
| `edge/src/db/local_db.py` | WAL is enabled. record_scan requires FERTILE/INFERTILE but does not validate confidence/action combinations. | Keep WAL; add validation and a separate operational record for unclassified failures. |
| `edge/src/db/local_db.py`, `backend/app/models/session.py` | Session counters track class predictions, without independent review/resolution/routing completion counts. | Separate prediction statistics from completed physical cycles and unresolved reviews. |
| `firmware/prototype/vision.py` | Prototype sessions use synthetic batch/device IDs and remain local. | Keep prototype records isolated; reconcile real batch/device/session identities before production sync. |
| `edge/src/sync/sync_worker.py` | Payload sends scan fields only and marks scans synced on HTTP 200. | Validate acknowledgements and introduce separate cycle/event sync with versioned updates. Sync batch/session prerequisites first. |
| `edge/src/db/local_db.py` | No persistent cycle state, holder sequence association, calibration snapshot, routing completion evidence, or recovery status. | Add durable cycles and events; keep classification immutable once committed. |
| `edge/src/db/local_db.py` | Foreign keys are declared, but each connection does not enable PRAGMA foreign_keys. | Audit orphan records, then enable enforcement on every connection in a tested migration. |
| `edge/src/db/local_db.py` | Startup legacy migration can add abnormal_count into infertile_count repeatedly if DROP COLUMN is unsupported. | Use explicit schema versions and a once-only migration ledger; inspect rollups before any repair. |

## Proposed data model

1. **Calibration profiles (local):** version, holder pitch in steps, chamber/sorter/clearance travel, direction, motor speed, camera ROI, lighting values, servo angles/timings, board firmware identities, and validation status. Snapshot the approved profile into each session so edits cannot change an active cycle's interpretation.
2. **Sessions:** target egg count, lifecycle status (configured/running/paused/recovery-required/completed/aborted), configuration snapshot, and completion timestamp. An interrupted camera worker must not automatically imply a successfully completed batch.
3. **Operation cycles:** cycle UUID, session ID, holder sequence, nullable scan ID, estimated position, presence status, phase, fault code, routing status, command correlation IDs, timestamps, and evidence. One active unresolved cycle per session. An empty-holder attempt is not a fertility scan.
4. **Operation events:** immutable event UUID, cycle/session IDs, local sequence, event type, timestamp, evidence payload, sync state. Record movement faults, camera/inference failures, operator removal, and recovery without inventing a model label.
5. **Scans:** retain FERTILE/INFERTILE as the only biological labels. Add MANUAL_REVIEW routing for low-confidence predictions. Store unclassified failures in cycles/events with no fabricated scan label; if a unified scan API later needs nullable class/confidence, migrate all consumers together rather than using a sentinel class or confidence zero.

Classification commit and its cycle association must be atomic before releasing the move-to-sorter command. Commit completion only after movement/actuation evidence and camera clearance. Record a routing request as pending, never completed merely because a serial write succeeded.

Use `(session_id, holder_sequence)` uniqueness for logical cycles and a separate attempt number for positioning retries. Every scan keeps its original UUID through network replay and recovery. Avoid overwriting a completed physical outcome when an operator corrects a biological label.

## Sync and reporting

- Preserve PostgreSQL `ON CONFLICT (scan_id) DO NOTHING` for scan insertion. It cannot propagate later routing changes by itself; use idempotent immutable events or a separately versioned cycle update endpoint.
- Synchronize real batches/devices/sessions before dependent scans and cycles. Retain unsynced rows on rejection and surface the actual failure.
- Report classified, completed, accepted, rejected, review-pending, manually-resolved, and fault counts with explicit definitions. Unknown classifications must not enter fertility-rate denominators or penoy revenue estimates.
- Snapshot counts after migration and compare with original records. Do not infer historical successful delivery from ACCEPT/REJECT or mark historical scans physically verified.
- SQLite commit is the movement gate. Document that WAL with synchronous NORMAL is not a guarantee against sudden power-loss loss of the newest transaction; choose and benchmark the required durability policy on the deployed machine.

## Migration sequence and acceptance

1. Inspect backups and read-only record counts: legacy labels, invalid actions/confidence, orphan sessions, duplicate sequences, prototype IDs, and unsynced rows. Do not construct LocalDatabaseManager for a read-only audit because initialization performs legacy updates.
2. Introduce schema-version tracking and additive local tables/columns with existing records preserved. Test upgrading an old temporary database twice, proving no duplicate counter changes.
3. Add PostgreSQL MANUAL_REVIEW action support, cycle/event persistence, Pydantic schemas, sync contracts, and matching dashboard types. Keep legacy records readable.
4. Test migration rollback/recovery, unknown inference outcomes, low-confidence review sync, duplicate replay, prerequisites, stale cycle updates, foreign-key enforcement, and crash recovery without command replay.
5. Deploy against backed-up data, verify counts, then separately consider archiving clearly identified demo records. Never delete unsynced scans during cleanup.

Implementation remains a separate task after protocol and geometry validation. This document is a migration plan, not a claim that the database or hardware already satisfies it.
