# -*- coding: utf-8 -*-
"""
Встраиваемый рантайм CamRig для Python Tag (полный текст в TPYTHON_CODE).
Не импортирует пакет camrig — при изменении логики синхронизируйте с config.py и python_tag_logic.py.
Константа EMBEDDED_RUNTIME_VERSION должна совпадать с camrig.config.PLUGIN_VERSION.

Точки входа тега C4D: main(), message() (globals: op, doc).
"""
import math
import c4d
from c4d import utils
from collections import namedtuple
from typing import Optional, Any, Dict

# --- Зеркало camrig/config.py: версию держать как PLUGIN_VERSION в config.py ---
EMBEDDED_RUNTIME_VERSION = "1.5.0"

# --- Зеркало camrig/config.py (строки UD и имена объектов) ---
DEFAULT_ORBIT = 0.0
DEFAULT_RADIUS = 500.0
DEFAULT_ROT_H = 0.0
DEFAULT_ROT_P = 0.0
DEFAULT_ROT_B = 0.0
DEFAULT_SHAKE_POS = 5.0
DEFAULT_SHAKE_ROT = 1.0
DEFAULT_DRIFT_POS = 0.0
DEFAULT_DRIFT_ROT = 0.0
DEFAULT_DRIFT_FREQ = 0.08
DEFAULT_USE_TARGET = True
DEFAULT_FREE_CAMERA = False

UD_ORBIT = "Orbit"
UD_RADIUS = "Radius"
UD_OFFSET_X = "Offset X"
UD_OFFSET_Y = "Offset Y"
UD_OFFSET_Z = "Offset Z"
UD_ROT_H = "Rot H"
UD_ROT_P = "Rot P"
UD_ROT_B = "Rot B"
UD_FOCAL = "Focal Length"
UD_FOCUS_DISTANCE = "Focus Distance"
UD_SHAKE_ENABLE = "Shake Enable"
UD_SHAKE_POS = "Shake Pos"
UD_SHAKE_ROT = "Shake Rot"
UD_DRIFT_POS = "Drift Pos"
UD_DRIFT_ROT = "Drift Rot"
UD_DRIFT_FREQ = "Drift Frequency"
UD_TARGET_A = "Target A"
UD_TARGET_B = "Target B"
UD_USE_TARGET = "Use Target"
UD_TARGET_BLEND = "Target Blend"
UD_FREE_CAMERA = "Free Camera"

TARGET_A_NAME = "Target_A"
TARGET_B_NAME = "Target_B"
LOOK_TARGET_NAME = "Look_Target"
FOCUS_NAME = "Focus"
LEGACY_INERTIA_FOLLOW_PREFIX = "Inertia_Follow"

RigObjects = namedtuple(
    "RigObjects",
    "rig circle follow offset cam fx align vib target_a target_b look_target target_expr focus",
)


def _get_bc_name_safe(bc: c4d.BaseContainer) -> str:
    try:
        return bc[c4d.DESC_NAME] or ""
    except Exception:
        return ""


def _read_all_user_data(obj: c4d.BaseObject) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for desc_id, bc in obj.GetUserDataContainer():
        name = _get_bc_name_safe(bc)
        if not name:
            continue
        try:
            result[name] = obj[desc_id]
        except (AttributeError, TypeError):
            pass
    return result


def _collect_rig_named_children(rig: c4d.BaseObject) -> Dict[str, c4d.BaseObject]:
    base_names = (TARGET_A_NAME, TARGET_B_NAME, LOOK_TARGET_NAME)
    found: Dict[str, c4d.BaseObject] = {}
    child = rig.GetDown()
    while child is not None:
        name = child.GetName()
        for base in base_names:
            if name.startswith(base):
                found[base] = child
                break
        if len(found) == len(base_names):
            break
        child = child.GetNext()
    return found


