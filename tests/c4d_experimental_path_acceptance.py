"""Owned-document animated Tracer checks against native evaluated motion."""
from pathlib import Path
import importlib.util
import uuid
import time
import c4d

ROOT=Path(__file__).resolve().parents[1]


def load(path):
    spec=importlib.util.spec_from_file_location('experimental_qa',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def run():
    rows=[]
    for typ in (c4d.SPLINETYPE_LINEAR,c4d.SPLINETYPE_CUBIC,c4d.SPLINETYPE_AKIMA,c4d.SPLINETYPE_BSPLINE):
        owned=[]
        try:
            d=c4d.documents.BaseDocument();owned.append(d);d.SetFps(30)
            r,o,ids=load(ROOT/'prototypes/cine_variants/builder.py').build(d,1)
            assert 'animated_path' in ids,'Experimental opt-in is missing'
            key=load(ROOT/'prototypes/simple_camera/builder.py').key
            tr=c4d.BaseObject(1018655);d.InsertObject(tr)
            links=c4d.InExcludeData();controls=[]
            for p in (c4d.Vector(0),c4d.Vector(200,20,300),c4d.Vector(-100,50,700),c4d.Vector(0,0,1000)):
                n=c4d.BaseObject(c4d.Onull);d.InsertObject(n);n.SetRelPos(p);controls.append(n);links.InsertObject(n,1)
            tr[c4d.MGTRACEROBJECT_OBJECTLIST]=links;tr[c4d.MGTRACEROBJECT_MODE]=c4d.MGTRACEROBJECT_MODE_LINK
            tr[c4d.SPLINEOBJECT_TYPE]=typ;r[ids['path']]=tr
            xdesc=c4d.DescID(c4d.DescLevel(c4d.ID_BASEOBJECT_REL_POSITION,c4d.DTYPE_VECTOR,0),c4d.DescLevel(c4d.VECTOR_X,c4d.DTYPE_REAL,0))
            key(d,controls[1],xdesc,[(0,200),(15,600),(30,200)])
            key(d,r,ids['progress'],[(0,0),(30,1)])
            def evaluate(frame):
                d.SetTime(c4d.BaseTime(int(round(frame*1000)),30000))
                d.ExecutePasses(None,True,True,True,c4d.BUILDFLAGS_NONE)
            evaluate(0)
            assert 'Stopped:' in r[ids['status']],'Default must remain static'
            r[ids['animated_path']]=True;evaluate(0)
            assert 'ready' in r[ids['status']],r[ids['status']]
            scope={};exec(r.GetTag(c4d.Tpython)[c4d.TPYTHON_CODE],scope)
            signature=[];sample=scope['motion_source'](r,o,signature)
            max_error=0.
            for frame in (0,3.25,12,15.5,23.75,30,5):
                expected=sample(frame/30)
                evaluate(frame)
                assert 'ready' in r[ids['status']],r[ids['status']]
                max_error=max(max_error,(expected-o[9].GetMg().off).GetLength())
            assert max_error<.001,('Historical sampler/native mismatch',max_error)
            r[ids['spring_strength']]=.65
            before=time.perf_counter();evaluate(30);cold_ms=(time.perf_counter()-before)*1000
            values={}
            for frame in (0,15.5,30,5.25,15.5):
                evaluate(frame);assert 'ready' in r[ids['status']],r[ids['status']]
                m=o[8].GetMg();v=tuple(x for a in (m.off,m.v1,m.v2,m.v3) for x in (a.x,a.y,a.z))
                if frame in values:assert max(abs(a-b) for a,b in zip(values[frame],v))<1e-7
                values[frame]=v
            curve=controls[1].FindCTrack(xdesc).GetCurve();curve.GetKey(1).SetValue(curve,850)
            evaluate(15.5);m=o[8].GetMg();edited=tuple(x for a in (m.off,m.v1,m.v2,m.v3) for x in (a.x,a.y,a.z))
            assert max(abs(a-b) for a,b in zip(edited,values[15.5]))>1,'Key edit did not invalidate history'
            guard=load(ROOT/'prototypes/simple_camera/portability_acceptance.py').guarded
            for tag in r.GetTags():
                if tag.GetType()==c4d.Tpython:tag[c4d.TPYTHON_CODE]=guard(tag[c4d.TPYTHON_CODE])
            path=ROOT/'tests/artifacts'/('animated_tracer_'+uuid.uuid4().hex+'.c4d')
            assert c4d.documents.SaveDocument(d,str(path),c4d.SAVEDOCUMENTFLAGS_DONTADDTORECENTLIST,c4d.FORMAT_C4DEXPORT)
            fresh=c4d.documents.LoadDocument(str(path),c4d.SCENEFILTER_OBJECTS|c4d.SCENEFILTER_MATERIALS,None);assert fresh;owned.append(fresh)
            fresh.ExecutePasses(None,True,True,True,c4d.BUILDFLAGS_NONE)
            root=fresh.GetFirstObject()
            while root and root.GetDataInstance().GetInt32(10699220)!=1:root=root.GetNext()
            assert root and 'ready' in root[ids['status']],root[ids['status']] if root else 'missing root'
            assert all(t.GetDataInstance().GetInt32(10699104)==1 for t in root.GetTags() if t.GetType()==c4d.Tpython)
            m=root[ids['camera']].GetMg();v=tuple(x for a in (m.off,m.v1,m.v2,m.v3) for x in (a.x,a.y,a.z))
            assert max(abs(a-b) for a,b in zip(v,edited))<1e-7
            rows.append({'type':typ,'pass':True,'native_error_cm':max_error,'cold_1s_ms':cold_ms,'scene':str(path)})
        except Exception as e:rows.append({'type':typ,'pass':False,'error':str(e)})
        finally:
            for d in reversed(owned):c4d.documents.KillDocument(d)
    return {'pass':all(r['pass'] for r in rows),'results':rows}
