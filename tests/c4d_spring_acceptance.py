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
        doc.SetTime(c4d.BaseTime(frame, doc.GetFps()))
        embedded.execute_spring(spring_tag)
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

    report = {"c4d": c4d.GetC4DVersion(), "python": sys.version, "samples": first,
              "repeat_frame_15": repeat_again, "random_order": random_order,
              "amount_zero": objects.spring.GetRelPos().y}
    output = ROOT / "tests/artifacts"
    output.mkdir(exist_ok=True)
    (output / "spring_acceptance.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    print(run())
