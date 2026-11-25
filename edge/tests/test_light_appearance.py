"""Soft-light contrast, live switching and withdrawn-parent dialog regression."""
import customtkinter as ctk
import pytest
from test_camera_preview_ui import hidden_ui
from src.ui.theme import FUTheme as T, DIM_PALETTE, LIGHT_PALETTE, set_palette
from src.ui.appearance import apply_appearance
from test_desktop_layout import luminance
from test_desktop_usability import station_preview, open_surface, descendants, hidden_ui
from test_live_camera_ui import pump


def test_both_palettes_have_readable_text():
    def lum(value):
        return luminance(tuple(int(value[i:i+2], 16)/255 for i in (1, 3, 5)))
    def contrast(a, b):
        high, low = sorted((lum(a), lum(b)), reverse=True)
        return (high+.05)/(low+.05)
    for palette in (DIM_PALETTE, LIGHT_PALETTE):
        for surface in ('BG_LIGHT', 'PANEL_LIGHT', 'PANEL_LIGHT_ALT', 'PANEL_ACCENT', 'INPUT_BG', 'SELECTION_BG'):
            for text in ('TEXT_PRIMARY', 'TEXT_SECONDARY', 'TEXT_MUTED'):
                assert contrast(palette[text], palette[surface]) >= 4.5, (text, surface)
        assert contrast(palette['BORDER_CONTROL'], palette['INPUT_BG']) >= 3
        assert contrast(palette['FOCUS'], palette['PANEL_LIGHT']) >= 3


def test_light_switch_and_withdrawn_parent_dialog(hidden_ui, tmp_path):
    app = station_preview(tmp_path)
    try:
        # The reported form was compressed to 320px when its parent had not
        # finished mapping. Dialog dimensions must come from the display.
        app.minsize(1, 1)
        app.geometry('320x330')
        app.update()
        app.withdraw()
        window = open_surface(app, 'batch')
        assert window.winfo_width() >= 640
        assert window.body.winfo_height() >= 250
        assert window.target.winfo_width() >= 400
        apply_appearance(app, 'light', remember=False)
        app.update()
        assert window.cget('fg_color') == LIGHT_PALETTE['BG_LIGHT']
        assert window.save.cget('fg_color') == '#800000'
        assert window.save.cget('text_color') == '#FFFFFF'
        assert window.target.cget('text_color') == LIGHT_PALETTE['TEXT_PRIMARY']
        assert app.progress_bar.cget('progress_color') == LIGHT_PALETTE['BRAND_TEXT']
        assert str(window.pick._combo.cget('state')) == 'readonly'
        apply_appearance(app, 'dim', remember=False)
        assert window.save.cget('fg_color') == '#800000'
        assert window.target.cget('text_color') == DIM_PALETTE['TEXT_PRIMARY']
        assert app.progress_bar.cget('progress_color') == DIM_PALETTE['BRAND_TEXT']
        assert window.records
        assert not app._station_prepared and not app.is_auto_cycle_running
        window.destroy()
    finally:
        app.shutdown()
        app.mainloop()
        set_palette('dim')


def test_appearance_preference_is_separate_and_validated(tmp_path, monkeypatch):
    from src.ui import appearance
    path = tmp_path / 'ui_appearance.json'
    monkeypatch.setattr(appearance, 'PREFERENCE', path)
    assert appearance.load_appearance() == 'dim'
    path.write_text('{"appearance":"light"}')
    assert appearance.load_appearance() == 'light'
    path.write_text('{"appearance":"invalid"}')
    assert appearance.load_appearance() == 'dim'
    path.write_text('broken')
    assert appearance.load_appearance() == 'dim'
