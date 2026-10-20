"""Shared operator states and batch validation for manual diagnostics."""
from enum import Enum


class OperatorState(str, Enum):
    READY = "READY"
    CAMERA_STARTING = "CAMERA_STARTING"
    CLASSIFYING = "CLASSIFYING"
    SAVING = "SAVING"
    REVIEW = "MANUAL_REVIEW"
    ERROR = "ERROR"
    STOPPING = "STOPPING"
    RECOVERY = "RECOVERY_REQUIRED"
    COMPLETE = "DIAGNOSTICS_COMPLETE"


def validate_batch_config(batch_id, operator, quantity, stage):
    """Reject invalid values rather than silently changing operator input."""
    batch_id, operator = str(batch_id).strip(), str(operator).strip()
    if not batch_id or len(batch_id) > 100:
        raise ValueError("Batch code must contain 1 to 100 characters.")
    if not operator or len(operator) > 100:
        raise ValueError("Operator name must contain 1 to 100 characters.")
    try:
        count = int(quantity)
    except (ValueError, TypeError):
        raise ValueError("Egg target must be a whole number from 1 to 100,000.") from None
    if isinstance(quantity, bool) or not isinstance(quantity, (int, str)) or not 1 <= count <= 100000:
        raise ValueError("Egg target must be a whole number from 1 to 100,000.")
    if stage != "DAY_10":
        raise ValueError("Only Day 10 candling is supported.")
    return batch_id, operator, count
