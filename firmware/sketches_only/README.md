# Dual-ESP32 firmware with chamber IR, protocol v2

Tasks: `TASK-NEW-FW-SAFE-01`, `TASK-NEW-EDGE-CONTROL-01`. These sketches implement the wired conveyor/servo protocol, locally stopped IR indexes and reset notifications. Classification and multi-holder sorting coordination belong to the main edge app. These sketches have not been flashed by this change. See [station setup](../../docs/OVALENS_EDGE_STATION_CONTROL.md).

## Build and wiring

Keep this entire `sketches_only` directory together: both sketches include the
shared `protocol.h` in their parent directory. Open the corresponding `.ino`
in Arduino IDE, select **ESP32 Dev Module**, and Verify using Arduino-ESP32
3.x. Install ESP32Servo for the servo board. Each sketch is uploaded separately.

| Board | Pins / assumptions |
| --- | --- |
| Conveyor | A4988 STEP GPIO2, DIR GPIO4; ENABLE physically LOW; active-low chamber IR GPIO14. Confirm wiring and 3.3 V sensor compatibility against the rig. |
| Servo | SG90 signal GPIO18, external regulated 5V supply, shared ground. |

GPIO2 is a boot-strapping pin. A4988 motor power and current limiting must be
configured separately. Software HALT stops step pulses but cannot disable
holding current with ENABLE wired LOW. Provide a physical emergency stop.
Servo boot requests 90 degrees and may move; bench-test with an unloaded gate.
Candling-light control is intentionally absent until its wiring is confirmed.

## Request and response format

Serial is 115200 baud, newline terminated (CRLF accepted). Commands are
case-sensitive. Maximum line length is 95 printable ASCII characters.

Actuator, calibration, and recovery commands require an increasing positive ID:

```text
@1 ACK_FAULT
@2 SETHOME
@3 JOG:100
```

IDs range from 1 to 2147483647 and are tracked independently on each board.
Replies and associated telemetry carry `ID:<id>:` prefixes:

```text
ID:3:OK:MOVE_ACCEPTED
ID:3:OK:MOVE_DONE
ID:3:POSITION:100
ID:3:BUSY:0
```

Every tagged non-stop request consumes its ID, even if rejected. Older/reused
IDs return `ERROR:ID_REUSED` and never replay movement. This is rejection,
not cached-response replay. After an uncertain acknowledgement, query STATUS
and resolve the physical cycle; do not send the same move with a new ID.
IDs/settings reset at boot. Startup acknowledgement and conveyor reference
validation are mandatory; the host must discard queued commands on any reset.

`HELLO`, `PING`, `STATUS`, `HALT`, `STOP`, and `ESTOP` may be untagged.
Boot emits `BOOT:CONVEYOR_V2` or `BOOT:SERVO_V2`; a host must invalidate the cycle on these unsolicited reset notifications.
Stops execute even with an old ID. Boot/unsolicited fault reports are untagged.
HELLO identifies `CONVEYOR_V2` or `SERVO_V2` and `PROTOCOL=2`; check board role
before sending commands. STATUS includes LAST_ID, ACTIVE_ID, FAULT and BUSY.

## Heartbeat and recovery

Send PING or STATUS to **both boards every 0.5 seconds** in an independent
serial worker. HELLO also counts as a heartbeat. Only these recognized reads
refresh the heartbeat; movement, unknown commands, and malformed lines do not.
Timeout is 3000 ms, including while idle once a link has been established.

Both boards start with a latched fault. Connect, send HELLO, wait for BUSY:0,
and issue a tagged ACK_FAULT after operator acknowledgement. For the conveyor,
manually align a holder and send tagged SETHOME before referenced travel.
Manual JOG is available after acknowledgement for alignment; it does not
establish a trustworthy physical reference on its own.

On link expiry:

- Conveyor stops new pulses, cancels the active move, and invalidates reference
  and station calibration. An already issued HIGH pulse finishes normally.
- Servo holds its last requested angle, cancels timed completion, and latches
  a fault. SG90 has no motion brake or physical feedback; holding the command
  does not prove the shaft instantly stops.
- A later heartbeat never clears the fault. ACK_FAULT is required. Inspect and
  re-align the conveyor, SETHOME, then restore calibration before restarting.

