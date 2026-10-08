# Three-board edge integration

Task: `TASK-NEW-EDGE-3BOARD-01`. Target: the October 2026 edge-system handoff.
This document defines the implemented contract and the evidence needed before
running eggs. Software verification does not prove electrical or mechanical behavior.

## Wiring and firmware

| Role | Connections | Boot / fault behavior |
| --- | --- | --- |
| Conveyor | A4988 STEP GPIO2, DIR GPIO4, pause input GPIO27 | No motion; reference invalid; pause input pull-up holds if the link wire opens |
| Egg controller | FC-51 active-low GPIO26, SG90 GPIO32, pause output GPIO25 | Pause HIGH; gate requests neutral 90 degrees at boot |
| Light controller | Active-high relay/driver GPIO27 | Lamp OFF |

Wire egg GPIO25 to conveyor GPIO27 and share ground. Confirm sensor logic levels,
motor current limit, servo power, relay polarity and gate travel on the actual rig.
Stopping step pulses does not disable holding current with A4988 ENABLE tied LOW.

Use all three sketches under `firmware/three_board/`. Keep the repository's
`firmware/` tree together: the v3 guard reuses the bounded parser in
`firmware/sketches_only/protocol.h`. Select ESP32 Dev Module, Arduino-ESP32 3.x,
and install ESP32Servo. Upload each board separately after identifying its role.
The unversioned example sketches in the original handoff are incompatible with
automatic sorting in this implementation.

## Protocol

Serial is 115200 baud, newline-terminated ASCII. PING returns the handoff roles:
`PONG:CONVEYOR`, `PONG:EGG_CONTROLLER`, `PONG:LIGHT_CONTROLLER`. HELLO additionally
requires `READY:<role>_V3:PROTOCOL=3`; boot emits `BOOT:<role>_V3`.
Discovery sends PING and HELLO only, requires all three unique roles and rejects
duplicate/missing roles. It opens ports and may reset ESP32 boards; discover with
the rig unloaded. USB port order never selects a board role.

Actuating and configuration requests require increasing IDs: `@1 ACK_FAULT`.
Replies use `ID:1:<field>`. Reports end in STATE. Acceptance is distinct from
completion; the host waits for the matching completion and full report. A lost
acknowledgement stops the rig and is never retried as a new move. STATE commits
each telemetry report atomically. Malformed/overlong input cannot execute suffixes.

All boards support HELLO / PING / STATUS, ACK_FAULT and untagged ESTOP / HALT /
STOP. Only recognized reads renew the three-second heartbeat. Startup faults,
link faults and stops require explicit acknowledgement. Heartbeats never clear
faults. A reset, serial failure, live board fault or command timeout stops all
required links. The host sends heartbeats independently every 0.5 seconds.

| Board | Commands / events |
| --- | --- |
| Conveyor | SPEED:200..5000, SETHOME, JOG:signed-steps, ADVANCE:signed-steps; moves bounded to 100000 steps and total position +/-10000000 |
| Egg | ARM, PAUSE, RESUME, SORT:FERTILE, SORT:INFERTILE, SERVO:0..180, RESET, SET_NEUTRAL / SET_FERTILE / SET_INFERTILE:angle |
| Light | LIGHT_ON / ON, LIGHT_OFF / OFF; independent 15000ms ON limit |
| Events | EVENT:EGG_DETECTED:sequence, EVENT:EGG_CLEARED:sequence; EGG_SEQ also appears in complete egg reports |

Conveyor ADVANCE completes either at its finite target or at hardware pause with
OK:EGG_STOPPED. The host reconciles stopped position, pause input, egg state,
sequence and event before capture. Duplicate/stale events or disagreements stop
the rig for recovery. Position counts issued pulses, not measured belt movement.
Positive motion uses the handoff's inverted direction; direction remains locally
configurable and must be checked unloaded.

Sensor confirmation is 40ms LOW and 350ms HIGH clearance. A retained 600ms
detection lockout faults on a premature new egg. Servo completion is a 500ms
settling timer, without physical angle feedback. The optional service command
GATE_RESET_DELAY:1..10000 counts only unpaused time, cancels on newer gate requests
or faults, handles clock wrap and emits GATE_RESET_DONE after settling. Production
routing uses positions instead of this timer.

The handoff's <10us pause claim is not established: the ISR samples pause before
new rising step edges; response depends on timer phase, and sensor confirmation
adds 40ms. An already issued pulse finishes. Measure electrical latency and
mechanical stopping on the rig; neither simulation nor compilation proves them.

## Operator setup

