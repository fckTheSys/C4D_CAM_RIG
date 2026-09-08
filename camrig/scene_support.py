"""Scene metadata, evaluation priorities and undo boundaries."""
from contextlib import contextmanager
import c4d
from . import config

_undo_scopes = []  # Main-thread command scopes, never expression/runtime state.

def add_undo(doc, kind, node):
    if not doc.AddUndo(kind, node):
        raise RuntimeError("Cinema 4D could not record Undo; command stopped.")
    for scope in reversed(_undo_scopes):
        if scope["doc"] == doc:
            scope["count"] += 1
            break

def set_schema(rig):
    meta = rig.GetDataInstance().GetContainer(config.META_ID)
    meta[config.META_SCHEMA] = config.SCHEMA_VERSION
    rig.GetDataInstance().SetContainer(config.META_ID, meta)

def schema_version(rig):
    return rig.GetDataInstance().GetContainer(config.META_ID).GetInt32(config.META_SCHEMA)

def set_priority(tag, value):
    priority = c4d.PriorityData()
    priority.SetPriorityValue(c4d.PRIORITYVALUE_MODE, c4d.CYCLE_EXPRESSION)
    priority.SetPriorityValue(c4d.PRIORITYVALUE_PRIORITY, value)
    priority.SetPriorityValue(c4d.PRIORITYVALUE_CAMERADEPENDENT, False)
    tag[c4d.EXPRESSION_PRIORITY] = priority

def configure_priorities(early, align, target, late, spring=None):
    for tag, value in ((early, -20), (align, -10), (spring, -5), (target, 0), (late, 20)):
        if tag is not None:
            set_priority(tag, value)

@contextmanager
def undo_group(doc):
    if not c4d.threading.GeIsMainThread():
        raise RuntimeError("CamRig scene commands require the main thread.")
    if any(scope["doc"] == doc for scope in _undo_scopes):
        raise RuntimeError("Nested CamRig Undo groups are not supported.")
    c4d.StopAllThreads()
    if not doc.StartUndo():
        raise RuntimeError("Cinema 4D could not start Undo.")
    scope = {"doc": doc, "count": 0}
    _undo_scopes.append(scope)
    try:
        yield
    except Exception:
        doc.EndUndo()
        if scope["count"]:
            doc.DoUndo()
        c4d.EventAdd()
        raise
    else:
        doc.EndUndo()
        c4d.EventAdd()
    finally:
        _undo_scopes.remove(scope)
