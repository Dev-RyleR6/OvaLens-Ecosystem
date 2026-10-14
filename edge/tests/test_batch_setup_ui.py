"""Native offline batch form, remembered selection and legacy recovery; fake hardware."""
from test_camera_preview_ui import preview_app, hidden_ui
from test_live_camera_ui import pump
from test_session_sync import local_run


def fill(widget, value):
    widget.delete(0, "end")
    widget.insert(0, str(value))


def open_setup(app):
    app.sync_worker.fetch_active_batches = lambda: app.db.list_available_batches()
    app.deiconify()
    app.open_batch_setup_dialog()
    dialog = app._batch_setup_window
    pump(app, lambda: dialog.loaded)
    return dialog


def finish(app):
    app.shutdown()
    app.mainloop()


def test_new_batch_saves_offline_with_separate_inventory_and_remembers_selection(hidden_ui, tmp_path):
    app, _, _ = preview_app(tmp_path)
    try:
        dialog = open_setup(app)
        assert dialog.mode.get() == "New batch"
        assert dialog.original_count.get() == dialog.set_date.get() == dialog.incubator.get() == ""
        for size in ("1024x720", "1280x860"):
            app.geometry(size)
            app.update()
            for button in (dialog.save, dialog.cancel):
                assert button.winfo_ismapped()
                assert button.winfo_rooty() + button.winfo_height() <= dialog.winfo_rooty() + dialog.winfo_height()
        fill(dialog.incubator, "FARM-INC-7")
        fill(dialog.set_date, "2026-01-01")
        fill(dialog.original_count, 100)
        fill(dialog.target, 20)
        fill(dialog.operator, "Worker Jay")
        identity = dialog.draft_id
        dialog.apply()
        pump(app, lambda: app.current_batch_id == identity)
        saved = app.db.get_local_batch(identity)
        assert saved["initial_egg_count"] == 100 and saved["synced_at"] is None
        assert app.target_egg_count == 20 and app._batch_record_ready
        assert app.db.get_batch_preferences()["incubator_id"] == "FARM-INC-7"
    finally:
        finish(app)
    reopened, _, _ = preview_app(tmp_path)
    try:
        pump(reopened, lambda: reopened.current_batch_id == identity)
        assert reopened.operator_name == "Worker Jay" and reopened.target_egg_count == 20
    finally:
        finish(reopened)


def test_legacy_details_preserve_prior_scan_and_do_not_infer_inventory(hidden_ui, tmp_path):
    app, _, _ = preview_app(tmp_path)
    session = local_run(app.db, "LEGACY-KAY-01")
    original = app.db.get_uncommitted_scans()[0]
    app.current_batch_id = "LEGACY-KAY-01"
    try:
        dialog = open_setup(app)
        dialog.choose("LEGACY-KAY-01")
        assert dialog.mode.get() == "Complete details"
        assert not dialog.original_count.get() and not dialog.set_date.get()
        fill(dialog.incubator, "INC-7")
        fill(dialog.set_date, "2026-01-01")
        fill(dialog.original_count, 100)
        fill(dialog.target, 10)
        dialog.apply()
        pump(app, lambda: app._batch_record_ready)
        assert app.current_batch_id == "LEGACY-KAY-01"
        assert app.db.get_session_stats(session)["batch_id"] == "LEGACY-KAY-01"
        assert app.db.get_uncommitted_scans()[0] == original
    finally:
        finish(app)


def test_invalid_or_failed_save_never_activates_a_batch_and_stop_cancels_late_selection(hidden_ui, tmp_path, monkeypatch):
    app, _, _ = preview_app(tmp_path)
    try:
        dialog = open_setup(app)
        previous = app.current_batch_id
        fill(dialog.incubator, "INC-7")
        fill(dialog.set_date, "2026-01-01")
        fill(dialog.original_count, 10)
        fill(dialog.target, 11)
        dialog.apply()
        assert "cannot exceed" in dialog.notice.cget("text") and app.current_batch_id == previous
        fill(dialog.target, 10)
        original_save = app.db.save_local_batch
        monkeypatch.setattr(app.db, "save_local_batch", lambda *a: (_ for _ in ()).throw(OSError("disk unavailable")))
        dialog.apply()
        pump(app, lambda: not dialog.busy)
        assert "disk unavailable" in dialog.notice.cget("text") and app.current_batch_id == previous
        monkeypatch.setattr(app.db, "save_local_batch", original_save)
        dialog.apply()
        app._operation_generation += 1  # STOP happened before the queued storage callback.
        pump(app, lambda: not dialog.busy)
        assert app.db.get_local_batch(dialog.draft_id) and app.current_batch_id == previous
        assert "Setup was stopped" in dialog.notice.cget("text")
    finally:
        finish(app)
