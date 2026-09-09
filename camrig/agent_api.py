"""High-level CamRig operations used by the local MCP proxy."""
import c4d
import os
import math
from . import config
from .agent_schema import CONTROL_SPECS, LINK_KEYS, canonical_controls, validate_controls
from .agent_state import resolve_rig, resolve_object, rig_state, scene_state, rigs, matrix_json
from .commands import ud_map, find_circle, upgrade_rig
from .scene_support import undo_group, add_undo
from .rig_reset import reset_rig_params
from .rig_assemble import build_cam_rig
from .diagnostics import inspect_rig
from .viewport_capture import capture
from .agent_time import time_at

def _preflight(rig):
    from .scene_support import schema_version
    from .commands import runtime_tags, normalized_source
    from .rig_assemble import _build_python_tag_source
    from .rig_objects import get_rig_objects
    circle=find_circle(rig)
    objs=get_rig_objects(circle) if circle else None
    if schema_version(rig)!=3 or objs is None or objs.spring is None or objs.align is None or objs.target_expr is None:
        raise ValueError('STRUCTURE_UNSUPPORTED: schema 3 and complete hierarchy required')
    tags=runtime_tags(circle)
    expected=normalized_source(_build_python_tag_source())
    if len(tags)!=3 or {t.GetDataInstance().GetContainer(config.META_ID).GetInt32(10) for t in tags}!={1,2,3} or any(normalized_source(t[c4d.TPYTHON_CODE])!=expected for t in tags):
        raise ValueError('STRUCTURE_UNSUPPORTED: unknown runtime or missing stage')

def _response(doc, rig=None, changes=None, warnings=None, errors=None):
    return {"ok":not errors,"scene":{"document":doc.GetDocumentName(),"current_frame":doc.GetTime().Get()*doc.GetFps()},
            "rig":rig_state(doc,rig,["controls","targets","camera","spring","diagnostics"]) if rig else None,
            "changes":changes or [],"state":scene_state(doc) if rig is None else {},"warnings":warnings or [],"errors":errors or []}

def get_state(doc, rig, include=None):
    selected=resolve_rig(doc,rig)
    result=_response(doc,selected)
    result["state"]=rig_state(doc,selected,include)
    return result

def set_controls(doc, rig_ref, controls, keyframe=False, evaluate=True):
    controls=validate_controls(controls); rig=resolve_rig(doc,rig_ref); ids=ud_map(rig); missing=[k for k in controls if CONTROL_SPECS[k][0] not in ids]
    if missing: raise ValueError("STRUCTURE_UNSUPPORTED: missing " + ",".join(missing))
    _preflight(rig)
    warnings=[]
    if not keyframe:
        warnings=["Animated control %s: evaluation can restore the value from its track." % key
                  for key in controls if rig.FindCTrack(ids[CONTROL_SPECS[key][0]]) is not None]
    changes=[]
    with undo_group(doc):
        add_undo(doc,c4d.UNDOTYPE_CHANGE,rig)
        for key,value in controls.items():
            desc=ids[CONTROL_SPECS[key][0]]; before=rig[desc]; rig[desc]=value
            changes.append({"key":key,"before":before,"after":value})
            if keyframe: _write_key(doc, rig, desc, doc.GetTime(), value, "step" if isinstance(value, bool) or key == "focus_mode" else "linear")
    if evaluate: doc.ExecutePasses(None,True,True,True,c4d.BUILDFLAGS_INTERNALRENDERER)
    return _response(doc,rig,changes,warnings=warnings)

def set_targets(doc, rig_ref, targets):
    rig=resolve_rig(doc,rig_ref); ids=ud_map(rig); resolved={}
    _preflight(rig)
    from .rig_objects import get_rig_objects
    objs=get_rig_objects(find_circle(rig))
    for key,path in targets.items():
        if key not in LINK_KEYS: raise KeyError(key)
        obj=resolve_object(doc,path) if path else None
        if path and obj is None: raise LookupError("INVALID_TARGET: " + path)
        if LINK_KEYS[key] not in ids: raise ValueError('STRUCTURE_UNSUPPORTED: missing '+key)
        if obj is not None and obj not in (objs.target_a,objs.target_b) and _is_desc(obj,rig): raise ValueError("INVALID_TARGET: target depends on controlled rig")
        resolved[key]=obj
    with undo_group(doc):
        add_undo(doc,c4d.UNDOTYPE_CHANGE,rig)
        for key,obj in resolved.items(): rig[ids[LINK_KEYS[key]]]=obj
    return _response(doc,rig)

