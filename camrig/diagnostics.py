# -*- coding: utf-8 -*-
import c4d

from . import config
from .rig_objects import get_rig_objects


def run_self_check() -> list[str]:
    lines = ["%s v%s self check" % (config.PLUGIN_NAME, config.PLUGIN_VERSION)]
    try:
        from . import tag_embedded
        emb = getattr(tag_embedded, "EMBEDDED_RUNTIME_VERSION", None)
    except Exception:
        emb = None
    lines.append("Embedded runtime: %s" % (emb or "MISSING"))
    if emb != config.PLUGIN_VERSION:
        lines.append("WARNING: embedded runtime version differs from PLUGIN_VERSION.")
    lines.append("CamRigRoot plugin ID: %s" % config.PLUGIN_ID_CAMRIG_ROOT)
    lines.append("Main plugin ID: %s" % config.PLUGIN_ID)
    return lines


def inspect_rig(doc) -> tuple[bool, str]:
    if doc is None:
        return False, "No active document."
    rig = _find_rig(doc)
    if rig is None:
        return False, "No Cam_Rig found. Select any object inside the rig first."
    circle = _find_main_camera_for_rig(rig)
    if circle is None:
        return False, "Rig found: %s\nERROR: Main_Camera not found." % rig.GetName()
    objs = get_rig_objects(circle, remove_vibrate=False)
    lines = ["Rig Inspector:", "Rig: " + rig.GetName(), "Main camera: " + circle.GetName()]
    if objs is None:
        lines.append("ERROR: Rig hierarchy cannot be resolved.")
        return False, "\n".join(lines)

    checks = (
        ("Target A", objs.target_a),
        ("Target B", objs.target_b),
        ("Look Target", objs.look_target),
        ("Follow", objs.follow),
        ("Offset", objs.offset),
        ("RS_CAM", objs.cam),
        ("FX_CAM", objs.fx),
        ("Align tag", objs.align),
        ("Target tag", objs.target_expr),
        ("Focus", objs.focus),
    )
    ok = True
    for label, obj in checks:
        if obj is None:
            ok = False
            lines.append("MISSING: " + label)
        else:
            lines.append("OK: " + label)
    first_child = objs.follow.GetDown() if objs.follow else None
    if first_child and first_child.GetName().startswith(config.LEGACY_INERTIA_FOLLOW_PREFIX):
        lines.append("Legacy: Inertia_Follow detected.")
    try:
        from . import tag_embedded
        lines.append("Embedded runtime: " + str(getattr(tag_embedded, "EMBEDDED_RUNTIME_VERSION", "?")))
    except Exception:
        lines.append("Embedded runtime: unavailable")
    return ok, "\n".join(lines)


def repair_selected_rig(doc) -> tuple[bool, str]:
    if doc is None:
        return False, "No active document."
    rig = _find_rig(doc)
    if rig is None:
        return False, "No Cam_Rig found."
    circle = _find_main_camera_for_rig(rig)
    if circle is None:
        return False, "Main_Camera not found; repair cannot safely rebuild hierarchy."

    changed = []
    objs = get_rig_objects(circle, remove_vibrate=False)
    if objs is None:
        return False, "Rig hierarchy cannot be resolved enough for safe repair."

    if objs.align is None and objs.follow is not None:
        align = c4d.BaseTag(c4d.Taligntospline)
        objs.follow.InsertTag(align)
        align[c4d.ALIGNTOSPLINETAG_LINK] = circle
        align[c4d.ALIGNTOSPLINETAG_AXIS] = 3
        align[c4d.ALIGNTOSPLINETAG_TANGENTIAL] = True
        changed.append("Align to Spline tag")

    if objs.target_expr is None and objs.cam is not None and objs.look_target is not None:
        tgt = c4d.BaseTag(c4d.Ttargetexpression)
        objs.cam.InsertTag(tgt)
        tgt[c4d.TARGETEXPRESSIONTAG_LINK] = objs.look_target
        changed.append("Target Expression tag")

    if objs.focus is None and objs.fx is not None:
        focus = c4d.BaseObject(c4d.Onull)
        focus.SetName(config.FOCUS_NAME)
        focus.SetRelPos(c4d.Vector(0, 0, config.DEFAULT_FOCUS_DISTANCE))
        focus.InsertUnder(objs.fx)
        changed.append("Focus object")

    py = circle.GetTag(c4d.Tpython)
    if py is None:
        try:
            from .rig_assemble import _build_python_tag_source
            py = c4d.BaseTag(c4d.Tpython)
            circle.InsertTag(py)
            py[c4d.TPYTHON_CODE] = _build_python_tag_source()
            changed.append("Python tag")
        except Exception as e:
            return False, "Failed to restore Python tag: %s" % e

    if changed:
        c4d.EventAdd()
        return True, "Repair done: " + ", ".join(changed)
    return True, "Repair: nothing to change."


def _find_rig(doc):
    active = doc.GetActiveObject()
    if active:
        obj = active
        while obj:
            name = obj.GetName()
            if name == config.RIG_ROOT_NAME or name.startswith(config.RIG_ROOT_NAME + "_"):
                return obj
            obj = obj.GetUp()
    root = doc.GetFirstObject()
    while root:
        name = root.GetName()
        if name == config.RIG_ROOT_NAME or name.startswith(config.RIG_ROOT_NAME + "_"):
            return root
        root = root.GetNext()
    return None


def _find_main_camera_for_rig(rig):
    child = rig.GetDown()
    while child:
        if child.GetName().startswith(config.MAIN_CAMERA_NAME):
            return child
        child = child.GetNext()
    return None
