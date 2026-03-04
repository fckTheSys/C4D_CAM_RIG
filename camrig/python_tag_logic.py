"""
Логика Python Tag: орбита, offset, focal, shake, target blend.
Look_Target — виртуальный null, цель камеры; смешивание между Target A и B по параметру Blend.

Архитектура поворота:
  Rot H/P/B применяются к FX_CAM (дочерний объект RS_CAM).
  RS_CAM всегда смотрит на Look_Target через Target Expression.
  FX_CAM наследует это направление и добавляет ручное смещение взгляда.
  Shake (Vibrate) на FX_CAM накладывается поверх ручного поворота.
"""
import c4d
from c4d import utils
from collections import namedtuple
from typing import Optional, Any, Dict

from . import config


RigObjects = namedtuple(
    "RigObjects",
    "follow offset cam fx align vib rig target_a target_b look_target",
)


# ---------------------------------------------------------------------------
# ОДНОРАЗОВЫЙ СБОР ДАННЫХ (вызывается один раз за кадр)
# ---------------------------------------------------------------------------

def _read_all_user_data(obj: c4d.BaseObject) -> Dict[str, Any]:
    """
    Читает ВСЕ User Data за один проход.
    Группы и другие нечитаемые записи пропускаются через try/except —
    c4d.DESC_TYPE недоступен в Python API, поэтому проверяем читаемость напрямую.
    """
    result: Dict[str, Any] = {}
    for desc_id, bc in obj.GetUserDataContainer():
        name = bc[c4d.DESC_NAME]
        if not name:
            continue
        try:
            result[name] = obj[desc_id]
        except AttributeError:
            pass
    return result


def _collect_rig_named_children(rig: c4d.BaseObject) -> Dict[str, c4d.BaseObject]:
    """Обходит прямых детей rig один раз, возвращает словарь имя→объект."""
    needed = {config.TARGET_A_NAME, config.TARGET_B_NAME, config.LOOK_TARGET_NAME}
    found: Dict[str, c4d.BaseObject] = {}
    child = rig.GetDown()
    while child is not None:
        name = child.GetName()
        if name in needed:
            found[name] = child
            if len(found) == len(needed):
                break
        child = child.GetNext()
    return found


def get_rig_objects(circle: c4d.BaseObject) -> Optional[RigObjects]:
    """
    Разрешает объекты рига от контроллера (circle).
    Target_A, Target_B, Look_Target ищутся по имени — порядок в Outliner не важен.
    Камерная цепочка (Follow → Offset → RS_CAM → FX_CAM) ищется позиционально.
    При ошибке печатает диагностику в Script Log и возвращает None.
    """
    rig = circle.GetUp()
    if rig is None:
        c4d.GePrint("[CamRig] ERROR: Main_Camera has no parent (Cam_Rig missing?)")
        return None

    children = _collect_rig_named_children(rig)

    target_a = children.get(config.TARGET_A_NAME)
    if target_a is None:
        c4d.GePrint("[CamRig] ERROR: '%s' not found under '%s'" % (config.TARGET_A_NAME, rig.GetName()))
        return None

    target_b = children.get(config.TARGET_B_NAME)
    if target_b is None:
        c4d.GePrint("[CamRig] ERROR: '%s' not found under '%s'" % (config.TARGET_B_NAME, rig.GetName()))
        return None

    look_target = children.get(config.LOOK_TARGET_NAME)
    if look_target is None:
        c4d.GePrint("[CamRig] ERROR: '%s' not found under '%s'" % (config.LOOK_TARGET_NAME, rig.GetName()))
        return None

    follow = circle.GetDown()
    if follow is None:
        c4d.GePrint("[CamRig] ERROR: Follow not found under Main_Camera")
        return None
    offset = follow.GetDown()
    if offset is None:
        c4d.GePrint("[CamRig] ERROR: Offset not found under Follow")
        return None
    cam = offset.GetDown()
    if cam is None:
        c4d.GePrint("[CamRig] ERROR: RS_CAM not found under Offset")
        return None
    fx = cam.GetDown()
    if fx is None:
        c4d.GePrint("[CamRig] ERROR: FX_CAM not found under RS_CAM")
        return None

    align = follow.GetTag(c4d.Taligntospline)
    vib = fx.GetTag(c4d.Tvibrate)
    return RigObjects(
        follow=follow,
        offset=offset,
        cam=cam,
        fx=fx,
        align=align,
        vib=vib,
        rig=rig,
        target_a=target_a,
        target_b=target_b,
        look_target=look_target,
    )


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


