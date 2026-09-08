"""High-level CamRig operations used by the local MCP proxy."""
import c4d
import os
from . import config
from .agent_schema import CONTROL_SPECS, LINK_KEYS, validate_controls
from .agent_state import resolve_rig, resolve_object, rig_state, scene_state, rigs, matrix_json
from .commands import ud_map, find_circle, upgrade_rig
from .scene_support import undo_group, add_undo
from .rig_reset import reset_rig_params
from .rig_assemble import build_cam_rig
from .diagnostics import inspect_rig

def _response(doc, rig=None, changes=None, warnings=None, errors=None):
    return {"ok":not errors,"scene":{"document":doc.GetDocumentName(),"current_frame":doc.GetTime().GetFrame(doc.GetFps())},
            "rig":rig_state(doc,rig,["controls","targets","camera","spring","diagnostics"]) if rig else None,
            "changes":changes or [],"state":scene_state(doc) if rig is None else {},"warnings":warnings or [],"errors":errors or []}

def get_state(doc, rig, include=None):
    selected=resolve_rig(doc,rig)
    result=_response(doc,selected)
    result["state"]=rig_state(doc,selected,include)
    return result

def set_controls(doc, rig_ref, controls, keyframe=False, evaluate=True):
    validate_controls(controls); rig=resolve_rig(doc,rig_ref); ids=ud_map(rig); missing=[k for k in controls if CONTROL_SPECS[k][0] not in ids]
    if missing: raise ValueError("STRUCTURE_UNSUPPORTED: missing " + ",".join(missing))
    changes=[]
    with undo_group(doc):
        add_undo(doc,c4d.UNDOTYPE_CHANGE,rig)
        for key,value in controls.items():
            desc=ids[CONTROL_SPECS[key][0]]; before=rig[desc]; rig[desc]=value
            changes.append({"key":key,"before":before,"after":value})
            if keyframe:
                track=rig.FindCTrack(desc)
                if track is None: track=c4d.CTrack(rig,desc); rig.InsertTrackSorted(track)
                kd=track.GetCurve().AddKey(doc.GetTime()); kd["key"].SetValue(track.GetCurve(),value)
    if evaluate: doc.ExecutePasses(None,True,True,True,c4d.BUILDFLAGS_INTERNALRENDERER)
    return _response(doc,rig,changes)

def set_targets(doc, rig_ref, targets):
    rig=resolve_rig(doc,rig_ref); ids=ud_map(rig); resolved={}
    for key,path in targets.items():
        if key not in LINK_KEYS: raise KeyError(key)
        obj=resolve_object(doc,path) if path else None
        if path and obj is None: raise LookupError("INVALID_TARGET: " + path)
        if obj is rig or (obj and (obj.GetUp() is rig or obj.GetUp() is not None and _is_desc(obj,rig))): raise ValueError("INVALID_TARGET: target is inside rig")
        resolved[key]=obj
    with undo_group(doc):
        add_undo(doc,c4d.UNDOTYPE_CHANGE,rig)
        for key,obj in resolved.items(): rig[ids[LINK_KEYS[key]]]=obj
    return _response(doc,rig)

def _is_desc(obj, root):
    cursor=obj
    while cursor is not None:
        if cursor is root: return True
        cursor=cursor.GetUp()
    return False

def set_time(doc, frame=None, seconds=None):
    t=c4d.BaseTime(float(seconds),1) if seconds is not None else c4d.BaseTime(int(frame),doc.GetFps())
    doc.SetTime(t); doc.ExecutePasses(None,True,True,True,c4d.BUILDFLAGS_INTERNALRENDERER); return _response(doc)

def set_camera_mode(doc, rig_ref, values):
    allowed={"use_target":config.UD_USE_TARGET,"target_blend":config.UD_TARGET_BLEND,
              "free_camera":config.UD_FREE_CAMERA,"focus_mode":config.UD_FOCUS_MODE,
              "focus_offset":config.UD_FOCUS_OFFSET,"focal_length":config.UD_FOCAL}
    unknown=set(values)-set(allowed)
    if unknown: raise KeyError(next(iter(unknown)))
    return set_controls(doc,rig_ref,values)

