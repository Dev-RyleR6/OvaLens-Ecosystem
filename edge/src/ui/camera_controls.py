"""Idle camera tuning alongside the main preview, using background requests."""
import math
import threading
from dataclasses import replace
import customtkinter as ctk

from ..core.camera_controls import (AUTO_CONTROLS, NUMERIC_CONTROLS, MANUAL_PAIRS,
                                    camera_values, exposure_modes, mode_label, slider_span,
                                    validate_slider_ranges)
from .theme import FUTheme


class CameraControlsPanel(ctk.CTkFrame):
    def __init__(self, app):
        super().__init__(app.right_panel, fg_color=FUTheme.PANEL_LIGHT, corner_radius=12,
                         border_width=1, border_color=FUTheme.BORDER)
        self.app = app
        self.pending = False
        self._live_after = None
        self._live_busy = False
        self._live_dirty = False
        self._live_last = None
        self._live_delay = 150
        self.entries, self.modes, self.readbacks, self.controls = {}, {}, {}, []
        self.sliders, self.range_fields = {}, {}
        self.slider_ranges = {}
        self.alignment_ready = False
        self.alignment_cancel = threading.Event()
        self.base = app.station.settings.camera
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=18, pady=(12, 4))
        self.done = ctk.CTkButton(header, text="Done", width=65, height=34,
            font=(FUTheme.FONT_FAMILY, 13), fg_color=FUTheme.PANEL_LIGHT_ALT,
            hover_color=FUTheme.PANEL_ACCENT, command=self.close)
        self.done.pack(side="right")
        ctk.CTkLabel(header, text="Camera controls", font=(FUTheme.FONT_FAMILY, 20, "bold"),
                     text_color=FUTheme.TEXT_PRIMARY).pack(side="left")
        ctk.CTkLabel(self, text="Live preview. Save to remember your changes.", height=18,
            wraplength=340, justify="left", anchor="w", font=(FUTheme.FONT_FAMILY, 13),
            text_color=FUTheme.TEXT_SECONDARY).pack(fill="x", padx=18, pady=(0, 8))
        actions = self.camera_actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(side="bottom", fill="x", padx=18, pady=(4, 10))
        actions.grid_columnconfigure((0, 1), weight=1)
        for column, (label, save) in enumerate((("Apply now", False), ("Save as default", True))):
            button = ctk.CTkButton(actions, text=label, height=34, width=155,
                font=(FUTheme.FONT_FAMILY, 13, "bold"),
                fg_color=FUTheme.PRIMARY_MAROON if not save else FUTheme.PANEL_LIGHT_ALT,
                hover_color=FUTheme.HOVER_MAROON if not save else FUTheme.PANEL_ACCENT,
                border_width=0 if not save else 1, border_color=FUTheme.BORDER,
                command=lambda save=save: self.apply(save))
            button.grid(row=0, column=column, padx=3, pady=4, sticky="ew")
            self.controls.append(button)
        restore = ctk.CTkButton(actions, text="Load saved settings", height=28,
            font=(FUTheme.FONT_FAMILY, 13), fg_color=FUTheme.PANEL_LIGHT_ALT,
            hover_color=FUTheme.PANEL_ACCENT, command=self.restore)
        restore.grid(row=1, column=0, columnspan=2, sticky="ew", padx=3, pady=4)
        self.controls.append(restore)
        self.notice = ctk.CTkLabel(self, text="Changes update the preview automatically.", height=18,
            font=(FUTheme.FONT_FAMILY, 12), text_color=FUTheme.TEXT_SECONDARY,
            wraplength=340, justify="left", anchor="w")
        self.notice.pack(side="bottom", fill="x", padx=20, pady=6)
        self.section = ctk.CTkSegmentedButton(self, values=["Camera", "Cradle"],
            font=(FUTheme.FONT_FAMILY, 13), command=self._section,
            selected_color=FUTheme.PRIMARY_MAROON, selected_hover_color=FUTheme.HOVER_MAROON,
            unselected_color=FUTheme.PANEL_LIGHT_ALT, unselected_hover_color=FUTheme.PANEL_ACCENT,
            fg_color=FUTheme.PANEL_LIGHT_ALT)
        self.section.pack(fill="x", padx=18, pady=(0, 4))
        self.section.set("Camera")
        self.controls.append(self.section)
        body = self.camera_body = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        body.pack(fill="both", expand=True, padx=12, pady=4)
        order = ("autofocus", "focus", "auto_exposure", "exposure", "gain",
                 "auto_white_balance", "white_balance", "brightness", "contrast",
                 "saturation", "sharpness")
        for name in order:
            row = self._row(body, name, (AUTO_CONTROLS | NUMERIC_CONTROLS)[name])
            if name in AUTO_CONTROLS:
                control = ctk.CTkOptionMenu(row, values=["Unchanged", "On", "Off", "Saved value"],
                    width=140, height=34, font=(FUTheme.FONT_FAMILY, 13),
                    fg_color=FUTheme.PANEL_LIGHT_ALT, button_color=FUTheme.PANEL_ACCENT,
                    button_hover_color=FUTheme.BORDER_DARK, command=self._mode_changed)
                self.modes[name] = control
            else:
                control = ctk.CTkEntry(row, width=92, height=34, font=(FUTheme.FONT_FAMILY, 13),
                    fg_color=FUTheme.BG_LIGHT, border_color=FUTheme.BORDER_DARK,
                    placeholder_text="Leave unchanged")
                self.entries[name] = control
                self._slider(row.master, row, name)
                control.bind("<KeyRelease>", lambda _, name=name: self._entry_changed(name))
                control.bind("<FocusOut>", lambda _, name=name: self._entry_changed(name))
            control.pack(side="right")
            self.controls.append(control)
        ctk.CTkLabel(body, text="Sliders and automatic modes update the preview live. Typed values apply after a short pause. Range edits the tuning span, not camera-reported limits. Turn automatic mode Off to tune its manual value.",
            wraplength=320, justify="left", font=(FUTheme.FONT_FAMILY, 12),
            text_color=FUTheme.TEXT_MUTED).pack(fill="x", padx=6, pady=10)
        self._build_cradle()
        self.fill(self.base)
        self._live_last = replace(self.base, slider_ranges=dict(self.slider_ranges))
        self.show_report(getattr(app.camera, "property_report", {}))
        self.place(x=0, y=0, relwidth=1, relheight=1)
        self.lift()

    def _slider(self, group, row, name):
        button = ctk.CTkButton(row, text="Range", width=52, height=30,
            fg_color=FUTheme.PANEL_LIGHT_ALT, hover_color=FUTheme.PANEL_ACCENT,
            command=lambda: self._toggle_range(name))
        button.pack(side="right", padx=4)
        slider = ctk.CTkSlider(group, from_=0, to=255, number_of_steps=255,
            progress_color=FUTheme.PRIMARY_MAROON, button_color=FUTheme.TEXT_PRIMARY,
            command=lambda value: self._slider_changed(name, value))
        slider.pack(fill="x", pady=(6, 2), before=self.readbacks[name])
        editor = ctk.CTkFrame(group, fg_color="transparent")
        fields = []
        for label in ("Min", "Max"):
            ctk.CTkLabel(editor, text=label, width=28, font=(FUTheme.FONT_FAMILY, 12)).pack(side="left")
            field = ctk.CTkEntry(editor, width=75, height=30)
            field.pack(side="left", padx=(0, 5))
            fields.append(field)
        set_button = ctk.CTkButton(editor, text="Set", width=48, height=30,
            fg_color=FUTheme.PANEL_LIGHT_ALT, command=lambda: self._set_range(name))
        set_button.pack(side="left")
        self.sliders[name] = slider
        self.range_fields[name] = (editor, *fields)
        self.controls.extend((button, slider, *fields, set_button))

    def _toggle_range(self, name):
        editor = self.range_fields[name][0]
        if editor.winfo_manager():
            editor.pack_forget()
        else:
            editor.pack(fill="x", pady=4)

    def _set_range(self, name):
        try:
            _, low, high = self.range_fields[name]
            span = [float(low.get()), float(high.get())]
            validate_slider_ranges({name: span})
        except ValueError:
            self.notice.configure(text="Slider range needs a finite minimum smaller than its maximum.")
            return
        self.slider_ranges[name] = span
        self._configure_slider(name, expand=False)
        self.notice.configure(text="Slider span updated. Camera limits still depend on the driver.")

    def _configure_slider(self, name, expand=True):
        try:
            value = float(self.entries[name].get())
        except ValueError:
            value = None
        if value is not None and not math.isfinite(value):
            return
        identity = getattr(self.app.camera, "identity", "") or self.base.identity
        try:
            low, high = slider_span(name, identity, value if expand else None, self.slider_ranges)
        except ValueError as exc:
            self.notice.configure(text=str(exc))
            return
        count = max(1, min(10000, round(high - low))) if high - low >= 1 else 1000
        self.sliders[name].configure(from_=low, to=high, number_of_steps=count)
        if value is None:
            actual = getattr(self.app.camera, "property_report", {}).get(name, {}).get("actual")
            value = actual if type(actual) in (int, float) and math.isfinite(actual) else low
        self.sliders[name].set(max(low, min(high, value)))
        for field, number in zip(self.range_fields[name][1:], (low, high)):
            field.delete(0, "end")
            field.insert(0, f"{number:g}")

    def _slider_changed(self, name, value):
        entry = self.entries[name]
        if self.pending or entry.cget("state") == "disabled":
            return
        entry.delete(0, "end")
        entry.insert(0, f"{value:.6g}")
        self._queue_live()

    def _entry_changed(self, name):
        if not self.pending:
            self._configure_slider(name)
            self._queue_live(delay=350, trailing=True)

    def _mode_changed(self, _):
        self._manual_states()
        self._queue_live()

    def _values(self):
        camera = camera_values(self.base, {k: e.get() for k, e in self.entries.items()},
                               {k: m.get() for k, m in self.modes.items()}, self._exposure_modes())
        camera.slider_ranges = {k: list(v) for k, v in self.slider_ranges.items()}
        return camera

    def _cancel_live(self):
        if self._live_after is not None:
            self.after_cancel(self._live_after)
            self._live_after = None
        self._live_dirty = False

    def _queue_live(self, delay=150, trailing=False):
        if self.pending or self.app._closing or self.section.get() != "Camera":
            return
        self._live_dirty = True
        self._live_delay = delay
        if self._live_busy:
            return  # One in-flight request; the next one reads only the newest form.
        if self._live_after is not None:
            if not trailing:
                return
            self.after_cancel(self._live_after)
        self._live_after = self.after(delay, self._flush_live)

    def _flush_live(self):
        self._live_after = None
        if self.pending or self._live_busy or self.app._closing or not self.winfo_exists():
            return
        if not self._live_dirty or self.section.get() != "Camera" or not self.app._camera_tuning_allowed():
            self._live_dirty = False
            return
        self._live_dirty = False
        try:
            camera = self._values()
        except ValueError as exc:
            self.notice.configure(text=str(exc))
            return
        if camera == self._live_last:
            return
        self._live_busy = True
        self.app._diagnostic_view = None
        self.app.setup_inspected.set(False)
        self.notice.configure(text="Updating live preview...")
        def finished(report, failed=False):
            self._live_busy = False
            if self.app._closing or not self.winfo_exists():
                return
            if not failed:
                self._live_last = camera
                self.base = self.app.station.settings.camera
            if self.pending or self.section.get() != "Camera":
                return  # An explicit action already supersedes the live request.
            if failed:
                self._cancel_live()
                self.notice.configure(text="Live update failed: " + str(report) + "; adjust a value or use Apply now to retry.")
            else:
                self.show_report(report["properties"])
                self.notice.configure(text="Live preview updated. Save to remember.")
                if self._live_dirty:
                    self._queue_live(delay=self._live_delay)
        try:
            self.app._jobs.submit(lambda: self.app.station.apply_camera_controls(camera, live_preview=True),
                finished, lambda error: finished(error, True))
        except Exception as exc:
            finished(str(exc), True)

    def _section(self, name):
        if name != "Camera":
            self._cancel_live()
        self.camera_body.pack_forget()
        self.cradle_body.pack_forget()
        self.camera_actions.pack_forget()
        if name == "Camera":
            self.camera_actions.pack(side="bottom", fill="x", padx=18, pady=(4, 10), before=self.notice)
            self.camera_body.pack(fill="both", expand=True, padx=12, pady=4)
        else:
            self.cradle_body.pack(fill="both", expand=True, padx=12, pady=4)

    def _build_cradle(self):
        body = self.cradle_body = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        self.path_clear = ctk.BooleanVar(value=False)
        check = ctk.CTkCheckBox(body, text="Path clear; hands away from mechanism", variable=self.path_clear,
            font=(FUTheme.FONT_FAMILY, 12), command=self._alignment_states,
            fg_color=FUTheme.PRIMARY_MAROON, hover_color=FUTheme.HOVER_MAROON)
        check.pack(fill="x", pady=(6, 10))
        self.connect_alignment = ctk.CTkButton(body, text="Connect for alignment", height=36,
            fg_color=FUTheme.PRIMARY_MAROON, hover_color=FUTheme.HOVER_MAROON,
            command=self._prepare_alignment)
        self.connect_alignment.pack(fill="x", pady=4)
        row = ctk.CTkFrame(body, fg_color="transparent")
        row.pack(fill="x", pady=8)
        ctk.CTkLabel(row, text="Steps per click", font=(FUTheme.FONT_FAMILY, 13)).pack(side="left")
        self.jog_steps = ctk.CTkOptionMenu(row, values=["10", "25", "50", "100", "250", "500", "1000"], width=100,
            fg_color=FUTheme.PANEL_LIGHT_ALT, button_color=FUTheme.PANEL_ACCENT,
            button_hover_color=FUTheme.BORDER_DARK)
        self.jog_steps.set("25")
        self.jog_steps.pack(side="right")
        jogs = ctk.CTkFrame(body, fg_color="transparent")
        jogs.pack(fill="x", pady=4)
        jogs.grid_columnconfigure((0, 1), weight=1)
        self.jog_buttons = []
        for col, (label, direction) in enumerate((("Backward", -1), ("Forward", 1))):
            button = ctk.CTkButton(jogs, text=label, width=140, height=38,
                fg_color=FUTheme.PANEL_LIGHT_ALT, hover_color=FUTheme.PANEL_ACCENT,
                command=lambda direction=direction: self._jog(direction))
            button.grid(row=0, column=col, sticky="ew", padx=3)
            self.jog_buttons.append(button)
        ctk.CTkLabel(body, text="Connect opens the saved COM ports, acknowledges startup/STOP faults, holds the conveyor and turns the lamp on. Each click makes one slow move, then holds again. The IR sensor can stop it early. Done turns the lamp off; re-inspect before sorting. STOP [R] cancels movement.",
            wraplength=320, justify="left", font=(FUTheme.FONT_FAMILY, 12),
            text_color=FUTheme.TEXT_SECONDARY).pack(fill="x", pady=10)
        self.controls.extend((check, self.connect_alignment, self.jog_steps, *self.jog_buttons))
        self._alignment_states()

    def _alignment_states(self):
        allowed = not self.pending and self.path_clear.get()
        self.connect_alignment.configure(state="normal" if allowed else "disabled")
        for button in self.jog_buttons:
            button.configure(state="normal" if allowed and self.alignment_ready else "disabled")

    def _prepare_alignment(self):
        if self.pending or not self.app._camera_tuning_allowed() or not self.path_clear.get():
            return
        self.alignment_ready = False
        self.alignment_cancel = cancel = threading.Event()
        self.app.setup_inspected.set(False)
        def ready(message):
            self.alignment_ready = not cancel.is_set() and self.app.station._camera_alignment_boards is not None
            self.notice.configure(text=message if self.alignment_ready else "Alignment stopped. Inspect and reconnect.")
        self._job(lambda: self.app.station.prepare_camera_alignment(True, cancel=cancel), ready,
                  "Connecting for alignment...")

    def _jog(self, direction):
        if self.pending or not self.alignment_ready or not self.path_clear.get() or not self.app._camera_tuning_allowed():
            return
        steps = direction * int(self.jog_steps.get()) * self.app.station.settings.calibration.direction
        self.app.setup_inspected.set(False)
        self.app._diagnostic_view = None
        cancel = self.alignment_cancel
        self._job(lambda: self.app.station.jog_camera_cradle(steps, cancel=cancel),
                  lambda message: self.notice.configure(text=message if not cancel.is_set() else
                      "Alignment stopped. Inspect and reconnect."), "Moving cradle; STOP [R] is available...")

    def cancel_alignment(self):
        self._cancel_live()
        self.alignment_cancel.set()
        self.alignment_ready = False
        self.path_clear.set(False)
        self._alignment_states()

    def _row(self, parent, name, label):
        group = ctk.CTkFrame(parent, fg_color="transparent")
        group.pack(fill="x", padx=6, pady=(6, 0))
        row = ctk.CTkFrame(group, fg_color="transparent")
        row.pack(fill="x")
        ctk.CTkLabel(row, text=label, height=22, font=(FUTheme.FONT_FAMILY, 13),
                     text_color=FUTheme.TEXT_PRIMARY, anchor="w").pack(side="left")
        readback = ctk.CTkLabel(group, text="Driver: not checked", wraplength=315, height=18,
            justify="left", anchor="w", font=(FUTheme.FONT_FAMILY, 12), text_color=FUTheme.TEXT_MUTED)
        readback.pack(fill="x", pady=(2, 0))
        self.readbacks[name] = readback
        return row

    def _exposure_modes(self):
        return getattr(self.app.camera, "exposure_modes", None) or exposure_modes(
            getattr(self.app.camera, "identity", "") or self.base.identity)

    def fill(self, camera):
        self.base = camera
        self.slider_ranges = {k: list(v) for k, v in camera.slider_ranges.items()}
        for name, entry in self.entries.items():
            entry.configure(state="normal")
            entry.delete(0, "end")
            value = getattr(camera, name)
            entry.insert(0, "" if value is None else str(value))
            self._configure_slider(name)
        for name, menu in self.modes.items():
            values = self._exposure_modes() if name == "auto_exposure" else {"On": 1.0, "Off": 0.0}
            menu.set(mode_label(getattr(camera, name), values))
        self._manual_states()

    def _manual_states(self):
        for auto, manual in MANUAL_PAIRS.items():
            state = "disabled" if self.pending or self.modes[auto].get() == "On" else "normal"
            self.entries[manual].configure(state=state)
            self.sliders[manual].configure(state=state)

    def show_report(self, report):
        for name, label in self.readbacks.items():
            if name not in report:
                continue
            item = report[name]
            actual = "unavailable" if item["actual"] is None else str(item["actual"])
            label.configure(text=f"Driver: {actual}; {item['status']}")

    def _job(self, work, success, message="Applying camera settings..."):
        if self.pending or self.app._closing:
            return
        self._cancel_live()
        self.pending = True
        for control in [self.done, *self.controls]:
            control.configure(state="disabled")
        self.notice.configure(text=message)
        def finish(value, failed=False):
            self.pending = False
            if self.app._closing or not self.winfo_exists():
                return
            for control in [self.done, *self.controls]:
                control.configure(state="normal")
            if failed:
                if self.alignment_cancel.is_set() or "alignment" in message.lower() or "cradle" in message.lower():
                    self.alignment_ready = False
                self.notice.configure(text="Operation failed: " + str(value))
            else:
                success(value)
            if not self.winfo_exists():
                return
            self._manual_states()
            self._alignment_states()
        try:
            self.app._jobs.submit(work, lambda value: finish(value), lambda error: finish(error, True))
        except Exception as exc:
            finish(str(exc), True)

    def apply(self, save=False):
        if self.pending or not self.app._camera_tuning_allowed():
            return
        try:
            camera = self._values()
        except ValueError as exc:
            self.notice.configure(text=str(exc))
            return
        self.app._diagnostic_view = None
        self.app.setup_inspected.set(False)
        def applied(report):
            self._live_last = camera
            self.fill(self.app.station.settings.camera)
            self.show_report(report["properties"])
            self.notice.configure(text="Defaults saved. Inspect driver readback." if save else
                                  "Applied. Inspect readback; Save to remember.")
            self.app._log("[CAMERA] " + ("Defaults saved." if save else "Preview settings applied."))
        self._job(lambda: self.app.station.apply_camera_controls(camera, save=save), applied)

    def restore(self):
        self._job(self.app.station.store.load, lambda settings: (
            self.fill(settings.camera), self.notice.configure(text="Saved values loaded. Apply to preview to use them.")))

    def close(self):
        if self.pending:
            return
        dirty = self._live_dirty
        self._cancel_live()
        if dirty:
            try:
                camera = self._values()
            except ValueError:
                camera = None  # Leave the last valid applied values on an incomplete edit.
        else:
            camera = None
        self.alignment_ready = False
        if self._live_busy or camera is not None or self.app.station._camera_alignment_boards is not None:
            def finish():
                if camera is not None:
                    self.app.station.apply_camera_controls(camera, live_preview=True)
                self.app.station.finish_camera_alignment()
            self._job(finish, lambda _: self._destroy(), "Finishing camera preview and holding conveyor...")
            return
        self._destroy()

    def _destroy(self):
        self._cancel_live()
        self.app._camera_panel = None
        self.destroy()
        self.app._set_session_active_state(False)
