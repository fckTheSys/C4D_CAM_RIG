"""Owned detached-document edit, Undo/Redo and two-rig live acceptance.

Call run(new_output_directory) on the C4D main thread. This module never inserts
documents into the user document list or selects/closes a user's document.
"""
import json
from pathlib import Path
import runpy
import time

import c4d


FRAMES = (37, 89.5, 90, 149, 175)
TOLERANCE = 1e-5


def _ids(root):
    return {bc[c4d.DESC_NAME]: desc for desc, bc in root.GetUserDataContainer()}


def _difference(left, right):
    if len(left) != len(right) or any(a['frame'] != b['frame'] for a, b in zip(left, right)):
        raise ValueError('Comparison samples do not refer to the same times')
    return max(abs(x-y) for a, b in zip(left, right)
               for x, y in zip(a['matrix'], b['matrix']))


def _edit(kind, root, objects):
    ids = _ids(root)
    path = objects[2]
    if kind == 'path_point':
        path.SetPoint(1, path.GetPoint(1)+c4d.Vector(130, 0, -60))
        path.Message(c4d.MSG_UPDATE)
    elif kind == 'path_tangent':
        tangent = path.GetTangent(1)
        path.SetTangent(1, tangent['vl']+c4d.Vector(-80, 0, 40),
                        tangent['vr']+c4d.Vector(90, 0, 60))
        path.Message(c4d.MSG_UPDATE)
    elif kind == 'key_value':
        curve = root.FindCTrack(ids['Progress']).GetCurve()
        curve.GetKey(2).SetValue(curve, .64)
    elif kind == 'key_tangent':
        curve = root.FindCTrack(ids['Progress']).GetCurve()
        key = curve.GetKey(2)
        key.SetInterpolation(curve, c4d.CINTERPOLATION_SPLINE)
        key.ChangeNBit(c4d.NBIT_CKEY_AUTO, c4d.NBITCONTROL_CLEAR)
        key.SetTimeLeft(curve, c4d.BaseTime(-.35))
        key.SetValueLeft(curve, -.25)
        key.SetTimeRight(curve, c4d.BaseTime(.2))
        key.SetValueRight(curve, .08)
    elif kind == 'static_step_length':
        if root.FindCTrack(ids['Step Length']) is not None:
            raise RuntimeError('Static Step Length test requires an unkeyed control')
        root[ids['Step Length']] = 43.0
    elif kind == 'seed':
        root[ids['Seed']] = 29.0
    else:
        raise ValueError('Unknown edit case')


def _edit_case(builder, acceptance, kind):
    document, root, objects, unused = builder['fixture']()
    sample = acceptance['_sample']
    # Fill old prefix caches through the end before changing their input.
    sample(document, root, objects, 180)
    before = [sample(document, root, objects, frame) for frame in FRAMES]
    _edit(kind, root, objects)
    warmed = [sample(document, root, objects, frame) for frame in FRAMES]
    fresh_document, fresh_root, fresh_objects, unused = builder['fixture']()
    _edit(kind, fresh_root, fresh_objects)
    fresh = [sample(fresh_document, fresh_root, fresh_objects, frame) for frame in FRAMES]
    error = _difference(warmed, fresh)
    effect = _difference(before, warmed)
    return {'status': 'PASS' if error <= TOLERANCE and effect > TOLERANCE else 'FAIL',
            'max_component_error': error, 'observed_edit_effect': effect,
            'samples': {'before': before, 'warmed_edited': warmed, 'fresh_edited': fresh}}


def _undo_case(builder, acceptance):
    document = c4d.documents.BaseDocument()
    document.SetFps(30)
    root, objects, ids = builder['build'](document)
    root[ids['Progress']] = .43
    root[ids['Pan']] = 17.0
    root[ids['Shake Strength']] = .25
    before = [acceptance['_sample'](document, root, objects, frame) for frame in FRAMES]
    undone = document.DoUndo()
    # Never access pre-Undo object references after the document changed.
    root = objects = ids = None
    if not undone or document.GetFirstObject() is not None:
        raise RuntimeError('Builder Undo did not remove the sole owned subtree')
    redone = document.DoRedo()
    if not redone:
        raise RuntimeError('Builder Redo failed')
    # Resolver checks complete role membership and both native object links.
    root, objects = acceptance['_resolve'](document)
    after = [acceptance['_sample'](document, root, objects, frame) for frame in FRAMES]
    error = _difference(before, after)
    return {'status': 'PASS' if error <= TOLERANCE else 'FAIL',
            'undo_removed_owned_root': True, 'redo_links_resolved': True,
            'max_component_error': error, 'samples': {'before': before, 'after_redo': after}}


