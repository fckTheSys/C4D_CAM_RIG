"""JSON-safe scene and rig state for the CamRig Agent facade."""
import c4d
from . import config
from .commands import walk, is_rig, find_circle, ud_map
from .rig_objects import get_rig_objects
from .scene_support import schema_version
from .agent_schema import CONTROL_SPECS, LINK_KEYS

def _path(obj):
    parts=[]
    while obj is not None:
        parts.append(obj.GetName()); obj=obj.GetUp()
    return "/" + "/".join(reversed(parts))

def _json(value):
    if isinstance(value, c4d.Vector): return {"x": value.x, "y": value.y, "z": value.z}
    if isinstance(value, c4d.BaseList2D): return _path(value)
    if isinstance(value, (str, int, float, bool)) or value is None: return value
    return str(value)

def matrix_json(matrix):
    return {"off":_json(matrix.off),"v1":_json(matrix.v1),"v2":_json(matrix.v2),"v3":_json(matrix.v3)}

def rigs(doc):
    return [o for o in walk(doc.GetFirstObject()) if is_rig(o)]

def resolve_rig(doc, ref):
    found=[]
    for rig in rigs(doc):
        if not ref or rig.GetName()==ref or _path(rig)==ref: found.append(rig)
    if not found: raise LookupError("RIG_NOT_FOUND: " + str(ref))
    if len(found)>1: raise LookupError("AMBIGUOUS_RIG: " + str(ref))
    return found[0]

def resolve_object(doc, ref):
    """Resolve an absolute hierarchy path, falling back to a unique name."""
    candidates=[]
    for obj in walk(doc.GetFirstObject()):
        if _path(obj)==ref or obj.GetName()==ref: candidates.append(obj)
    if not candidates: raise LookupError("INVALID_TARGET: " + str(ref))
    if len(candidates)>1: raise LookupError("AMBIGUOUS_TARGET: " + str(ref))
    return candidates[0]

def _tag_state(node):
    out=[]
    if node:
        for tag in node.GetTags():
            if tag.CheckType(c4d.Tpython):
                meta=tag.GetDataInstance().GetContainer(config.META_ID)
                out.append({"name":tag.GetName(),"role":meta.GetInt32(10),"priority":tag[c4d.EXPRESSION_PRIORITY]})
    return out

def rig_state(doc, rig, include=None):
    include=set(include or ["controls","targets","camera","spring","diagnostics"]); ids=ud_map(rig)
    state={"path":_path(rig),"schema":schema_version(rig),"runtime":config.PLUGIN_VERSION}
    if "controls" in include:
        state["controls"]={k:_json(rig[ids[name]]) for k,(name,_,_) in CONTROL_SPECS.items() if name in ids}
    if "targets" in include:
        state["targets"]={k:_json(rig[ids[n]]) for k,n in LINK_KEYS.items() if n in ids}
    circle=find_circle(rig); objs=get_rig_objects(circle) if circle else None
    state["objects"]={k:_path(v) for k,v in {"root":rig,"circle":circle,"camera":getattr(objs,"cam",None),"fx_camera":getattr(objs,"fx",None),"target_a":getattr(objs,"target_a",None),"target_b":getattr(objs,"target_b",None)}.items() if v}
    state["stages"]=_tag_state(circle)
    return state

def scene_state(doc):
    current=doc.GetTime().GetFrame(doc.GetFps())
    return {"document":doc.GetDocumentName(),"path":doc.GetDocumentPath(),"fps":doc.GetFps(),
            "current_frame":current,"min_frame":doc.GetMinTime().GetFrame(doc.GetFps()),
            "max_frame":doc.GetMaxTime().GetFrame(doc.GetFps()),"rigs":[rig_state(doc,r,["controls","diagnostics"]) for r in rigs(doc)]}
