import c4d
from typing import Optional

from . import config

# Единицы для слайдеров (могут отсутствовать в старых версиях C4D)
_UNIT_DEGREE = getattr(c4d, "DESC_UNIT_DEGREE", None)
_UNIT_PERCENT = getattr(c4d, "DESC_UNIT_PERCENT", None)


def add_slider(
    obj: c4d.BaseObject,
    name: str,
    val: float,
    minv: float,
    maxv: float,
    parent_group: Optional[c4d.DescID] = None,
    step: float = 0.01,
    unit: Optional[int] = None,
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
    Код, который будет записан в Python Tag.
    Он очень короткий и просто делегирует логику в модуль camrig.python_tag_logic.
    """
    return (
        "import c4d\n"
        "from camrig import python_tag_logic\n\n"
        "def main():\n"
        "    python_tag_logic.main(op)\n"
    )


def _add_controller_user_data(
    circle: c4d.BaseObject,
    target_a: c4d.BaseObject,
    target_b: c4d.BaseObject,
) -> None:
    """Добавляет на контроллер (circle) все группы и User Data (орбита, offset, rotation, focal, shake, target)."""
    group_orbit = _add_group(circle, "Orbit & Radius")
    add_slider(circle, config.UD_ORBIT, config.DEFAULT_ORBIT, 0, 360, parent_group=group_orbit, step=0.1, unit=_UNIT_DEGREE)
    add_slider(circle, config.UD_RADIUS, config.DEFAULT_RADIUS, 0, 5000, parent_group=group_orbit, step=1)

    group_offset = _add_group(circle, "Offset")
    add_slider(circle, config.UD_OFFSET_X, config.DEFAULT_OFFSET_X, -2000, 2000, parent_group=group_offset, step=1)
    add_slider(circle, config.UD_OFFSET_Y, config.DEFAULT_OFFSET_Y, -2000, 2000, parent_group=group_offset, step=1)
    add_slider(circle, config.UD_OFFSET_Z, config.DEFAULT_OFFSET_Z, -2000, 2000, parent_group=group_offset, step=1)

    group_rotation = _add_group(circle, "Rotation")
    add_slider(circle, config.UD_ROT_H, config.DEFAULT_ROT_H, -180, 180, parent_group=group_rotation, step=0.1, unit=_UNIT_DEGREE)
    add_slider(circle, config.UD_ROT_P, config.DEFAULT_ROT_P, -180, 180, parent_group=group_rotation, step=0.1, unit=_UNIT_DEGREE)
    add_slider(circle, config.UD_ROT_B, config.DEFAULT_ROT_B, -180, 180, parent_group=group_rotation, step=0.1, unit=_UNIT_DEGREE)

    group_camera = _add_group(circle, "Camera")
    add_slider(circle, config.UD_FOCAL, config.DEFAULT_FOCAL, 10, 200, parent_group=group_camera, step=0.1)

    group_shake = _add_group(circle, "Shake")
    add_bool(circle, config.UD_SHAKE_ENABLE, config.DEFAULT_SHAKE_ENABLE, parent_group=group_shake)
    add_slider(circle, config.UD_SHAKE_POS, config.DEFAULT_SHAKE_POS, 0, 100, parent_group=group_shake, step=0.1)
    add_slider(circle, config.UD_SHAKE_ROT, config.DEFAULT_SHAKE_ROT, 0, 20, parent_group=group_shake, step=0.01)

    group_target = _add_group(circle, "Target")
    add_link(circle, config.UD_TARGET_A, default_link=target_a, parent_group=group_target)
    add_link(circle, config.UD_TARGET_B, default_link=target_b, parent_group=group_target)
    add_bool(circle, config.UD_USE_TARGET_B, config.DEFAULT_USE_TARGET_B, parent_group=group_target)
    add_slider(circle, config.UD_TARGET_BLEND, config.DEFAULT_TARGET_BLEND, 0, 100, parent_group=group_target, step=1)


def build_cam_rig(
    doc: c4d.documents.BaseDocument,
    position_global: Optional[c4d.Matrix] = None,
) -> None:
    """
    Строит камеру-риг в переданном документе.
    Риг всегда создаётся в корне документа.
    Если передан position_global (например mg активного null), риг ставится в этих координатах.
    """
    # ------------------------------------------------
    # RIG ROOT
    # ------------------------------------------------
    rig = c4d.BaseObject(c4d.Onull)
    rig.SetName(config.RIG_ROOT_NAME)
    if position_global is not None:
        rig.SetMg(position_global)
    doc.InsertObject(rig)

    # ------------------------------------------------
    # Target_A, Target_B, Look_Target, Main_Camera — прямые дети rig (соседи).
    # InsertAfter гарантирует, что они не окажутся дочерними объектами друг друга.
    # ------------------------------------------------
    target_a = c4d.BaseObject(c4d.Onull)
    target_a.SetName(config.TARGET_A_NAME)
    target_a.InsertUnder(rig)

    target_b = c4d.BaseObject(c4d.Onull)
    target_b.SetName(config.TARGET_B_NAME)
    target_b.SetRelPos(c4d.Vector(0, 0, 200))
    target_b.InsertAfter(target_a)

    aim = c4d.BaseObject(c4d.Onull)
    aim.SetName(config.LOOK_TARGET_NAME)
    aim.SetRelPos(target_a.GetRelPos())
    aim.InsertAfter(target_b)

    circle = c4d.BaseObject(c4d.Osplinecircle)
    circle.SetName(config.MAIN_CAMERA_NAME)
    circle[c4d.PRIM_PLANE] = c4d.PRIM_PLANE_XZ
    circle[c4d.PRIM_CIRCLE_RADIUS] = config.DEFAULT_RADIUS
    circle.InsertAfter(aim)

    # ------------------------------------------------
    # FOLLOW OBJECT
    # ------------------------------------------------
    follow = c4d.BaseObject(c4d.Onull)
    follow.SetName(config.FOLLOW_NAME)
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
    offset.SetName(config.OFFSET_NAME)
    offset.InsertUnder(follow)

    # ------------------------------------------------
    # MAIN CAMERA
    # ------------------------------------------------
    cam = c4d.BaseObject(c4d.Ocamera)
    cam.SetName("RS_CAM")
    cam.InsertUnder(offset)

    # ------------------------------------------------
    # FX CAMERA
    # ------------------------------------------------
    fx = c4d.BaseObject(c4d.Ocamera)
    fx.SetName("FX_CAM")
    fx.InsertUnder(cam)

    # Камера смотрит на Look_Target (позиция = blend между Target A и Target B)
    tgt = c4d.BaseTag(c4d.Ttargetexpression)
    cam.InsertTag(tgt)
    tgt[c4d.TARGETEXPRESSIONTAG_LINK] = aim

    # Shake реализуется процедурно в Python Tag, Vibrate не создаём.

    _add_controller_user_data(circle, target_a, target_b)

    # Лок трансформации circle — управляется только орбитой/радиусом через плагин
    _lock_circle_transform(circle)

    # ------------------------------------------------
    # PYTHON TAG
    # ------------------------------------------------
    py = c4d.BaseTag(c4d.Tpython)
    circle.InsertTag(py)

    py[c4d.TPYTHON_CODE] = _build_python_tag_source()


def reset_rig_to_defaults(circle: c4d.BaseObject) -> None:
    """
    Сбрасывает User Data объекта circle (Main_Camera) к дефолтам из config.
    Ссылки (Target A/B) не меняются.
    """
    for desc_id, bc in circle.GetUserDataContainer():
        name = bc.Get(c4d.DESC_NAME, "")
        if name in config.UD_DEFAULTS:
            circle[desc_id] = config.UD_DEFAULTS[name]
