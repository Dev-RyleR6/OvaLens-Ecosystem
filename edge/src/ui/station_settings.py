"""Idle-only station settings, applied through the operation worker."""
import customtkinter as ctk
from .select_field import SelectField
from serial.tools import list_ports
from ..core.settings import EdgeSettings
from .theme import FUTheme
from .desktop_style import enable_button_keyboard, reveal_in_scroll_frame


class StationSettingsWindow(ctk.CTkToplevel):
    PROFILES = {
        "Single-board unified rig": "unified_v4",
        "Three-board candling rig": "three_v3",
        "Two-board indexed rig": "dual_v2",
    }
    def __init__(self, app):
        super().__init__(app)
        self.app, self.station = app, app.station
        self.title("OvaLens station settings")
        self.geometry("1000x800")
        app._center_window(self, 1000, 800)
        self.minsize(min(800, app.winfo_width() - 24), min(640, app.winfo_height() - 32))
        self.configure(fg_color=FUTheme.BG_LIGHT)
        self.transient(app)
        self.grab_set()
        self.pending = False
        self.entries = {}
        self.buttons = []
        ctk.CTkLabel(self, text="Station settings", font=(FUTheme.FONT_FAMILY, 22, "bold")).pack(anchor="w", padx=24, pady=(18, 4))
        ctk.CTkLabel(self, font=(FUTheme.FONT_FAMILY, 14), text="Configure the idle station. Use Maintenance for physical tests and alignment.", wraplength=850).pack(anchor="w", padx=24)
        from .appearance import appearance_picker
        appearance_row = ctk.CTkFrame(self, fg_color="transparent")
        appearance_row.pack(fill="x", padx=24, pady=(8, 0))
        ctk.CTkLabel(appearance_row, text="Appearance", text_color=FUTheme.TEXT_PRIMARY).pack(side="left")
        self.appearance = appearance_picker(appearance_row, app)
        self.appearance.pack(side="right")
        workspace = ctk.CTkFrame(self, fg_color=FUTheme.PANEL_LIGHT, corner_radius=8,
                                 border_width=1, border_color=FUTheme.BORDER)
        workspace.pack(fill="both", expand=True, padx=20, pady=12)
        workspace.grid_columnconfigure(1, weight=1)
        workspace.grid_rowconfigure(0, weight=1)
        navigation = ctk.CTkFrame(workspace, width=164, fg_color=FUTheme.PANEL_LIGHT_ALT, corner_radius=0)
        navigation.grid(row=0, column=0, sticky="ns", padx=1, pady=1)
        navigation.grid_propagate(False)
        navigation.grid_columnconfigure(0, weight=1)
        content = ctk.CTkFrame(workspace, fg_color="transparent")
        content.grid(row=0, column=1, sticky="nsew", padx=16, pady=12)
        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(0, weight=1)
        self.sections, self.section_buttons = {}, {}
        for index, name in enumerate(("Connections", "Camera", "Detection", "Calibration", "Maintenance")):
            frame = ctk.CTkFrame(content, fg_color="transparent")
            self.sections[name] = frame
            button = ctk.CTkButton(navigation, text=name, anchor="w", height=40, width=144,
                font=(FUTheme.FONT_FAMILY, 13), fg_color="transparent",
                text_color=FUTheme.TEXT_SECONDARY, hover_color=FUTheme.PANEL_ACCENT,
                command=lambda name=name: self._show_section(name))
            button.grid(row=index, column=0, sticky="ew", padx=8, pady=(12 if index == 0 else 2, 2))
            self.section_buttons[name] = button
            enable_button_keyboard(button)
        recovery = getattr(self.station, "recovery", None)
        recovery_notice = "Interrupted cycle found. Inspect and reconcile physical eggs before acknowledging faults or validating." if recovery and recovery.get("state") not in {"COMPLETE", "CLEARED"} else ""
        self.notice = ctk.CTkLabel(self, font=(FUTheme.FONT_FAMILY, 14), text=self.station.settings_error or recovery_notice or "Apply for this run is temporary. Save defaults also remembers these settings.",
                                  wraplength=850, justify="left")
        self.notice.pack(fill="x", padx=24, pady=6)
        self.confirm_camera = ctk.BooleanVar(value=False)
        self.inspected = ctk.BooleanVar(value=False)

        connection = ctk.CTkScrollableFrame(self.sections.get("Connections"), fg_color="transparent")
        connection.pack(fill="both", expand=True)
        self._heading(connection, "Controller connections", "Choose the installed rig, apply its ports, then connect and identify.")
        self.profile = ctk.StringVar(value="Three-board candling rig")
        ctk.CTkLabel(connection, text="Rig profile", font=(FUTheme.FONT_FAMILY, FUTheme.FONT_LABEL, "bold"),
                     text_color=FUTheme.TEXT_PRIMARY).pack(anchor="w", padx=8, pady=(8, 0))
        self.profile_menu = SelectField(connection, values=list(self.PROFILES), variable=self.profile, font=(FUTheme.FONT_FAMILY, 14))
        self.profile_menu.pack(fill="x", padx=8, pady=8)
        self._button(connection, "Load selected rig defaults", self._rig_defaults)
        self._entry(connection, "conveyor_port", "Conveyor ESP32 serial port", "")
        self._entry(connection, "servo_port", "Egg / servo ESP32 serial port", "")
        self._entry(connection, "light_port", "Light ESP32 port (three-board rig)", "")
        self.port_label = ctk.CTkLabel(connection, font=(FUTheme.FONT_FAMILY, 14), text="Refresh to list connected serial ports", wraplength=820, justify="left")
        self.port_label.pack(anchor="w", padx=8, pady=10)
        self._button(connection, "Refresh ports", lambda: self._job(lambda: "\n".join(f"{p.device}: {p.description}" for p in list_ports.comports()) or "No ports found", self._ports))
        self._button(connection, "Find controller ports", self._discover)
        self._button(connection, "Connect and identify boards", lambda: self._job(self.station.connect))
        ctk.CTkLabel(connection, font=(FUTheme.FONT_FAMILY, 14), text="Connect after applying the selected ports. Acknowledgement clears faults; it does not establish conveyor position.", wraplength=820).pack(anchor="w", padx=8, pady=12)

        camera = ctk.CTkScrollableFrame(self.sections.get("Camera"), height=200, fg_color="transparent")
        camera.pack(fill="both", expand=True)
        self._heading(camera, "Camera configuration", "Set the device and capture format here. Tune the image with Camera controls beside the live preview.")
        camera_labels = {"index": "Camera index", "width": "Width (pixels)", "height": "Height (pixels)", "fps": "Requested FPS",
                         "auto_exposure": "Auto exposure (native driver value)", "autofocus": "Autofocus (0 off / 1 on)",
                         "auto_white_balance": "Auto white balance (0 off / 1 on)", "exposure": "Exposure (native driver units)",
                         "gain": "Gain", "focus": "Focus", "white_balance": "White balance temperature",
                         "brightness": "Brightness", "contrast": "Contrast", "saturation": "Saturation", "sharpness": "Sharpness"}
        for name in camera_labels:
            if name == "auto_exposure":
                self._heading(camera, "Driver defaults", "Optional native values. Blank fields leave the current driver value unchanged.")
            self._entry(camera, "camera." + name, camera_labels[name], "")
        ctk.CTkLabel(camera, font=(FUTheme.FONT_FAMILY, 14), text="Blank optional fields leave the driver unchanged. DirectShow uses 0 for manual exposure and 1 for automatic. Use Camera controls beside the preview for backend-aware On / Off choices; verify readback.", wraplength=760, justify="left").pack(anchor="w", padx=8, pady=10)
        ctk.CTkCheckBox(camera, font=(FUTheme.FONT_FAMILY, 14), text="Confirm camera device identity", variable=self.confirm_camera).pack(anchor="w", padx=8, pady=6)
        self._heading(camera, "Driver readback")
        self.report = ctk.CTkTextbox(camera, height=150, font=(FUTheme.FONT_FAMILY, 13),
            fg_color=FUTheme.BG_LIGHT, text_color=FUTheme.TEXT_SECONDARY)
        self.report.pack(fill="x", padx=8, pady=(8, 12))
        self.report.insert("1.0", "No camera property report yet. Apply settings to start idle preview and inspect readback.")
        self.report.configure(state="disabled")

        detection = ctk.CTkScrollableFrame(self.sections["Detection"], fg_color="transparent")
        detection.pack(fill="both", expand=True)
        self._heading(detection, "Classification thresholds", "Automatic sorting uses the station threshold. Uncertain results stop for manual review.")
        for name, label in (("confidence", "Detection confidence (0.01–0.99)"), ("iou", "NMS IoU (0.01–0.99)"),
                            ("sort_confidence", "Automatic-sort confidence (0.70–0.99)")):
            self._entry(detection, "detection." + name, label, "")
        ctk.CTkLabel(detection, font=(FUTheme.FONT_FAMILY, 14), text="Sorting requires three agreeing fresh frames over at least 300 ms, within two seconds. Low confidence or conflicting evidence holds the conveyor for review.", wraplength=800, justify="left").pack(anchor="w", padx=8, pady=20)

        calibration = ctk.CTkScrollableFrame(self.sections.get("Calibration"), fg_color="transparent")
        calibration.pack(fill="both", expand=True)
        self._heading(calibration, "Measured rig calibration", "Enter measured geometry and timing. Apply changes before validating the inspected setup.")
        labels = {"holder_steps": "Holder spacing (steps)", "sorter_steps": "Chamber to gate centre (steps)",
                  "gate_clearance_steps": "Gate approach / exit clearance (steps)", "direction": "Forward direction (-1 or 1)",
                  "speed_us": "STEP half-period (microseconds)", "ir_offset_steps": "IR trigger to stopped capture (steps)",
                  "position_tolerance_steps": "Chamber arrival tolerance (steps)", "settle_ms": "Capture settling time (ms)",
                  "passage_ms": "Gate passage wait (ms)", "neutral_angle": "Neutral servo angle", "fertile_angle": "Fertile angle",
                  "infertile_angle": "Infertile angle", "hold_ms": "Result display hold (ms)",
                  "buffer_drain": "Fresh capture buffer drain (frames)", "jam_timeout_s": "Egg search timeout (seconds)"}
        for name, label in labels.items():
            self._entry(calibration, "calibration." + name, label, "")
        maintenance = ctk.CTkScrollableFrame(self.sections["Maintenance"], fg_color="transparent")
        maintenance.pack(fill="both", expand=True)
        self._heading(maintenance, "Hardware maintenance", "These commands can move the rig or switch the lamp. Empty the conveyor and inspect the path first. Position and passage remain estimated.")
        self._button(maintenance, "Acknowledge inspected board faults", self._acknowledge)
        self._heading(maintenance, "Conveyor alignment")
        self.jog = self._entry(maintenance, "_jog", "Manual jog steps (signed, at most 100000)", "100")
        self._button(maintenance, "Jog conveyor", self._jog)
        self._button(maintenance, "Set aligned position as software home", lambda: self._job(lambda: self.station.command("CONVEYOR", "SETHOME")))
        self._heading(maintenance, "Sorting gate")
        for label, text in (("Test fertile route", "SORT:FERTILE"), ("Test infertile route", "SORT:INFERTILE"), ("Return servo to neutral", "RESET")):
            self._button(maintenance, label, lambda text=text: self._job(lambda: self.station.command("SERVO", text)))
        self._heading(maintenance, "Candling lamp and pause")
        for label, text in (("Test candling lamp ON", "LIGHT_ON"), ("Turn candling lamp OFF", "LIGHT_OFF")):
            self._button(maintenance, label, lambda text=text: self._job(lambda: self.station.command("LIGHT_CONTROLLER", text)))
        self._button(maintenance, "Release hardware pause for alignment", lambda: self._job(lambda: self.station.command("SERVO", "RESUME")))
        self._button(maintenance, "Hold hardware pause", lambda: self._job(lambda: self.station.command("SERVO", "PAUSE")))
        ctk.CTkLabel(calibration, font=(FUTheme.FONT_FAMILY, 14), text="Clear downstream eggs and bench-test stopping, gate directions and spacing. Three-board routing uses measured gate entry / exit positions; the old IR offset and passage wait apply only to the two-board rig. Release hardware pause deliberately before an unloaded alignment jog.", wraplength=760, justify="left").pack(anchor="w", padx=8, pady=8)
        ctk.CTkCheckBox(calibration, font=(FUTheme.FONT_FAMILY, 14), text="Rig inspected and calibration verified",
                        variable=self.inspected).pack(anchor="w", padx=8, pady=14)
        self._button(calibration, "Load calibration and validate inspected setup", self._validate)

        actions = ctk.CTkFrame(self, fg_color="transparent")
        self.actions = actions
        actions.pack(fill="x", padx=24, pady=(6, 18))
        for label, command in (("Apply for this run", lambda: self._apply(False)), ("Save defaults", lambda: self._apply(True)),
                               ("Load saved", self._restore)):
            self._button(actions, label, command, side="left")
        self.stop_button = ctk.CTkButton(actions, text="STOP", fg_color=FUTheme.REJECT_RED,
            hover_color=FUTheme.REJECT_RED_HOVER, command=self.station.halt, width=75, height=44)
        self.stop_button.pack(side="right", padx=4)
        enable_button_keyboard(self.stop_button)
        self.done_button = ctk.CTkButton(actions, text="Done", width=72, height=40,
            fg_color=FUTheme.PANEL_LIGHT_ALT, hover_color=FUTheme.PANEL_ACCENT,
            text_color=FUTheme.TEXT_PRIMARY, border_width=1, border_color=FUTheme.BORDER_CONTROL,
            command=self._close)
        self.done_button.pack(side="right", padx=4)
        enable_button_keyboard(self.done_button)
        self._show_section("Connections")
        self._fill(self.station.settings)
        self.protocol("WM_DELETE_WINDOW", self._close)
        self._wrapped_labels = []
        def collect(parent):
            for child in parent.winfo_children():
                if isinstance(child, ctk.CTkLabel) and child.cget("wraplength"):
                    self._wrapped_labels.append(child)
                collect(child)
        collect(self)
        self.bind("<Configure>", self._fit_text)
        self._fit_text()

    def _heading(self, parent, title, detail=""):
        ctk.CTkLabel(parent, text=title, anchor="w", font=(FUTheme.FONT_FAMILY, 16, "bold"),
            text_color=FUTheme.TEXT_PRIMARY).pack(fill="x", padx=8, pady=(16, 4))
        if detail:
            ctk.CTkLabel(parent, text=detail, anchor="w", justify="left", wraplength=550,
                font=(FUTheme.FONT_FAMILY, 13), text_color=FUTheme.TEXT_MUTED).pack(fill="x", padx=8, pady=(0, 12))

    def _show_section(self, name):
        for title, frame in self.sections.items():
            frame.grid_forget()
            selected = title == name
            self.section_buttons[title].configure(
                fg_color=FUTheme.PANEL_LIGHT if selected else "transparent",
                text_color=FUTheme.BRAND_TEXT if selected else FUTheme.TEXT_SECONDARY,
                font=(FUTheme.FONT_FAMILY, 13, "bold" if selected else "normal"))
        self.sections[name].grid(row=0, column=0, sticky="nsew")
        self.active_section = name

    def _fit_text(self, event=None):
        if event is not None and event.widget is not self:
            return
        width = max(240, self.winfo_width() - 112)
        if width == getattr(self, "_text_width", None):
            return
        self._text_width = width
        field_rows = {entry.master for entry in self.entries.values()}
        for label in self._wrapped_labels:
            available = max(180, self.winfo_width() - 440) if label.master in field_rows else max(240, self.winfo_width() - 330)
            label.configure(wraplength=min(300, available) if label.master in field_rows else available)

    def _entry(self, parent, key, label, value):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=8, pady=4)
        row.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(row, text=label, anchor="w", justify="left", wraplength=300,
                     font=(FUTheme.FONT_FAMILY, 14), text_color=FUTheme.TEXT_SECONDARY).grid(row=0, column=0, sticky="w", padx=(0, 16))
        entry = ctk.CTkEntry(row, height=36, width=150, font=(FUTheme.FONT_FAMILY, 14),
                            fg_color=FUTheme.INPUT_BG, border_color=FUTheme.BORDER_CONTROL,
                            text_color=FUTheme.TEXT_PRIMARY)
        entry.grid(row=0, column=1, sticky="e", padx=(0, 8))
        entry.bind("<FocusIn>", lambda _: reveal_in_scroll_frame(entry), add="+")
        entry.insert(0, value)
        self.entries[key] = entry
        return entry

    def _button(self, parent, label, command, side=None):
        primary = label == "Apply for this run"
        button = ctk.CTkButton(parent, text=label, command=command, height=44 if primary else 40,
                              width=max(100, len(label) * 7 + 20),
                              font=(FUTheme.FONT_FAMILY, 14, "bold"),
                              fg_color=FUTheme.PRIMARY_MAROON if primary else FUTheme.PANEL_LIGHT_ALT,
                              hover_color=FUTheme.HOVER_MAROON if primary else FUTheme.PANEL_ACCENT,
                              border_width=1, border_color=FUTheme.BORDER_CONTROL,
                              text_color=FUTheme.TEXT_WHITE if primary else FUTheme.TEXT_PRIMARY,
                              text_color_disabled=FUTheme.TEXT_DISABLED_ON_ACCENT if primary else FUTheme.TEXT_MUTED)
        button.pack(side=side or "top", anchor="w", padx=6, pady=4)
        enable_button_keyboard(button)
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
        prof = self.PROFILES[self.profile.get()]
        if prof == "unified_v4":
            settings = EdgeSettings.unified_board()
        elif prof == "three_v3":
            settings = EdgeSettings.three_board()
        else:
            settings = EdgeSettings()
        self._fill(settings)
        self.notice.configure(text="Rig defaults loaded into the form. Select ports and confirm the camera, then Apply. Physical calibration is still required.")

    def _discover(self):
        prof = self.PROFILES[self.profile.get()]
        if prof == "unified_v4":
            def found_unified(port):
                self.entries["conveyor_port"].delete(0, "end")
                self.entries["conveyor_port"].insert(0, port)
                self.notice.configure(text=f"Unified ESP32 controller identified on {port}. Apply and Connect.")
            self._job(self.station.discover, found_unified)
            return
        if prof != "three_v3":
            self.notice.configure(text="Select the single-board or three-board rig before discovery.")
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
