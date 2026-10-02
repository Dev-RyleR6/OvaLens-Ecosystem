"""OvaLens mechanical edge prototype. Run: python -m firmware.prototype.app."""

import argparse
from collections import deque
from datetime import datetime
import queue
import tkinter as tk
import time

import customtkinter as ctk
from serial.tools import list_ports

from .controller import PrototypeRig, choose_port, egg_status, integer


BG = "#0F172A"
CARD = "#1E293B"
BORDER = "#334155"
MAROON = "#800000"
GREEN = "#357a38"
RED = "#DC2626"
TEXT = "#F8FAFC"
MUTED = "#CBD5E1"


class PrototypeApp(ctk.CTk):
    def __init__(self, simulate=False, egg_port="", servo_port="", connect=False):
        super().__init__()
        self.title("OvaLens | Edge Hardware Prototype")
        self.geometry("1180x900")
        self.minsize(1000, 760)
        self.configure(fg_color=BG)
        self.events = queue.Queue()
        self.rig = PrototypeRig(self.events)
        self.preferred_ports = {"egg": egg_port, "servo": servo_port}
        self.egg_flags = {"BUSY": None, "AUTO": None}
        self.connection_widgets = {}
        self.telemetry = {}
        self.entries = {}
        self.states = {"egg": "OFFLINE", "servo": "OFFLINE"}
        self.connection_states = {"egg": "DISCONNECTED", "servo": "DISCONNECTED"}
        self.logs = deque(maxlen=500)
        self.closing = False
        self._log_dirty = False
        self._last_log_render = 0.0
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        self._build_header()
        self._build_connections(simulate)
        self._build_shared_controls()
        self._build_workspace()
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.after(0, self.refresh_ports)
        self.after(16, self.poll)
        if connect:
            self.after(0, self.connect_all)

    def label(self, parent, text, size=13, color=TEXT, **kwargs):
        return ctk.CTkLabel(parent, text=text, text_color=color,
                            font=("Segoe UI", size), **kwargs)

    def button(self, parent, text, callback, color=BORDER, **kwargs):
        return ctk.CTkButton(parent, text=text, command=lambda: self.perform(callback),
                             fg_color=color, hover_color=MAROON, height=34,
                             text_color=TEXT, **kwargs)

    def perform(self, callback):
        try:
            callback()
        except (ValueError, RuntimeError) as exc:
            self.notice.configure(text=str(exc), text_color="#FCA5A5")
            self.add_log("APP", "ERROR", str(exc))

    def card(self, parent, title):
        frame = ctk.CTkFrame(parent, fg_color=CARD, border_color=BORDER, border_width=1)
        frame.pack(fill="x", padx=8, pady=7)
        self.label(frame, title, 18).pack(anchor="w", padx=16, pady=(12, 6))
        return frame

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=MAROON, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        self.label(header, "OVALENS  /  EDGE HARDWARE PROTOTYPE", 24).pack(
            anchor="w", padx=24, pady=(16, 2))
        self.label(header, "Foundation University  •  Egg transport + servo sorting", 13).pack(
            anchor="w", padx=24, pady=(0, 16))

    def _build_connections(self, simulate):
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.grid(row=1, column=0, sticky="ew", padx=16, pady=12)
        row.grid_columnconfigure((0, 1), weight=1, uniform="connections")
        for column, role in enumerate(("egg", "servo")):
            frame = ctk.CTkFrame(row, fg_color=CARD, border_width=1, border_color=BORDER)
            frame.grid(row=0, column=column, sticky="ew", padx=6)
            frame.grid_columnconfigure(0, weight=1)
            self.label(frame, f"{role.title()} ESP32  /  115200 baud", 16).grid(
                row=0, column=0, columnspan=3, sticky="w", padx=12, pady=8)
            preferred = self.preferred_ports[role]
            port = ctk.CTkComboBox(frame, values=[preferred or "No ports"], state="readonly", width=140)
            port.set(preferred or "No ports")
            port.grid(row=1, column=0, sticky="ew", padx=12, pady=6)
            self.button(frame, "Refresh", self.refresh_ports, width=70).grid(
                row=1, column=1, padx=4)
            connect = self.button(frame, "Connect", lambda r=role: self.toggle_connection(r),
                                  color=MAROON, width=105)
            connect.grid(row=1, column=2, padx=(4, 12))
            mock = tk.BooleanVar(value=simulate)
            switch = ctk.CTkSwitch(frame, text="Simulation (no hardware)", variable=mock,
                                  progress_color=MAROON)
            switch.grid(row=2, column=0, columnspan=3, sticky="w", padx=12, pady=8)
            status = self.label(frame, "DISCONNECTED", color=MUTED)
            status.grid(row=3, column=0, columnspan=3, sticky="w", padx=12, pady=(0, 8))
            self.connection_widgets[role] = (port, connect, mock, switch, status)

    def _build_shared_controls(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 8))
        self.start_button = self.button(frame, "START CONVEYOR", self.rig.start,
                                         color=MAROON, width=190)
        self.start_button.pack(side="left", padx=(0, 8))
        self.button(frame, "STOP & HOME + NEUTRAL", self.rig.stop, color=RED,
                    width=240).pack(side="left", padx=8)
        self.button(frame, "Status: both boards", self.status_all, width=160).pack(
            side="left", padx=8)

    def _build_workspace(self):
        tabs = ctk.CTkTabview(self, fg_color=BG, segmented_button_selected_color=MAROON)
        tabs.grid(row=3, column=0, sticky="nsew", padx=16, pady=(0, 6))
        controls = tabs.add("Hardware controls")
        monitor = tabs.add("Serial monitor")
        controls.grid_columnconfigure((0, 1), weight=1, uniform="panels")
        controls.grid_rowconfigure(0, weight=1)
        egg_panel = ctk.CTkScrollableFrame(controls, fg_color=BG)
        egg_panel.grid(row=0, column=0, sticky="nsew")
        servo_panel = ctk.CTkScrollableFrame(controls, fg_color=BG)
        servo_panel.grid(row=0, column=1, sticky="nsew")
        self._build_egg(egg_panel)
        self._build_servo(servo_panel)
        self.label(monitor, "Commands are logged after USB write. Board replies confirm device state.",
                   color=MUTED).pack(anchor="w", padx=12, pady=8)
        self.log_box = ctk.CTkTextbox(monitor, fg_color=CARD, font=("Consolas", 13))
        self.log_box.pack(fill="both", expand=True, padx=12, pady=6)
        self.log_box.configure(state="disabled")
        self.button(monitor, "Clear log", self.clear_log, width=100).pack(anchor="e", padx=12, pady=6)
        self.notice = self.label(self, "Hardware mode. Select each board's COM port and connect both controllers.",
                                 color=MUTED, wraplength=950, anchor="w")
        self.notice.grid(row=4, column=0, sticky="ew", padx=24, pady=(0, 4))
        self.label(self, "Manual hardware prototype • Sorting buttons test presets; no AI inference. "
                   "STOP returns home; use a physical E-stop to cut power.",
                   color=MUTED, wraplength=950).grid(row=5, column=0, sticky="ew", padx=24, pady=(0, 12))

    def telemetry_card(self, panel, role, title, fields):
        frame = self.card(panel, title)
        for field, caption in fields:
            label = self.label(frame, f"{caption}: —", color=MUTED)
            label.pack(anchor="w", padx=16, pady=2)
            self.telemetry[(role, field)] = (label, caption)
        self.label(frame, " ", 2).pack()

    def field(self, frame, key, label, initial):
        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=5)
        self.label(row, label, color=MUTED).pack(side="left")
        entry = ctk.CTkEntry(row, width=110)
        entry.insert(0, initial)
        entry.pack(side="right")
        self.entries[key] = entry
        return row

    def actions(self, frame, actions):
        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=8)
        for column, (text, callback, color) in enumerate(actions):
            row.grid_columnconfigure(column, weight=1)
            self.button(row, text, callback, color=color, width=50).grid(
                row=0, column=column, sticky="ew", padx=4)

    def send(self, role, command):
        self.rig.links[role].send(command)

    def number_command(self, role, prefix, key, low, high):
        value = integer(self.entries[key].get(), low, high, key.replace("_", " ").title())
        self.send(role, f"{prefix}:{value}")

    def _build_egg(self, panel):
        self.telemetry_card(panel, "egg", "Egg conveyor", [
            ("STATE", "State"), ("POSITION", "Position (steps)"),
            ("CHAMBER", "Chamber (steps)"), ("OUTPUT", "Output (steps)"),
            ("SPEED", "Step delay (µs)")])
        frame = self.card(panel, "Transport & calibration")
        self.actions(frame, [("Home", lambda: self.send("egg", "HOME"), BORDER),
                             ("Status", lambda: self.send("egg", "STATUS"), BORDER)])
        self.label(frame, "Jog relative to current position", color=MUTED).pack(anchor="w", padx=16)
        self.actions(frame, [(str(value), lambda v=value: self.send("egg", f"JOG:{v}"), BORDER)
                             for value in (-100, -10, -1, 1, 10, 100)])
        self.actions(frame, [("Set home here", lambda: self.send("egg", "SETHOME"), MAROON)])
        self.label(frame, "Set home redefines software zero at the current position.",
                   color=MUTED).pack(anchor="w", padx=16)
        for name in ("CHAMBER", "OUTPUT"):
            self.actions(frame, [
                (f"Save {name.lower()}", lambda n=name: self.send("egg", f"SET{n}"), BORDER),
                (f"Go to {name.lower()}", lambda n=name: self.send("egg", f"GOTO:{n}"), BORDER)])
        self.field(frame, "step_delay", "Step delay (200–5000 µs)", "800")
        self.actions(frame, [("Apply speed", lambda: self.number_command(
            "egg", "SPEED", "step_delay", 200, 5000), MAROON)])
        frame = self.card(panel, "Single distance test")
        self.field(frame, "test_distance", "Distance (1–100000 steps)", "500")
        self.field(frame, "test_delay", "Step delay (200–5000 µs)", "800")
        self.actions(frame, [("Run once", self.motion_test, MAROON),
                             ("Stop & home", lambda: self.rig.links["egg"].send("STOP", priority=True), RED)])
        self.label(frame, "Return HOME before repeating a distance test.", color=MUTED).pack(
            anchor="w", padx=16, pady=(0, 10))

    def motion_test(self):
        # Validate both before enqueueing either command.
        distance = integer(self.entries["test_distance"].get(), 1, 100000, "Distance")
        speed = integer(self.entries["test_delay"].get(), 200, 5000, "Step delay")
        self.rig.links["egg"].send_many([f"SPEED:{speed}", f"TEST:{distance}"])

    def _build_servo(self, panel):
        self.telemetry_card(panel, "servo", "Sorting servo", [
            ("STATE", "State"), ("ANGLE", "Reported angle (°)"),
            ("FERTILE", "Fertile preset (°)"), ("INFERTILE", "Infertile preset (°)")])
        frame = self.card(panel, "Manual servo positioning")
        self.selected = self.label(frame, "Selected angle: 90°", color=MUTED)
        self.selected.pack(anchor="w", padx=16)
        self.slider = ctk.CTkSlider(frame, from_=0, to=180, number_of_steps=180,
                                    progress_color=MAROON, command=self.select_angle)
        self.slider.set(90)
        self.slider.pack(fill="x", padx=18, pady=12)
        self.field(frame, "angle", "Angle (0–180°)", "90")
        self.actions(frame, [("Move", lambda: self.number_command("servo", "SERVO", "angle", 0, 180),
                              MAROON), ("Neutral", lambda: self.send("servo", "RESET"), BORDER)])
        self.actions(frame, [(f"{angle}°", lambda a=angle: self.move_angle(a), BORDER)
                             for angle in (0, 30, 60, 90, 120, 150, 180)])
        self.actions(frame, [(f"{offset:+}°", lambda v=offset: self.adjust_angle(v), BORDER)
                             for offset in (-10, -1, 1, 10)])
        frame = self.card(panel, "Sorting presets • Day 10")
        self.field(frame, "fertile_angle", "Fertile → incubation tray (°)", "30")
        self.actions(frame, [
            ("Save fertile", lambda: self.number_command("servo", "SET_FERTILE", "fertile_angle", 0, 180), BORDER),
            ("Test fertile", lambda: self.send("servo", "SORT:FERTILE"), GREEN)])
        self.field(frame, "infertile_angle", "Infertile → Penoy (°)", "90")
        self.actions(frame, [
            ("Save infertile", lambda: self.number_command("servo", "SET_INFERTILE", "infertile_angle", 0, 180), BORDER),
            ("Test infertile", lambda: self.send("servo", "SORT:INFERTILE"), RED)])
        self.actions(frame, [("Reset / neutral", lambda: self.send("servo", "RESET"), BORDER),
                             ("Status", lambda: self.send("servo", "STATUS"), BORDER)])

    def select_angle(self, value):
        angle = round(float(value))
        self.selected.configure(text=f"Selected angle: {angle}°")
        if "angle" in self.entries:
            self.entries["angle"].delete(0, "end")
            self.entries["angle"].insert(0, str(angle))

    def move_angle(self, angle):
        self.slider.set(angle)
        self.select_angle(angle)
        self.send("servo", f"SERVO:{angle}")

    def adjust_angle(self, offset):
        angle = integer(self.entries["angle"].get(), 0, 180, "Angle") + offset
        if not 0 <= angle <= 180:
            raise ValueError("Adjusted angle must be between 0 and 180°.")
        self.move_angle(angle)

    def refresh_ports(self):
        # Enumeration is also kept off the UI thread on slow USB hosts.
        import threading

        def discover():
            try:
                names = [port.device for port in list_ports.comports()]
                self.events.put(("ports", names))
            except Exception as exc:
                self.events.put(("port_error", str(exc)))

        threading.Thread(target=discover, daemon=True, name="OvaLens-PortDiscovery").start()

    def toggle_connection(self, role):
        link = self.rig.links[role]
        if link.active:
            link.disconnect()
            self.connection_states[role] = "DISCONNECTING"
            self.connection_widgets[role][4].configure(text="DISCONNECTING…", text_color=MUTED)
            return
        port, _, mock, _, _ = self.connection_widgets[role]
        self.rig.connect(role, "" if port.get() == "No ports" else port.get(), mock.get())

    def connect_all(self):
        for role in self.rig.links:
            self.perform(lambda r=role: self.toggle_connection(r))

    def status_all(self):
        failures = []
        for role in self.rig.links:
            try:
                self.send(role, "STATUS")
            except ValueError as exc:
                failures.append(str(exc))
        if failures:
            raise ValueError(" ".join(failures))

    def add_log(self, role, kind, value):
        stamp = datetime.now().strftime("%H:%M:%S")
        self.logs.append(f"{stamp}  {role.upper():5}  {kind.upper():10}  {value}")
        self._log_dirty = True

    def clear_log(self):
        self.logs.clear()
        self._log_dirty = True

    def receive(self, role, line):
        parts = line.split(":")
        if parts[0] == "OK" and len(parts) >= 3:
            parts = parts[1:]
        if len(parts) >= 2 and (role, parts[0]) in self.telemetry:
            label, caption = self.telemetry[(role, parts[0])]
            value = ":".join(parts[1:])
            label.configure(text=f"{caption}: {value.replace('_', ' ')}")
            if parts[0] == "STATE":
                self.states[role] = value
            elif role == "servo" and parts[0] == "ANGLE":
                self.states[role] = "RESPONDING"
                state_label, caption = self.telemetry[(role, "STATE")]
                state_label.configure(text=f"{caption}: RESPONDING")
        elif role == "egg" and len(parts) == 2 and parts[0] in self.egg_flags:
            if parts[1] in {"0", "1"}:
                self.egg_flags[parts[0]] = parts[1]
                state = egg_status(self.egg_flags["BUSY"], self.egg_flags["AUTO"])
                self.states[role] = state
                state_label, caption = self.telemetry[(role, "STATE")]
                state_label.configure(text=f"{caption}: {state.replace('_', ' ')}")
        elif line == "OK:HOME_SET":
            label, caption = self.telemetry[(role, "POSITION")]
            label.configure(text=f"{caption}: 0")
        if line.startswith(("ERROR:", "NACK:")):
            self.notice.configure(text=f"{role.title()} board: {line}", text_color="#FCA5A5")

    def poll(self):
        for _ in range(100):
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            if isinstance(event, tuple):
                kind, value = event
                if kind == "ports":
                    used = set()
                    for role, widgets in self.connection_widgets.items():
                        port = widgets[0]
                        selected = choose_port(value, port.get(), self.preferred_ports[role], used)
                        choices = list(value)
                        if selected not in choices:
                            choices.append(selected)
                        port.configure(values=choices)
                        port.set(selected)
                        used.add(selected)
                else:
                    self.notice.configure(text=f"Port discovery failed: {value}", text_color="#FCA5A5")
                continue
            self.add_log(event.role, event.kind, event.value)
            if event.kind == "connection":
                self.connection_states[event.role] = event.value
                _, button, _, _, status = self.connection_widgets[event.role]
                status.configure(text=event.value, text_color=GREEN if "CONNECTED " in event.value else MUTED)
                button.configure(text="Connect" if event.value == "DISCONNECTED" else "Disconnect")
                if event.value == "DISCONNECTED":
                    self.states[event.role] = "OFFLINE"
                    if event.role == "egg":
                        self.egg_flags = {"BUSY": None, "AUTO": None}
                    for (role, field), (label, caption) in self.telemetry.items():
                        if role == event.role:
                            label.configure(text=f"{caption}: {'OFFLINE' if field == 'STATE' else '—'}")
                elif event.value.startswith("CONNECTED "):
                    label, caption = self.telemetry[(event.role, "STATE")]
                    label.configure(text=f"{caption}: Awaiting board status")
                    self.notice.configure(text="Hardware connected. Use Status: both boards to check replies.",
                                          text_color=MUTED)
                elif event.value == "SIMULATED":
                    self.notice.configure(text="Simulation mode: commands do not move physical hardware.",
                                          text_color=MUTED)
            elif event.kind == "rx":
                self.receive(event.role, event.value)
            elif event.kind == "error":
                self.notice.configure(text=f"{event.role.title()} controller: {event.value}",
                                       text_color="#FCA5A5")
        # Render bounded logs at 10 Hz while control/telemetry polling stays at 16 ms.
        if self._log_dirty and time.monotonic() - self._last_log_render >= 0.1:
            self.log_box.configure(state="normal")
            self.log_box.delete("1.0", "end")
            self.log_box.insert("end", "\n".join(self.logs))
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
            self._log_dirty = False
            self._last_log_render = time.monotonic()
        for role, link in self.rig.links.items():
            port, _, _, switch, _ = self.connection_widgets[role]
            port.configure(state="disabled" if link.active else "readonly")
            switch.configure(state="disabled" if link.active else "normal")
        ready = all(link.ready for link in self.rig.links.values())
        same_mode = len({link.simulated for link in self.rig.links.values()}) == 1
        self.start_button.configure(state="normal" if ready and same_mode else "disabled")
        if self.closing and not any(link.active for link in self.rig.links.values()):
            self.destroy()
            return
        self.after(16, self.poll)

    def close(self):
        if self.closing:
            return
        self.closing = True
        self.notice.configure(text="Closing controller connections…", text_color=MUTED)
        self.rig.close()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="OvaLens egg + servo hardware prototype")
    parser.add_argument("--simulate", action="store_true", help="Preselect simulation for both boards")
    parser.add_argument("--egg-port", default="", help="Egg controller port, e.g. COM5")
    parser.add_argument("--servo-port", default="", help="Servo controller port, e.g. COM7")
    parser.add_argument("--connect", action="store_true", help="Connect both selected boards at startup; queries STATUS only")
    args = parser.parse_args(argv)
    if args.connect and not args.simulate and (not args.egg_port or not args.servo_port):
        parser.error("--connect requires --egg-port and --servo-port in hardware mode")
    if args.egg_port and args.servo_port and args.egg_port.casefold() == args.servo_port.casefold():
        parser.error("The egg and servo controllers require different ports")
    return args


def main():
    args = parse_args()
    ctk.set_appearance_mode("dark")
    app = PrototypeApp(simulate=args.simulate, egg_port=args.egg_port,
                       servo_port=args.servo_port, connect=args.connect)
    app.mainloop()


if __name__ == "__main__":
    main()
