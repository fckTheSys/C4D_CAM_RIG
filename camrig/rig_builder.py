"""
Построение камерного рига CamRig: иерархия объектов, User Data из JSON-шаблона,
сброс параметров. См. docs/Technical Specification.md и docs/KNOWN_ISSUES_AND_FIXES.md.
"""
import c4d
import json
import os
from typing import Optional, List, Dict, Any

from . import config
from .rig_objects import get_rig_objects

# Единицы для слайдеров (могут отсутствовать в старых версиях C4D; опционально в ud_template.json)
_UNIT_DEGREE = getattr(c4d, "DESC_UNIT_DEGREE", None)
_UNIT_PERCENT = getattr(c4d, "DESC_UNIT_PERCENT", None)

# Интерфейсы для Float (real): соответствие строк из JSON и C4D DESC_CUSTOMGUI.
# В C4D: Float | Float Slider | Float Slider (No Editfield) | Latitude/Longitude | RSSlider
_REAL_INTERFACE_MAP = {
    "float": None,
    "slider": getattr(c4d, "CUSTOMGUI_REALSLIDER", None),
    "float_slider": getattr(c4d, "CUSTOMGUI_REALSLIDER", None),
    "float_slider_no_editfield": getattr(c4d, "CUSTOMGUI_REALSLIDER_NOEDIT", None),
    "latitude_longitude": getattr(c4d, "CUSTOMGUI_LATLONG", None),
    "latlong": getattr(c4d, "CUSTOMGUI_LATLONG", None),
    "rsslider": getattr(c4d, "CUSTOMGUI_RSSLIDER", None),
}


def add_slider(
    obj: c4d.BaseObject,
    name: str,
    val: float,
    minv: float,
    maxv: float,
    parent_group: Optional[c4d.DescID] = None,
    step: float = 0.01,
    unit: Optional[int] = None,
    custom_gui: Optional[int] = None,
) -> c4d.DescID:
    """Создаёт слайдер User Data на объекте и возвращает его ID."""
    bc = c4d.GetCustomDataTypeDefault(c4d.DTYPE_REAL)

    bc[c4d.DESC_NAME] = name
    bc[c4d.DESC_MIN] = minv
    bc[c4d.DESC_MAX] = maxv
    bc[c4d.DESC_STEP] = step
    if parent_group is not None:
        bc[c4d.DESC_PARENTGROUP] = parent_group
    if unit is not None:
        bc[c4d.DESC_UNIT] = unit
    if custom_gui is not None:
        bc[c4d.DESC_CUSTOMGUI] = custom_gui

    element = obj.AddUserData(bc)
    obj[element] = val

    return element


def _add_group(obj: c4d.BaseObject, name: str, titlebar: bool = True) -> c4d.DescID:
    """Создаёт группу User Data и возвращает её DescID."""
    bc = c4d.GetCustomDataTypeDefault(c4d.DTYPE_GROUP)
    bc[c4d.DESC_NAME] = name
    bc[c4d.DESC_TITLEBAR] = titlebar
    return obj.AddUserData(bc)


def add_bool(
    obj: c4d.BaseObject,
    name: str,
    default_val: bool = False,
    parent_group: Optional[c4d.DescID] = None,
) -> c4d.DescID:
    """Создаёт User Data типа Bool (checkbox) на объекте."""
    bc = c4d.GetCustomDataTypeDefault(c4d.DTYPE_BOOL)
    bc[c4d.DESC_NAME] = name
    if parent_group is not None:
        bc[c4d.DESC_PARENTGROUP] = parent_group

    element = obj.AddUserData(bc)
    obj[element] = default_val
    return element


def add_button(obj: c4d.BaseObject, name: str, parent_group: Optional[c4d.DescID] = None) -> Optional[c4d.DescID]:
    """Создаёт кнопку User Data на объекте. DESC_HIDE = False — чтобы кнопка отображалась в Attribute Manager."""
    try:
        bc = c4d.GetCustomDataTypeDefault(c4d.DTYPE_BUTTON)
    except (TypeError, AttributeError):
        return None
    bc[c4d.DESC_NAME] = name
    if parent_group is not None:
        bc[c4d.DESC_PARENTGROUP] = parent_group
    try:
        customgui_button = getattr(c4d, "CUSTOMGUI_BUTTON", None)
        if customgui_button is not None:
            bc[c4d.DESC_CUSTOMGUI] = customgui_button
    except (TypeError, AttributeError):
        pass
    try:
        bc[c4d.DESC_HIDE] = False
    except (TypeError, AttributeError):
        pass
    return obj.AddUserData(bc)


