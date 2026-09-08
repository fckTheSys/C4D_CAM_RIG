"""Сборка иерархии орбитального камерного рига и Python Tag."""
import os
from typing import Optional

import c4d

from . import config
from . import log
from .scene_support import add_undo, configure_priorities, set_schema
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
        raise RuntimeError("Cannot create a portable rig without embedded runtime.") from e


def _count_rigs(doc: c4d.documents.BaseDocument) -> int:
    """Считает существующие риги в документе (по имени RIG_ROOT_NAME или Cam_Rig_*)."""
    count = 0
    if not doc:
        return 0
    while doc.SearchObject(config.RIG_ROOT_NAME + "_" + str(count)) is not None:
        count += 1
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
    if not template:
        raise RuntimeError("CamRig User Data template is missing or invalid.")
    build_user_data_from_template(rig, template, {"target_a": target_a, "target_b": target_b})



def build_cam_rig(
    doc: c4d.documents.BaseDocument,
    position_global: Optional[c4d.Matrix] = None,
    record_undo: bool = False,
) -> Optional[c4d.BaseObject]:
    """
    Строит камеру-риг в переданном документе.
    Риг всегда создаётся в корне документа.
    Если передан position_global (например mg активного null), риг ставится в этих координатах.
    Имена объектов с уникальным суффиксом: Cam_Rig_0, Main_Camera_0, ...
    Возвращает созданный rig (корневой null) для выбора в AM.
    """
    source = _build_python_tag_source()
    if load_ud_template() is None:
        raise RuntimeError("CamRig User Data template is missing.")
    suffix = _count_rigs(doc)
    names = _make_rig_names(suffix)

    try:
        root_type = config.PLUGIN_ID_CAMRIG_ROOT if c4d.plugins.FindPlugin(config.PLUGIN_ID_CAMRIG_ROOT, c4d.PLUGINTYPE_OBJECT) else c4d.Onull
        rig = c4d.BaseObject(root_type)
    except (TypeError, AttributeError):
        rig = c4d.BaseObject(c4d.Onull)
    if rig is None:
        rig = c4d.BaseObject(c4d.Onull)
    rig.SetName(names["rig"])
    if position_global is not None:
        rig.SetMg(position_global)
    doc.InsertObject(rig)
    if record_undo:
        add_undo(doc, c4d.UNDOTYPE_NEWOBJ, rig)

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
        camera_type = config.RS_CAMERA_ID if c4d.plugins.FindPlugin(config.RS_CAMERA_ID, c4d.PLUGINTYPE_OBJECT) else c4d.Ocamera
        cam = c4d.BaseObject(camera_type)
    except (TypeError, AttributeError):
        cam = c4d.BaseObject(c4d.Ocamera)
    if cam is None:
        cam = c4d.BaseObject(c4d.Ocamera)
    cam.SetName(names["rs_cam"])
    cam.InsertUnder(offset)

    try:
        fx = c4d.BaseObject(camera_type)
    except (TypeError, AttributeError):
        fx = c4d.BaseObject(c4d.Ocamera)
    if fx is None:
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
        if record_undo:
            add_undo(doc, c4d.UNDOTYPE_NEWOBJ, sys_layer)
    unique_layer = c4d.documents.LayerObject()
    unique_layer.SetName(names["main_camera"])
    unique_layer.InsertUnder(layer_root)
    if record_undo:
        add_undo(doc, c4d.UNDOTYPE_NEWOBJ, unique_layer)
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
    py.SetName("CamRig Runtime 1.5")
    py[c4d.TPYTHON_CODE] = source
    late = c4d.BaseTag(c4d.Tpython)
    late.SetName(config.FOCUS_TAG_NAME)
    late[c4d.TPYTHON_CODE] = source
    circle.InsertTag(late)
    configure_priorities(py, align, tgt, late)
    set_schema(rig)

    return rig
