"""
Логика Python Tag в редакторе: делегирует во встраиваемый tag_embedded.py
(идентичное поведение с кодом в сцене).
"""
import c4d

from . import tag_embedded


def main(op: c4d.BaseTag) -> None:
    tag_embedded._execute(op)


def message(op: c4d.BaseTag, mid: int, data) -> bool:
    return tag_embedded.message(mid, data)