def get_rig_objects(circle: c4d.BaseObject, remove_vibrate: bool = False) -> Optional[RigObjects]:
    if circle is None:
        return None
    rig = circle.GetUp()
    if rig is None:
        return None

    children = _collect_rig_named_children(rig)
    target_a = children.get(TARGET_A_NAME)
    target_b = children.get(TARGET_B_NAME)
    look_target = children.get(LOOK_TARGET_NAME)
    if target_a is None or target_b is None or look_target is None:
        return None

    follow = circle.GetDown()
    if follow is None:
        return None
    first_child = follow.GetDown()
    if first_child is None:
        return None
    if first_child.GetName().startswith(LEGACY_INERTIA_FOLLOW_PREFIX):
        offset = first_child.GetDown()
    else:
        offset = first_child
    if offset is None:
        return None
    cam = offset.GetDown()
    if cam is None:
        return None
    fx = cam.GetDown()
    if fx is None:
        return None

    vib = fx.GetTag(c4d.Tvibrate)

    focus = None
    child_fx = fx.GetDown()
    while child_fx is not None:
        if child_fx.GetName().startswith(FOCUS_NAME):
            focus = child_fx
            break
        child_fx = child_fx.GetNext()

    align = follow.GetTag(c4d.Taligntospline)
    target_expr = cam.GetTag(c4d.Ttargetexpression)

    return RigObjects(
        rig=rig,
        circle=circle,
        follow=follow,
        offset=offset,
        cam=cam,
        fx=fx,
        align=align,
        vib=vib,
        target_a=target_a,
        target_b=target_b,
        look_target=look_target,
        target_expr=target_expr,
        focus=focus,
    )


def _safe_float(val: Any, default: float) -> float:
    try:
        value = float(val)
        return value if math.isfinite(value) else default
    except (TypeError, ValueError):
        return default


def _apply_orbit_radius(
    circle: c4d.BaseObject,
    align: Optional[c4d.BaseTag],
    orbit: Any,
    radius: Any,
) -> None:
    if radius is not None:
        circle[c4d.PRIM_CIRCLE_RADIUS] = max(0.0, _safe_float(radius, DEFAULT_RADIUS))
    if align and orbit is not None:
        align[c4d.ALIGNTOSPLINETAG_POSITION] = orbit_phase(orbit)


def _apply_offset(offset: c4d.BaseObject, offx: Any, offy: Any, offz: Any) -> None:
    if offx is not None and offy is not None and offz is not None:
        offset.SetRelPos(c4d.Vector(offx, offy, offz))


_FOCAL_LENGTH_ID = getattr(c4d, "RSCAMERAOBJECT_FOCAL_LENGTH", None) or getattr(c4d, "CAMERA_FOCUS", None)


def _apply_focal(cam: c4d.BaseObject, fx: c4d.BaseObject, focal: Any) -> None:
    if focal is None or _FOCAL_LENGTH_ID is None:
        return
    try:
        f = float(focal)
        if cam is not None:
            cam[camera_focal_id(cam)] = f
        if fx is not None:
            fx[camera_focal_id(fx)] = f
    except (TypeError, AttributeError):
        pass


def _noise_1d(t: float, seed: float) -> float:
    x = t + seed * 0.173
    n1 = math.sin(x * 1.0 + seed * 1.31)
    n2 = math.sin(x * 2.03 + seed * 2.17) * 0.5
    n3 = math.sin(x * 4.17 + seed * 0.79) * 0.25
    return (n1 + n2 + n3) / 1.75


