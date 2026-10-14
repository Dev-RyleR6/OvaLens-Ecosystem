# Three-ESP32 candling rig

Use the conveyor, egg-controller and light-controller sketches in this directory
with the main `edge/launcher.py` application's **Three-board candling rig** profile.
See [setup, protocol and verification](../../docs/EDGE_THREE_BOARD_IMPLEMENTATION.md).

Keep the complete `firmware/` tree: the shared guard uses the bounded ASCII parser
in `sketches_only/protocol.h`. Verify each sketch independently with Arduino-ESP32
3.x, ESP32 Dev Module, and ESP32Servo. Discovery uses the handoff's PING role
identities plus a mandatory v3 HELLO. Movement/configuration commands require IDs.
The unversioned handoff firmware must be replaced before automatic sorting.

All boards boot faulted. The egg board holds hardware pause HIGH; the conveyor
pause input has a pull-up, and the lamp boots OFF. Inspect and acknowledge faults,
align the unloaded belt, deliberately set software home, then validate calibration.
No automatic recovery or blind movement retry is supported. Unplugging a board
does not prove a mechanical stop; bench-test the assembled rig before using eggs.

## Stepper-only diagnostic (COM5)

Close Edge and Arduino Serial Monitor, empty the conveyor, then run from the
repository root:

```powershell
.venv\Scripts\python.exe scripts\test_stepper.py --check
.venv\Scripts\python.exe scripts\test_stepper.py
```

The first command displays status. The second asks for confirmation, makes
one relative **50-step** jog at a slow **5000 us pulse half-period**, verifies
reported completion, then sends ESTOP and closes COM5. It opens no servo, IR,
camera or lamp ports. It does not set software home, classify eggs or save scans.
Change direction/distance with `--steps -50` / `--steps 200`; the limit is
1000 steps per invocation. `--speed-us` accepts 200–5000; higher is slower.
Press Ctrl+C to stop. Errors never cause an automatic movement retry.

The installed v3 conveyor firmware requires the GPIO27 hardware pause input
to be LOW before moving. COM7 controls that pause wire. If pause is HIGH, this
COM5-only script reports **Hardware pause is active** and exits; it cannot
release the pause and does not bypass it. Closing Edge or resetting COM7 normally
holds this signal HIGH. In that case, use Edge's **Camera controls → Cradle**
workflow for a coordinated test instead of expecting a COM5-only jog to work.
After any serial test, inspect and Prepare station again before sorting.
The reported step count confirms controller pulses, not actual motor movement;
watch the unloaded conveyor to verify smooth physical operation.

## Servo-only diagnostic (COM7)

Close Edge and Arduino Serial Monitor and clear the entire gate path. From the
repository root run:

```powershell
.venv\Scripts\python.exe scripts\test_servo.py
```

Confirm with **y** before any connection. Opening COM7 can reset the ESP32 and
move its servo to the firmware boot angle (90°), including in `--check` mode.
The diagnostic waits two seconds for boot, clears startup replies and terminates
any partial serial input line before requesting fresh v3 identity/status. If
`ERROR:INVALID_LINE` persists after this synchronization, the test stops; close
other serial applications and check the installed firmware and USB connection.
The default sequence is **90° → 120° → 90°**, with one second to observe each
intermediate position. Each command waits for reported completion; the conveyor
pause stays held. COM5 and COM9 are never opened and no RESUME is issued.
No IR sensor is required: missing or blocked IR readings and egg-cycle state
do not prevent this standalone servo test. Normal sorting keeps its IR checks.

Use `--angles 90 120 90` for a custom sequence within the gate's clear mechanical
range, or `--check` to display status without sending angle commands. Angles must
be 0–180° with at most ten per invocation. `--hold-ms 2000` changes observation
time between confirmed positions; it does not change the servo's physical speed.
The script does not change saved settings or firmware sorting presets.

Ctrl+C, controller faults, lost pause or incorrect angle feedback stops the
sequence without retry or an automatic return movement. Cleanup requests ESTOP,
holds the last angle and closes COM7. Inspect the gate and Prepare station again
before sorting. Controller-reported angles are commanded targets, not independent
position feedback; observe that the servo actually moves smoothly.
