# Main Edge Application Operation Audit

Task: `TASK-NEW-EDGE-AUDIT-01`
Scope: `edge/launcher.py`, startup configuration, main operator UI, camera/inference, local SQLite, and backend synchronization contracts. The separate hardware prototype launcher and physical rig are not certified by this audit. Read alongside [the position-based specification](OVALENS_POSITION_BASED_OPERATION_PROMPT.md) and [database audit](OVALENS_POSITION_BASED_DATABASE_AUDIT.md).

## Outcome

The main application has safer manual diagnostic and simulation flows. **Automatic physical sorting is disabled and remains incomplete.** Its retired single-board optical-sensor controller cannot operate the two-board sensorless spaced-holder conveyor correctly. The launcher does not connect to arbitrary serial ports or start movement. Manual ejection and the old timed sorting loop are blocked.

No boards were flashed, no conveyor was operated, and no production scans were deleted. Tests use temporary databases. Existing local legacy normalization now has a one-time migration marker; this is not approval for a broader production database cleanup.

## Findings and changes

| Finding | Result |
| --- | --- |
| Unsupported `#ffffff40` Tk color crashed startup | Replaced with a supported theme color; real startup window construction tested. |
| Missing camera silently generated synthetic captures | Synthetic preview requires explicit simulation; normal camera failure reports an error, releases the capture, and invalidates stale frames. Camera opening and reads run off the UI thread. |
| Empty detections became confident `INFERTILE` results | Empty/unknown detections yield no classification and require review. They are not fabricated binary scan records. |
| Model input precision and low-confidence routing were inconsistent | ONNX input respects FP16/FP32 metadata; real inference uses the 0.75 review boundary. Unsupported output layouts fail explicitly. Simulation/model fallback results remain unsaved preview. |
| Inference failure could leave callers without a result | Worker failures return an explicit review/error result. |
| Inference, database access, exports, and foreign-thread callbacks could freeze or corrupt UI flow | Bounded background jobs and a UI event inbox handle worker completion on the main thread. History reads and CSV exports run on a worker. |
| Counters advanced before SQLite writes succeeded | Session creation and scan recording happen before success counters/banner updates. Failed storage is visible; retry reuses an existing local session. Review records are excluded from fertility and Penoy totals. |
| Stop could accept late predictions or mix session identity | Cancellation invalidates callbacks; worker tasks capture session/batch identity. Session finalization follows prior queued writes. Configuration changes are blocked during scan/session/stop activity. |
| Closing during dialog construction could destroy Tk mid-construction | Shutdown waits until dialog construction finishes, then polls worker cleanup without blocking the UI. A hidden history-window shutdown regression covers this race. |
| CSV exports truncated batch records and trusted raw filename identifiers | Exports include all matching rows and sanitize filename components. Regression exports 10,001 records and checks output directory containment. |
| Sync treated any HTTP 200 as durable success and did not replay session creation | Original local session metadata is registered first; identity must match the server response. Scan acknowledgements must account for the complete packet before local records are marked synced. Packets contain one session. Errors retain records and appear in status. |
| Hardcoded sync credential and implicit hardware fallback obscured readiness | Credentials come from environment; absent key is visible and retains local data. Simulation is explicit and does not run background scan sync. |

## Supported operator flow

1. Launch `edge/launcher.py`; configure batch/operator and numeric values. Cancel exits before workers or hardware start.
2. The operator dashboard opens in standby. Startup does not move the belt. Sorting readiness is marked unavailable.
3. Press Scan once. The app starts the camera if necessary, waits up to three seconds for a fresh frame, and then classifies it. Camera failure or expiry shows an explicit error; retry after correcting the camera.
4. A manual request runs inference on a worker. Missing egg/unknown output or inference failure requires review without inventing a class. Explicit simulation and fallback predictions are preview only.
5. A valid real ONNX diagnostic result creates/reuses a local session and commits the scan to SQLite WAL. Only after success do counters advance. Low-confidence binary predictions are recorded as `MANUAL_REVIEW`, without movement.
6. Background sync attempts session registration and scan ingestion. Network/authentication/validation errors retain local records. A rejected acknowledgement cannot mark them synchronized.
7. Stop cancels unfinished predictions and finalizes the captured session after pending writes. A failed finalization preserves the session ID and blocks scanning/settings until Retry Finalization succeeds. Close waits asynchronously for cleanup; timeout or failed finalization is reported. An abrupt process/power loss is not covered by graceful shutdown guarantees.
8. History and CSV remain available without running sorting. History statistics describe the latest 5,000 records; CSV exports contain all matching records. Stored scans describe classification decisions, not confirmed physical routing.

