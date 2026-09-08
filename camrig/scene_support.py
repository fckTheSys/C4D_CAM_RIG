"""Scene metadata, evaluation priorities and undo boundaries."""
from contextlib import contextmanager
import c4d
from . import config

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

def configure_priorities(early, align, target, late):
    for tag, value in ((early, -20), (align, -10), (target, 0), (late, 20)):
        if tag is not None:
            set_priority(tag, value)

@contextmanager
def undo_group(doc):
    c4d.StopAllThreads()
    doc.StartUndo()
    try:
        yield
    except Exception:
        doc.EndUndo()
        doc.DoUndo()
        c4d.EventAdd()
        raise
    else:
        doc.EndUndo()
        c4d.EventAdd()
