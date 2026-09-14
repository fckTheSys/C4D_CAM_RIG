"""Live P1 checks, main thread only; no inspection of user documents."""
import importlib.util
import math
from pathlib import Path
import uuid
import c4d


def run():
    spec = importlib.util.spec_from_file_location('cine_p1_builder', Path(__file__).with_name('builder.py'))
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    document = c4d.documents.BaseDocument()
    document.SetFps(30)
    passed = []

    def near(a, b, tolerance=1e-5):
        assert (a - b).GetLength() < tolerance, (str(a), str(b))

    def evaluate(time=0):
        document.SetTime(c4d.BaseTime(int(round(time * 1000)), 30000))
        document.ExecutePasses(None, True, True, True, c4d.BUILDFLAGS_NONE)
        assert root[ids['status']] == 'Orbit prototype: ready', root[ids['status']]

    try:
        root, nodes, ids = builder.build(document)
        camera = nodes[8]
        evaluate()
        assert sum(n.GetType() in (c4d.Ocamera, 1057516) for n in nodes.values()) == 1
        assert nodes[6].GetType() == c4d.Onull
        assert camera.GetMg().off.GetLength() > 400, 'Native Align did not evaluate'
        for angle in (-720., -90., 0., 90., 360., 810.):
            root[ids['angle']] = angle
            evaluate()
            position = camera.GetMg().off
            assert abs(math.hypot(position.x, position.z) - 500.) < .01
            assert abs(position.y - 150.) < 1e-5
            forward = (nodes[3].GetMg().off - position).GetNormalized()
            assert camera.GetMg().v3.GetNormalized().Dot(forward) > .999999
        passed.append('one camera; signed multi-turn orbit; native target alignment')

        root.SetRelPos(c4d.Vector(75, 20, -40))
        root.SetRelRot(c4d.Vector(.3, .1, -.2))
        nodes[2].SetRelPos(c4d.Vector(20, 30, 40))
        evaluate()
        local = ~root.GetMg() * camera.GetMg().off - nodes[2].GetRelPos()
        assert abs(math.hypot(local.x, local.z) - 500.) < .01
        assert abs(local.y - 150.) < 1e-5
        passed.append('translated and rotated rig; independent orbit center')

        root[ids['aim_mode']] = 0
        root[ids['pan']] = 25.
        root[ids['tilt']] = -10.
        root[ids['roll']] = 5.
        evaluate()
        near(nodes[6].GetRelRot(), c4d.Vector())
        near(nodes[7].GetRelRot(), c4d.Vector(*map(math.radians, (25, -10, 5))))
        root[ids['aim_mode']] = 1
        root[ids['pan']] = root[ids['tilt']] = root[ids['roll']] = 0.
        passed.append('target to manual reset; frame pan/tilt/roll')

        track = c4d.CTrack(root, ids['angle'])
        root.InsertTrackSorted(track)
        curve = track.GetCurve()
        for frame, value in ((0, -180.), (60, 540.)):
            key = curve.AddKey(c4d.BaseTime(frame, 30))['key']
            key.SetValue(curve, value)
            key.SetInterpolation(curve, c4d.CINTERPOLATION_LINEAR)
        times = (0, 7.5, 15, 30, 44.25, 60)
        samples = {}
        for time in times:
            evaluate(time)
            samples[time] = camera.GetMg()
        for time in reversed(times):
            evaluate(time)
            actual, expected = camera.GetMg(), samples[time]
            for field in ('off', 'v1', 'v2', 'v3'):
                near(getattr(actual, field), getattr(expected, field))
        evaluate(15)
        before = camera.GetMg().off
        root[ids['angle']] = 45.
        document.ExecutePasses(None, False, True, True, c4d.BUILDFLAGS_NONE)
        assert (camera.GetMg().off - before).GetLength() > 1.
        passed.append('keyed forward/reverse and subframes; live unkeyed edit on keyed parameter')

        for node in nodes.values():
            node.SetName('Renamed')
        evaluate(30)
        translator = c4d.AliasTrans()
        assert translator.Init(document)
        duplicate = root.GetClone(c4d.COPYFLAGS_NONE, translator)
        translator.Translate(True)
        document.InsertObject(duplicate)
        duplicate[ids['radius']] = 250.
        duplicate.SetRelPos(c4d.Vector(1000, 0, 0))
        evaluate(30)
        assert duplicate[ids['center']] != nodes[2]
        assert duplicate[ids['camera']] != camera
        assert duplicate[ids['status']] == 'Orbit prototype: ready'
        passed.append('renaming and clone-local controller links')

        focal = c4d.RSCAMERAOBJECT_FOCAL_LENGTH if camera.GetType() == 1057516 else c4d.CAMERA_FOCUS
        camera[focal] = 72.
        evaluate(12)
        assert abs(camera[focal] - 72.) < 1e-6
        root[ids['center']] = camera
        document.ExecutePasses(None, True, True, True, c4d.BUILDFLAGS_NONE)
        assert 'cannot depend' in root[ids['status']]
        root[ids['center']] = nodes[2]
        evaluate(12)
        passed.append('native lens ownership; cycle diagnostic and recovery')

        standard, standard_nodes, standard_ids = builder.build(document, use_redshift=False)
        evaluate(0)
        assert standard_nodes[8].GetType() == c4d.Ocamera
        assert standard[standard_ids['status']] == 'Orbit prototype: ready'
        passed.append('standard camera fallback')

        duplicate[ids['movement_mode']] = 1
        standard[standard_ids['movement_mode']] = 2
        evaluate(0)

        artifact = Path(__file__).resolve().parents[2] / 'tests' / 'artifacts' / ('cine_p1_' + uuid.uuid4().hex + '.c4d')
        artifact.parent.mkdir(parents=True, exist_ok=True)
        assert c4d.documents.SaveDocument(document, str(artifact), c4d.SAVEDOCUMENTFLAGS_DONTADDTORECENTLIST, c4d.FORMAT_C4DEXPORT)
        loaded = c4d.documents.LoadDocument(str(artifact), c4d.SCENEFILTER_OBJECTS | c4d.SCENEFILTER_MATERIALS, None)
        assert loaded is not None
        try:
            loaded.ExecutePasses(None, True, True, True, c4d.BUILDFLAGS_NONE)
            loaded_root = loaded.GetFirstObject()
            while loaded_root is not None:
                assert loaded_root[ids['status']].endswith('prototype: ready')
                loaded_camera = loaded_root[ids['camera']]
                assert loaded_camera.GetDocument() == loaded
                loaded_root = loaded_root.GetNext()
        finally:
            c4d.documents.KillDocument(loaded)
        passed.append('native save/load of all three modes; embedded runtime and links')
        return {'status': 'PASS', 'checks': passed, 'host': c4d.GetC4DVersion(),
                'artifact': str(artifact),
                'boundary': 'isolated document, no viewport/render or old-rig visual acceptance'}
    finally:
        c4d.documents.KillDocument(document)
