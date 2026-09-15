"""Live edit/recovery stress checks in detached owned documents."""
from pathlib import Path
import runpy
import random
import math
import time
import c4d

ROOT=Path(__file__).resolve().parents[1]

def run(builder_path=None):
    build=runpy.run_path(str(builder_path or ROOT/'prototypes/cine_variants/builder.py'))['build']
    rows=[]
    for typ in (0,1,2,3):
        d=c4d.documents.BaseDocument()
        count=0; timings=[]
        try:
            root,objects,ids=build(d,1)
            root[ids['animated_path']]=True
            root[ids['progress']]=.43
            tr=c4d.BaseObject(1018655);d.InsertObject(tr)
            tr[c4d.MGTRACEROBJECT_MODE]=c4d.MGTRACEROBJECT_MODE_LINK
            tr[c4d.SPLINEOBJECT_TYPE]=typ
            root[ids['path']]=tr
            nodes=[]
            rng=random.Random(155)
            def new():
                n=c4d.BaseObject(c4d.Onull);d.InsertObject(n)
                n.SetRelPos(c4d.Vector(rng.uniform(-500,500),rng.uniform(-100,100),rng.uniform(0,1500)))
                return n
            def link():
                links=c4d.InExcludeData()
                for n in nodes:links.InsertObject(n,1)
                tr[c4d.MGTRACEROBJECT_OBJECTLIST]=links
            def evaluate(valid=True):
                nonlocal count
                before=time.perf_counter()
                d.ExecutePasses(None,True,True,True,c4d.BUILDFLAGS_NONE)
                timings.append((time.perf_counter()-before)*1000);count+=1
                status=str(root[ids['status']])
                assert ('ready' in status) if valid else status.startswith('Stopped:'),status
                m=objects[8].GetMg()
                assert all(math.isfinite(v) for a in (m.off,m.v1,m.v2,m.v3) for v in (a.x,a.y,a.z))
                if valid and not root[ids['spring_strength']]:
                    cache=tr.GetCache()
                    expected=cache.GetMg()*cache.GetSplinePoint(.43)
                    assert (objects[9].GetMg().off-expected).GetLength()<.001,'Stale native path'
                return m.off
            nodes=[new() for _ in range(4)];link();evaluate()
            # Delete an actual linked scene object, without rewriting Tracer links.
            removed=nodes.pop(1);removed.Remove()
            d.ExecutePasses(None,True,True,True,c4d.BUILDFLAGS_NONE)
            deletion_status=str(root[ids['status']])
            assert 'ready' in deletion_status or deletion_status.startswith('Stopped:'),deletion_status
            link();evaluate()
            for strength in (0.,.65):
                root[ids['spring_strength']]=strength
                d.SetTime(c4d.BaseTime(1))
                for i in range(60):
                    action=i%4
                    if action==0:nodes.insert(1,new())
                    elif action==1 and len(nodes)>2:nodes.pop(1).Remove()
                    elif action==2:rng.shuffle(nodes)
                    else:nodes[1].SetRelPos(c4d.Vector(rng.uniform(-1000,1000),50,700))
                    link();a=evaluate();b=evaluate()
                    assert (a-b).GetLength()<1e-7,'Repeated frame drift'
                saved=list(nodes)
                for bad_count in (0,1):
                    nodes=saved[:bad_count];link();evaluate(False)
                    nodes=list(saved);link();evaluate()
                positions=[n.GetRelPos() for n in nodes]
                for n in nodes:n.SetRelPos(c4d.Vector())
                evaluate(False)
                for n,p in zip(nodes,positions):n.SetRelPos(p)
                evaluate()
            nodes=[new() for _ in range(64)];link();evaluate()
            nodes.append(new());link();evaluate(False)
            nodes.pop().Remove();link();evaluate()
            timings.sort()
            rows.append({'type':typ,'pass':True,'evaluations':count,'deleted_object_status':deletion_status,'median_ms':timings[len(timings)//2],'max_ms':max(timings)})
        except Exception as error:
            rows.append({'type':typ,'pass':False,'evaluations':count,'error':str(error)})
        finally:c4d.documents.KillDocument(d)
    return {'pass':all(row['pass'] for row in rows),'results':rows}