def _is_desc(obj, root):
    cursor=obj
    while cursor is not None:
        if cursor == root: return True
        cursor=cursor.GetUp()
    return False

def set_time(doc, frame=None, seconds=None):
    if (frame is None) == (seconds is None): raise ValueError("INVALID_TIME: provide exactly one of frame or seconds")
    t=time_at(seconds) if seconds is not None else time_at(frame,doc.GetFps())
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
    _preflight(rig)
    if not isinstance(transform,dict) or set(transform)-{"position","rotation_deg","scale","confirm"}: raise ValueError("INVALID_TRANSFORM")
    for field in ("position", "rotation_deg", "scale"):
        if field not in transform: continue
        values=transform[field]
        if not isinstance(values,dict) or set(values)-{"x","y","z"}:
            raise ValueError("INVALID_TRANSFORM: %s must contain only x/y/z" % field)
        for value in values.values():
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
                raise ValueError("INVALID_TRANSFORM: %s requires finite numbers" % field)
    if "scale" in transform:
        if transform.get("confirm") is not True: raise ValueError("CONFIRMATION_REQUIRED: root scale requires confirm=true")
        s=transform["scale"]
        if not isinstance(s,dict) or any(not isinstance(s.get(k),(int,float)) or s[k] <= 0 for k in ("x","y","z")):
            raise ValueError("INVALID_TRANSFORM: scale must be positive")
        node=rig
        while node is not None:
            if (node.GetFrozenPos().GetLength()>1e-10 or node.GetFrozenRot().GetLength()>1e-10 or
                    (node.GetFrozenScale()-c4d.Vector(1)).GetLength()>1e-10):
                raise ValueError("STRUCTURE_UNSUPPORTED: frozen transforms on "+node.GetName())
            if any(track.GetDescriptionID()[0].id==c4d.ID_BASEOBJECT_REL_SCALE for track in node.GetCTracks()):
                raise ValueError("STRUCTURE_UNSUPPORTED: animated scale on "+node.GetName())
            node=node.GetUp()
    with undo_group(doc):
        add_undo(doc,c4d.UNDOTYPE_CHANGE,rig)
        if "position" in transform:
            v=transform["position"]; old=rig.GetRelPos(); rig.SetRelPos(c4d.Vector(v.get("x",old.x),v.get("y",old.y),v.get("z",old.z)))
        if "rotation_deg" in transform:
            v=transform["rotation_deg"]; old=rig.GetRelRot(); rig.SetRelRot(c4d.Vector(math.radians(v.get("x",math.degrees(old.x))),math.radians(v.get("y",math.degrees(old.y))),math.radians(v.get("z",math.degrees(old.z)))))
        if "scale" in transform:
            v=transform["scale"]; rig.SetRelScale(c4d.Vector(v["x"],v["y"],v["z"]))
    return _response(doc,rig)

def _write_key(doc, rig, desc, time, value, interpolation):
    interpolation_map={"linear":c4d.CINTERPOLATION_LINEAR,"spline":c4d.CINTERPOLATION_SPLINE,"step":c4d.CINTERPOLATION_STEP}
    track=rig.FindCTrack(desc)
    if track is None:
        track=c4d.CTrack(rig,desc); rig.InsertTrackSorted(track)
        add_undo(doc,c4d.UNDOTYPE_NEWOBJ,track)
    else: add_undo(doc,c4d.UNDOTYPE_CHANGE,track)
    curve=track.GetCurve(); found=None
    for i in range(curve.GetKeyCount()):
        if abs(curve.GetKey(i).GetTime().Get()-time.Get()) < 1e-10: found=curve.GetKey(i); break
    key=found if found is not None else curve.AddKey(time)["key"]
    key.SetValue(curve,value); key.SetInterpolation(curve,interpolation_map[interpolation])