def _second_rig(builder, document):
    root, objects, ids = builder['build'](document)
    root[ids['Seed']] = 63.0
    root[ids['Height']] = 32.0
    root[ids['Step Length']] = 46.0
    root[ids['Pan']] = -22.0
    root[ids['Shake Strength']] = .4
    root[ids['Drift Strength']] = .3
    builder['key'](document, root, ids['Progress'], [(0, .1), (100, .9), (180, .2)])
    return root, objects


def _two_rigs_case(builder, acceptance):
    document, first, first_objects, unused = builder['fixture']()
    sample = acceptance['_sample']
    sample(document, first, first_objects, 180)
    original = [sample(document, first, first_objects, frame) for frame in FRAMES]
    second, second_objects = _second_rig(builder, document)
    first_rows, second_rows = [], []
    for frame in FRAMES:
        first_rows.append(sample(document, first, first_objects, frame))
        second_rows.append(sample(document, second, second_objects, frame))
    independent = c4d.documents.BaseDocument()
    independent.SetFps(30)
    independent.SetMaxTime(c4d.BaseTime(180, 30))
    fresh_root, fresh_objects = _second_rig(builder, independent)
    fresh = [sample(independent, fresh_root, fresh_objects, frame) for frame in FRAMES]
    errors = {'first_rig_unchanged': _difference(original, first_rows),
              'second_matches_independent': _difference(second_rows, fresh)}
    distinct = _difference(first_rows, second_rows)
    return {'status': 'PASS' if all(e <= TOLERANCE for e in errors.values()) and distinct > TOLERANCE else 'FAIL',
            'max_component_errors': errors, 'distinct_rig_difference': distinct,
            'samples': {'first_alone': original, 'first_together': first_rows,
                        'second_together': second_rows, 'second_independent': fresh}}


def run(output_directory):
    if not c4d.threading.GeIsMainThread():
        raise RuntimeError('Edit acceptance must run on the C4D main thread')
    output = Path(output_directory).resolve()
    output.mkdir(parents=True, exist_ok=False)
    folder = Path(__file__).parent
    builder = runpy.run_path(str(folder/'builder.py'))
    acceptance = runpy.run_path(str(folder/'acceptance.py'))
    start = time.perf_counter()
    cases = {}
    jobs = [(kind, lambda kind=kind: _edit_case(builder, acceptance, kind)) for kind in
            ('path_point', 'path_tangent', 'key_value', 'key_tangent', 'static_step_length', 'seed')]
    jobs.extend([('builder_undo_redo', lambda: _undo_case(builder, acceptance)),
                 ('two_rig_isolation', lambda: _two_rigs_case(builder, acceptance))])
    for name, job in jobs:
        case_start = time.perf_counter()
        try:
            cases[name] = job()
        except Exception as error:
            cases[name] = {'status': 'FAIL', 'exception': type(error).__name__, 'error': str(error)}
        cases[name]['elapsed_ms'] = (time.perf_counter()-case_start)*1000
    evidence = output/'edit_evidence.json'
    result = {'status': 'PASS' if all(case['status'] == 'PASS' for case in cases.values()) else 'FAIL',
              'scope': 'Detached owned documents: six input edits, builder Undo/Redo and two-rig isolation; no visual/render acceptance.',
              'matrix_component_tolerance': TOLERANCE, 'frames': FRAMES,
              'elapsed_ms': (time.perf_counter()-start)*1000,
              'cases': cases, 'evidence_path': str(evidence)}
    with evidence.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False, allow_nan=False)
    return result
