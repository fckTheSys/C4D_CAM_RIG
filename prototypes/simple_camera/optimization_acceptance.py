"""Compare frozen v002 and current runtime during owned stationary-frame edits."""
import hashlib
import io
import json
from pathlib import Path
import runpy
import statistics
import time
import zipfile

import c4d

OLD_SHA256 = 'b12bba1205d1cf2b211c4e0d9adf72804c48f26a0ff7dd4a0db50e9d2815d396'
SOURCE_NAMES = ('motion_math.py', 'path_math.py', 'curve_math.py', 'runtime.py')
TOLERANCE = 1e-5


def _matrix(camera):
    matrix = camera.GetMg()
    return [component for v in (matrix.off, matrix.v1, matrix.v2, matrix.v3)
            for component in (v.x, v.y, v.z)]


def _error(a, b):
    return max(abs(x-y) for x, y in zip(a, b))


def _evaluate(document, root, camera, animation):
    begin = time.perf_counter()
    document.ExecutePasses(None, animation, True, True, c4d.BUILDFLAGS_NONE)
    elapsed = (time.perf_counter()-begin)*1000
    diagnostics = [tag.GetDataInstance().GetString(10699102) for tag in root.GetTags()
                   if tag.GetType() == c4d.Tpython]
    if len(diagnostics) != 2 or any(diagnostics):
        raise RuntimeError('Runtime diagnostic: ' + repr(diagnostics))
    return _matrix(camera), elapsed


def _fixture(builder, source, control):
    document, root, objects, ids = builder['fixture']()
    builder['key'](document, root, ids['Step Length'], [(0, 70), (90, 40), (180, 90)])
    builder['key'](document, root, ids['Shake Frequency'], [(0, .5), (90, 4), (180, 1)])
    if root.FindCTrack(ids[control]) is None:
        value = root[ids[control]]
        builder['key'](document, root, ids[control], [(0, value), (180, value)])
    for tag in root.GetTags():
        if tag.GetType() == c4d.Tpython:
            tag[c4d.TPYTHON_CODE] = source
    document.SetTime(c4d.BaseTime(150, 30))
    clean, _ = _evaluate(document, root, objects[9], True)
    # Standard fixture is airborne at 150 and its keyed gait strength is zero.
    # Enable a live override so amplitude/step-length benchmarks exercise gait.
    root[ids['Walk Strength']] = 1.0
    _evaluate(document, root, objects[9], False)
    _evaluate(document, root, objects[9], False)
    return document, root, objects[9], ids, clean


def run(output_directory):
    if not c4d.threading.GeIsMainThread():
        raise RuntimeError('Optimization acceptance requires the C4D main thread')
    output = Path(output_directory).resolve()
    output.mkdir(parents=True, exist_ok=False)
    folder = Path(__file__).parent
    archive = folder.parents[1] / 'tests/artifacts/simple_camera/package_v002/SimpleCamera_live_edit_fix.zip'
    with zipfile.ZipFile(archive) as package:
        old_source = '\n\n'.join(io.TextIOWrapper(package.open('SimpleCamera/'+name),
                                  encoding='utf-8').read() for name in SOURCE_NAMES)
    old_hash = hashlib.sha256(old_source.encode('utf-8')).hexdigest()
    if old_hash != OLD_SHA256:
        raise RuntimeError('Reference package source hash differs from frozen v002')
    builder = runpy.run_path(str(folder/'builder.py'))
    new_source = builder['source']()
    new_hash = hashlib.sha256(new_source.encode('utf-8')).hexdigest()
    controls = {
        'Pan': [-45, -30, -15, 0, 15, 30, 45, 60],
        'Body Y': [0, 15, 30, 45, 60, 75, 90, 120],
        'Walk Strength': [.1, .25, .4, .55, .7, .85, 1, 1.2],
        'Walk Amplitude': [.25, .5, 1, 1.5, 2, 3, 4, 5],
        'Step Length': [30, 40, 50, 60, 70, 80, 100, 120],
        'Shake Frequency': [.25, .5, 1, 2, 3, 4, 6, 8],
        'Progress': [.1, .2, .3, .4, .5, .6, .75, .9],
    }
    cases = []
    for control, values in controls.items():
        old = _fixture(builder, old_source, control)
        new = _fixture(builder, new_source, control)
        rows = []
        baseline_error = _error(old[4], new[4])
        for index, value in enumerate(values):
            measurements = {}
            # Alternate order to reduce systematic first-run timing bias.
            variants = [('old', old), ('new', new)] if index % 2 == 0 else [('new', new), ('old', old)]
            for label, fixture in variants:
                document, root, camera, ids, clean = fixture
                root[ids[control]] = value
                matrix, elapsed = _evaluate(document, root, camera, False)
                measurements[label] = {'matrix': matrix, 'ms': elapsed}
            rows.append({'value': value, 'old_ms': measurements['old']['ms'],
                         'new_ms': measurements['new']['ms'],
                         'matrix_error': _error(measurements['old']['matrix'], measurements['new']['matrix']),
                         'old_matrix': measurements['old']['matrix'], 'new_matrix': measurements['new']['matrix']})
        restore = {}
        for label, fixture in (('old', old), ('new', new)):
            document, root, camera, ids, clean = fixture
            matrix, _ = _evaluate(document, root, camera, True)
            restore[label] = _error(matrix, clean)
        old_times = [row['old_ms'] for row in rows]
        new_times = [row['new_ms'] for row in rows]
        max_error = max([baseline_error] + [row['matrix_error'] for row in rows])
        cases.append({'control': control, 'passed': max_error <= TOLERANCE and max(restore.values()) <= TOLERANCE,
                      'max_matrix_error': max_error, 'animation_restore_errors': restore,
                      'old_median_ms': statistics.median(old_times), 'old_max_ms': max(old_times),
                      'new_median_ms': statistics.median(new_times), 'new_max_ms': max(new_times),
                      'median_speedup': statistics.median(old_times)/max(statistics.median(new_times), 1e-12),
                      'samples': rows})
    evidence = output/'evidence.json'
    result = {'status': 'PASS' if all(case['passed'] for case in cases) else 'FAIL',
              'scope': 'One six-second detached rig at warmed frame150; animation-disabled scalar edits plus animation restoration. Timings are measured, not acceptance thresholds.',
              'reference_archive': str(archive), 'reference_source_sha256': old_hash,
              'current_source_sha256': new_hash, 'source_join_order': list(SOURCE_NAMES),
              'matrix_tolerance': TOLERANCE, 'cases': cases, 'evidence_path': str(evidence)}
    with evidence.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
    return result
