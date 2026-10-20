"""Inline daily preparation checklist; all device/storage work stays off Tk."""
import queue
import threading
import time

import customtkinter as ctk

from .theme import FUTheme


class StationReadinessPanel(ctk.CTkFrame):
    def __init__(self, app):
        super().__init__(app.right_panel, fg_color=FUTheme.PANEL_LIGHT, corner_radius=12)
        self.app = app
        ctk.CTkLabel(self, text="Station readiness", anchor="w",
            font=(FUTheme.FONT_FAMILY, 19, "bold")).pack(fill="x", padx=20, pady=(18, 4))
        self.summary = ctk.CTkLabel(self, text="Choose batch → Prepare station → Start sorting",
            anchor="w", justify="left", wraplength=350, font=(FUTheme.FONT_FAMILY, 13),
            text_color=FUTheme.TEXT_SECONDARY)
        self.summary.pack(fill="x", padx=20, pady=(0, 10))
        body = ctk.CTkScrollableFrame(self, fg_color="transparent", height=1)
        body.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        self.labels = {}
        for key, title in (("batch", "Batch"), ("settings", "Saved configuration"),
                           ("camera", "Camera"), ("model", "Classification model"),
                           ("storage", "Local scan storage"), ("stepper", "Stepper controller"),
                           ("gate", "Sorting gate and IR"), ("light", "Light controller"), ("sync", "Backend sync")):
            row = ctk.CTkFrame(body, fg_color="transparent")
            row.pack(fill="x", pady=(3, 7))
            ctk.CTkLabel(row, text=title, anchor="w", font=(FUTheme.FONT_FAMILY, 14, "bold")).pack(fill="x")
            value = ctk.CTkLabel(row, text="Checking", anchor="w", justify="left", wraplength=320,
                font=(FUTheme.FONT_FAMILY, 12), text_color=FUTheme.TEXT_SECONDARY)
            value.pack(fill="x")
            self.labels[key] = value
        self.retry = ctk.CTkButton(self, text="Recheck software", height=34,
            fg_color=FUTheme.PANEL_LIGHT_ALT, border_width=1, border_color=FUTheme.BORDER,
            hover_color=FUTheme.PANEL_ACCENT, command=app.run_software_checks)
        self.retry.pack(fill="x", padx=20, pady=(0, 10))
        ctk.CTkLabel(body, text="Controller checks confirm communication. Inspect the belt, gate and lamp before preparing.",
            anchor="w", justify="left", wraplength=350, font=(FUTheme.FONT_FAMILY, 12),
            text_color=FUTheme.TEXT_MUTED).pack(fill="x", pady=(8, 14))
        self._signature = None

    def render(self, rows, ready, busy):
        app = self.app
        batch_ready = bool(getattr(app, "_batch_record_ready", False))
        online = bool(getattr(app.sync_worker, "is_online", False))
        error = getattr(app.sync_worker, "last_error", None)
        values = [(r.key, r.state + " · " + r.detail, r.state) for r in rows]
        values += [("batch", app.current_batch_code if batch_ready else "Choose or create a batch in Batch setup", "Ready" if batch_ready else "Not checked"),
                   ("sync", "Online" if online and not error else "Offline / pending sync — scans stay saved locally", "Ready" if online and not error else "Warning")]
        signature = tuple(values), ready, busy, batch_ready, getattr(app.station.readiness, "reason", "")
        if signature == self._signature:
            return
        self._signature = signature
        for key, text, state in values:
            self.labels[key].configure(text=text, text_color=FUTheme.INFERTILE_AMBER
                if state in {"Needs attention", "Warning"} else FUTheme.TEXT_SECONDARY)
        first_error = next((r.detail for r in rows if r.state == "Needs attention"), "")
        self.summary.configure(text="Checking station. Keep the conveyor empty." if busy else
            "Ready — press Start sorting when ready to feed eggs." if ready and batch_ready else first_error or app.station.readiness.reason)
        self.retry.configure(state="disabled" if busy else "normal")


