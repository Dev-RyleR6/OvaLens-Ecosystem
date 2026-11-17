"""TASK-NEW-EDGE-SOFT-DESKTOP-01: native layout, disclosure and readable controls."""
import tkinter as tk
from tkinter import ttk

import customtkinter as ctk
import pytest

from test_camera_preview_ui import preview_app
from test_startup_config import hidden_ui
from src.core.batches import new_batch_record
from src.ui.select_field import SelectField, STYLE


def bounds(widget):
    x, y = widget.winfo_rootx(), widget.winfo_rooty()
    return x, y, x + widget.winfo_width(), y + widget.winfo_height()


def contained(widget, container):
    x, y, right, bottom = bounds(widget)
    cx, cy, cright, cbottom = bounds(container)
    assert cx <= x < right <= cright, (widget, bounds(widget), bounds(container))
    assert cy <= y < bottom <= cbottom, (widget, bounds(widget), bounds(container))


@pytest.mark.parametrize("size", ["1024x720", "1280x860"])
def test_primary_controls_and_camera_survive_disclosure_and_review(hidden_ui, tmp_path, size):
    app, _, _ = preview_app(tmp_path)
    errors = []
    app.report_callback_exception = lambda *args: errors.append(args)
    try:
        app.geometry(size)
        app.deiconify()
        app.update()
        record = new_batch_record("KAYUMANGGI", "North incubator", 100, "2026-11-03",
                                  batch_code="W" * 48)
        app._apply_batch_selection(record, "W" * 100, 100)
        app.refresh_readiness(force=True)
        app.update_idletasks()
        for control in (app.batch_btn, app.help_btn, app.kiosk_btn, app.settings_btn,
                        app.session_btn, app.eject_btn, app.light_btn, app.readiness_panel.details):
            assert control.winfo_ismapped()
            contained(control, app)
        assert bounds(app.batch_btn)[2] < bounds(app.header_actions)[0]
        assert app._batch_caption_font.measure(app.batch_btn.cget("text")) <= 216
        assert app._operator_caption_font.measure(app.operator_label.cget("text")) <= 240
        stop_position = bounds(app.eject_btn)
        assert app.video_container.winfo_width() > app.right_panel.winfo_width()
        assert app.video_container.winfo_height() > 200
        assert app.history_btn.winfo_ismapped()
        assert app.log_textbox.winfo_height() >= 32
        app.readiness_panel.details.invoke()
        app.update_idletasks()
        assert app.readiness_panel.body.winfo_ismapped()
        assert bounds(app.eject_btn) == stop_position
        contained(app.readiness_panel.details, app.right_panel)
        app.readiness_panel.details.invoke()
        app.update_idletasks()
        assert not app.readiness_panel.body.winfo_ismapped()
        assert app.history_btn.winfo_ismapped()
        app.current_session_id = "layout-review"
        app.is_auto_cycle_running = True
        app._set_session_active_state(True)
        app.refresh_readiness(force=True)
        app.review_row.pack(fill="x", padx=12, pady=(0, 8))
        app._update_result_banner("INFERTILE", .94, "MANUAL_REVIEW", 15)
        app._update_cycle_hud("", "#875A12", "Review this egg",
                              detail="Keep the egg in place. Confirm its classification below.")
        app.update_idletasks()
        assert bounds(app.eject_btn) == stop_position
        for control in (app.session_btn, app.eject_btn, app.history_btn, *app.review_buttons):
            assert control.winfo_ismapped()
            contained(control, app)
        contained(app.result_title, app.result_banner)
        contained(app.result_subtitle, app.result_banner)
        contained(app.cycle_detail_label, app.cycle_hud)
        assert app.video_container.winfo_height() > 200
        assert app.log_textbox.winfo_height() >= 32
        assert not errors
    finally:
        app.current_session_id = None
        app.is_auto_cycle_running = False
        app.shutdown()
        app.mainloop()


def color(widget, value):
    if isinstance(value, (tuple, list)):
        value = value[0]  # The operator workspace uses the light appearance.
    if value == "transparent":
        return background(widget.master)
    return tuple(v / 65535 for v in widget.winfo_rgb(value))


def background(widget):
    while widget is not None:
        try:
            value = widget.cget("fg_color")
        except (ValueError, AttributeError, tk.TclError):
            widget = widget.master
            continue
        if value != "transparent":
            return color(widget, value)
        widget = widget.master
    raise AssertionError("No native surface color")


def luminance(rgb):
    values = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in rgb]
    return sum(c * weight for c, weight in zip(values, (.2126, .7152, .0722)))


