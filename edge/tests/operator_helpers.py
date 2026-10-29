"""Registered staff fixtures for hardware-free native workflow checks."""
STAFF_ID = "e47a7caa-4da2-4c28-8d5f-e54f38da7901"


def select_staff(app, name="Worker Jay"):
    record = {"user_id": STAFF_ID, "full_name": name, "role": "OPERATOR"}
    app.db.cache_operators([record])
    app.db.select_operator(STAFF_ID)
    app.operator_id, app.operator_name = STAFF_ID, name
    return record
