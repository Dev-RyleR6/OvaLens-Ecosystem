"""TASK-NEW-EDGE-TYPE-CONTRAST-01: real font resolution and accessible native controls."""
from types import SimpleNamespace
from unittest.mock import Mock, call
import json
import sys
import tkinter.font as tkfont

import customtkinter as ctk
import pytest

from test_camera_preview_ui import preview_app
from test_startup_config import hidden_ui
from test_desktop_layout import color, luminance, check_readable
from src.ui import desktop_style
from src.ui.theme import FUTheme


def contrast(first, second):
    light, dark = sorted((luminance(first), luminance(second)), reverse=True)
    return (light + .05) / (dark + .05)


def test_windows_registration_is_private_and_loads_both_static_weights(monkeypatch):
    register = Mock(return_value=True)
    monkeypatch.setattr(desktop_style, 'sys', SimpleNamespace(platform='win32'))
    monkeypatch.setattr(ctk.FontManager, 'windows_load_font', register)
    assert desktop_style._register_fonts()
    assert register.call_args_list == [
        call(str(desktop_style.ASSETS / 'fonts' / name), private=True, enumerable=True)
        for name in desktop_style.FONT_FILES]


def test_missing_fonts_do_not_attempt_native_registration(tmp_path, monkeypatch):
    monkeypatch.setattr(desktop_style, 'ASSETS', tmp_path)
    register = Mock()
    monkeypatch.setattr(ctk.FontManager, 'windows_load_font', register)
    assert not desktop_style._register_fonts()
    register.assert_not_called()


def test_default_theme_keeps_text_and_control_states_distinguishable():
    theme = json.loads((desktop_style.ASSETS / 'desktop_theme.json').read_text())
    def rgb(hex_color):
        return tuple(int(hex_color[n:n + 2], 16) / 255 for n in (1, 3, 5))
    for kind, foreground, surfaces in (
        ('CTkButton', 'text_color', ('fg_color', 'hover_color')),
        ('CTkButton', 'text_color_disabled', ('fg_color',)),
        ('CTkEntry', 'placeholder_text_color', ('fg_color',)),
        ('CTkSegmentedButton', 'text_color', ('selected_color', 'selected_hover_color',
                                            'unselected_color', 'unselected_hover_color')),
        ('DropdownMenu', 'text_color', ('fg_color', 'hover_color')),
    ):
        for surface in surfaces:
            assert contrast(rgb(theme[kind][foreground]), rgb(theme[kind][surface])) >= 4.5, (kind, surface)
    assert contrast(rgb(theme['CTkEntry']['border_color']), rgb(theme['CTk']['fg_color'])) >= 3
    assert contrast(rgb(theme['CTkEntry']['border_color']), rgb(theme['CTkEntry']['fg_color'])) >= 3


@pytest.mark.parametrize('platform, expected', [('win32', 'Segoe UI'), ('linux', 'DejaVu Sans')])
def test_font_registration_failure_keeps_a_native_fallback(monkeypatch, platform, expected):
    monkeypatch.setattr(desktop_style, '_configured', False)
    monkeypatch.setattr(desktop_style, '_register_fonts', Mock(side_effect=OSError('font API unavailable')))
    monkeypatch.setattr(desktop_style, 'sys', SimpleNamespace(platform=platform))
    monkeypatch.setattr(FUTheme, 'FONT_FAMILY', 'Inter')
    monkeypatch.setattr(ctk, 'set_default_color_theme', Mock())
    monkeypatch.setattr(ctk, 'set_appearance_mode', Mock())
    monkeypatch.setattr(ctk.ThemeManager, 'theme', {'CTkFont': {}})
    desktop_style.configure_desktop()
    assert FUTheme.FONT_FAMILY == expected
    assert ctk.ThemeManager.theme['CTkFont']['family'] == expected
    desktop_style.configure_desktop()
    assert desktop_style._register_fonts.call_count == 1


def test_actual_control_fonts_placeholder_edges_and_keyboard_focus(hidden_ui, tmp_path):
    app, _, _ = preview_app(tmp_path)
    try:
        app.geometry('1024x720')
        app.deiconify()
        app.update()
        if sys.platform in {'win32', 'linux'}:
            assert FUTheme.FONT_FAMILY == 'Inter'
        panel = ctk.CTkFrame(app, fg_color=FUTheme.PANEL_LIGHT, width=500, height=160)
        panel.place(x=24, y=130)
        label = ctk.CTkLabel(panel, text='Batch IP-KAY · Penoy ₱14.00')
        label.pack()
        entry = ctk.CTkEntry(panel, placeholder_text='Original egg count', width=220)
        entry.pack(pady=8)
        button = ctk.CTkButton(panel, text='Continue')
        button.pack()
        app.update_idletasks()
        # Inspect the underlying Tk fonts, not just the requested family name.
        for native in (label._label, entry._entry, button._text_label, app.session_btn._text_label):
            actual = tkfont.Font(root=app, font=native.cget('font')).actual()
            assert actual['family'] == FUTheme.FONT_FAMILY
        assert tkfont.Font(root=app, font=app.session_btn._text_label.cget('font')).actual('weight') == 'bold'
        assert contrast(color(entry, entry.cget('placeholder_text_color')),
                        color(entry, entry.cget('fg_color'))) >= 4.5
        assert contrast(color(entry, entry.cget('border_color')),
                        color(panel, panel.cget('fg_color'))) >= 3
        original_border = entry.cget('border_color')
        entry.focus_force()
        app.update()
        assert entry.cget('border_color') == FUTheme.FOCUS
        entry.insert(0, '120')
        button.focus_force()
        app.update()
        assert entry.cget('border_color') == original_border
        assert entry.get() == '120'
        entry.focus_force()
        app.update()
        entry.configure(border_color=FUTheme.REJECT_RED)
        button.focus_force()
        app.update()
        assert entry.cget('border_color') == FUTheme.REJECT_RED
        check_readable(panel)
        panel.destroy()
        app.open_camera_controls()
        app.update()
        for menu in app._camera_panel.modes.values():
            assert contrast(color(menu, menu.cget('text_color')),
                            color(menu, menu.cget('button_color'))) >= 3
        check_readable(app)
        app._camera_panel.close()
    finally:
        app.shutdown()
        app.mainloop()