### Daily setup with remembered settings

1. Double-click **Start_OvaLens.cmd**, or run `python edge/launcher.py`, and enter
   the batch details. Both launchers prefer the project `.venv`. Restart an older
   running window after updating the app or packages.
2. The saved camera starts its preview automatically. New defaults use **camera
   0**, **COM5 stepper**, **COM7 servo + IR**, and **COM9 light**.
3. Empty and align the conveyor; inspect the gate. Tick **Conveyor empty, aligned;
   gate checked**, then click **Start sorting** once. Preparation checks the
   camera, discovers required firmware roles, acknowledges faults, sets the
   inspected position as home, loads the saved presets and returns the gate to
   neutral before starting. **STOP** cancels preparation and prevents late
   callbacks from starting a batch. Inspect again before retrying.
4. Feed one egg only when the large instruction says **Feed next egg**. Wait
   through **Inspecting egg**, **Positioning gate** and **Wait ? egg passing**.
   Review decisions appear only when the current egg needs inspection.
5. At the target, the last egg finishes its calibrated gate passage and the
   worker finalizes SQLite records. Totals and **Start next batch** appear inline.
   If reading final totals fails, **Retry Finalization** retains the session ID.
   Each new batch requires another empty-conveyor inspection.

Saved camera controls and measured calibration are retained. Healthy board links
are reused between batches; disconnected links trigger role discovery using the
remembered ports first. All three v3 sketches must already be installed; the app
does not flash them. **Tools** groups Single scan (Space), Settings and Retry
camera preview. A saved two-board profile still uses its advanced preparation.
Default gate distances are starting estimates requiring physical measurement.

### Advanced setup and calibration

1. Run `python edge/launcher.py`. Opening the app never starts a conveyor.
2. Open Tools > Settings, choose **Three-board candling rig**, and **Load selected rig
   defaults** if migrating. Existing saved profiles stay two-board until changed.
3. Discover the three boards or enter their separate COM ports. Apply, then Connect.
   Profile or camera-index changes require camera confirmation. Camera 0 is the
   user-selected default (the original handoff specified 1); 1280x720 remains the
   starting resolution. Check the actual device/readback.
4. Inspect the unloaded mechanisms and acknowledge faults. Deliberately release
   hardware pause before an alignment jog; establish software home only after
   inspection. Stopping and reconnecting do not restore permission to sort.
5. Measure chamber-to-gate center, gate entry/exit clearance, feed spacing and
   direction. Bench-test both gate routes, lamp, hardware pause and watchdogs.
   Clear the chamber and downstream eggs, then validate calibration.
6. Close Settings and Start sorting. Stop feeding at the target. Additional eggs
   encountered while draining require recovery, rather than an unrecorded route.

Defaults: speed 3000us half-period, fertile 180 / infertile 120 / neutral 90,
settle 1500ms, six buffer grabs, display hold 300ms, search timeout 30 seconds,
detection threshold 0.30 and automatic-sort threshold 0.85 (minimum 0.75).
The default gate exit is 417 steps from capture, approximately 2.5 seconds of
movement at the default speed. This estimate must be replaced with measured
calibration. The old IR offset and timed passage wait apply to the two-board profile.

## Candling, routing and recovery

`TASK-NEW-EDGE-STOPSCAN-01`: Camera acquisition and live preview continue while
the belt moves. The operator app creates no continuous detection/tracking worker.
The model stays loaded after its three startup warmup passes; automatic inference
is requested only by the stopped capture state machine. Single Scan remains an
explicit diagnostic action, guarded against a connected conveyor reporting motion.

The egg board pauses the belt locally. The host confirms lamp ON, waits settling,
requests six buffer grabs and a fresh read on the camera's sole owning thread,
then requires three agreeing real ONNX detections over at least 300ms within a
two-second evidence window. Geometry, confidence, frame order and settings revision
must agree. Camera failure cannot substitute synthetic frames into a real session.

Predictions use three fresh frames spaced at least 150ms apart, avoiding redundant
AI work during the 300ms evidence interval. Before and after each prediction the
host checks health, stopped position, pause, held egg sequence and lamp ON.
Camera-setting changes and late results after a stop/fault are discarded.
The three-board camera settle defaults to 1500ms after lamp ON confirmation. The display hold is
300ms; explicitly saved timings are retained. This extra result pause occurs
after the sorting servo has confirmed completion. The two-second evidence deadline remains bounded.

