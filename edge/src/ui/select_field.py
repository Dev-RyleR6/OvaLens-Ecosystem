"""A native read-only desktop picker inside the lightweight CTk layout."""
import tkinter as tk
from tkinter import ttk
from weakref import WeakSet

import customtkinter as ctk

from .theme import FUTheme as T


STYLE = 'OvaLens.TCombobox'


def _install_style(root):
    if getattr(root, '_ovalens_selects', None) is not None:
        return
    root._ovalens_selects = WeakSet()
    style = ttk.Style(root)
    # The bundled Tk theme honors field/focus colors on Windows and Linux.
    if 'clam' in style.theme_names() and style.theme_use() != 'clam':
        style.theme_use('clam')
    style.configure(STYLE, fieldbackground=T.PANEL_LIGHT, background=T.PANEL_LIGHT,
                    foreground=T.TEXT_PRIMARY, arrowcolor=T.TEXT_SECONDARY,
                    borderwidth=0, relief='flat', padding=(8, 4, 6, 4), arrowsize=13)
    style.map(STYLE, fieldbackground=[('disabled', T.PANEL_LIGHT_ALT), ('readonly', T.PANEL_LIGHT)],
              background=[('disabled', T.PANEL_LIGHT_ALT), ('active', T.PANEL_ACCENT)],
              foreground=[('disabled', T.TEXT_MUTED), ('readonly', T.TEXT_PRIMARY)],
              selectbackground=[('readonly', T.PRIMARY_MAROON_BG)],
              selectforeground=[('readonly', T.TEXT_PRIMARY)],
              arrowcolor=[('disabled', T.TEXT_MUTED), ('readonly', T.TEXT_SECONDARY)])
    for option, value in (('font', (T.FONT_FAMILY, -T.FONT_BODY)), ('background', T.PANEL_LIGHT),
                          ('foreground', T.TEXT_PRIMARY), ('selectBackground', T.PRIMARY_MAROON),
                          ('selectForeground', T.TEXT_WHITE)):
        root.option_add('*TCombobox*Listbox.' + option, value)

    def popup_wheel(event):
        # Let Tk's Listbox class scroll first, then keep CTk's bind_all handler
        # from also moving the setup form underneath the open native picker.
        path = str(event.widget)
        if any(path.startswith(str(field._combo) + '.') for field in root._ovalens_selects):
            return 'break'
    for event in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
        root.bind_class('Listbox', event, popup_wheel, add='+')


class SelectField(ctk.CTkFrame):
    """get/set/configure semantics match the former CTkOptionMenu selectors.

    Programmatic set/variable updates stay silent. Only a user selection calls
    command, and normal always means read-only rather than free-form input.
    """
    def __init__(self, master, values, variable=None, command=None, width=240,
                 height=36, font=None, state='normal', **kwargs):
        # Old selectors mixed action-colored and field-colored backgrounds.
        # Native pickers deliberately share one neutral, input-like appearance.
        for key in ('fg_color', 'button_color', 'button_hover_color', 'text_color',
                    'text_color_disabled', 'dropdown_font', 'dropdown_fg_color',
                    'dropdown_hover_color', 'dropdown_text_color', 'dynamic_resizing', 'corner_radius'):
            kwargs.pop(key, None)
        super().__init__(master, width=width, height=height, corner_radius=8,
                         fg_color=T.PANEL_LIGHT, border_width=1, border_color=T.BORDER_CONTROL, **kwargs)
        self._select_font = font if font is not None else ctk.CTkFont(size=T.FONT_BODY)
        self._select_command = command
        self._select_state = state
        self._select_values = list(values)
        self._select_variable = variable if variable is not None else tk.StringVar(
            master=self, value=self._select_values[0] if self._select_values else '')
        root = self._root()
        _install_style(root)
        self._combo = ttk.Combobox(self, values=self._select_values, textvariable=self._select_variable,
            width=1, height=8, style=STYLE, state='readonly',
            font=self._apply_font_scaling(self._select_font), takefocus=True)
        self._combo.place(x=2, y=2, relwidth=1, relheight=1, width=-4, height=-4)
        root._ovalens_selects.add(self)
        self._combo.bind('<<ComboboxSelected>>', self._selected)
        self._combo.bind('<FocusIn>', lambda _: super(SelectField, self).configure(border_color=T.PRIMARY_MAROON))
        self._combo.bind('<FocusOut>', lambda _: self._restore_border())
        self._combo.bind('<space>', self._open_from_keyboard)
        self._combo.bind('<Escape>', lambda _: 'break')
        # A wheel over a closed picker must not silently change camera modes.
        for event in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
            self._combo.bind(event, self._closed_wheel)
        self.configure(state=state)

    def _closed_wheel(self, event):
        parent = self.master
        while parent is not None:
            if isinstance(parent, ctk.CTkScrollableFrame):
                parent._mouse_wheel_all(event)
                break
            parent = parent.master
        return 'break'

    def _restore_border(self):
        super().configure(border_color=T.BORDER if self._select_state == 'disabled' else T.BORDER_CONTROL)

    def _open_from_keyboard(self, event):
        if self._select_state != 'disabled':
            self._combo.event_generate('<Down>')
        return 'break'

    def _selected(self, event=None):
        if self._select_state != 'disabled' and self._select_command is not None:
            self._select_command(self.get())

    def get(self):
        return self._select_variable.get()

    def set(self, value):
        self._select_variable.set(value)

    def configure(self, require_redraw=False, **kwargs):
        if not hasattr(self, '_combo'):
            return super().configure(require_redraw=require_redraw, **kwargs)
        if 'values' in kwargs:
            self._select_values = list(kwargs.pop('values'))
            self._combo.configure(values=self._select_values)
        if 'command' in kwargs:
            self._select_command = kwargs.pop('command')
        if 'variable' in kwargs:
            self._select_variable = kwargs.pop('variable')
            self._combo.configure(textvariable=self._select_variable)
        if 'font' in kwargs:
            self._select_font = kwargs.pop('font')
            self._combo.configure(font=self._apply_font_scaling(self._select_font))
        if 'state' in kwargs:
            self._select_state = kwargs.pop('state')
            self._combo.configure(state='disabled' if self._select_state == 'disabled' else 'readonly')
            self._restore_border()
        if kwargs:
            super().configure(require_redraw=require_redraw, **kwargs)

    def cget(self, name):
        if name == 'values':
            return self._select_values
        if name == 'state':
            return self._select_state
        if name == 'variable':
            return self._select_variable
        if name == 'font':
            return self._select_font
        if name == 'text_color':
            return T.TEXT_PRIMARY
        if name in {'button_color', 'button_hover_color'}:
            return T.PANEL_LIGHT
        return super().cget(name)

    def focus_set(self):
        self._combo.focus_set()

    def focus_force(self):
        self._combo.focus_force()

    def _set_scaling(self, *args, **kwargs):
        super()._set_scaling(*args, **kwargs)
        if hasattr(self, '_combo'):
            self._combo.configure(font=self._apply_font_scaling(self._select_font))

    def destroy(self):
        root = self._root()
        if hasattr(root, '_ovalens_selects'):
            root._ovalens_selects.discard(self)
        super().destroy()
