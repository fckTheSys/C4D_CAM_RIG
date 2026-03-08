"""
Логика Python Tag: орбита, offset, focal, shake, target blend.
Look_Target — виртуальный null, цель камеры; смешивание между Target A и B по параметру Blend.

Архитектура поворота:
  Rot H/P/B применяются к FX_CAM (дочерний объект RS_CAM).
  RS_CAM всегда смотрит на Look_Target через Target Expression.
  FX_CAM наследует это направление и добавляет ручное смещение взгляда.
  Shake — процедурный noise на FX_CAM (SetRelPos/SetRelRot от времени и UD). Vibrate не используется.
"""
import math
import c4d
from c4d import utils
from typing import Optional, Any, Dict

from . import config
from .rig_objects import RigObjects, get_rig_objects


# ---------------------------------------------------------------------------
# ОДНОРАЗОВЫЙ СБОР ДАННЫХ (вызывается один раз за кадр)
# ---------------------------------------------------------------------------

def _get_bc_name_safe(bc: c4d.BaseContainer) -> str:
    """Читает DESC_NAME из BaseContainer без вызова .get() (BaseContainer не словарь)."""
    try:
        return bc[c4d.DESC_NAME] or ""
    except Exception:
        return ""


def _read_all_user_data(obj: c4d.BaseObject) -> Dict[str, Any]:
    """
    Читает ВСЕ User Data за один проход.
    Группы и другие нечитаемые записи пропускаются через try/except —
    c4d.DESC_TYPE недоступен в Python API, поэтому проверяем читаемость напрямую.
    """
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


# ---------------------------------------------------------------------------
# ПРИМЕНЕНИЕ ПАРАМЕТРОВ
# ---------------------------------------------------------------------------

def _apply_orbit_radius(
    circle: c4d.BaseObject,
    align: Optional[c4d.BaseTag],
    orbit: Any,
    radius: Any,
) -> None:
    if radius is not None:
        circle[c4d.PRIM_CIRCLE_RADIUS] = radius
    if align and orbit is not None:
        align[c4d.ALIGNTOSPLINETAG_POSITION] = orbit / 360.0


def _apply_offset(offset: c4d.BaseObject, offx: Any, offy: Any, offz: Any) -> None:
    if offx is not None and offy is not None and offz is not None:
        offset.SetRelPos(c4d.Vector(offx, offy, offz))


# Константы фокуса: стандартная камера C4D и Redshift
_FOCAL_LENGTH_ID = getattr(c4d, "RSCAMERAOBJECT_FOCAL_LENGTH", None) or getattr(c4d, "CAMERA_FOCUS", None)


def _apply_focal(cam: c4d.BaseObject, fx: c4d.BaseObject, focal: Any) -> None:
    if focal is None or _FOCAL_LENGTH_ID is None:
        return
    try:
        f = float(focal)
        if cam is not None:
            cam[_FOCAL_LENGTH_ID] = f
        if fx is not None:
            fx[_FOCAL_LENGTH_ID] = f
    except (TypeError, AttributeError):
        pass


def _safe_float(val: Any, default: float) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _noise_1d(t: float, seed: float) -> float:
    """Детерминированный плавный noise [-1, 1] от времени и seed."""
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
    roth: Any,
    rotp: Any,
    rotb: Any,
) -> None:
    """
    Процедурный shake на FX_CAM: позиция и вращение от noise по времени.
    Базовые Rot H/P/B из UD; при Shake Enable добавляется noise поверх.
    """
    base_h = _safe_float(roth, config.DEFAULT_ROT_H)
    base_p = _safe_float(rotp, config.DEFAULT_ROT_P)
    base_b = _safe_float(rotb, config.DEFAULT_ROT_B)

    if not shake_enable:
        fx.SetRelPos(c4d.Vector(0, 0, 0))
        fx.SetRelRot(c4d.Vector(utils.DegToRad(base_h), utils.DegToRad(base_p), utils.DegToRad(base_b)))
        return

    time_sec = 0.0
    if doc is not None:
        try:
            time_sec = doc.GetTime().Get()
        except Exception:
            pass
    amp_pos = max(0.0, _safe_float(shake_pos, config.DEFAULT_SHAKE_POS))
    amp_rot = max(0.0, _safe_float(shake_rot, config.DEFAULT_SHAKE_ROT))
    seed, freq = 1.0, 1.5
    t = time_sec * freq

    nx = _noise_1d(t + 0.0, seed + 11.0)
    ny = _noise_1d(t + 3.7, seed + 23.0)
    nz = _noise_1d(t + 7.9, seed + 37.0)

    fx.SetRelPos(c4d.Vector(nx * amp_pos, ny * amp_pos, nz * amp_pos))
    rot_h = base_h + nx * amp_rot
    rot_p = base_p + ny * amp_rot
    rot_b = base_b + nz * amp_rot
    fx.SetRelRot(c4d.Vector(utils.DegToRad(rot_h), utils.DegToRad(rot_p), utils.DegToRad(rot_b)))