def check_readable(root):
    for widget in root.winfo_children():
        if not widget.winfo_ismapped():
            continue
        if isinstance(widget, (ctk.CTkButton, ctk.CTkLabel, ctk.CTkOptionMenu, SelectField)):
            text = widget.get() if isinstance(widget, (ctk.CTkOptionMenu, SelectField)) else widget.cget("text")
            if text and not (isinstance(widget, ctk.CTkButton) and widget.cget("state") == "disabled"):
                if isinstance(widget, SelectField):
                    style = ttk.Style(widget)
                    state = widget._combo.state()
                    foreground = luminance(color(widget, style.lookup(STYLE, 'foreground', state)))
                    surface = luminance(color(widget, style.lookup(STYLE, 'fieldbackground', state)))
                else:
                    foreground = luminance(color(widget, widget.cget("text_color")))
                    surface = luminance(background(widget))
                ratio = (max(foreground, surface) + .05) / (min(foreground, surface) + .05)
                assert ratio >= 4.5, (text, ratio)
        check_readable(widget)


def test_light_workspace_and_camera_controls_keep_text_readable(hidden_ui, tmp_path):
    app, _, _ = preview_app(tmp_path)
    try:
        app.geometry("1024x720")
        app.deiconify()
        app.update()
        check_readable(app)
        app.open_camera_controls()
        app.update()
        check_readable(app)
        panel = app._camera_panel
        for button in (panel.done, *panel.camera_actions.winfo_children()):
            if isinstance(button, ctk.CTkButton) and button.winfo_ismapped():
                contained(button, app.right_panel)
        app._camera_panel.close()
        app.update_idletasks()
    finally:
        app.shutdown()
        app.mainloop()


@pytest.mark.parametrize("size", ["1024x720", "1280x860"])
def test_settings_sections_preserve_edits_and_fixed_safe_actions(hidden_ui, tmp_path, size):
    from src.ui.station_settings import StationSettingsWindow
    app, _, _ = preview_app(tmp_path)
    try:
        app.geometry(size)
        app.deiconify()
        app.update()
        window = StationSettingsWindow(app)
        window.update()
        stop_position = bounds(window.stop_button)
        window.entries["conveyor_port"].delete(0, "end")
        window.entries["conveyor_port"].insert(0, "COM42")
        for section in window.sections:
            window.section_buttons[section].invoke()
            window.update()
            assert window.active_section == section
            assert window.sections[section].winfo_ismapped()
            contained(window.section_buttons[section], window)
            for action in window.actions.winfo_children():
                if isinstance(action, ctk.CTkButton):
                    assert action.winfo_ismapped()
                    contained(action, window)
            assert bounds(window.stop_button) == stop_position
            check_readable(window)
        assert window.entries["conveyor_port"].get() == "COM42"
        assert window._values().conveyor_port == "COM42"
        window.pending = True
        window.done_button.invoke()
        assert window.winfo_exists()
        assert "Wait" in window.notice.cget("text")
        window.pending = False
        window.done_button.invoke()
        app.update()
        assert not window.winfo_exists()
    finally:
        app.shutdown()
        app.mainloop()


def test_settings_keyboard_navigation_and_disabled_actions(hidden_ui, tmp_path):
    from unittest.mock import Mock
    from src.ui.station_settings import StationSettingsWindow
    from src.ui.theme import FUTheme
    app, _, _ = preview_app(tmp_path)
    try:
        app.deiconify()
        app.update()
        window = StationSettingsWindow(app)
        window.update()
        camera = window.section_buttons["Camera"]
        camera._canvas.focus_force()
        camera._canvas.event_generate("<Return>")
        window.update()
        assert window.active_section == "Camera"
        assert camera._canvas.cget("highlightcolor") == FUTheme.PRIMARY_MAROON
        assert int(camera._canvas.cget("highlightthickness")) == 2
        # Tk lazily loads traversal procedures; load before querying directly.
        window.tk.call("auto_load", "tk_focusNext")
        assert str(window.tk.call("tk_focusNext", str(camera._canvas))) == str(window.section_buttons["Detection"]._canvas)
        apply = window.buttons[-3]
        callback = Mock()
        apply.configure(command=callback)
        apply._canvas.focus_force()
        apply._canvas.event_generate("<space>")
        window.update()
        callback.assert_called_once()
        apply.configure(state="disabled")
        apply._canvas.event_generate("<Return>")
        window.update()
        callback.assert_called_once()
        assert not app.inference_worker.submit.called
        window._show_section("Maintenance")
        window.update()
        last = next(b for b in window.buttons if b.cget("text") == "Hold hardware pause")
        last._canvas.focus_force()
        window.update()
        canvas = last.master._parent_canvas
        assert canvas.canvasy(0) > 0
        assert last.winfo_rooty() >= canvas.winfo_rooty()
        assert last.winfo_rooty() + last.winfo_height() <= canvas.winfo_rooty() + canvas.winfo_height()
        window._close()
    finally:
        app.shutdown()
        app.mainloop()