class ReadinessFlow:
    def run_software_checks(self):
        if (not self.station or getattr(self, "_software_check_busy", False) or self._closing
                or self._stopping or self.current_session_id or getattr(self, "_setup_busy", False)
                or self._scan_busy or getattr(self, "_camera_panel", None) is not None):
            return
        self._software_check_busy = True
        def finished(result):
            self._software_check_busy = False
            if not self._closing:
                self.refresh_readiness(force=True)
        try:
            self._jobs.submit(self.station.readiness.software_checks, finished, finished)
        except (queue.Full, RuntimeError) as exc:
            finished(str(exc))

    def refresh_readiness(self, force=False):
        panel = getattr(self, "readiness_panel", None)
        if panel is None:
            return
        visible = (not self.simulation and not self.current_session_id and not self._scan_busy
                   and not self._closing and not getattr(self, "_batch_complete", False)
                   and getattr(self, "_camera_panel", None) is None and getattr(self, "_diagnostic_view", None) is None)
        if visible != getattr(self, "_readiness_visible", None):
            self._readiness_visible = visible
            if visible:
                panel.place(x=0, y=0, relwidth=1, relheight=1)
                panel.lift()
            else:
                panel.place_forget()
        if not visible:
            return
        now = time.monotonic()
        if not force and now < getattr(self, "_next_readiness_refresh", 0):
            return
        self._next_readiness_refresh = now + .25
        readiness = self.station.readiness
        # A once-ready station cannot become ready again without explicit preparation.
        was_ready = getattr(self, "_station_prepared", False)
        dual = self.station.settings.rig_profile == "dual_v2"
        self._station_prepared = (self.station.calibrated if dual else readiness.ready) if not getattr(self, "_setup_busy", False) else False
        if was_ready and not self._station_prepared:
            self.setup_inspected.set(False)
            self.setup_notice.configure(text=readiness.reason)
            self._update_cycle_hud("", FUTheme.INFERTILE_AMBER, "Check station", detail=readiness.reason)
        if was_ready != self._station_prepared:
            self.iot_status_badge.configure(text="SORTER: READY" if self._station_prepared else "SORTER: SETUP NEEDED",
                text_color=FUTheme.FERTILE_GREEN_TEXT if self._station_prepared else FUTheme.INFERTILE_AMBER)
        panel.render(readiness.rows(), self._station_prepared,
                     getattr(self, "_setup_busy", False) or getattr(self, "_software_check_busy", False))

    def prepare_station(self):
        if (not self.station or self.simulation or self._closing or self._stopping or self._scan_busy
                or self.current_session_id or self.grab_current() is not None or self._finalization_failed
                or self._pending_finalization_id is not None or self.inference_worker.busy
                or getattr(self, "_setup_busy", False) or getattr(self, "_light_busy", False)
                or getattr(self, "_camera_panel", None) is not None):
            return
        if not getattr(self, "_batch_record_ready", False):
            self.setup_notice.configure(text="Choose or create a batch first.")
            self.open_batch_setup_dialog()
            return
        if not self.setup_inspected.get():
            self.setup_notice.configure(text="Confirm the conveyor is empty, aligned and the gate checked.")
            return
        if self.station.settings.rig_profile != "three_v3":
            self.setup_notice.configure(text="Prepare the saved two-board profile in Tools / Settings.")
            return
        from ..core.operator_flow import validate_batch_config
        try:
            validate_batch_config(self.current_batch_id, self.operator_name, self.target_egg_count, self.current_stage)
        except ValueError as exc:
            self.setup_notice.configure(text=str(exc))
            return
        self._submit_station_request(start=False)

    def _submit_station_request(self, start=False, args=None):
        request = {"generation": self._operation_generation, "cancel": threading.Event()}
        self._setup_request = request
        self._setup_busy = True
        self._station_prepared = False
        self.setup_inspected.set(False)
        self._diagnostic_view = None
        title = "Starting sorting" if start else "Preparing station"
        self.setup_notice.configure(text=title + ". Keep the conveyor empty; STOP remains available.")
        self._update_cycle_hud("", FUTheme.TEXT_PRIMARY, title, detail="Keep the conveyor empty.")
        self._set_session_active_state(False)
        def progress(message):
            def show():
                if (self._setup_request is request and not request["cancel"].is_set()
                        and request["generation"] == self._operation_generation and not self._closing):
                    self.setup_notice.configure(text=message)
                    self._update_cycle_hud("", FUTheme.TEXT_PRIMARY, title, detail=message)
            self._ui_events.put(show)
        def finish(result=None, error=None):
            if self._setup_request is not request:
                return
            self._setup_busy = False
            self._setup_request = None
            if self._closing:
                return
            if request["cancel"].is_set() or request["generation"] != self._operation_generation:
                self.station.halt()
                self.setup_notice.configure(text="Preparation cancelled. Inspect and prepare again.")
            elif error:
                self.setup_notice.configure(text=str(error))
                self._update_cycle_hud("", FUTheme.INFERTILE_AMBER, "Check station", detail=str(error))
                self._log("[READINESS] " + str(error))
            elif start:
                self._activate_cycle(result)
            else:
                self._station_prepared = self.station.readiness.ready
                self.setup_inspected.set(self._station_prepared)
                self.setup_notice.configure(text=self.station.readiness.reason)
                self._update_cycle_hud("", FUTheme.TEXT_PRIMARY, "Station ready", detail="Press Start sorting when ready to feed eggs.")
                self.iot_status_badge.configure(text="SORTER: READY", text_color=FUTheme.FERTILE_GREEN_TEXT)
            self.refresh_readiness(force=True)
            self._set_session_active_state(self.is_session_active)
        def work():
            if start:
                return self.station.readiness.start(*args, request["cancel"])
            return self.station.readiness.prepare(True, request["cancel"], progress,
                                                 batch_id=self.current_batch_id, target=self.target_egg_count)
        try:
            self._jobs.submit(work, finish, lambda error: finish(error=error))
        except (queue.Full, RuntimeError) as exc:
            finish(error=str(exc))