def _apply_shake(
    fx: c4d.BaseObject,
    doc: Optional[c4d.documents.BaseDocument],
    shake_enable: Any,
    shake_pos: Any,
    shake_rot: Any,
    drift_pos: Any,
    drift_rot: Any,
    drift_freq: Any,
    roth: Any,
    rotp: Any,
    rotb: Any,
) -> None:
    base_h = _safe_float(roth, DEFAULT_ROT_H)
    base_p = _safe_float(rotp, DEFAULT_ROT_P)
    base_b = _safe_float(rotb, DEFAULT_ROT_B)

    time_sec = 0.0
    if doc is not None:
        try:
            time_sec = doc.GetTime().Get()
        except Exception:
            pass

    amp_drift_pos = max(0.0, _safe_float(drift_pos, DEFAULT_DRIFT_POS))
    amp_drift_rot = max(0.0, _safe_float(drift_rot, DEFAULT_DRIFT_ROT))
    drift_frequency = max(0.01, _safe_float(drift_freq, DEFAULT_DRIFT_FREQ))
    dt = time_sec * drift_frequency
    dx = _noise_1d(dt + 17.0, 101.0)
    dy = _noise_1d(dt + 41.0, 113.0)
    dz = _noise_1d(dt + 73.0, 127.0)

    if not shake_enable:
        fx.SetRelPos(c4d.Vector(dx * amp_drift_pos, dy * amp_drift_pos, dz * amp_drift_pos))
        fx.SetRelRot(
            c4d.Vector(
                utils.DegToRad(base_h + dx * amp_drift_rot),
                utils.DegToRad(base_p + dy * amp_drift_rot),
                utils.DegToRad(base_b + dz * amp_drift_rot),
            )
        )
        return

    amp_pos = max(0.0, _safe_float(shake_pos, DEFAULT_SHAKE_POS))
    amp_rot = max(0.0, _safe_float(shake_rot, DEFAULT_SHAKE_ROT))
    seed, freq = 1.0, 1.5
    t = time_sec * freq

    nx = _noise_1d(t + 0.0, seed + 11.0)
    ny = _noise_1d(t + 3.7, seed + 23.0)
    nz = _noise_1d(t + 7.9, seed + 37.0)

    fx.SetRelPos(c4d.Vector(nx * amp_pos + dx * amp_drift_pos, ny * amp_pos + dy * amp_drift_pos, nz * amp_pos + dz * amp_drift_pos))
    rot_h = base_h + nx * amp_rot + dx * amp_drift_rot
    rot_p = base_p + ny * amp_rot + dy * amp_drift_rot
    rot_b = base_b + nz * amp_rot + dz * amp_drift_rot
    fx.SetRelRot(c4d.Vector(utils.DegToRad(rot_h), utils.DegToRad(rot_p), utils.DegToRad(rot_b)))


def _apply_focus_distance(focus: Optional[c4d.BaseObject], distance: Any) -> None:
    if focus is None or distance is None:
        return
    try:
        d = max(1.0, float(distance))
        focus.SetRelPos(c4d.Vector(0, 0, d))
    except (TypeError, ValueError):
        pass


def _apply_target_blend(
    objs: RigObjects,
    ud: Dict[str, Any],
) -> None:
    link_a = ud.get(UD_TARGET_A)
    link_b = ud.get(UD_TARGET_B)
    obj_a = valid_target(link_a, objs) or objs.target_a
    obj_b = valid_target(link_b, objs)

    pos_a = obj_a.GetMg().off if obj_a else None
    pos_b = obj_b.GetMg().off if obj_b else None

    if pos_a is None:
        return

    if pos_b is not None:
        blend = ud.get(UD_TARGET_BLEND)
        t = max(0.0, min(100.0, float(blend) if blend is not None else 0.0)) / 100.0
        aim_pos = pos_a + (pos_b - pos_a) * t
    else:
        aim_pos = pos_a

    mg = objs.look_target.GetMg()
    aim_offset = c4d.Vector(*[_safe_float(ud.get(k), 0.0) for k in
                             ("Aim Offset X", "Aim Offset Y", "Aim Offset Z")])
    mg.off = aim_pos + objs.rig.GetMg().MulV(aim_offset)
    objs.look_target.SetMg(mg)


