"""Owned C4D save/reload probe with tag-local import and file-access guards.

This is dependency isolation, not a security sandbox or a clean-machine test.
The wrapper exists only in the uniquely named QA scene, never production rigs.
"""
import ast
import hashlib
import json
from pathlib import Path
import runpy
import uuid

import c4d

FRAMES = (149.25, 0, 90, 37.125, 180, 15.5, 120, 130.75, 89.5, 175, 90)
GUARD_ID = 10699104


def guarded(source):
    # Reject import mechanisms beyond the host and standard-library boundary.
    tree = ast.parse(source)
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add(node.module or '')
    if not imports <= {'c4d', 'math', 'bisect'}:
        raise AssertionError('Unexpected embedded imports: ' + repr(imports))
    return '''import c4d, math, bisect, builtins
_allowed = {'c4d': c4d, 'math': math, 'bisect': bisect}
def _import(name, globals=None, locals=None, fromlist=(), level=0):
    if level or name not in _allowed:
        raise ImportError('Portability guard blocked import: ' + name)
    return _allowed[name]
def _blocked(*args, **kwargs):
    raise RuntimeError('Portability guard blocked file access')
_builtins = dict(vars(builtins))
_builtins.update({'__import__': _import, 'open': _blocked})
_scope = {'__builtins__': _builtins, '__name__': 'ck_isolated_runtime'}
exec(%r, _scope)
# Prove guards actually reject dependencies, without touching global builtins.
for _probe in (lambda: _import('camrig'), lambda: _blocked('unused')):
    try:
        _probe()
        raise AssertionError('Inactive portability guard')
    except (ImportError, RuntimeError):
        pass
def main():
    _scope['op'] = op
    _scope['main']()
    op.GetDataInstance().SetInt32(%d, 1)
''' % (source, GUARD_ID)


def run(output_directory):
    if not c4d.threading.GeIsMainThread():
        raise RuntimeError('Run on the C4D main thread')
    folder = Path(__file__).parent
    builder = runpy.run_path(str(folder / 'builder.py'))
    acceptance = runpy.run_path(str(folder / 'acceptance.py'))
    output = Path(output_directory).resolve()
    output.mkdir(parents=True, exist_ok=True)
    scene = output / ('ck_portability_' + uuid.uuid4().hex + '.c4d')
    owned = []
    try:
        document, root, objects = acceptance['_fixture'](builder)
        owned.append(document)
        baseline = [acceptance['_sample'](document, root, objects, f) for f in FRAMES]
        hashes = []
        for tag in root.GetTags():
            if tag.GetType() == c4d.Tpython:
                source = tag[c4d.TPYTHON_CODE]
                hashes.append(hashlib.sha256(source.encode('utf-8')).hexdigest())
                tag[c4d.TPYTHON_CODE] = guarded(source)
        if not c4d.documents.SaveDocument(document, str(scene),
                c4d.SAVEDOCUMENTFLAGS_DONTADDTORECENTLIST, c4d.FORMAT_C4DEXPORT):
            raise RuntimeError('Save failed')
        reopened = c4d.documents.LoadDocument(str(scene),
            c4d.SCENEFILTER_OBJECTS | c4d.SCENEFILTER_MATERIALS, None)
        if reopened is None:
            raise RuntimeError('Reload failed')
        owned.append(reopened)
        fresh_root, fresh_objects = acceptance['_resolve'](reopened)
        samples = []
        for frame in FRAMES:
            samples.append(acceptance['_sample'](reopened, fresh_root, fresh_objects, frame))
            for tag in fresh_root.GetTags():
                if tag.GetType() == c4d.Tpython:
                    if tag.GetDataInstance().GetInt32(GUARD_ID) != 1:
                        raise AssertionError('Guarded tag did not execute')
        error = max(abs(a-b) for x,y in zip(baseline,samples)
                    for a,b in zip(x['matrix'],y['matrix']))
        result = {'status': 'PASS' if error <= 1e-5 else 'FAIL',
                  'c4d_version': c4d.GetC4DVersion(),
                  'frames': FRAMES, 'max_matrix_component_error': error,
                  'tolerance': 1e-5, 'embedded_sha256': hashes,
                  'camera_type': fresh_objects[9].GetType(),
                  'allowed_runtime_imports': ['c4d', 'math', 'bisect'],
                  'builtin_open_blocked': True, 'guard_self_check': True,
                  'native_links_reloaded': True, 'runtime_diagnostics': [],
                  'scene_path': str(scene),
                  'limitations': ['Same running C4D process; installed plugins remain loaded.',
                    'Tag-local dependency guard is not an operating-system sandbox.',
                    'Requires Redshift camera type 1057516 and enabled Python expressions.',
                    'No clean-machine startup, farm render, or motion-blur test.']}
        evidence = scene.with_suffix('.json')
        result['evidence_path'] = str(evidence)
        with evidence.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
        return result
    finally:
        for document in reversed(owned):
            c4d.documents.KillDocument(document)
