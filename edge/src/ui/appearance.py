"""Visual-only appearance preference, independent of rig configuration."""
import json
from pathlib import Path
import tkinter as tk

import customtkinter as ctk
from .theme import FUTheme as T, DIM_PALETTE, LIGHT_PALETTE, set_palette

PREFERENCE = Path(__file__).resolve().parents[2] / 'db' / 'ui_appearance.json'


def load_appearance():
    try:
        value = json.loads(PREFERENCE.read_text(encoding='utf-8')).get('appearance')
        return value if isinstance(value, str) and value in {'dim', 'light'} else 'dim'
    except (OSError, ValueError, AttributeError):
        return 'dim'


def color_mapping(before, after):
    # Camera wells and solid action text retain their own fixed palette.
    fixed = {'DARKROOM_VIEWPORT', 'VIEWPORT_TEXT', 'VIEWPORT_MUTED', 'TEXT_WHITE'}
    return {before[key].lower(): after[key] for key in before if key not in fixed and before[key] != after[key]}


def apply_appearance(root, appearance, remember=True):
    before = dict(LIGHT_PALETTE if T.appearance == 'light' else DIM_PALETTE)
    set_palette(appearance)
    after = LIGHT_PALETTE if T.appearance == 'light' else DIM_PALETTE
    mapping = color_mapping(before, after)

    def replace(value):
        if isinstance(value, str):
            return mapping.get(value.lower(), value)
        if isinstance(value, (list, tuple)):
            return [replace(item) for item in value]
        return value

    for section in ctk.ThemeManager.theme.values():
        for key, value in section.items():
            if 'color' in key:
                if key in {'fg_color', 'hover_color'} and value in (
                        T.PRIMARY_MAROON, T.DARK_MAROON, T.HOVER_MAROON, T.FERTILE_GREEN, T.REJECT_RED):
                    continue
                section[key] = replace(value)

    def visit(widget, camera=False):
        if getattr(widget, '_appearance_picker', False):
            widget.set('Soft light' if T.appearance == 'light' else 'Dim slate')
        try:
            camera = camera or widget.cget('fg_color') == T.DARKROOM_VIEWPORT
        except (ValueError, tk.TclError):
            pass
        if not camera:
            options = {}
            for key in ('fg_color', 'bg_color', 'text_color', 'text_color_disabled',
                        'border_color', 'hover_color', 'button_color', 'button_hover_color',
                        'progress_color', 'placeholder_text_color', 'selected_color',
                        'selected_hover_color', 'unselected_color', 'unselected_hover_color',
                        'scrollbar_button_color', 'scrollbar_button_hover_color'):
                try:
                    original = widget.cget(key)
                    updated = replace(original)
                    if key in {'fg_color', 'hover_color'} and isinstance(original, str) and original in {
                            T.PRIMARY_MAROON, T.DARK_MAROON, T.HOVER_MAROON,
                            T.FERTILE_GREEN, T.REJECT_RED}:
                        updated = original
                    if updated != original:
                        options[key] = updated
                except (ValueError, tk.TclError):
                    pass
            if options:
                if isinstance(widget, ctk.CTkSegmentedButton):
                    options.pop('border_color', None)
                widget.configure(**options)
            for key in ('_desktop_border', '_desktop_focus_border'):
                if hasattr(widget, key):
                    setattr(widget, key, replace(getattr(widget, key)))
        for child in widget.winfo_children():
            visit(child, camera)
    visit(root)
    ctk.set_appearance_mode('light' if T.appearance == 'light' else 'dark')
    from .select_field import refresh_style
    refresh_style(root)
    if remember:
        try:
            PREFERENCE.parent.mkdir(parents=True, exist_ok=True)
            temporary = PREFERENCE.with_suffix('.tmp')
            temporary.write_text(json.dumps({'appearance': T.appearance}), encoding='utf-8')
            temporary.replace(PREFERENCE)
        except OSError:
            # Appearance remains usable when the preference directory is read-only.
            return False
    return True


def appearance_picker(parent, root):
    from .select_field import SelectField
    field = SelectField(parent, values=['Dim slate', 'Soft light'], width=144, height=36,
                        command=lambda value: apply_appearance(root, 'light' if value == 'Soft light' else 'dim'))
    field.set('Soft light' if T.appearance == 'light' else 'Dim slate')
    field._appearance_picker = True
    return field
