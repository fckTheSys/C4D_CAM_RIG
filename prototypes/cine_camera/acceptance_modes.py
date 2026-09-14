"""Live trajectory/free regression checks in an owned, detached C4D document."""
import importlib.util
from pathlib import Path
import c4d


def run():
    spec = importlib.util.spec_from_file_location('cine_modes_builder', Path(__file__).with_name('builder.py'))
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    document = c4d.documents.BaseDocument()
    document.SetFps(30)
    passed = []
    try:
        root, nodes, ids = builder.build(document)
        camera = nodes[8]

        def evaluate(frame=0, animation=True):
            document.SetTime(c4d.BaseTime(int(frame * 1000), 30000))
            document.ExecutePasses(None, animation, True, True, c4d.BUILDFLAGS_NONE)
            status = root[ids['status']]
            assert status.endswith('prototype: ready'), status

        def near(a, b, tolerance=1e-5):
            assert (a - b).GetLength() < tolerance, (str(a), str(b))

        def same_matrix(a, b):
            for name in ('off', 'v1', 'v2', 'v3'):
                near(getattr(a, name), getattr(b, name))

        root[ids['movement_mode']] = 1
        root.SetRelPos(c4d.Vector(100, 0, 30))
        root.SetRelRot(c4d.Vector(.4, .2, -.1))
        for progress, index in ((0., 0), (1., 2)):
            root[ids['progress']] = progress
            evaluate()
            # Native Align endpoint interpolation has sub-millimetre error.
            near(camera.GetMg().off, nodes[10].GetMg() * nodes[10].GetPoint(index), .01)
            direction = (nodes[3].GetMg().off - camera.GetMg().off).GetNormalized()
            assert camera.GetMg().v3.GetNormalized().Dot(direction) > .999999
        passed.append('native trajectory endpoints under transformed root; target alignment')

        external = c4d.SplineObject(2, c4d.SPLINETYPE_LINEAR)
        external.SetAllPoints([c4d.Vector(), c4d.Vector(0, 0, 600)])
        document.InsertObject(external)
        external.SetRelPos(c4d.Vector(700, 200, -300))
        external.SetRelRot(c4d.Vector(.8, 0, 0))
        external.Message(c4d.MSG_UPDATE)
        root[ids['path']] = external
        root[ids['progress']] = .25
        root[ids['offset_x']] = 35.
        evaluate()
        near(camera.GetMg().off, external.GetMg() * c4d.Vector(0, 0, 150) + root.GetMg().v1 * 35.)
        root[ids['offset_x']] = 0.
        passed.append('external transformed spline; offset in rig axes')

        track = c4d.CTrack(root, ids['progress'])
        root.InsertTrackSorted(track)
        curve = track.GetCurve()
        for frame, value in ((0, 0.), (60, 1.)):
            key = curve.AddKey(c4d.BaseTime(frame, 30))['key']
            key.SetValue(curve, value)
            key.SetInterpolation(curve, c4d.CINTERPOLATION_LINEAR)
        snapshots = {}
        for frame in (0, 12.5, 30, 47.25, 60):
            evaluate(frame)
            snapshots[frame] = camera.GetMg()
        for frame in (60, 12.5, 47.25, 0, 30):
            evaluate(frame)
            same_matrix(camera.GetMg(), snapshots[frame])
        before = camera.GetMg().off
        root[ids['progress']] = .2
        evaluate(30, animation=False)
        assert (camera.GetMg().off - before).GetLength() > 1.
        passed.append('progress keys, shuffled subframes and live unkeyed preview')

        root[ids['movement_mode']] = 2
        root[ids['aim_mode']] = 0
        nodes[11].SetRelPos(c4d.Vector(30, 70, -20))
        nodes[11].SetRelRot(c4d.Vector(.7, -.2, .15))
        evaluate()
        same_matrix(camera.GetMg(), nodes[11].GetMg())
        root[ids['offset_z']] = 25.
        evaluate()
        near(camera.GetMg().off, nodes[11].GetMg() * c4d.Vector(0, 0, 25))
        root[ids['offset_z']] = 0.
        passed.append('free controller full transform; offset in controller axes')

        free_desc = c4d.DescID(c4d.DescLevel(c4d.ID_BASEOBJECT_REL_POSITION, c4d.DTYPE_VECTOR, 0),
                               c4d.DescLevel(c4d.VECTOR_X, c4d.DTYPE_REAL, 0))
        free_track = c4d.CTrack(nodes[11], free_desc)
        nodes[11].InsertTrackSorted(free_track)
        free_curve = free_track.GetCurve()
        for frame, value in ((0, 0.), (60, 300.)):
            key = free_curve.AddKey(c4d.BaseTime(frame, 30))['key']
            key.SetValue(free_curve, value)
            key.SetInterpolation(free_curve, c4d.CINTERPOLATION_LINEAR)
        for frame in (0, 45.5, 60, 12.5, 0):
            evaluate(frame)
            same_matrix(camera.GetMg(), nodes[11].GetMg())
        passed.append('direct Free Controller position keys at arbitrary subframes')

        root[ids['aim_mode']] = 1
        for mode in (2, 0, 1, 2, 1, 0):
            root[ids['movement_mode']] = mode
            evaluate(30)
            direction = (nodes[3].GetMg().off - camera.GetMg().off).GetNormalized()
            assert camera.GetMg().v3.GetNormalized().Dot(direction) > .999999
            if mode != 2:
                near(nodes[5].GetRelRot(), c4d.Vector())
        passed.append('mode switching clears previous rotation and retains common aim')

        root[ids['movement_mode']] = 1
        root[ids['path']] = nodes[8]
        document.ExecutePasses(None, True, True, True, c4d.BUILDFLAGS_NONE)
        assert 'cannot depend' in root[ids['status']]
        root[ids['movement_mode']] = 0
        evaluate()
        root[ids['path']] = None
        root[ids['movement_mode']] = 1
        evaluate()
        passed.append('cycle diagnosis; inactive path ignored; empty link uses built-in path')
        return {'status': 'PASS', 'host': c4d.GetC4DVersion(), 'checks': passed}
    finally:
        c4d.documents.KillDocument(document)
