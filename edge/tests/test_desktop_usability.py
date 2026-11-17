"""TASK-NEW-EDGE-DIM-USABILITY-03: glare, contrast, modal reachability and clear daily flow."""
from types import SimpleNamespace
import customtkinter as ctk
import pytest
from test_camera_preview_ui import preview_app, hidden_ui
from test_desktop_layout import contained, check_readable, luminance, color
from test_live_camera_ui import pump
from operator_helpers import select_staff
from src.core.batches import new_batch_record
from src.ui.theme import FUTheme as T


def descendants(parent):
    for child in parent.winfo_children():
        yield child
        yield from descendants(child)


def station_preview(tmp_path):
    app, _, _ = preview_app(tmp_path)
    app.inference_worker.engine = SimpleNamespace(engine_type="ONNX", model_contract_verified=True, warmup_complete=True)
    select_staff(app, "Hatchery Operator " + "Long surname " * 5)
    record = new_batch_record("KAYUMANGGI", "North incubator", 100, "2026-01-01", batch_code="BATCH-KAY-" + "LONG" * 8)
    app.db.save_local_batch(record, app.device_id, app.operator_name, app.operator_id)
    app._apply_batch_selection(record, app.operator_name, 100)
    app.sync_worker.fetch_operators = lambda: app.db.get_operator_state()
    app.sync_worker.fetch_active_batches = lambda: app.db.list_available_batches()
    return app


def open_surface(app, kind):
    before = set(app.winfo_children())
    if kind == "batch":
        app.open_batch_setup_dialog()
        pump(app, lambda: app._batch_setup_window.loaded)
    elif kind == "preparation":
        app.open_preparation_confirmation()
    elif kind == "settings":
        app.open_calibration_dialog()
    elif kind == "end":
        app.open_end_session_modal()
    elif kind == "summary":
        app._show_session_summary(dict(batch_id=app.current_batch_code, stage="DAY_10", operator_name=app.operator_name,
            session_id=None, total_scanned=12, fertile_count=8, infertile_count=3, manual_review_count=1,
            duration_seconds=60, eggs_per_minute=12, ended_at="2026-11-17T00:00:00Z"))
    elif kind == "guide":
        app.open_onboarding_guide()
    elif kind == "history":
        app.open_scan_history_modal()
    elif kind == "exit":
        app.confirm_exit_dialog()
    elif kind == "jam":
        app._show_jam_alert_modal()
    app.update()
    if kind == "history":
        pump(app, lambda: any(isinstance(w, ctk.CTkLabel) and str(w.cget("text")).startswith("No scans found") for w in descendants(app)))
    return next(child for child in app.winfo_children() if child not in before and isinstance(child, ctk.CTkToplevel))


def test_dim_palette_has_readable_text_controls_and_focus():
    def rgb(value):
        return tuple(int(value[n:n+2], 16)/255 for n in (1, 3, 5))
    def ratio(first, second):
        high, low = sorted([luminance(rgb(first)), luminance(rgb(second))], reverse=True)
        return (high+.05)/(low+.05)
    assert luminance(rgb(T.PANEL_LIGHT)) < .08
    assert T.PRIMARY_MAROON == "#800000" and T.FERTILE_GREEN == "#357a38" and T.REJECT_RED == "#DC2626"
    for surface in (T.BG_LIGHT, T.PANEL_LIGHT, T.PANEL_LIGHT_ALT, T.INPUT_BG, T.SELECTION_BG, T.PANEL_ACCENT):
        for ink in (T.TEXT_PRIMARY, T.TEXT_SECONDARY, T.TEXT_MUTED):
            assert ratio(ink, surface) >= 4.5, (ink, surface)
    for surface in (T.PANEL_LIGHT, T.INPUT_BG, T.PANEL_LIGHT_ALT):
        assert ratio(T.BORDER_CONTROL, surface) >= 3
        assert ratio(T.FOCUS, surface) >= 3
    for ink, surface in ((T.FERTILE_GREEN_TEXT, T.FERTILE_GREEN_CARD), (T.INFERTILE_AMBER_TEXT, T.INFERTILE_AMBER_CARD), (T.REJECT_RED_TEXT, T.REJECT_RED_CARD)):
        assert ratio(ink, surface) >= 4.5


@pytest.mark.parametrize("size", ["1024x720", "1280x860"])
def test_operator_dialogs_keep_actions_and_text_usable_at_supported_sizes(hidden_ui, tmp_path, size):
    app = station_preview(tmp_path)
    errors = []
    app.report_callback_exception = lambda *args: errors.append(args)
    try:
        app.geometry(size)
        app.deiconify()
        app.update()
        assert app.settings_btn.cget("text") == "Settings"
        assert "Step 2" in app.flow_label.cget("text")
        assert app.cycle_status_label.cget("text") == "Inspect the empty station"
        assert "Choose an operator" not in app.cycle_detail_label.cget("text")
        app._station_prepared = True
        app._set_session_active_state(False)
        assert app.cycle_status_label.cget("text") == "Ready to start sorting"
        app._station_prepared = False
        app._set_session_active_state(False)
        contained(app.more_btn, app)
        for kind in ("batch", "preparation", "end", "summary", "guide", "history", "exit", "jam", "settings"):
            dialog = open_surface(app, kind)
            assert dialog.winfo_width() >= 640, kind
            contained(dialog, app)
            if kind == "batch":
                dialog.mode.set("Create batch")
                dialog.change_mode("Create batch")
                assert dialog.target.winfo_ismapped()
                contained(dialog.target, dialog)
            if kind == "preparation":
                dialog.confirm_button.invoke()
                assert "Confirm the inspection" in dialog.notice.cget("text")
                assert not app._setup_busy
                check = next(w for w in descendants(dialog) if isinstance(w, ctk.CTkCheckBox))
                check._canvas.focus_force()
                check._canvas.event_generate("<space>")
                app.update()
                assert dialog.inspected.get()
                assert not app._setup_busy
            if kind == "settings":
                for section in dialog.sections:
                    dialog._show_section(section)
                    app.update()
                    check_readable(dialog)
                dialog._show_section("Connections")
            dialog.geometry("%dx%d" % tuple(map(int, dialog.tk.call("wm", "minsize", dialog._w))))
            app.update()
            fixed = []
            for button in descendants(dialog):
                if not isinstance(button, ctk.CTkButton):
                    continue
                parent = button.master
                while parent is not dialog and not isinstance(parent, ctk.CTkScrollableFrame):
                    parent = parent.master
                if parent is dialog and button.winfo_ismapped():
                    fixed.append(button)
                    contained(button, dialog)
                    assert button.cget("height") >= 36
                    if button.cget("fg_color") in {T.PRIMARY_MAROON, T.REJECT_RED, T.REJECT_RED_BG, T.FERTILE_GREEN}:
                        assert button.cget("height") >= 44
            assert fixed, kind
            check_readable(dialog)
            dialog.destroy()
            app.update()
        assert not app.is_auto_cycle_running and not app._setup_busy
        assert not errors
    finally:
        app.shutdown()
        app.mainloop()