## Remaining readiness blockers

1. **Dual-board integration:** implement separate serial workers for the tagged firmware protocol, command/board identity, heartbeat, acknowledgements, completion, faults, and stopped recovery. The main startup screen still has legacy single-port/timing controls; it needs the position-based configuration and readiness checks.
2. **Physical identity and calibration:** measured holder spacing, chamber/sorter coordinates, step conversion, servo neutral/travel limits, independent camera presence and clearance checks, and controlled rig tests are required. Classification alone does not prove egg identity, departure, or successful routing. No throughput, 60 FPS, mechanical accuracy, or biological model accuracy claim was validated here.
3. **Review synchronization:** backend routing enums still only accept `ACCEPT`/`REJECT`. A `MANUAL_REVIEW` packet is retained locally after HTTP 422. A rejected review record can also block later records in that packet/backlog. Apply a coordinated backend migration and ingestion policy before offline sorting is enabled.
4. **Durable lifecycle and faults:** local session completion is recorded, but remote completion/reconciliation, resumable interrupted operations, immutable fault/operation events, and physical route outcomes remain to implement. Missing-egg/model errors are currently visible UI events, not durable operation records.
5. **Deployment validation:** verify actual COM assignments, camera, deployed sketches, model, API key, registered device and batch, and reconnect/restart/power-loss behavior on the rig. Passing automated tests does not prove these conditions.

## Verification

- Repository `verify_and_commit.py --task TASK-NEW-EDGE-AUDIT-01 --verify-only`: backend API suite **14 passed**, edge suite **124 passed / 22 skipped**, and dashboard TypeScript/Vite build passed. The edge gate skipped 21 native C++ tests on Windows and one environment-dependent Tk root construction check.
- Focused GUI and failure-path run: **25 passed**, including actual hidden startup/operator windows, history construction, and shutdown.
- Final complete edge confirmation run: **125 passed / 21 skipped**. Both GUI checks passed; the 21 Windows compiler skips were covered by the WSL run below.
- Native firmware tests under WSL with C++ compiler: **21 passed**, without flashing hardware.
- Export regression verifies complete 10,001-record reports and sanitized paths. Failure tests cover stale/missing cameras, unknown/empty inference, low confidence, failed persistence, cancelled callbacks, malformed/rejected sync acknowledgements, duplicate acknowledgement handling, and one-time legacy migration.
- `git diff --check` passed. Verification-only mode does not stage, commit, or modify the Excel checklist; unrelated existing workspace changes are preserved.

Review summary: security/secrets improved for this scope; architecture preserves two classes and local WAL; physical edge resilience remains a concern pending integration; software failure coverage passed with the environment-dependent skip noted above.

## Operator flow improvement — TASK-NEW-EDGE-FLOW-01

The manual path now shows `READY -> CAMERA_STARTING -> CLASSIFYING -> SAVING -> READY/MANUAL_REVIEW`. Camera wait is bounded at three seconds; inference is bounded at two seconds independently of the storage worker. A timed-out model call may still be running: the application discards its late result and rejects overlapping inference until the worker is available. Stop and storage remain independent of that call.

Requests carry unique IDs and operation generations. Counters still advance only after local commit. Stop recovers counters from SQLite if a scan committed before its UI callback was cancelled. Cancelling before the first write does not fabricate a missing-session fault. At the configured diagnostic target, the session finalizes and additional scans are blocked until a new batch is configured; this is diagnostic completion, not proof of distinct eggs or successful physical routing.

Batch settings require valid quantity, operator name, and Day 10 stage. A retained local session locks settings even if its first scan failed. SQLite rejects writes to finished sessions and mismatched batch IDs within a write transaction. Space in an editable field or an open dialog cannot start a scan.

Hardware integration, physical egg identity, crash recovery across application restarts, and the backend review contract remain pending as described above.

Flow verification: final complete edge suite **141 passed / 21 native compiler skips**, including both real GUI checks. The repository verification-only gate also passed **14 backend tests** and the dashboard build. An additional focused flow run passed **17 tests**, including the editable-field/dialog shortcut regression. Firmware was unchanged in this task; its 21 native tests passed under WSL during the preceding audit.
