"""High-level CamRig operations used by the local MCP proxy."""
import c4d
from . import config
from .agent_schema import CONTROL_SPECS, LINK_KEYS, validate_controls
from .agent_state import resolve_rig, rig_state, scene_state, rigs
from .commands import ud_map, find_circle, upgrade_rig
from .scene_support import undo_group, add_undo
from .rig_reset import reset_rig_params
from .rig_assemble import build_cam_rig

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
        obj=doc.SearchObject(path.strip("/").split("/")[-1]) if path else None
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
    if action=="set_time": return set_time(doc,payload.get("frame"),payload.get("seconds"))
    if action=="reset": return reset(doc,payload["rig"],payload.get("group","all"))
    if action=="upgrade":
        rig=resolve_rig(doc,payload["rig"])
        with undo_group(doc): upgrade_rig(doc,rig)
        return _response(doc,rig)
    raise ValueError("Unsupported action: " + action)
