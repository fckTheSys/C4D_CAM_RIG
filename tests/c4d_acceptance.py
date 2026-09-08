"""Run run() on Cinema 4D's main thread; writes only isolated test artifacts."""
import importlib.util
import json
import math
from pathlib import Path
import sys
import traceback
import c4d

ROOT = Path(__file__).resolve().parents[1]

def run():
    alias = 'camrig_acceptance'
    for key in list(sys.modules):
        if key == alias or key.startswith(alias + '.'):
            del sys.modules[key]
    spec = importlib.util.spec_from_file_location(alias, ROOT / 'camrig/__init__.py', submodule_search_locations=[str(ROOT / 'camrig')])
    pkg = importlib.util.module_from_spec(spec)
    sys.modules[alias] = pkg
    spec.loader.exec_module(pkg)
    cmds = importlib.import_module(alias + '.commands')
    rt = importlib.import_module(alias + '.tag_embedded')
    cfg = importlib.import_module(alias + '.config')
    ss = importlib.import_module(alias + '.scene_support')
    reset = importlib.import_module(alias + '.rig_reset')
    assemble = importlib.import_module(alias + '.rig_assemble')
    diag = importlib.import_module(alias + '.diagnostics')
    doc = c4d.documents.BaseDocument()
    doc.SetDocumentName('CamRig 1.6 automated acceptance')
    c4d.documents.InsertBaseDocument(doc)
    c4d.documents.SetActiveDocument(doc)
    rig = assemble.build_cam_rig(doc)
    objs = rt.get_rig_objects(cmds.find_circle(rig))
    ids = cmds.ud_map(rig)
    records = []
    output=ROOT/'tests/artifacts'
    output.mkdir(exist_ok=True)

    def test(name, fn):
        try:
            details = fn()
            records.append({'test': name, 'status': 'PASS', 'details': details})
        except Exception:
            records.append({'test': name, 'status': 'FAIL', 'error': traceback.format_exc()})

    def check(value, message='assertion failed'):
        if not value:
            raise AssertionError(message)

    def near(a, b, tol=1e-6):
        error = (a-b).GetLength() if isinstance(a, c4d.Vector) else abs(a-b)
        check(error <= tol, 'error %s > %s: %s != %s' % (error, tol, a, b))

    def evaluate(frame=0):
        doc.SetTime(c4d.BaseTime(frame, doc.GetFps()))
        doc.ExecutePasses(None, True, True, True, c4d.BUILDFLAGS_NONE)

    def set_ud(**values):
        for key, value in values.items():
            rig[ids[key.replace('_', ' ')]] = value

    def curve(node, desc, pairs):
        track = c4d.CTrack(node, desc)
        node.InsertTrackSorted(track)
        cv = track.GetCurve()
        for frame, value in pairs:
            key = cv.AddKey(c4d.BaseTime(frame, doc.GetFps()))['key']
            key.SetValue(cv, value)
            key.SetInterpolation(cv, c4d.CINTERPOLATION_LINEAR)
        return track

    def orbit():
        for angle in [-1080., -720., -10., 0., 350., 360., 370., 1080.]:
            set_ud(Orbit=angle)
            evaluate()
            near(objs.align[c4d.ALIGNTOSPLINETAG_POSITION], (angle%360)/360)
            near(rig[ids['Orbit']], angle)
        track = curve(rig, ids['Orbit'], [(0,0.),(90,1080.),(150,-720.)])
        for frame in [0,30,60,90,150,60,60,1,149]:
            evaluate(frame)
            near(objs.align[c4d.ALIGNTOSPLINETAG_POSITION], (rig[ids['Orbit']]%360)/360)
        check([track.GetCurve().GetKey(i).GetValue() for i in range(3)] == [0.,1080.,-720.])
        track.Remove()
        return 'Signed values and original key values retained; repeated/random seeks.'
    test('orbit and keyframes', orbit)

    def plane():
        rig.SetRelPos(c4d.Vector(100,200,300))
        rig.SetRelRot(c4d.Vector(.4,.2,.1))
        before = objs.target_a.GetMg().off
        set_ud(Center_X=12.,Height=250.,Center_Z=-42.,Plane_Heading=30.,Plane_Tilt=45.,Plane_Bank=12.)
        evaluate()
        near(objs.circle.GetMg().off, rig.GetMg()*c4d.Vector(12,250,-42))
        near(objs.target_a.GetMg().off, before)
        near(objs.circle.GetRelRot(), c4d.Vector(*map(math.radians,(30,45,12))))
        center=c4d.BaseObject(c4d.Onull)
        center.SetName('Independent Orbit Center')
        doc.InsertObject(center)
        center.SetRelPos(c4d.Vector(750,-200,120))
        set_ud(Orbit_Center=center)
        evaluate()
        near(objs.circle.GetMg().off, center.GetMg().off+rig.GetMg().MulV(c4d.Vector(12,250,-42)))
        pose=objs.circle.GetMg()
        center.SetRelRot(c4d.Vector(1,.7,.4))
        center.SetRelScale(c4d.Vector(2,3,4))
        evaluate()
        near(objs.circle.GetMg().v1,pose.v1)
        near(objs.circle.GetMg().off,pose.off)
        set_ud(Orbit_Center=None)
        return 'External position only; root-space offset and HPB; targets stationary.'
    test('orbit plane and external center', plane)

    def focus():
        set_ud(Aim_Offset_X=25.,Aim_Offset_Y=70.,Aim_Offset_Z=-15.,Focus_Mode=1)
        for blend in [0.,100.,50.]:
            set_ud(Target_Blend=blend)
            evaluate()
            expected=objs.target_a.GetMg().off+(objs.target_b.GetMg().off-objs.target_a.GetMg().off)*(blend/100)
            expected+=rig.GetMg().MulV(c4d.Vector(25,70,-15))
            near(objs.look_target.GetMg().off,expected)
            near(objs.fx[rt.camera_focus_id(objs.fx)],rt.focus_depth(objs.fx.GetMg(),expected))
        set_ud(Offset_X=45.,Offset_Y=123.,Rot_H=12.,Rot_P=5.,Shake_Enable=True,Drift_Pos=12.,Drift_Rot=2.)
        for frame in [3,12,49,3,3,50,1]:
            evaluate(frame)
            near(objs.fx[rt.camera_focus_id(objs.fx)],rt.focus_depth(objs.fx.GetMg(),objs.look_target.GetMg().off))
        set_ud(Use_Target=False,Focus_Distance=456.)
        evaluate()
        near(objs.fx[rt.camera_focus_id(objs.fx)],456.)
        target=c4d.BaseObject(c4d.Onull)
        target.SetName('Independent Focus Target')
        doc.InsertObject(target)
        target.SetMg(c4d.Matrix(off=objs.fx.GetMg().off-objs.fx.GetMg().v3*100))
        set_ud(Focus_Mode=2,Focus_Target=target)
        evaluate()
        near(objs.fx[rt.camera_focus_id(objs.fx)],1.)
        set_ud(Focus_Target=objs.fx)
        evaluate()
        near(objs.fx[rt.camera_focus_id(objs.fx)],456.)
        check('rejected' in diag.inspect_rig(doc,rig)[1])
        set_ud(Focus_Target=None)
        return 'Same-frame FX optical depth, missing/cyclic fallback, behind-camera clamp.'
    test('independent focus and aim', focus)

    def scaled_focus():
        set_ud(Focus_Mode=1,Use_Target=True,Focus_Offset=35.)
        rig.SetRelScale(c4d.Vector(2))
        evaluate(15)
        expected=rt.focus_depth(objs.fx.GetMg(),objs.look_target.GetMg().off,35.)
        near(objs.fx[rt.camera_focus_id(objs.fx)],expected)
        near((objs.focus.GetMg().off-objs.fx.GetMg().off).GetLength(),expected)
        rig.SetRelScale(c4d.Vector(1))
        set_ud(Focus_Offset=0.)
        return 'Focus Offset and visual focus control agree at scaled root.'
    test('scaled root autofocus',scaled_focus)

    def zero_and_reset():
        nonlocal rig, objs, ids
        rig_name = rig.GetName()
        root_matrix=rig.GetMg()
        external=c4d.BaseObject(c4d.Onull)
        doc.InsertObject(external)
        set_ud(Orbit_Center=external,Radius=0.)
        evaluate()
        check(all(math.isfinite(v) for axis in (objs.fx.GetMg().off,objs.fx.GetMg().v1,objs.fx.GetMg().v2,objs.fx.GetMg().v3) for v in (axis.x,axis.y,axis.z)))
        with ss.undo_group(doc):
            ss.add_undo(doc,c4d.UNDOTYPE_CHANGE,rig)
            reset.reset_rig_to_defaults(rig)
        near(rig.GetMg().off,root_matrix.off)
        check(rig[ids['Orbit Center']]==external)
        check(rig[ids['Height']]==0.)
        check(doc.DoUndo())
        rig = doc.SearchObject(rig_name)
        objs = rt.get_rig_objects(cmds.find_circle(rig))
        ids = cmds.ud_map(rig)
        near(rig[ids['Radius']],0.)
        check(doc.DoRedo())
        rig = doc.SearchObject(rig_name)
        objs = rt.get_rig_objects(cmds.find_circle(rig))
        ids = cmds.ud_map(rig)
        set_ud(Orbit_Center=None)
        return 'Finite zero-radius pose; Reset preserves link/root; Undo and Redo.'
    test('zero radius reset undo redo',zero_and_reset)

    def break_guard():
        set_ud(Height=4.)
        before=[t[c4d.TPYTHON_CODE] for t in cmds.runtime_tags(objs.circle)]
        try:
            cmds.break_preflight(rig)
        except ValueError as exc:
            check('Height' in str(exc))
        else:
            raise AssertionError('Break allowed unsupported Height')
        check(before==[t[c4d.TPYTHON_CODE] for t in cmds.runtime_tags(objs.circle)])
        set_ud(Height=0.)
    test('Break guard is nonmutating',break_guard)

    def legacy():
        old=assemble.build_cam_rig(doc)
        old.SetName('Legacy Upgrade Fixture')
        oo=rt.get_rig_objects(cmds.find_circle(old))
        template=json.loads((ROOT/'camrig/ud_template.json').read_text(encoding='utf-8'))
        newnames={g['name'] for g in template['groups'] if g['name'] in ('Orbit Rig','Aim Offset','Focus','Spring')}
        for g in template['groups']:
            if g['name'] in newnames:
                newnames.update(p['name'] for p in g['params'])
        for desc,bc in reversed(old.GetUserDataContainer()):
            if bc[c4d.DESC_NAME] in newnames:
                old.RemoveUserData(desc)
        old.GetDataInstance().RemoveData(cfg.META_ID)
        tags=cmds.runtime_tags(oo.circle)
        late=next(t for t in tags if t.GetName()==cfg.FOCUS_TAG_NAME)
        late.Remove()
        early=next(t for t in tags if t.GetName()=='CamRig Runtime 1.5')
        spring_tag=next(t for t in tags if t.GetName()==cfg.SPRING_TAG_NAME)
        spring_tag.Remove()
        if oo.spring is not None:
            oo.cam.InsertUnder(oo.offset)
            oo.spring.Remove()
        original=(ROOT/'camrig/legacy_140.txt').read_text(encoding='utf-8')
        early[c4d.TPYTHON_CODE]=original
        early.SetName('Python')
        for t in (early,oo.align,oo.target_expr): ss.set_priority(t,0)
        oi=cmds.ud_map(old)
        old[oi['Focal Length']]=62.
        old[oi['Shake Enable']]=True
        old[oi['Drift Pos']]=3.
        oo.circle.SetRelPos(c4d.Vector(20,80,-10))
        oo.circle.SetRelRot(c4d.Vector(.2,.3,.1))
        track=curve(old,oi['Orbit'],[(0,15.),(60,300.)])
        cv=track.GetCurve()
        for index in range(cv.GetKeyCount()):
            key=cv.GetKey(index)
            key.SetInterpolation(cv,c4d.CINTERPOLATION_SPLINE)
            key.SetTimeLeft(cv,c4d.BaseTime(-3,doc.GetFps()))
            key.SetTimeRight(cv,c4d.BaseTime(4,doc.GetFps()))
            key.SetValueLeft(cv,-12.)
            key.SetValueRight(cv,17.)
        def key_state(track):
            curve=track.GetCurve()
            return [(k.GetTime().Get(),k.GetValue(),k.GetInterpolation(),k.GetTimeLeft().Get(),k.GetTimeRight().Get(),k.GetValueLeft(),k.GetValueRight()) for k in [curve.GetKey(i) for i in range(curve.GetKeyCount())]]
        original_keys=key_state(track)
        def snapshot():
            return [(cam.GetMg(),cam[rt.camera_focal_id(cam)]) for cam in (oo.cam,oo.fx)]
        frames=[0,12,30,60]
        before={}
        for f in frames:
            evaluate(f)
            evaluate(f) # legacy equal priorities can require a settling evaluation
            before[f]=snapshot()
        identity=str(track.GetDescriptionID())
        check(c4d.documents.SaveDocument(doc,str(output/'legacy-before-upgrade.c4d'),c4d.SAVEDOCUMENTFLAGS_DONTADDTORECENTLIST,c4d.FORMAT_C4DEXPORT))
        changed,message=cmds.upgrade_rig(doc,old)
        check(changed,message)
        check(cmds.ud_map(old)['Orbit']==oi['Orbit'])
        check(str(old.FindCTrack(oi['Orbit']).GetDescriptionID())==identity)
        check(key_state(old.FindCTrack(oi['Orbit']))==original_keys,'key tangent data changed')
        maxpos=maxrot=maxfocal=0.
        for f in frames:
            evaluate(f)
            for (matrix,focal),(baseline,bf) in zip(snapshot(),before[f]):
                maxpos=max(maxpos,(matrix.off-baseline.off).GetLength())
                delta=~baseline*matrix
                angle=math.acos(max(-1.,min(1.,(delta.v1.x+delta.v2.y+delta.v3.z-1)/2)))
                maxrot=max(maxrot,angle)
                maxfocal=max(maxfocal,abs(focal-bf))
        check(maxpos<=1e-4 and maxrot<=1e-5 and maxfocal<=1e-4,str((maxpos,maxrot,maxfocal)))
        check(not cmds.upgrade_rig(doc,old)[0])
        check(doc.DoUndo())
        old=doc.SearchObject('Legacy Upgrade Fixture')
        oo=rt.get_rig_objects(cmds.find_circle(old))
        check(ss.schema_version(old)==0)
        check(cmds.normalized_source(cmds.runtime_tags(oo.circle)[0][c4d.TPYTHON_CODE])==cmds.normalized_source(original))
        check(doc.DoRedo())
        old=doc.SearchObject('Legacy Upgrade Fixture')
        check(ss.schema_version(old)==cfg.SCHEMA_VERSION)
        return {'max_position_error':maxpos,'max_orientation_radians':maxrot,'max_focal_error':maxfocal,'note':'Legacy baseline evaluated twice to settle equal-priority tags.'}
    test('legacy Upgrade matrices and Undo',legacy)

    def upgrade_rejection():
        candidate=assemble.build_cam_rig(doc)
        candidate.SetName('Rejected Upgrade Fixture')
        co=rt.get_rig_objects(cmds.find_circle(candidate))
        tags=cmds.runtime_tags(co.circle)
        spring=next(t for t in tags if t.GetName()==cfg.SPRING_TAG_NAME)
        early=spring
        early[c4d.TPYTHON_CODE]=early[c4d.TPYTHON_CODE]+'\n# user customization\n'
        def reject(expected):
            before=[(str(d),bc[c4d.DESC_NAME]) for d,bc in candidate.GetUserDataContainer()]
            code=early[c4d.TPYTHON_CODE]
            try: cmds.upgrade_rig(doc,candidate)
            except ValueError as exc: check(expected in str(exc),str(exc))
            else: raise AssertionError('Unsupported migration accepted')
            check(before==[(str(d),bc[c4d.DESC_NAME]) for d,bc in candidate.GetUserDataContainer()])
            check(early[c4d.TPYTHON_CODE]==code)
        reject('changed')
        # This disposable fixture is not part of the persistence acceptance scene.
        candidate.Remove()
        return 'Edited code, scale, animated circle: refused without partial UD/code changes.'
    test('Upgrade refusal is atomic',upgrade_rejection)

    def standard_camera():
        standard=assemble.build_cam_rig(doc)
        standard.SetName('Standard Camera Rig')
        so=rt.get_rig_objects(cmds.find_circle(standard))
        cam=c4d.BaseObject(c4d.Ocamera)
        cam.SetName('RS_CAM_standard')
        cam.InsertUnder(so.offset)
        fx=c4d.BaseObject(c4d.Ocamera)
        fx.SetName('FX_CAM_standard')
        fx.InsertUnder(cam)
        so.focus.InsertUnder(fx)
        so.target_expr.Remove()
        cam.InsertTag(so.target_expr)
        so.cam.Remove()
        si=cmds.ud_map(standard)
        standard[si['Focal Length']]=77.
        standard[si['Focus Mode']]=1
        evaluate(11)
        near(cam[c4d.CAMERA_FOCUS],77.)
        near(fx[c4d.CAMERA_FOCUS],77.)
        near(fx[c4d.CAMERAOBJECT_TARGETDISTANCE],rt.focus_depth(fx.GetMg(),so.look_target.GetMg().off))
        standard[si['Focus Mode']]=0
        standard[si['Focus Distance']]=800.
        evaluate()
        near(fx[c4d.CAMERAOBJECT_TARGETDISTANCE],800.)
        return 'Native standard focal and target distance, auto/manual focus.'
    test('standard camera',standard_camera)

    def creation_undo():
        count=lambda:len(list(cmds.walk(doc.GetFirstObject())))
        before=count()
        layers=lambda:len(list(cmds.walk(doc.GetLayerObjectRoot().GetDown())))
        layer_count=layers()
        with ss.undo_group(doc):
            created=assemble.build_cam_rig(doc,record_undo=True)
        check(count()>before)
        check(doc.DoUndo())
        check(count()==before)
        check(layers()==layer_count)
        check(doc.DoRedo())
        check(count()>before)
        return 'Entire created hierarchy and new layer undo in one action.'
    test('Create Undo including layers',creation_undo)

    def repair():
        repaired=assemble.build_cam_rig(doc)
        repaired.SetName('Repair Fixture')
        ro=rt.get_rig_objects(cmds.find_circle(repaired))
        next(t for t in cmds.runtime_tags(ro.circle) if t.GetName()==cfg.FOCUS_TAG_NAME).Remove()
        ro.align.Remove()
        ok,message=diag.repair_selected_rig(doc,repaired)
        check(ok,message)
        ro=rt.get_rig_objects(cmds.find_circle(repaired))
        check(ro.align is not None and len(cmds.runtime_tags(ro.circle))==3)
        check(diag.inspect_rig(doc,repaired)[0])
        check(doc.DoUndo())
        repaired=doc.SearchObject('Repair Fixture')
        ro=rt.get_rig_objects(cmds.find_circle(repaired))
        check(ro.align is None and len(cmds.runtime_tags(ro.circle))==2)
        check(doc.DoRedo())
        return 'Missing Align/late stage repaired and undone as one operation.'
    test('Repair Undo',repair)

    def rollback_scope():
        probe=c4d.BaseObject(c4d.Onull)
        probe.SetName('Rollback Probe')
        doc.InsertObject(probe)
        with ss.undo_group(doc):
            ss.add_undo(doc,c4d.UNDOTYPE_CHANGE,probe)
            probe.SetRelPos(c4d.Vector(10,0,0))
        try:
            with ss.undo_group(doc):
                raise RuntimeError('before mutation')
        except RuntimeError: pass
        near(doc.SearchObject('Rollback Probe').GetRelPos(),c4d.Vector(10,0,0))
        try:
            with ss.undo_group(doc):
                ss.add_undo(doc,c4d.UNDOTYPE_CHANGE,probe)
                probe.SetRelPos(c4d.Vector(20,0,0))
                raise RuntimeError('after mutation')
        except RuntimeError: pass
        near(doc.SearchObject('Rollback Probe').GetRelPos(),c4d.Vector(10,0,0))
        return 'Failed command rolls back only its own recorded changes; earlier user Undo untouched.'
    test('exception rollback boundaries',rollback_scope)

    def multiple():
        translator=c4d.AliasTrans()
        check(translator.Init(doc))
        clone=rig.GetClone(c4d.COPYFLAGS_NONE,translator)
        translator.Translate(True)
        doc.InsertObject(clone)
        clone.SetName('Cloned Rig')
        clone_objs=rt.get_rig_objects(cmds.find_circle(clone))
        clone_ids=cmds.ud_map(clone)
        check(clone[clone_ids['Target A']]==clone_objs.target_a)
        doc.SetActiveObject(clone_objs.fx,c4d.SELECTION_NEW)
        check(cmds.choose_rig(doc)==clone)
        cmds.select_part(doc,clone,'camera')
        check(doc.GetActiveBaseDraw().GetSceneCamera(doc)==clone_objs.fx)
        doc.SetActiveObject(rig,c4d.SELECTION_NEW)
        doc.SetActiveObject(clone,c4d.SELECTION_ADD)
        try: cmds.choose_rig(doc)
        except ValueError: pass
        else: raise AssertionError('Ambiguous selection silently chose one rig')
        return 'Clone links remapped; descendant selection and FX viewport; ambiguity rejected.'
    test('multiple rigs navigation clone',multiple)

    def turn_demos():
        for label,end,x in [('Three Forward Turns',1080.,-1500),('Two Reverse Turns',-720.,1500)]:
            demo=assemble.build_cam_rig(doc)
            demo.SetName(label)
            demo.SetRelPos(c4d.Vector(x,0,0))
            di=cmds.ud_map(demo)
            do=rt.get_rig_objects(cmds.find_circle(demo))
            curve(demo,di['Orbit'],[(0,0.),(150,end)])
            curve(demo,di['Height'],[(0,0.),(150,250.)])
            for frame in range(151):
                evaluate(frame)
                near(demo[di['Orbit']],end*frame/150,1e-5)
                near(do.align[c4d.ALIGNTOSPLINETAG_POSITION],(demo[di['Orbit']]%360)/360)
            for frame in [100,1,149,0,0]:
                evaluate(frame)
                near(demo[di['Orbit']],end*frame/150,1e-5)
        doc.SetMaxTime(c4d.BaseTime(150,doc.GetFps()))
        doc.SetLoopMaxTime(c4d.BaseTime(150,doc.GetFps()))
        return 'Persisted forward/reverse demo rigs; every frame 0..150 evaluated.'
    test('sequential forward and reverse demo scenes',turn_demos)

    def persistence():
        path=output/'camrig-1.6-acceptance.c4d'
        check(c4d.documents.SaveDocument(doc,str(path),c4d.SAVEDOCUMENTFLAGS_DONTADDTORECENTLIST,c4d.FORMAT_C4DEXPORT))
        loaded=c4d.documents.LoadDocument(str(path),c4d.SCENEFILTER_OBJECTS|c4d.SCENEFILTER_MATERIALS,None)
        check(loaded is not None)
        loaded.ExecutePasses(None,True,True,True,c4d.BUILDFLAGS_NONE)
        roots=[node for node in cmds.walk(loaded.GetFirstObject()) if cmds.is_rig(node)]
        check(len(roots)>=2)
        for root in roots:
            loaded_rig=cmds.find_circle(root).GetUp()
            if ss.schema_version(loaded_rig)==cfg.SCHEMA_VERSION:
                check(len(cmds.runtime_tags(cmds.find_circle(root)))==3)
        return str(path)
    test('save and reopen',persistence)
    report={'c4d':c4d.GetC4DVersion(),'python':sys.version,'records':records}
    (output/'acceptance.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    c4d.EventAdd()
    return report
