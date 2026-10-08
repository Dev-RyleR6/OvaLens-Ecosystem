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
