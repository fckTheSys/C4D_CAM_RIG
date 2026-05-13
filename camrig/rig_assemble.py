"""Сборка иерархии орбитального камерного рига и Python Tag."""
import os
from typing import Optional

import c4d

from . import config
from . import log
from .ud_build import (
    add_bool,
    add_group,
    add_link,
    add_slider,
    apply_ud_defaults_from_template,
    build_user_data_from_template,
    load_ud_template,
)


def _lock_circle_transform(circle: c4d.BaseObject) -> None:
    """Залочить позицию/вращение/масштаб circle — управление только через орбиту/UD."""
    lock_pos = getattr(c4d, "ID_BASEOBJECT_REL_POSITION_LOCK", None)
    lock_rot = getattr(c4d, "ID_BASEOBJECT_REL_ROTATION_LOCK", None)
    lock_scale = getattr(c4d, "ID_BASEOBJECT_REL_SCALE_LOCK", None)
    try:
        if lock_pos is not None:
            circle[lock_pos] = True
        if lock_rot is not None:
            circle[lock_rot] = True
        if lock_scale is not None:
            circle[lock_scale] = True
    except (TypeError, AttributeError):
        pass


def _build_python_tag_source() -> str:
    """
    Полный скрипт для Python Tag — воспроизводится без установленного плагина.
    Читает camrig/tag_embedded.py рядом с этим модулем.
    """
    base = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, "tag_embedded.py")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError as e:
        log.error("tag_embedded.py not readable: " + str(e))
        return (
            "import c4d\ndef main():\n"
            "    pass  # CamRig: missing tag_embedded.py\n"
        )


def _count_rigs(doc: c4d.documents.BaseDocument) -> int:
    """Считает существующие риги в документе (по имени RIG_ROOT_NAME или Cam_Rig_*)."""
    count = 0
    if not doc:
        return 0
    root = doc.GetFirstObject()
    while root:
        name = root.GetName()
        if name == config.RIG_ROOT_NAME or name.startswith(config.RIG_ROOT_NAME + "_"):
            count += 1
        root = root.GetNext()
    return count


def _make_rig_names(suffix: int) -> dict:
    """Возвращает словарь имён объектов рига с суффиксом _N."""
    s = "_%d" % suffix if suffix >= 0 else ""
    return {
        "rig": config.RIG_ROOT_NAME + s,
        "main_camera": config.MAIN_CAMERA_NAME + s,
        "target_a": config.TARGET_A_NAME + s,
        "target_b": config.TARGET_B_NAME + s,
        "look_target": config.LOOK_TARGET_NAME + s,
        "follow": config.FOLLOW_NAME + s,
        "offset": config.OFFSET_NAME + s,
        "rs_cam": "RS_CAM" + s,
        "fx_cam": "FX_CAM" + s,
        "focus": config.FOCUS_NAME + s,
    }


