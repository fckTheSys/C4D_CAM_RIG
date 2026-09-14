"""Effects and historical source live checks in a private test document."""
import importlib.util
from pathlib import Path
import c4d
import uuid
import time


def run():
    spec = importlib.util.spec_from_file_location('cine_fx_builder', Path(__file__).with_name('builder.py'))
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    document = c4d.documents.BaseDocument()
    document.SetFps(30)
    passed = []
    try:
        root, nodes, ids = builder.build(document)
        def evaluate(frame):
            document.SetTime(c4d.BaseTime(int(frame * 1000), 30000))
            document.ExecutePasses(None, True, True, True, c4d.BUILDFLAGS_NONE)
            assert root[ids['status']].endswith('prototype: ready'), root[ids['status']]
            return nodes[8].GetMg()
        def key(node, desc, values):
            track = c4d.CTrack(node, desc)
            node.InsertTrackSorted(track)
            curve = track.GetCurve()
            for frame, value in values:
                item = curve.AddKey(c4d.BaseTime(frame, 30))['key']
                item.SetValue(curve, value)
                item.SetInterpolation(curve, c4d.CINTERPOLATION_LINEAR)
        def same(a, b):
            for field in ('off', 'v1', 'v2', 'v3'):
                assert (getattr(a, field)-getattr(b, field)).GetLength() < 1e-6

        key(root, ids['angle'], [(0,0.),(60,180.),(120,180.)])
        key(root, ids['progress'], [(0,0.),(60,1.),(120,1.)])
        desc = c4d.DescID(c4d.DescLevel(c4d.ID_BASEOBJECT_REL_POSITION,c4d.DTYPE_VECTOR,0),
                          c4d.DescLevel(c4d.VECTOR_X,c4d.DTYPE_REAL,0))
        key(nodes[11], desc, [(0,500.),(60,800.),(120,800.)])
        root[ids['spring_strength']] = .7
        for mode in (0, 1, 2):
            root[ids['movement_mode']] = mode
            snapshots = {frame:evaluate(frame) for frame in (0, 12.5, 30, 60, 75.25, 120)}
            for frame in (120, 12.5, 75.25, 0, 30, 60):
                same(evaluate(frame), snapshots[frame])
            evaluate(45)
            assert nodes[12].GetRelPos().GetLength() > .01, 'Inertia has no effect'
            direction = (nodes[3].GetMg().off-nodes[8].GetMg().off).GetNormalized()
            assert nodes[8].GetMg().v3.GetNormalized().Dot(direction) > .999999
            at_stop = (evaluate(60).off-nodes[9].GetMg().off).GetLength()
            settled = (evaluate(120).off-nodes[9].GetMg().off).GetLength()
            assert settled < at_stop * .1, (mode, at_stop, settled)
        passed.append('inertia on all modes; subframes and shuffled seeks; aim and settling')

        root[ids['spring_strength']] = 0.
        baseline = evaluate(30)
        assert nodes[12].GetRelPos().GetLength() < 1e-8
        for prefix in ('shake', 'drift'):
            root[ids[prefix+'_strength']] = .5
            snapshots = {frame:evaluate(frame) for frame in (0, 15.5, 45, 90)}
            assert nodes[13].GetRelPos().GetLength() > 0
            assert nodes[13].GetRelRot().GetLength() > 0
            for frame in (90, 0, 45, 15.5):
                same(evaluate(frame), snapshots[frame])
            root[ids[prefix+'_strength']] = 0.
        same(evaluate(30), baseline)
        passed.append('independent drift and shake; deterministic samples; exact zero bypass')

        root[ids['spring_strength']] = .7
        before = evaluate(45)
        spring_before = nodes[12].GetRelPos()
        root[ids['shake_strength']] = .25
        root[ids['drift_strength']] = .2
        evaluate(45)
        assert (spring_before - nodes[12].GetRelPos()).GetLength() < 1e-8
        assert (nodes[8].GetMg().off-before.off).GetLength() > .001
        key(root, ids['shake_strength'], [(0,0.), (30,.5), (60,0.)])
        snapshots = {frame:evaluate(frame) for frame in (0,15.5,30,60)}
        for frame in (60,15.5,0,30):
            same(evaluate(frame),snapshots[frame])
        passed.append('FX do not feed inertia; animated strength fades are seek-independent')
        baseline = evaluate(45)
        artifact = Path(__file__).resolve().parents[2] / 'tests' / 'artifacts' / ('cine_p3_' + uuid.uuid4().hex + '.c4d')
        artifact.parent.mkdir(parents=True, exist_ok=True)
        assert c4d.documents.SaveDocument(document, str(artifact), c4d.SAVEDOCUMENTFLAGS_DONTADDTORECENTLIST, c4d.FORMAT_C4DEXPORT)
        loaded = c4d.documents.LoadDocument(str(artifact), c4d.SCENEFILTER_OBJECTS | c4d.SCENEFILTER_MATERIALS, None)
        assert loaded is not None
        try:
            loaded.SetTime(c4d.BaseTime(45,30))
            loaded.ExecutePasses(None,True,True,True,c4d.BUILDFLAGS_NONE)
            restored = loaded.GetFirstObject()
            assert restored[ids['status']].endswith('prototype: ready'), restored[ids['status']]
            same(restored[ids['camera']].GetMg(),baseline)
        finally:
            c4d.documents.KillDocument(loaded)
        passed.append('save/load cold inertia cache reproduces camera with all effects')
        evaluate(-3)
        assert nodes[12].GetRelPos().GetLength() < 1e-8
        evaluate(45)
        begin = time.perf_counter()
        for index in range(40):
            root[ids['drift_strength']] = .2 + index / 1000.
            document.ExecutePasses(None,False,True,True,c4d.BUILDFLAGS_NONE)
        warm_ms = (time.perf_counter()-begin)*1000/40
        return {'status':'PASS','host':c4d.GetC4DVersion(),'checks':passed,
                'warm_effect_edit_ms':round(warm_ms,3),'artifact':str(artifact),
                'timing_scope':'40 expression passes in tiny detached fixture; not viewport FPS'}
    finally:
        c4d.documents.KillDocument(document)
