# OvaLens edge station control

Task: `TASK-NEW-EDGE-CONTROL-01`; extends `TASK-NEW-FW-SAFE-01` and replaces the sensorless assumption in `TASK-NEW-EDGE-POS-SPEC-01` for this rig.

## Run and configure

Install `edge/requirements.txt` in a dedicated Python environment and run `python edge/launcher.py` from the repository root. Use **Settings** in the operator window. Opening the application never starts the conveyor.

1. In **Camera**, choose the camera index and requested resolution/FPS. Apply settings to start idle preview. Disable automatic exposure, focus and white balance before tuning their manual values, where the driver supports these controls. Blank optional fields leave the driver unchanged. Exposure and auto-exposure values use the camera backend's native units; DirectShow commonly uses 0.25 for manual and 0.75 for automatic exposure. Check the displayed readback on your camera.
2. In **Connections**, enter separate conveyor and servo COM ports, Apply, and then **Connect and identify boards**. Port descriptions do not prove board identity: the serial protocol checks each board's role. The app will reject old firmware and conveyor firmware without IR capability.
3. Inspect the mechanisms, then **Acknowledge inspected board faults**. This does not home or move the conveyor. Jog slowly for alignment and use **Set aligned position as software home** deliberately.
4. In **Calibration**, enter measured holder spacing, chamber-to-gate distance, gate approach/exit clearance, direction, STEP half-period, IR capture offset, arrival tolerance, settling time, passage time and servo angles. Apply before validation. Gate clearance must be less than half a holder pitch, tolerance less than clearance, and travel between holders at least 600 ms. These checks do not establish physical accuracy.
5. Bench-test the unloaded IR stop and both gate directions. Align the **next holder one pitch before the camera station**, clear every downstream holder, and leave the IR beam clear. Confirm the inspection checkbox and load/validate calibration. This restores approved board presets and moves the empty gate to neutral; it does not move the conveyor.
6. Close Settings and choose **Start sorting**. The batch target counts recorded eggs; empty holders do not count. Stop feeding after the configured number of eggs. Additional eggs encountered during draining require recovery.

**Apply** changes the current run. **Save as Default** also writes `edge/db/edge_settings.json` atomically. **Restore Saved Defaults** loads the form; Apply is still required. The file contains settings, never permission to move. Camera identity currently consists of OpenCV index/backend, not a hardware serial number: confirm the selected device after USB changes, including replacement at the same index. Reapply settings after a backend/identity mismatch. A driver accepting a write and returning the value is labelled verified readback; this does not independently prove the camera disabled its automatic algorithms.

Settings are locked during sorting and unfinished sessions. Finish the session before tuning. Initial detection confidence is 0.25, NMS IoU 0.45, automatic-sort confidence 0.85, and settling time 150 ms. The automatic-sort threshold cannot be below 0.75. These values require bench validation.

## Firmware and wiring

Use the two sketches under `firmware/sketches_only`, preserving their shared `protocol.h`. Verify with Arduino-ESP32 3.x and ESP32Servo. This implementation does not flash either board or identify which sketch is currently deployed on your hardware.

| Board | Assumed connections |
| --- | --- |
| Conveyor ESP32 | A4988 STEP GPIO2, DIR GPIO4; active-low chamber IR on GPIO14 with input pull-up |
| Servo ESP32 | SG90 signal GPIO18; regulated external servo supply and common ground |

Confirm actual pins, IR polarity, 3.3 V-compatible sensor output, motor current limit, gate travel and power wiring before uploading. GPIO2 is a boot-strapping pin. The A4988 ENABLE line remains physically LOW in this design: stopping pulses does not remove holding current. Use a physical emergency stop. Candling-light control is not implemented because its wiring remains unspecified.

The v2 request envelope remains `@<increasing-id> <command>`, at 115200 baud, newline terminated. New capabilities are:

- `BOOT:CONVEYOR_V2` / `BOOT:SERVO_V2`: unsolicited reset notification; invalidate the host cycle.
- `IR_CAPABLE:1`, `IR_ACTIVE:0/1`, `IR_OFFSET:<steps>`: conveyor telemetry.
- Tagged `IR_OFFSET:<0..99999>`: configure forward-travel steps from detection to the stopped capture point.
- Tagged `INDEX:<signed-steps>`: bounded referenced movement with locally handled IR stopping. Existing manual `JOG` does not arm automatic IR stopping.
- `ID:<id>:EVENT:IR:<position>`: the trigger position, separate from `OK:MOVE_DONE` and the final position report. The ISR enforces the 600 ms lockout; the timer completes an existing high pulse and applies the configured offset without exceeding the requested movement bound.

