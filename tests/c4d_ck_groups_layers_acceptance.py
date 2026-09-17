"""CK_CAM 0.5.7 groups, service layer, names and verified upgrade.

Run in Cinema 4D on the main thread: run(). Every document is detached and
owned by this probe. The 0.5.6 embedded runtime is rebuilt from git (OLD_REF)
exactly as builder.source() joined it; its SHA256 must match the accepted 0.5.6
digest. Missing git history fails the run: upgrade coverage is mandatory."""
import importlib.util
import math
import os
import subprocess
import tempfile
from pathlib import Path

import c4d

ROOT = Path(__file__).resolve().parents[1]
FRAMES = (0, 15, 45, 90, 125, 150, 180)
TOLERANCE = 1e-4
OLD_REF = '056f977'
OLD_SHA256 = '88b13ae03be446b6ecb3f671e0e89fa5b9657f52d5d6412a4551b43931b7e3e0'
OLD_PARTS = ('prototypes/path_source.py', 'prototypes/look_source.py',
             'prototypes/simple_camera/motion_math.py', 'prototypes/simple_camera/path_math.py',
             'prototypes/simple_camera/curve_math.py', 'prototypes/simple_camera/runtime.py')


def old_runtime_from_git(ref=OLD_REF):
    texts = []
    for part in OLD_PARTS:
        data = subprocess.run(['git', 'show', ref + ':' + part], cwd=str(ROOT), capture_output=True,
                              check=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)).stdout
        texts.append(data.decode('utf-8').replace('\r\n', '\n').replace('\r', '\n'))
    code = '\n\n'.join(texts)
    digest = load().runtime_sha(code)
    if digest != OLD_SHA256:
        raise RuntimeError('Rebuilt 0.5.6 runtime digest mismatch: ' + digest)
    return code


