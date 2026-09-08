"""Viewport capture for CamRig QA, independent of ComfyUI/Lesta."""
from pathlib import Path
import c4d
from .agent_state import resolve_rig
from .commands import find_circle
from .rig_objects import get_rig_objects

def capture(doc, rig_ref, path, frame=None, width=1280, height=720):
    rig=resolve_rig(doc,rig_ref); objs=get_rig_objects(find_circle(rig))
    if objs is None or objs.fx is None: raise ValueError("STRUCTURE_UNSUPPORTED: FX camera missing")
    active=doc.GetActiveBaseDraw(); render=doc.GetRenderBaseDraw()
    if active is None or render is None: raise RuntimeError("No Cinema 4D viewport")
    original_time=doc.GetTime(); old_active=active.GetSceneCamera(doc); old_render=render.GetSceneCamera(doc)
    if frame is not None:
        doc.SetTime(c4d.BaseTime(float(frame),doc.GetFps()))
        doc.ExecutePasses(None,True,True,True,c4d.BUILDFLAGS_INTERNALRENDERER)
    active.SetSceneCamera(objs.fx); render.SetSceneCamera(objs.fx)
    settings=c4d.BaseContainer(); settings[c4d.RDATA_XRES]=int(width); settings[c4d.RDATA_YRES]=int(height)
    settings[c4d.RDATA_FILMASPECT]=float(width)/float(height); settings[c4d.RDATA_PIXELASPECT]=1.0
    settings[c4d.RDATA_RENDERENGINE]=c4d.RDATA_RENDERENGINE_PREVIEWHARDWARE
    settings[c4d.RDATA_FRAMESEQUENCE]=c4d.RDATA_FRAMESEQUENCE_CURRENTFRAME
    settings[c4d.RDATA_ALPHACHANNEL]=False
    bmp=c4d.bitmaps.BaseBitmap(); result=bmp.Init(int(width),int(height),24)
    if result!=c4d.IMAGERESULT_OK: raise RuntimeError("Could not allocate capture bitmap")
    try:
        result=c4d.documents.RenderDocument(doc,settings,bmp,c4d.RENDERFLAGS_EXTERNAL|c4d.RENDERFLAGS_OCIO_BAKE_RENDERING)
        if result!=c4d.RENDERRESULT_OK: raise RuntimeError("Viewport render failed: %s" % result)
        target=Path(path); target.parent.mkdir(parents=True,exist_ok=True)
        if bmp.Save(str(target),c4d.FILTER_PNG)!=c4d.IMAGERESULT_OK: raise RuntimeError("PNG save failed")
    finally:
        active.SetSceneCamera(old_active); render.SetSceneCamera(old_render); doc.SetTime(original_time)
        doc.ExecutePasses(None,True,True,True,c4d.BUILDFLAGS_INTERNALRENDERER)
    return {"path":str(target),"width":int(width),"height":int(height),"frame":frame,"camera":objs.fx.GetName()}
