"""Elapsed run metrics derived solely from persisted session evidence."""
from datetime import datetime
import math


def session_metrics(started_at, ended_at, total_scanned):
    unavailable = {"duration_seconds": None, "eggs_per_minute": None}
    try:
        start = datetime.fromisoformat(started_at) if isinstance(started_at, str) else started_at
        end = datetime.fromisoformat(ended_at) if isinstance(ended_at, str) else ended_at
        if not start or not end or start.utcoffset() is None or end.utcoffset() is None:
            return unavailable
        seconds = (end - start).total_seconds()
        if not math.isfinite(seconds) or seconds < 0:
            return unavailable
        rate = total_scanned * 60 / seconds if seconds > 0 else None
        return {"duration_seconds": seconds, "eggs_per_minute": rate}
    except (ValueError, TypeError, AttributeError, OverflowError):
        return unavailable


def estimate_capacity(total_scanned, duration_seconds, minutes):
    """Return whole scan capacity, or None when evidence/input is insufficient."""
    try:
        minutes = float(minutes)
        if not math.isfinite(minutes) or minutes <= 0 or not duration_seconds or duration_seconds <= 0 or total_scanned <= 0:
            return None
        estimate = total_scanned * minutes * 60 / duration_seconds
        return math.floor(estimate) if math.isfinite(estimate) else None
    except (TypeError, ValueError, OverflowError):
        return None


def format_duration(seconds):
    if seconds is None:
        return "Unavailable"
    hours, remainder = divmod(int(seconds), 3600)
    minutes, whole_seconds = divmod(remainder, 60)
    fraction = f"{seconds % 1:.6f}"[1:].rstrip("0").rstrip(".")
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d}{fraction}"