The UI receives each camera snapshot and its detections together. While held it
shows that exact captured image, including during manual review. Stored image
evidence is updated atomically to match the final predicted frame and records its
sequence, capture timestamp and settings revision. Capture overlays are cleared
before RESUME/ADVANCE/INDEX commands, on operator stop and on recovery faults.
The render cache includes the capture/live source so the next UI refresh removes
the box even if the camera sequence has not changed. Moving video has no AI boxes.

Image evidence is written atomically and linked to the scan. The scan and decision
commit to SQLite WAL before release or sorting commands. The journal retains
pending captures, unresolved reviews, holder identities, position, settings,
original predictions and manual decisions. Saved scans include model path, SHA256,
tensor precision and class metadata. Counts follow committed records.

Low confidence, no confirmed egg, conflicting results or invalid evidence enter
MANUAL_REVIEW while holding the belt. The lamp turns OFF before human review so
review cannot exceed its independent ON limit. The operator sees the retained
captured image. Fertile/Infertile decisions remain marked MANUAL_REVIEW in the scan;
EMPTY confirms a false sensor trigger without creating a third biological class.

`TASK-NEW-EDGE-GATEFIRST-01`: Immediately after the classification commits to WAL,
the host sends SORT while the hardware pause still holds the egg in the chamber.
It waits for the correlated completion, BUSY=0 and the expected configured ANGLE,
then rechecks the stopped position and held egg sequence. Only then does the
display hold finish, the lamp turn OFF and the host send RESUME. Completion is
the firmware's existing 500ms settling timer; there is no physical angle sensor.
A failed/missing completion stops the rig with the saved decision retained.

The gate angle is retained from release through the calibrated exit position;
RESET completes at that stopped boundary. There is no delayed approach-position
SORT command. Feed one egg at a time when the status says Gate clear. An arrival
before the previous gate exit enters recovery with both holder identities retained,
without a new classification, gate change or release. If arrival and exit coincide,
the previous gate reset completes before the new egg is classified and preset.
The search timeout begins again after clearance, while gate passage remains bounded
by motion-command deadlines. Pauses do not consume passage distance. Missing
clearance, extra eggs, storage faults and synchronization disagreements require
recovery. No gate-passage sensor exists, so delivery remains estimated.

Stop/error cleanup holds transport, turns the lamp OFF and preserves the gate
angle; it never sends RESUME or resets a potentially loaded gate. On restart the
journal is displayed as recovery evidence and no board reconnects or moves
automatically. Inspect and reconcile physical eggs before acknowledging faults,
re-establishing home and validating again. Backend outages only retain the local
sync queue; they do not block the physical cycle.

## Model selection

`edge/models/weights/best.onnx` is the existing artifact. Inspection showed input
`[1,3,640,640]`, output `[1,6,8400]`, class metadata 0=FER / 1=INF and FP32 tensors.
It must not be described as a verified FP16 export or as best_v3. The handoff's
best_v3.pt is absent; the user approved retaining the existing best.onnx for this
integration. To change models later, export the supplied checkpoint with
`python edge/models/export_onnx.py --weights <path-to-best_v3.pt>` and set an
absolute `ONNX_MODEL_PATH` in `edge/.env`. Inspect the resulting tensor precision
and benchmark on the target host. Metadata and shape validation reject swapped
classes, extra classes, missing metadata and incompatible detector layouts.
PyTorch and heuristic fallbacks remain preview-only. Startup retains three warmup passes.

## Verification record and remaining physical acceptance

Baseline: backend 22 passed; dashboard production build passed; edge 187 passed /
26 skipped after using isolated PySerial. The system Python has both unrelated
`serial` and `pyserial` packages installed; use a clean virtual environment or the
existing ignored `.flow_tests/deps` overlay. Do not uninstall packages from a shared
Python environment as part of station operation.

Implemented checks cover actual serial workers, discovery, correlation, event
overflow, watchdogs, sensor debounce, safe boot, servo settling, relay timeout,
clock wrap, malformed commands, fresh camera ownership, model contract rejection,
50-egg routing, crowded gate intervals, manual review, cancellation, storage
failure, restart journals, offline replay and lost acknowledgements. Native tests
execute the actual C++ sketches with GPIO/timer/servo shims. Arduino-ESP32 3.3.11
and ESP32Servo 3.2.1 compile all three sketches for ESP32 Dev Module.

Final software gate (2026-10-08): backend **22 passed**, edge **264 passed**
with no skips, and dashboard production build passed. The edge suite includes
all five Tk GUI smoke checks and 43 native firmware checks. A 50-egg test uses
the actual capture/inference workers, image persistence, WAL store and coordinator
with synthetic camera/model/board adapters; it does not establish model accuracy
or physical throughput. Existing backend deprecation and Vite warnings remain.

