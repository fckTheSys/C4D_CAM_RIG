"""Document lifecycle helpers for the public CamRig MCP contract test."""
import c4d
import os
import runpy

MARKER_ID = 105968701


def _objects(node):
    result=[]
    while node:
        result.append({"name":node.GetName(), "type":node.GetType(),
                       "position":[node.GetRelPos().x,node.GetRelPos().y,node.GetRelPos().z]})
        result.extend(_objects(node.GetDown()))
        node=node.GetNext()
    return result


def fingerprint(doc):
    render=doc.GetActiveRenderData().GetData()
    return {"fps":doc.GetFps(), "time":doc.GetTime().Get(),
            "min_time":doc.GetMinTime().Get(), "max_time":doc.GetMaxTime().Get(),
            "objects":_objects(doc.GetFirstObject()),
            "materials":[{"name":m.GetName(),"type":m.GetType()} for m in iter_materials(doc)],
            "render":{"xres":render.GetInt32(c4d.RDATA_XRES),"yres":render.GetInt32(c4d.RDATA_YRES),
                      "engine":render.GetInt32(c4d.RDATA_RENDERENGINE),"sequence":render.GetInt32(c4d.RDATA_FRAMESEQUENCE)}}


def iter_materials(doc):
    material=doc.GetFirstMaterial()
    while material:
        yield material
        material=material.GetNext()


def _registered(document):
    node=c4d.documents.GetFirstDocument()
    while node:
        if node==document: return True
        node=node.GetNext()
    return False


def prepare(snapshot_path, temporary_name, fixture_path, token):
    original=c4d.documents.GetActiveDocument()
    if original is None or not _registered(original):
        raise RuntimeError("active document is not registered; open or save it in Cinema 4D before running the contract harness")
    before=fingerprint(original)
    snapshot=original.GetClone(c4d.COPYFLAGS_0)
    if snapshot is None or not c4d.documents.SaveDocument(snapshot,snapshot_path,c4d.SAVEDOCUMENTFLAGS_0,c4d.FORMAT_C4DEXPORT):
        raise RuntimeError("could not write contract snapshot")
    original.GetDataInstance().SetString(MARKER_ID,token)
    qa=None
    try:
        qa=runpy.run_path(fixture_path)["build"]()
        qa.SetDocumentName(temporary_name)
        c4d.documents.InsertBaseDocument(qa)
        c4d.documents.SetActiveDocument(qa)
    except Exception:
        if qa is not None and qa.GetDocument() is not None: c4d.documents.KillDocument(qa)
        if _registered(original): original.GetDataInstance().RemoveData(MARKER_ID)
        raise
    return {"temporary":temporary_name,"snapshot":snapshot_path,"token":token,"before":before}


def cleanup(snapshot_path, temporary_name, token, before):
    original=None
    temporary=None
    node=c4d.documents.GetFirstDocument()
    while node:
        if node.GetDataInstance().GetString(MARKER_ID)==token: original=node
        if node.GetDocumentName()==temporary_name: temporary=node
        node=node.GetNext()
    if temporary is None: raise RuntimeError("temporary document missing")
    source="original"
    if original is None:
        original=c4d.documents.LoadDocument(snapshot_path,c4d.SCENEFILTER_OBJECTS|c4d.SCENEFILTER_MATERIALS,None)
        if original is None: raise RuntimeError("contract snapshot could not be reopened")
        c4d.documents.InsertBaseDocument(original)
        source="snapshot"
    after=fingerprint(original)
    if after!=before: raise RuntimeError("original document fingerprint changed during contract test")
    c4d.documents.SetActiveDocument(original)
    if original.GetDataInstance().GetString(MARKER_ID)==token: original.GetDataInstance().RemoveData(MARKER_ID)
    c4d.documents.KillDocument(temporary)
    if os.path.exists(snapshot_path): os.remove(snapshot_path)
    return {"restored":c4d.documents.GetActiveDocument()==original,"source":source,"fingerprint_match":True}
