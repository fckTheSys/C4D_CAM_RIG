"""Live C4D regression for CamRig MCP document isolation and recovery."""
import c4d
import os
import runpy
import uuid


def _add_key(node, desc_id, frame, value, fps):
    track = c4d.CTrack(node, desc_id)
    node.InsertTrackSorted(track)
    curve = track.GetCurve()
    key = curve.AddKey(c4d.BaseTime(frame, fps))["key"]
    key.SetValue(curve, value)
    key.SetInterpolation(curve, c4d.CINTERPOLATION_LINEAR)


def _source(name, output):
    doc = c4d.documents.BaseDocument()
    doc.SetDocumentName(name)
    doc.SetDocumentPath(output)
    doc.SetFps(47)
    doc.SetMinTime(c4d.BaseTime(-5, 47))
    doc.SetMaxTime(c4d.BaseTime(94, 47))
    doc.SetTime(c4d.BaseTime(13, 47))
    root = c4d.BaseObject(c4d.Onull)
    root.SetName("Lifecycle Root")
    root.SetRelPos(c4d.Vector(11, 22, 33))
    root.SetRelRot(c4d.Vector(.1, .2, .3))
    root.SetRelScale(c4d.Vector(1.5, 2.0, 2.5))
    child = c4d.BaseObject(c4d.Ocube)
    child.SetName("Lifecycle Child")
    child.SetRelPos(c4d.Vector(7, 8, 9))
    child.InsertUnderLast(root)
    scalar = c4d.GetCustomDataTypeDefault(c4d.DTYPE_REAL)
    scalar[c4d.DESC_NAME] = "Lifecycle Scalar"
    scalar_id = root.AddUserData(scalar)
    root[scalar_id] = 12.5
    _add_key(root, scalar_id, 0, 1.0, 47)
    link = c4d.GetCustomDataTypeDefault(c4d.DTYPE_BASELISTLINK)
    link[c4d.DESC_NAME] = "Lifecycle Link"
    link_id = root.AddUserData(link)
    root[link_id] = child
    doc.InsertObject(root)
    material = c4d.Material()
    material.SetName("Lifecycle Material")
    material[c4d.MATERIAL_USE_COLOR] = True
    material[c4d.MATERIAL_COLOR_COLOR] = c4d.Vector(.2, .4, .6)
    doc.InsertMaterial(material)
    render = doc.GetActiveRenderData().GetDataInstance()
    render.SetInt32(c4d.RDATA_XRES, 1234)
    render.SetInt32(c4d.RDATA_YRES, 567)
    doc.SetActiveObject(root, c4d.SELECTION_NEW)
    return doc


def _close(document):
    if document:
        try:
            c4d.documents.KillDocument(document)
        except (ReferenceError, RuntimeError):
            pass


def _prepare(harness, fixture, output, label, fault=None):
    token = label + "_" + uuid.uuid4().hex
    snapshot = os.path.join(output, label + "_" + token + ".c4d")
    return token, snapshot, harness["prepare"](snapshot, "QA " + token, fixture, token, fault)


def run(project_root, output):
    """Run normal, duplicate-name, injected-fault, and emergency-recovery cases."""
    os.makedirs(output, exist_ok=True)
    harness = runpy.run_path(os.path.join(project_root, "tools", "c4d_mcp_harness.py"))
    fixture = os.path.join(project_root, "tests", "build_agent_qa.py")
    results = {}

    # Normal identity restoration with a populated, saved-style source document.
    normal = _source("Lifecycle Normal.c4d", output)
    c4d.documents.InsertBaseDocument(normal)
    c4d.documents.SetActiveDocument(normal)
    normal_before = harness["fingerprint"](normal)
    token, snapshot, setup = _prepare(harness, fixture, output, "normal")
    restored = harness["cleanup"](snapshot, setup["temporary"], token, setup["before"])
    if restored["status"] != "PASS" or harness["fingerprint"](normal) != normal_before:
        raise AssertionError("normal lifecycle did not preserve exact source identity")
    results["normal"] = restored
    _close(normal)

    # Exact registry identity wins even when another document has the same name.
    other = _source("Duplicate Lifecycle.c4d", output)
    duplicate = _source("Duplicate Lifecycle.c4d", output)
    c4d.documents.InsertBaseDocument(other)
    c4d.documents.InsertBaseDocument(duplicate)
    c4d.documents.SetActiveDocument(duplicate)
    duplicate_before = harness["fingerprint"](duplicate)
    token, snapshot, setup = _prepare(harness, fixture, output, "duplicate")
    restored = harness["cleanup"](snapshot, setup["temporary"], token, setup["before"])
    if restored["status"] != "PASS" or harness["fingerprint"](duplicate) != duplicate_before:
        raise AssertionError("duplicate-name lifecycle selected the wrong source")
    results["duplicate_name"] = restored
    _close(other)
    _close(duplicate)

    # A setup failure after QA insertion must restore the original without a PASS.
    setup_fault = _source("Lifecycle Setup Fault.c4d", output)
    c4d.documents.InsertBaseDocument(setup_fault)
    c4d.documents.SetActiveDocument(setup_fault)
    before = harness["fingerprint"](setup_fault)
    try:
        _prepare(harness, fixture, output, "setup_fault", "after_insert")
        raise AssertionError("injected setup failure was not raised")
    except RuntimeError as error:
        if "injected setup failure" not in str(error):
            raise
    if harness["fingerprint"](setup_fault) != before or c4d.documents.GetActiveDocument() != setup_fault:
        raise AssertionError("setup failure changed its source document")
    results["setup_fault"] = "rejected_and_restored"
    _close(setup_fault)

    # A cleanup failure must retain session/snapshot and be recoverable on retry.
    cleanup_fault = _source("Lifecycle Cleanup Fault.c4d", output)
    c4d.documents.InsertBaseDocument(cleanup_fault)
    c4d.documents.SetActiveDocument(cleanup_fault)
    token, snapshot, setup = _prepare(harness, fixture, output, "cleanup_fault")
    try:
        harness["cleanup"](snapshot, setup["temporary"], token, setup["before"], "before_restore")
        raise AssertionError("injected cleanup failure was not raised")
    except RuntimeError as error:
        if "injected cleanup failure" not in str(error):
            raise
    restored = harness["cleanup"](snapshot, setup["temporary"], token, setup["before"])
    if restored["status"] != "PASS":
        raise AssertionError("cleanup retry unexpectedly required snapshot recovery")
    results["cleanup_fault"] = restored
    _close(cleanup_fault)

    # Explicitly remove a disposable source: recovery must be visible as RECOVERED.
    recovery = _source("Lifecycle Recovery.c4d", output)
    c4d.documents.InsertBaseDocument(recovery)
    c4d.documents.SetActiveDocument(recovery)
    recovery_before = harness["fingerprint"](recovery)
    token, snapshot, setup = _prepare(harness, fixture, output, "recovery")
    if harness["_registered"](recovery):
        _close(recovery)
    restored = harness["cleanup"](snapshot, setup["temporary"], token, setup["before"])
    active = c4d.documents.GetActiveDocument()
    if restored["status"] != "RECOVERED" or harness["fingerprint"](active) != recovery_before:
        raise AssertionError("emergency snapshot recovery was not explicit and exact")
    results["forced_recovery"] = restored
    _close(active)
    c4d.EventAdd()
    return results
