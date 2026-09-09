"""Host-independent rejection tests; not a substitute for live C4D tests."""
import ast
import math
import os
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def api_function(name, **dependencies):
    tree = ast.parse((ROOT / 'camrig/agent_api.py').read_text(encoding='utf-8'))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    namespace = dict(math=math, os=os, **dependencies)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(ROOT / 'camrig/agent_api.py'), 'exec'), namespace)
    return namespace[name]


class PreflightTests(unittest.TestCase):
    def test_invalid_transform_rejected_before_undo(self):
        mutations = []
        def unexpected_undo(doc):
            mutations.append(True)
            raise AssertionError('Mutation started before validation completed')
        operation = api_function('set_root_transform', resolve_rig=lambda *_: object(),
                                 _preflight=lambda _: None, undo_group=unexpected_undo)
        for bad in [True, float('nan'), float('inf'), '12']:
            with self.subTest(value=bad), self.assertRaisesRegex(ValueError, 'INVALID_TRANSFORM'):
                operation(None, '/Rig', {'position': {'x': 120}, 'rotation_deg': {'y': bad}})
        for transform in [{'position': {'w': 1}}, {'position': []}, {'unknown': 1}]:
            with self.assertRaisesRegex(ValueError, 'INVALID_TRANSFORM'):
                operation(None, '/Rig', transform)
        self.assertEqual(mutations, [])

    def test_scale_confirmation_is_boolean(self):
        operation = api_function('set_root_transform', resolve_rig=lambda *_: object(), _preflight=lambda _: None)
        for confirm in [False, 'true', 1]:
            with self.assertRaisesRegex(ValueError, 'CONFIRMATION_REQUIRED'):
                operation(None, '/Rig', {'scale': {'x': 1, 'y': 1, 'z': 1}, 'confirm': confirm})

    def test_invalid_save_path_does_not_call_c4d(self):
        operation = api_function('save_scene')  # c4d deliberately unavailable
        for path in [None, 1, 'relative.c4d', os.path.abspath('wrong.png')]:
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'INVALID_PATH'):
                operation(None, path)


if __name__ == '__main__':
    unittest.main()
