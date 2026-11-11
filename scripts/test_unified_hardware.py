"""
Interactive Terminal Console for OvaLens Single-ESP32 Hardware Testing.
Uses the production UnifiedBoardController protocol to test Lamp, Servo, IR, and Stepper.

Run directly in terminal:
    .venv\\Scripts\\python.exe scripts\\test_unified_hardware.py
Or with flags:
    .venv\\Scripts\\python.exe scripts\\test_unified_hardware.py --lamp
    .venv\\Scripts\\python.exe scripts\\test_unified_hardware.py --servo
    .venv\\Scripts\\python.exe scripts\\test_unified_hardware.py --ir
    .venv\\Scripts\\python.exe scripts\\test_unified_hardware.py --stepper-fwd
    .venv\\Scripts\\python.exe scripts\\test_unified_hardware.py --stepper-rev
"""
import sys
from pathlib import Path
import time
import argparse
import serial.tools.list_ports

# Ensure edge module is in path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "edge"))
from src.iot.unified_board import UnifiedBoardController

DEFAULT_PORT = "COM5"


def resolve_port(port_override=None):
    if port_override:
        return port_override
    ports = [p.device for p in serial.tools.list_ports.comports()]
    if DEFAULT_PORT in ports:
        return DEFAULT_PORT
    for p in serial.tools.list_ports.comports():
        desc = (p.description or "").lower()
        if "ch340" in desc or "cp210" in desc or "usb" in desc or "serial" in desc or "esp32" in desc:
            return p.device
    return ports[0] if ports else DEFAULT_PORT


def connect_controller(port):
    print(f"Connecting to Unified ESP32 on {port}...")
    ctrl = UnifiedBoardController(port)
    ctrl.start()

    deadline = time.monotonic() + 5.0
    while not ctrl.link._status_complete:
        state = ctrl.link.snapshot()
        if state.error or time.monotonic() >= deadline:
            ctrl.stop()
            raise RuntimeError(state.error or f"Connection timed out on {port}. Check USB connection.")
        time.sleep(0.05)

    # Automatically clear any startup or link timeout fault
    state = ctrl.link.snapshot()
    fault = state.telemetry.get("FAULT", "NONE")
    if fault != "NONE":
        ctrl.link.command("ACK_FAULT").result(3.5)

    print(f"[CONNECTED] ESP32 running UNIFIED_V3 protocol on {port}!\n")
    return ctrl


def toggle_lamp(ctrl):
    state = ctrl.link.snapshot()
    cur_light = state.telemetry.get("LIGHT") == "1"
    new_cmd = "LIGHT_OFF" if cur_light else "LIGHT_ON"
    res = ctrl.link.command(new_cmd).result(3.5)
    light_status = "ON [HIGH]" if res.get("LIGHT") == "1" else "OFF [LOW]"
    print(f">>> Lamp is now: {light_status}")


def test_servo(ctrl):
    print(">>> Testing Sorting Gate Servo...")
    print(" -> Moving to Fertile Accept (180 deg)...")
    ctrl.link.command("SORT:FERTILE").result(3.5)
    time.sleep(1.0)

    print(" -> Moving to Infertile Reject (50 deg)...")
    ctrl.link.command("SORT:INFERTILE").result(3.5)
    time.sleep(1.0)

    print(" -> Returning to Neutral (90 deg)...")
    ctrl.link.command("RESET").result(3.5)
    time.sleep(0.5)
    print(">>> Servo Test Complete!")


def test_ir(ctrl, duration=10):
    print(f"\n>>> LIVE IR SENSOR TEST ACTIVE ({duration} seconds)...")
    print(">>> Wave your hand in front of the IR sensor now!\n")
    start = time.monotonic()
    last_sensor = None
    while time.monotonic() - start < duration:
        state = ctrl.link.snapshot()
        sensor_active = state.telemetry.get("SENSOR") == "1"
        if sensor_active != last_sensor:
            last_sensor = sensor_active
            if sensor_active:
                print("  [EVENT] EGG / OBJECT DETECTED! (IR Sensor Active)")
            else:
                print("  [EVENT] BEAM CLEAR")
        time.sleep(0.05)
    print(">>> IR Test Finished.\n")