def set_root_transform(doc, rig_ref, transform):
    rig=resolve_rig(doc,rig_ref)
    if "scale" in transform and transform["scale"] != {"x":1,"y":1,"z":1}:
        raise ValueError("CONFIRMATION_REQUIRED: root scale changes require explicit confirmation")
    with undo_group(doc):
        add_undo(doc,c4d.UNDOTYPE_CHANGE,rig)
        if "position" in transform:
            v=transform["position"]; rig.SetRelPos(c4d.Vector(v.get("x",0),v.get("y",0),v.get("z",0)))
        if "rotation_deg" in transform:
            import math
            v=transform["rotation_deg"]; rig.SetRelRot(c4d.Vector(math.radians(v.get("x",0)),math.radians(v.get("y",0)),math.radians(v.get("z",0))))
    return _response(doc,rig)

def set_keyframes(doc, rig_ref, tracks, interpolation="linear", replace_existing=False, confirm=False):
    if replace_existing and not confirm: raise ValueError("CONFIRMATION_REQUIRED: replace_existing requires confirm=true")
    rig=resolve_rig(doc,rig_ref); ids=ud_map(rig); fps=doc.GetFps()
    with undo_group(doc):
        add_undo(doc,c4d.UNDOTYPE_CHANGE,rig)
        for key,items in tracks.items():
            if key not in CONTROL_SPECS or CONTROL_SPECS[key][0] not in ids: raise ValueError("INVALID_CONTROL: "+key)
            desc=ids[CONTROL_SPECS[key][0]]; track=rig.FindCTrack(desc)
            if track is None: track=c4d.CTrack(rig,desc); rig.InsertTrackSorted(track)
            curve=track.GetCurve()
            for item in items:
                time=c4d.BaseTime(float(item["frame"]),fps); kd=curve.AddKey(time)
                if kd: kd["key"].SetValue(curve,item["value"])
    return _response(doc,rig)

def duplicate(doc, rig_ref, name=None):
    source=resolve_rig(doc,rig_ref)
    clone=source.GetClone(c4d.COPYFLAGS_NONE)
    if clone is None: raise RuntimeError("Could not clone CamRig")
    clone.SetName(name or source.GetName()+"_Copy")
    with undo_group(doc):
        doc.InsertObject(clone); add_undo(doc,c4d.UNDOTYPE_NEWOBJ,clone)
    return _response(doc,clone)

def save_scene(doc, path, confirm=False):
    if not path: raise ValueError("path is required")
    path=os.path.abspath(path)
    if os.path.exists(path) and not confirm: raise ValueError("CONFIRMATION_REQUIRED: overwrite requires confirm=true")
    result=c4d.documents.SaveDocument(doc,path,c4d.SAVEDOCUMENTFLAGS_0,c4d.FORMAT_C4DEXPORT)
    if not result: raise RuntimeError("Could not save Cinema 4D document")
    return _response(doc)

def diagnostics(doc, rig_ref):
    rig=resolve_rig(doc,rig_ref); ok,message=inspect_rig(doc,rig)
    result=_response(doc,rig)
    result["state"]={"inspector":{"ok":ok,"message":message}}
    if not ok: result["warnings"].append(message)
    return result

def sample(doc, rig_ref, frames):
    rig=resolve_rig(doc,rig_ref); circle=find_circle(rig); objs=__import__('camrig.rig_objects',fromlist=['get_rig_objects']).get_rig_objects(circle)
    if objs is None: raise ValueError("STRUCTURE_UNSUPPORTED: incomplete rig")
    original=doc.GetTime(); rows=[]; fps=doc.GetFps()
    try:
        for frame in frames:
            t=c4d.BaseTime(float(frame),fps); doc.SetTime(t); doc.ExecutePasses(None,True,True,True,c4d.BUILDFLAGS_INTERNALRENDERER)
            row={"frame":frame,"camera":matrix_json(objs.cam.GetMg()),"fx_camera":matrix_json(objs.fx.GetMg()),"focal_length":float(rig[ud_map(rig)[config.UD_FOCAL]])}
            if objs.spring: row["spring_offset"]=matrix_json(objs.spring.GetMg())
            rows.append(row)
    finally:
        doc.SetTime(original); doc.ExecutePasses(None,True,True,True,c4d.BUILDFLAGS_INTERNALRENDERER)
    result=_response(doc,rig); result["state"]={"samples":rows}; return result

