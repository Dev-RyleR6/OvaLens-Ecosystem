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
