"""
Общее разрешение объектов рига от Main_Camera (circle).
Один источник правды для иерархии: используется в python_tag_logic и в break_rig_user_data.
"""
import c4d
from collections import namedtuple
from typing import Optional, Dict

from . import config


RigObjects = namedtuple(
    "RigObjects",
    "rig circle follow offset cam fx align vib target_a target_b look_target target_expr focus",
)


def _collect_rig_named_children(rig: c4d.BaseObject) -> Dict[str, c4d.BaseObject]:
    """Обходит прямых детей rig. Поиск по префиксу для поддержки суффиксов (_01, _02)."""
    base_names = (config.TARGET_A_NAME, config.TARGET_B_NAME, config.LOOK_TARGET_NAME)
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


def get_rig_objects(
    circle: c4d.BaseObject,
    remove_vibrate: bool = True,
) -> Optional[RigObjects]:
    """
    Разрешает объекты рига от контроллера (circle).
    Target_A, Target_B, Look_Target ищутся по имени; цепочка Follow → Offset → RS_CAM → FX_CAM — по иерархии.
    remove_vibrate: если True, тег Vibrate на FX_CAM удаляется (для Python Tag). Для Break передать False.
    При ошибке печатает в Script Log и возвращает None.
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

    vib = fx.GetTag(c4d.Tvibrate)
    if remove_vibrate and vib is not None:
        vib.Remove()
        vib = None

    focus = None
    child_fx = fx.GetDown()
    while child_fx is not None:
        if child_fx.GetName().startswith(config.FOCUS_NAME):
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
