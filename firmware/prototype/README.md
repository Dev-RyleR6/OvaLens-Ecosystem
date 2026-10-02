# OvaLens edge hardware prototype

One CustomTkinter desktop app combines real camera egg detection with the controls from
`firmware/esp32_actuator/egg_controller.py` and `servo_controller.py`.
It uses two independently connected ESP32 boards at **115200 baud**.
Each board has its own background worker; USB connection, boot wait, reads,
writes, and disconnection run outside the GUI thread.

## Operator workspace and detection

- **Operate & detect** shows the real camera, Day 10 result, confidence,
  inference latency, detection counts, optical events, and quick hardware controls.
- **Calibration** holds conveyor positions, motor tests, and servo presets.
- **Serial monitor** appends logs while visible and retains the most recent
  500 entries. Numeric telemetry is coalesced so bursts do not build a stale UI backlog.

Click **Start camera** using camera index 0, or choose the connected candling
camera's index. Camera initialization, continuous frame draining, ONNX loading,
three warmup passes, inference, and SQLite writes run outside the GUI thread.
The preview targets 30 FPS; inference is capped at 10 passes per second and
uses the newest frame. The existing `edge/models/weights/best.onnx` must load;
missing cameras/models report an error and do not generate simulated detection results.

Hold one egg in the central camera zone. Three consistent detections record
one scan; five clear frames rearm detection for the next egg. Empty frames
are shown as **No egg**. Geometry, illuminated area, and centering are checked
before classification. Confidence below 0.75 is **Manual review**. Camera,
storage, or UI backlog errors pause detection and prevent scan-based sorting.

Scans are committed with SQLite WAL to `edge/db/prototype_scans.db` before the
**Sort recorded egg** button becomes available. This button requests the saved
Fertile/Infertile preset on the real servo board. It requires both real boards,
a fresh matching detection, confidence at least 0.75, and a scan under 10 seconds
old. One sort request is permitted per saved scan. The monitor confirms USB
write, not physical delivery; this firmware does not provide a shared ACK protocol.

Manual sorting remains available when the automatic cycle is stopped. The
prototype also provides the repeatable integration cycle below. Prototype
sessions remain local; they do not sync to the backend.

## Automatic stepper / camera / servo cycle

**COM5 is the stepper; COM7 is the servo.** In **Calibration**, choose:

- **Classify & sort**: wait for a stable, recorded fertility result and use
  the Fertile/Infertile angles in the servo panel.
- **Detect & block**: wait for a stable, recorded egg detection and use a
  fixed blocking angle, regardless of the fertility class.

Both modes require real camera/model results, confidence at least 0.75,
and successful SQLite persistence. No imaginary egg or simulated detection
is injected. An empty view waits for an egg until the timeout.

Set the initial travel, camera-to-servo travel, and clearance travel in
**motor steps**, then press **START AUTO CYCLE**. Initial test values are
120 / 40 / 40 steps; these are editable prototype values, not measured rig
dimensions. Camera index defaults to 0 and starts automatically if needed.

1. Query stepper status, require it to be idle, apply the selected speed,
   configure fertility presets, and move the servo to neutral.
2. Move forward by the camera distance using `JOG`. Wait for the actual
   target `POSITION`, `BUSY:0`, and `AUTO:0` after the command is written.
3. Keep the stepper stopped, allow camera settling, then collect three
   stable detections from fresh stationary frames and commit the scan.
4. Resume for the camera-to-servo distance and wait for target/idle feedback.
5. Activate the sorting/blocking angle. Require `ANGLE:` feedback and allow
   the configured servo settling time before moving again.
6. Move through the clearance distance with the servo held, then return the
   servo to neutral. Count the completed cycle and repeat from step 2.

Distances are **relative forward moves**: repeated cycles advance the belt;
they do not return home or redefine software zero. Camera capture continues
during travel, while inference/scan recording are suspended. Each camera stop
explicitly rearms inspection, so neither an old frame nor an earlier saved
scan can resume the stepper. Manual motion controls are locked during a cycle.

This is a segmented integration cycle with a brief stop at the gate. The
legacy boards cannot schedule an accurately synchronized servo stroke during
one continuous stepper move. Missing status/angle feedback, failed storage,
camera loss, controller errors, low confidence, or a detection timeout enter
**Manual review** and cancel the loop. There is no automatic retry or reconnect.
Inspect the issue before pressing Start again. Stop also suspends inference;
restart the camera for independent manual detection, or start another cycle.

`STOP & HOME + NEUTRAL` cancels the cycle, discards queued commands, sends
stepper `STOP`, and resets the servo. **The deployed `STOP` returns home and
can cause movement**; routine station pauses therefore use completed finite
moves. This prototype does not track multiple cradles or confirm mechanical
egg passage. Position and angle replies report board state, not independent
physical encoders. Verify the travel and gate geometry on the rig.

An optical counter recognizes `EVENT:EGG_DETECTED` from the egg board with a
600 ms debounce. Camera presence and optical triggers are separate counts.
It does not infer optical events from conveyor position. The current board must
emit this event for the counter to advance; no firmware is flashed by the app.

## Launch

From the monorepo root, with Python 3.11+ and Tk installed:

```powershell
python -m pip install -r firmware/prototype/requirements.txt
python -m firmware.prototype.app
```

