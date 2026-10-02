# OvaLens edge hardware prototype

One CustomTkinter desktop app combines the controls from
`firmware/esp32_actuator/egg_controller.py` and `servo_controller.py`.
It uses two independently connected ESP32 boards at **115200 baud**.
Each board has its own background worker; USB connection, boot wait, reads,
writes, and disconnection run outside the GUI thread.

## Launch

From the monorepo root, with Python 3.11+ and Tk installed:

```powershell
python -m pip install -r firmware/prototype/requirements.txt
python -m firmware.prototype.app
```

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
6. **Start conveyor** sends `START` to the egg board after both connections
   are ready. Servo sorting remains manual through the test buttons.
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

Simulation exercises calibration, one-step distance tests, presets, and an
automatic chamber/output/home position loop. Its moves are synthetic and
do not model motor timing, loads, sensors, or real sorting accuracy.

This is a mechanical prototype of the edge app: it does not capture images,
run inference, record scans, or connect to the backend. It uses only the
Day 10 `FERTILE` / `INFERTILE` sorting presets. Future automatic sorting must
add cradle tracking, SQLite WAL scan persistence, and manual review for
confidence below 0.75 or synchronization errors before driving the rig.

## Verification

```powershell
python -m pytest edge/tests/test_firmware_prototype.py -v
```

These tests exercise command validation, board routing, partial serial
messages, worker-only I/O, shutdown, connection failures, and simulation.
They do not verify physical motor travel or servo alignment.
