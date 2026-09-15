"""Run on C4D main thread; detached documents, never the user's scene."""
import importlib.util
import json
import uuid
from pathlib import Path
import c4d

ROOT = Path(__file__).resolve().parents[1]


def load(relative):
    spec = importlib.util.spec_from_file_location('path_acceptance_module', ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run():
    results = []
    for kind in ('cine', 'ck'):
        for source_kind in ('linear', 'bspline', 'bezier', 'tracer'):
            d = c4d.documents.BaseDocument()
            try:
                b = load('prototypes/'+('cine_variants' if kind == 'cine' else 'simple_camera')+'/builder.py')
                root, obj, ids = b.build(d, 1) if kind == 'cine' else b.build(d)
                path_id = ids['path' if kind == 'cine' else 'Path']
                progress_id = ids['progress' if kind == 'cine' else 'Progress']
                status_id = ids['status' if kind == 'cine' else 'Status']
                moving = obj[5 if kind == 'cine' else 4]
                if kind == 'ck':
                    root[ids['Walk Strength']] = 0
                if source_kind == 'tracer':
                    path = c4d.BaseObject(1018655)
                    links = c4d.InExcludeData()
                    controls = []
                    for z in (0, 800):
                        n = c4d.BaseObject(c4d.Onull)
                        d.InsertObject(n)
                        n.SetRelPos(c4d.Vector(500, 0, z))
                        links.InsertObject(n, 1)
                        controls.append(n)
                    path[c4d.MGTRACEROBJECT_OBJECTLIST] = links
                    path[c4d.MGTRACEROBJECT_MODE] = c4d.MGTRACEROBJECT_MODE_LINK
                    path.SetRelPos(c4d.Vector(70, 30, 90))
                else:
                    spline_type = {'linear':c4d.SPLINETYPE_LINEAR, 'bspline':c4d.SPLINETYPE_BSPLINE,
                                   'bezier':c4d.SPLINETYPE_BEZIER}[source_kind]
                    path = c4d.SplineObject(2, spline_type)
                    path.SetAllPoints([c4d.Vector(0), c4d.Vector(0, 0, 800)])
                    path.SetRelPos(c4d.Vector(500, 0, 0))
                    path.Message(c4d.MSG_UPDATE)
                d.InsertObject(path)
                root[path_id] = path
                # Exactly ONE evaluation per edit: repeated passes can hide a frame lag.
                for p in (0., .25, 1., .5):
                    root[progress_id] = p
                    d.ExecutePasses(None, True, True, True, c4d.BUILDFLAGS_NONE)
                    status = root[status_id]
                    assert 'ready' in status.lower(), status
                    expected = (path.GetMg()*path.GetSplinePoint(p) if kind == 'cine' and source_kind != 'tracer'
                                else c4d.Vector(500, 0, 800*p))
                    error = (moving.GetMg().off-expected).GetLength()
                    assert error < .01, ('wrong route', p, error, str(moving.GetMg().off))
                if source_kind == 'tracer':
                    for n in controls:
                        n.SetRelPos(n.GetRelPos()+c4d.Vector(200, 0, 0))
                else:
                    path.SetRelPos(c4d.Vector(700, 0, 0))
                d.ExecutePasses(None, True, True, True, c4d.BUILDFLAGS_NONE)
                assert (moving.GetMg().off-c4d.Vector(700, 0, 400)).GetLength() < .01, 'edit lag/stale route'
                if kind == 'cine':
                    root[ids['spring_strength']] = 1.
                    d.ExecutePasses(None, True, True, True, c4d.BUILDFLAGS_NONE)
                    assert 'ready' in root[status_id].lower(), root[status_id]
                obj[10 if kind == 'cine' else 2].Remove()
                d.ExecutePasses(None, True, True, True, c4d.BUILDFLAGS_NONE)
                assert 'ready' in root[status_id].lower(), root[status_id]
                load('Cine_CAM/menu.py').inspect(root)
                invalid = c4d.BaseObject(c4d.Onull)
                d.InsertObject(invalid)
                root[path_id] = invalid
                d.ExecutePasses(None, True, True, True, c4d.BUILDFLAGS_NONE)
                assert 'ready' not in root[status_id].lower(), 'invalid path reported ready'
                assert moving.GetTag(c4d.Taligntospline)[c4d.ALIGNTOSPLINETAG_LINK] is None, 'old path still driven'
                root[path_id] = path
                d.ExecutePasses(None, True, True, True, c4d.BUILDFLAGS_NONE)
                assert 'ready' in root[status_id].lower(), root[status_id]
                root[path_id] = None
                d.ExecutePasses(None, True, True, True, c4d.BUILDFLAGS_NONE)
                assert 'ready' not in root[status_id].lower(), 'empty Path silently used fallback'
                results.append({'rig':kind, 'source':source_kind, 'pass':True})
            except Exception as error:
                results.append({'rig':kind, 'source':source_kind, 'pass':False, 'error':str(error)})
            finally:
                c4d.documents.KillDocument(d)
    return {'pass':all(row['pass'] for row in results), 'results':results}


def run_animated():
    """Four-control curved routes, FX, arbitrary seeks, edits and guarded reopen."""
    results = []
    guard = load('prototypes/simple_camera/portability_acceptance.py').guarded
    points = [c4d.Vector(350, 0, 0), c4d.Vector(550, 50, 230),
              c4d.Vector(-170, 100, 640), c4d.Vector(600, 0, 1050)]
    for kind in ('cine', 'ck'):
        for spline_type in (c4d.SPLINETYPE_LINEAR, c4d.SPLINETYPE_BEZIER, c4d.SPLINETYPE_BSPLINE,
                            c4d.SPLINETYPE_CUBIC, c4d.SPLINETYPE_AKIMA):
            owned = []
            try:
                d = c4d.documents.BaseDocument(); owned.append(d); d.SetFps(30)
                b = load('prototypes/'+('cine_variants' if kind == 'cine' else 'simple_camera')+'/builder.py')
                root, obj, ids = b.build(d, 1) if kind == 'cine' else b.build(d)
                path_id = ids['path' if kind == 'cine' else 'Path']
                progress_id = ids['progress' if kind == 'cine' else 'Progress']
                status_id = ids['status' if kind == 'cine' else 'Status']
                camera_id = ids['camera' if kind == 'cine' else 'Camera']
                tracer = c4d.BaseObject(1018655); d.InsertObject(tracer)
                tracer.SetRelPos(c4d.Vector(125, 35, 80))
                tracer.SetRelRot(c4d.Vector(.3, .1, -.2))
                links = c4d.InExcludeData(); controllers = []
                for p in points:
                    n = c4d.BaseObject(c4d.Onull); d.InsertObject(n); n.SetRelPos(p)
                    links.InsertObject(n, 1); controllers.append(n)
                tracer[c4d.MGTRACEROBJECT_OBJECTLIST] = links
                tracer[c4d.MGTRACEROBJECT_MODE] = c4d.MGTRACEROBJECT_MODE_LINK
                tracer[c4d.SPLINEOBJECT_TYPE] = spline_type
                root[path_id] = tracer
                keyer = load('prototypes/simple_camera/builder.py').key
                keyer(d, root, progress_id, [(0, 0), (60, 1)])
                if kind == 'cine':
                    root[ids['spring_strength']] = .6
                    root[ids['shake_strength']] = .2
                else:
                    root[ids['Walk Strength']] = 1.
                    root[ids['Shake Strength']] = .2
                def sample(document, rig, frame):
                    document.SetTime(c4d.BaseTime(int(frame*1000),30000))
                    document.ExecutePasses(None,True,True,True,c4d.BUILDFLAGS_NONE)
                    assert 'ready' in rig[status_id].lower(), rig[status_id]
                    m = rig[camera_id].GetMg()
                    return tuple(value for v in (m.off,m.v1,m.v2,m.v3) for value in (v.x,v.y,v.z))
                frames = (0, 5.5, 15, 30.25, 45, 60)
                baseline = {f:sample(d,root,f) for f in frames}
                errors = [max(abs(a-b) for a,b in zip(sample(d,root,f),baseline[f])) for f in reversed(frames)]
                assert max(errors) < 1e-5, ('seek error',max(errors))
                before = sample(d,root,30.25)
                # Undo/Redo link edits must re-resolve host wrappers.
                replacement = c4d.SplineObject(2,c4d.SPLINETYPE_LINEAR)
                replacement.SetAllPoints([c4d.Vector(0),c4d.Vector(1000,0,0)])
                replacement.Message(c4d.MSG_UPDATE);d.InsertObject(replacement)
                d.StartUndo();d.AddUndo(c4d.UNDOTYPE_CHANGE,root)
                root[path_id] = replacement;d.EndUndo()
                sample(d,root,30.25)
                assert d.DoUndo()
                role_id = 10699220 if kind == 'cine' else 10699101
                root = d.GetFirstObject()
                while root and root.GetDataInstance().GetInt32(role_id) != 1: root = root.GetNext()
                assert root is not None
                restored = sample(d,root,30.25)
                assert max(abs(a-b) for a,b in zip(before,restored)) < 1e-5
                tracer = root[path_id]
                links = tracer[c4d.MGTRACEROBJECT_OBJECTLIST]
                controllers = [links.ObjectFromIndex(d,i) for i in range(links.GetObjectCount())]
                controllers[1].SetRelPos(controllers[1].GetRelPos()+c4d.Vector(300,70,200))
                after = sample(d,root,30.25)
                assert max(abs(a-b) for a,b in zip(before,after)) > 1, 'controller edit ignored'
                # Save with dependency guards; embedded tags must run without local files/imports.
                for tag in root.GetTags():
                    if tag.GetType() == c4d.Tpython:
                        tag[c4d.TPYTHON_CODE] = guard(tag[c4d.TPYTHON_CODE])
                scene = ROOT/'tests'/'artifacts'/('static_tracer_'+uuid.uuid4().hex+'.c4d')
                scene.parent.mkdir(parents=True,exist_ok=True)
                assert c4d.documents.SaveDocument(d,str(scene),c4d.SAVEDOCUMENTFLAGS_DONTADDTORECENTLIST,c4d.FORMAT_C4DEXPORT)
                reopened = c4d.documents.LoadDocument(str(scene),c4d.SCENEFILTER_OBJECTS|c4d.SCENEFILTER_MATERIALS,None)
                assert reopened is not None; owned.append(reopened)
                fresh = reopened.GetFirstObject()
                role_id = 10699220 if kind == 'cine' else 10699101
                while fresh and fresh.GetDataInstance().GetInt32(role_id) != 1:
                    fresh = fresh.GetNext()
                assert fresh is not None
                cold = sample(reopened,fresh,30.25)
                assert all(tag.GetDataInstance().GetInt32(10699104) == 1 for tag in fresh.GetTags()
                           if tag.GetType() == c4d.Tpython), 'guarded tags did not execute'
                error = max(abs(a-b) for a,b in zip(after,cold))
                assert error < 1e-5, ('cold edited-path error',error)
                results.append({'rig':kind,'tracer_spline_type':spline_type,'pass':True,'cold_error':error,'scene':str(scene)})
            except Exception as error:
                results.append({'rig':kind,'tracer_spline_type':spline_type,'pass':False,'error':str(error)})
            finally:
                for document in reversed(owned): c4d.documents.KillDocument(document)
    return {'pass':all(row['pass'] for row in results),'results':results}


def run_boundaries():
    results = []
    for kind in ('cine','ck'):
        d = c4d.documents.BaseDocument()
        try:
            b = load('prototypes/'+('cine_variants' if kind=='cine' else 'simple_camera')+'/builder.py')
            root,obj,ids = b.build(d,1) if kind=='cine' else b.build(d)
            path_id=ids['path' if kind=='cine' else 'Path']; status_id=ids['status' if kind=='cine' else 'Status']
            for case in ('closed','one_point','zero_length','multi_segment','trace_history','animated_controller','cycle'):
                if case in ('trace_history','animated_controller','cycle'):
                    source=c4d.BaseObject(1018655);d.InsertObject(source)
                    links=c4d.InExcludeData(); controls=[]
                    for p in (c4d.Vector(0),c4d.Vector(300,0,800)):
                        n=c4d.BaseObject(c4d.Onull);d.InsertObject(n);n.SetRelPos(p);links.InsertObject(n,1);controls.append(n)
                    source[c4d.MGTRACEROBJECT_MODE]=c4d.MGTRACEROBJECT_MODE_TRACE if case=='trace_history' else c4d.MGTRACEROBJECT_MODE_LINK
                    if case=='animated_controller':
                        desc=c4d.DescID(c4d.DescLevel(c4d.ID_BASEOBJECT_REL_POSITION,c4d.DTYPE_VECTOR,0),c4d.DescLevel(c4d.VECTOR_X,c4d.DTYPE_REAL,0))
                        load('prototypes/simple_camera/builder.py').key(d,controls[0],desc,[(0,0),(30,100)])
                    if case=='cycle': links.InsertObject(obj[8 if kind=='cine' else 9],1)
                    source[c4d.MGTRACEROBJECT_OBJECTLIST]=links
                else:
                    count=1 if case=='one_point' else 4
                    source=c4d.SplineObject(count,c4d.SPLINETYPE_LINEAR);d.InsertObject(source)
                    source.SetAllPoints([c4d.Vector(0) for i in range(count)] if case=='zero_length' else
                                        [c4d.Vector(0),c4d.Vector(300,0,0),c4d.Vector(300,0,600),c4d.Vector(0,0,600)][:count])
                    if case=='closed': source[c4d.SPLINEOBJECT_CLOSED]=True
                    if case=='multi_segment':
                        source.ResizeObject(4,2);source.SetSegment(0,2,False);source.SetSegment(1,2,False)
                    source.Message(c4d.MSG_UPDATE)
                root[path_id]=source
                d.ExecutePasses(None,True,True,True,c4d.BUILDFLAGS_NONE)
                ready='ready' in root[status_id].lower()
                results.append({'rig':kind,'case':case,'pass':ready==(case=='closed'),'status':root[status_id]})
        finally:c4d.documents.KillDocument(d)
    return {'pass':all(r['pass'] for r in results),'results':results}


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