def _apply_focus_distance(focus: Optional[c4d.BaseObject], distance: Any) -> None:
    """Ставит фокус-объект внутри FX_CAM на дистанцию по оси вида: (0, 0, distance)."""
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
    """
    Target_0 (Look_Target) перемещается в глобальные координаты объекта из UD link A или B.
    - Поле A заполнено: Target_0 → pos(A).
    - Оба поля A и B заполнены: Target_0 → blend(pos(A), pos(B)), 0%=A, 100%=B.
    Вызывать только при включённом Use Target.
    """
    link_a = ud.get(config.UD_TARGET_A)
    link_b = ud.get(config.UD_TARGET_B)
    obj_a = link_a if isinstance(link_a, c4d.BaseObject) else objs.target_a
    obj_b = link_b if isinstance(link_b, c4d.BaseObject) else None

    pos_a = obj_a.GetMg().off if obj_a else None
    pos_b = obj_b.GetMg().off if obj_b else None

    if pos_a is None:
        return

    if pos_b is not None:
        blend = ud.get(config.UD_TARGET_BLEND)
        t = max(0.0, min(100.0, float(blend) if blend is not None else 0.0)) / 100.0
        aim_pos = pos_a + (pos_b - pos_a) * t
    else:
        aim_pos = pos_a

    mg = objs.look_target.GetMg()
    mg.off = aim_pos
    objs.look_target.SetMg(mg)


# ---------------------------------------------------------------------------
# ТОЧКА ВХОДА PYTHON TAG
# ---------------------------------------------------------------------------

def main(op: c4d.BaseTag) -> None:
    """
    Вызывается каждый кадр Python Tag'ом на Main_Camera.
    Один проход по User Data, один проход по детям riga. Rotation и shake в _apply_shake.
    """
    circle = op.GetObject()
    objs = get_rig_objects(circle)
    if objs is None:
        return

    doc = op.GetDocument()
    ud = _read_all_user_data(objs.rig)  # UD на главном родителе (rig)
    if not ud:
        ud = _read_all_user_data(circle)  # Обратная совместимость: старые сцены с UD на circle

    _apply_orbit_radius(circle, objs.align, ud.get(config.UD_ORBIT), ud.get(config.UD_RADIUS))
    _apply_offset(objs.offset, ud.get(config.UD_OFFSET_X), ud.get(config.UD_OFFSET_Y), ud.get(config.UD_OFFSET_Z))
    _apply_focal(objs.cam, objs.fx, ud.get(config.UD_FOCAL))
    _apply_focus_distance(objs.focus, ud.get(config.UD_FOCUS_DISTANCE))
    _apply_shake(
        objs.fx,
        doc,
        ud.get(config.UD_SHAKE_ENABLE),
        ud.get(config.UD_SHAKE_POS),
        ud.get(config.UD_SHAKE_ROT),
        ud.get(config.UD_ROT_H),
        ud.get(config.UD_ROT_P),
        ud.get(config.UD_ROT_B),
    )

    # Use target: вкл — камера смотрит на Look_Target (позиция A или blend A-B), выкл — свободная камера
    use_target = ud.get(config.UD_USE_TARGET, config.DEFAULT_USE_TARGET)
    free_camera = ud.get(config.UD_FREE_CAMERA, config.DEFAULT_FREE_CAMERA)
    if objs.target_expr is not None:
        if use_target and not free_camera:
            objs.target_expr[c4d.TARGETEXPRESSIONTAG_LINK] = objs.look_target
            _apply_target_blend(objs, ud)
        else:
            objs.target_expr[c4d.TARGETEXPRESSIONTAG_LINK] = None




# ---------------------------------------------------------------------------
# ОБРАТНАЯ СОВМЕСТИМОСТЬ PYTHON TAG
# ---------------------------------------------------------------------------

def message(op: c4d.BaseTag, mid: int, data) -> bool:
    """
    Совместимость со старыми Python Tag, которые вызывают python_tag_logic.message().
    Текущая версия рига не использует события message для логики обновления.
    """
    return True
