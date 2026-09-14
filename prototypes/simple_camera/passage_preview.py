"""Editable owned demonstration, rendered by C4D viewport without editor activation."""
from pathlib import Path
import json
import runpy
import c4d


def create(output_directory):
    output=Path(output_directory).resolve()
    output.mkdir(parents=True,exist_ok=False)
    b=runpy.run_path(str(Path(__file__).with_name('builder.py')))
    d=c4d.documents.BaseDocument();d.SetFps(30);d.SetMaxTime(c4d.BaseTime(180,30))
    root,obj,ids=b['build'](d)
    b['key'](d,root,ids['Progress'],[(0,0),(20,.02),(85,.4),(105,.4),(125,.55),(160,.85),(180,1)])
    b['key'](d,root,ids['Pan'],[(0,0),(85,0),(95,25),(110,0),(180,0)])
    b['key'](d,root,ids['Body Y'],[(0,0),(125,0),(132,-8),(150,95),(168,0),(172,-5),(180,0)])
    b['key'](d,root,ids['Walk Strength'],[(0,.6),(125,.6),(132,0),(168,0),(180,.6)])
    root[ids['Shake Strength']]=.08;root[ids['Drift Strength']]=.12
    for name in ('Progress','Pan','Body Y','Walk Strength'):
        curve=root.FindCTrack(ids[name]).GetCurve()
        for i in range(curve.GetKeyCount()):
            k=curve.GetKey(i);k.SetInterpolation(curve,c4d.CINTERPOLATION_SPLINE)
            k.ChangeNBit(c4d.NBIT_CKEY_AUTO,c4d.NBITCONTROL_CLEAR)
            if i:k.SetTimeLeft(curve,c4d.BaseTime((curve.GetKey(i-1).GetTime().Get()-k.GetTime().Get())/3))
            if i+1<curve.GetKeyCount():k.SetTimeRight(curve,c4d.BaseTime((curve.GetKey(i+1).GetTime().Get()-k.GetTime().Get())/3))
            k.SetValueLeft(curve,0);k.SetValueRight(curve,0)
    obj[3].SetRelPos(c4d.Vector(0,170,3500))
    def cube(name,size,pos,color):
        node=c4d.BaseObject(c4d.Ocube);node.SetName(name)
        node[c4d.PRIM_CUBE_LEN]=c4d.Vector(*size);node.SetRelPos(c4d.Vector(*pos))
        node[c4d.ID_BASEOBJECT_USECOLOR]=2;node[c4d.ID_BASEOBJECT_COLOR]=c4d.Vector(*color)
        d.InsertObject(node)
    cube('Floor',(900,20,2800),(0,-10,1100),(.25,.28,.32))
    for z in range(0,2600,250):
        for x in (-330,330):
            cube('Column',(35,400,35),(x,200,z),(.48,.52,.58))
        cube('Header',(700,25,35),(0,400,z),(.48,.52,.58))
    cube('Jump marker',(450,40,40),(0,20,920),(.85,.38,.12))
    cube('End marker',(120,180,40),(0,90,2400),(.15,.6,.62))
    d.ForceCreateBaseDraw()
    for bd in (d.GetActiveBaseDraw(),d.GetRenderBaseDraw()):
        if bd:
            bd.SetSceneCamera(obj[9])
            bd[c4d.BASEDRAW_DATA_SDISPLAYACTIVE]=c4d.BASEDRAW_SDISPLAY_FLAT_WIRE
            bd[c4d.BASEDRAW_DATA_SDISPLAYINACTIVE]=c4d.BASEDRAW_SDISPLAY_FLAT_WIRE
    d.SetActiveObject(root,c4d.SELECTION_NEW)
    d.ExecutePasses(None,True,True,True,c4d.BUILDFLAGS_NONE)
    scene=output/'simple_camera_passage.c4d'
    if not c4d.documents.SaveDocument(d,str(scene),c4d.SAVEDOCUMENTFLAGS_DONTADDTORECENTLIST,c4d.FORMAT_C4DEXPORT):
        raise RuntimeError('Scene save failed')
    return {'scene':str(scene),'frames':180,'fps':30}


def render(scene_path,frames):
    scene=Path(scene_path).resolve();output=scene.parent
    d=c4d.documents.LoadDocument(str(scene),c4d.SCENEFILTER_OBJECTS|c4d.SCENEFILTER_MATERIALS,None)
    if d is None:raise RuntimeError('Scene load failed')
    d.ForceCreateBaseDraw()
    root=d.GetFirstObject()
    while root and root.GetDataInstance().GetInt32(10699101)!=1:root=root.GetNext()
    if root is None:raise RuntimeError('Missing rig')
    stack=[root];camera=None
    while stack:
        node=stack.pop();stack.extend(node.GetChildren())
        if node.GetDataInstance().GetInt32(10699101)==9:camera=node
    for bd in (d.GetActiveBaseDraw(),d.GetRenderBaseDraw()):
        if bd:bd.SetSceneCamera(camera)
    rows=[]
    for frame in frames:
        path=output/('frame_%04d.png'%frame)
        if path.exists():raise FileExistsError(str(path))
        d.SetTime(c4d.BaseTime(frame,30));d.ExecutePasses(None,True,True,True,c4d.BUILDFLAGS_NONE)
        errors=[t.GetDataInstance().GetString(10699102) for t in root.GetTags() if t.GetType()==c4d.Tpython]
        if len(errors)!=2 or any(errors):raise RuntimeError(str(errors))
        settings=c4d.documents.RenderData()
        for key,value in ((c4d.RDATA_RENDERENGINE,c4d.RDATA_RENDERENGINE_PREVIEWHARDWARE),
                          (c4d.RDATA_XRES,640.0),(c4d.RDATA_YRES,360.0),(c4d.RDATA_FILMASPECT,640/360),
                          (c4d.RDATA_PIXELASPECT,1.0),(c4d.RDATA_FRAMESEQUENCE,1),
                          (c4d.RDATA_FRAMEFROM,d.GetTime()),(c4d.RDATA_FRAMETO,d.GetTime()),(c4d.RDATA_SAVEIMAGE,False)):
            settings[key]=value
        bitmap=c4d.bitmaps.MultipassBitmap(640,360,c4d.COLORMODE_RGB);bitmap.AddChannel(True,True)
        code=c4d.documents.RenderDocument(d,settings.GetDataInstance(),bitmap,c4d.RENDERFLAGS_EXTERNAL)
        if code!=c4d.RENDERRESULT_OK:raise RuntimeError('Render failed: '+str(code))
        if bitmap.Save(str(path),c4d.FILTER_PNG)!=c4d.IMAGERESULT_OK:raise RuntimeError('PNG save failed')
        rows.append(str(path))
    return rows
