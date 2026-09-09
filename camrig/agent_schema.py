"""Stable, host-facing CamRig Agent schema.

This module is intentionally separate from the embedded expression runtime.  It
is safe to import from Cinema 4D's Python console/bridge, but is never embedded
in a scene tag.
"""
import math
from . import config

CONTROL_SPECS = {
    "orbit": (config.UD_ORBIT, None, None), "radius": (config.UD_RADIUS, 0, None),
    "offset_x": (config.UD_OFFSET_X, -2000, 2000), "offset_y": (config.UD_OFFSET_Y, -2000, 2000),
    "offset_z": (config.UD_OFFSET_Z, -2000, 2000), "rot_h": (config.UD_ROT_H, -180, 180),
    "rot_p": (config.UD_ROT_P, -180, 180), "rot_b": (config.UD_ROT_B, -180, 180),
    "focal_length": (config.UD_FOCAL, 10, 200), "focus_distance": (config.UD_FOCUS_DISTANCE, 1, 100000),
    "shake_enable": (config.UD_SHAKE_ENABLE, None, None), "shake_pos": (config.UD_SHAKE_POS, 0, 100),
    "shake_rot": (config.UD_SHAKE_ROT, 0, 20), "drift_pos": (config.UD_DRIFT_POS, 0, 50),
    "drift_rot": (config.UD_DRIFT_ROT, 0, 10), "drift_frequency": (config.UD_DRIFT_FREQ, .01, 1),
    "use_target": (config.UD_USE_TARGET, None, None), "target_blend": (config.UD_TARGET_BLEND, 0, 100),
    "free_camera": (config.UD_FREE_CAMERA, None, None), "center_x": (config.UD_CENTER_X, None, None),
    "height": (config.UD_HEIGHT, None, None), "center_z": (config.UD_CENTER_Z, None, None),
    "plane_h": (config.UD_PLANE_H, None, None), "plane_p": (config.UD_PLANE_P, None, None),
    "plane_b": (config.UD_PLANE_B, None, None), "aim_x": (config.UD_AIM_X, None, None),
    "aim_y": (config.UD_AIM_Y, None, None), "aim_z": (config.UD_AIM_Z, None, None),
    "spring_amount": (config.UD_SPRING_AMOUNT, 0, 100), "spring_response": (config.UD_SPRING_RESPONSE, 0, 100),
    "spring_damping": (config.UD_SPRING_DAMPING, 0, 100), "focus_mode": (config.UD_FOCUS_MODE, 0, 2),
    "focus_offset": (config.UD_FOCUS_OFFSET, None, None),
}
LINK_KEYS = {"target_a": config.UD_TARGET_A, "target_b": config.UD_TARGET_B,
             "orbit_center": config.UD_ORBIT_CENTER, "focus_target": config.UD_FOCUS_TARGET}
ALIASES = {"plane_heading": "plane_h", "plane_tilt": "plane_p", "plane_bank": "plane_b"}

def canonical_controls(controls):
    """Normalize documented aliases, refusing conflicting spellings."""
    if not isinstance(controls, dict): raise ValueError("INVALID_CONTROL: controls must be an object")
    result = dict(controls)
    for alias, key in ALIASES.items():
        if alias in result:
            if key in result: raise ValueError("INVALID_CONTROL: both %s and %s were supplied" % (alias, key))
            result[key] = result.pop(alias)
    return result

def validate_controls(controls):
    controls = canonical_controls(controls)
    for key, value in controls.items():
        if key not in CONTROL_SPECS: raise ValueError("INVALID_CONTROL: " + key)
        if key in ("shake_enable", "use_target", "free_camera"):
            if not isinstance(value, bool): raise ValueError("INVALID_CONTROL: %s must be boolean" % key)
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise ValueError("INVALID_CONTROL: %s must be a finite number" % key)
        if key == "focus_mode" and not isinstance(value, int):
            raise ValueError("INVALID_CONTROL: focus_mode must be 0, 1, or 2")
        _, low, high = CONTROL_SPECS[key]
        if low is not None and value < low or high is not None and value > high:
            raise ValueError("INVALID_CONTROL: %s must be in [%s, %s]" % (key, low, high))
    return controls
