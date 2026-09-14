"""Detached-document numerical convergence, bounded benchmark and guard probe."""
import json
import math
from pathlib import Path
import runpy
import time

import c4d


FRAMES = (0, 15.5, 37, 89.5, 91, 125, 149.25, 175, 180)
POSITION_TOLERANCE = .01
BASIS_TOLERANCE = 1e-4
ROLE_ID = 10699101
DIAGNOSTIC_ID = ROLE_ID+1


def _diagnostics(root):
    tags = [tag for tag in root.GetTags() if tag.GetType() == c4d.Tpython]
    if len(tags) != 2:
        raise RuntimeError('Expected exactly two rig Python stages')
    return [tag.GetDataInstance().GetString(DIAGNOSTIC_ID) for tag in tags]


def _evaluate(document, frame):
    document.SetTime(c4d.BaseTime(int(round(frame*1000)), document.GetFps()*1000))
    document.ExecutePasses(None, True, True, True, c4d.BUILDFLAGS_NONE)


def _convergence(builder, acceptance):
    document, root, objects = acceptance['_fixture'](builder)
    reference_document, reference_root, reference_objects = acceptance['_fixture'](builder)
    old, new = 'grid=1.0/120.0', 'grid=1.0/480.0'
    for tag in reference_root.GetTags():
        if tag.GetType() != c4d.Tpython:
            continue
        code = tag[c4d.TPYTHON_CODE]
        if code.count(old) != 1:
            raise RuntimeError('Cannot safely identify the integration-grid declaration')
        tag[c4d.TPYTHON_CODE] = code.replace(old, new)
    normal, reference, errors = [], [], []
    for frame in FRAMES:
        a = acceptance['_sample'](document, root, objects, frame)
        b = acceptance['_sample'](reference_document, reference_root, reference_objects, frame)
        normal.append(a); reference.append(b)
        errors.append({'frame': frame,
                       'position_cm': math.dist(a['matrix'][:3], b['matrix'][:3]),
                       'basis_component': max(abs(x-y) for x, y in zip(a['matrix'][3:], b['matrix'][3:]))})
    position = max(row['position_cm'] for row in errors)
    basis = max(row['basis_component'] for row in errors)
    return {'status': 'PASS' if position <= POSITION_TOLERANCE and basis <= BASIS_TOLERANCE else 'FAIL',
            'max_position_cm': position, 'max_basis_component': basis,
            'method': '120 Hz compared with same embedded source at 480 Hz; numerical refinement, not an independent analytic ground truth.',
            'errors': errors, 'samples_120hz': normal, 'samples_480hz': reference}


def _benchmark(builder, acceptance, count):
    document, root, objects = acceptance['_fixture'](builder)
    roots = [root]
    for unused in range(count-1):
        clone = root.GetClone(c4d.COPYFLAGS_NONE)
        if clone is None:
            raise RuntimeError('Could not clone the owned benchmark rig')
        document.InsertObject(clone)
        roots.append(clone)
    start = time.perf_counter()
    _evaluate(document, 180)
    cold_ms = (time.perf_counter()-start)*1000
    for candidate in roots:
        if any(_diagnostics(candidate)):
            raise RuntimeError('Cold benchmark runtime diagnostic')
    start = time.perf_counter()
    for frame in range(181):
        # Exactly one document evaluation per frame irrespective of rig count.
        _evaluate(document, frame)
        for candidate in roots:
            errors = _diagnostics(candidate)
            if any(errors):
                raise RuntimeError('Benchmark runtime diagnostic: '+repr(errors))
    elapsed = (time.perf_counter()-start)*1000
    return {'rig_count': count, 'cold_seek180_ms': cold_ms,
            'warm_181_frames_ms': elapsed, 'warm_ms_per_frame': elapsed/181,
            'frame_count': 181, 'diagnostics': []}


def _position_x():
    return c4d.DescID(c4d.DescLevel(c4d.ID_BASEOBJECT_REL_POSITION, c4d.DTYPE_VECTOR, 0),
                      c4d.DescLevel(c4d.VECTOR_X, c4d.DTYPE_REAL, 0))


def _guard(builder, acceptance, kind):
    document, root, objects, ids = builder['fixture']()
    # Start valid to check that invalidation produces a current diagnostic.
    acceptance['_sample'](document, root, objects, 90)
    if kind == 'zero_path':
        path = objects[2]
        path.SetAllPoints([c4d.Vector(0) for unused in range(path.GetPointCount())])
        for index in range(path.GetPointCount()):
            path.SetTangent(index, c4d.Vector(0), c4d.Vector(0))
        path.Message(c4d.MSG_UPDATE)
    elif kind == 'camera_psr_keys':
        builder['key'](document, objects[9], _position_x(), [(0, 0), (180, 25)])
    elif kind == 'animated_root_transform':
        builder['key'](document, root, _position_x(), [(0, 0), (180, 25)])
    elif kind == 'path_tracks':
        builder['key'](document, objects[2], _position_x(), [(0, 0), (180, 25)])
    elif kind == 'target_expression':
        tag = c4d.BaseTag(c4d.Tpython)
        tag[c4d.TPYTHON_CODE] = 'def main():\n    pass\n'
        objects[3].InsertTag(tag)
    else:
        raise ValueError('Unknown guard case')
    _evaluate(document, 91)
    diagnostics = _diagnostics(root)
    return {'status': 'PASS' if any(diagnostics) else 'FAIL',
            'diagnostics': diagnostics,
            'criterion': 'Invalid source must report a nonempty diagnostic; camera output after rejection is not accepted.'}


def run(output_directory):
    if not c4d.threading.GeIsMainThread():
        raise RuntimeError('Numerical acceptance must run on C4D main thread')
    output = Path(output_directory).resolve()
    output.mkdir(parents=True, exist_ok=False)
    folder = Path(__file__).parent
    builder = runpy.run_path(str(folder/'builder.py'))
    acceptance = runpy.run_path(str(folder/'acceptance.py'))
    results = {}
    jobs = [('convergence', lambda: _convergence(builder, acceptance)),
            ('one_rig_benchmark', lambda: dict(status='PASS', **_benchmark(builder, acceptance, 1))),
            ('six_rig_benchmark', lambda: dict(status='PASS', **_benchmark(builder, acceptance, 6)))]
    jobs.extend((kind, lambda kind=kind: _guard(builder, acceptance, kind)) for kind in
                ('zero_path', 'camera_psr_keys', 'animated_root_transform', 'path_tracks', 'target_expression'))
    start = time.perf_counter()
    for name, job in jobs:
        try:
            results[name] = job()
        except Exception as error:
            results[name] = {'status': 'FAIL', 'exception': type(error).__name__, 'error': str(error)}
    evidence = output/'numerical_evidence.json'
    result = {'status': 'PASS' if all(case['status']=='PASS' for case in results.values()) else 'FAIL',
              'scope': 'Six-second owned fixtures; numerical refinement, runtime guards and one/six-rig timings. No render or visual acceptance.',
              'position_tolerance_cm': POSITION_TOLERANCE, 'rotation_basis_component_tolerance': BASIS_TOLERANCE,
              'benchmark_note': 'PASS checks execution and diagnostics only; timings have no speed acceptance threshold.',
              'elapsed_ms': (time.perf_counter()-start)*1000,
              'cases': results, 'evidence_path': str(evidence)}
    with evidence.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False, allow_nan=False)
    return result
