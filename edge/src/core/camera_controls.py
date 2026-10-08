"""Camera tuning values; retain native driver units and unset preferences."""
from dataclasses import replace
import math

NUMERIC_CONTROLS = {
    "focus": "Focus", "exposure": "Exposure", "gain": "Gain",
    "white_balance": "White balance (K)", "brightness": "Brightness",
    "contrast": "Contrast", "saturation": "Saturation", "sharpness": "Sharpness",
}
AUTO_CONTROLS = {"autofocus": "Autofocus", "auto_exposure": "Auto exposure",
                 "auto_white_balance": "Auto white balance"}
MANUAL_PAIRS = {"autofocus": "focus", "auto_exposure": "exposure", "auto_white_balance": "white_balance"}


def validate_slider_ranges(ranges):
    if not isinstance(ranges, dict):
        raise ValueError("Camera slider ranges must be a mapping")
    for name, span in ranges.items():
        if (name not in NUMERIC_CONTROLS or not isinstance(span, (list, tuple)) or len(span) != 2
                or any(type(v) not in (int, float) or not math.isfinite(v) for v in span)
                or not span[0] < span[1] or not math.isfinite(span[1] - span[0])):
            raise ValueError("Each camera slider range needs finite minimum < maximum")


def slider_span(name, identity, value=None, ranges=None):
    """Editable UI spans; never claim these are the webcam's supported limits."""
    defaults = {"focus": (0, 255), "exposure": (-13, 0) if identity.endswith(":DSHOW") else (1, 1000),
                "gain": (0, 255), "white_balance": (2000, 8000), "brightness": (-64, 255),
                "contrast": (0, 255), "saturation": (0, 255), "sharpness": (0, 10)}
    low, high = (ranges or {}).get(name, defaults[name])
    # Preserve saved/current values outside a starting span instead of clamping them.
    if value is not None and math.isfinite(value):
        low, high = min(low, value), max(high, value)
    if not math.isfinite(high - low):
        raise ValueError("Value is too large for a slider span; use a smaller range")
    return float(low), float(high)


def exposure_modes(identity, normalized=False):
    backend = identity.rsplit(":", 1)[-1].upper()
    if backend == "DSHOW":
        return {"On": 1.0, "Off": 0.0}
    if backend in {"V4L2", "V4L"}:
        return {"On": .75, "Off": .25} if normalized else {"On": 3.0, "Off": 1.0}
    return {}


def mode_label(value, values):
    if value is None:
        return "Unchanged"
    return next((name for name, native in values.items() if value == native), "Saved value")


def camera_values(current, text_values, modes, exposure):
    result = replace(current)
    for name in NUMERIC_CONTROLS:
        text = text_values[name].strip()
        try:
            value = float(text) if text else None
        except ValueError:
            raise ValueError(f"{NUMERIC_CONTROLS[name]} must be a number or blank.") from None
        if value is not None and not math.isfinite(value):
            raise ValueError(f"{NUMERIC_CONTROLS[name]} must be finite.")
        setattr(result, name, value)
    for name in AUTO_CONTROLS:
        mode = modes[name]
        values = exposure if name == "auto_exposure" else {"On": 1.0, "Off": 0.0}
        if mode == "Unchanged":
            setattr(result, name, None)
        elif mode == "Saved value":
            pass
        elif mode in values:
            setattr(result, name, values[mode])
        else:
            raise ValueError("This camera backend needs native auto-exposure values in Tools / Settings.")
        if mode == "On":
            setattr(result, MANUAL_PAIRS[name], None)
    return result
