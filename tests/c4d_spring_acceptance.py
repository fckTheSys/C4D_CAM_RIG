"""Focused Follow Spring smoke test; run from Cinema 4D's main thread."""
import importlib.util
import json
from pathlib import Path
import sys
import c4d

ROOT = Path(__file__).resolve().parents[1]


def run():
    alias = "camrig_spring_acceptance"
    for key in list(sys.modules):
        if key == alias or key.startswith(alias + "."):
            del sys.modules[key]
    spec = importlib.util.spec_from_file_location(alias, ROOT / "camrig/__init__.py", submodule_search_locations=[str(ROOT / "camrig")])
    package = importlib.util.module_from_spec(spec)
    sys.modules[alias] = package
    spec.loader.exec_module(package)
    config = importlib.import_module(alias + ".config")
    embedded = importlib.import_module(alias + ".tag_embedded")
    assemble = importlib.import_module(alias + ".rig_assemble")
    commands = importlib.import_module(alias + ".commands")
    objects_module = importlib.import_module(alias + ".rig_objects")

    doc = c4d.documents.BaseDocument()
    doc.SetDocumentName("CamRig 1.6 Follow Spring acceptance")
    c4d.documents.InsertBaseDocument(doc)
    rig = assemble.build_cam_rig(doc)
    circle = commands.find_circle(rig)
    objects = objects_module.get_rig_objects(circle)
    ids = commands.ud_map(rig)

    def curve(desc, pairs):
        track = c4d.CTrack(rig, desc)
        rig.InsertTrackSorted(track)
        curve_data = track.GetCurve()
        for frame, value in pairs:
            key = curve_data.AddKey(c4d.BaseTime(frame, doc.GetFps()))["key"]
            key.SetValue(curve_data, value)
            key.SetInterpolation(curve_data, c4d.CINTERPOLATION_LINEAR)

    curve(ids[config.UD_HEIGHT], [(0, 0.0), (30, 400.0)])
    rig[ids[config.UD_SPRING_AMOUNT]] = 100.0
    rig[ids[config.UD_SPRING_RESPONSE]] = 60.0
    rig[ids[config.UD_SPRING_DAMPING]] = 30.0
    spring_tag = next(tag for tag in circle.GetTags() if tag.GetName() == config.SPRING_TAG_NAME)

    def evaluate(frame):
        doc.SetTime(embedded._spring_time(frame / doc.GetFps()))
        doc.ExecutePasses(None, True, True, True, c4d.BUILDFLAGS_NONE)
        return objects.spring.GetRelPos().y

    first = {frame: evaluate(frame) for frame in (0, 1, 5, 10, 15, 20, 30, 45)}
    repeat = evaluate(15)
    random_order = [evaluate(frame) for frame in (30, 5, 45, 1)]
    repeat_again = evaluate(15)
    if abs(first[1]) < 1e-6 or abs(first[15]) < 1e-6:
        raise AssertionError("Height transition did not produce Spring Offset motion")
    if abs(repeat - repeat_again) > 1e-8:
        raise AssertionError("Repeated random frame is not reproducible")
    if first[30] == first[45]:
        raise AssertionError("Damped settling did not evolve after the target stopped")

    rig[ids[config.UD_SPRING_AMOUNT]] = 0.0
    if abs(evaluate(15)) > 1e-12:
        raise AssertionError("Amount 0 did not bypass Spring Offset")

    checks = []
    def near(a,b,tol=1e-4):
        error = (a-b).GetLength() if isinstance(a,c4d.Vector) else abs(a-b)
        assert error <= tol, (error,a,b)
    # Real Align expression versus detached historical sampler.
    sampler = embedded._spring_sampler()
    parent = c4d.BaseObject(c4d.Onull)
    doc.InsertObject(parent)
    rig.InsertUnder(parent)
    parent.SetRelPos(c4d.Vector(13,22,37))
    parent.SetRelRot(c4d.Vector(.2,.3,.1))
    parent.SetRelScale(c4d.Vector(1.3))
    rig[ids['Offset X']] = 12.
    rig[ids['Offset Y']] = 17.
    rig[ids['Offset Z']] = -23.
    rig[ids['Plane Tilt']] = 27.
    for angle in (-720.,-17.,0.,73.,350.,370.,1080.):
        rig[ids['Orbit']] = angle
        evaluate(15)
        near(embedded._spring_base_position(objects,doc.GetTime(),doc,sampler),objects.cam.GetMg().off)
    checks.append('native sampler: signed orbit, plane, XYZ offset, rotated/scaled parent')

    # Signature must ignore Amount and include changed source constants/start/parents.
    signature = embedded._spring_signature(objects)
    rig[ids[config.UD_SPRING_AMOUNT]] = 50.
    assert signature == embedded._spring_signature(objects)
    parent.SetRelPos(c4d.Vector(40,22,37))
    assert signature != embedded._spring_signature(objects)
    signature = embedded._spring_signature(objects)
    doc.SetMinTime(c4d.BaseTime(-1))
    assert signature != embedded._spring_signature(objects)
    doc.SetMinTime(c4d.BaseTime(0))
    checks.append('cache signature: Amount excluded, static parent and range start included')

    # Rename all Python tags: stages must still execute using metadata roles.
    for stage in circle.GetTags():
        if stage.CheckType(c4d.Tpython):
            stage.SetName('Renamed stage')
    evaluate(15)
    assert objects.spring.GetRelPos().GetLength() > .01
    checks.append('renamed embedded stages execute by role')

    # Compare hot history to a cold recompiled tag at arbitrary subframes and FPS.
    rig[ids[config.UD_SPRING_AMOUNT]] = 100.
    matrix_samples = {}
    for probe_index, frame in enumerate((15.123,30.,5.37,45.,1.1,15.123)):
        evaluate(frame)
        hot = c4d.Vector(objects.cam.GetMg().off)
        spring_tag[c4d.TPYTHON_CODE] = assemble._build_python_tag_source() + '\n# cold-cache probe ' + str(probe_index) + '\n'
        evaluate(frame)
        near(hot, objects.cam.GetMg().off)
        matrix_samples[frame] = c4d.Vector(objects.cam.GetMg().off)
    for fps in (24,25,30,60):
        doc.SetFps(fps)
        for frame, expected in matrix_samples.items():
            evaluate(frame*fps/30)
            near(expected,objects.cam.GetMg().off)
    doc.SetFps(30)
    checks.append('real expressions: cold/hot cache, random subframes, 24/25/30/60 FPS')

    # An ordinary display tag is safe; expressions and frozen sources are rejected.
    display = c4d.BaseTag(c4d.Tdisplay)
    parent.InsertTag(display)
    assert embedded._spring_source_issue(objects) is None
    expression = c4d.BaseTag(c4d.Tpython)
    parent.InsertTag(expression)
    assert 'expression' in embedded._spring_source_issue(objects)
    evaluate(15)
    near(objects.spring.GetRelPos(),c4d.Vector(0))
    expression.Remove()
    parent.SetFrozenPos(c4d.Vector(1,0,0))
    assert 'frozen' in embedded._spring_source_issue(objects)
    parent.SetFrozenPos(c4d.Vector(0))
    checks.append('source guards: display accepted, expression/frozen rejected')

    # Exact 1.5 fixture: preserve matrices and existing animation through Upgrade/Undo.
    scene_support = importlib.import_module(alias + '.scene_support')
    legacy = assemble.build_cam_rig(doc)
    legacy.SetName('Schema2 migration probe')
    old = objects_module.get_rig_objects(commands.find_circle(legacy))
    old_source = (ROOT/'camrig/legacy_150.txt').read_text(encoding='utf-8')
    for tag in list(old.circle.GetTags()):
        if tag.CheckType(c4d.Tpython):
            if tag.GetName() == config.SPRING_TAG_NAME:
                tag.Remove()
            else:
                tag[c4d.TPYTHON_CODE] = old_source
    old.cam.InsertUnder(old.offset)
    old.spring.Remove()
    for desc,bc in reversed(legacy.GetUserDataContainer()):
        if bc[c4d.DESC_NAME] in config.SPRING_KEYS + ['Spring']:
            legacy.RemoveUserData(desc)
    meta=legacy.GetDataInstance().GetContainer(config.META_ID)
    meta[config.META_SCHEMA]=2
    legacy.GetDataInstance().SetContainer(config.META_ID,meta)
    old_ids=commands.ud_map(legacy)
    legacy[old_ids['Height']]=75.
    legacy[old_ids['Orbit']]=37.
    legacy[old_ids['Drift Pos']]=2.
    def pose():
        doc.ExecutePasses(None,True,True,True,c4d.BUILDFLAGS_NONE)
        current=objects_module.get_rig_objects(commands.find_circle(legacy))
        return [cam.GetMg() for cam in (current.cam,current.fx)]
    before=pose()
    assert commands.upgrade_rig(doc,legacy)[0]
    for a,b in zip(before,pose()):
        for field in ('off','v1','v2','v3'): near(getattr(a,field),getattr(b,field),1e-5)
    assert commands.ud_map(legacy)['Orbit']==old_ids['Orbit']
    assert not commands.upgrade_rig(doc,legacy)[0]
    assert doc.DoUndo()
    legacy=doc.SearchObject('Schema2 migration probe')
    assert scene_support.schema_version(legacy)==2
    assert objects_module.get_rig_objects(commands.find_circle(legacy)).spring is None
    for a,b in zip(before,pose()):
        for field in ('off','v1','v2','v3'): near(getattr(a,field),getattr(b,field),1e-5)
    assert doc.DoRedo()
    legacy=doc.SearchObject('Schema2 migration probe')
    assert scene_support.schema_version(legacy)==3
    for a,b in zip(before,pose()):
        for field in ('off','v1','v2','v3'): near(getattr(a,field),getattr(b,field),1e-5)
    checks.append('schema 2 Upgrade: both camera matrices, DescID, idempotence, Undo/Redo')

    report = {"c4d": c4d.GetC4DVersion(), "python": sys.version, "samples": first,
              "repeat_frame_15": repeat_again, "random_order": random_order,
              "checks": checks, "amount_zero": 0.0}
    output = ROOT / "tests/artifacts"
    output.mkdir(exist_ok=True)
    (output / "spring_acceptance.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    print(run())
