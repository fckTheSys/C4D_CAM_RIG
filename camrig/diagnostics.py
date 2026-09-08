"""Read-only diagnostics and explicit, undoable repair of known schema-2 rigs."""
import c4d
from . import config, tag_embedded
from .commands import choose_rig, find_circle, ud_map, runtime_tags, normalized_source
from .rig_objects import get_rig_objects
from .rig_assemble import _build_python_tag_source
from .scene_support import schema_version, undo_group, configure_priorities

def run_self_check():
    from .ud_build import validate_ud_template_vs_config
    validate_ud_template_vs_config()
    return ["CamRig " + config.PLUGIN_VERSION, "Runtime " + tag_embedded.EMBEDDED_RUNTIME_VERSION,
            "Schema " + str(config.SCHEMA_VERSION), "UD template checked"]

def inspect_rig(doc, rig=None):
    rig = rig or choose_rig(doc)
    objs = get_rig_objects(find_circle(rig))
    if objs is None:
        return False, "Incomplete hierarchy; repair cannot rebuild it safely."
    lines = ["Rig: " + rig.GetName(), "Schema: " + str(schema_version(rig))]
    ok = True
    for key in ("target_a", "target_b", "look_target", "follow", "offset", "cam", "fx", "align", "target_expr", "focus"):
        if getattr(objs, key) is None:
            lines.append("MISSING: " + key)
            ok = False
    if schema_version(rig) == 0:
        lines.append("Legacy rig: use Upgrade Selected Rig; no automatic scene changes.")
    source = normalized_source(_build_python_tag_source())
    tags = runtime_tags(objs.circle)
    if schema_version(rig) == config.SCHEMA_VERSION:
        if len(tags) != 2 or {t.GetName() for t in tags} != {"CamRig Runtime 1.5", config.FOCUS_TAG_NAME}:
            lines.append("WARNING: runtime stages missing or renamed.")
            ok = False
        if any(normalized_source(t[c4d.TPYTHON_CODE]) != source for t in tags):
            lines.append("WARNING: embedded runtime edited or outdated.")
            ok = False
    ids = ud_map(rig)
    for key in (config.UD_TARGET_A, config.UD_TARGET_B, config.UD_ORBIT_CENTER, config.UD_FOCUS_TARGET):
        value = rig[ids[key]] if key in ids else None
        if value is not None and tag_embedded.valid_target(value, objs) is None:
            lines.append("WARNING: " + key + " rejected: cross-document or camera-driven descendant creates a dependency cycle.")
            ok = False
    if config.UD_FOCUS_MODE in ids and rig[ids[config.UD_FOCUS_MODE]] == 2:
        if tag_embedded.valid_target(rig[ids[config.UD_FOCUS_TARGET]], objs) is None:
            lines.append("WARNING: Focus Target unavailable; manual distance is used.")
    if (objs.look_target.GetMg().off - objs.cam.GetMg().off).GetLength() < 1e-8:
        lines.append("WARNING: camera and look point coincide; aim direction is undefined.")
    if objs.vib:
        lines.append("WARNING: legacy Vibrate found; use Repair/Upgrade.")
    return ok, "\n".join(lines)

def repair_selected_rig(doc, rig=None):
    rig = rig or choose_rig(doc)
    if schema_version(rig) != config.SCHEMA_VERSION:
        return False, "Legacy/unknown schema: use Upgrade; Repair will not rewrite its runtime."
    circle = find_circle(rig)
    objs = get_rig_objects(circle)
    if objs is None:
        return False, "Incomplete hierarchy; cannot safely reconstruct it."
    source = _build_python_tag_source()
    known_names = ("CamRig Runtime 1.5", config.FOCUS_TAG_NAME)
    tags = runtime_tags(circle)
    if any(t.GetName() not in known_names or normalized_source(t[c4d.TPYTHON_CODE]) != normalized_source(source) for t in tags):
        return False, "Unknown or edited Python tag; refusing overwrite."
    if len({t.GetName() for t in tags}) != len(tags):
        return False, "Duplicate runtime stages; resolve manually."
    changes = []
    with undo_group(doc):
        align, target = objs.align, objs.target_expr
        if align is None:
            align = c4d.BaseTag(c4d.Taligntospline)
            objs.follow.InsertTag(align)
            doc.AddUndo(c4d.UNDOTYPE_NEWOBJ, align)
            changes.append("Align")
        else:
            doc.AddUndo(c4d.UNDOTYPE_CHANGE, align)
        align[c4d.ALIGNTOSPLINETAG_LINK] = circle
        align[c4d.ALIGNTOSPLINETAG_AXIS] = 3
        align[c4d.ALIGNTOSPLINETAG_TANGENTIAL] = True
        if target is None:
            target = c4d.BaseTag(c4d.Ttargetexpression)
            objs.cam.InsertTag(target)
            doc.AddUndo(c4d.UNDOTYPE_NEWOBJ, target)
            changes.append("Target")
        else:
            doc.AddUndo(c4d.UNDOTYPE_CHANGE, target)
        target[c4d.TARGETEXPRESSIONTAG_LINK] = objs.look_target
        if objs.focus is None:
            focus = c4d.BaseObject(c4d.Onull)
            focus.SetName(config.FOCUS_NAME)
            focus.InsertUnder(objs.fx)
            doc.AddUndo(c4d.UNDOTYPE_NEWOBJ, focus)
            changes.append("Focus")
        stages = {}
        for name in known_names:
            tag = next((t for t in tags if t.GetName() == name), None)
            if tag is None:
                tag = c4d.BaseTag(c4d.Tpython)
                tag.SetName(name)
                tag[c4d.TPYTHON_CODE] = source
                circle.InsertTag(tag)
                doc.AddUndo(c4d.UNDOTYPE_NEWOBJ, tag)
                changes.append(name)
            else:
                doc.AddUndo(c4d.UNDOTYPE_CHANGE, tag)
            stages[name] = tag
        configure_priorities(stages[known_names[0]], align, target, stages[known_names[1]])
        if objs.vib:
            doc.AddUndo(c4d.UNDOTYPE_DELETEOBJ, objs.vib)
            objs.vib.Remove()
            changes.append("removed legacy Vibrate")
    return True, "Repair: priorities/links checked; " + (", ".join(changes) or "no missing components.")
