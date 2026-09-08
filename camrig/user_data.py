"""
Вспомогательные функции для работы с User Data объектов C4D.
Массовое чтение UD в рантайме тега — в camrig.tag_embedded (`_read_all_user_data`).
"""
import c4d
from typing import Any, Optional

from .ud_utils import get_ud_desc_name


def get_user_data(obj: c4d.BaseObject, name: str) -> Optional[Any]:
    """Возвращает значение User Data по имени. Группы пропускаются (по имени не различаются)."""
    if not name:
        return None
    for desc_id, bc in obj.GetUserDataContainer():
        if get_ud_desc_name(bc) != name:
            continue
        try:
            return obj[desc_id]
        except (TypeError, AttributeError):
            return None
    return None