def _execute(op: c4d.BaseTag) -> None:
    circle = op.GetObject()
    objs = get_rig_objects(circle)
    if objs is None:
        return

    doc = op.GetDocument()
    ud = _read_all_user_data(objs.rig)
    if not ud:
        ud = _read_all_user_data(circle)

    apply_orbit_plane(objs, ud)
    _apply_orbit_radius(circle, objs.align, ud.get(UD_ORBIT), ud.get(UD_RADIUS))
    _apply_offset(objs.offset, ud.get(UD_OFFSET_X), ud.get(UD_OFFSET_Y), ud.get(UD_OFFSET_Z))
    _apply_focal(objs.cam, objs.fx, ud.get(UD_FOCAL))
    _apply_focus_distance(objs.focus, ud.get(UD_FOCUS_DISTANCE))
    _apply_shake(
        objs.fx,
        doc,
        ud.get(UD_SHAKE_ENABLE),
        ud.get(UD_SHAKE_POS),
        ud.get(UD_SHAKE_ROT),
        ud.get(UD_DRIFT_POS),
        ud.get(UD_DRIFT_ROT),
        ud.get(UD_DRIFT_FREQ),
        ud.get(UD_ROT_H),
        ud.get(UD_ROT_P),
        ud.get(UD_ROT_B),
    )

    use_target = ud.get(UD_USE_TARGET, DEFAULT_USE_TARGET)
    free_camera = ud.get(UD_FREE_CAMERA, DEFAULT_FREE_CAMERA)
    if objs.target_expr is not None:
        if use_target and not free_camera:
            objs.target_expr[c4d.TARGETEXPRESSIONTAG_LINK] = objs.look_target
            _apply_target_blend(objs, ud)
        else:
            objs.target_expr[c4d.TARGETEXPRESSIONTAG_LINK] = None


def main() -> None:
    """Точка входа Python Tag в сцене (global op)."""
    if op.GetName() == "CamRig Focus 1.5":
        execute_focus(op)
    else:
        _execute(op)


def message(mid: int, data) -> bool:
    return True


def orbit_phase(angle):
    """The track stores turns; only the spline parameter wraps."""
    return (_safe_float(angle, 0.0) % 360.0) / 360.0


def valid_target(target, objs):
    """Reject cross-document, self and driven descendants; never mutate a link."""
    if not isinstance(target, c4d.BaseObject) or target.GetDocument() != objs.rig.GetDocument():
        return None
    node = target
    while node is not None:
        if node == objs.circle or node == objs.look_target:
            return None
        node = node.GetUp()
    return target


def apply_orbit_plane(objs, ud):
    # Missing controls in unupgraded scenes must not reset a custom circle pose.
    if "Height" not in ud:
        return
    pos = c4d.Vector(*[_safe_float(ud.get(key), 0.0) for key in ("Center X", "Height", "Center Z")])
    center = valid_target(ud.get("Orbit Center"), objs)
    if center is not None:
        pos += ~objs.rig.GetMg() * center.GetMg().off
    rot = c4d.Vector(*[math.radians(_safe_float(ud.get(key), 0.0))
                       for key in ("Plane Heading", "Plane Tilt", "Plane Bank")])
    objs.circle.SetRelPos(pos)
    objs.circle.SetRelRot(rot)


def camera_focal_id(camera):
    return c4d.RSCAMERAOBJECT_FOCAL_LENGTH if camera.GetType() == 1057516 else c4d.CAMERA_FOCUS


def camera_focus_id(camera):
    return c4d.RSCAMERAOBJECT_FOCUS_DISTANCE if camera.GetType() == 1057516 else c4d.CAMERAOBJECT_TARGETDISTANCE


def focus_depth(camera_matrix, position, offset=0.0):
    axis = camera_matrix.v3.GetNormalized()
    return max(1.0, (position - camera_matrix.off).Dot(axis) + _safe_float(offset, 0.0))


def execute_focus(tag):
    """Late expression: Align and Target have already evaluated this frame."""
    objs = get_rig_objects(tag.GetObject())
    if objs is None:
        return
    ud = _read_all_user_data(objs.rig)
    mode = int(_safe_float(ud.get("Focus Mode"), 0))
    distance = max(1.0, _safe_float(ud.get(UD_FOCUS_DISTANCE), 1000.0))
    point = None
    if mode == 1 and ud.get(UD_USE_TARGET, True) and not ud.get(UD_FREE_CAMERA, False):
        point = objs.look_target.GetMg().off
    elif mode == 2:
        target = valid_target(ud.get("Focus Target"), objs)
        if target is not None:
            point = target.GetMg().off
    if point is not None:
        distance = focus_depth(objs.fx.GetMg(), point, ud.get("Focus Offset", 0.0))
    _apply_focus_distance(objs.focus, distance)
    for camera in (objs.cam, objs.fx):
        camera[camera_focus_id(camera)] = distance
