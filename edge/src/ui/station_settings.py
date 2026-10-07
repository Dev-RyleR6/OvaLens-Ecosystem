"""Idle-only station settings, applied through the operation worker."""
import customtkinter as ctk
from serial.tools import list_ports
from ..core.settings import EdgeSettings
from .theme import FUTheme


class StationSettingsWindow(ctk.CTkToplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app, self.station = app, app.station
        self.title("OvaLens station settings")
        self.geometry("920x740")
        self.minsize(800, 640)
        self.configure(fg_color=FUTheme.BG_LIGHT)
        self.transient(app)
        self.grab_set()
        self.pending = False
        self.entries = {}
        self.buttons = []
        ctk.CTkLabel(self, text="Station settings", font=(FUTheme.FONT_FAMILY, 22, "bold")).pack(anchor="w", padx=24, pady=(18, 4))
        ctk.CTkLabel(self, text="Tune while idle. Readback confirms a driver value; position and passage remain estimated.", wraplength=850).pack(anchor="w", padx=24)
        tabs = ctk.CTkTabview(self, fg_color=FUTheme.PANEL_LIGHT)
        tabs.pack(fill="both", expand=True, padx=20, pady=12)
        for name in ("Connections", "Camera", "Detection", "Calibration"):
            tabs.add(name)
        self.notice = ctk.CTkLabel(self, text=self.station.settings_error or "Apply affects this run. Save as Default also persists settings.",
                                  wraplength=850, justify="left")
        self.notice.pack(fill="x", padx=24, pady=6)
        self.report = ctk.CTkTextbox(tabs.tab("Camera"), height=150)
        self.confirm_camera = ctk.BooleanVar(value=False)
        self.inspected = ctk.BooleanVar(value=False)

        connection = tabs.tab("Connections")
        self._entry(connection, "conveyor_port", "Stepper / IR ESP32 serial port", "")
        self._entry(connection, "servo_port", "Servo ESP32 serial port", "")
        self.port_label = ctk.CTkLabel(connection, text="Refresh to list connected serial ports", wraplength=820, justify="left")
        self.port_label.pack(anchor="w", padx=8, pady=10)
        self._button(connection, "Refresh ports", lambda: self._job(lambda: "\n".join(f"{p.device}: {p.description}" for p in list_ports.comports()) or "No ports found", self._ports))
        self._button(connection, "Connect and identify boards", lambda: self._job(self.station.connect))
        self._button(connection, "Acknowledge inspected board faults", self._acknowledge)
        ctk.CTkLabel(connection, text="Connect after applying the selected ports. Acknowledgement clears faults; it does not establish conveyor position.", wraplength=820).pack(anchor="w", padx=8, pady=12)

        camera = ctk.CTkScrollableFrame(tabs.tab("Camera"), height=200)
        camera.pack(fill="both", expand=True)
        camera_labels = {"index": "Camera index", "width": "Width (pixels)", "height": "Height (pixels)", "fps": "Requested FPS",
                         "auto_exposure": "Auto exposure (native driver value)", "autofocus": "Autofocus (0 off / 1 on)",
                         "auto_white_balance": "Auto white balance (0 off / 1 on)", "exposure": "Exposure (native driver units)",
                         "gain": "Gain", "focus": "Focus", "white_balance": "White balance temperature"}
        for name in camera_labels:
            self._entry(camera, "camera." + name, camera_labels[name], "")
        ctk.CTkLabel(camera, text="Blank optional fields leave the driver unchanged. DirectShow commonly uses 0.25 for manual exposure and 0.75 for automatic; verify the readback on your camera.", wraplength=760, justify="left").pack(anchor="w", padx=8, pady=10)
        ctk.CTkCheckBox(camera, text="Confirm selected camera / changed device identity", variable=self.confirm_camera).pack(anchor="w", padx=8, pady=6)
        self.report.pack(fill="x", pady=(8, 0))
        self.report.insert("1.0", "No camera property report yet. Apply settings to start idle preview and inspect readback.")
        self.report.configure(state="disabled")

        detection = tabs.tab("Detection")
        for name, label in (("confidence", "Detection confidence (0.01–0.99)"), ("iou", "NMS IoU (0.01–0.99)"),
                            ("sort_confidence", "Automatic-sort confidence (0.75–0.99)")):
            self._entry(detection, "detection." + name, label, "")
        ctk.CTkLabel(detection, text="Sorting requires three agreeing fresh frames over at least 300 ms, within two seconds. Low confidence or conflicting evidence holds the conveyor for review.", wraplength=800, justify="left").pack(anchor="w", padx=8, pady=20)

        calibration = ctk.CTkScrollableFrame(tabs.tab("Calibration"))
        calibration.pack(fill="both", expand=True)
        labels = {"holder_steps": "Holder spacing (steps)", "sorter_steps": "Chamber to gate centre (steps)",
                  "gate_clearance_steps": "Gate approach / exit clearance (steps)", "direction": "Forward direction (-1 or 1)",
                  "speed_us": "STEP half-period (microseconds)", "ir_offset_steps": "IR trigger to stopped capture (steps)",
                  "position_tolerance_steps": "Chamber arrival tolerance (steps)", "settle_ms": "Capture settling time (ms)",
                  "passage_ms": "Gate passage wait (ms)", "neutral_angle": "Neutral servo angle", "fertile_angle": "Fertile angle",
                  "infertile_angle": "Infertile angle"}
        for name, label in labels.items():
            self._entry(calibration, "calibration." + name, label, "")
        self.jog = self._entry(calibration, "_jog", "Manual jog steps (signed, at most 100000)", "100")
        self._button(calibration, "Jog conveyor", self._jog)
        self._button(calibration, "Set aligned position as software home", lambda: self._job(lambda: self.station.command("CONVEYOR", "SETHOME")))
        for label, text in (("Test fertile route", "SORT:FERTILE"), ("Test infertile route", "SORT:INFERTILE"), ("Return servo to neutral", "RESET")):
            self._button(calibration, label, lambda text=text: self._job(lambda: self.station.command("SERVO", text)))
        ctk.CTkLabel(calibration, text="Validate with the next holder one pitch before the chamber and all downstream holders empty. Bench-test IR stopping and both gate directions first.", wraplength=760, justify="left").pack(anchor="w", padx=8, pady=8)
        ctk.CTkCheckBox(calibration, text="IR / gate bench-tested, geometry measured, holders aligned and cleared",
                        variable=self.inspected).pack(anchor="w", padx=8, pady=14)
        self._button(calibration, "Load calibration and validate inspected setup", self._validate)

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=24, pady=(6, 18))
        for label, command in (("Apply", lambda: self._apply(False)), ("Save as Default", lambda: self._apply(True)),
                               ("Restore Saved Defaults", self._restore)):
            self._button(actions, label, command, side="left")
        ctk.CTkButton(actions, text="STOP", fg_color="#DC2626", command=self.station.halt, width=75, height=40).pack(side="right", padx=4)
        self._fill(self.station.settings)
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _entry(self, parent, key, label, value):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(row, text=label, anchor="w", width=370).pack(side="left")
        entry = ctk.CTkEntry(row, height=34, width=200)
        entry.pack(side="left", padx=8)
        entry.insert(0, value)
        self.entries[key] = entry
        return entry

    def _button(self, parent, label, command, side=None):
        button = ctk.CTkButton(parent, text=label, command=command, height=38,
                              fg_color=FUTheme.PRIMARY_MAROON, hover_color=FUTheme.HOVER_MAROON)
        button.pack(side=side or "top", anchor="w", padx=6, pady=4)
        self.buttons.append(button)
        return button

    def _fill(self, settings):
        values = settings.snapshot()
        for key, entry in self.entries.items():
            if key.startswith("_"):
                continue
            parts = key.split(".")
            value = values[parts[0]][parts[1]] if len(parts) == 2 else values[key]
            entry.delete(0, "end")
            entry.insert(0, "" if value is None else str(value))

    def _values(self):
        values = self.station.settings.snapshot()
        for key, entry in self.entries.items():
            if key.startswith("_"):
                continue
            text = entry.get().strip()
            if "." not in key:
                values[key] = text
                continue
            group, name = key.split(".")
            if group == "detection":
                value = float(text)
            elif group == "camera" and name not in {"index", "width", "height", "fps"}:
                value = float(text) if text else None
            else:
                value = int(text)
            values[group][name] = value
        return EdgeSettings.from_dict(values)

    def _job(self, work, success=None):
        if self.pending:
            return
        self.pending = True
        for button in self.buttons:
            button.configure(state="disabled")
        for entry in self.entries.values():
            entry.configure(state="disabled")
        self.notice.configure(text="Working…")
        def finish(value, failed=False):
            self.pending = False
            if not self.winfo_exists():
                return
            for button in self.buttons:
                button.configure(state="normal")
            for entry in self.entries.values():
                entry.configure(state="normal")
            self.notice.configure(text=("Failed: " if failed else "") + str(value))
            if success and not failed:
                success(value)
        try:
            self.app._jobs.submit(work, lambda value: finish(value), lambda error: finish(error, True))
        except Exception as exc:
            finish(str(exc), True)

    def _apply(self, save):
        try:
            settings = self._values()
            confirm = self.confirm_camera.get()
        except ValueError as exc:
            self.notice.configure(text=str(exc))
            return
        self.app.realtime_detector.pause()
        def applied(report):
            self._fill(self.station.settings)
            self.confirm_camera.set(False)
            self.report.configure(state="normal")
            self.report.delete("1.0", "end")
            self.report.insert("1.0", "\n".join(f"{name}: requested {v['requested']}, readback {v['actual']} — {v['status']}" for name, v in report["properties"].items()))
            self.report.configure(state="disabled")
            self.notice.configure(text="Defaults saved." if save else "Applied for this run. Revalidate calibration before sorting.")
            self.app.realtime_detector.resume()
        self._job(lambda: self.station.apply(settings, save, confirm), applied)

    def _restore(self):
        self._job(self.station.store.load, lambda value: (self._fill(value), self.notice.configure(text="Saved defaults loaded into the form. Apply to use them.")))

    def _ports(self, value):
        self.port_label.configure(text=value)

    def _acknowledge(self):
        def work():
            self.station.command("CONVEYOR", "ACK_FAULT")
            self.station.command("SERVO", "ACK_FAULT")
            return "Faults acknowledged. Align the next holder and establish software home."
        self._job(work)

    def _jog(self):
        try:
            steps = int(self.jog.get())
            if steps == 0 or abs(steps) > 100000:
                raise ValueError("Jog must be nonzero and within ±100000 steps")
        except ValueError as exc:
            self.notice.configure(text=str(exc))
            return
        self._job(lambda: self.station.command("CONVEYOR", f"JOG:{steps}", max(5, abs(steps) * .01 + 2)))

    def _validate(self):
        inspected = self.inspected.get()
        self._job(lambda: self.station.validate_calibration(inspected))

    def _close(self):
        if self.pending:
            self.notice.configure(text="Wait for the current operation or use STOP.")
            return
        self.app.realtime_detector.resume()
        self.destroy()
