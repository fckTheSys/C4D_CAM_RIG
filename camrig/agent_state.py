"""JSON-safe scene and rig state for the CamRig Agent facade."""
import c4d
import ast
from urllib.parse import quote
from . import config
from .commands import walk, is_rig, find_circle, ud_map
from .rig_objects import get_rig_objects
from .scene_support import schema_version
from .agent_schema import CONTROL_SPECS, LINK_KEYS

def _path(obj):
    parts=[]
    while obj is not None:
        parent=obj.GetUp()
        first=parent.GetDown() if parent else obj.GetDocument().GetFirstObject()
        matches=[]
        while first is not None:
            if first.GetName()==obj.GetName(): matches.append(first)
            first=first.GetNext()
        segment=quote(obj.GetName(),safe=' _-.')
        if len(matches)>1: segment+='[%d]' % (next(i for i,node in enumerate(matches) if node==obj)+1)
        parts.append(segment); obj=parent
    return "/" + "/".join(reversed(parts))

def runtime_version(rig):
    circle=find_circle(rig)
    versions=[]
    for tag in circle.GetTags() if circle else []:
        if not tag.CheckType(c4d.Tpython): continue
        version=None
        try:
            for node in ast.parse(tag[c4d.TPYTHON_CODE]).body:
                if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='EMBEDDED_RUNTIME_VERSION' for t in node.targets):
                    version=ast.literal_eval(node.value)
        except (ValueError,SyntaxError,TypeError): pass
        versions.append(version)
    return versions[0] if versions and isinstance(versions[0],str) and all(v==versions[0] for v in versions) else None

def _priority_value(priority):
    try: return int(priority.GetPriorityValue(c4d.PRIORITYVALUE_PRIORITY))
    except Exception: return None

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
                out.append({"name":tag.GetName(),"role":meta.GetInt32(10),"priority":_priority_value(tag[c4d.EXPRESSION_PRIORITY])})
    return out

def rig_state(doc, rig, include=None):
    include=set(include or ["controls","targets","camera","spring","diagnostics"]); ids=ud_map(rig)
    state={"path":_path(rig),"schema":schema_version(rig),"runtime":runtime_version(rig)}
    if "controls" in include:
        state["controls"]={k:_json(rig[ids[name]]) for k,(name,_,_) in CONTROL_SPECS.items() if name in ids}
    if "targets" in include:
        state["targets"]={k:_json(rig[ids[n]]) for k,n in LINK_KEYS.items() if n in ids}
    circle=find_circle(rig); objs=get_rig_objects(circle) if circle else None
    state["objects"]={k:_path(v) for k,v in {"root":rig,"circle":circle,"camera":getattr(objs,"cam",None),"fx_camera":getattr(objs,"fx",None),"target_a":getattr(objs,"target_a",None),"target_b":getattr(objs,"target_b",None)}.items() if v}
    state["stages"]=_tag_state(circle)
    return state

def scene_state(doc):
    current=doc.GetTime().Get()*doc.GetFps()
    return {"document":doc.GetDocumentName(),"path":doc.GetDocumentPath(),"fps":doc.GetFps(),
            "current_frame":current,"min_frame":doc.GetMinTime().GetFrame(doc.GetFps()),
            "max_frame":doc.GetMaxTime().GetFrame(doc.GetFps()),"rigs":[rig_state(doc,r,["controls","diagnostics"]) for r in rigs(doc)]}
