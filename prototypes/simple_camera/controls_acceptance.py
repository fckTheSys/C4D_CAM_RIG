"""Bounded control/ownership checks, executed only on the C4D main thread."""
import json
import math
from pathlib import Path
import runpy

import c4d

ROLE_ID = 10699101


def _matrix(matrix):
    return [n for v in (matrix.off, matrix.v1, matrix.v2, matrix.v3) for n in (v.x, v.y, v.z)]


def _error(left, right):
    return max(abs(a-b) for a, b in zip(_matrix(left), _matrix(right)))


def _tracks(root):
    result = []
    for track in root.GetCTracks():
        desc = track.GetDescriptionID()
        curve = track.GetCurve()
        keys = []
        for i in range(curve.GetKeyCount()):
            key = curve.GetKey(i)
            keys.append([key.GetTime().Get(), key.GetValue(), key.GetInterpolation(),
                         key.GetTimeLeft().Get(), key.GetTimeRight().Get(),
                         key.GetValueLeft(), key.GetValueRight()])
        result.append({'description': [[desc[i].id, desc[i].dtype, desc[i].creator]
                                      for i in range(desc.GetDepth())],
                       'before': track.GetBefore(), 'after': track.GetAfter(), 'keys': keys})
    return result


def run(output_directory):
    if not c4d.threading.GeIsMainThread():
        raise RuntimeError('Control acceptance requires the C4D main thread')
    output = Path(output_directory).resolve()
    output.mkdir(parents=True, exist_ok=False)
    folder = Path(__file__).parent
    create = runpy.run_path(str(folder / 'create_simple_camera.py'))
    select = runpy.run_path(str(folder / 'select_camera.py'))
    builder = runpy.run_path(str(folder / 'builder.py'))
    active_before = c4d.documents.GetActiveDocument()
    document = c4d.documents.BaseDocument()
    document.SetFps(30)
    document.SetMaxTime(c4d.BaseTime(180, 30))
    root = create['main'](document)
    cases = []

    def check(name, passed, **details):
        cases.append(dict(name=name, passed=bool(passed), **details))

    check('create selects owned root', document.GetActiveObject() == root and
          root.GetDocument() == document and root.GetDataInstance().GetInt32(ROLE_ID) == 1)
    objects = {}
    stack = [root]
    while stack:
        node = stack.pop()
        objects[node.GetDataInstance().GetInt32(ROLE_ID)] = node
        stack.extend(node.GetChildren())
    camera = select['main'](document)
    check('select camera from root', camera == objects[9] and document.GetActiveObject() == camera)
    document.SetActiveObject(objects[5], c4d.SELECTION_NEW)
    check('select camera from descendant', select['main'](document) == camera)
    metadata = {bc[c4d.DESC_NAME]: (desc, bc) for desc, bc in root.GetUserDataContainer()}
    required_groups = ('Route / Body', 'Look', 'Motion', 'Walk', 'Shake', 'Drift', 'Camera')
    groups = [bc[c4d.DESC_NAME] for desc, bc in root.GetUserDataContainer()
              if desc[desc.GetDepth()-1].dtype == c4d.DTYPE_GROUP]
    check('compact groups', all(name in groups for name in required_groups), groups=groups)
    check('percent progress', metadata['Progress'][1][c4d.DESC_UNIT] == c4d.DESC_UNIT_PERCENT)
    check('mode not animatable', metadata['Aim Mode'][1][c4d.DESC_ANIMATE] == c4d.DESC_ANIMATE_OFF)
    links_ok = all(root[metadata[name][0]] == objects[role] and
                   bool(metadata[name][1][c4d.DESC_EDITABLE]) == (name != 'Camera')
                   for name, role in (('Path', 2), ('Target', 3), ('Camera', 9)))
    check('editable path/target and readonly camera', links_ok)
    check('readonly status', 'Status' in metadata and metadata['Status'][1][c4d.DESC_EDITABLE] == 0)

    def set_value(name, value):
        root[metadata[name][0]] = value

    def evaluate(frame):
        document.SetTime(c4d.BaseTime(frame, 30))
        document.ExecutePasses(None, True, True, True, c4d.BUILDFLAGS_NONE)
        diagnostics = [tag.GetDataInstance().GetString(ROLE_ID+1)
                       for tag in root.GetTags() if tag.GetType() == c4d.Tpython]
        if len(diagnostics) != 2 or any(diagnostics):
            raise RuntimeError('Runtime diagnostic: ' + repr(diagnostics))

    for name in ('Walk Strength', 'Shake Strength', 'Drift Strength'):
        set_value(name, 0.0)
    evaluate(0)
    fx_error = _error(objects[8].GetMl(), c4d.Matrix())
    camera_error = _error(camera.GetMg(), objects[7].GetMg())
    check('zero effects base pose', max(fx_error, camera_error) <= 1e-10,
          fx_identity_error=fx_error, camera_look_error=camera_error)
    # Visit a target-derived orientation before switching to manual mode.
    set_value('Aim Mode', 1)
    evaluate(0)
    set_value('Aim Mode', 0)
    for name, value in (('Pan', 30.0), ('Tilt', 70.0), ('Roll', 90.0), ('Body Y', 100.0)):
        set_value(name, value)
    evaluate(0)
    expected = (c4d.utils.MatrixRotY(math.radians(30)) *
                c4d.utils.MatrixRotX(math.radians(70)) *
                c4d.utils.MatrixRotZ(math.radians(90)))
    aim_error = _error(objects[6].GetMl(), c4d.Matrix())
    look_error = _error(objects[7].GetMl(), expected)
    check('target to manual resets aim and composes look', max(aim_error, look_error) <= 1e-10,
          aim_error=aim_error, look_error=look_error)
    actual = objects[5].GetMg().off - objects[4].GetMg().off
    expected_jump = root.GetMg().MulV(c4d.Vector(0, root[metadata['Height'][0]] + 100, 0))
    jump_error = (actual - expected_jump).GetLength()
    check('jump stays rig up with tilt70 roll90', jump_error <= 1e-10, error_cm=jump_error)

    set_value('Aim Mode', 1)
    evaluate(0)
    expected_direction=(objects[3].GetMg().off-objects[6].GetMg().off).GetNormalized()
    aim_direction_error=(objects[6].GetMg().v3.GetNormalized()-expected_direction).GetLength()
    check('manual to target aims in the same pass', aim_direction_error <= 1e-10,
          direction_error=aim_direction_error)

    builder['key'](document, root, metadata['Progress'][0], [(0, 0), (90, .7), (180, 1)])
    set_value('Walk Strength', 1.0)
    set_value('Shake Strength', .2)
    set_value('Drift Strength', .2)
    evaluate(0)
    camera_before = camera.GetDataInstance().GetClone(c4d.COPYFLAGS_NONE)
    tracks_before = _tracks(root)
    for frame in (30, 90, 150, 60, 180, 0):
        evaluate(frame)
    camera_after = camera.GetDataInstance().GetClone(c4d.COPYFLAGS_NONE)
    check('native camera data unchanged by evaluation', camera_before == camera_after,
          comparison='Full native BaseContainer equality; no guessed Redshift property IDs')
    tracks_after = _tracks(root)
    check('root key curves unchanged by evaluation', tracks_before == tracks_after)
    check('active document unchanged', c4d.documents.GetActiveDocument() == active_before)
    evidence = output / 'evidence.json'
    result = {'status': 'PASS' if all(case['passed'] for case in cases) else 'FAIL',
              'scope': 'Owned control UI, selection, base pose, manual reset, jump basis and source-data preservation only.',
              'cases': cases, 'tracks_before': tracks_before, 'tracks_after': tracks_after,
              'evidence_path': str(evidence)}
    with evidence.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
    c4d.documents.KillDocument(document)
    return result