def set_keyframes(doc, rig_ref, tracks, interpolation="linear", replace_existing=False, confirm=False):
    if replace_existing and not confirm: raise ValueError("CONFIRMATION_REQUIRED: replace_existing requires confirm=true")
    if interpolation not in ("linear","spline","step"): raise ValueError("INVALID_ANIMATION: interpolation")
    rig=resolve_rig(doc,rig_ref); ids=ud_map(rig); fps=doc.GetFps(); tracks=canonical_controls(tracks)
    _preflight(rig)
    validated=[]
    for key,items in tracks.items():
        if key not in CONTROL_SPECS or CONTROL_SPECS[key][0] not in ids or not isinstance(items,list): raise ValueError("INVALID_CONTROL: "+key)
        for item in items:
            if not isinstance(item,dict) or not isinstance(item.get("frame"),(int,float)) or not isinstance(item.get("value"),(int,float)):
                raise ValueError("INVALID_ANIMATION: %s" % key)
            validate_controls({key:item['value']})
            validated.append((key,time_at(item['frame'],fps),item['value']))
    with undo_group(doc):
        add_undo(doc,c4d.UNDOTYPE_CHANGE,rig)
        if replace_existing:
            for key in tracks:
                track=rig.FindCTrack(ids[CONTROL_SPECS[key][0]])
                if track:
                    add_undo(doc,c4d.UNDOTYPE_CHANGE,track)
                    track.GetCurve().FlushKeys()
        for key,time,value in validated:
            mode="step" if key in ("shake_enable","use_target","free_camera","focus_mode") else interpolation
            _write_key(doc,rig,ids[CONTROL_SPECS[key][0]],time,value,mode)
    return _response(doc,rig)

def duplicate(doc, rig_ref, name=None):
    source=resolve_rig(doc,rig_ref)
    _preflight(source)
    alias=c4d.AliasTrans(); clone=source.GetClone(c4d.COPYFLAGS_NONE,alias)
    if clone is None: raise RuntimeError("Could not clone CamRig")
    clone.SetName(name or source.GetName()+"_Copy")
    with undo_group(doc):
        doc.InsertObject(clone); alias.Translate(True); add_undo(doc,c4d.UNDOTYPE_NEWOBJ,clone)
        source_objs=__import__('camrig.rig_objects',fromlist=['get_rig_objects']).get_rig_objects(find_circle(source))
        clone_objs=__import__('camrig.rig_objects',fromlist=['get_rig_objects']).get_rig_objects(find_circle(clone))
        if source_objs is None or clone_objs is None or clone_objs.align is None or clone_objs.target_expr is None:
            raise ValueError("STRUCTURE_UNSUPPORTED: duplicate hierarchy")
        for node in (clone_objs.align,clone_objs.target_expr,clone): add_undo(doc,c4d.UNDOTYPE_CHANGE,node)
        clone_objs.align[c4d.ALIGNTOSPLINETAG_LINK]=clone_objs.circle
        clone_objs.target_expr[c4d.TARGETEXPRESSIONTAG_LINK]=clone_objs.look_target
        mapping={source_objs.target_a:clone_objs.target_a,source_objs.target_b:clone_objs.target_b,
                 source_objs.look_target:clone_objs.look_target,source_objs.circle:clone_objs.circle,
                 source_objs.cam:clone_objs.cam,source_objs.fx:clone_objs.fx}
        source_ids,clone_ids=ud_map(source),ud_map(clone)
        for name in LINK_KEYS.values():
            if name in source_ids and name in clone_ids and source[source_ids[name]] in mapping:
                clone[clone_ids[name]]=mapping[source[source_ids[name]]]
    return _response(doc,clone)