The host sends a heartbeat/status request every 0.5 seconds to each board. Board watchdogs expire after three seconds. Host reply and command deadlines stop both boards on failure. A timed-out move is never retried with a new ID. Stop has priority over queued commands, invalidates calibration, and requires inspection/reconnect. Neither board measures belt slip or motor stall.

## Classification, records and recovery

One inference scheduler serves preview and capture; capture discards queued stale preview work. Camera acquisition remains independent and retains only the latest timestamped frame. Classification starts after motion completion and settling, requires at least three distinct agreeing frames spanning 300 ms, and has a two-second deadline. Position disagreement, multiple detections, low confidence, empty/occupied disagreement between IR and camera, or unstable evidence holds the conveyor for review.

The review buttons explicitly confirm fertile, infertile or an empty holder. A human-resolved egg is stored with `MANUAL_REVIEW` routing and the operator's selected class before routing. It remains in the review counter. There is no third biological class or physical review lane.

Each egg receives a durable SQLite WAL scan before advancement. Local scan evidence includes the settings snapshot, holder identity and confirmation evidence. The additive `evidence_json` column and `machine_journal` table require no backend API migration. The existing background sync payload remains compatible and outages retain local records. The journal records in-flight operations before motion and retains unresolved holders after interruption; completed holders are removed from the active in-memory queue.

The coordinator schedules gate approach/exit events independently of camera events, including distances that are not whole multiples of holder pitch. It waits for the matching servo completion before allowing an egg into the gate. Gate completion is a **timed settling/passage estimate**, not measured shaft angle or egg delivery.

On stop, device failure or application restart, inspect and remove/reconcile outstanding eggs. End/finalize any visible session, reconnect, acknowledge faults, re-align and establish software home, then validate the cleared setup. Inspection validation closes an interrupted local session and starts a fresh holder reference; it never silently resumes the previous belt position. Manual review during an otherwise healthy cycle preserves holders and permits explicit resolution without restarting.

## Verification and performance

Run `python -m pytest edge/tests -v` and the repository verification utility. `test_station_control.py` covers settings, camera ownership/readback, inference priority, correlated serial replies, stop priority, gaps, bidirectional movement, gate order, local evidence and storage faults. Native firmware tests compile the actual sketches with Arduino shims; they require g++ or clang++. UI construction tests require working Tcl/Tk. None proves real electrical behavior, optical alignment, stopping distance or sort accuracy.

Run `python edge/benchmark.py --output <path>` for a 50-frame synthetic model timing measurement, and optionally `--threads <n>` or `--baseline <previous-json>`. Use the same machine, model and frame size for comparisons. The cycle exposes capture age and cycle duration; the inference scheduler exposes inference latency and queue depth. The UI tracks dispatch intervals. Synthetic timing excludes actual camera exposure, physical travel and hatchery accuracy. No throughput or latency SLA is claimed before rig validation.

If importing `serial` does not expose `Serial`, the unrelated `serial` package is shadowing PySerial. Use a clean virtual environment with the edge requirements; do not use the serialization package for hardware control.
## Operator interface refinement

`TASK-NEW-EDGE-UI-POLISH-01` uses native Segoe UI on the Windows station. The main
operator surface uses 12 px metadata, 14 px controls, a 20 px application heading,
and 24 px scan counts. FU maroon, green, red and slate remain the theme. Device
telemetry occupies a separate header row, STOP remains visible during sessions,
and holder decisions appear when the cycle requests manual review. Recent history
remains available through the History control and S shortcut.

Control and cycle-HUD refreshes now compare complete presentation signatures
before touching Tk widgets. Busy inference, session identity, completion, shutdown
and failed finalization invalidate the control signature. Camera, inference,
storage and physical movement behavior are unchanged by this refinement.

On the Windows development PC, 500 repeated unchanged control/HUD refresh pairs
using real CustomTkinter widgets took 7,245.55 ms before this change (0556e6b),
and 7.92–23.68 ms afterward. This isolated benchmark excludes event-loop waiting,
camera rendering and inference; it establishes reduced redundant Tk work, not
an end-to-end frame rate or sorting throughput. Native GUI verification covers
1280×860 and 1024×720 layouts, active/review controls, startup and settings.

`TASK-NEW-EDGE-DESIGN-02` refines this into one record panel with aligned 20 px
count rows and thin section dividers, replacing the coloured metric tiles. The
standby instruction sits directly in the camera well. Settings distinguish
primary actions from neutral secondary commands. End Session stays in the
footer so the cycle reason can use the full camera HUD. Cached refreshes remain
in place; the same 500-refresh Tk probe measured 5.18 ms during this refinement.
See `edge/DESIGN.md` for the native Operate design rules.