For the prototype rig with **egg controller COM5** and **servo controller COM7**:

```powershell
python -m firmware.prototype.app --egg-port COM5 --servo-port COM7 --connect
```

From inside the `firmware` directory, run:

```powershell
python -m prototype.app --egg-port COM5 --servo-port COM7 --connect
```

Or double-click `firmware/test_integration.cmd`. This launcher uses real
hardware, connects both boards, and requests their status. Movement begins
only when an operator clicks a transport or servo control. Close the other
standalone controllers and any Arduino serial monitor first so the COM ports
are available. Explicit port selections are retained when ports are refreshed.

For a hardware-free demo:

```powershell
python -m firmware.prototype.app --simulate
```

Click **Connect** in both connection cards. `--simulate` preselects simulation;
it does not connect automatically. No USB ports are opened in simulation.
Failed hardware connections stay disconnected and report the error.

## Hardware compatibility

Use the same firmware that works with the two existing standalone Python
controllers. Choose a different COM port for each board. The egg board accepts
the transport commands below; the servo board accepts the preset commands.

**The existing `esp32_actuator.ino` is a different, single-actuator firmware.**
Its `CMD:EJECT`, `CMD:LIGHT`, and `RESP:...` protocol does not implement the
conveyor and preset protocols used here. The matching two-board Arduino
sketches are not currently checked into this repository. This app does not
flash or modify firmware. Verify the board firmware before using hardware;
a successful USB connection alone does not confirm protocol compatibility.

## Operator workflow

1. Connect both boards, or enable simulation for both. Mixed hardware and
   simulation cannot start the shared conveyor control.
2. Jog the conveyor to its reference position and **Set home here**. This
   changes software zero; it is not a physical limit-switch homing operation.
3. Jog to the chamber and output stations and save each position.
4. Set the conveyor step delay (200–5000 microseconds). Run a single distance
   test from home; return home before repeating it.
5. Move the servo to test angles (0–180 degrees), save the fertile and
   infertile presets, then test each sorting position.
6. For repeated integration, configure **Automatic cycle settings** and click
   **START AUTO CYCLE**. Manual test buttons remain available outside a cycle.
7. **Stop & Home + Neutral** discards pending commands and independently
   queues `STOP` for the egg board and `RESET` for the servo board. If one
   connection fails, the other still receives its command.

`STOP` uses the existing conveyor's stop-and-return-home behavior and can
cause motion. It is **not an emergency stop**. An in-flight serial write may
finish before the stop is sent. Use a physical emergency stop to cut power.
The two boards do not provide a shared acknowledgement handshake, so shared
controls are best-effort independent commands rather than atomic operations.

Closing the app cancels queued commands, asks a connected conveyor to stop
and return home, asks a connected servo to reset, and closes both ports.
There is no automatic reconnect or replay of motion commands.

## Command contract

| Board | Commands | Reported telemetry |
| --- | --- | --- |
| Egg | `START`, `STOP`, `HOME`, `STATUS`, `SETHOME`, `SETCHAMBER`, `SETOUTPUT`, `GOTO:CHAMBER`, `GOTO:OUTPUT`, `JOG:<steps>`, `SPEED:<us>`, `TEST:<steps>` | `POSITION:`, `CHAMBER:`, `OUTPUT:`, `SPEED:`, `STATE:`, `OK:CHAMBER:`, `OK:OUTPUT:`, `OK:HOME_SET`, `ERROR:` |
| Servo | `SERVO:<angle>`, `SET_FERTILE:<angle>`, `SET_INFERTILE:<angle>`, `SORT:FERTILE`, `SORT:INFERTILE`, `RESET`, `STATUS` | `ANGLE:`, `FERTILE:`, `INFERTILE:`, `STATE:`, `ERROR:` |

Commands are newline-terminated. The serial monitor tags each line by board
and retains the most recent 500 entries. TX means the worker wrote the
command; reported state comes from board replies. Edited fields are requested
settings; telemetry cards show the board's reported settings.

The deployed conveyor also reports `BUSY:0|1` and `AUTO:0|1`; these update
the state to Idle, Moving, or Auto Running. The deployed servo's `ANGLE:`
reply marks it Responding when no `STATE:` line is supplied. Additional
servo calibration lines such as `NEUTRAL:` remain visible in the serial log.

Simulation exercises calibration, one-step distance tests, presets, and an
automatic chamber/output/home position loop. Its moves are synthetic and
do not model motor timing, loads, sensors, or real sorting accuracy.

The prototype uses only Day 10 `FERTILE` / `INFERTILE` model classes.
Production conveyor sorting still requires cradle tracking and independently
verified mechanical alignment. Local prototype records remain offline.

## Verification

```powershell
python -m pytest edge/tests/test_firmware_prototype.py edge/tests/test_prototype_vision.py edge/tests/test_prototype_cycle.py -v
```

These tests exercise command validation, board routing, partial serial
messages, worker-only I/O, shutdown, connection failures, and simulation.
Detection tests also cover empty/invalid frames, duplicate suppression,
optical debounce, camera failure, WAL persistence, storage failure, and stale
or repeated sorting guards. Cycle tests cover both modes, motion feedback,
station capture rearming, servo settling, repeat/stop behavior, and failures.
They do not verify physical motor travel or servo alignment.