The setup simplification (`TASK-NEW-EDGE-SETUP-01`, 2026-10-08) passed **22 backend
tests**, **277 edge tests** with no skips, and the dashboard production build.
Added checks cover remembered ports, changed port order, fallback discovery,
inspection requirements, STOP during detection/preparation, saved defaults and
the actual main-screen controls at 1280x860 and 1024x720. Visual inspection also
covered both sizes and the startup instructions. All device traffic used fakes.

Reproduce software verification:

Stopped-only inference verification (`TASK-NEW-EDGE-STOPSCAN-01`, 2026-10-09):
the final repository gate passed **22 backend tests**, **298 edge tests** and
the dashboard production build. One Tk initialization skip occurred in the full
edge run; the operator-window test and the new live-preview test each passed in
a fresh process. Coverage includes a live preview with zero background inference,
50 simulated eggs with exactly 150 predictions, no prediction during motion,
exact image/prediction persistence, manual-review retention, late-result rejection
on stop/pause/sequence/position/lamp/settings changes, and cache invalidation when
the box clears or the camera becomes stale. `launcher.py --check-runtime` confirmed
the project interpreter and PySerial 3.5. No physical device was exercised for
this change; actual stopping, exposure and sorting acceptance remain below.

Servo-before-release verification (`TASK-NEW-EDGE-GATEFIRST-01`, 2026-10-09):
**22 backend tests**, **307 edge tests** and the dashboard build passed. One
minimum-window GUI test skipped during Tk initialization and passed in a fresh
process. Added tests hold a servo completion pending and prove no release occurs,
cover both sorting presets before the display hold, stop/cancellation, missing or
invalid completion, wrong angle, lost hardware pause, and simultaneous gate exit
and next arrival. The 50-egg integration uses feed arrivals 450 steps apart, beyond
the default 417-step gate exit; earlier conflicting arrivals stop without replacing
the previous gate preset. This change uses existing v3 firmware completion reports
and requires restarting the host app, with no firmware upload. All new verification
used simulated devices; physical servo travel and calibrated gate clearance remain
rig acceptance work.

```powershell
python -m pytest edge/tests -v
python scripts/verify_and_commit.py --verify-only --task TASK-NEW-EDGE-3BOARD-01 -m "feat(edge): integrate three-board candling rig"
arduino-cli compile --fqbn esp32:esp32:esp32 firmware/three_board/conveyor_esp32
arduino-cli compile --fqbn esp32:esp32:esp32 firmware/three_board/egg_controller_esp32
arduino-cli compile --fqbn esp32:esp32:esp32 firmware/three_board/light_controller_esp32
```

Native execution requires g++/clang++, or set OVALENS_TEST_ZIG to an isolated Zig
binary. For this machine prepend `.flow_tests/deps` to PYTHONPATH to avoid the
unrelated serial package. Tk smoke checks should also run in a fresh Python process
if a prior in-process Tk initialization fails.

Physical acceptance remains unchecked until observed:

- [x] Identify installed firmware roles and upload the three v3 builds to the matching boards (2026-10-08; see installation record below).
- [ ] Confirm unloaded wiring, pause polarity / broken-wire hold, servo stroke and lamp relay behavior.
- [ ] Measure detection-to-pause latency and stopping distance; calibrate capture position and gate boundaries.
- [ ] Verify minimum egg spacing, beam clearance, motor stall/slip handling and both destination trays.
- [ ] Disconnect each USB link during movement and while paused; confirm recovery and lamp shutdown.
- [ ] If replacing the approved existing model later, verify the new ONNX export, provenance and measured latency.
- [ ] Complete TASK-EVL-01 / TASK-EVL-02 with physical eggs and measured throughput.

## Authorized firmware installation record

Task: `TASK-NEW-FW-INSTALL-01`, 2026-10-08. The initial integration remained
software-only and retained the existing best.onnx. The user subsequently
explicitly authorized serial checks and firmware uploads, confirming the conveyor
was empty. All three boards answered their expected PING identities but rejected
the v3 HELLO, establishing that the previous unversioned firmware was installed.

All three current sketches were rebuilt for ESP32 Dev Module with Arduino-ESP32
3.3.11 and ESP32Servo 3.2.1, then uploaded in conveyor / egg / light order using
Arduino CLI `upload --verify`. Each upload reported a verified flash data hash.

