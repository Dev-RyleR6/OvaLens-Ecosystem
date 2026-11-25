"""Registered staff attribution and explicit, cancellable preparation entry."""
import queue
import customtkinter as ctk
from .theme import FUTheme as T, fit_caption
from .desktop_style import finish_dialog_layout


class GuidedSetupFlow:
    def _apply_operator_state(self, state):
        if not isinstance(state, dict) or self.current_session_id or self._closing:
            return
        selected = next((r for r in state["operators"] if r["user_id"] == state["selected_id"]), None)
        self.operator_id = selected["user_id"] if selected else None
        self.operator_name = selected["full_name"] if selected else "Choose operator"
        if hasattr(self, "operator_label"):
            self.operator_label.configure(text=fit_caption("Operator: " + self.operator_name,
                self._operator_caption_font.measure, 240))
        self._operator_roster_loaded = bool(state.get("downloaded_at"))
        self._set_session_active_state(self.is_session_active)

    def refresh_registered_operators(self):
        if self._closing or getattr(self, "_operator_refresh_busy", False):
            return
        self._operator_refresh_busy = True
        def done(state=None, error=None):
            self._operator_refresh_busy = False
            if self._closing:
                return
            self._operator_roster_error = error
            if state is not None:
                self._apply_operator_state(state)
            window = getattr(self, "_batch_setup_window", None)
            if window is not None and window.winfo_exists():
                if state is not None:
                    window.refresh_operators(state)
                window.operator_status.configure(text="Roster refresh failed. Cached staff remain available. Check the backend connection and station API key."
                                                  if error else "Registered staff refreshed. Available offline.")
        try:
            self._jobs.submit(self.sync_worker.fetch_operators, done,
                              lambda error: done(error="Roster refresh failed. Cached staff remain available. " + str(error)))
        except (AttributeError, queue.Full, RuntimeError) as exc:
            done(error="Roster refresh failed. Cached staff remain available. " + str(exc))

    def open_preparation_confirmation(self):
        if self._closing or self._stopping or self.current_session_id or self.grab_current() is not None:
            return
        if not self._batch_record_ready or not self.operator_id:
            self.open_batch_setup_dialog()
            return
        if self.station.settings.rig_profile == "dual_v2":
            self.setup_notice.configure(text="Prepare the saved two-board profile in Settings, then Start sorting.")
            return
        dialog = ctk.CTkToplevel(self)
        self._preparation_window = dialog
        dialog.title("Prepare station")
        height = min(560, self.winfo_screenheight() - 80)
        dialog.geometry(f"680x{height}")
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(fg_color=T.BG_LIGHT)
        self._center_window(dialog, 680, height)
        actions = ctk.CTkFrame(dialog, fg_color="transparent")
        actions.pack(side="bottom", fill="x", padx=40, pady=(12, 24))
        body = ctk.CTkScrollableFrame(dialog, fg_color=T.PANEL_LIGHT)
        body.pack(fill="both", expand=True, padx=20, pady=20)
        ctk.CTkLabel(body, text="Inspect the empty station", font=(T.FONT_FAMILY, 20, "bold"),
                     text_color=T.TEXT_PRIMARY).pack(anchor="w", padx=20, pady=(20, 8))
        ctk.CTkLabel(body, text=f"{self.current_batch_code}\nOperator: {self.operator_name}\nRun target: {self.target_egg_count:,} scans",
                     wraplength=460, justify="left", anchor="w", text_color=T.TEXT_PRIMARY).pack(fill="x", padx=20)
        ctk.CTkLabel(body, text="Connection may reset controllers and position the gate. Keep the belt empty. Sorting starts only after a separate Start sorting action.",
                     wraplength=460, justify="left", text_color=T.TEXT_SECONDARY).pack(fill="x", padx=20, pady=12)
        inspected = ctk.BooleanVar(master=dialog, value=False)
        check = ctk.CTkCheckBox(body, text="Conveyor empty and aligned; gate checked", variable=inspected,
                              text_color=T.TEXT_PRIMARY)
        check.pack(anchor="w", padx=20, pady=8)
        notice = ctk.CTkLabel(body, text="", text_color=T.REJECT_RED_TEXT)
        notice.pack(fill="x", padx=20)

        generation = self._operation_generation
        intent = object()
        self._preparation_intent = intent
        def cancel():
            if self._preparation_intent is intent:
                self._preparation_intent = None
            self._animate_modal_close(dialog)
        def confirm():
            if not inspected.get():
                notice.configure(text="Confirm the inspection before preparation.")
                return
            button.configure(state="disabled")
            def prepare():
                if self._closing or generation != self._operation_generation or self._preparation_intent is not intent:
                    return
                self._preparation_intent = None
                self.setup_inspected.set(True)
                self.prepare_station()
            # CTk destruction flushes idle callbacks before releasing the grab.
            # A timer runs after destruction, so preparation sees no modal grab.
            self._animate_modal_close(dialog, on_close=lambda: self.after(0, prepare))
        cancel_button = ctk.CTkButton(actions, text="Cancel", height=44, fg_color=T.PANEL_LIGHT_ALT,
                                     text_color=T.TEXT_PRIMARY, command=cancel, text_color_disabled=T.TEXT_MUTED, border_color=T.BORDER_CONTROL, border_width=1)
        cancel_button.pack(side="left")
        button = ctk.CTkButton(actions, text="Prepare station", height=44, fg_color=T.PRIMARY_MAROON,
                              hover_color=T.HOVER_MAROON, command=confirm)
        button.pack(side="right")
        dialog.inspected, dialog.confirm_button, dialog.notice = inspected, button, notice
        dialog.cancel_button = cancel_button
        dialog.protocol("WM_DELETE_WINDOW", cancel)
        finish_dialog_layout(dialog)
