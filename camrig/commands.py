"""Shared selection, navigation and migration operations (UI and MCP)."""
import math
from pathlib import Path
import c4d
from . import config
from .rig_objects import get_rig_objects
from .scene_support import add_undo, undo_group, schema_version, set_schema, configure_priorities
from .ud_build import load_ud_template, build_user_data_from_template, set_real_limits
from .rig_assemble import _build_python_tag_source

def walk(root):
    while root:
        yield root
        yield from walk(root.GetDown())
        root = root.GetNext()

def find_circle(rig):
    child = rig.GetDown()
    while child:
        if child.GetName().startswith(config.MAIN_CAMERA_NAME) and child.CheckType(c4d.Osplinecircle):
            return child
        child = child.GetNext()
    return None

def is_rig(obj):
    return obj is not None and find_circle(obj) is not None

def choose_rig(doc, interactive=False):
    candidates = []
    for active in doc.GetActiveObjects(c4d.GETACTIVEOBJECTFLAGS_NONE):
        node = active
        while node:
            if is_rig(node):
                if node not in candidates:
                    candidates.append(node)
                break
            node = node.GetUp()
    if not candidates:
        candidates = [obj for obj in walk(doc.GetFirstObject()) if is_rig(obj)]
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise ValueError("No CamRig found.")
    if interactive:
        menu = c4d.BaseContainer()
        for index, rig in enumerate(candidates):
            menu[1000 + index] = rig.GetName() + " [" + str(index + 1) + "]"
        selected = c4d.gui.ShowPopupDialog(None, menu, c4d.MOUSEPOS, c4d.MOUSEPOS)
        if 1000 <= selected < 1000 + len(candidates):
            return candidates[selected - 1000]
        return None
    raise ValueError("Several rigs found. Select one rig or an object inside it.")

def ud_map(rig):
    return {bc[c4d.DESC_NAME]: desc for desc, bc in rig.GetUserDataContainer()
            if desc[-1].dtype != c4d.DTYPE_GROUP}

def select_part(doc, rig, part):
    objs = get_rig_objects(find_circle(rig))
    if objs is None:
        raise ValueError("Incomplete rig hierarchy.")
    c4d.StopAllThreads()
    if part == "camera":
        doc.GetActiveBaseDraw().SetSceneCamera(objs.fx)
    else:
        nodes = {"rig": [rig], "orbit": [objs.circle], "targets": [objs.target_a, objs.target_b]}[part]
        for index, node in enumerate(nodes):
            doc.SetActiveObject(node, c4d.SELECTION_NEW if index == 0 else c4d.SELECTION_ADD)
    c4d.EventAdd()

def normalized_source(code):
    return code.replace("\r\n", "\n").strip()

def runtime_tags(circle):
    return [t for t in circle.GetTags() if t.CheckType(c4d.Tpython)]

