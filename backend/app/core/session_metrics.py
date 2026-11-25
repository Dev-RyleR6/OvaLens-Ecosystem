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
