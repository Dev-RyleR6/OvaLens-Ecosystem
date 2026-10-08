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

### Quick setup with defaults

1. Run `python edge/launcher.py`, enter the batch details, and open the operator app.
   Windows users can instead double-click **Start_OvaLens.cmd** in the root folder.
   Both launch methods prefer the project `.venv`; close and reopen an older
   running window after a package/environment fix.
2. Empty the conveyor, then click **Use defaults & detect** on the main screen. Default ports are **COM5
   stepper**, **COM7 servo + IR sensor**, and **COM9 light**. Camera 0 and the handoff
   timing defaults load automatically. Detected roles and settings are saved.
3. Check the live camera, empty and align the conveyor, and check the gate. Tick
   **Conveyor empty, aligned; gate checked**, then click **Prepare conveyor**.
   This acknowledges faults, sets the inspected position as home and returns the
   servo to neutral. The conveyor stays stopped and the lamp stays off.
4. Click **Start sorting**, then feed eggs. **STOP** remains available during setup
   and operation. Repeat preparation for each batch.

Detection verifies firmware roles rather than trusting COM numbers; if the USB
ports change, it searches the other available ports. All three v3 sketches must
be installed first. Missing/wrong firmware produces a setup error with the source
location; nothing is flashed automatically. This update was tested only with
software fakes and did not open the connected boards.

**Use defaults & detect** replaces custom camera/timing settings with the handoff
presets. Use **Settings** for a previously measured custom calibration or a saved
two-board rig. Default gate distances are starting estimates; replace them with
measured distances when calibrating the physical rig.

### Advanced setup and calibration

1. Run `python edge/launcher.py`. Opening the app never starts a conveyor.
2. Open Settings, choose **Three-board candling rig**, and **Load selected rig
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
settle 700ms, six buffer grabs, display hold 1500ms, search timeout 30 seconds,
detection threshold 0.30 and automatic-sort threshold 0.85 (minimum 0.75).
The default gate exit is 417 steps from capture, approximately 2.5 seconds of
movement at the default speed. This estimate must be replaced with measured
calibration. The old IR offset and timed passage wait apply to the two-board profile.

## Candling, routing and recovery

The egg board pauses the belt locally. The host confirms lamp ON, waits settling,
requests six buffer grabs and a fresh read on the camera's sole owning thread,
then requires three agreeing real ONNX detections over at least 300ms within a
two-second evidence window. Geometry, confidence, frame order and settings revision
must agree. Camera failure cannot substitute synthetic frames into a real session.

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

After capture the lamp turns OFF. The belt advances only to the next sensor stop
or tracked gate boundary. A later egg's classification cannot overwrite an earlier
egg's route. The gate changes while stationary at entry and resets after the
tracked exit. Pauses do not consume passage distance. Overlapping gate intervals,
missing clearance, extra eggs, storage faults and synchronization disagreements
require recovery. No gate-passage sensor exists, so delivery remains estimated.

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

Retry **Use defaults & detect** in the operator app, inspect and confirm the
empty conveyor, then click **Prepare conveyor**. This installation verifies
firmware identity and reported boot states; physical stop latency, relay output,
servo travel, gate distances and actual egg sorting still require the remaining
acceptance checks above.