def upgrade_rig(doc, rig):
    """Preflight first; preserve UD identities/tracks and restore original code via Undo."""
    circle = find_circle(rig)
    objs = get_rig_objects(circle) if circle else None
    if objs is None or objs.align is None or objs.target_expr is None:
        raise ValueError("Upgrade requires an intact orbital rig including Align and Target tags.")
    tags = runtime_tags(circle)
    source = _build_python_tag_source()
    if schema_version(rig) == config.SCHEMA_VERSION:
        if (len(tags) != 3 or {t.GetName() for t in tags} != {"CamRig Runtime 1.5", config.FOCUS_TAG_NAME, config.SPRING_TAG_NAME}
                or any(normalized_source(t[c4d.TPYTHON_CODE]) != normalized_source(source) for t in tags)):
            raise ValueError("The 1.5 runtime was changed or a stage is missing. Refusing overwrite.")
        return False, "Rig is already up to date."
    if schema_version(rig) not in (0, 2):
        raise ValueError("Unsupported rig schema.")
    if schema_version(rig) == 2:
        if len(tags) != 2 or {t.GetName() for t in tags} != {"CamRig Runtime 1.5", config.FOCUS_TAG_NAME}:
            raise ValueError("CamRig 1.5 runtime stages are missing or renamed.")
        expected_150 = Path(__file__).with_name("legacy_150.txt").read_text(encoding="utf-8")
        if any(normalized_source(t[c4d.TPYTHON_CODE]) != normalized_source(expected_150) for t in tags):
            raise ValueError("Unknown or edited 1.5 runtime. Upgrade would overwrite custom code.")
        template = load_ud_template()
        new_groups = [g for g in template["groups"] if g["name"] == "Spring"]
        early = next(t for t in tags if t.GetName() == "CamRig Runtime 1.5")
        late = next(t for t in tags if t.GetName() == config.FOCUS_TAG_NAME)
        with undo_group(doc):
            for node in (rig, circle, early, late, objs.align, objs.target_expr):
                add_undo(doc, c4d.UNDOTYPE_CHANGE, node)
            build_user_data_from_template(rig, {"groups": new_groups}, {})
            spring_offset = c4d.BaseObject(c4d.Onull)
            spring_offset.SetName(config.SPRING_OFFSET_NAME)
            spring_offset.InsertUnder(objs.offset)
            add_undo(doc, c4d.UNDOTYPE_NEWOBJ, spring_offset)
            objs.cam.InsertUnder(spring_offset)
            spring_tag = c4d.BaseTag(c4d.Tpython)
            spring_tag.SetName(config.SPRING_TAG_NAME)
            spring_tag[c4d.TPYTHON_CODE] = source
            circle.InsertTag(spring_tag)
            add_undo(doc, c4d.UNDOTYPE_NEWOBJ, spring_tag)
            configure_priorities(early, objs.align, objs.target_expr, late, spring_tag)
            set_schema(rig)
        return True, "CamRig 1.5 upgraded to 1.6 with Spring Amount = 0."
    expected = Path(__file__).with_name("legacy_140.txt").read_text(encoding="utf-8")
    if len(tags) != 1 or normalized_source(tags[0][c4d.TPYTHON_CODE]) != normalized_source(expected):
        raise ValueError("Unknown or edited legacy runtime. Upgrade would overwrite custom code.")
    if circle.GetCTracks():
        raise ValueError("Circle has animation tracks. Automatic migration is not supported.")
    scale = circle.GetRelScale()
    if (scale-c4d.Vector(1)).GetLength() > 1e-8 or (circle.GetFrozenScale()-c4d.Vector(1)).GetLength() > 1e-8:
        raise ValueError("Circle has non-unit scale.")
    if circle.GetFrozenPos().GetLength() > 1e-8 or circle.GetFrozenRot().GetLength() > 1e-8:
        raise ValueError("Circle has frozen transforms. Automatic migration is not supported.")
    template = load_ud_template()
    if template is None:
        raise ValueError("Missing UD template.")
    existing = ud_map(rig)
    if not {"Orbit", "Radius", "Focal Length", "Focus Distance"}.issubset(existing):
        raise ValueError("Legacy control schema is incomplete.")
    if any(key in existing for key in config.ORBIT_RIG_KEYS + config.AIM_KEYS + [config.UD_FOCUS_MODE]):
        raise ValueError("Legacy rig already has conflicting new controls.")
    new_groups = [g for g in template["groups"] if g["name"] in ("Orbit Rig", "Aim Offset", "Focus", "Spring")]
    position, rotation = circle.GetRelPos(), circle.GetRelRot()
    early = tags[0]
    with undo_group(doc):
        for node in (rig, circle, early, objs.align, objs.target_expr):
            add_undo(doc, c4d.UNDOTYPE_CHANGE, node)
        try:
            meta = rig.GetDataInstance().GetContainer(config.META_ID)
            meta[config.META_BACKUP_CODE] = early[c4d.TPYTHON_CODE]
            meta[config.META_BACKUP_PRIORITY] = early[c4d.EXPRESSION_PRIORITY]
            rig.GetDataInstance().SetContainer(config.META_ID, meta)
            build_user_data_from_template(rig, {"groups": new_groups}, {})
            ids = ud_map(rig)
            for key, value in zip(config.ORBIT_RIG_KEYS, [position.x, position.y, position.z,
                                   math.degrees(rotation.x), math.degrees(rotation.y), math.degrees(rotation.z)]):
                rig[ids[key]] = value
            containers = rig.GetUserDataContainer()
            for key, lo, hi in (("Orbit", None, None), ("Radius", 0, None)):
                bc = next(bc for desc, bc in containers if desc == ids[key])
                set_real_limits(bc, lo, hi, 0, 360 if key == "Orbit" else 5000)
                rig.SetUserDataContainer(ids[key], bc)
            early.SetName("CamRig Runtime 1.5")
            early[c4d.TPYTHON_CODE] = source
            late = c4d.BaseTag(c4d.Tpython)
            late.SetName(config.FOCUS_TAG_NAME)
            late[c4d.TPYTHON_CODE] = source
            circle.InsertTag(late)
            add_undo(doc, c4d.UNDOTYPE_NEWOBJ, late)
            spring_offset = c4d.BaseObject(c4d.Onull)
            spring_offset.SetName(config.SPRING_OFFSET_NAME)
            spring_offset.InsertUnder(objs.offset)
            add_undo(doc, c4d.UNDOTYPE_NEWOBJ, spring_offset)
            objs.cam.InsertUnder(spring_offset)
            spring_tag = c4d.BaseTag(c4d.Tpython)
            spring_tag.SetName(config.SPRING_TAG_NAME)
            spring_tag[c4d.TPYTHON_CODE] = source
            circle.InsertTag(spring_tag)
            add_undo(doc, c4d.UNDOTYPE_NEWOBJ, spring_tag)
            configure_priorities(early, objs.align, objs.target_expr, late, spring_tag)
            set_schema(rig)
            # Structural legacy cleanup belongs to this command, not expressions.
            if objs.vib:
                add_undo(doc, c4d.UNDOTYPE_DELETEOBJ, objs.vib)
                objs.vib.Remove()
        except Exception:
            # End the undo group before rolling it back.
            raise
    return True, "Upgraded to 1.6; existing User Data and tracks preserved."

