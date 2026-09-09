"""Isolated document lifecycle helpers for the public CamRig MCP contract test.

No marker is written into a user's document. A C4D-interpreter session registry
holds the exact source document identity; a verified on-disk clone is the
emergency recovery path.
"""
import builtins
import c4d
import math
import os
import runpy

_SESSION_KEY = "__camrig_agent_mcp_contract_sessions__"


def _sessions():
    value = getattr(builtins, _SESSION_KEY, None)
    if value is None:
        value = {}
        setattr(builtins, _SESSION_KEY, value)
    return value


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _number(value):
    return round(float(value), 10) if _finite(value) else None


def _vector(value):
    return [_number(value.x), _number(value.y), _number(value.z)]


def _iter_objects(node):
    while node:
        yield node
        child = node.GetDown()
        if child:
            yield from _iter_objects(child)
        node = node.GetNext()


def _object_paths(doc):
    paths = {}

    def walk(node, parent):
        names = {}
        while node:
            base = node.GetName() or "<unnamed>"
            index = names.get(base, 0)
            names[base] = index + 1
            segment = base if index == 0 else "%s[%d]" % (base, index)
            path = parent + "/" + segment
            paths[id(node)] = path
            if node.GetDown():
                walk(node.GetDown(), path)
            node = node.GetNext()

    walk(doc.GetFirstObject(), "")
    return paths


def _path_for(value, paths):
    if value is None:
        return None
    return paths.get(id(value), "<external-or-unresolved>")


def _desc_id(desc_id):
    try:
        return [[int(desc_id[index].id), int(desc_id[index].dtype), int(desc_id[index].creator)]
                for index in range(desc_id.GetDepth())]
    except Exception:
        return []


def _track_state(node):
    result = []
    track = node.GetFirstCTrack()
    while track:
        curve = track.GetCurve()
        keys = []
        if curve:
            for index in range(curve.GetKeyCount()):
                key = curve.GetKey(index)
                item = {"time": _number(key.GetTime().Get()), "value": _number(key.GetValue()),
                        "interpolation": int(key.GetInterpolation())}
                for field, method in (("value_left", "GetValueLeft"), ("value_right", "GetValueRight"),
                                      ("time_left", "GetTimeLeft"), ("time_right", "GetTimeRight"),
                                      ("automatic_tangent", "GetAutomaticTangentMode")):
                    try:
                        value = getattr(key, method)()
                        item[field] = bool(value) if isinstance(value, bool) else _number(value)
                    except Exception:
                        item[field] = None
                keys.append(item)
        result.append({"desc_id": _desc_id(track.GetDescriptionID()), "keys": keys})
        track = track.GetNext()
    return result


def _value(value, paths):
    if value is None or isinstance(value, (str, bool)):
        return value
    if _finite(value):
        return _number(value)
    if isinstance(value, c4d.Vector):
        return _vector(value)
    if isinstance(value, c4d.BaseList2D):
        return {"link": _path_for(value, paths), "type": int(value.GetType())}
    return "<unsupported:%s>" % type(value).__name__


def _user_data(node, paths):
    result = []
    try:
        values = node.GetUserDataContainer()
    except Exception:
        return result
    for desc_id, container in values:
        try:
            value = node[desc_id]
        except Exception:
            value = "<unreadable>"
        result.append({"desc_id": _desc_id(desc_id), "name": container.GetString(c4d.DESC_NAME),
                       "value": _value(value, paths)})
    return result


def _tags(node, paths):
    result = []
    tag = node.GetFirstTag()
    while tag:
        result.append({"name": tag.GetName(), "type": int(tag.GetType()), "tracks": _track_state(tag),
                       "user_data": _user_data(tag, paths)})
        tag = tag.GetNext()
    return result


def _objects(doc, paths):
    return [{"path": _path_for(node, paths), "name": node.GetName(), "type": int(node.GetType()),
             "position": _vector(node.GetRelPos()), "rotation": _vector(node.GetRelRot()),
             "scale": _vector(node.GetRelScale()), "tracks": _track_state(node),
             "user_data": _user_data(node, paths), "tags": _tags(node, paths)}
            for node in _iter_objects(doc.GetFirstObject())]


def _iter_materials(doc):
    material = doc.GetFirstMaterial()
    while material:
        yield material
        material = material.GetNext()


def _materials(doc, paths):
    result = []
    for material in _iter_materials(doc):
        item = {"name": material.GetName(), "type": int(material.GetType()), "tracks": _track_state(material)}
        for field, parameter in (("use_color", c4d.MATERIAL_USE_COLOR), ("color", c4d.MATERIAL_COLOR_COLOR),
                                 ("use_luminance", c4d.MATERIAL_USE_LUMINANCE),
                                 ("luminance", c4d.MATERIAL_LUMINANCE_COLOR)):
            try:
                item[field] = _value(material[parameter], paths)
            except Exception:
                item[field] = None
        result.append(item)
    return result


def _registered(document):
    if document is None:
        return False
    node = c4d.documents.GetFirstDocument()
    while node:
        try:
            if node == document:
                return True
        except ReferenceError:
            return False
        node = node.GetNext()
    return False


