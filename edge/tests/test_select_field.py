"""TASK-NEW-EDGE-SELECT-LAYOUT-01: native pickers never invent selection side effects."""
from types import SimpleNamespace
from unittest.mock import Mock
import sys
from tkinter import ttk

import customtkinter as ctk

from test_startup_config import hidden_ui
from test_camera_preview_ui import preview_app
from test_desktop_layout import contained, check_readable
from src.ui.select_field import SelectField, STYLE
from src.ui.station_settings import StationSettingsWindow
from src.ui.app import OvaLensOperatorApp


def test_picker_preserves_values_variables_callbacks_and_readonly_state(hidden_ui, tmp_path):
    app, _, _ = preview_app(tmp_path)
    try:
        variable = ctk.StringVar(master=app, value='Choose operator')
        command = Mock()
        field = SelectField(app, values=['On', 'Off'], variable=variable, command=command, width=140)
        field.place(x=24, y=120)
        app.deiconify()
        app.update()
        assert field.get() == 'Choose operator'
        variable.set('Saved value')
        assert field.get() == 'Saved value'
        field.set('Off')
        assert variable.get() == 'Off'
        field.configure(values=['On', 'Off', 'Unchanged'])
        assert field.get() == 'Off'
        command.assert_not_called()
        replacement = Mock()
        field.configure(command=replacement)
        field._combo.current(0)
        field._combo.event_generate('<<ComboboxSelected>>')
        app.update()
        replacement.assert_called_once_with('On')
        command.assert_not_called()
        field.configure(state='disabled')
        field._combo.event_generate('<<ComboboxSelected>>')
        app.update()
        assert replacement.call_count == 1
        field.configure(state='normal')
        assert str(field._combo.cget('state')) == 'readonly'
        assert field.winfo_width() == 140
        contained(field._combo, field)
        style = ttk.Style(app)
        assert style.lookup(STYLE, 'foreground', ('readonly',)) == field.cget('text_color')
        app.trigger_candling_scan = Mock()
        app.trigger_manual_eject = Mock()
        event = SimpleNamespace(widget=field._combo)
        OvaLensOperatorApp._scan_shortcut(app, event)
        OvaLensOperatorApp._stop_shortcut(app, event)
        app.trigger_candling_scan.assert_not_called()
        app.trigger_manual_eject.assert_not_called()
    finally:
        app.shutdown()
        app.mainloop()


def test_native_popup_is_bounded_and_scroll_does_not_move_setup_form(hidden_ui, tmp_path):
    app, _, _ = preview_app(tmp_path)
    errors = []
    app.report_callback_exception = lambda *args: errors.append(args)
    try:
        app.geometry('1024x720')
        body = ctk.CTkScrollableFrame(app, width=300, height=200)
        body.place(x=24, y=130)
        command = Mock()
        field = SelectField(body, values=[f'Station batch {n:03d}' for n in range(100)], command=command)
        field.pack(fill='x')
        for n in range(15):
            ctk.CTkLabel(body, text=f'Configuration row {n}').pack()
        app.deiconify()
        app.update()
        before = body._parent_canvas.yview()
        if sys.platform == 'win32':
            field._combo.event_generate('<MouseWheel>', delta=-120)
        else:
            field._combo.event_generate('<Button-5>')
        app.update()
        assert body._parent_canvas.yview() != before
        command.assert_not_called()
        body._parent_canvas.yview_moveto(0)
        app.update()
        before = body._parent_canvas.yview()
        field.focus_force()
        field._combo.event_generate('<Down>')
        app.update()
        def descendants(path):
            children = app.tk.splitlist(app.tk.call('winfo', 'children', path))
            return [child for name in children for child in [name, *descendants(name)]]
        popups = [name for name in descendants(str(field._combo))
                  if app.tk.call('winfo', 'class', name) == 'Listbox']
        assert len(popups) == 1
        popup = popups[0]
        assert app.tk.getboolean(app.tk.call('winfo', 'ismapped', popup))
        assert int(field._combo.cget('height')) == 8
        position = app.tk.call(popup, 'yview')
        if sys.platform == 'win32':
            app.tk.call('event', 'generate', popup, '<MouseWheel>', '-delta', -120)
        else:
            app.tk.call('event', 'generate', popup, '<Button-5>')
        app.update()
        assert app.tk.call(popup, 'yview') != position
        assert body._parent_canvas.yview() == before
        app.tk.call('event', 'generate', popup, '<Escape>')
        app.update()
        command.assert_not_called()
        assert not errors
    finally:
        app.shutdown()
        app.mainloop()


def test_settings_fit_workspace_and_tools_open_below_header_button(hidden_ui, tmp_path):
    app, _, _ = preview_app(tmp_path)
    errors = []
    app.report_callback_exception = lambda *args: errors.append(args)
    try:
        app.geometry('1024x720')
        app.deiconify()
        app.update()
        menu = app.tools_menu
        app.tools_menu = Mock()
        app.open_tools_menu()
        app.tools_menu.tk_popup.assert_called_once_with(app.more_btn.winfo_rootx(),
            app.more_btn.winfo_rooty() + app.more_btn.winfo_height() + 6)
        app.tools_menu = menu
        window = StationSettingsWindow(app)
        window.update()
        contained(window, app)
        stop = [child for group in window.winfo_children() for child in group.winfo_children()
                if isinstance(child, ctk.CTkButton) and child.cget('text') == 'STOP']
        assert len(stop) == 1
        contained(stop[0], window)
        contained(window.profile_menu, window)
        assert all(label.cget('wraplength') <= window.winfo_width() - 112 for label in window._wrapped_labels)
        check_readable(window)
        window._close()
        app.update()
        app._update_cycle_hud('', '#875A12', 'Review the stopped egg before continuing',
            detail='The capture and sensor disagree. Keep the egg in place, inspect it, then confirm the result below.')
        app.update_idletasks()
        contained(app.cycle_status_label, app.cycle_hud)
        contained(app.cycle_detail_label, app.cycle_hud)
        contained(app.eject_btn, app)
        assert app.video_container.winfo_height() > 200
        assert not errors
    finally:
        app.shutdown()
        app.mainloop()
