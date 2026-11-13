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
        self.continue_to_prepare = getattr(app, "_prepare_after_selection", False)
        app._prepare_after_selection = False
        self.busy, self.loaded = False, False
        self.draft_id = str(uuid4())
        self.title("Set up run")
        self.geometry("600x640")
        self.minsize(540, 500)
        self.configure(fg_color=T.BG_LIGHT)
        self.transient(app)
        self.grab_set()
        app._center_window(self, 600, 640)
        self.protocol("WM_DELETE_WINDOW", self.close)
        ctk.CTkLabel(self, text="Set up run", font=(T.FONT_FAMILY, 20, "bold"),
                     text_color=T.TEXT_PRIMARY).pack(anchor="w", padx=20, pady=(16, 2))
        ctk.CTkLabel(self, text="Save on this station. Registration and scans sync automatically.",
                     text_color=T.TEXT_MUTED, font=(T.FONT_FAMILY, 12)).pack(anchor="w", padx=20, pady=(0, 12))
        self.notice = ctk.CTkLabel(self, text="Loading saved batches…", text_color=T.TEXT_MUTED,
                                  wraplength=450, justify="left", anchor="w")
        self.notice.pack(fill="x", padx=20, pady=(0, 6))
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
        self.operator_id = getattr(app, "operator_id", None)
        self.operator_records, self.operator_labels = {}, {}
        self.operator_area = ctk.CTkFrame(self.body, fg_color="transparent")
        self.operator_area.pack(fill="x", padx=12, pady=(12, 0))
        self.label(self.operator_area, "Registered operator", bold=True)
        self.operator_summary = ctk.CTkLabel(self.operator_area, text="Choose registered staff", anchor="w",
                                            wraplength=450, text_color=T.TEXT_PRIMARY)
        self.operator_summary.pack(fill="x")
        operator_actions = ctk.CTkFrame(self.operator_area, fg_color="transparent")
        operator_actions.pack(fill="x", pady=4)
        ctk.CTkButton(operator_actions, text="Change operator", height=44,
                     fg_color=T.PANEL_LIGHT_ALT, text_color=T.TEXT_PRIMARY,
                     command=self.change_operator).pack(side="left")
        self.operator = ctk.CTkOptionMenu(self.operator_area, values=["Loading registered staff..."],
            command=self.choose_operator, height=44, fg_color=T.PANEL_LIGHT_ALT,
            button_color=T.PRIMARY_MAROON, text_color=T.TEXT_PRIMARY)
        self.operator_status = ctk.CTkLabel(self.operator_area, text="", wraplength=450,
                                           justify="left", text_color=T.TEXT_MUTED)
        self.operator_status.pack(fill="x")
        ctk.CTkButton(operator_actions, text="Refresh staff", height=44, fg_color=T.PANEL_LIGHT_ALT,
                     text_color=T.TEXT_PRIMARY, command=app.refresh_registered_operators).pack(side="left", padx=(8, 0))
        self.mode = ctk.CTkSegmentedButton(self.body, values=["Choose batch", "Create batch"],
            selected_color="#EEDADA", selected_hover_color="#E5C4C4",
            unselected_color=T.PANEL_LIGHT_ALT, text_color=T.TEXT_PRIMARY, command=self.change_mode)
        self.mode.pack(fill="x", padx=12, pady=12)
        self.mode.set("Choose batch")
        self.pick_frame = ctk.CTkFrame(self.body, fg_color="transparent")
        self.pick_frame.pack(fill="x", padx=12)
        self.label(self.pick_frame, "Saved batch")
        self.label(self.pick_frame, "Search batch code or incubator")
        self.search_text = ctk.StringVar(master=self, value="")
        self.search = ctk.CTkEntry(self.pick_frame, textvariable=self.search_text, height=44,
                                  placeholder_text="Search batch code or incubator")
        self.search.pack(fill="x", pady=(2, 6))
        self.search_text.trace_add("write", lambda *_: self.populate_pick())
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
        self.original_count.bind("<KeyRelease>", lambda _: self.update_target())
        self.common = ctk.CTkFrame(self.body, fg_color="transparent")
        self.common.pack(fill="x", padx=12, pady=(6, 0))
        self.label(self.common, "Day 10 candling run", bold=True)
        self._quantity_custom = False
        self.target_summary = ctk.CTkLabel(self.common, text="Run target: choose a batch", anchor="w", text_color=T.TEXT_PRIMARY)
        self.target_summary.pack(fill="x")
        ctk.CTkButton(self.common, text="Change quantity", height=44, fg_color=T.PANEL_LIGHT_ALT,
                     text_color=T.TEXT_PRIMARY, command=self.change_quantity).pack(anchor="w", pady=4)
        self.target = ctk.CTkEntry(self.common, height=44)
        self.update_code()
        app._jobs.submit(lambda: (app.db.list_available_batches(), app.db.get_batch_preferences(), app.db.get_operator_state()),
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
        records, prefs, staff = result
        self.prefs = prefs
        self.refresh_operators(staff)
        self.incubator.insert(0, prefs.get("incubator_id", ""))
        if prefs.get("breed") in BREEDS:
            self.breed.set(BREEDS[prefs["breed"]])
        self.loaded = True
        self.refresh(records)
        if not records:
            self.mode.set("Create batch")
            self.change_mode("Create batch")
        self.save.configure(state="normal")
        self.notice.configure(text="Saved batches remain available offline.")
        self.app.refresh_registered_operators()
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
        query = self.search_text.get().strip().casefold()
        candidates = [row for row in self.records.values()
                      if (self.mode.get() != "Complete details" or row.get("needs_details"))
                      and (not query or query in (row["batch_code"] + " " + str(row.get("incubator_id", ""))).casefold())]
        self.labels = {r["batch_code"]: r["batch_id"] for r in candidates}
        self.pick.configure(values=list(self.labels) or ["No saved batches — choose New batch"])
        identities = set(self.labels.values())
        selected = self.selected_id if self.selected_id in identities else next(iter(self.labels.values()), None)
        if selected:
            self.selected_id = selected
            self.pick.set(next(label for label, identity in self.labels.items() if identity == selected))
            self.show_summary()
            self.update_target()
        else:
            self.pick.set("No saved batches — choose New batch")

    def choose(self, label):
        self.pick.set(label)
        selected = self.labels.get(label)
        if selected != self.selected_id:
            self._quantity_custom = False
        self.selected_id = selected
        self.show_summary()
        if self.records.get(self.selected_id, {}).get("needs_details"):
            self.mode.configure(values=["Choose batch", "Create batch", "Complete details"])
            self.mode.set("Complete details")
        elif self.mode.get() == "Complete details":
            self.mode.set("Choose batch")
        self.change_mode(self.mode.get())

    def refresh_operators(self, state):
        if not self.winfo_exists() or self.busy:
            return
        self.operator_records = {r["user_id"]: r for r in state["operators"]}
        self.operator_labels = {}
        for record in state["operators"]:
            name = record["full_name"]
            name = name if len(name) <= 35 else name[:32] + "..."
            label = f"{name} ({record['role']}) - {record['user_id'][:8]}"
            if label in self.operator_labels:
                previous = self.operator_labels.pop(label)
                self.operator_labels[label + " / " + previous] = previous
                label += " / " + record["user_id"]
            self.operator_labels[label] = record["user_id"]
        if self.operator_id is None:
            self.operator_id = state.get("selected_id")
        if self.operator_id not in self.operator_records:
            self.operator_id = None
        self.operator.configure(values=list(self.operator_labels) or ["No registered staff cached"])
        label = next((label for label, identity in self.operator_labels.items() if identity == self.operator_id), "Choose operator")
        self.operator.set(label)
        self.operator_summary.configure(text=self.operator_records[self.operator_id]["full_name"] if self.operator_id else "Choose registered staff")
        self.operator_status.configure(text="Cached registered staff are available offline." if self.operator_records else
            "Connect once and Refresh staff. Register active staff in Dashboard > Users. Preview and settings remain available.")
        if not self.operator_id:
            self.change_operator()

    def change_operator(self):
        self.operator.pack(fill="x", before=self.operator_status, pady=4)

    def choose_operator(self, label):
        self.operator_id = self.operator_labels.get(label)
        if self.operator_id:
            self.operator_summary.configure(text=self.operator_records[self.operator_id]["full_name"])

    def change_quantity(self):
        self._quantity_custom = True
        self.target.pack(fill="x", pady=4)
        self.target.focus_set()

    def update_target(self):
        row = self.records.get(self.selected_id, {})
        if not self._quantity_custom:
            try:
                count = min(100000, int(self.original_count.get() if self.mode.get() in {"Create batch", "Complete details"} else row.get("initial_egg_count", 0)))
            except ValueError:
                count = 0
            prefs = getattr(self, "prefs", {})
            if self.mode.get() == "Choose batch" and prefs.get("batch_id") == self.selected_id:
                count = prefs.get("egg_count", count)
            self.target.delete(0, "end")
            self.target.insert(0, str(count))
        self.target_summary.configure(text=f"Run target: {self.target.get()} scans (maximum 100,000 per run)")

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
        if mode != "Create batch":
            self.pick_frame.pack(fill="x", padx=12, before=self.common)
        if mode != "Choose batch":
            self.fields.pack(fill="x", padx=12, before=self.common)
        self.save.configure(text="Create & use batch" if mode == "Create batch" else "Save details & use batch" if mode == "Complete details" else "Use batch")
        if mode != "Create batch":
            self.populate_pick()
        self.update_target()
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
            if not self.operator_id or self.operator_id not in self.operator_records:
                raise ValueError("Select a registered operator. Connect once and Refresh staff if none are cached.")
            selected_operator = self.operator_records[self.operator_id]
            if mode == "Choose batch":
                if not row or row.get("needs_details"):
                    self.mode.configure(values=["Choose batch", "Create batch", "Complete details"])
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
            if not self._quantity_custom and mode != "Choose batch":
                self.target.delete(0, "end")
                self.target.insert(0, str(min(100000, record["initial_egg_count"])))
            batch_id, operator, target = validate_batch_config(record["batch_id"], selected_operator["full_name"], self.target.get(), "DAY_10")
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
            self.app.db.select_operator(selected_operator["user_id"])
            if mode != "Choose batch":
                self.app.db.save_local_batch(record, self.app.device_id, operator, selected_operator["user_id"])
            return self.app.db.remember_batch_selection(batch_id, operator, target)
        def saved(batch):
            if not self.winfo_exists():
                return
            self.busy = False
            if self.app._closing or generation != self.app._operation_generation:
                self.failed("Batch saved locally. Setup was stopped; select it when the station is idle.")
                return
            self.app._apply_batch_selection(batch, operator, target)
            self.app.operator_id = selected_operator["user_id"]
            self.app._set_session_active_state(False)
            if self.continue_to_prepare:
                self.app._animate_modal_close(self, on_close=lambda: self.app.after_idle(self.app.open_preparation_confirmation))
            else:
                self.app._animate_modal_close(self)
        try:
            self.app._jobs.submit(work, saved, self.failed)
        except (queue.Full, RuntimeError) as exc:
            self.failed(str(exc))

    def close(self):
        if not self.busy:
            self.app._animate_modal_close(self)