def break_preflight(rig):
    tags = runtime_tags(find_circle(rig))
    allowed = [normalized_source(_build_python_tag_source()),
               normalized_source(Path(__file__).with_name("legacy_140.txt").read_text(encoding="utf-8"))]
    if not tags or any(normalized_source(t[c4d.TPYTHON_CODE]) not in allowed for t in tags):
        raise ValueError("Break refuses unknown or edited runtime tags.")
    ids = ud_map(rig)
    keys = config.ORBIT_RIG_KEYS + config.AIM_KEYS + [config.UD_FOCUS_MODE, config.UD_FOCUS_OFFSET] + config.SPRING_KEYS
    for key in keys:
        desc = ids.get(key)
        if desc is not None and (rig.FindCTrack(desc) is not None or rig[desc] != config.UD_DEFAULTS[key]):
            raise ValueError("Break cannot preserve " + key + ". Keep the rig; full camera bake is required.")
    for key in (config.UD_ORBIT_CENTER, config.UD_FOCUS_TARGET):
        if key in ids and rig[ids[key]] is not None:
            raise ValueError("Break cannot preserve linked " + key + ".")
    orbit = ids.get(config.UD_ORBIT)
    if orbit is not None:
        track = rig.FindCTrack(orbit)
        if track or not 0 <= rig[orbit] < 360:
            raise ValueError("Break cannot preserve wrapped orbit animation. Full camera bake is required.")

def hud_instructions(doc, rig):
    select_part(doc, rig, "rig")
    return ("Native HUD creation is not exposed by the Cinema 4D Python API.\n"
            "In the Attribute Manager select Orbit, Radius, Height, Plane Tilt and Focal Length,\n"
            "then right-click > Add to HUD. These are the actual animated User Data values.\n"
            "Use each HUD element's native Show/Remove menu; other HUD elements are unaffected.")