def _add_controller_user_data(
    rig: c4d.BaseObject,
    target_a: c4d.BaseObject,
    target_b: c4d.BaseObject,
) -> None:
    """Добавляет на корень rig все группы и User Data из ud_template.json или fallback."""
    template = load_ud_template()
    if template:
        link_objects = {"target_a": target_a, "target_b": target_b}
        build_user_data_from_template(rig, template, link_objects)
        apply_ud_defaults_from_template(template)
        return
    group_orbit = add_group(rig, "Orbit")
    add_slider(rig, config.UD_ORBIT, config.DEFAULT_ORBIT, 0, 360, parent_group=group_orbit, step=0.1)
    add_slider(rig, config.UD_RADIUS, config.DEFAULT_RADIUS, 0, 5000, parent_group=group_orbit, step=1)

    group_transform = add_group(rig, "Transform")
    add_slider(rig, config.UD_OFFSET_X, config.DEFAULT_OFFSET_X, -2000, 2000, parent_group=group_transform, step=1)
    add_slider(rig, config.UD_OFFSET_Y, config.DEFAULT_OFFSET_Y, -2000, 2000, parent_group=group_transform, step=1)
    add_slider(rig, config.UD_OFFSET_Z, config.DEFAULT_OFFSET_Z, -2000, 2000, parent_group=group_transform, step=1)
    add_slider(rig, config.UD_ROT_H, config.DEFAULT_ROT_H, -180, 180, parent_group=group_transform, step=0.1)
    add_slider(rig, config.UD_ROT_P, config.DEFAULT_ROT_P, -180, 180, parent_group=group_transform, step=0.1)
    add_slider(rig, config.UD_ROT_B, config.DEFAULT_ROT_B, -180, 180, parent_group=group_transform, step=0.1)

    group_camera = add_group(rig, "Camera")
    add_slider(rig, config.UD_FOCAL, config.DEFAULT_FOCAL, 10, 200, parent_group=group_camera, step=0.1)
    add_slider(rig, config.UD_FOCUS_DISTANCE, config.DEFAULT_FOCUS_DISTANCE, 1, 100000, parent_group=group_camera, step=1)

    group_shake = add_group(rig, "Shake")
    add_bool(rig, config.UD_SHAKE_ENABLE, config.DEFAULT_SHAKE_ENABLE, parent_group=group_shake)
    add_slider(rig, config.UD_SHAKE_POS, config.DEFAULT_SHAKE_POS, 0, 100, parent_group=group_shake, step=0.1)
    add_slider(rig, config.UD_SHAKE_ROT, config.DEFAULT_SHAKE_ROT, 0, 20, parent_group=group_shake, step=0.01)
    add_slider(rig, config.UD_DRIFT_POS, config.DEFAULT_DRIFT_POS, 0, 50, parent_group=group_shake, step=0.1)
    add_slider(rig, config.UD_DRIFT_ROT, config.DEFAULT_DRIFT_ROT, 0, 10, parent_group=group_shake, step=0.01)
    add_slider(rig, config.UD_DRIFT_FREQ, config.DEFAULT_DRIFT_FREQ, 0.01, 1, parent_group=group_shake, step=0.01)

    group_target = add_group(rig, "Target")
    add_bool(rig, config.UD_USE_TARGET, config.DEFAULT_USE_TARGET, parent_group=group_target)
    add_link(rig, config.UD_TARGET_A, default_link=target_a, parent_group=group_target)
    add_link(rig, config.UD_TARGET_B, default_link=target_b, parent_group=group_target)
    add_slider(rig, config.UD_TARGET_BLEND, config.DEFAULT_TARGET_BLEND, 0, 100, parent_group=group_target, step=1)
    add_bool(rig, config.UD_FREE_CAMERA, config.DEFAULT_FREE_CAMERA, parent_group=group_target)