def add_link(
    obj: c4d.BaseObject,
    name: str,
    default_link: Optional[c4d.BaseList2D] = None,
    parent_group: Optional[c4d.DescID] = None,
) -> c4d.DescID:
    """Создаёт User Data типа Link на объекте и возвращает его ID."""
    bc = c4d.GetCustomDataTypeDefault(c4d.DTYPE_BASELISTLINK)
    bc[c4d.DESC_NAME] = name
    bc[c4d.DESC_ANIMATE] = c4d.DESC_ANIMATE_OFF
    if parent_group is not None:
        bc[c4d.DESC_PARENTGROUP] = parent_group

    element = obj.AddUserData(bc)
    if default_link is not None:
        obj[element] = default_link

    return element


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
    Код, который будет записан в Python Tag (на Main_Camera).
    Делегирует логику в camrig.python_tag_logic.
    """
    return (
        "import c4d\n"
        "from camrig import python_tag_logic\n\n"
        "def main():\n"
        "    python_tag_logic.main(op)\n"
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


def _load_ud_template() -> Optional[Dict[str, Any]]:
    """Загружает JSON-шаблон User Data из ud_template.json рядом с rig_builder.py. При ошибке возвращает None."""
    try:
        dir_path = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(dir_path, "ud_template.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and "groups" in data:
            return data
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    return None


def _real_interface_to_custom_gui(interface: Optional[str]) -> Optional[int]:
    """Преобразует строку interface из JSON в константу C4D DESC_CUSTOMGUI для real.
    Допустимые значения: float, slider, float_slider, float_slider_no_editfield,
    latitude_longitude, latlong, rsslider. Пробелы приводятся к подчёркиваниям, регистр — нижний."""
    if not interface:
        return None
    key = (
        str(interface)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("(", "")
        .replace(")", "")
    )
    if key == "float":
        return None
    gui = _REAL_INTERFACE_MAP.get(key)
    return gui if gui is not None else None


def _build_user_data_from_template(
    rig: c4d.BaseObject,
    template: Dict[str, Any],
    link_objects: Dict[str, Optional[c4d.BaseList2D]],
) -> None:
    """Создаёт все группы и User Data на rig по шаблону. link_objects: {'target_a': obj, 'target_b': obj}."""
    for group in template.get("groups", []):
        group_name = group.get("name")
        if not group_name:
            continue
        titlebar = group.get("titlebar", True)
        parent_group = _add_group(rig, group_name, titlebar)
        for param in group.get("params", []):
            ptype = param.get("type")
            name = param.get("name")
            if not name:
                continue
            if ptype == "real":
                custom_gui = _real_interface_to_custom_gui(param.get("interface"))
                add_slider(
                    rig,
                    name,
                    float(param.get("default", 0)),
                    float(param["min"]),
                    float(param["max"]),
                    parent_group=parent_group,
                    step=float(param.get("step", 0.01)),
                    unit=param.get("unit"),
                    custom_gui=custom_gui,
                )
            elif ptype == "bool":
                add_bool(rig, name, bool(param.get("default", False)), parent_group=parent_group)
            elif ptype == "link":
                link_ref = param.get("link_ref")
                default_link = link_objects.get(link_ref) if link_ref else None
                add_link(rig, name, default_link=default_link, parent_group=parent_group)
            elif ptype == "button":
                add_button(rig, name, parent_group=parent_group)


def _apply_ud_defaults_from_template(template: Dict[str, Any]) -> None:
    """Строит из шаблона dict имя -> default для real/bool и обновляет config.UD_DEFAULTS (один источник правды)."""
    defaults: Dict[str, Any] = {}
    for group in template.get("groups", []):
        for param in group.get("params", []):
            ptype = param.get("type")
            name = param.get("name")
            if not name or ptype not in ("real", "bool"):
                continue
            if ptype == "real":
                defaults[name] = float(param.get("default", 0))
            else:
                defaults[name] = bool(param.get("default", False))
    if defaults:
        config.UD_DEFAULTS.update(defaults)


def _add_controller_user_data(
    rig: c4d.BaseObject,
    target_a: c4d.BaseObject,
    target_b: c4d.BaseObject,
) -> None:
    """Добавляет на главный родитель (rig) все группы и User Data. Использует ud_template.json при успешной загрузке, иначе fallback."""
    template = _load_ud_template()
    if template:
        link_objects = {"target_a": target_a, "target_b": target_b}
        _build_user_data_from_template(rig, template, link_objects)
        _apply_ud_defaults_from_template(template)
        return
    # Fallback: жёстко прописанная логика
    group_orbit = _add_group(rig, "Orbit")
    add_slider(rig, config.UD_ORBIT, config.DEFAULT_ORBIT, 0, 360, parent_group=group_orbit, step=0.1)
    add_slider(rig, config.UD_RADIUS, config.DEFAULT_RADIUS, 0, 5000, parent_group=group_orbit, step=1)

    group_transform = _add_group(rig, "Transform")
    add_slider(rig, config.UD_OFFSET_X, config.DEFAULT_OFFSET_X, -2000, 2000, parent_group=group_transform, step=1)
    add_slider(rig, config.UD_OFFSET_Y, config.DEFAULT_OFFSET_Y, -2000, 2000, parent_group=group_transform, step=1)
    add_slider(rig, config.UD_OFFSET_Z, config.DEFAULT_OFFSET_Z, -2000, 2000, parent_group=group_transform, step=1)
    add_slider(rig, config.UD_ROT_H, config.DEFAULT_ROT_H, -180, 180, parent_group=group_transform, step=0.1)
    add_slider(rig, config.UD_ROT_P, config.DEFAULT_ROT_P, -180, 180, parent_group=group_transform, step=0.1)
    add_slider(rig, config.UD_ROT_B, config.DEFAULT_ROT_B, -180, 180, parent_group=group_transform, step=0.1)

    group_camera = _add_group(rig, "Camera")
    add_slider(rig, config.UD_FOCAL, config.DEFAULT_FOCAL, 10, 200, parent_group=group_camera, step=0.1)
    add_slider(rig, config.UD_FOCUS_DISTANCE, config.DEFAULT_FOCUS_DISTANCE, 1, 100000, parent_group=group_camera, step=1)

    group_shake = _add_group(rig, "Shake")
    add_bool(rig, config.UD_SHAKE_ENABLE, config.DEFAULT_SHAKE_ENABLE, parent_group=group_shake)
    add_slider(rig, config.UD_SHAKE_POS, config.DEFAULT_SHAKE_POS, 0, 100, parent_group=group_shake, step=0.1)
    add_slider(rig, config.UD_SHAKE_ROT, config.DEFAULT_SHAKE_ROT, 0, 20, parent_group=group_shake, step=0.01)

    group_target = _add_group(rig, "Target")
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

    # ------------------------------------------------
    # RIG ROOT
    # ------------------------------------------------
    try:
        rig = c4d.BaseObject(config.PLUGIN_ID_CAMRIG_ROOT)
    except (TypeError, AttributeError, BaseException):
        rig = c4d.BaseObject(c4d.Onull)
    rig.SetName(names["rig"])
    if position_global is not None:
        rig.SetMg(position_global)
    doc.InsertObject(rig)

    # ------------------------------------------------
    # Target_A, Target_B, Look_Target, Main_Camera — прямые дети rig (соседи).
    # ------------------------------------------------
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

    # ------------------------------------------------
    # FOLLOW OBJECT
    # ------------------------------------------------
    follow = c4d.BaseObject(c4d.Onull)
    follow.SetName(names["follow"])
    follow.InsertUnder(circle)

    # ------------------------------------------------
    # ALIGN TO SPLINE
    # ------------------------------------------------
    align = c4d.BaseTag(c4d.Taligntospline)
    follow.InsertTag(align)

    align[c4d.ALIGNTOSPLINETAG_LINK] = circle
    align[c4d.ALIGNTOSPLINETAG_AXIS] = 3  # -X orientation
    align[c4d.ALIGNTOSPLINETAG_TANGENTIAL] = True

    # ------------------------------------------------
    # OFFSET
    # ------------------------------------------------
    offset = c4d.BaseObject(c4d.Onull)
    offset.SetName(names["offset"])
    offset.InsertUnder(follow)

    # ------------------------------------------------
    # MAIN CAMERA (Redshift if available, else standard)
    # ------------------------------------------------
    try:
        cam = c4d.BaseObject(config.RS_CAMERA_ID)
    except (TypeError, AttributeError):
        cam = c4d.BaseObject(c4d.Ocamera)
    cam.SetName(names["rs_cam"])
    cam.InsertUnder(offset)

    # ------------------------------------------------
    # FX CAMERA (Redshift if available, else standard) + Vibrate
    # ------------------------------------------------
    try:
        fx = c4d.BaseObject(config.RS_CAMERA_ID)
    except (TypeError, AttributeError):
        fx = c4d.BaseObject(c4d.Ocamera)
    fx.SetName(names["fx_cam"])
    fx.InsertUnder(cam)

    # Фокус-объект внутри FX_CAM (дистанция от камеры по UD)
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

    # Камера смотрит на Look_Target (позиция = blend между Target A и Target B)
    tgt = c4d.BaseTag(c4d.Ttargetexpression)
    cam.InsertTag(tgt)
    tgt[c4d.TARGETEXPRESSIONTAG_LINK] = aim

    # Shake реализуется процедурно в Python Tag (без тега Vibrate)

    # ------------------------------------------------
    # LAYERS: hidenSysRig (общий) + уникальный слой рига
    # ------------------------------------------------
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

    # Лок трансформации circle — управляется только орбитой/радиусом через плагин
    _lock_circle_transform(circle)

    # ------------------------------------------------
    # PYTHON TAG (на circle — логика орбиты/offset/shake)
    # ------------------------------------------------
    py = c4d.BaseTag(c4d.Tpython)
    circle.InsertTag(py)
    py[c4d.TPYTHON_CODE] = _build_python_tag_source()

    return rig


def _get_ud_name_safe(bc: c4d.BaseContainer) -> str:
    """BaseContainer не имеет .get(); читаем через [] и try/except."""
    try:
        return bc[c4d.DESC_NAME] or ""
    except Exception:
        return ""


def _set_ud_value_safe(obj: c4d.BaseObject, desc_id: c4d.DescID, value) -> None:
    """Записывает значение в UD с приведением типа (bool -> int для C4D)."""
    try:
        if isinstance(value, bool):
            obj[desc_id] = int(value)
        elif isinstance(value, (int, float)):
            obj[desc_id] = float(value)
        else:
            obj[desc_id] = value
    except (TypeError, AttributeError):
        pass


def reset_rig_params(obj: c4d.BaseObject, groups: List[str]) -> None:
    """
    Сбрасывает только указанные группы UD к дефолтам.
    groups: список "orbit", "offset", "rotation", "camera", "target", "shake"
    """
    keys_to_reset = set()
    for g in groups:
        if g in config.RESET_GROUP_KEYS:
            keys_to_reset.update(config.RESET_GROUP_KEYS[g])
    if not keys_to_reset:
        return
    for desc_id, bc in obj.GetUserDataContainer():
        name = _get_ud_name_safe(bc)
        if name in keys_to_reset and name in config.UD_DEFAULTS:
            _set_ud_value_safe(obj, desc_id, config.UD_DEFAULTS[name])


def reset_rig_to_defaults(obj: c4d.BaseObject) -> None:
    """
    Сбрасывает User Data объекта (rig или circle) к дефолтам из config.
    Ссылки (Target A/B) не меняются.
    """
    for desc_id, bc in obj.GetUserDataContainer():
        name = _get_ud_name_safe(bc)
        if name in config.UD_DEFAULTS:
            _set_ud_value_safe(obj, desc_id, config.UD_DEFAULTS[name])


# ---------------------------------------------------------------------------
# Break User Data: transfer keys from rig UD to target objects, remove layer, remove Python tag
# ---------------------------------------------------------------------------

def _copy_float_track(
    doc: c4d.documents.BaseDocument,
    source: c4d.BaseList2D,
    source_desc_id: c4d.DescID,
    dest: c4d.BaseList2D,
    dest_desc_id: c4d.DescID,
    transform_fn,
) -> None:
    """Copy animated values from source track to dest track, with optional value transform."""
    track_src = source.FindCTrack(source_desc_id)
    if track_src is None:
        return
    curve_src = track_src.GetCurve()
    if curve_src is None:
        return
    track_dest = dest.FindCTrack(dest_desc_id)
    if track_dest is None:
        try:
            track_dest = c4d.CTrack(dest, dest_desc_id)
            dest.InsertTrackSorted(track_dest)
        except Exception:
            return
    curve_dest = track_dest.GetCurve()
    if curve_dest is None:
        return
    try:
        n = curve_src.GetKeyCount()
    except Exception:
        return
    for i in range(n):
        try:
            key_src = curve_src.GetKey(i)
            t = key_src.GetTime()
            val = key_src.GetValue(curve_src)
            new_val = transform_fn(val)
            key_dict = curve_dest.AddKey(t)
            if key_dict is None:
                continue
            key_dest = key_dict.get("key")
            nidx = key_dict.get("nidx", 0)
            if key_dest is not None:
                key_dest.SetValue(curve_dest, new_val)
                try:
                    curve_dest.SetKeyDefault(doc, nidx)
                except Exception:
                    pass
        except Exception:
            continue


def _transfer_rig_ud_keys_to_targets(
    doc: c4d.documents.BaseDocument,
    rig: c4d.BaseObject,
    circle: c4d.BaseObject,
    objs,
) -> None:
    """Transfer animated UD from rig to the objects that use them (orbit->align, radius->circle, etc.)."""
    from c4d import utils
    id_rel_pos = getattr(c4d, "ID_BASEOBJECT_REL_POSITION", None)
    id_rel_rot = getattr(c4d, "ID_BASEOBJECT_REL_ROTATION", None)
    focal_id = getattr(c4d, "RSCAMERAOBJECT_FOCAL_LENGTH", None) or getattr(c4d, "CAMERA_FOCUS", None)
    if not objs or not objs.align or not objs.cam or not objs.fx:
        return
    ud_by_name = {}
    for desc_id, bc in rig.GetUserDataContainer():
        name = _get_ud_name_safe(bc)
        if name:
            ud_by_name[name] = desc_id
    # Orbit -> Align to Spline Position (0..1)
    if config.UD_ORBIT in ud_by_name and objs.align:
        _copy_float_track(
            doc, rig, ud_by_name[config.UD_ORBIT],
            objs.align, c4d.DescID(c4d.ALIGNTOSPLINETAG_POSITION),
            lambda v: float(v) / 360.0,
        )
    # Radius -> circle
    if config.UD_RADIUS in ud_by_name:
        _copy_float_track(
            doc, rig, ud_by_name[config.UD_RADIUS],
            circle, c4d.DescID(c4d.PRIM_CIRCLE_RADIUS),
            float,
        )
    # Offset X,Y,Z -> offset null rel position (three UD -> one vector track: sample and set)
    if id_rel_pos and config.UD_OFFSET_X in ud_by_name and config.UD_OFFSET_Y in ud_by_name and config.UD_OFFSET_Z in ud_by_name:
        _copy_vector_track_from_three_ud(
            doc, rig,
            ud_by_name[config.UD_OFFSET_X], ud_by_name[config.UD_OFFSET_Y], ud_by_name[config.UD_OFFSET_Z],
            objs.offset, id_rel_pos,
            lambda x, y, z: c4d.Vector(float(x), float(y), float(z)),
        )
    # Rot H,P,B -> FX_CAM rel rotation (degrees -> radians)
    if id_rel_rot and config.UD_ROT_H in ud_by_name and config.UD_ROT_P in ud_by_name and config.UD_ROT_B in ud_by_name:
        _copy_vector_track_from_three_ud(
            doc, rig,
            ud_by_name[config.UD_ROT_H], ud_by_name[config.UD_ROT_P], ud_by_name[config.UD_ROT_B],
            objs.fx, id_rel_rot,
            lambda h, p, b: c4d.Vector(utils.DegToRad(h), utils.DegToRad(p), utils.DegToRad(b)),
        )
    # Focal -> RS_CAM and FX_CAM
    if focal_id and config.UD_FOCAL in ud_by_name:
        desc_focal = c4d.DescID(focal_id)
        _copy_float_track(doc, rig, ud_by_name[config.UD_FOCAL], objs.cam, desc_focal, float)
        _copy_float_track(doc, rig, ud_by_name[config.UD_FOCAL], objs.fx, desc_focal, float)
    # Focus Distance -> Focus object rel position Z (local (0,0,-distance))
    if objs.focus and config.UD_FOCUS_DISTANCE in ud_by_name:
        try:
            id_rel_pos = getattr(c4d, "ID_BASEOBJECT_REL_POSITION", None)
            if id_rel_pos is not None:
                desc_z = c4d.DescID(c4d.DescLevel(id_rel_pos, c4d.DTYPE_VECTOR, 0), c4d.DescLevel(2, c4d.DTYPE_REAL, 0))
                _copy_float_track(doc, rig, ud_by_name[config.UD_FOCUS_DISTANCE], objs.focus, desc_z, float)
        except Exception:
            pass
    # Shake — процедурный в Python Tag; при Break ключи Shake не переносим на отдельный объект


def _copy_vector_track_from_three_ud(
    doc: c4d.documents.BaseDocument,
    rig: c4d.BaseObject,
    desc_id_x: c4d.DescID,
    desc_id_y: c4d.DescID,
    desc_id_z: c4d.DescID,
    dest: c4d.BaseList2D,
    dest_param_id: int,
    vector_from_xyz,
) -> None:
    """Sample three float UD tracks at key times and write one vector track on dest."""
    tr_x = rig.FindCTrack(desc_id_x)
    tr_y = rig.FindCTrack(desc_id_y)
    tr_z = rig.FindCTrack(desc_id_z)
    if tr_x is None and tr_y is None and tr_z is None:
        return
    curve_x = tr_x.GetCurve() if tr_x else None
    curve_y = tr_y.GetCurve() if tr_y else None
    curve_z = tr_z.GetCurve() if tr_z else None
    times = set()
    for curve in (curve_x, curve_y, curve_z):
        if curve is not None:
            try:
                for i in range(curve.GetKeyCount()):
                    times.add(curve.GetKey(i).GetTime())
            except Exception:
                pass
    if not times:
        return
    try:
        fps = doc.GetFps()
        desc_id = c4d.DescID(dest_param_id)
        track_dest = dest.FindCTrack(desc_id)
        if track_dest is None:
            track_dest = c4d.CTrack(dest, desc_id)
            dest.InsertTrackSorted(track_dest)
        curve_dest = track_dest.GetCurve()
        if curve_dest is None:
            return
        for t in sorted(times, key=lambda bt: bt.Get()):
            try:
                vx = curve_x.GetValue(t, fps) if curve_x else 0.0
            except Exception:
                vx = 0.0
            try:
                vy = curve_y.GetValue(t, fps) if curve_y else 0.0
            except Exception:
                vy = 0.0
            try:
                vz = curve_z.GetValue(t, fps) if curve_z else 0.0
            except Exception:
                vz = 0.0
            vec = vector_from_xyz(vx, vy, vz)
            key_dict = curve_dest.AddKey(t)
            if key_dict is None:
                continue
            key_dest = key_dict.get("key")
            nidx = key_dict.get("nidx", 0)
            if key_dest is not None:
                key_dest.SetValue(curve_dest, vec)
                try:
                    curve_dest.SetKeyDefault(doc, nidx)
                except Exception:
                    pass
    except Exception:
        pass


def break_rig_user_data(doc: c4d.documents.BaseDocument, circle: c4d.BaseObject) -> None:
    """
    Break the link between the rig and User Data: transfer animated UD keys to target objects,
    remove rig objects from their layer, and remove the Python Tag from Main_Camera.
    """
    if not doc or not circle:
        return
    objs = get_rig_objects(circle, remove_vibrate=False)
    if not objs:
        c4d.GePrint("[CamRig] Break: could not resolve rig objects from Main_Camera.")
        return
    _transfer_rig_ud_keys_to_targets(doc, objs.rig, circle, objs)
    for obj in (objs.follow, objs.offset, objs.cam, objs.fx, objs.look_target, objs.focus):
        if obj is not None:
            try:
                obj.SetLayerObject(None)
            except Exception:
                pass
    tag = circle.GetFirstTag()
    while tag is not None:
        next_tag = tag.GetNext()
        if tag.GetType() == c4d.Tpython:
            tag.Remove()
            break
        tag = next_tag
    c4d.EventAdd()