def load():
    path = ROOT/'prototypes'/'simple_camera'/'builder.py'
    spec = importlib.util.spec_from_file_location('ck_groups_builder', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def status(root):
    desc = next(desc for desc, bc in root.GetUserDataContainer() if bc[c4d.DESC_NAME] == 'Status')
    return str(root[desc])


def sample(document, root, frames=FRAMES):
    camera = load().rig_nodes(root)[9]
    rows = []
    for frame in frames:
        document.SetTime(c4d.BaseTime(frame, document.GetFps()))
        document.ExecutePasses(None, True, True, True, c4d.BUILDFLAGS_NONE)
        rows.append((camera.GetMg(), status(root)))
    return rows


def ready(rows):
    bad = [text for _, text in rows if text != 'Ready']
    assert not bad, bad[0]


def error(a, b, transform=None):
    worst = 0.0
    for (ma, _), (mb, _) in zip(a, b):
        if transform is not None:
            ma = transform * ma
        for va, vb in zip((ma.off, ma.v1, ma.v2, ma.v3), (mb.off, mb.v1, mb.v2, mb.v3)):
            worst = max(worst, (va-vb).GetLength())
    return worst


def group(document, name, parent=None, matrix=None):
    node = c4d.BaseObject(c4d.Onull)
    node.SetName(name)
    if parent is None:
        document.InsertObject(node)
    else:
        node.InsertUnderLast(parent)
    if matrix is not None:
        node.SetMg(matrix)
    return node


def nest(document, root, matrices):
    parent = None
    for index, matrix in enumerate(matrices):
        parent = group(document, 'GRP_%d' % index, parent, matrix)
    world = root.GetMg()
    root.Remove()
    root.InsertUnder(parent)
    root.SetMg(world)
    return parent


def transform(offset, hpb):
    matrix = c4d.utils.HPBToMatrix(c4d.Vector(*(math.radians(v) for v in hpb)))
    matrix.off = c4d.Vector(*offset)
    return matrix


def fixture(b):
    document, root, objects, ids = b.fixture()
    return document, root, objects, ids


def layers(document):
    found, stack = [], [document.GetLayerObjectRoot().GetDown()]
    while stack:
        layer = stack.pop()
        while layer is not None:
            found.append(layer.GetName())
            stack.append(layer.GetDown())
            layer = layer.GetNext()
    return found


def run(old_runtime=None):
    b = load()
    results = {}
    old_runtime = old_runtime or old_runtime_from_git()
    assert OLD_SHA256 in b.UPGRADABLE_RUNTIMES and b.runtime_sha(old_runtime) == OLD_SHA256

    def test(name, fn):
        try:
            results[name] = fn() or 'PASS'
        except Exception as failure:
            results[name] = 'FAIL: %s: %s' % (type(failure).__name__, failure)

    def layout():
        document, root, obj, _ = fixture(b)
        try:
            assert root.GetName() == obj[9].GetName() == 'CK_CAM'
            assert obj[3].GetName() == 'CK_CAM_TGT' and obj[10].GetName() == 'CK_CAM_LTGT'
            assert b.names_synced(obj)
            layer = obj[4].GetLayerObject(document)
            assert layer is not None and layer.GetName() == b.LAYER_NAME
            data = layer.GetLayerData(document)
            assert not data['manager'] and not data['view'] and not data['locked']
            assert data['expressions'] and data['animation'] and data['generators']
            assert all(obj[r].GetLayerObject(document) == layer for r in b.SERVICE_ROLES)
            assert all(obj[r].GetLayerObject(document) is None for r in (1, 3, 9, 10))
            b.build(document, 'CK_CAM_B')
            assert layers(document).count(b.LAYER_NAME) == 1
            ready(sample(document, root, (0, 90)))
        finally:
            c4d.documents.KillDocument(document)

    def nested_equivalence():
        base, base_root, _, _ = fixture(b)
        nested, nested_root, _, _ = fixture(b)
        try:
            reference = sample(base, base_root)
            ready(reference)
            outer = nest(nested, nested_root, (transform((300, -40, 900), (35, 10, -5)),
                                               transform((-120, 15, 60), (-80, 0, 20)),
                                               transform((5, 5, 5), (0, 0, 0))))
            placed = sample(nested, nested_root)
            ready(placed)
            same_world = error(reference, placed)
            assert same_world < TOLERANCE, same_world
            # Moving a group afterwards moves the whole camera rigidly.
            top = outer
            while top.GetUp() is not None:
                top = top.GetUp()
            move = transform((-700, 250, 30), (120, -15, 8))
            top.SetMg(move * top.GetMg())
            moved = sample(nested, nested_root)
            ready(moved)
            rigid = error(reference, moved, move)
            assert rigid < TOLERANCE, rigid
            # Taking the rig out of the groups again restores the original result.
            world = nested_root.GetMg()
            nested_root.Remove()
            nested.InsertObject(nested_root)
            nested_root.SetMg(~move * world)
            back = sample(nested, nested_root)
            ready(back)
            restored = error(reference, back)
            assert restored < TOLERANCE, restored
            return {'same_world': same_world, 'rigid_move': rigid, 'unnested': restored}
        finally:
            c4d.documents.KillDocument(base)
            c4d.documents.KillDocument(nested)

    def refused(setup, expected):
        document, root, obj, _ = fixture(b)
        try:
            parent = nest(document, root, (transform((10, 0, 0), (15, 0, 0)),))
            setup(document, parent, root, obj)
            text = sample(document, root, (30,))[0][1]
            assert expected in text, text
            return text
        finally:
            c4d.documents.KillDocument(document)

    def scaled(document, parent, root, obj):
        parent.SetRelScale(c4d.Vector(2))

    def mirrored(document, parent, root, obj):
        parent.SetRelScale(c4d.Vector(-1, 1, 1))

    def keyed(document, parent, root, obj):
        desc = c4d.DescID(c4d.DescLevel(c4d.ID_BASEOBJECT_REL_POSITION, c4d.DTYPE_VECTOR, 0),
                          c4d.DescLevel(c4d.VECTOR_X, c4d.DTYPE_REAL, 0))
        track = c4d.CTrack(parent, desc)
        parent.InsertTrackSorted(track)
        track.GetCurve().AddKey(c4d.BaseTime(0))

    def expression(document, parent, root, obj):
        tag = parent.MakeTag(c4d.Tpython)
        tag.SetName('Driver')

    def generator(document, parent, root, obj):
        cube = c4d.BaseObject(c4d.Ocube)
        document.InsertObject(cube)
        parent.Remove()
        parent.InsertUnder(cube)

    def layer_off(document, parent, root, obj):
        layer = obj[4].GetLayerObject(document)
        data = layer.GetLayerData(document)
        data['expressions'] = False
        layer.SetLayerData(document, data)

    def annotated():
        document, root, obj, _ = fixture(b)
        try:
            parent = nest(document, root, (transform((10, 0, 0), (15, 0, 0)),))
            parent.MakeTag(1030659)
            obj[2].GetUp()  # internal path is under root, so the group is its ancestor
            ready(sample(document, root, (0, 90)))
        finally:
            c4d.documents.KillDocument(document)

    def own_layer_kept():
        document, root, obj, _ = fixture(b)
        try:
            mine = c4d.documents.LayerObject()
            mine.SetName('L_MINE')
            mine.InsertUnder(document.GetLayerObjectRoot())
            obj[5][c4d.ID_LAYER_LINK] = mine
            for node in b.service_nodes(obj):
                if node != obj[5]:
                    node[c4d.ID_LAYER_LINK] = None
            b.assign_layer(document, obj)
            assert obj[5].GetLayerObject(document) == mine
            assert obj[4].GetLayerObject(document).GetName() == b.LAYER_NAME
        finally:
            c4d.documents.KillDocument(document)

    def save_reopen():
        document, root, _, _ = fixture(b)
        folder = tempfile.mkdtemp(prefix='ck-groups-')
        path = os.path.join(folder, 'nested.c4d')
        loaded = None
        try:
            nest(document, root, (transform((50, 0, 20), (40, 0, 0)), transform((0, 30, 0), (0, 10, 0))))
            before = sample(document, root)
            ready(before)
            assert c4d.documents.SaveDocument(document, path, c4d.SAVEDOCUMENTFLAGS_DONTADDTORECENTLIST,
                                              c4d.FORMAT_C4DEXPORT)
            loaded = c4d.documents.LoadDocument(path, c4d.SCENEFILTER_OBJECTS | c4d.SCENEFILTER_MATERIALS)
            copy = next(node for node in b._walk(loaded.GetFirstObject())
                        if node.GetDataInstance().GetInt32(b.ROLE_ID) == 1)
            after = sample(loaded, copy)
            ready(after)
            assert layers(loaded).count(b.LAYER_NAME) == 1
            assert b.rig_nodes(copy)[4].GetLayerObject(loaded).GetName() == b.LAYER_NAME
            worst = error(before, after)
            assert worst < TOLERANCE, worst
            return {'max_error': worst}
        finally:
            c4d.documents.KillDocument(document)
            if loaded is not None:
                c4d.documents.KillDocument(loaded)
            try:
                os.remove(path)
                os.rmdir(folder)
            except OSError:
                pass

    def downgrade(document, root, obj):
        for tag in b.runtime_tags(root):
            tag[c4d.TPYTHON_CODE] = old_runtime
        for node in b.service_nodes(obj):
            node[c4d.ID_LAYER_LINK] = None

    def upgrade_identical():
        document, root, obj, _ = fixture(b)
        try:
            downgrade(document, root, obj)
            before = sample(document, root)
            ready(before)
            report = b.upgrade(document, root)
            assert report['changed'] and report['reference'] == 'in_place', report
            assert report['max_error'] < TOLERANCE and report['live_error'] < TOLERANCE, report
            assert any(f in report['frames'] for f in (89, 91)), report['frames']  # key neighbours sampled
            current = b.runtime_sha(b.source())
            assert all(b.runtime_sha(t[c4d.TPYTHON_CODE]) == current for t in b.runtime_tags(root))
            assert obj[4].GetLayerObject(document).GetName() == b.LAYER_NAME
            after = sample(document, root)
            ready(after)
            assert error(before, after) < TOLERANCE
            assert document.DoUndo()
            old = b.runtime_sha(old_runtime)
            root = next(n for n in b._walk(document.GetFirstObject()) if n.GetDataInstance().GetInt32(b.ROLE_ID) == 1)
            assert all(b.runtime_sha(t[c4d.TPYTHON_CODE]) == old for t in b.runtime_tags(root))
            assert b.upgrade(document, root)['changed']
            assert not b.upgrade(document, root)['changed']
            return {'max_error': report['max_error'], 'live_error': report['live_error'],
                    'frames': len(report['frames'])}
        finally:
            c4d.documents.KillDocument(document)

    def upgrade_nested_old():
        document, root, obj, _ = fixture(b)
        try:
            downgrade(document, root, obj)
            nest(document, root, (transform((100, 0, 0), (30, 0, 0)),))
            text = sample(document, root, (30,))[0][1]
            assert 'top-level' in text, text
            reference = sample_top_level(document, root)
            report = b.upgrade(document, root)
            assert report['changed'] and report['reference'] == 'top_level_copy', report
            upgraded = sample(document, root)
            ready(upgraded)
            worst = error(reference, upgraded)
            assert worst < TOLERANCE and report['max_error'] < TOLERANCE, (worst, report)
            return {'status_before': text, 'max_error': report['max_error']}
        finally:
            c4d.documents.KillDocument(document)

    def sample_top_level(document, root):
        clone = document.GetClone(c4d.COPYFLAGS_NONE)
        try:
            copied = list(b._walk(clone.GetFirstObject()))[b._index(document, root)]
            world = copied.GetMg()
            copied.Remove()
            clone.InsertObject(copied)
            copied.SetMg(world)
            rows = sample(clone, copied)
            ready(rows)
            return rows
        finally:
            c4d.documents.KillDocument(clone)

    def refuse_upgrade(document, root, expected):
        code = [t[c4d.TPYTHON_CODE] for t in b.runtime_tags(root)]
        try:
            b.upgrade(document, root)
        except ValueError as failure:
            assert expected in str(failure), str(failure)
            assert [t[c4d.TPYTHON_CODE] for t in b.runtime_tags(root)] == code, 'Live rig changed'
            return str(failure)
        raise AssertionError('Upgrade was not refused')

    def upgrade_changed_camera_refused():
        document, root, obj, ids = fixture(b)
        original = b.source
        try:
            downgrade(document, root, obj)
            ready(sample(document, root, (0, 90)))
            # A runtime that shifts Height by 0.01 cm must fail the comparison.
            b.source = lambda: original().replace("read('Height',t)", "(read('Height',t)+0.01)")
            assert b.runtime_sha(b.source()) != b.runtime_sha(original())
            return refuse_upgrade(document, root, 'changes the camera')
        finally:
            b.source = original
            c4d.documents.KillDocument(document)

    def upgrade_broken_rig_refused():
        document, root, obj, ids = fixture(b)
        try:
            downgrade(document, root, obj)
            root[ids['Target']] = None  # World Target mode without a target: not Ready at top level
            return refuse_upgrade(document, root, 'fix it first')
        finally:
            c4d.documents.KillDocument(document)

    def upgrade_nested_broken_refused():
        document, root, obj, ids = fixture(b)
        try:
            downgrade(document, root, obj)
            root[ids['Target']] = None
            nest(document, root, (transform((100, 0, 0), (30, 0, 0)),))
            return refuse_upgrade(document, root, 'even outside its groups')
        finally:
            c4d.documents.KillDocument(document)

    def upgrade_live_mismatch_undone():
        document, root, obj, _ = fixture(b)
        original = b.check_live
        try:
            downgrade(document, root, obj)
            old = b.runtime_sha(old_runtime)
            def mismatch(*args, **kwargs):
                raise ValueError('Live upgrade differs from the verified copy (injected)')
            b.check_live = mismatch
            try:
                b.upgrade(document, root)
            except ValueError as failure:
                assert 'injected' in str(failure)
            else:
                raise AssertionError('Live mismatch ignored')
            root = next(n for n in b._walk(document.GetFirstObject()) if n.GetDataInstance().GetInt32(b.ROLE_ID) == 1)
            assert all(b.runtime_sha(t[c4d.TPYTHON_CODE]) == old for t in b.runtime_tags(root)), 'Not undone'
            return 'undone'
        finally:
            b.check_live = original
            c4d.documents.KillDocument(document)

    def unknown_refused():
        document, root, obj, _ = fixture(b)
        try:
            for tag in b.runtime_tags(root):
                tag[c4d.TPYTHON_CODE] = tag[c4d.TPYTHON_CODE] + '\n# local edit\n'
            try:
                b.upgrade(document, root)
            except ValueError as failure:
                assert 'Unknown embedded' in str(failure)
                return 'refused'
            raise AssertionError('Unknown runtime was overwritten')
        finally:
            c4d.documents.KillDocument(document)

    def panel():
        spec = importlib.util.spec_from_file_location('ck_groups_menu', ROOT/'Cine_CAM'/'menu.py')
        menu = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(menu)
        document = c4d.documents.BaseDocument()
        document.SetFps(30)
        try:
            first, obj, _ = menu.create(document, 3)
            second, _, _ = menu.create(document, 3)
            assert (first.GetName(), second.GetName()) == ('CK_CAM_001', 'CK_CAM_002')
            assert obj[9].GetName() == 'CK_CAM_001' and layers(document).count(b.LAYER_NAME) == 1
            first.SetName('CAM_POV3_450-734')
            document.SetActiveObject(obj[9])
            menu.sync_names(menu.selected_ck(document))
            assert obj[9].GetName() == 'CAM_POV3_450-734' and obj[3].GetName() == 'CAM_POV3_450-734_TGT'
            assert document.DoUndo() and obj[9].GetName() == 'CK_CAM_001'
            assert 'already current' in menu.upgrade_ck(first)
            rows = menu.scene_cameras(document)
            assert sorted(row['label'] for row in rows) == ['CAM_POV3_450-734 / CK_CAM_001', 'CK_CAM_002'], rows
            for tag in b.runtime_tags(second):
                tag[c4d.TPYTHON_CODE] = old_runtime
            assert 'upgraded to CK_CAM ' + b.VERSION in menu.upgrade_ck(second)
        finally:
            c4d.documents.KillDocument(document)

    test('layout, names and one shared layer', layout)
    test('panel create, sync names and upgrade', panel)
    test('nested groups equal top-level and move rigidly', nested_equivalence)
    test('group scale refused', lambda: refused(scaled, 'scale 1'))
    test('group mirror refused', lambda: refused(mirrored, 'scale 1'))
    test('animated group refused', lambda: refused(keyed, 'transform keys'))
    test('expression on group refused', lambda: refused(expression, "expression tag 'Driver'"))
    test('non-Null group refused', lambda: refused(generator, 'plain Null'))
    test('disabled layer expressions reported', lambda: refused(layer_off, "Layer 'L_CAM_RIG'"))
    test('annotation on group allowed', annotated)
    test('user layer choice kept', own_layer_kept)
    test('nested rig save/reopen', save_reopen)
    test('unknown runtime not overwritten', unknown_refused)
    test('0.5.6 upgrade identical with Undo', upgrade_identical)
    test('0.5.6 rig in group matches its top-level copy', upgrade_nested_old)
    test('upgrade that moves the camera refused', upgrade_changed_camera_refused)
    test('upgrade of a broken rig refused', upgrade_broken_rig_refused)
    test('upgrade of a broken grouped rig refused', upgrade_nested_broken_refused)
    test('live mismatch undone', upgrade_live_mismatch_undone)
    return results
