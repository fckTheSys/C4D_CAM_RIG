"""Reproducibility probe in exact owned detached documents; C4D main thread."""
import json
from pathlib import Path
import runpy
import time

import c4d

ROLE_ID = 10699101
DIAGNOSTIC_ID = 10699102
TOLERANCE = 1e-5


def _fixture(builder):
    document, root, objects, ids = builder['fixture']()
    builder['key'](document, root, ids['Step Length'], [(0, 70), (90, 40), (180, 90)])
    builder['key'](document, root, ids['Shake Frequency'], [(0, .5), (90, 4), (180, 1)])
    curve=root.FindCTrack(ids['Progress']).GetCurve()
    for i in range(curve.GetKeyCount()):
        key=curve.GetKey(i)
        key.SetInterpolation(curve,c4d.CINTERPOLATION_SPLINE)
        key.ChangeNBit(c4d.NBIT_CKEY_AUTO,c4d.NBITCONTROL_CLEAR)
        if i:
            key.SetTimeLeft(curve,c4d.BaseTime((curve.GetKey(i-1).GetTime().Get()-key.GetTime().Get())/3))
        if i+1<curve.GetKeyCount():
            key.SetTimeRight(curve,c4d.BaseTime((curve.GetKey(i+1).GetTime().Get()-key.GetTime().Get())/3))
        key.SetValueLeft(curve,0.0);key.SetValueRight(curve,0.0)
    return document, root, objects


def _sample(document, root, objects, frame):
    document.SetTime(c4d.BaseTime(int(round(frame * 1000)), document.GetFps() * 1000))
    document.ExecutePasses(None, True, True, True, c4d.BUILDFLAGS_NONE)
    diagnostics = [tag.GetDataInstance().GetString(DIAGNOSTIC_ID)
                   for tag in root.GetTags() if tag.GetType() == c4d.Tpython]
    if len(diagnostics) != 2:
        raise RuntimeError('Expected Prepare and Finish Python tags')
    if any(diagnostics):
        raise RuntimeError('Runtime diagnostics: ' + repr(diagnostics))
    matrix = objects[9].GetMg()
    return {'frame': frame, 'matrix': [component for vector in
            (matrix.off, matrix.v1, matrix.v2, matrix.v3)
            for component in (vector.x, vector.y, vector.z)]}


def _sequence(document, root, objects, frames):
    begin = time.perf_counter()
    rows = [_sample(document, root, objects, frame) for frame in frames]
    return rows, (time.perf_counter() - begin) * 1000


def _error(rows, baseline):
    return max(abs(a-b) for row in rows
               for a, b in zip(row['matrix'], baseline[int(row['frame'])]['matrix']))


def _resolve(document):
    roots = []
    node = document.GetFirstObject()
    while node is not None:
        if node.GetDataInstance().GetInt32(ROLE_ID) == 1:
            roots.append(node)
        node = node.GetNext()
    if len(roots) != 1:
        raise RuntimeError('Expected one owned reopened root')
    root = roots[0]
    objects = {}
    stack = [root]
    while stack:
        node = stack.pop()
        role = node.GetDataInstance().GetInt32(ROLE_ID)
        if role in objects:
            raise RuntimeError('Duplicate role in reopened rig')
        objects[role] = node
        stack.extend(node.GetChildren())
    if set(objects) != set(range(1, 11)):
        raise RuntimeError('Incomplete reopened rig role map')
    align = objects[4].GetTag(c4d.Taligntospline)
    target = objects[6].GetTag(c4d.Ttargetexpression)
    if (align is None or target is None or
            align[c4d.ALIGNTOSPLINETAG_LINK] != objects[2] or
            target[c4d.TARGETEXPRESSIONTAG_LINK] != objects[3]):
        raise RuntimeError('Native links did not survive reopen')
    return root, objects


def run(output_directory):
    if not c4d.threading.GeIsMainThread():
        raise RuntimeError('Acceptance must run on the C4D main thread')
    output = Path(output_directory).resolve()
    output.mkdir(parents=True, exist_ok=False)
    builder = runpy.run_path(str(Path(__file__).with_name('builder.py')))
    document, root, objects = _fixture(builder)
    baseline, sequential_ms = _sequence(document, root, objects, range(181))
    repeated, repeat_ms = _sequence(document, root, objects, range(181))
    mixed, _ = _sequence(document, root, objects, (90, 30, 150, 60, 90, 0, 180))
    reverse, _ = _sequence(document, root, objects, reversed(range(181)))
    fresh_document, fresh_root, fresh_objects = _fixture(builder)
    fresh90 = _sample(fresh_document, fresh_root, fresh_objects, 90)
    sub_document, sub_root, sub_objects = _fixture(builder)
    _sequence(sub_document, sub_root, sub_objects, range(90))
    half = _sample(sub_document, sub_root, sub_objects, 89.5)
    after_half = _sample(sub_document, sub_root, sub_objects, 90)

    saved_document, saved_root, saved_objects = _fixture(builder)
    saved, _ = _sequence(saved_document, saved_root, saved_objects, range(181))
    scene = output / 'simple_camera.c4d'
    if not c4d.documents.SaveDocument(saved_document, str(scene),
            c4d.SAVEDOCUMENTFLAGS_DONTADDTORECENTLIST, c4d.FORMAT_C4DEXPORT):
        raise RuntimeError('Could not save owned scene')
    reopened_document = c4d.documents.LoadDocument(str(scene),
        c4d.SCENEFILTER_OBJECTS | c4d.SCENEFILTER_MATERIALS, None)
    if reopened_document is None:
        raise RuntimeError('Could not reopen owned scene')
    reopened_root, reopened_objects = _resolve(reopened_document)
    reopened, reopen_ms = _sequence(reopened_document, reopened_root, reopened_objects, range(181))
    errors = {'repeat': _error(repeated, baseline), 'mixed': _error(mixed, baseline),
              'reverse': _error(reverse, baseline), 'fresh90': _error([fresh90], baseline),
              'subframe_then90': _error([after_half], baseline),
              'save_reopen': _error(reopened, saved)}
    evidence = output / 'evidence.json'
    result = {'status': 'PASS' if all(v <= TOLERANCE for v in errors.values()) else 'FAIL',
              'scope': 'One-rig reproducibility with eased Progress, animated Step Length and Shake Frequency; not full rig acceptance.',
              'matrix_component_tolerance': TOLERANCE, 'max_component_errors': errors,
              'runtime_diagnostics': [], 'native_links_reopened': True,
              'timings_ms': {'one_rig_181_frames': sequential_ms, 'repeat': repeat_ms, 'reopen': reopen_ms},
              'scene_path': str(scene), 'evidence_path': str(evidence),
              'samples': {'baseline': baseline, 'repeat': repeated, 'mixed': mixed,
                          'reverse': reverse, 'fresh90': fresh90, 'subframe89_5': half,
                          'after_subframe90': after_half, 'saved': saved, 'reopened': reopened}}
    with evidence.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False, allow_nan=False)
    return result