def _apply_rotation(fx: c4d.BaseObject, roth: Any, rotp: Any, rotb: Any) -> None:
    """
    Применяет Rot H/P/B к FX_CAM (дочерний RS_CAM).
    RS_CAM смотрит на Look_Target через Target Expression;
    FX_CAM наследует это направление и добавляет смещение взгляда.
    Таким образом H/P/B — это угол ОТНОСИТЕЛЬНО направления на таргет, а не орбиты.
    """
    if roth is not None and rotp is not None and rotb is not None:
        fx.SetRelRot(
            c4d.Vector(
                utils.DegToRad(roth),
                utils.DegToRad(rotp),
                utils.DegToRad(rotb),
            )
        )


def _apply_focal(cam: c4d.BaseObject, fx: c4d.BaseObject, focal: Any) -> None:
    if focal is not None:
        cam[c4d.CAMERA_FOCUS] = focal
        fx[c4d.CAMERA_FOCUS] = focal


def _apply_shake(
    vib: Optional[c4d.BaseTag],
    shake_enable: Any,
    shake_pos: Any,
    shake_rot: Any,
) -> None:
    if not vib:
        return
    if shake_enable and shake_pos is not None and shake_rot is not None:
        vib[c4d.VIBRATEEXPRESSION_POS_AMPLITUDE] = c4d.Vector(shake_pos)
        vib[c4d.VIBRATEEXPRESSION_ROT_AMPLITUDE] = c4d.Vector(shake_rot)
    else:
        vib[c4d.VIBRATEEXPRESSION_POS_AMPLITUDE] = c4d.Vector(0)
        vib[c4d.VIBRATEEXPRESSION_ROT_AMPLITUDE] = c4d.Vector(0)


def _apply_target_blend(
    objs: RigObjects,
    ud: Dict[str, Any],
) -> None:
    """
    Вычисляет позицию Look_Target как blend между Target A и Target B.
    Использует уже считанный словарь ud — без повторных итераций по User Data.
    """
    link_a = ud.get(config.UD_TARGET_A)
    link_b = ud.get(config.UD_TARGET_B)
    obj_a = link_a if isinstance(link_a, c4d.BaseObject) else objs.target_a
    obj_b = link_b if isinstance(link_b, c4d.BaseObject) else objs.target_b

    pos_a = obj_a.GetMg().off
    pos_b = obj_b.GetMg().off

    use_target_b = ud.get(config.UD_USE_TARGET_B)
    blend = ud.get(config.UD_TARGET_BLEND)

    if use_target_b and blend is not None:
        t = max(0.0, min(100.0, float(blend))) / 100.0
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
    Один проход по User Data, один проход по детям riga — без повторных итераций.
    """
    circle = op.GetObject()
    objs = get_rig_objects(circle)
    if objs is None:
        return

    ud = _read_all_user_data(circle)

    _apply_orbit_radius(circle, objs.align, ud.get(config.UD_ORBIT), ud.get(config.UD_RADIUS))
    _apply_offset(objs.offset, ud.get(config.UD_OFFSET_X), ud.get(config.UD_OFFSET_Y), ud.get(config.UD_OFFSET_Z))
    _apply_rotation(objs.fx, ud.get(config.UD_ROT_H), ud.get(config.UD_ROT_P), ud.get(config.UD_ROT_B))
    _apply_focal(objs.cam, objs.fx, ud.get(config.UD_FOCAL))
    _apply_shake(objs.vib, ud.get(config.UD_SHAKE_ENABLE), ud.get(config.UD_SHAKE_POS), ud.get(config.UD_SHAKE_ROT))
    _apply_target_blend(objs, ud)
