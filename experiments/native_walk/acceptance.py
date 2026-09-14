"""Extended native Footsteps measurements; invoke run() on the C4D main thread.

All documents are detached and owned by this call. Results are measurements,
not a declaration that history-dependent native motion passes acceptance.
"""
import importlib.util
import json
import math
from pathlib import Path
import time

import c4d


def _load_probe():
    path = Path(__file__).with_name('probe.py')
    spec = importlib.util.spec_from_file_location('native_walk_probe', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sequence(probe, document, rigs):
    begin = time.perf_counter()
    rows = [probe.sample(document, rigs, frame) for frame in range(181)]
    return rows, (time.perf_counter() - begin) * 1000.0


def _error(rows, reference):
    return max(math.dist(row['position'], reference[int(row['frame'])]['position'])
               for row in rows)


def _loaded_rigs(document):
    """Resolve by native tag/link types within this exact loaded document."""
    rigs = []
    stack = [document.GetFirstObject()]
    while stack:
        node = stack.pop()
        if node is None:
            continue
        stack.extend((node.GetNext(), node.GetDown()))
        motion = node.GetTag(c4d.Tmotioncam)
        if motion is None:
            continue
        source = motion[c4d.TMOTIONCAM_BASE_LINK]
        if source is None or source.GetDocument() != document:
            raise RuntimeError('Reopened Motion Camera source link is invalid')
        align = source.GetTag(c4d.Taligntospline)
        aim = source.GetTag(c4d.Ttargetexpression)
        if align is None or aim is None:
            raise RuntimeError('Reopened source lacks native Align or Target')
        for tag, parameter in ((align, c4d.ALIGNTOSPLINETAG_LINK),
                               (aim, c4d.TARGETEXPRESSIONTAG_LINK)):
            linked = tag[parameter]
            if linked is None or linked.GetDocument() != document:
                raise RuntimeError('Reopened native tag link is invalid')
        rigs.append((source, node, motion))
    if len(rigs) != 1:
        raise RuntimeError('Expected exactly one reopened native camera rig')
    return rigs


def run(output_directory):
    if not c4d.threading.GeIsMainThread():
        raise RuntimeError('Native camera acceptance requires the C4D main thread')
    output = Path(output_directory).resolve()
    output.mkdir(parents=True, exist_ok=False)
    probe = _load_probe()
    result = {'status': 'MEASURED', 'frames': 181, 'fps': 30,
              'note': 'Position errors are measured; native Footsteps may depend on evaluation history.',
              'output_directory': str(output), 'performance': []}

    # ExecutePasses evaluates every rig, though sample reports the first camera.
    for count in (1, 6):
        document, rigs = probe.build(count=count)
        rows, elapsed = _sequence(probe, document, rigs)
        result['performance'].append({'rig_count': count, 'sequential_ms': elapsed,
                                      'ms_per_frame': elapsed / 181.0})

    document, rigs = probe.build()
    reference, elapsed = _sequence(probe, document, rigs)
    repeated, repeat_elapsed = _sequence(probe, document, rigs)
    jumps = [probe.sample(document, rigs, frame) for frame in (90, 30, 150, 60, 90)]
    fresh, fresh_rigs = probe.build()
    fresh90 = probe.sample(fresh, fresh_rigs, 90)
    subframe_document, subframe_rigs = probe.build()
    for frame in range(90):
        probe.sample(subframe_document, subframe_rigs, frame)
    subframe = probe.sample(subframe_document, subframe_rigs, 89.5)
    after_subframe = probe.sample(subframe_document, subframe_rigs, 90)

    # Save an independently prepared sequence, not the random-jump document.
    saved, saved_rigs = probe.build()
    saved_sequence, _ = _sequence(probe, saved, saved_rigs)
    scene_path = output / 'native_walk.c4d'
    if not c4d.documents.SaveDocument(saved, str(scene_path),
                                      c4d.SAVEDOCUMENTFLAGS_DONTADDTORECENTLIST, c4d.FORMAT_C4DEXPORT):
        raise RuntimeError('Saving the owned native rig document failed')
    loaded = c4d.documents.LoadDocument(str(scene_path),
        c4d.SCENEFILTER_OBJECTS | c4d.SCENEFILTER_MATERIALS, None)
    if loaded is None:
        raise RuntimeError('Reopening the owned native rig document failed')
    reopened_rigs = _loaded_rigs(loaded)
    reopened, reopen_elapsed = _sequence(probe, loaded, reopened_rigs)
    result.update({
        'sequential_ms': elapsed,
        'repeat_sequential_ms': repeat_elapsed,
        'repeat_position_error_cm': _error(repeated, reference),
        'random_position_error_cm': _error(jumps, reference),
        'fresh_jump90_error_cm': _error([fresh90], reference),
        'subframe_then90_error_cm': _error([after_subframe], reference),
        'save_reopen_position_error_cm': _error(reopened, saved_sequence),
        'save_reopen_sequential_ms': reopen_elapsed,
        'native_links_reopened': True,
        'scene_path': str(scene_path),
        'samples': {'reference': reference, 'repeated': repeated,
                    'random': jumps, 'fresh90': fresh90, 'subframe89_5': subframe,
                    'after_subframe90': after_subframe, 'saved': saved_sequence,
                    'reopened': reopened},
    })
    evidence = output / 'evidence.json'
    result['evidence_path'] = str(evidence)
    with evidence.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
    return result
