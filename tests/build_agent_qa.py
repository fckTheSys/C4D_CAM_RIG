"""Reproducible visual fixture; call build() on Cinema 4D's main thread."""
import math
import c4d
from camrig.rig_assemble import build_cam_rig
from camrig.commands import ud_map

def build():
    doc=c4d.documents.BaseDocument()
    doc.SetDocumentName('CamRig Agent QA')
    doc.SetFps(30)
    doc.SetMaxTime(c4d.BaseTime(120,30))
    def shape(kind,name,position,color):
        obj=c4d.BaseObject(kind); obj.SetName(name); obj.SetRelPos(c4d.Vector(*position))
        obj[c4d.ID_BASEOBJECT_USECOLOR]=2; obj[c4d.ID_BASEOBJECT_COLOR]=c4d.Vector(*color)
        doc.InsertObject(obj)
        return obj
    for axis,color in [(0,(1,.1,.1)),(1,(.1,1,.1)),(2,(.1,.3,1))]:
        size=[8,8,8]; size[axis]=600
        pos=[0,0,0]; pos[axis]=300
        beam=shape(c4d.Ocube,'+'+'XYZ'[axis],pos,color)
        beam[c4d.PRIM_CUBE_LEN]=c4d.Vector(*size)
        for distance in (100,200,300,400,500,600):
            pos=[0,0,0]; pos[axis]=distance
            tick=shape(c4d.Osphere,'XYZ'[axis]+' '+str(distance),pos,color)
            tick[c4d.PRIM_SPHERE_RAD]=12
    targets={}
    for name,pos,color in [('Target A',(-200,100,0),(1,.5,0)),('Target B',(200,180,150),(.7,.1,1)),('Orbit Center',(80,40,-60),(.1,1,1)),('Focus Target',(0,140,300),(1,1,.1))]:
        obj=shape(c4d.Osphere,name,pos,color); obj[c4d.PRIM_SPHERE_RAD]=30; targets[name]=obj
    rig=build_cam_rig(doc); rig.SetName('QA Rig')
    ids=ud_map(rig)
    for name,obj in targets.items(): rig[ids[name]]=obj
    parent=shape(c4d.Onull,'Transformed Parent',(900,200,0),(.5,.5,.5))
    parent.SetRelRot(c4d.Vector(math.radians(35),math.radians(15),0))
    second=build_cam_rig(doc); second.SetName('QA Rig 2'); second.InsertUnder(parent)
    camera=shape(c4d.Ocamera,'QA Overview',(1600,1100,-1800),(1,1,1))
    camera.SetRelRot(c4d.utils.VectorToHPB(c4d.Vector(350,150,0)-camera.GetRelPos()))
    doc.GetActiveBaseDraw().SetSceneCamera(camera)
    doc.GetRenderBaseDraw().SetSceneCamera(camera)
    doc.ExecutePasses(None,True,True,True,c4d.BUILDFLAGS_NONE)
    return doc
