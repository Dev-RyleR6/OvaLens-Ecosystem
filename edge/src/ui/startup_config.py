"""
OvaLens Startup Configuration Screen
Shown before the main operation window. Operator sets batch parameters
then clicks 'Start OvaLens Operation' to launch the chamber cycle.
"""

import threading
import math
from datetime import datetime
from typing import Optional, Dict, Any

import customtkinter as ctk
import serial.tools.list_ports

from .theme import FUTheme


class StartupConfigWindow(ctk.CTk):
    """
    Full-window startup configuration screen.
    Returns a config dict through self.result after the user confirms.
    Call show() which blocks until the user confirms or closes.
    """

    def __init__(self, device_id: str = "STATION-01-RP5"):
        super().__init__()
        self.device_id = device_id
        self.result: Optional[Dict[str, Any]] = None
        self._simulation_var = ctk.BooleanVar(value=False)

        # Window setup
        self.title("OvaLens — Batch Configuration")
        self.geometry("860x680")
        self.resizable(False, False)
        ctk.set_appearance_mode("dark")
        self.configure(fg_color=FUTheme.BG_LIGHT)
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        try:
            self.update_idletasks()
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            x = max(0, (sw - 860) // 2)
            y = max(0, (sh - 680) // 2)
            self.geometry(f"860x680+{x}+{y}")
        except Exception:
            pass

        self._build_ui()
        self._auto_detect_ports()

    # ─── UI Construction ──────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Header ──────────────────────────────────────────────────────────
        header = ctk.CTkFrame(
            self, fg_color=FUTheme.PRIMARY_MAROON, corner_radius=0, height=72
        )
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        header_inner = ctk.CTkFrame(header, fg_color="transparent")
        header_inner.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            header_inner,
            text="🥚  OvaLens",
            font=(FUTheme.FONT_FAMILY, 22, "bold"),
            text_color="#FFFFFF",
        ).pack(side="left", padx=(0, 16))

        divider = ctk.CTkFrame(header_inner, fg_color=FUTheme.LIGHT_MAROON, width=1, height=32)
        divider.pack(side="left", padx=12)

        ctk.CTkLabel(
            header_inner,
            text="Automated Duck Egg Candling System",
            font=(FUTheme.FONT_FAMILY, 13),
            text_color="#FFD0D0",
        ).pack(side="left", padx=12)

        ctk.CTkLabel(
            header_inner,
            text="Foundation University",
            font=(FUTheme.FONT_FAMILY, 11),
            text_color="#FFB0B0",
        ).pack(side="left", padx=(8, 0))

        # ── Main Content ─────────────────────────────────────────────────────
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=40, pady=24)

        # Left column: batch settings
        left = ctk.CTkFrame(
            main, fg_color=FUTheme.PANEL_LIGHT, corner_radius=12,
            border_width=1, border_color=FUTheme.BORDER
        )
        left.pack(side="left", fill="both", expand=True, padx=(0, 12))

        # Right column: hardware settings
        right = ctk.CTkFrame(
            main, fg_color=FUTheme.PANEL_LIGHT, corner_radius=12,
            border_width=1, border_color=FUTheme.BORDER, width=300
        )
        right.pack(side="right", fill="y", padx=(0, 0))
        right.pack_propagate(False)

        self._build_batch_panel(left)
        self._build_hardware_panel(right)

        # ── Footer / CTA ─────────────────────────────────────────────────────
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=40, pady=(0, 24))

        self._status_label = ctk.CTkLabel(
            footer, text="",
            font=(FUTheme.FONT_FAMILY, 11), text_color=FUTheme.TEXT_MUTED
        )
        self._status_label.pack(side="left")

        ctk.CTkButton(
            footer,
            text="▶  Start OvaLens Operation",
            font=(FUTheme.FONT_FAMILY, 14, "bold"),
            fg_color=FUTheme.PRIMARY_MAROON,
            hover_color=FUTheme.HOVER_MAROON,
            text_color="#FFFFFF",
            height=48,
            corner_radius=10,
            command=self._on_start,
        ).pack(side="right", padx=(12, 0))

        ctk.CTkButton(
            footer,
            text="Cancel",
            font=(FUTheme.FONT_FAMILY, 12),
            fg_color="transparent",
            hover_color=FUTheme.PANEL_ACCENT,
            text_color=FUTheme.TEXT_MUTED,
            border_width=1,
            border_color=FUTheme.BORDER,
            height=48,
            corner_radius=10,
            width=100,
            command=self._on_cancel,
        ).pack(side="right")

    def _build_batch_panel(self, parent):
        ctk.CTkLabel(
            parent,
            text="Batch Configuration",
            font=(FUTheme.FONT_FAMILY, 14, "bold"),
            text_color=FUTheme.TEXT_PRIMARY,
        ).pack(anchor="w", padx=20, pady=(18, 4))
        ctk.CTkLabel(
            parent,
            text="Set up the candling batch before starting the conveyor.",
            font=(FUTheme.FONT_FAMILY, 11),
            text_color=FUTheme.TEXT_MUTED,
        ).pack(anchor="w", padx=20, pady=(0, 16))

        # ── Breed ────────────────────────────────────────────────────────────
        self._breed_map = {
            "IP-Kayumanggi (Commercial Hybrid)": "KAY",
            "IP-Itim (Pure Line — Black)": "ITM",
            "IP-Khaki (Pure Line — Khaki)": "KHK",
        }
        self._add_label(parent, "Duck Breed / Genetic Line:")
        self._breed_var = ctk.StringVar(value=list(self._breed_map.keys())[0])
        self._breed_menu = ctk.CTkOptionMenu(
            parent,
            values=list(self._breed_map.keys()),
            variable=self._breed_var,
            fg_color=FUTheme.PANEL_LIGHT_ALT,
            text_color=FUTheme.TEXT_PRIMARY,
            button_color=FUTheme.PRIMARY_MAROON,
            button_hover_color=FUTheme.HOVER_MAROON,
            dropdown_fg_color=FUTheme.PANEL_LIGHT,
            dropdown_text_color=FUTheme.TEXT_PRIMARY,
            dropdown_hover_color=FUTheme.PANEL_ACCENT,
            height=36,
            corner_radius=8,
            command=self._update_batch_preview,
        )
        self._breed_menu.pack(fill="x", padx=20, pady=(2, 10))

        # ── Egg Count ────────────────────────────────────────────────────────
        self._add_label(parent, "Total Eggs in This Batch:")
        count_row = ctk.CTkFrame(parent, fg_color="transparent")
        count_row.pack(fill="x", padx=20, pady=(2, 6))

        self._count_entry = ctk.CTkEntry(
            count_row,
            fg_color=FUTheme.PANEL_LIGHT_ALT,
            text_color=FUTheme.TEXT_PRIMARY,
            height=36,
            corner_radius=8,
            font=(FUTheme.FONT_FAMILY, 14, "bold"),
            justify="center",
        )
        self._count_entry.insert(0, "500")
        self._count_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        # Quick preset chips
        presets_frame = ctk.CTkFrame(count_row, fg_color="transparent")
        presets_frame.pack(side="right")
        for label, val in [("100", 100), ("250", 250), ("500", 500)]:
            ctk.CTkButton(
                presets_frame,
                text=label,
                font=(FUTheme.FONT_FAMILY, 10, "bold"),
                fg_color=FUTheme.PANEL_LIGHT_ALT,
                hover_color=FUTheme.PANEL_ACCENT,
                text_color=FUTheme.TEXT_SECONDARY,
                border_width=1,
                border_color=FUTheme.BORDER,
                height=30,
                width=46,
                corner_radius=6,
                command=lambda v=val: self._set_count(v),
            ).pack(side="left", padx=2)

        # ── Operator Name ────────────────────────────────────────────────────
        self._add_label(parent, "Operator Name:")
        self._operator_entry = ctk.CTkEntry(
            parent,
            fg_color=FUTheme.PANEL_LIGHT_ALT,
            text_color=FUTheme.TEXT_PRIMARY,
            height=36,
            corner_radius=8,
            placeholder_text="e.g. Maria Santos",
        )
        self._operator_entry.pack(fill="x", padx=20, pady=(2, 10))

        # ── Batch Code Preview ───────────────────────────────────────────────
        self._add_label(parent, "Auto-Generated Batch Code:")
        preview_card = ctk.CTkFrame(
            parent,
            fg_color=FUTheme.PRIMARY_MAROON_BG,
            corner_radius=10,
            border_width=1,
            border_color=FUTheme.PRIMARY_MAROON_BORDER,
        )
        preview_card.pack(fill="x", padx=20, pady=(2, 12))

        p_top = ctk.CTkFrame(preview_card, fg_color="transparent")
        p_top.pack(fill="x", padx=14, pady=(8, 0))
        ctk.CTkLabel(
            p_top, text="BATCH CODE:",
            font=(FUTheme.FONT_FAMILY, 9, "bold"), text_color=FUTheme.TEXT_MUTED
        ).pack(side="left")
        ctk.CTkLabel(
            p_top, text="● DAY 10 CANDLING",
            font=(FUTheme.FONT_FAMILY, 9, "bold"), text_color=FUTheme.FERTILE_GREEN
        ).pack(side="right")

        self._batch_preview_label = ctk.CTkLabel(
            preview_card,
            text=self._generate_batch_code(),
            font=(FUTheme.FONT_FAMILY, 18, "bold"),
            text_color=FUTheme.TEXT_PRIMARY,
        )
        self._batch_preview_label.pack(anchor="w", padx=14, pady=(2, 10))

        # Batch number selector
        batch_num_row = ctk.CTkFrame(parent, fg_color="transparent")
        batch_num_row.pack(fill="x", padx=20, pady=(0, 4))
        ctk.CTkLabel(
            batch_num_row, text="Batch # in this month:",
            font=(FUTheme.FONT_FAMILY, 10, "bold"), text_color=FUTheme.TEXT_MUTED
        ).pack(side="left", padx=(0, 8))
        self._batch_num_var = ctk.StringVar(value="01")
        self._batch_num_menu = ctk.CTkOptionMenu(
            batch_num_row,
            values=[f"{i:02d}" for i in range(1, 13)],
            variable=self._batch_num_var,
            fg_color=FUTheme.PANEL_LIGHT_ALT,
            text_color=FUTheme.TEXT_PRIMARY,
            button_color=FUTheme.PRIMARY_MAROON,
            button_hover_color=FUTheme.HOVER_MAROON,
            dropdown_fg_color=FUTheme.PANEL_LIGHT,
            dropdown_text_color=FUTheme.TEXT_PRIMARY,
            height=30,
            width=80,
            corner_radius=6,
            command=self._update_batch_preview,
        )
        self._batch_num_menu.pack(side="left")

    def _build_hardware_panel(self, parent):
        ctk.CTkLabel(
            parent,
            text="Hardware & Timing",
            font=(FUTheme.FONT_FAMILY, 14, "bold"),
            text_color=FUTheme.TEXT_PRIMARY,
        ).pack(anchor="w", padx=20, pady=(18, 4))
        ctk.CTkLabel(
            parent,
            text="ESP32 wired via USB Serial.",
            font=(FUTheme.FONT_FAMILY, 10),
            text_color=FUTheme.TEXT_MUTED,
        ).pack(anchor="w", padx=20, pady=(0, 14))

        # ── Serial Port ──────────────────────────────────────────────────────
        self._add_label(parent, "ESP32 Serial Port:")
        port_row = ctk.CTkFrame(parent, fg_color="transparent")
        port_row.pack(fill="x", padx=20, pady=(2, 10))

        self._port_var = ctk.StringVar(value="Auto-Detect")
        self._port_menu = ctk.CTkOptionMenu(
            port_row,
            values=["Auto-Detect"],
            variable=self._port_var,
            fg_color=FUTheme.PANEL_LIGHT_ALT,
            text_color=FUTheme.TEXT_PRIMARY,
            button_color=FUTheme.PRIMARY_MAROON,
            button_hover_color=FUTheme.HOVER_MAROON,
            dropdown_fg_color=FUTheme.PANEL_LIGHT,
            dropdown_text_color=FUTheme.TEXT_PRIMARY,
            height=34,
            corner_radius=8,
        )
        self._port_menu.pack(side="left", fill="x", expand=True, padx=(0, 6))

        ctk.CTkButton(
            port_row, text="↺",
            font=(FUTheme.FONT_FAMILY, 14, "bold"),
            fg_color=FUTheme.PANEL_LIGHT_ALT,
            hover_color=FUTheme.PANEL_ACCENT,
            text_color=FUTheme.TEXT_PRIMARY,
            border_width=1, border_color=FUTheme.BORDER,
            height=34, width=36, corner_radius=8,
            command=self._auto_detect_ports,
        ).pack(side="right")

        # ── Conveyor Timing ──────────────────────────────────────────────────
        self._add_label(parent, "Belt Speed (cm/s):")
        self._speed_entry = self._make_entry(parent, "12.5")

        self._add_label(parent, "Chamber → Gate Distance (cm):")
        self._dist_entry = self._make_entry(parent, "25.0")

        self._add_label(parent, "Result Display Time (ms):")
        self._display_ms_entry = self._make_entry(parent, "1200")

        self._add_label(parent, "Servo Pulse Duration (ms):")
        self._pulse_entry = self._make_entry(parent, "250")

        # ── ESP32 Connection Status ──────────────────────────────────────────
        ctk.CTkCheckBox(parent, text="Simulation preview (no sorting or saved scans)",
                       variable=self._simulation_var, font=(FUTheme.FONT_FAMILY, 10),
                       text_color=FUTheme.TEXT_PRIMARY).pack(anchor="w", padx=20, pady=6)
        self._esp32_status = ctk.CTkLabel(
            parent,
            text="● ESP32: Detecting...",
            font=(FUTheme.FONT_FAMILY, 10, "bold"),
            text_color=FUTheme.TEXT_MUTED,
        )
        self._esp32_status.pack(anchor="w", padx=20, pady=(14, 4))

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def _add_label(self, parent, text: str):
        ctk.CTkLabel(
            parent, text=text,
            font=(FUTheme.FONT_FAMILY, 10, "bold"),
            text_color=FUTheme.TEXT_PRIMARY,
        ).pack(anchor="w", padx=20, pady=(4, 2))

    def _make_entry(self, parent, default: str) -> ctk.CTkEntry:
        e = ctk.CTkEntry(
            parent,
            fg_color=FUTheme.PANEL_LIGHT_ALT,
            text_color=FUTheme.TEXT_PRIMARY,
            height=32,
            corner_radius=8,
        )
        e.insert(0, default)
        e.pack(fill="x", padx=20, pady=(2, 8))
        return e

    def _set_count(self, val: int):
        self._count_entry.delete(0, "end")
        self._count_entry.insert(0, str(val))

    def _generate_batch_code(self) -> str:
        now = datetime.now()
        ym = now.strftime("%Y-%m")
        breed_key = self._breed_var.get() if hasattr(self, "_breed_var") else "KAY"
        breed_code = self._breed_map.get(breed_key, "KAY")
        batch_num = self._batch_num_var.get() if hasattr(self, "_batch_num_var") else "01"
        return f"BATCH-{ym}-{breed_code}-{batch_num}"

    def _update_batch_preview(self, *_):
        self._batch_preview_label.configure(text=self._generate_batch_code())

    def _auto_detect_ports(self):
        """Scan available COM ports and populate the dropdown."""
        ports = serial.tools.list_ports.comports()
        esp_ports = []
        for p in ports:
            desc = (p.description or "").lower()
            if any(k in desc for k in ("ch340", "cp210", "usb", "serial", "esp32", "ftdi")):
                esp_ports.append(p.device)

        all_opts = ["Auto-Detect"] + esp_ports + [p.device for p in ports if p.device not in esp_ports]
        if not all_opts:
            all_opts = ["Auto-Detect"]

        self._port_menu.configure(values=all_opts)

        if esp_ports:
            self._port_var.set(esp_ports[0])
            self._esp32_status.configure(
                text=f"● ESP32: {esp_ports[0]} (detected)",
                text_color=FUTheme.FERTILE_GREEN_TEXT,
            )
        else:
            self._port_var.set("Auto-Detect")
            self._esp32_status.configure(
                text="● ESP32: Not found — automatic sorting unavailable",
                text_color=FUTheme.INFERTILE_AMBER,
            )

    # ─── Actions ──────────────────────────────────────────────────────────────

    def _on_start(self):
        """Validate inputs and store config result."""
        try:
            egg_count = int(self._count_entry.get().strip())
            if not 1 <= egg_count <= 100000:
                raise ValueError
        except (ValueError, AttributeError):
            self._status_label.configure(
                text="⚠ Enter a valid egg count (minimum 1).",
                text_color=FUTheme.REJECT_RED_TEXT,
            )
            return

        operator = self._operator_entry.get().strip()
        if not operator or len(operator) > 100:
            self._status_label.configure(text="Enter an operator name (1 to 100 characters).",
                                         text_color=FUTheme.REJECT_RED_TEXT)
            return
        port_val = self._port_var.get()
        serial_port = None if port_val == "Auto-Detect" else port_val

        try:
            speed = float(self._speed_entry.get().strip())
            dist = float(self._dist_entry.get().strip())
            display_ms = int(self._display_ms_entry.get().strip())
            pulse_ms = int(self._pulse_entry.get().strip())
            if (not math.isfinite(speed) or not math.isfinite(dist) or speed <= 0 or dist <= 0
                    or not 1 <= display_ms <= 10000 or not 1 <= pulse_ms <= 5000):
                raise ValueError
        except ValueError:
            self._status_label.configure(
                text="⚠ Check hardware/timing values.",
                text_color=FUTheme.REJECT_RED_TEXT,
            )
            return

        breed_label = self._breed_var.get()
        breed_code = self._breed_map.get(breed_label, "KAY")
        batch_code = self._generate_batch_code()

        self.result = {
            "batch_id": batch_code,
            "breed": breed_label,
            "breed_code": breed_code,
            "egg_count": egg_count,
            "operator": operator,
            "stage": "DAY_10",
            "serial_port": serial_port,
            "conveyor_speed_cm_s": speed,
            "conveyor_dist_cm": dist,
            "display_result_ms": display_ms,
            "servo_pulse_ms": pulse_ms,
            "simulation": self._simulation_var.get(),
            "fullscreen": True,
        }
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self.destroy()


def show_startup_config(device_id: str = "STATION-01-RP5") -> Optional[Dict[str, Any]]:
    """
    Show the startup config window and block until the user confirms or cancels.
    Returns the config dict or None if cancelled.
    """
    win = StartupConfigWindow(device_id=device_id)
    win.mainloop()
    return win.result
