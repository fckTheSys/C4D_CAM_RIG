"""Общие утилиты для описания User Data (DESC_NAME из BaseContainer)."""
import c4d


def get_ud_desc_name(bc: c4d.BaseContainer) -> str:
    """Безопасно читает имя элемента описания UD. BaseContainer не имеет .get()."""
    try:
        return bc[c4d.DESC_NAME] or ""
    except Exception:
        return ""
