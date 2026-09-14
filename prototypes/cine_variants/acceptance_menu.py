"""Isolated menu action checks; optionally load an installed menu path."""
import importlib.util
from pathlib import Path
import c4d


def run(menu_path=None):
    path = Path(menu_path) if menu_path else Path(__file__).resolve().parents[2]/'Cine_CAM'/'menu.py'
    spec = importlib.util.spec_from_file_location('cine_pack_menu_test',path)
    menu = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(menu)
    document = c4d.documents.BaseDocument()
    checks = []
    try:
        for mode in range(4):
            root,objects,_ = menu.create(document,mode)
            _,_,ids = menu.inspect(root)
            document.ExecutePasses(None,True,True,True,c4d.BUILDFLAGS_NONE)
            assert root[ids['status']] if mode == 3 else root[ids['status']].endswith('prototype: ready')
            assert menu.inspect(root)[0] == mode
            for destination,expected in (('camera',objects[9 if mode == 3 else 8]),('target',objects[3]),
                    ('motion',objects[(2,10,11,2)[mode]]),('rig',root)):
                assert menu.navigate(document,root,destination) == expected
                assert menu.selected(document) == root
            root[ids['pan']] = 12.
            root[ids['offset_x']] = 15.
            menu.reset(root,'framing')
            assert root[ids['pan']] == root[ids['offset_x']] == 0.
            for key in (('walk_strength' if mode == 3 else 'spring_strength'),'shake_strength','drift_strength'):
                root[ids[key]] = .3
            menu.reset(root,'effects')
            assert all(root[ids[key]]==0. for key in (('walk_strength' if mode == 3 else 'spring_strength'),'shake_strength','drift_strength'))
            root[ids['pan']] = 9.
            root[ids['offset_x']] = 25.
            track = c4d.CTrack(root,ids['pan']);root.InsertTrackSorted(track)
            curve = track.GetCurve();item = curve.AddKey(c4d.BaseTime(0))['key'];item.SetValue(curve,9.)
            try:
                menu.reset(root,'framing')
                raise AssertionError('Reset accepted keyed controls')
            except ValueError:
                pass
            assert root[ids['pan']]==9. and root[ids['offset_x']]==25.
            assert root.FindCTrack(ids['pan'])==track and curve.GetKey(0).GetValue()==9.
            assert 'Hierarchy: OK' in menu.report(root)
        checks.extend(['four create actions', 'navigation from descendants', 'inspector',
                       'framing/effect reset', 'keyed reset rejected before any writes'])
        return {'status':'PASS','menu_path':str(path),'checks':checks,
                'boundary':'owned C4D document; startup command registration not exercised'}
    finally:
        c4d.documents.KillDocument(document)
