"""Idle-only station settings, applied through the operation worker."""
import customtkinter as ctk
from serial.tools import list_ports
from ..core.settings import EdgeSettings
from .theme import FUTheme


class StationSettingsWindow(ctk.CTkToplevel):
    PROFILES = {"Three-board candling rig": "three_v3", "Two-board indexed rig": "dual_v2"}
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
        ctk.CTkLabel(self, font=(FUTheme.FONT_FAMILY, 14), text="Tune while idle. Readback confirms a driver value; position and passage remain estimated.", wraplength=850).pack(anchor="w", padx=24)
        tabs = ctk.CTkTabview(self, fg_color=FUTheme.PANEL_LIGHT,
                            segmented_button_selected_color=FUTheme.PRIMARY_MAROON,
                            segmented_button_selected_hover_color=FUTheme.HOVER_MAROON,
                            text_color=FUTheme.TEXT_PRIMARY)
        tabs._segmented_button.configure(font=(FUTheme.FONT_FAMILY, 14, "bold"))
        tabs.pack(fill="both", expand=True, padx=20, pady=12)
        for name in ("Connections", "Camera", "Detection", "Calibration"):
            tabs.add(name)
        recovery = getattr(self.station, "recovery", None)
        recovery_notice = "Interrupted cycle found. Inspect and reconcile physical eggs before acknowledging faults or validating." if recovery and recovery.get("state") not in {"COMPLETE", "CLEARED"} else ""
        self.notice = ctk.CTkLabel(self, font=(FUTheme.FONT_FAMILY, 14), text=self.station.settings_error or recovery_notice or "Apply affects this run. Save as Default also persists settings.",
                                  wraplength=850, justify="left")
        self.notice.pack(fill="x", padx=24, pady=6)
        self.report = ctk.CTkTextbox(tabs.tab("Camera"), height=150,
                                    font=(FUTheme.FONT_FAMILY, 13),
                                    fg_color=FUTheme.BG_LIGHT, text_color=FUTheme.TEXT_SECONDARY)
        self.confirm_camera = ctk.BooleanVar(value=False)
        self.inspected = ctk.BooleanVar(value=False)

        connection = ctk.CTkScrollableFrame(tabs.tab("Connections"))
        connection.pack(fill="both", expand=True)
        self.profile = ctk.StringVar(value="Three-board candling rig")
        self.profile_menu = ctk.CTkOptionMenu(connection, values=list(self.PROFILES), variable=self.profile,
                          font=(FUTheme.FONT_FAMILY, 14), fg_color=FUTheme.PRIMARY_MAROON,
                          button_color=FUTheme.HOVER_MAROON)
        self.profile_menu.pack(anchor="w", padx=8, pady=8)
        self._button(connection, "Load selected rig defaults", self._rig_defaults)
        self._entry(connection, "conveyor_port", "Conveyor ESP32 serial port", "")
        self._entry(connection, "servo_port", "Egg / servo ESP32 serial port", "")
        self._entry(connection, "light_port", "Light ESP32 port (three-board rig)", "")
        self.port_label = ctk.CTkLabel(connection, font=(FUTheme.FONT_FAMILY, 14), text="Refresh to list connected serial ports", wraplength=820, justify="left")
        self.port_label.pack(anchor="w", padx=8, pady=10)
        self._button(connection, "Refresh ports", lambda: self._job(lambda: "\n".join(f"{p.device}: {p.description}" for p in list_ports.comports()) or "No ports found", self._ports))
        self._button(connection, "Discover three-board rig", self._discover)
        self._button(connection, "Connect and identify boards", lambda: self._job(self.station.connect))
        self._button(connection, "Acknowledge inspected board faults", self._acknowledge)
        ctk.CTkLabel(connection, font=(FUTheme.FONT_FAMILY, 14), text="Connect after applying the selected ports. Acknowledgement clears faults; it does not establish conveyor position.", wraplength=820).pack(anchor="w", padx=8, pady=12)

        camera = ctk.CTkScrollableFrame(tabs.tab("Camera"), height=200)
        camera.pack(fill="both", expand=True)
        camera_labels = {"index": "Camera index", "width": "Width (pixels)", "height": "Height (pixels)", "fps": "Requested FPS",
                         "auto_exposure": "Auto exposure (native driver value)", "autofocus": "Autofocus (0 off / 1 on)",
                         "auto_white_balance": "Auto white balance (0 off / 1 on)", "exposure": "Exposure (native driver units)",
                         "gain": "Gain", "focus": "Focus", "white_balance": "White balance temperature",
                         "brightness": "Brightness", "contrast": "Contrast", "saturation": "Saturation", "sharpness": "Sharpness"}
        for name in camera_labels:
            self._entry(camera, "camera." + name, camera_labels[name], "")
        ctk.CTkLabel(camera, font=(FUTheme.FONT_FAMILY, 14), text="Blank optional fields leave the driver unchanged. DirectShow uses 0 for manual exposure and 1 for automatic. Use Camera controls beside the preview for backend-aware On / Off choices; verify readback.", wraplength=760, justify="left").pack(anchor="w", padx=8, pady=10)
        ctk.CTkCheckBox(camera, font=(FUTheme.FONT_FAMILY, 14), text="Confirm selected camera / changed device identity", variable=self.confirm_camera).pack(anchor="w", padx=8, pady=6)
        self.report.pack(fill="x", pady=(8, 0))
        self.report.insert("1.0", "No camera property report yet. Apply settings to start idle preview and inspect readback.")
        self.report.configure(state="disabled")

        detection = tabs.tab("Detection")
        for name, label in (("confidence", "Detection confidence (0.01–0.99)"), ("iou", "NMS IoU (0.01–0.99)"),
                            ("sort_confidence", "Automatic-sort confidence (0.70–0.99)")):
            self._entry(detection, "detection." + name, label, "")
        ctk.CTkLabel(detection, font=(FUTheme.FONT_FAMILY, 14), text="Sorting requires three agreeing fresh frames over at least 300 ms, within two seconds. Low confidence or conflicting evidence holds the conveyor for review.", wraplength=800, justify="left").pack(anchor="w", padx=8, pady=20)

        calibration = ctk.CTkScrollableFrame(tabs.tab("Calibration"))
        calibration.pack(fill="both", expand=True)
        labels = {"holder_steps": "Holder spacing (steps)", "sorter_steps": "Chamber to gate centre (steps)",
                  "gate_clearance_steps": "Gate approach / exit clearance (steps)", "direction": "Forward direction (-1 or 1)",
                  "speed_us": "STEP half-period (microseconds)", "ir_offset_steps": "IR trigger to stopped capture (steps)",
                  "position_tolerance_steps": "Chamber arrival tolerance (steps)", "settle_ms": "Capture settling time (ms)",
                  "passage_ms": "Gate passage wait (ms)", "neutral_angle": "Neutral servo angle", "fertile_angle": "Fertile angle",
                  "infertile_angle": "Infertile angle", "hold_ms": "Result display hold (ms)",
                  "buffer_drain": "Fresh capture buffer drain (frames)", "jam_timeout_s": "Egg search timeout (seconds)"}
        for name, label in labels.items():
            self._entry(calibration, "calibration." + name, label, "")
        self.jog = self._entry(calibration, "_jog", "Manual jog steps (signed, at most 100000)", "100")
        self._button(calibration, "Jog conveyor", self._jog)
        self._button(calibration, "Set aligned position as software home", lambda: self._job(lambda: self.station.command("CONVEYOR", "SETHOME")))
        for label, text in (("Test fertile route", "SORT:FERTILE"), ("Test infertile route", "SORT:INFERTILE"), ("Return servo to neutral", "RESET")):
            self._button(calibration, label, lambda text=text: self._job(lambda: self.station.command("SERVO", text)))
        for label, text in (("Test candling lamp ON", "LIGHT_ON"), ("Turn candling lamp OFF", "LIGHT_OFF")):
            self._button(calibration, label, lambda text=text: self._job(lambda: self.station.command("LIGHT_CONTROLLER", text)))
        self._button(calibration, "Release hardware pause for alignment", lambda: self._job(lambda: self.station.command("SERVO", "RESUME")))
        self._button(calibration, "Hold hardware pause", lambda: self._job(lambda: self.station.command("SERVO", "PAUSE")))
        ctk.CTkLabel(calibration, font=(FUTheme.FONT_FAMILY, 14), text="Clear downstream eggs and bench-test stopping, gate directions and spacing. Three-board routing uses measured gate entry / exit positions; the old IR offset and passage wait apply only to the two-board rig. Release hardware pause deliberately before an unloaded alignment jog.", wraplength=760, justify="left").pack(anchor="w", padx=8, pady=8)
        ctk.CTkCheckBox(calibration, font=(FUTheme.FONT_FAMILY, 14), text="IR / gate bench-tested, geometry measured, holders aligned and cleared",
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
        ctk.CTkLabel(row, text=label, anchor="w", width=370,
                     font=(FUTheme.FONT_FAMILY, 14), text_color=FUTheme.TEXT_SECONDARY).pack(side="left")
        entry = ctk.CTkEntry(row, height=38, width=200, font=(FUTheme.FONT_FAMILY, 14),
                            fg_color=FUTheme.BG_LIGHT, border_color=FUTheme.BORDER_DARK,
                            text_color=FUTheme.TEXT_PRIMARY)
        entry.pack(side="right", padx=8)
        entry.insert(0, value)
        self.entries[key] = entry
        return entry

    def _button(self, parent, label, command, side=None):
        primary = label in {"Apply", "Connect and identify boards"}
        button = ctk.CTkButton(parent, text=label, command=command, height=40,
                              width=max(140, len(label) * 8 + 24),
                              font=(FUTheme.FONT_FAMILY, 14, "bold"),
                              fg_color=FUTheme.PRIMARY_MAROON if primary else FUTheme.PANEL_LIGHT_ALT,
                              hover_color=FUTheme.HOVER_MAROON if primary else FUTheme.PANEL_ACCENT,
                              border_width=0 if primary else 1, border_color=FUTheme.BORDER,
                              text_color=FUTheme.TEXT_WHITE if primary else FUTheme.TEXT_PRIMARY)
        button.pack(side=side or "top", anchor="w", padx=6, pady=4)
        self.buttons.append(button)
        return button

    def _fill(self, settings):
        values = settings.snapshot()
        self.profile.set(next(label for label, value in self.PROFILES.items() if value == settings.rig_profile))
        for key, entry in self.entries.items():
            if key.startswith("_"):
                continue
            parts = key.split(".")
            value = values[parts[0]][parts[1]] if len(parts) == 2 else values[key]
            entry.delete(0, "end")
            entry.insert(0, "" if value is None else str(value))

    def _values(self):
        values = self.station.settings.snapshot()
        values["rig_profile"] = self.PROFILES[self.profile.get()]
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
        self.profile_menu.configure(state="disabled")
        for button in self.buttons:
            button.configure(state="disabled")
        for entry in self.entries.values():
            entry.configure(state="disabled")
        self.notice.configure(text="Working…")
        def finish(value, failed=False):
            self.pending = False
            if not self.winfo_exists():
                return
            self.profile_menu.configure(state="normal")
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
        self.app._diagnostic_view = None
        def applied(report):
            self._fill(self.station.settings)
            self.confirm_camera.set(False)
            self.report.configure(state="normal")
            self.report.delete("1.0", "end")
            self.report.insert("1.0", "\n".join(f"{name}: requested {v['requested']}, readback {v['actual']} — {v['status']}" for name, v in report["properties"].items()))
            self.report.configure(state="disabled")
            self.notice.configure(text="Defaults saved." if save else "Applied for this run. Revalidate calibration before sorting.")
        self._job(lambda: self.station.apply(settings, save, confirm), applied)

    def _restore(self):
        self._job(self.station.store.load, lambda value: (self._fill(value), self.notice.configure(text="Saved defaults loaded into the form. Apply to use them.")))

    def _ports(self, value):
        self.port_label.configure(text=value)

    def _rig_defaults(self):
        settings = EdgeSettings.three_board() if self.PROFILES[self.profile.get()] == "three_v3" else EdgeSettings()
        self._fill(settings)
        self.notice.configure(text="Rig defaults loaded into the form. Select ports and confirm the camera, then Apply. Physical calibration is still required.")

    def _discover(self):
        if self.PROFILES[self.profile.get()] != "three_v3":
            self.notice.configure(text="Select the three-board rig before discovery.")
            return
        def found(ports):
            for key, role in (("conveyor_port", "CONVEYOR"), ("servo_port", "EGG_CONTROLLER"), ("light_port", "LIGHT_CONTROLLER")):
                self.entries[key].delete(0, "end")
                self.entries[key].insert(0, ports[role])
            self.notice.configure(text="Three roles identified. Apply these ports, then Connect and inspect the rig.")
        self._job(self.station.discover, found)

    def _acknowledge(self):
        def work():
            links = self.station.board_links()
            if not links:
                raise RuntimeError("Connect and inspect the rig first")
            for link in links:
                self.station.command(link.role, "ACK_FAULT")
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
        self.destroy()
