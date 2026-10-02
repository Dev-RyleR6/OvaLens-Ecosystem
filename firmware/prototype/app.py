"""OvaLens mechanical edge prototype. Run: python -m firmware.prototype.app."""

import argparse
from collections import deque
from datetime import datetime
import queue
import tkinter as tk
import time

import customtkinter as ctk
import cv2
from PIL import Image, ImageTk
from serial.tools import list_ports

from .controller import EventInbox, OpticalCounter, PrototypeRig, choose_port, egg_status, integer
from .vision import VisionEvent, VisionWorker
from .cycle import AutomaticCycle, CycleSettings


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
        self.geometry("1280x880")
        self.minsize(1100, 800)
        self.configure(fg_color=BG)
        self.events = EventInbox()
        self.rig = PrototypeRig(self.events)
        self.vision = VisionWorker(self.events)
        self.cycle = AutomaticCycle(self.rig, self.vision)
        self._cycle_display = None
        self._manual_buttons = []
        self.optical = OpticalCounter()
        self._widget_cache = {}
        self._pending_log = deque(maxlen=500)
        self._video_number = -1
        self._video_image = None
        self._last_video_render = 0.0
        self._last_metrics_render = 0.0
        self._discovery_active = False
        self._closing_at = None
        self._vision_error = False
        self._dropped_seen = 0
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
        self.label(header, "OVALENS  /  OPERATOR WORKSPACE", 22).pack(
            anchor="w", padx=24, pady=(10, 0))
        self.label(header, "Foundation University  •  Day 10 candling & hardware integration", 12).pack(
            anchor="w", padx=24, pady=(0, 10))

    def _build_connections(self, simulate):
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.grid(row=1, column=0, sticky="ew", padx=16, pady=8)
        row.grid_columnconfigure((0, 1), weight=1, uniform="connections")
        for column, role in enumerate(("egg", "servo")):
            frame = ctk.CTkFrame(row, fg_color=CARD, border_width=1, border_color=BORDER)
            frame.grid(row=0, column=column, sticky="ew", padx=6)
            frame.grid_columnconfigure(0, weight=1)
            title = "Stepper" if role == "egg" else "Servo"
            self.label(frame, f"{title} ESP32  /  115200 baud", 16).grid(
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
            if simulate:
                switch.grid(row=2, column=0, columnspan=3, sticky="w", padx=12, pady=8)
            else:
                self.label(frame, "Hardware mode", color=MUTED).grid(
                    row=2, column=0, columnspan=3, sticky="w", padx=12, pady=4)
            status = self.label(frame, "DISCONNECTED", color=MUTED)
            status.grid(row=3, column=0, columnspan=3, sticky="w", padx=12, pady=(0, 8))
            self.connection_widgets[role] = (port, connect, mock, switch, status)

    def _build_shared_controls(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 8))
        self.start_button = self.button(frame, "START AUTO CYCLE", self.start_cycle,
                                         color=MAROON, width=190)
        self.start_button.pack(side="left", padx=(0, 8))
        self.button(frame, "STOP & HOME + NEUTRAL", self.stop_cycle, color=RED,
                    width=240).pack(side="left", padx=8)
        self.button(frame, "Status: both boards", self.status_all, width=160).pack(
            side="left", padx=8)

    def _build_workspace(self):
        tabs = ctk.CTkTabview(self, fg_color=BG, segmented_button_selected_color=MAROON,
                             command=self.tab_changed)
        self.tabs = tabs
        tabs.grid(row=3, column=0, sticky="nsew", padx=16, pady=(0, 6))
        operator = tabs.add("Operate & detect")
        controls = tabs.add("Calibration")
        monitor = tabs.add("Serial monitor")
        self._build_operator(operator)
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
        self.label(self, "Auto cycle: move → detect → move → servo → clear → repeat. "
                   "STOP returns home; use a physical E-stop to cut power.",
                   color=MUTED, wraplength=950).grid(row=5, column=0, sticky="ew", padx=24, pady=(0, 12))

    def configure_changed(self, widget, **values):
        cache = self._widget_cache.setdefault(widget, {})
        changed = {key: value for key, value in values.items() if cache.get(key) != value}
        if changed:
            widget.configure(**changed)
            cache.update(changed)

    def _build_operator(self, parent):
        parent.grid_columnconfigure(0, weight=3, uniform="operator")
        parent.grid_columnconfigure(1, weight=2, uniform="operator")
        parent.grid_rowconfigure(0, weight=1)
        left = ctk.CTkFrame(parent, fg_color=CARD)
        left.grid(row=0, column=0, sticky="nsew", padx=(4, 10), pady=4)
        self.label(left, "Live candling camera", 18).pack(anchor="w", padx=16, pady=(12, 4))
        row = ctk.CTkFrame(left, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=6)
        self.label(row, "Camera", color=MUTED).pack(side="left", padx=(0, 6))
        entry = ctk.CTkEntry(row, width=55)
        entry.insert(0, "0")
        entry.pack(side="left")
        self.entries["camera_index"] = entry
        self.camera_button = self.button(row, "Start camera", self.toggle_camera, MAROON, width=130)
        self.camera_button.pack(side="left", padx=10)
        self.camera_status = self.label(row, "Camera stopped", color=MUTED)
        self.camera_status.pack(side="left", padx=4)
        self.video = tk.Canvas(left, bg="#020617", highlightthickness=0, height=180)
        self.video.pack(fill="both", expand=True, padx=16, pady=8)
        self.video.create_text(10, 10, anchor="nw", fill=MUTED,
                               text="Start the real camera to detect eggs.", tags="placeholder")
        self.video_item = self.video.create_image(0, 0, anchor="nw")
        self.detection_label = self.label(left, "NO CAMERA", 24)
        self.detection_label.pack(anchor="w", padx=16, pady=(4, 0))
        self.detection_metrics = self.label(left, "Confidence —  •  Inference —  •  Camera — FPS", color=MUTED)
        self.detection_metrics.pack(anchor="w", padx=16, pady=4)
        self.detection_counts = self.label(left, "Fertile 0  |  Infertile 0  |  Review 0  |  Optical triggers 0", color=MUTED)
        self.detection_counts.pack(anchor="w", padx=16, pady=(0, 12))
        right = ctk.CTkScrollableFrame(parent, fg_color=BG)
        right.grid(row=0, column=1, sticky="nsew", padx=4, pady=4)
        cycle_card = self.card(right, "Automatic integration cycle")
        self.cycle_status = self.label(cycle_card, "Ready · 0 cycles completed", color=MUTED,
                                       wraplength=360, anchor="w", justify="left")
        self.cycle_status.pack(fill="x", padx=16, pady=(0, 8))
        self.label(cycle_card, "Defaults: move 1000 → detect → resume 1000. Servo activates halfway. "
                   "Travel and gate mode are editable in Calibration.",
                   color=MUTED, wraplength=360, justify="left").pack(anchor="w", padx=16, pady=(0, 10))
        board_status = ctk.CTkFrame(right, fg_color="transparent")
        board_status.pack(fill="x")
        egg_status_panel = ctk.CTkFrame(board_status, fg_color="transparent")
        egg_status_panel.pack(side="left", fill="both", expand=True)
        servo_status_panel = ctk.CTkFrame(board_status, fg_color="transparent")
        servo_status_panel.pack(side="left", fill="both", expand=True)
        self.telemetry_card(egg_status_panel, "egg", "Stepper controller", [
            ("STATE", "State"), ("POSITION", "Position (steps)")])
        self.telemetry_card(servo_status_panel, "servo", "Servo controller", [
            ("STATE", "State"), ("ANGLE", "Angle (°)")])
        frame = self.card(right, "Quick controls")
        self.actions(frame, [("Home conveyor", lambda: self.send("egg", "HOME"), BORDER),
                             ("Neutral servo", lambda: self.send("servo", "RESET"), BORDER)])
        self.actions(frame, [("Jog −10", lambda: self.send("egg", "JOG:-10"), BORDER),
                             ("Jog +10", lambda: self.send("egg", "JOG:10"), BORDER)])
        self.actions(frame, [("Test fertile", lambda: self.send("servo", "SORT:FERTILE"), GREEN),
                             ("Test infertile", lambda: self.send("servo", "SORT:INFERTILE"), RED)])
        self.sort_scan_button = self.button(frame, "Sort recorded egg", self.sort_recorded, MAROON)
        self.sort_scan_button.pack(fill="x", padx=16, pady=8)
        self.scan_status = self.label(frame, "No recorded egg", color=MUTED, wraplength=360)
        self.scan_status.pack(anchor="w", padx=16, pady=(0, 10))

    def toggle_camera(self):
        if self.vision.active:
            if self.cycle.active:
                self.stop_cycle()
            self.vision.stop()
        else:
            index = integer(self.entries["camera_index"].get(), 0, 9, "Camera index")
            self._vision_error = False
            self.configure_changed(self.detection_label, text="LOADING MODEL", text_color=MUTED)
            self.vision.start(index)
            self._video_number = -1

    def start_cycle(self):
        if self.closing:
            return
        values = {key: integer(self.entries[f"cycle_{key}"].get(), low, high, caption)
                  for key, caption, _, low, high in self.cycle_fields}
        values["fertile_angle"] = integer(self.entries["fertile_angle"].get(), 0, 180, "Fertile angle")
        values["infertile_angle"] = integer(self.entries["infertile_angle"].get(), 0, 180, "Infertile angle")
        settings = CycleSettings(**values, mode=self.cycle_mode.get()).validate()
        if not all(link.ready and not link.simulated for link in self.rig.links.values()):
            raise ValueError("Connect both real controllers before starting the cycle.")
        if not self.vision.active:
            self.toggle_camera()
        self.cycle.start(settings)
        self.notice.configure(text="Automatic cycle started. Distances use motor steps; no home return between eggs.",
                              text_color=MUTED)

    def stop_cycle(self):
        self.cycle.stop()

    def require_manual(self):
        if self.cycle.active:
            raise ValueError("Stop the automatic cycle before using manual motion or calibration controls.")

    def sort_recorded(self):
        self.require_manual()
        if not all(link.ready and not link.simulated for link in self.rig.links.values()):
            raise ValueError("Connect both real controllers before sorting a recorded egg.")
        scan = self.vision.routable_scan()
        self.send("servo", f"SORT:{scan['final_class']}")
        self.vision.mark_routed(scan["scan_id"])
        self.scan_status.configure(text=f"Sort requested: {scan['final_class']} • scan {scan['sequence_number']}")

    def tab_changed(self):
        if self.tabs.get() == "Serial monitor":
            self.log_box.configure(state="normal")
            self.log_box.delete("1.0", "end")
            self.log_box.insert("end", "\n".join(self.logs) + ("\n" if self.logs else ""))
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
            self._pending_log.clear()
            self._log_dirty = False

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
            button = self.button(row, text, callback, color=color, width=50)
            button.grid(row=0, column=column, sticky="ew", padx=4)
            if not text.lower().startswith(("stop", "status")):
                self._manual_buttons.append(button)

    def send(self, role, command):
        if command != "STATUS":
            self.require_manual()
        self.rig.links[role].send(command)

    def number_command(self, role, prefix, key, low, high):
        value = integer(self.entries[key].get(), low, high, key.replace("_", " ").title())
        self.send(role, f"{prefix}:{value}")

    def _build_egg(self, panel):
        frame = self.card(panel, "Automatic cycle settings · steps")
        self.cycle_mode = ctk.CTkOptionMenu(frame, values=["Detect & block", "Classify & sort"],
                                           fg_color=MAROON, button_color=MAROON)
        self.cycle_mode.pack(fill="x", padx=16, pady=8)
        self.cycle_fields = [
            ("camera_steps", "Move to camera (steps)", "1000", 1, 100000),
            ("resume_steps", "Total travel after detection (steps)", "1000", 2, 100000),
            ("step_delay", "Step delay (µs)", "1800", 200, 5000),
            ("neutral_angle", "Neutral angle (°)", "90", 0, 180),
            ("block_angle", "Detection blocking angle (°)", "30", 0, 180),
            ("settle_ms", "Camera settling (ms)", "300", 0, 5000),
            ("servo_settle_ms", "Servo settling (ms)", "300", 0, 5000),
            ("detection_timeout", "Wait for egg (seconds)", "15", 1, 120),
        ]
        for key, caption, initial, _, _ in self.cycle_fields:
            self.field(frame, f"cycle_{key}", caption, initial)
        self.label(frame, "Servo triggers at half the resumed travel (500 of 1000 steps by default). "
                   "Classification uses the fertile/infertile angles in the servo panel. "
                   "Start snapshots these settings. Finite moves stop at each station.",
                   color=MUTED, wraplength=420, justify="left").pack(anchor="w", padx=16, pady=10)
        self.telemetry_card(panel, "egg", "Reported conveyor settings", [
            ("CHAMBER", "Chamber (steps)"), ("OUTPUT", "Output (steps)"), ("SPEED", "Step delay (µs)")])
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
                             ("Stop & home", self.stop_cycle, RED)])
        self.label(frame, "Return HOME before repeating a distance test.", color=MUTED).pack(
            anchor="w", padx=16, pady=(0, 10))

    def motion_test(self):
        self.require_manual()
        # Validate both before enqueueing either command.
        distance = integer(self.entries["test_distance"].get(), 1, 100000, "Distance")
        speed = integer(self.entries["test_delay"].get(), 200, 5000, "Step delay")
        self.rig.links["egg"].send_many([f"SPEED:{speed}", f"TEST:{distance}"])

    def _build_servo(self, panel):
        self.telemetry_card(panel, "servo", "Reported sorting presets", [
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

        if self._discovery_active:
            return
        self._discovery_active = True

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
            if self.cycle.active:
                self.perform(self.stop_cycle)
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
        line = f"{stamp}  {role.upper():5}  {kind.upper():10}  {value}"
        self.logs.append(line)
        self._pending_log.append(line)
        self._log_dirty = True

    def clear_log(self):
        self.logs.clear()
        self._pending_log.clear()
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")
        self._log_dirty = False

    def receive(self, role, line):
        if role == "egg":
            self.optical.feed(line)
        parts = line.split(":")
        if parts[0] == "OK" and len(parts) >= 3:
            parts = parts[1:]
        if len(parts) >= 2 and (role, parts[0]) in self.telemetry:
            label, caption = self.telemetry[(role, parts[0])]
            value = ":".join(parts[1:])
            self.configure_changed(label, text=f"{caption}: {value.replace('_', ' ')}")
            if parts[0] == "STATE":
                self.states[role] = value
            elif role == "servo" and parts[0] == "ANGLE":
                self.states[role] = "RESPONDING"
                state_label, caption = self.telemetry[(role, "STATE")]
                self.configure_changed(state_label, text=f"{caption}: RESPONDING")
        elif role == "egg" and len(parts) == 2 and parts[0] in self.egg_flags:
            if parts[1] in {"0", "1"}:
                self.egg_flags[parts[0]] = parts[1]
                state = egg_status(self.egg_flags["BUSY"], self.egg_flags["AUTO"])
                self.states[role] = state
                state_label, caption = self.telemetry[(role, "STATE")]
                self.configure_changed(state_label, text=f"{caption}: {state.replace('_', ' ')}")
        elif line == "OK:HOME_SET":
            label, caption = self.telemetry[(role, "POSITION")]
            self.configure_changed(label, text=f"{caption}: 0")
        if line.startswith(("ERROR:", "NACK:")):
            self.notice.configure(text=f"{role.title()} board: {line}", text_color="#FCA5A5")

    def poll(self):
        started = time.monotonic()
        processed = False
        for _ in range(200):
            if time.monotonic() - started >= 0.008:
                break
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            processed = True
            if isinstance(event, VisionEvent):
                self.add_log("VISION", event.kind, str(event.value))
                if event.kind == "status":
                    self.configure_changed(self.camera_status, text=str(event.value))
                    if event.value == "Camera stopped" and not self._vision_error:
                        self.configure_changed(self.detection_label, text="CAMERA STOPPED", text_color=MUTED)
                elif event.kind == "scan":
                    scan = event.value
                    text = f"Saved scan {scan['sequence_number']}: {scan['state'].replace('_', ' ')}"
                    self.configure_changed(self.scan_status, text=text)
                elif event.kind == "error":
                    if self.cycle.active:
                        self.cycle.fail(f"Detection: {event.value}")
                    self._vision_error = True
                    self.vision.stop()
                    self.notice.configure(text=f"Detection: {event.value}", text_color="#FCA5A5")
                    self.configure_changed(self.detection_label, text="MANUAL REVIEW", text_color="#FBBF24")
                continue
            if isinstance(event, tuple):
                kind, value = event
                self._discovery_active = False
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
            self.cycle.event(event)
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
                            self.configure_changed(label, text=f"{caption}: {'OFFLINE' if field == 'STATE' else '—'}")
                elif event.value.startswith("CONNECTED "):
                    label, caption = self.telemetry[(event.role, "STATE")]
                    self.configure_changed(label, text=f"{caption}: Awaiting board status")
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
        if self.events.dropped > self._dropped_seen:
            if self.cycle.active:
                self.cycle.fail("Event backlog overflow · inspect manually")
            self._dropped_seen = self.events.dropped
            self._vision_error = True
            self.vision.stop()
            self.notice.configure(text="Event backlog overflow. Detection paused; inspect the current egg.",
                                  text_color="#FCA5A5")
            self.configure_changed(self.detection_label, text="MANUAL REVIEW", text_color="#FBBF24")
        # Append logs only when visible; retain a bounded history without repeated full redraws.
        if (self._log_dirty and self.tabs.get() == "Serial monitor" and
                time.monotonic() - self._last_log_render >= 0.1):
            self.log_box.configure(state="normal")
            self.log_box.insert("end", "\n".join(self._pending_log) + "\n")
            self._pending_log.clear()
            lines = int(self.log_box.index("end-1c").split(".")[0])
            if lines > 501:
                self.log_box.delete("1.0", f"{lines - 500}.0")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
            self._log_dirty = False
            self._last_log_render = time.monotonic()
        for role, link in self.rig.links.items():
            port, _, _, switch, _ = self.connection_widgets[role]
            self.configure_changed(port, state="disabled" if link.active else "readonly")
            self.configure_changed(switch, state="disabled" if link.active else "normal")
        if not self.closing:
            self.cycle.tick()
        display = (self.cycle.state, self.cycle.message, self.cycle.completed)
        if display != self._cycle_display:
            self._cycle_display = display
            self.configure_changed(self.cycle_status,
                                   text=f"{self.cycle.state.replace('_', ' ')} · {self.cycle.completed} cycles completed\n{self.cycle.message}",
                                   text_color="#FBBF24" if self.cycle.state == "MANUAL_REVIEW" else MUTED)
            self.add_log("CYCLE", self.cycle.state, self.cycle.message)
            if self.cycle.state == "MANUAL_REVIEW":
                self.notice.configure(text=self.cycle.message, text_color="#FCA5A5")
                self.configure_changed(self.detection_label, text="MANUAL REVIEW", text_color="#FBBF24")
            elif self.cycle.state == "INSPECTING":
                self.configure_changed(self.detection_label, text="WAITING FOR EGG", text_color=MUTED)
            elif self.cycle.active:
                self.configure_changed(self.detection_label, text="TRAVEL · DETECTION PAUSED", text_color=MUTED)
            elif self.cycle.state == "STOPPED":
                self.configure_changed(self.detection_label, text="CYCLE STOPPED", text_color=MUTED)
        ready = all(link.ready for link in self.rig.links.values())
        same_mode = len({link.simulated for link in self.rig.links.values()}) == 1
        hardware = ready and all(not link.simulated for link in self.rig.links.values())
        self.configure_changed(self.start_button, state="normal" if hardware and not self.cycle.active and not self.closing else "disabled")
        self.configure_changed(self.cycle_mode, state="disabled" if self.cycle.active else "normal")
        for button in self._manual_buttons:
            self.configure_changed(button, state="disabled" if self.cycle.active or self.closing else "normal")
        self.configure_changed(self.slider, state="disabled" if self.cycle.active or self.closing else "normal")
        for key, *_ in self.cycle_fields:
            self.configure_changed(self.entries[f"cycle_{key}"], state="disabled" if self.cycle.active else "normal")
        self.configure_changed(self.camera_button, text="Stop camera" if self.vision.active else "Start camera",
                               state="disabled" if self.closing else "normal")
        self.configure_changed(self.entries["camera_index"], state="disabled" if self.vision.active else "normal")
        routable = False
        if ready and same_mode and not self.rig.links["servo"].simulated:
            try:
                self.vision.routable_scan()
                routable = True
            except ValueError:
                pass
        self.configure_changed(self.sort_scan_button, state="normal" if routable and not self.cycle.active and not self.closing else "disabled")
        self.render_vision()
        stopped = not any(link.active for link in self.rig.links.values()) and not self.vision.active
        if self.closing and (stopped or time.monotonic() - self._closing_at > 4):
            self.destroy()
            return
        self.after(16 if processed or self.vision.active or self.closing else 50, self.poll)

    def render_vision(self):
        now = time.monotonic()
        latest = self.vision.snapshot()
        if now - self._last_metrics_render >= 0.25:
            self._last_metrics_render = now
            counts = self.vision.counts
            text = (f"Fertile {counts['FERTILE']}  |  Infertile {counts['INFERTILE']}  |  "
                    f"Review {counts['MANUAL_REVIEW']}  |  Optical triggers {self.optical.count}")
            self.configure_changed(self.detection_counts, text=text)
            if latest and not self._vision_error and now - latest["timestamp"] < 0.5:
                state = latest["state"]
                color = {"FERTILE": GREEN, "INFERTILE": RED, "MANUAL_REVIEW": "#FBBF24"}.get(state, MUTED)
                self.configure_changed(self.detection_label, text=state.replace("_", " "), text_color=color)
                confidence = f"{latest['candidate']['confidence']:.0%}" if latest["candidate"] else "—"
                text = (f"Confidence {confidence}  •  Inference {latest['inference_ms']} ms  •  "
                        f"Camera {latest['fps']:.0f} FPS")
                self.configure_changed(self.detection_metrics, text=text)
            elif latest and not self._vision_error:
                self.configure_changed(self.detection_label, text="WAITING FOR DETECTION", text_color=MUTED)
        if self.tabs.get() != "Operate & detect" or now - self._last_video_render < 1 / 30:
            return
        self._last_video_render = now
        camera = self.vision.camera
        if camera is None:
            return
        number, stamp, frame, _ = camera.snapshot()
        if frame is None or now - stamp > 0.5:
            self.video.itemconfigure(self.video_item, image="")
            self.video.delete("overlay")
            self.video.itemconfigure("placeholder", text="No live camera frame. Check the camera connection.")
            return
        if number == self._video_number:
            return
        self._video_number = number
        width, height = max(1, self.video.winfo_width()), max(1, self.video.winfo_height())
        scale = min(width / frame.shape[1], height / frame.shape[0])
        image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).resize(
            (max(1, round(frame.shape[1] * scale)), max(1, round(frame.shape[0] * scale))), Image.Resampling.BILINEAR)
        self._video_image = ImageTk.PhotoImage(image)
        ox, oy = (width - image.width) // 2, (height - image.height) // 2
        self.video.coords(self.video_item, ox, oy)
        self.video.itemconfigure(self.video_item, image=self._video_image)
        self.video.itemconfigure("placeholder", text="")
        self.video.delete("overlay")
        if latest and latest["candidate"] and now - latest["timestamp"] < 0.3:
            x1, y1, x2, y2 = latest["candidate"]["pixels"]
            self.video.create_rectangle(ox+x1*scale, oy+y1*scale, ox+x2*scale, oy+y2*scale,
                                        outline="#FBBF24" if latest["state"] == "MANUAL_REVIEW" else "#FFFFFF",
                                        width=2, tags="overlay")

    def close(self):
        if self.closing:
            return
        self.closing = True
        self._closing_at = time.monotonic()
        self.cycle.state = "STOPPED"
        self.notice.configure(text="Closing controller connections…", text_color=MUTED)
        self.rig.close()
        self.vision.stop()


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
