"""Live C4D save/reopen equivalence test. Runs only on a detached QA document."""
import math
import c4d
from camrig import agent_api as api, agent_state as state
from camrig.rig_assemble import build_cam_rig
from camrig.commands import ud_map


def _vec(raw): return c4d.Vector(raw['x'],raw['y'],raw['z'])


def _angle(left, right):
    trace=sum(_vec(left[key]).GetNormalized().Dot(_vec(right[key]).GetNormalized()) for key in ('v1','v2','v3'))
    return math.acos(max(-1.0,min(1.0,(trace-1.0)/2.0)))


def _assert_matrix(left, right):
    assert (_vec(left['off'])-_vec(right['off'])).GetLength() <= 1e-4, (left['off'],right['off'])
    assert _angle(left,right) <= 1e-5, _angle(left,right)


def _assert_samples(before, after):
    assert len(before)==len(after)
    for left,right in zip(before,after):
        assert left['frame']==right['frame']
        _assert_matrix(left['camera'],right['camera'])
        _assert_matrix(left['fx_camera'],right['fx_camera'])
        _assert_matrix(left['spring_offset_local'],right['spring_offset_local'])
        assert abs(left['focal_length']-right['focal_length']) <= 1e-4
        assert abs(left['focus_distance']-right['focus_distance']) <= 1e-4


def _tracks(rig):
    result={}
    for key in ('Orbit', 'Height'):
        track=rig.FindCTrack(ud_map(rig)[key])
        curve=track.GetCurve()
        result[key]=[(curve.GetKey(i).GetTime().Get(), curve.GetKey(i).GetValue(), curve.GetKey(i).GetInterpolation())
                     for i in range(curve.GetKeyCount())]
    return result


def run(path):
    doc=c4d.documents.BaseDocument(); doc.SetFps(30); doc.SetMaxTime(c4d.BaseTime(100,30))
    rig=build_cam_rig(doc); rig.SetName('Save Reopen QA'); ref=state._path(rig)
    assert api.set_keyframes(doc,ref,{
        'orbit':[{'frame':0,'value':-180.0},{'frame':60.5,'value':720.0}],
        'height':[{'frame':0,'value':0.0},{'frame':10,'value':300.0},{'frame':100,'value':300.0}],
    },'step',True,True)['ok']
    assert api.set_controls(doc,ref,{'spring_amount':100.,'spring_response':35.,'spring_damping':35.},True)['ok']
    before=api.sample(doc,ref,[0,10,15,30,60.5,100])['state']['samples']
    before_tracks=_tracks(rig)
    assert api.save_scene(doc,path,True)['ok']
    loaded=c4d.documents.LoadDocument(path,c4d.SCENEFILTER_OBJECTS|c4d.SCENEFILTER_MATERIALS,None)
    assert loaded is not None
    loaded_rig=state.resolve_rig(loaded,'/Save Reopen QA')
    after=api.sample(loaded,'/Save Reopen QA',[0,10,15,30,60.5,100])['state']['samples']
    _assert_samples(before,after)
    assert before_tracks==_tracks(loaded_rig)
    return {'samples':len(before),'track_equivalence':'PASS','camera_equivalence':'PASS'}
