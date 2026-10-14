"""Open the station; complete batch creation/selection in the operator workspace."""
from typing import Optional, Dict, Any
import customtkinter as ctk
from .theme import FUTheme as T


class StartupConfigWindow(ctk.CTk):
    def __init__(self, device_id="STATION-01-RP5", operator_name=""):
        super().__init__()
        self.device_id, self.result = device_id, None
        self._simulation_var = ctk.BooleanVar(value=False)
        self.title("OvaLens — Open station")
        self.geometry("620x460")
        self.minsize(600, 440)
        self.configure(fg_color=T.BG_LIGHT)
        ctk.set_appearance_mode("dark")
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        body = ctk.CTkFrame(self, fg_color=T.PANEL_LIGHT, corner_radius=8)
        body.pack(fill="both", expand=True, padx=24, pady=(24, 12))
        ctk.CTkLabel(body, text="OvaLens Edge Operator", font=(T.FONT_FAMILY, 22, "bold"),
                     text_color=T.TEXT_PRIMARY).pack(anchor="w", padx=20, pady=(20, 4))
        ctk.CTkLabel(body, text=f"Foundation University · Station {device_id}",
                     font=(T.FONT_FAMILY, 12), text_color=T.TEXT_MUTED).pack(anchor="w", padx=20)
        ctk.CTkLabel(body, text="Operator name", text_color=T.TEXT_PRIMARY,
                     font=(T.FONT_FAMILY, 12, "bold")).pack(anchor="w", padx=20, pady=(20, 4))
        self._operator_entry = ctk.CTkEntry(body, height=36, text_color=T.TEXT_PRIMARY,
                                           fg_color=T.PANEL_LIGHT_ALT)
        self._operator_entry.insert(0, operator_name)
        self._operator_entry.pack(fill="x", padx=20)
        ctk.CTkLabel(body, text="Choose a saved batch or create one in Batch setup.\n"
                     "Batch details and scans save locally, including while offline.\n"
                     "Prepare the empty conveyor, then Start sorting.", wraplength=520,
                     justify="left", text_color=T.TEXT_SECONDARY,
                     font=(T.FONT_FAMILY, 13)).pack(anchor="w", padx=20, pady=(16, 8))
        ctk.CTkCheckBox(body, text="Simulation preview only", variable=self._simulation_var,
                        text_color=T.TEXT_PRIMARY).pack(anchor="w", padx=20, pady=(4, 16))
        self._status_label = ctk.CTkLabel(self, text="", text_color=T.REJECT_RED_TEXT)
        self._status_label.pack(fill="x", padx=24)
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=24, pady=(4, 20))
        ctk.CTkButton(actions, text="Cancel", command=self._on_cancel, fg_color=T.PANEL_LIGHT_ALT,
                       text_color=T.TEXT_PRIMARY, height=38).pack(side="left")
        ctk.CTkButton(actions, text="Open station", command=self._on_start, fg_color=T.PRIMARY_MAROON,
                       hover_color=T.HOVER_MAROON, text_color=T.TEXT_WHITE, height=38).pack(side="right")

    def _on_start(self):
        operator = self._operator_entry.get().strip()
        if not operator or len(operator) > 100:
            self._status_label.configure(text="Enter an operator name (1–100 characters).")
            return
        self.result = {"operator": operator, "stage": "DAY_10",
                       "simulation": self._simulation_var.get(), "fullscreen": True}
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self.destroy()


def show_startup_config(device_id="STATION-01-RP5", operator_name="") -> Optional[Dict[str, Any]]:
    window = StartupConfigWindow(device_id, operator_name)
    window.mainloop()
    return window.result