def jog_stepper(ctrl, steps=100):
    direction = "FORWARD" if steps > 0 else "REVERSE"
    print(f">>> Jogging Stepper {direction} ({abs(steps)} steps)...")
    ctrl.link.command("RESUME").result(3.5)
    timeout = 3.0 + abs(steps) * 0.01
    res = ctrl.link.command(f"JOG:{steps}", timeout=timeout).result(timeout + 0.5)
    ctrl.link.command("PAUSE").result(3.5)
    print(f">>> Move Done! New Position: {res.get('POSITION')}")


def print_status(ctrl):
    state = ctrl.link.snapshot()
    tel = state.telemetry
    print("\n--- Board Telemetry ---")
    for k in sorted(tel.keys()):
        print(f"  {k:18} : {tel[k]}")
    print()


def interactive_menu(ctrl):
    menu_text = """
======================================================
        OvaLens Single-ESP32 Hardware Console
======================================================
  [1]  Toggle Candling Lamp ON / OFF     (GPIO 27)
  [2]  Test Sorting Servo Gate           (GPIO 32)
  [3]  Live IR Sensor Test (10s)         (GPIO 26)
  [4]  Jog Stepper Forward (100 steps)   (GPIO 16, 4)
  [5]  Jog Stepper Reverse (100 steps)   (GPIO 16, 4)
  [s]  Show Hardware Status & Telemetry
  [m]  Show this menu again
  [q]  Quit
======================================================
"""
    print(menu_text)
    while True:
        try:
            choice = input("Enter choice [1, 2, 3, 4, 5, s, m, q]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting console.")
            break

        if choice in ("q", "quit", "exit"):
            print("Exiting console. Goodbye!")
            break
        elif choice in ("m", "menu", "?"):
            print(menu_text)
        elif choice == "1":
            toggle_lamp(ctrl)
        elif choice == "2":
            test_servo(ctrl)
        elif choice == "3":
            test_ir(ctrl, duration=10)
        elif choice == "4":
            jog_stepper(ctrl, steps=100)
        elif choice == "5":
            jog_stepper(ctrl, steps=-100)
        elif choice == "s":
            print_status(ctrl)
        else:
            print("[!] Invalid option. Enter 1, 2, 3, 4, 5, s, or q.")


def main():
    parser = argparse.ArgumentParser(description="Test single-ESP32 production hardware")
    parser.add_argument("--port", default="", help="Serial port (default: auto-detect COM5)")
    parser.add_argument("--lamp", action="store_true", help="Toggle lamp ON for 2s then OFF")
    parser.add_argument("--servo", action="store_true", help="Sweep servo 180 -> 50 -> 90")
    parser.add_argument("--ir", action="store_true", help="Monitor IR sensor for 10s")
    parser.add_argument("--stepper-fwd", action="store_true", help="Jog stepper forward 100 steps")
    parser.add_argument("--stepper-rev", action="store_true", help="Jog stepper reverse 100 steps")
    parser.add_argument("--status", action="store_true", help="Display board telemetry")

    args = parser.parse_args()
    port = resolve_port(args.port)

    ctrl = None
    try:
        ctrl = connect_controller(port)

        if args.lamp:
            print("Turning Lamp ON...")
            ctrl.link.command("LIGHT_ON").result(3.5)
            print("Waiting 2 seconds...")
            time.sleep(2.0)
            print("Turning Lamp OFF...")
            ctrl.link.command("LIGHT_OFF").result(3.5)
            print("Lamp test complete.")
        elif args.servo:
            test_servo(ctrl)
        elif args.ir:
            test_ir(ctrl, duration=10)
        elif args.stepper_fwd:
            jog_stepper(ctrl, steps=100)
        elif args.stepper_rev:
            jog_stepper(ctrl, steps=-100)
        elif args.status:
            print_status(ctrl)
        else:
            interactive_menu(ctrl)

    except Exception as e:
        print(f"\n[ERROR] Hardware test error: {e}", file=sys.stderr)
        return 1
    finally:
        if ctrl:
            try:
                ctrl.stop()
            except Exception:
                pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
