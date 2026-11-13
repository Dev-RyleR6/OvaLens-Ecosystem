"""Offline desktop fonts and native control defaults; no system font installation."""
import ctypes
import sys
from pathlib import Path

import customtkinter as ctk

from .theme import FUTheme


ASSETS = Path(__file__).with_name('assets')
FONT_FILES = ('Inter-Regular.ttf', 'Inter-Bold.ttf')
_configured = False
_fontconfig = None


def _register_fonts():
    """Register the two shipped static weights for this process only."""
    global _fontconfig
    paths = [ASSETS / 'fonts' / name for name in FONT_FILES]
    if not all(path.is_file() for path in paths):
        return False
    if sys.platform == 'win32':
        return all(ctk.FontManager.windows_load_font(str(path), private=True, enumerable=True)
                   for path in paths)
    if sys.platform.startswith('linux'):
        # Fontconfig application fonts avoid copying files into ~/.fonts or
        # rebuilding a system cache on the Raspberry Pi.
        _fontconfig = ctypes.CDLL('libfontconfig.so.1')
        _fontconfig.FcConfigGetCurrent.restype = ctypes.c_void_p
        _fontconfig.FcConfigAppFontAddFile.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        _fontconfig.FcConfigAppFontAddFile.restype = ctypes.c_int
        config = _fontconfig.FcConfigGetCurrent()
        return bool(config) and all(_fontconfig.FcConfigAppFontAddFile(config, bytes(path))
                                    for path in paths)
    return False


def configure_desktop():
    """Run before constructing Tk so font enumeration sees the bundled family."""
    global _configured
    if _configured:
        return
    try:
        loaded = _register_fonts()
    except (OSError, AttributeError):
        loaded = False
    FUTheme.FONT_FAMILY = 'Inter' if loaded else 'Segoe UI' if sys.platform == 'win32' else 'DejaVu Sans'
    if not loaded:
        print(f'[UI] Bundled Inter unavailable; using {FUTheme.FONT_FAMILY}.')
    ctk.set_default_color_theme(str(ASSETS / 'desktop_theme.json'))
    ctk.ThemeManager.theme['CTkFont']['family'] = FUTheme.FONT_FAMILY
    ctk.set_appearance_mode('light')
    _configured = True


def install_entry_focus(root):
    """Show keyboard focus without adding widgets, timers or extra event loops."""
    def focus_in(event):
        control = event.widget.master
        if isinstance(control, ctk.CTkEntry):
            control._desktop_border = control.cget('border_color')
            control.configure(border_color=FUTheme.PRIMARY_MAROON)

    def focus_out(event):
        control = event.widget.master
        if isinstance(control, ctk.CTkEntry) and hasattr(control, '_desktop_border'):
            # Retain a validation color applied while editing.
            if control.cget('border_color') == FUTheme.PRIMARY_MAROON:
                control.configure(border_color=control._desktop_border)
            del control._desktop_border

    root.bind_class('Entry', '<FocusIn>', focus_in, add='+')
    root.bind_class('Entry', '<FocusOut>', focus_out, add='+')