def fingerprint(doc):
    """Return a JSON-safe, deliberately broad state fingerprint for QA."""
    paths = _object_paths(doc)
    render = doc.GetActiveRenderData().GetDataInstance()
    try:
        active = [_path_for(node, paths) for node in doc.GetActiveObjects(c4d.GETACTIVEOBJECTFLAGS_0)]
    except Exception:
        active = []
    scene_camera = None
    base_draw = doc.GetActiveBaseDraw()
    if base_draw:
        try:
            scene_camera = _path_for(base_draw.GetSceneCamera(doc), paths)
        except Exception:
            pass
    return {"fps": int(doc.GetFps()), "time": _number(doc.GetTime().Get()),
            "min_time": _number(doc.GetMinTime().Get()), "max_time": _number(doc.GetMaxTime().Get()),
            "active_objects": active, "scene_camera": scene_camera, "objects": _objects(doc, paths),
            "materials": _materials(doc, paths),
            "render": {"xres": int(render.GetInt32(c4d.RDATA_XRES)),
                       "yres": int(render.GetInt32(c4d.RDATA_YRES)),
                       "engine": int(render.GetInt32(c4d.RDATA_RENDERENGINE)),
                       "sequence": int(render.GetInt32(c4d.RDATA_FRAMESEQUENCE))}}


def _save_verified_snapshot(original, snapshot_path, before):
    snapshot = original.GetClone(c4d.COPYFLAGS_0)
    if snapshot is None:
        raise RuntimeError("could not clone original document for contract snapshot")
    if not c4d.documents.SaveDocument(snapshot, snapshot_path, c4d.SAVEDOCUMENTFLAGS_0, c4d.FORMAT_C4DEXPORT):
        raise RuntimeError("could not write contract snapshot")
    verified = c4d.documents.LoadDocument(snapshot_path, c4d.SCENEFILTER_OBJECTS | c4d.SCENEFILTER_MATERIALS, None)
    if verified is None:
        raise RuntimeError("could not reopen contract snapshot")
    try:
        if fingerprint(verified) != before:
            raise RuntimeError("contract snapshot verification fingerprint differs from source")
    finally:
        if _registered(verified):
            c4d.documents.KillDocument(verified)


def prepare(snapshot_path, temporary_name, fixture_path, token, fault=None):
    """Snapshot the active document and open a disposable QA document."""
    original = c4d.documents.GetActiveDocument()
    if original is None or not _registered(original):
        raise RuntimeError("active document is not registered; open or save it in Cinema 4D before running the contract harness")
    before = fingerprint(original)
    _save_verified_snapshot(original, snapshot_path, before)
    session = {"original": original, "original_name": original.GetDocumentName(),
               "original_path": original.GetDocumentPath(), "temporary": temporary_name,
               "snapshot": snapshot_path, "before": before}
    _sessions()[token] = session
    qa = None
    try:
        qa = runpy.run_path(fixture_path)["build"]()
        qa.SetDocumentName(temporary_name)
        c4d.documents.InsertBaseDocument(qa)
        c4d.documents.SetActiveDocument(qa)
        if fault == "after_insert":
            raise RuntimeError("injected setup failure after QA insertion")
    except Exception:
        if qa is not None and _registered(qa):
            c4d.documents.KillDocument(qa)
        if _registered(original):
            c4d.documents.SetActiveDocument(original)
        _sessions().pop(token, None)
        raise
    return {"temporary": temporary_name, "snapshot": snapshot_path, "token": token, "before": before,
            "snapshot_verified": True}


def cleanup(snapshot_path, temporary_name, token, before, fault=None):
    """Restore source or verified snapshot; a recovery is never ordinary PASS."""
    session = _sessions().pop(token, None)
    if session is None:
        raise RuntimeError("contract session registry entry is missing")
    temporary = None
    node = c4d.documents.GetFirstDocument()
    while node:
        if node.GetDocumentName() == temporary_name:
            temporary = node
            break
        node = node.GetNext()
    if temporary is None:
        raise RuntimeError("temporary document missing")
    if fault == "before_restore":
        _sessions()[token] = session
        raise RuntimeError("injected cleanup failure before restore")
    original = session["original"]
    source = "original"
    if not _registered(original):
        original = c4d.documents.LoadDocument(snapshot_path, c4d.SCENEFILTER_OBJECTS | c4d.SCENEFILTER_MATERIALS, None)
        if original is None:
            raise RuntimeError("contract snapshot could not be reopened")
        original.SetDocumentName(session["original_name"])
        original.SetDocumentPath(session["original_path"])
        c4d.documents.InsertBaseDocument(original)
        source = "snapshot"
    if fingerprint(original) != before:
        raise RuntimeError("original document fingerprint changed during contract test")
    c4d.documents.SetActiveDocument(original)
    c4d.documents.KillDocument(temporary)
    return {"restored": c4d.documents.GetActiveDocument() == original, "source": source,
            "status": "PASS" if source == "original" else "RECOVERED", "fingerprint_match": True,
            "snapshot": snapshot_path, "snapshot_retained": os.path.exists(snapshot_path)}
