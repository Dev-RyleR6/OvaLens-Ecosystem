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
    ctk.set_appearance_mode('dark')
    _configured = True


def install_entry_focus(root):
    """Show keyboard focus without adding widgets, timers or extra event loops."""
    def focus_in(event):
        control = event.widget.master
        if isinstance(control, ctk.CTkEntry):
            reveal_in_scroll_frame(control)
            control._desktop_border = control.cget('border_color')
            control.configure(border_color=FUTheme.FOCUS)

    def focus_out(event):
        control = event.widget.master
        if isinstance(control, ctk.CTkEntry) and hasattr(control, '_desktop_border'):
            # Retain a validation color applied while editing.
            if control.cget('border_color') == FUTheme.FOCUS:
                control.configure(border_color=control._desktop_border)
            del control._desktop_border

    def mapped(event):
        control = getattr(event.widget, "master", None)
        if isinstance(control, (ctk.CTkButton, ctk.CTkCheckBox)):
            enable_button_keyboard(control)
    root.bind_class('Canvas', '<Map>', mapped, add='+')
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
    if getattr(button, "_desktop_keyboard", False):
        return button
    button._desktop_keyboard = True
    if isinstance(button, ctk.CTkButton):
        fill = button._apply_appearance_mode(button.cget("fg_color"))
        minimum = 44 if fill in {FUTheme.PRIMARY_MAROON, FUTheme.REJECT_RED, FUTheme.REJECT_RED_BG, FUTheme.FERTILE_GREEN} else 36
        if button.cget("height") < minimum:
            button.configure(height=minimum)
    canvas = button._canvas
    canvas.configure(takefocus=lambda _path: int(button.cget("state") != "disabled"), highlightthickness=0)
    def focus_in(event):
        reveal_in_scroll_frame(button)
        if not hasattr(button, "_desktop_focus_border"):
            button._desktop_focus_border = (button.cget("border_color"), button.cget("border_width"))
        button.configure(border_color=FUTheme.FOCUS, border_width=2)
    def focus_out(event):
        original = getattr(button, "_desktop_focus_border", None)
        if original is not None:
            if button.cget("border_color") == FUTheme.FOCUS:
                button.configure(border_color=original[0], border_width=original[1])
            del button._desktop_focus_border
    canvas.bind("<FocusIn>", focus_in, add="+")
    canvas.bind("<FocusOut>", focus_out, add="+")
    def activate(event):
        if isinstance(button, ctk.CTkCheckBox):
            if button.cget("state") != "disabled":
                button.toggle()
        else:
            button.invoke()  # CTk preserves its disabled-state guard.
        return "break"  # Space must not propagate to the app's scan shortcut.
    for key in ("<space>", "<Return>", "<KP_Enter>"):
        canvas.bind(key, activate, add="+")
    return button


def fit_dialog_content(dialog):
    """Wrap explanatory text at the actual dialog width and preserve native close guards."""
    def fit(event=None):
        if not dialog.winfo_exists() or (event is not None and event.widget is not dialog):
            return
        width = dialog.winfo_width()
        if event is not None and width == getattr(dialog, "_desktop_fit_width", None):
            return
        dialog._desktop_fit_width = width
        def visit(parent):
            for child in parent.winfo_children():
                if isinstance(child, (ctk.CTkButton, ctk.CTkCheckBox)):
                    enable_button_keyboard(child)
                elif isinstance(child, ctk.CTkLabel):
                    text = child.cget("text")
                    if len(text) > 55 and child.winfo_manager() == "pack":
                        parent_width = parent.winfo_width()
                        available = dialog.winfo_width() - 120
                        if parent_width >= 300:
                            available = min(available, parent_width - 36)
                        child.configure(wraplength=child._reverse_widget_scaling(max(180, available)), justify="left")
                visit(child)
        visit(dialog)
    def close(event):
        handler = dialog.protocol("WM_DELETE_WINDOW")
        if handler:
            dialog.tk.call("eval", handler)
        else:
            dialog.destroy()
        return "break"
    dialog.bind("<Configure>", fit, add="+")
    dialog.bind("<Escape>", close, add="+")
    dialog._desktop_fit = fit
    dialog.after_idle(fit)


def add_dialog_stop(parent, app):
    """Keep the station's existing immediate stop command reachable in operator dialogs."""
    button = ctk.CTkButton(parent, text="STOP", width=84, height=44,
        font=(FUTheme.FONT_FAMILY, 14, "bold"), fg_color=FUTheme.REJECT_RED,
        hover_color=FUTheme.REJECT_RED_HOVER, text_color=FUTheme.TEXT_WHITE,
        command=app.trigger_manual_eject)
    button.pack(side="right", padx=(12, 0))
    enable_button_keyboard(button)
    return button


def finish_dialog_layout(dialog):
    """Measure the completed widget tree before fitting prose; early frames can be 1px wide."""
    dialog.update_idletasks()
    fit = getattr(dialog, "_desktop_fit", None)
    if fit is not None:
        fit()
        dialog.update_idletasks()
