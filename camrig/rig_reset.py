"""Сброс User Data рига к значениям по умолчанию."""
from typing import List

import c4d

from . import config
from .ud_utils import get_ud_desc_name


def _set_ud_value_safe(obj: c4d.BaseObject, desc_id: c4d.DescID, value) -> None:
    """Записывает значение в UD с приведением типа (bool -> int для C4D)."""
    try:
        if isinstance(value, bool):
            obj[desc_id] = int(value)
        elif isinstance(value, int):
            obj[desc_id] = value
        elif isinstance(value, float):
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
        name = get_ud_desc_name(bc)
        if name in keys_to_reset and name in config.UD_DEFAULTS:
            _set_ud_value_safe(obj, desc_id, config.UD_DEFAULTS[name])


def reset_rig_to_defaults(obj: c4d.BaseObject) -> None:
    """
    Сбрасывает User Data объекта (rig или circle) к дефолтам из config.
    Ссылки (Target A/B) не меняются.
    """
    for desc_id, bc in obj.GetUserDataContainer():
        name = get_ud_desc_name(bc)
        if name in config.UD_DEFAULTS:
            _set_ud_value_safe(obj, desc_id, config.UD_DEFAULTS[name])
