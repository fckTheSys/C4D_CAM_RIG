"""Keyed User Data preview on a stationary frame, without animation/key writes."""
from pathlib import Path
import json
import runpy
import c4d


def run(output_directory):
    output=Path(output_directory);output.mkdir(parents=True,exist_ok=False)
    folder=Path(__file__).parent
    b=runpy.run_path(str(folder/'builder.py'))
    helpers=runpy.run_path(str(folder/'controls_acceptance.py'))
    cases=[]
    for name,value in [('Progress',.85),('Pan',35),('Body Y',90),('Walk Strength',0),
                       ('Step Length',110),('Shake Frequency',7),('Drift Frequency',.8)]:
        d,r,o,ids=b['fixture']()
        if r.FindCTrack(ids[name]) is None:
            old=r[ids[name]]
            b['key'](d,r,ids[name],[(0,old),(180,old)])
        d.SetTime(c4d.BaseTime(60,30))
        d.ExecutePasses(None,True,True,True,c4d.BUILDFLAGS_NONE)
        original=helpers['_matrix'](o[9].GetMg())
        tracks=helpers['_tracks'](r)
        r[ids[name]]=value
        # Attribute edits on a stopped frame must not be overwritten by running
        # the animation pass here: that would deliberately restore the keys.
        d.ExecutePasses(None,False,True,True,c4d.BUILDFLAGS_NONE)
        edited=helpers['_matrix'](o[9].GetMg())
        diagnostics=[t.GetDataInstance().GetString(10699102) for t in r.GetTags() if t.GetType()==c4d.Tpython]
        change=max(abs(x-y) for x,y in zip(original,edited))
        unchanged=tracks==helpers['_tracks'](r)
        d.ExecutePasses(None,False,True,True,c4d.BUILDFLAGS_NONE)
        repeat=helpers['_matrix'](o[9].GetMg())
        repeat_error=max(abs(x-y) for x,y in zip(edited,repeat))
        d.ExecutePasses(None,True,True,True,c4d.BUILDFLAGS_NONE)
        restored=helpers['_matrix'](o[9].GetMg())
        reset_error=max(abs(x-y) for x,y in zip(original,restored))
        passed=change>1e-6 and unchanged and repeat_error<1e-5 and reset_error<1e-5 and not any(diagnostics)
        cases.append(dict(control=name,passed=passed,change=change,keys_unchanged=unchanged,
                          repeat_error=repeat_error,animation_restore_error=reset_error,diagnostics=diagnostics))
    result={'status':'PASS' if all(row['passed'] for row in cases) else 'FAIL','cases':cases,
            'scope':'Host expression passes at fixed frame with animation pass disabled emulate live keyed value edits; physical UI dragging not automated.'}
    with (output/'evidence.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    return result