def bake_camera(doc, rig_ref, confirm=False):
    rig=resolve_rig(doc,rig_ref); minimum=doc.GetMinTime().GetFrame(doc.GetFps()); maximum=doc.GetMaxTime().GetFrame(doc.GetFps())
    plan={"dry_run":not confirm,"frame_range":[minimum,maximum],"camera":rig_state(doc,rig,["camera"]).get("objects",{}).get("fx_camera"),"risk":"Procedural tags and Spring would be replaced by baked keys."}
    if not confirm: result=_response(doc,rig); result["state"]={"bake":plan}; return result
    raise ValueError("CONFIRMATION_REQUIRED: actual bake is not enabled until the verified bake command is selected")

def batch(doc, payload):
    refs=payload.get("rigs",[]); dry=payload.get("dry_run",True); confirm=payload.get("confirm",False)
    if not refs: raise ValueError("rigs must not be empty")
    selected=[resolve_rig(doc,r) for r in refs]
    action=payload.get("action","set_controls")
    if dry: return {"ok":True,"scene":{"document":doc.GetDocumentName()},"rig":None,"changes":[],"state":{"batch":{"action":action,"rigs":[rig_state(doc,r,["controls"]) for r in selected],"dry_run":True}},"warnings":[],"errors":[]}
    if not confirm: raise ValueError("CONFIRMATION_REQUIRED: batch requires confirm=true")
    with undo_group(doc):
        for rig in selected:
            add_undo(doc,c4d.UNDOTYPE_CHANGE,rig)
            if action=="set_controls":
                values=payload.get("controls",{}); validate_controls(values); ids=ud_map(rig)
                for key,value in values.items(): rig[ids[CONTROL_SPECS[key][0]]]=value
            elif action=="reset": reset_rig_params(rig,[payload.get("group","all")])
            else: raise ValueError("Unsupported batch action: "+action)
    return {"ok":True,"scene":{"document":doc.GetDocumentName()},"rig":None,"changes":[],"state":{"batch":{"action":action,"rigs":[rig_state(doc,r) for r in selected]}},"warnings":[],"errors":[]}

def reset(doc, rig_ref, group="all"):
    rig=resolve_rig(doc,rig_ref)
    groups=[group] if isinstance(group,str) else list(group)
    with undo_group(doc): add_undo(doc,c4d.UNDOTYPE_CHANGE,rig); reset_rig_params(rig,groups)
    return _response(doc,rig)

def dispatch(doc, action, payload):
    if action in ("scene_state","list_rigs"): return _response(doc)
    if action=="get_state": return get_state(doc,payload.get("rig"),payload.get("include"))
    if action=="set_controls": return set_controls(doc,payload["rig"],payload.get("controls",{}),payload.get("keyframe",False),payload.get("evaluate",True))
    if action=="set_targets": return set_targets(doc,payload["rig"],payload.get("targets",{}))
    if action=="set_camera_mode": return set_camera_mode(doc,payload["rig"],payload.get("values",{}))
    if action=="set_root_transform": return set_root_transform(doc,payload["rig"],payload.get("transform",{}))
    if action=="set_keyframes": return set_keyframes(doc,payload["rig"],payload.get("tracks",{}),payload.get("interpolation","linear"),payload.get("replace_existing",False),payload.get("confirm",False))
    if action=="set_time": return set_time(doc,payload.get("frame"),payload.get("seconds"))
    if action=="sample": return sample(doc,payload["rig"],payload.get("frames",[]))
    if action=="diagnostics": return diagnostics(doc,payload["rig"])
    if action=="reset": return reset(doc,payload["rig"],payload.get("group","all"))
    if action=="upgrade":
        rig=resolve_rig(doc,payload["rig"])
        with undo_group(doc): upgrade_rig(doc,rig)
        return _response(doc,rig)
    if action=="undo": doc.DoUndo(); return _response(doc)
    if action=="redo": doc.DoRedo(); return _response(doc)
    if action=="create":
        with undo_group(doc): rig=build_cam_rig(doc,record_undo=True); rig.SetName(payload.get("name",rig.GetName()))
        return _response(doc,rig)
    if action=="duplicate": return duplicate(doc,payload["rig"],payload.get("name"))
    if action=="save_scene": return save_scene(doc,payload.get("path"),payload.get("confirm",False))
    if action=="bake_camera": return bake_camera(doc,payload["rig"],payload.get("confirm",False))
    if action=="batch": return batch(doc,payload)
    raise ValueError("Unsupported action: " + action)
