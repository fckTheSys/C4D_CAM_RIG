"""Run on the C4D main thread; owns an isolated, disposable document."""
import c4d
from camrig import agent_api as api, agent_state as state
from camrig.commands import ud_map
from camrig.agent_time import time_at
from camrig.rig_assemble import build_cam_rig

def run():
    doc=c4d.documents.BaseDocument()
    doc.SetFps(30)
    rig=build_cam_rig(doc)
    ref=state._path(rig)
    result=[]
    for mode,expected in [('linear',2),('step',3),('spline',1)]:
        api.set_keyframes(doc,ref,{'orbit':[{'frame':0,'value':-720.0},{'frame':60.5,'value':1080.0}]},mode,True,True)
        rig=state.resolve_rig(doc,ref)
        curve=rig.FindCTrack(ud_map(rig)['Orbit']).GetCurve()
        assert curve.GetKeyCount()==2
        assert abs(curve.GetKey(1).GetTime().Get()*30-60.5)<1e-9
        assert [curve.GetKey(i).GetInterpolation() for i in range(2)]==[expected]*2
        assert [curve.GetKey(i).GetValue() for i in range(2)]==[-720.,1080.]
        if mode=='linear': assert abs(curve.GetValue(time_at(30.25,30),30)-180)<1e-6
        if mode=='step': assert curve.GetValue(time_at(30.25,30),30)==-720
        result.append(mode+' exact subframe and curve PASS')
    before=curve.GetKey(1).GetValue()
    for value in [float('nan'),float('inf'),True,-1]:
        response=api.dispatch(doc,'set_keyframes',{'rig':ref,'tracks':{'radius':[{'frame':0,'value':value}]}})
        assert not response['ok'],value
    assert curve.GetKey(1).GetValue()==before
    result.append('invalid animation rejected PASS')
    for fps in [24,25,30,60]: assert abs(time_at(60.5,fps).Get()*fps-60.5)<1e-9
    result.append('24/25/30/60 FPS exact time PASS')
    assert state.runtime_version(rig)=='1.6.0'
    a=c4d.BaseObject(c4d.Onull); b=c4d.BaseObject(c4d.Onull)
    for obj in [a,b]: obj.SetName('same/name'); doc.InsertObject(obj)
    assert state._path(a)!=state._path(b)
    assert state.resolve_object(doc,state._path(a))==a
    result.append('duplicate names and escaped paths PASS')
    second=build_cam_rig(doc)
    second.RemoveUserData(ud_map(second)['Height'])
    before=rig[ud_map(rig)['Height']]
    response=api.dispatch(doc,'batch',{'rigs':[ref,state._path(second)],'controls':{'height':123},'dry_run':True})
    assert not response['ok'] and response['errors'][0]['code']=='STRUCTURE_UNSUPPORTED'
    assert rig[ud_map(rig)['Height']]==before
    result.append('batch dry-run missing DescID preflight PASS')
    api.set_keyframes(doc,ref,{'height':[{'frame':0,'value':17},{'frame':60.5,'value':33}]},'linear',True,True)
    assert doc.DoUndo()
    rig=state.resolve_rig(doc,ref)
    assert rig.FindCTrack(ud_map(rig)['Height']) is None
    assert doc.DoRedo()
    rig=state.resolve_rig(doc,ref)
    restored=rig.FindCTrack(ud_map(rig)['Height']).GetCurve()
    assert restored.GetKeyCount()==2
    assert abs(restored.GetKey(1).GetTime().Get()*30-60.5)<1e-9
    result.append('new track Undo/Redo exact keys PASS')
    original=rig.GetMl()
    for bad in [True,float('nan'),float('inf'),'12']:
        response=api.dispatch(doc,'set_root_transform',{'rig':ref,'transform':{'position':{'x':999},'rotation_deg':{'y':bad}}})
        assert not response['ok'] and response['errors'][0]['code']=='INVALID_TRANSFORM'
        assert rig.GetMl()==original
    api.set_root_transform(doc,ref,{'position':{'x':123}})
    assert rig.GetRelPos()==c4d.Vector(123,original.off.y,original.off.z)
    assert doc.DoUndo()
    rig=state.resolve_rig(doc,ref)
    assert rig.GetMl()==original
    result.append('root transform preflight and partial XYZ Undo PASS')
    rollback_doc=c4d.documents.BaseDocument()
    rollback_refs=[]
    for name,value in [('Rollback_A',111),('Rollback_B',222)]:
        node=build_cam_rig(rollback_doc)
        node.SetName(name)
        node[ud_map(node)['Height']]=value
        rollback_refs.append(state._path(node))
    original_reset=api.reset_rig_params
    calls=[]
    def fail_second(*args,**kwargs):
        calls.append(args[0].GetName())
        if len(calls)==2: raise RuntimeError('QA injected second-rig failure')
        return original_reset(*args,**kwargs)
    try:
        api.reset_rig_params=fail_second
        response=api.dispatch(rollback_doc,'batch',{'rigs':rollback_refs,'action':'reset','group':'all','dry_run':False,'confirm':True})
    finally:
        api.reset_rig_params=original_reset
    assert len(calls)==2 and not response['ok']
    restored_nodes=[state.resolve_rig(rollback_doc,ref) for ref in rollback_refs]
    assert [node[ud_map(node)['Height']] for node in restored_nodes]==[111,222]
    result.append('batch second-rig failure restores both heights PASS')
    return result