| Port | Verified identity | Observed boot telemetry |
| --- | --- | --- |
| COM5 | CONVEYOR_V3, PROTOCOL=3 | POSITION=0, PAUSED=1, BUSY=0, REFERENCE_VALID=0 |
| COM7 | EGG_CONTROLLER_V3, PROTOCOL=3 | ANGLE=90, SENSOR=0, PAUSED=1, BUSY=0 after settling |
| COM9 | LIGHT_CONTROLLER_V3, PROTOCOL=3 | LIGHT=0, BUSY=0 |

All boards reported the expected STARTUP_ACK_REQUIRED fault. The application's
real `discover_boards` function subsequently returned CONVEYOR=COM5,
EGG_CONTROLLER=COM7 and LIGHT_CONTROLLER=COM9. Firmware checks sent PING / HELLO
only; no fault acknowledgements, conveyor moves, pause releases or lamp-ON
commands were sent. The egg board requests its neutral servo angle at boot.

Restart the operator app, inspect and confirm the empty conveyor, then click
**Start sorting** to connect and prepare it. This installation verifies
firmware identity and reported boot states; physical stop latency, relay output,
servo travel, gate distances and actual egg sorting still require the remaining
acceptance checks above.

## Simplified daily workflow verification

`TASK-NEW-EDGE-EASYFLOW-01`, 2026-10-09: one inspected Start sorting action now
combines remembered configuration, firmware role discovery, empty-station
preparation and cycle start. STOP cancels queued or running setup; late progress
and completion callbacks cannot restart it. Camera preview starts when the app
opens and remains available between batches. Inference remains stopped-only.

The main instruction uses plain feeding cues. Single scan and settings live in
Tools; automatic completion reads durable local totals and offers Start next
batch inline. Failed final-total reads retain the session identity for retry.
Saved camera/calibration settings survive preparation, and healthy board links
are reused. The new three-board display hold is 300ms. This machine's previous
1500ms default was changed to 300ms while retaining camera 0, COM5/COM7/COM9 and
all other remembered settings; custom saved hold values remain respected.

Verification used synthetic camera/serial adapters only:

- Required gate: **22 backend tests passed**, **325 edge tests passed / 1 Tk
  lifecycle skip**, and **dashboard production build passed**. The skipped Tk
  lifecycle test passed separately in a fresh Python process.
- Setup cancellation at queued, camera, discovery and preparation stages,
  including an external stop during presets; late callbacks, duplicate clicks,
  invalid batch input, failure/retry and preserved calibration were covered.
- Native window checks passed at 1280×860 and 1024×720. Captured idle, feeding,
  passage, review and completion layouts were inspected; STOP and review choices
  remain visible. The Tools entries and hidden main-screen diagnostic were
  checked in the native tests.
- `edge/launcher.py --check-runtime` confirmed the project `.venv` and PySerial
  **3.5**. No camera device or connected board was opened for this change.

The existing stopped evidence, WAL-before-release and gate-before-resume tests
passed in the full edge gate. Physical sorting accuracy and measured throughput
remain part of the rig acceptance checks, rather than software-test claims.


## Capture-settling adjustment

`TASK-NEW-EDGE-CAPTURE-SETTLE-01`, 2026-10-09: the operator reported blurred
captures and lower confidence. The previous three-board pre-capture pause was
700ms. The new default is **1500ms after confirmed lamp ON**, while the egg is
held and the conveyor is stopped. This adds 800ms per egg before flushing six
camera frames and collecting the existing three-frame evidence. The **300ms
post-classification result hold** is separate and remains unchanged.

The remembered settings on this machine were changed from 700ms to 1500ms only
for this pre-capture pause. Camera 0, COM5/COM7/COM9, camera controls, confidence
thresholds, gate calibration and result hold remain as saved. Other saved custom
settle values remain respected. Capture evidence now includes the configured
`settle_ms` alongside frame-drain and evidence timing.

This is a conservative first adjustment, not a measured blur correction. If the
held image stays blurred after the longer pause, inspect focus, exposure and egg
vibration with the lamp on. A lower confidence threshold would not correct image
quality. Physical sharpness and throughput must be observed on the actual rig.

Software verification: **37 focused regressions passed**; the required gate
passed **22 backend tests**, **329 edge tests / 1 shared-process Tk skip**, and
the dashboard build. The skipped Tk lifecycle test passed in a fresh process.
The capture-order regression checks lamp ON, a configured 1.5-second settling
pause, six-frame drain and three predictions in that order, independently of
the result-display hold. STOP during the settling pause prevents capture and
inference. Tests use fake camera/serial adapters; no device was activated.
