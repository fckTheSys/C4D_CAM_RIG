"""Viewport capture for CamRig QA, independent of ComfyUI/Lesta."""
from pathlib import Path
import c4d
from .agent_state import resolve_rig
from .commands import find_circle
from .rig_objects import get_rig_objects

def capture(doc, rig_ref, path, frame=None, width=1280, height=720, camera="fx", confirm=False):
    if not isinstance(width,int) or not isinstance(height,int) or not 1 <= width <= 8192 or not 1 <= height <= 8192:
        raise ValueError("INVALID_CAPTURE: width and height must be 1..8192")
    if not isinstance(path,str) or not path.lower().endswith(".png") or not Path(path).is_absolute():
        raise ValueError("INVALID_CAPTURE: path must be an absolute PNG path")
    target=Path(path)
    if target.exists() and not confirm: raise ValueError("CONFIRMATION_REQUIRED: PNG overwrite requires confirm=true")
    rig=resolve_rig(doc,rig_ref); objs=get_rig_objects(find_circle(rig))
    if objs is None or objs.fx is None: raise ValueError("STRUCTURE_UNSUPPORTED: FX camera missing")
    active=doc.GetActiveBaseDraw(); render=doc.GetRenderBaseDraw()
    if active is None or render is None: raise RuntimeError("No Cinema 4D viewport")
    original_time=doc.GetTime(); old_active=active.GetSceneCamera(doc); old_render=render.GetSceneCamera(doc)
    selected=objs.fx if camera=="fx" else old_active if camera=="active" else None
    if selected is None: raise ValueError("INVALID_CAPTURE: camera must be fx or active")
    if frame is not None:
        doc.SetTime(c4d.BaseTime(float(frame),doc.GetFps()))
        doc.ExecutePasses(None,True,True,True,c4d.BUILDFLAGS_INTERNALRENDERER)
    active.SetSceneCamera(selected); render.SetSceneCamera(selected)
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
        target.parent.mkdir(parents=True,exist_ok=True)
        if bmp.Save(str(target),c4d.FILTER_PNG)!=c4d.IMAGERESULT_OK: raise RuntimeError("PNG save failed")
        check=c4d.bitmaps.BaseBitmap(); result=check.InitWith(str(target))
        result=result[0] if isinstance(result,tuple) else result
        if result!=c4d.IMAGERESULT_OK or check.GetBw()!=width or check.GetBh()!=height: raise RuntimeError("PNG verification failed")
    finally:
        active.SetSceneCamera(old_active); render.SetSceneCamera(old_render); doc.SetTime(original_time)
        doc.ExecutePasses(None,True,True,True,c4d.BUILDFLAGS_INTERNALRENDERER)
    return {"path":str(target),"width":int(width),"height":int(height),"frame":frame,"camera":selected.GetName()}
