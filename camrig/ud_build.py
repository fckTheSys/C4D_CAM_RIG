"""Создание элементов User Data из примитивов и из ud_template.json."""
import c4d
import json
import os
from typing import Any, Dict, List, Optional

from . import config
from . import log

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


def add_group(obj: c4d.BaseObject, name: str, titlebar: bool = True) -> c4d.DescID:
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


def load_ud_template() -> Optional[Dict[str, Any]]:
    """Загружает JSON-шаблон User Data из ud_template.json рядом с этим модулем."""
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


def build_user_data_from_template(
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
        parent_group = add_group(rig, group_name, titlebar)
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


def apply_ud_defaults_from_template(template: Dict[str, Any]) -> None:
    """Строит из шаблона dict имя -> default для real/bool и обновляет config.UD_DEFAULTS."""
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


def validate_ud_template_vs_config() -> None:
    """
    Проверка консистентности при загрузке плагина:
      1) каждое real/bool из ud_template.json есть в config.UD_DEFAULTS;
      2) каждое имя из config.UD_DEFAULTS встречается в ud_template.json.
    Несоответствия не валят плагин — пишутся как WARNING в Script Log.
    """
    template = load_ud_template()
    if template is None:
        log.warn("ud_template.json missing or invalid — cannot validate UD vs config.UD_DEFAULTS.")
        return
    template_names: List[str] = []
    missing_in_config: List[str] = []
    for group in template.get("groups", []):
        for param in group.get("params", []):
            ptype = param.get("type")
            name = param.get("name")
            if not name or ptype not in ("real", "bool"):
                continue
            template_names.append(name)
            if name not in config.UD_DEFAULTS:
                missing_in_config.append(name)
    if missing_in_config:
        log.warn(
            "ud_template.json has real/bool params not in config.UD_DEFAULTS: "
            + ", ".join(sorted(set(missing_in_config)))
        )
    template_set = set(template_names)
    missing_in_template = [n for n in config.UD_DEFAULTS.keys() if n not in template_set]
    if missing_in_template:
        log.warn(
            "config.UD_DEFAULTS has names not present in ud_template.json: "
            + ", ".join(sorted(set(missing_in_template)))
        )
