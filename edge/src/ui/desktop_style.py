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


def reveal_in_scroll_frame(widget):
    """Keep a keyboard-focused control in view without changing the active page."""
    parent = widget.master
    while parent is not None:
        if isinstance(parent, ctk.CTkScrollableFrame):
            canvas = parent._parent_canvas
            extent = canvas.bbox("all")
            if not extent:
                return
            total = max(1, extent[3] - extent[1])
            top = widget.winfo_rooty() - parent.winfo_rooty()
            bottom = top + widget.winfo_height()
            visible_top = canvas.canvasy(0)
            height = canvas.winfo_height()
            if top < visible_top:
                canvas.yview_moveto(max(0, top - 8) / total)
            elif bottom > visible_top + height:
                canvas.yview_moveto(max(0, bottom - height + 8) / total)
            return
        parent = getattr(parent, "master", None)


def enable_button_keyboard(button):
    """Give a CTk button native Tab traversal, a focus ring and key activation."""
    canvas = button._canvas
    canvas.configure(takefocus=lambda _path: int(button.cget("state") != "disabled"),
                     highlightthickness=2, highlightcolor=FUTheme.PRIMARY_MAROON,
                     highlightbackground=button._apply_appearance_mode(button._bg_color))
    canvas.bind("<FocusIn>", lambda _: reveal_in_scroll_frame(button), add="+")
    def activate(event):
        button.invoke()  # CTk preserves its disabled-state guard.
        return "break"  # Space must not propagate to the app's scan shortcut.
    for key in ("<space>", "<Return>", "<KP_Enter>"):
        canvas.bind(key, activate, add="+")
    return button