def build_cam_rig(
    doc: c4d.documents.BaseDocument,
    position_global: Optional[c4d.Matrix] = None,
) -> Optional[c4d.BaseObject]:
    """
    Строит камеру-риг в переданном документе.
    Риг всегда создаётся в корне документа.
    Если передан position_global (например mg активного null), риг ставится в этих координатах.
    Имена объектов с уникальным суффиксом: Cam_Rig_0, Main_Camera_0, ...
    Возвращает созданный rig (корневой null) для выбора в AM.
    """
    suffix = _count_rigs(doc)
    names = _make_rig_names(suffix)

    try:
        rig = c4d.BaseObject(config.PLUGIN_ID_CAMRIG_ROOT)
    except (TypeError, AttributeError, BaseException):
        rig = c4d.BaseObject(c4d.Onull)
    rig.SetName(names["rig"])
    if position_global is not None:
        rig.SetMg(position_global)
    doc.InsertObject(rig)

    target_a = c4d.BaseObject(c4d.Onull)
    target_a.SetName(names["target_a"])
    target_a.InsertUnder(rig)

    target_b = c4d.BaseObject(c4d.Onull)
    target_b.SetName(names["target_b"])
    target_b.SetRelPos(c4d.Vector(0, 0, 200))
    target_b.InsertAfter(target_a)

    aim = c4d.BaseObject(c4d.Onull)
    aim.SetName(names["look_target"])
    aim.SetRelPos(target_a.GetRelPos())
    aim.InsertAfter(target_b)

    circle = c4d.BaseObject(c4d.Osplinecircle)
    circle.SetName(names["main_camera"])
    circle[c4d.PRIM_PLANE] = c4d.PRIM_PLANE_XZ
    circle[c4d.PRIM_CIRCLE_RADIUS] = config.DEFAULT_RADIUS
    circle.InsertAfter(aim)

    follow = c4d.BaseObject(c4d.Onull)
    follow.SetName(names["follow"])
    follow.InsertUnder(circle)

    align = c4d.BaseTag(c4d.Taligntospline)
    follow.InsertTag(align)

    align[c4d.ALIGNTOSPLINETAG_LINK] = circle
    align[c4d.ALIGNTOSPLINETAG_AXIS] = 3  # -X orientation
    align[c4d.ALIGNTOSPLINETAG_TANGENTIAL] = True

    offset = c4d.BaseObject(c4d.Onull)
    offset.SetName(names["offset"])
    offset.InsertUnder(follow)

    try:
        cam = c4d.BaseObject(config.RS_CAMERA_ID)
    except (TypeError, AttributeError):
        cam = c4d.BaseObject(c4d.Ocamera)
    cam.SetName(names["rs_cam"])
    cam.InsertUnder(offset)

    try:
        fx = c4d.BaseObject(config.RS_CAMERA_ID)
    except (TypeError, AttributeError):
        fx = c4d.BaseObject(c4d.Ocamera)
    fx.SetName(names["fx_cam"])
    fx.InsertUnder(cam)

    focus_obj = c4d.BaseObject(c4d.Onull)
    focus_obj.SetName(names["focus"])
    focus_obj.SetRelPos(c4d.Vector(0, 0, config.DEFAULT_FOCUS_DISTANCE))
    focus_obj.InsertUnder(fx)
    try:
        focus_obj[c4d.NULLOBJECT_DISPLAY] = config.FOCUS_DISPLAY_MODE
        focus_obj[c4d.NULLOBJECT_RADIUS] = config.FOCUS_DISPLAY_RADIUS
        focus_obj[c4d.ID_BASEOBJECT_USECOLOR] = config.FOCUS_USECOLOR_MODE
        focus_obj[c4d.ID_BASEOBJECT_COLOR] = config.FOCUS_COLOR
    except (AttributeError, TypeError):
        pass

    tgt = c4d.BaseTag(c4d.Ttargetexpression)
    cam.InsertTag(tgt)
    tgt[c4d.TARGETEXPRESSIONTAG_LINK] = aim

    layer_root = doc.GetLayerObjectRoot()
    sys_layer = None
    child = layer_root.GetDown()
    while child is not None:
        if child.GetName() == config.SYSTEM_LAYER_NAME:
            sys_layer = child
            break
        child = child.GetNext()
    if sys_layer is None:
        sys_layer = c4d.documents.LayerObject()
        sys_layer.SetName(config.SYSTEM_LAYER_NAME)
        sys_layer.InsertUnder(layer_root)
    unique_layer = c4d.documents.LayerObject()
    unique_layer.SetName(names["main_camera"])
    unique_layer.InsertUnder(layer_root)
    follow.SetLayerObject(sys_layer)
    offset.SetLayerObject(sys_layer)
    circle.SetLayerObject(sys_layer)
    aim.SetLayerObject(sys_layer)
    focus_obj.SetLayerObject(sys_layer)
    rig.SetLayerObject(unique_layer)
    target_a.SetLayerObject(unique_layer)
    target_b.SetLayerObject(unique_layer)
    cam.SetLayerObject(unique_layer)
    fx.SetLayerObject(unique_layer)

    _add_controller_user_data(rig, target_a, target_b)

    _lock_circle_transform(circle)

    py = c4d.BaseTag(c4d.Tpython)
    circle.InsertTag(py)
    py[c4d.TPYTHON_CODE] = _build_python_tag_source()

    return rig
