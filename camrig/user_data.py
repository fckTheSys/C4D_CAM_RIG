"""
Вспомогательные функции для работы с User Data объектов C4D.
"""
import c4d
from typing import Any, Optional


def get_user_data(obj: c4d.BaseObject, name: str) -> Optional[Any]:
    """Возвращает значение User Data по имени."""
    for desc_id, bc in obj.GetUserDataContainer():
        if bc[c4d.DESC_NAME] == name:
            return obj[desc_id]
    return None
