"""Offline-first batch setup. All storage/network work stays off the Tk thread."""
from datetime import datetime
import queue
import threading
from uuid import uuid4

import customtkinter as ctk

from .theme import FUTheme as T
from ..core.batches import BREEDS, FARM_TIMEZONE, new_batch_record
from ..core.operator_flow import validate_batch_config


class BatchSetupWindow(ctk.CTkToplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app, self.records, self.selected_id = app, {}, app.current_batch_id
        self.busy, self.loaded = False, False
        self.draft_id = str(uuid4())
        self.title("Batch setup")
        self.geometry("600x640")
        self.minsize(540, 500)
        self.configure(fg_color=T.BG_LIGHT)
        self.transient(app)
        self.grab_set()
        app._center_window(self, 600, 640)
        self.protocol("WM_DELETE_WINDOW", self.close)
        ctk.CTkLabel(self, text="Batch setup", font=(T.FONT_FAMILY, 20, "bold"),
                     text_color=T.TEXT_PRIMARY).pack(anchor="w", padx=20, pady=(16, 2))
        ctk.CTkLabel(self, text="Save on this station. Registration and scans sync automatically.",
                     text_color=T.TEXT_MUTED, font=(T.FONT_FAMILY, 12)).pack(anchor="w", padx=20, pady=(0, 12))
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(side="bottom", fill="x", padx=20, pady=(8, 16))
        self.cancel = ctk.CTkButton(footer, text="Cancel", width=100, height=38,
            fg_color=T.PANEL_LIGHT_ALT, border_width=1, border_color=T.BORDER,
            command=self.close, text_color=T.TEXT_PRIMARY)
        self.cancel.pack(side="left")
        self.save = ctk.CTkButton(footer, text="Use batch", height=38, fg_color=T.PRIMARY_MAROON,
            hover_color=T.HOVER_MAROON, text_color=T.TEXT_WHITE, command=self.apply, state="disabled")
        self.save.pack(side="right", fill="x", expand=True, padx=(12, 0))
        self.body = ctk.CTkScrollableFrame(self, fg_color=T.PANEL_LIGHT, corner_radius=8)
        self.body.pack(fill="both", expand=True, padx=20)
        self.mode = ctk.CTkSegmentedButton(self.body, values=["Existing batch", "New batch", "Complete details"],
            selected_color=T.PRIMARY_MAROON, selected_hover_color=T.HOVER_MAROON,
            unselected_color=T.PANEL_LIGHT_ALT, text_color=T.TEXT_PRIMARY, command=self.change_mode)
        self.mode.pack(fill="x", padx=12, pady=12)
        self.mode.set("Existing batch")
        self.pick_frame = ctk.CTkFrame(self.body, fg_color="transparent")
        self.pick_frame.pack(fill="x", padx=12)
        self.label(self.pick_frame, "Saved batch")
        self.pick = ctk.CTkOptionMenu(self.pick_frame, values=["Loading saved batches…"],
            command=self.choose, fg_color=T.PANEL_LIGHT_ALT, button_color=T.PRIMARY_MAROON,
            text_color=T.TEXT_PRIMARY, height=34)
        self.pick.pack(fill="x", pady=(2, 6))
        self.summary = ctk.CTkLabel(self.pick_frame, text="", text_color=T.TEXT_MUTED,
                                   wraplength=450, justify="left", anchor="w")
        self.summary.pack(fill="x", pady=(0, 8))
        self.fields = ctk.CTkFrame(self.body, fg_color="transparent")
        self.code = ctk.CTkLabel(self.fields, text="", text_color=T.TEXT_PRIMARY, anchor="w")
        self.code.pack(fill="x", pady=(0, 8))
        self.label(self.fields, "Duck breed")
        self.breed = ctk.CTkOptionMenu(self.fields, values=list(BREEDS.values()), command=lambda _: self.update_code(),
            fg_color=T.PANEL_LIGHT_ALT, button_color=T.PRIMARY_MAROON, text_color=T.TEXT_PRIMARY, height=34)
        self.breed.set(BREEDS.get(app.current_breed, BREEDS["KAYUMANGGI"]))
        self.breed.pack(fill="x", pady=(2, 8))
        self.incubator = self.entry(self.fields, "Incubator ID")
        self.set_date = self.entry(self.fields, "Incubation set date (YYYY-MM-DD)", "Date incubation began")
        self.original_count = self.entry(self.fields, "Original egg count", "Eggs originally placed into incubation")
        self.common = ctk.CTkFrame(self.body, fg_color="transparent")
        self.common.pack(fill="x", padx=12, pady=(6, 0))
        self.label(self.common, "Day 10 candling run", bold=True)
        self.target = self.entry(self.common, "Eggs to scan in this run")
        self.target.insert(0, str(app.target_egg_count))
        self.operator = self.entry(self.common, "Operator name")
        self.operator.insert(0, app.operator_name)
        self.notice = ctk.CTkLabel(self.body, text="Loading saved batches…", text_color=T.TEXT_MUTED,
                                  wraplength=450, justify="left", anchor="w")
        self.notice.pack(fill="x", padx=12, pady=(8, 12))
        self.update_code()
        app._jobs.submit(lambda: (app.db.list_available_batches(), app.db.get_batch_preferences()),
                         self.initial, self.failed)

    @staticmethod
    def label(parent, text, bold=False):
        ctk.CTkLabel(parent, text=text, text_color=T.TEXT_PRIMARY,
                     font=(T.FONT_FAMILY, 12, "bold" if bold else "normal")).pack(anchor="w")

    def entry(self, parent, label, placeholder=""):
        self.label(parent, label)
        widget = ctk.CTkEntry(parent, fg_color=T.PANEL_LIGHT_ALT, text_color=T.TEXT_PRIMARY,
                            placeholder_text=placeholder, placeholder_text_color=T.TEXT_MUTED, height=34)
        widget.pack(fill="x", pady=(2, 8))
        return widget

    def initial(self, result):
        if not self.winfo_exists():
            return
        records, prefs = result
        self.incubator.insert(0, prefs.get("incubator_id", ""))
        if prefs.get("breed") in BREEDS:
            self.breed.set(BREEDS[prefs["breed"]])
        self.loaded = True
        self.refresh(records)
        if not records:
            self.mode.set("New batch")
            self.change_mode("New batch")
        self.save.configure(state="normal")
        self.notice.configure(text="Saved batches remain available offline.")
        # Remote refresh cannot delay the local form or its Save action.
        def remote():
            try:
                records = self.app.sync_worker.fetch_active_batches()
                self.app._ui_events.put(lambda: self.refresh(records))
            except Exception:
                pass
        threading.Thread(target=remote, daemon=True, name="OvaLens-BatchRefresh").start()

    def refresh(self, records):
        if not self.winfo_exists() or self.busy:
            return
        self.records = {row["batch_id"]: row for row in records}
        self.populate_pick()

    def populate_pick(self):
        candidates = [row for row in self.records.values()
                      if self.mode.get() != "Complete details" or row.get("needs_details")]
        self.labels = {r["batch_code"]: r["batch_id"] for r in candidates}
        self.pick.configure(values=list(self.labels) or ["No saved batches — choose New batch"])
        identities = set(self.labels.values())
        selected = self.selected_id if self.selected_id in identities else next(iter(self.labels.values()), None)
        if selected:
            self.selected_id = selected
            self.pick.set(next(label for label, identity in self.labels.items() if identity == selected))
            self.show_summary()
        else:
            self.pick.set("No saved batches — choose New batch")

    def choose(self, label):
        self.pick.set(label)
        self.selected_id = self.labels.get(label)
        self.show_summary()
        if self.records.get(self.selected_id, {}).get("needs_details"):
            self.mode.set("Complete details")
        self.change_mode(self.mode.get())

    def show_summary(self):
        row = self.records.get(self.selected_id, {})
        if row.get("needs_details"):
            message = "Older local batch: enter its real incubation details once. Existing scans keep their IDs."
        elif row:
            status = "Synced" if row.get("synced_at") else "Saved locally · registration pending"
            set_day = datetime.fromisoformat(row["set_date"]).astimezone(FARM_TIMEZONE).strftime("%Y-%m-%d")
            message = f"{BREEDS[row['breed']]} · {row['incubator_id']} · {row['initial_egg_count']} original eggs\nSet: {set_day} · {status}"
            if row.get("sync_error"):
                message += "\n" + row["sync_error"]
        else:
            message = "Choose New batch to save the first incubation record."
        self.summary.configure(text=message)

    def change_mode(self, mode):
        if self.busy:
            return
        self.pick_frame.pack_forget()
        self.fields.pack_forget()
        if mode != "New batch":
            self.pick_frame.pack(fill="x", padx=12, before=self.common)
        if mode != "Existing batch":
            self.fields.pack(fill="x", padx=12, before=self.common)
        self.save.configure(text="Create & use batch" if mode == "New batch" else "Save details & use batch" if mode == "Complete details" else "Use batch")
        if mode != "New batch":
            self.populate_pick()
        self.update_code()

    def update_code(self):
        if self.mode.get() == "Complete details":
            self.code.configure(text="Preserve code: " + self.records.get(self.selected_id, {}).get("batch_code", "Choose a batch above"))
        else:
            breed = next(key for key, label in BREEDS.items() if label == self.breed.get())
            self.code.configure(text=f"Code: BATCH-{datetime.now(FARM_TIMEZONE):%Y%m%d}-{breed[:3]}-{self.draft_id[:8].upper()}")

    def failed(self, message):
        if self.winfo_exists():
            self.busy = False
            self.save.configure(state="normal" if self.loaded else "disabled")
            self.cancel.configure(state="normal")
            self.mode.configure(state="normal")
            self.notice.configure(text=str(message), text_color=T.REJECT_RED_TEXT)

    def apply(self):
        if self.busy or not self.loaded:
            return
        mode = self.mode.get()
        row = self.records.get(self.selected_id)
        try:
            if mode == "Existing batch":
                if not row or row.get("needs_details"):
                    self.mode.set("Complete details")
                    self.change_mode("Complete details")
                    raise ValueError("Complete the selected batch's incubation details first.")
                record = row
            else:
                if mode == "Complete details" and (not row or not row.get("needs_details")):
                    raise ValueError("Choose an older batch that needs details. Saved batch details cannot be overwritten here.")
                breed = next(key for key, label in BREEDS.items() if label == self.breed.get())
                record = new_batch_record(breed, self.incubator.get(), self.original_count.get(), self.set_date.get(),
                    batch_id=row["batch_id"] if mode == "Complete details" else self.draft_id,
                    batch_code=row["batch_code"] if mode == "Complete details" else None)
            batch_id, operator, target = validate_batch_config(record["batch_id"], self.operator.get(), self.target.get(), "DAY_10")
            if target > record["initial_egg_count"]:
                raise ValueError("This run's scan target cannot exceed the original egg count.")
        except ValueError as exc:
            self.failed(str(exc))
            return
        self.busy = True
        generation = self.app._operation_generation
        self.save.configure(state="disabled", text="Saving locally…")
        self.cancel.configure(state="disabled")
        self.mode.configure(state="disabled")
        self.notice.configure(text="Saving batch and selection on this station…", text_color=T.TEXT_MUTED)
        def work():
            if mode != "Existing batch":
                self.app.db.save_local_batch(record, self.app.device_id, operator)
            return self.app.db.remember_batch_selection(batch_id, operator, target)
        def saved(batch):
            if not self.winfo_exists():
                return
            self.busy = False
            if self.app._closing or generation != self.app._operation_generation:
                self.failed("Batch saved locally. Setup was stopped; select it when the station is idle.")
                return
            self.app._apply_batch_selection(batch, operator, target)
            self.app._animate_modal_close(self)
        try:
            self.app._jobs.submit(work, saved, self.failed)
        except (queue.Full, RuntimeError) as exc:
            self.failed(str(exc))

    def close(self):
        if not self.busy:
            self.app._animate_modal_close(self)
