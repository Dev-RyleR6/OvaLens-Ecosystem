"""Idle camera tuning alongside the main preview, using background requests."""
import customtkinter as ctk

from ..core.camera_controls import (AUTO_CONTROLS, NUMERIC_CONTROLS, MANUAL_PAIRS,
                                    camera_values, exposure_modes, mode_label)
from .theme import FUTheme


class CameraControlsPanel(ctk.CTkFrame):
    def __init__(self, app):
        super().__init__(app.right_panel, fg_color=FUTheme.PANEL_LIGHT, corner_radius=12,
                         border_width=1, border_color=FUTheme.BORDER)
        self.app = app
        self.pending = False
        self.entries, self.modes, self.readbacks, self.controls = {}, {}, {}, []
        self.base = app.station.settings.camera
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=18, pady=(16, 4))
        self.done = ctk.CTkButton(header, text="Done", width=65, height=34,
            font=(FUTheme.FONT_FAMILY, 13), fg_color=FUTheme.PANEL_LIGHT_ALT,
            hover_color=FUTheme.PANEL_ACCENT, command=self.close)
        self.done.pack(side="right")
        ctk.CTkLabel(header, text="Camera controls", font=(FUTheme.FONT_FAMILY, 20, "bold"),
                     text_color=FUTheme.TEXT_PRIMARY).pack(side="left")
        ctk.CTkLabel(self, text="Adjust while watching the preview. Blank values leave the camera unchanged.",
            wraplength=340, justify="left", anchor="w", font=(FUTheme.FONT_FAMILY, 13),
            text_color=FUTheme.TEXT_SECONDARY).pack(fill="x", padx=18, pady=(0, 8))
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(side="bottom", fill="x", padx=18, pady=(4, 14))
        actions.grid_columnconfigure((0, 1), weight=1)
        for column, (label, save) in enumerate((("Apply to preview", False), ("Save as default", True))):
            button = ctk.CTkButton(actions, text=label, height=38, width=155,
                font=(FUTheme.FONT_FAMILY, 13, "bold"),
                fg_color=FUTheme.PRIMARY_MAROON if not save else FUTheme.PANEL_LIGHT_ALT,
                hover_color=FUTheme.HOVER_MAROON if not save else FUTheme.PANEL_ACCENT,
                border_width=0 if not save else 1, border_color=FUTheme.BORDER,
                command=lambda save=save: self.apply(save))
            button.grid(row=0, column=column, padx=3, pady=4, sticky="ew")
            self.controls.append(button)
        restore = ctk.CTkButton(actions, text="Load saved settings", height=34,
            font=(FUTheme.FONT_FAMILY, 13), fg_color=FUTheme.PANEL_LIGHT_ALT,
            hover_color=FUTheme.PANEL_ACCENT, command=self.restore)
        restore.grid(row=1, column=0, columnspan=2, sticky="ew", padx=3, pady=4)
        self.controls.append(restore)
        self.notice = ctk.CTkLabel(self, text="Apply first to inspect the result. Save when satisfied.",
            font=(FUTheme.FONT_FAMILY, 12), text_color=FUTheme.TEXT_SECONDARY,
            wraplength=340, justify="left", anchor="w")
        self.notice.pack(side="bottom", fill="x", padx=20, pady=6)
        body = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
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
                    button_hover_color=FUTheme.BORDER_DARK, command=lambda _: self._manual_states())
                self.modes[name] = control
            else:
                control = ctk.CTkEntry(row, width=140, height=34, font=(FUTheme.FONT_FAMILY, 13),
                    fg_color=FUTheme.BG_LIGHT, border_color=FUTheme.BORDER_DARK,
                    placeholder_text="Leave unchanged")
                self.entries[name] = control
            control.pack(side="right")
            self.controls.append(control)
        ctk.CTkLabel(body, text="Numeric controls use camera-driver units. Turn an automatic mode Off before tuning its manual value.",
            wraplength=320, justify="left", font=(FUTheme.FONT_FAMILY, 12),
            text_color=FUTheme.TEXT_MUTED).pack(fill="x", padx=6, pady=10)
        self.fill(self.base)
        self.show_report(getattr(app.camera, "property_report", {}))
        self.place(x=0, y=0, relwidth=1, relheight=1)
        self.lift()

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
        for name, entry in self.entries.items():
            entry.configure(state="normal")
            entry.delete(0, "end")
            value = getattr(camera, name)
            entry.insert(0, "" if value is None else str(value))
        for name, menu in self.modes.items():
            values = self._exposure_modes() if name == "auto_exposure" else {"On": 1.0, "Off": 0.0}
            menu.set(mode_label(getattr(camera, name), values))
        self._manual_states()

    def _manual_states(self):
        for auto, manual in MANUAL_PAIRS.items():
            self.entries[manual].configure(state="disabled" if self.pending or self.modes[auto].get() == "On" else "normal")

    def show_report(self, report):
        for name, label in self.readbacks.items():
            if name not in report:
                continue
            item = report[name]
            actual = "unavailable" if item["actual"] is None else str(item["actual"])
            label.configure(text=f"Driver: {actual}; {item['status']}")

    def _job(self, work, success):
        if self.pending or self.app._closing:
            return
        self.pending = True
        for control in [self.done, *self.controls]:
            control.configure(state="disabled")
        self.notice.configure(text="Applying camera settings...")
        def finish(value, failed=False):
            self.pending = False
            if self.app._closing or not self.winfo_exists():
                return
            for control in [self.done, *self.controls]:
                control.configure(state="normal")
            if failed:
                self.notice.configure(text="Camera operation failed: " + str(value))
            else:
                success(value)
            self._manual_states()
        try:
            self.app._jobs.submit(work, lambda value: finish(value), lambda error: finish(error, True))
        except Exception as exc:
            finish(str(exc), True)

    def apply(self, save=False):
        if self.pending or not self.app._camera_tuning_allowed():
            return
        try:
            camera = camera_values(self.base, {k: e.get() for k, e in self.entries.items()},
                                   {k: m.get() for k, m in self.modes.items()}, self._exposure_modes())
        except ValueError as exc:
            self.notice.configure(text=str(exc))
            return
        self.app._diagnostic_view = None
        self.app.setup_inspected.set(False)
        def applied(report):
            self.fill(self.app.station.settings.camera)
            self.show_report(report["properties"])
            self.notice.configure(text="Saved as default. Inspect driver readback." if save else
                                  "Request completed. Inspect driver readback; save to keep these settings.")
            self.app._log("[CAMERA] " + ("Defaults saved." if save else "Preview settings applied."))
        self._job(lambda: self.app.station.apply_camera_controls(camera, save=save), applied)

    def restore(self):
        self._job(self.app.station.store.load, lambda settings: (
            self.fill(settings.camera), self.notice.configure(text="Saved values loaded. Apply to preview to use them.")))

    def close(self):
        if self.pending:
            return
        self.app._camera_panel = None
        self.destroy()
        self.app._set_session_active_state(False)