The host must stop the conveyor if **either** required board loses communication.
Boards have no inter-board wire and cannot independently detect each other's
failure. Neither watchdog detects belt slip, motor stall, or mechanical jams.

## Conveyor commands

| Command | Behavior |
| --- | --- |
| HELLO / PING / STATUS | Identity, heartbeat, telemetry |
| HALT / STOP | Cancel the move, stop new pulses, preserve estimated position; never home |
| ESTOP | HALT plus latched fault and invalidated reference/calibration |
| ACK_FAULT | Acknowledge a latched fault while idle; does not restore reference |
| SETHOME | Confirm aligned current holder as software zero; invalidate stations |
| JOG:&lt;steps&gt; | Finite relative move, -100000..100000; idle only |
| INDEX:&lt;steps&gt; | Referenced nonzero relative move; arm chamber IR stop with 600 ms lockout |
| IR_OFFSET:&lt;steps&gt; | Configure 0..99999 steps from IR detection to stopped capture; never extend an index past its bound |
| SPEED:&lt;us&gt; | STEP half-period, 200..5000 us; idle only |
| HOME | Deliberate return to referenced software zero; idle only |
| SETCHAMBER / SETOUTPUT | Save referenced station coordinates |
| GOTO:CHAMBER / GOTO:OUTPUT | Travel to a saved station |
| TEST:&lt;steps&gt; | Positive finite move from referenced zero |

**Breaking change:** STOP no longer returns home. Use HOME deliberately.
START and the old optical-event cycle are unsupported. Repeated egg cycles
should use measured relative moves, not repeatedly return the belt to home.
Position counts issued pulses, not measured motion. Total software position
is bounded to +/-10000000 steps. Motion is constant speed without acceleration;
start with small slow bench moves. Default SPEED:1000 means 500 steps/second.

## Servo commands

| Command | Behavior |
| --- | --- |
| HELLO / PING / STATUS | Identity, heartbeat, telemetry |
| ESTOP / HALT / STOP | Hold last requested angle, cancel completion, latch fault |
| ACK_FAULT | Acknowledge fault while not settling |
| SERVO:&lt;angle&gt; | Request angle 0..180 |
| RESET | Move to configured neutral |
| SORT:FERTILE / SORT:INFERTILE | Move to configured route preset |
| SET_NEUTRAL / SET_FERTILE / SET_INFERTILE:&lt;angle&gt; | Configure corresponding preset, without moving |

Preset syntax is, for example, `@2 SET_NEUTRAL:85`. Defaults are neutral 90,
fertile 60, infertile 120. Values reset at boot; the host must restore its
approved calibration. Movement and preset edits are rejected while settling.
Acceptance and completion use the original command ID. Completion is a
500 ms settling timer, not independently measured angle or egg passage.
No automatic MANUAL_REVIEW route exists; hold for operator resolution unless
a separate physical review lane is calibrated and implemented.

## Bench sequence and host compatibility

Conveyor, unloaded (keep heartbeats running for moves longer than 3 seconds):

```text
HELLO
@1 ACK_FAULT
@2 SETHOME
@3 SPEED:2000
@4 JOG:100
STATUS
HALT
```

Servo, unloaded: HELLO, wait for startup BUSY:0, then tagged ACK_FAULT,
SET_NEUTRAL, SERVO, and RESET with increasing IDs. Wait for completion before
the next action. Test watchdog expiry and ESTOP with both mechanisms unloaded.

The main `edge/launcher.py` host supports this protocol with explicit station validation. The existing `firmware/prototype` host is **not compatible**: its actuator
commands lack IDs, it does not implement this recovery handshake, and it
expects unprefixed replies. Adapt and test the host before running real eggs.
Never automatically send ACK_FAULT or SETHOME on reconnect.

## Verification

```text
python -m pytest edge/tests/test_sensorless_firmware.py -v
```

The tests compile the actual sketches using native g++/clang++ with fake
Arduino/servo interfaces. They exercise command parsing, cancellation, faults,
heartbeat expiry/wraparound, correlation IDs, initialization failures and
servo settling. They skip if no native compiler is available. They do not
prove real ISR timing, physical stopping, electrical behavior, or sorting
accuracy. Also Verify both sketches with Arduino-ESP32 and bench-test the rig.
