"""Единый вывод в Script Log для CamRig."""
import c4d

_PREFIX = "[CamRig]"


def info(msg: str) -> None:
    c4d.GePrint("%s %s" % (_PREFIX, msg))


def warn(msg: str) -> None:
    c4d.GePrint("%s WARNING: %s" % (_PREFIX, msg))


def error(msg: str) -> None:
    c4d.GePrint("%s ERROR: %s" % (_PREFIX, msg))