def save_scene(doc, path, confirm=False):
    if not isinstance(path,str) or not os.path.isabs(path) or os.path.splitext(path)[1].lower()!='.c4d':
        raise ValueError("INVALID_PATH: an absolute .c4d path is required")
    path=os.path.normpath(path)
    if not os.path.isdir(os.path.dirname(path)): raise ValueError("INVALID_PATH: parent directory does not exist")
    if os.path.exists(path) and confirm is not True: raise ValueError("CONFIRMATION_REQUIRED: overwrite requires confirm=true")
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
            t=time_at(frame,fps); doc.SetTime(t); doc.ExecutePasses(None,True,True,True,c4d.BUILDFLAGS_INTERNALRENDERER)
            try:
                focal=float(objs.fx[c4d.CAMERA_FOCUS])
                focus=float(objs.fx[c4d.CAMERAOBJECT_TARGETDISTANCE])
                if not math.isfinite(focal) or not math.isfinite(focus): raise ValueError('non-finite camera value')
            except (TypeError, ValueError, KeyError) as error:
                raise ValueError('STRUCTURE_UNSUPPORTED: actual FX camera focal/focus parameter unavailable') from error
            row={"frame":frame,"camera":matrix_json(objs.cam.GetMg()),"fx_camera":matrix_json(objs.fx.GetMg()),
                 "focal_length":focal,"focus_distance":focus}
            if objs.spring: row["spring_offset_local"]=matrix_json(objs.spring.GetMl())
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
    for rig in selected: _preflight(rig)
    if any(r == earlier for i,r in enumerate(selected) for earlier in selected[:i]): raise ValueError("INVALID_BATCH: duplicate rig")
    action=payload.get("action","set_controls")
    if action not in ("set_controls","reset"): raise ValueError("INVALID_BATCH: action")
    if action == "set_controls": payload["controls"] = validate_controls(payload.get("controls",{}))
    if action == 'set_controls':
        for rig in selected:
            ids=ud_map(rig)
            missing=[key for key in payload['controls'] if CONTROL_SPECS[key][0] not in ids]
            if missing: raise ValueError('STRUCTURE_UNSUPPORTED: missing '+','.join(missing))
    if action == "reset" and payload.get("group","all") != "all" and payload.get("group") not in config.RESET_GROUP_KEYS:
        raise ValueError("INVALID_RESET_GROUP")
    if dry: return {"ok":True,"scene":{"document":doc.GetDocumentName()},"rig":None,"changes":[],"state":{"batch":{"action":action,"rigs":[rig_state(doc,r,["controls"]) for r in selected],"dry_run":True}},"warnings":[],"errors":[]}
    if not confirm: raise ValueError("CONFIRMATION_REQUIRED: batch requires confirm=true")
    with undo_group(doc):
        for rig in selected:
            add_undo(doc,c4d.UNDOTYPE_CHANGE,rig)
            if action=="set_controls":
                values=payload.get("controls",{}); ids=ud_map(rig)
                for key,value in values.items(): rig[ids[CONTROL_SPECS[key][0]]]=value
            elif action=="reset": reset_rig_params(rig,list(config.RESET_GROUP_KEYS) if payload.get("group","all")=="all" else [payload.get("group")])
            else: raise ValueError("Unsupported batch action: "+action)
    return {"ok":True,"scene":{"document":doc.GetDocumentName()},"rig":None,"changes":[],"state":{"batch":{"action":action,"rigs":[rig_state(doc,r) for r in selected]}},"warnings":[],"errors":[]}

def capture_viewport(doc, payload):
    rig=resolve_rig(doc,payload["rig"])
    result=capture(doc,payload['rig'],payload["path"],payload.get("frame"),payload.get("width",1280),payload.get("height",720),payload.get("camera","fx"),payload.get("confirm",False))
    response=_response(doc,rig); response["state"]={"capture":result}; return response

def reset(doc, rig_ref, group="all"):
    rig=resolve_rig(doc,rig_ref)
    _preflight(rig)
    if group != "all" and (not isinstance(group,str) or group not in config.RESET_GROUP_KEYS): raise ValueError("INVALID_RESET_GROUP")
    groups=list(config.RESET_GROUP_KEYS) if group=="all" else ([group] if isinstance(group,str) else list(group))
    with undo_group(doc): add_undo(doc,c4d.UNDOTYPE_CHANGE,rig); reset_rig_params(rig,groups)
    return _response(doc,rig)

def _error_code(exc):
    text=str(exc)
    for code in ("RIG_NOT_FOUND","AMBIGUOUS_RIG","AMBIGUOUS_TARGET","INVALID_TARGET","INVALID_CONTROL","INVALID_ANIMATION","INVALID_TIME","INVALID_TRANSFORM","INVALID_PATH","INVALID_BATCH","INVALID_RESET_GROUP","STRUCTURE_UNSUPPORTED","CONFIRMATION_REQUIRED"):
        if code in text: return code
    return "INTERNAL_ERROR"

def dispatch(doc, action, payload):
    try: return _dispatch(doc,action,payload)
    except Exception as exc:
        return _response(doc,errors=[{"code":_error_code(exc),"message":str(exc)}])

def _dispatch(doc, action, payload):
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
        upgrade_rig(doc,rig)
        return _response(doc,rig)
    if action=="undo":
        if not doc.DoUndo(): raise RuntimeError("UNDO_FAILED")
        return _response(doc)
    if action=="redo":
        if not doc.DoRedo(): raise RuntimeError("REDO_FAILED")
        return _response(doc)
    if action=="create":
        with undo_group(doc): rig=build_cam_rig(doc,record_undo=True); rig.SetName(payload.get("name",rig.GetName()))
        return _response(doc,rig)
    if action=="duplicate": return duplicate(doc,payload["rig"],payload.get("name"))
    if action=="save_scene": return save_scene(doc,payload.get("path"),payload.get("confirm",False))
    if action=="bake_camera": return bake_camera(doc,payload["rig"],payload.get("confirm",False))
    if action=="batch": return batch(doc,payload)
    if action=="capture_viewport": return capture_viewport(doc,payload)
    raise ValueError("Unsupported action: " + action)
