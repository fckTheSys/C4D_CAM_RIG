"""Detached QA for names/colors, scene discovery and viewport switching."""
from pathlib import Path
import importlib.util
import c4d


def run(menu_path=None):
    path=Path(menu_path) if menu_path else Path(__file__).resolve().parents[1]/'Cine_CAM/menu.py'
    spec=importlib.util.spec_from_file_location('browser_qa',path)
    menu=importlib.util.module_from_spec(spec);spec.loader.exec_module(menu)
    d=c4d.documents.BaseDocument()
    try:
        rigs=[menu.create(d,mode) for mode in (0,1,1,2,3,3)]
        roots=[r for r,o,i in rigs];cameras=[o[9 if 9 in o and o[9].GetType()==1057516 else 8] for r,o,i in rigs]
        assert len(set(r.GetName() for r in roots))==6,'Duplicate rig names'
        assert len(set(c.GetName() for c in cameras))==6,'Duplicate camera names'
        assert all(r[c4d.ID_BASEOBJECT_USECOLOR]==c4d.ID_BASEOBJECT_USECOLOR_ALWAYS for r in roots)
        assert len(set(str(r[c4d.ID_BASEOBJECT_COLOR]) for r in roots))>1
        plain=c4d.BaseObject(c4d.Ocamera);plain.SetName('Standalone QA');d.InsertObject(plain)
        rows=menu.scene_cameras(d);assert len(rows)==6
        assert len(menu.filter_cameras(rows,'Standalone QA'))==0
        assert menu.filter_cameras(rows,roots[1].GetName())
        selection=d.GetActiveObject()
        for row in rows:
            menu.switch_camera(d,row['id'])
            assert str(d.GetActiveBaseDraw().GetSceneCamera(d).GetGUID())==row['id']
            assert d.GetActiveObject()==selection,'Switch changed object selection'
        menu.switch_camera(d,None);assert d.GetActiveBaseDraw().GetSceneCamera(d)==d.GetActiveBaseDraw().GetEditorCamera()
        browser=menu.CameraBrowser();browser.refresh(d)
        first,second=rows[0]['id'],rows[1]['id']
        d.SetActiveObject(cameras[0])
        assert not browser.choose(first),'Object Manager selection incorrectly enabled live switching'
        browser.sync_active();assert browser.pending==first,'Timer lost pending selection'
        assert menu.active_bundle_camera(d) is None
        assert not browser.move(1);assert browser.pending==second
        assert browser.choose(second,confirm=True)
        assert menu.active_bundle_camera(d)==second
        assert browser.choose(first);assert menu.active_bundle_camera(d)==first
        assert browser.neighbour(-1) is None;assert not browser.move(-1)
        browser.filter(roots[1].GetName());assert len(browser.filtered)==1
        browser.choose(browser.filtered[0]['id']);assert browser.neighbour(1) is None
        browser.filter('no matching camera');assert not browser.filtered and browser.pending is None
        browser.filter('');browser.refresh(d)
        d.GetActiveBaseDraw().SetSceneCamera(plain)
        assert not browser.choose(first),'Foreign camera incorrectly enabled live switching'
        assert d.GetActiveBaseDraw().GetSceneCamera(d)==plain
        target=next(row for row in rows if row['id']==str(cameras[1].GetGUID()))
        assert menu.select_camera_rig(d,target['id'])==roots[1]
        stale=str(cameras[0].GetGUID());cameras[0].Remove()
        try:menu.switch_camera(d,stale);raise AssertionError('Deleted camera accepted')
        except ValueError:pass
        assert len(menu.scene_cameras(d))==5
        return {'pass':True,'rigs':len(rigs),'cameras':6,'checks':'names/colors, bundle-only, search, explicit activation, live switching, arrow boundaries, pending selection, foreign camera, stale handles'}
    finally:c4d.documents.KillDocument(d)
