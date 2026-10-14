"""Batch creation data; incubation inventory and a candling run are separate."""
from datetime import datetime, time, timezone, timedelta
from uuid import uuid4

BREEDS = {"KAYUMANGGI": "IP-Kayumanggi", "ITIM": "IP-Itim", "KHAKI": "IP-Khaki"}
FARM_TIMEZONE = timezone(timedelta(hours=8))
BATCH_FIELDS = ("batch_id", "batch_code", "breed", "incubator_id", "initial_egg_count", "set_date", "notes")


def validate_batch_record(record):
    result = {key: record.get(key) for key in BATCH_FIELDS}
    for key, maximum in (("batch_id", 64), ("batch_code", 64), ("incubator_id", 64)):
        value = result[key]
        minimum = 3 if key == "batch_code" else 1
        if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum:
            raise ValueError(f"{key.replace('_', ' ').capitalize()} must contain {minimum}–{maximum} characters.")
        result[key] = value.strip()
    if result["breed"] not in BREEDS:
        raise ValueError("Choose IP-Kayumanggi, IP-Itim or IP-Khaki.")
    quantity = result["initial_egg_count"]
    if type(quantity) is not int or not 1 <= quantity <= 1000000:
        raise ValueError("Original egg count must be a whole number from 1 to 1,000,000.")
    try:
        stamp = datetime.fromisoformat(result["set_date"])
        if stamp.tzinfo is None:
            raise ValueError()
    except (ValueError, TypeError):
        raise ValueError("Enter the actual incubation set date (YYYY-MM-DD).") from None
    if stamp.astimezone(FARM_TIMEZONE).date() > datetime.now(FARM_TIMEZONE).date():
        raise ValueError("Incubation set date cannot be in the future.")
    result["set_date"] = stamp.astimezone(timezone.utc).isoformat()
    notes = result["notes"]
    if notes is not None and (not isinstance(notes, str) or len(notes) > 2000):
        raise ValueError("Notes must contain at most 2,000 characters.")
    return result


def new_batch_record(breed, incubator_id, original_count, set_date, *, batch_id=None, batch_code=None):
    """Generate identity once, or preserve a legacy code and its existing scans."""
    try:
        if isinstance(original_count, bool) or not isinstance(original_count, (str, int)):
            raise ValueError()
        quantity = int(original_count)
        day = datetime.strptime(set_date, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        raise ValueError("Enter a whole original egg count and set date as YYYY-MM-DD.") from None
    identity = batch_id or str(uuid4())
    code = batch_code or f"BATCH-{datetime.now(FARM_TIMEZONE):%Y%m%d}-{breed[:3]}-{identity[:8].upper()}"
    return validate_batch_record({"batch_id": identity, "batch_code": code, "breed": breed,
        "incubator_id": incubator_id, "initial_egg_count": quantity,
        "set_date": datetime.combine(day, time.min, FARM_TIMEZONE).isoformat(), "notes": None})


def same_batch(left, right):
    """Compare registration acknowledgements without relying on timestamp spelling."""
    return validate_batch_record(left) == validate_batch_record(right)
