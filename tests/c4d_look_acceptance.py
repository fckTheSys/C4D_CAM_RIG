"""Main-thread QA in detached documents: target links and camera-relative look."""
import importlib.util
from pathlib import Path
import uuid
import c4d

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    spec=importlib.util.spec_from_file_location('look_qa',path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m


def run(menu_path=None):
    menu=load(Path(menu_path) if menu_path else ROOT/'Cine_CAM/menu.py')
    rows=[]
    for mode in range(4):
        owned=[]
        try:
            d=c4d.documents.BaseDocument();owned.append(d);d.SetFps(30)
            r,o,_=menu.builder(mode==3).build(d) if mode==3 else menu.builder().build(d,mode)
            _,_,ids=menu.inspect(r)
            aim_id=ids['aim_mode'];local=o[10 if mode==3 else 14]
            camera=o[9 if mode==3 else 8];aim=o[6];tag=aim.GetTag(c4d.Ttargetexpression)
            if mode==3:r[ids['walk_strength']]=0
            external=c4d.BaseObject(c4d.Onull);d.InsertObject(external)
            def evaluate():
                d.ExecutePasses(None,True,True,True,c4d.BUILDFLAGS_NONE)
                assert 'ready' in r[ids['status']].lower(),r[ids['status']]
            def pointed_at(target):
                direction=(target.GetMg().off-aim.GetMg().off).GetNormalized()
                assert camera.GetMg().v3.GetNormalized().Dot(direction)>1-1e-8
            r[aim_id]=1;r[ids['target']]=external
            for x in (-1000,1000):
                external.SetRelPos(c4d.Vector(x,400,2000));evaluate();pointed_at(external)
                assert tag[c4d.TARGETEXPRESSIONTAG_LINK]==external
                assert menu.navigate(d,r,'target')==external
            r[aim_id]=2
            local.SetRelPos(c4d.Vector(100,50,300));evaluate();pointed_at(local)
            assert menu.navigate(d,r,'target')==local
            relative=~aim.GetUp().GetMg()*local.GetMg().off
            r[ids['offset_y']]=150
            if mode==0:r[ids['angle']]=120
            elif mode==1:r[ids['progress']]=.8
            elif mode==2:o[11].SetRelPos(c4d.Vector(700,120,900))
            else:r[next(desc for desc,bc in r.GetUserDataContainer() if bc[c4d.DESC_NAME]=='Progress')]=.8
            evaluate();pointed_at(local)
            assert ((~aim.GetUp().GetMg()*local.GetMg().off)-relative).GetLength()<1e-7
            for switch in (0,1,2,0,2):
                r[aim_id]=switch;evaluate()
                if switch==0:
                    assert tag[c4d.TARGETEXPRESSIONTAG_LINK] is None
                    assert menu.navigate(d,r,'target')==r
                else:pointed_at(external if switch==1 else local)
            keyer=load(ROOT/'prototypes/simple_camera/builder.py').key
            for bad in (None,camera):
                r[aim_id]=1;r[ids['target']]=bad
                d.ExecutePasses(None,True,True,True,c4d.BUILDFLAGS_NONE)
                assert 'ready' not in r[ids['status']].lower()
                assert tag[c4d.TARGETEXPRESSIONTAG_LINK] is None
            r[aim_id]=2
            local.SetRelPos(c4d.Vector(0))
            d.ExecutePasses(None,True,True,True,c4d.BUILDFLAGS_NONE)
            assert 'ready' not in r[ids['status']].lower()
            local.SetRelPos(c4d.Vector(100,50,300));evaluate()
            keyer(d,r,ids['offset_y'],[(0,0),(15,100),(30,0)])
            if mode<3:
                r[ids['spring_strength']]=.6
                if mode<2:keyer(d,r,ids['angle' if mode==0 else 'progress'],[(0,0),(30,180 if mode==0 else 1)])
            else:
                progress_desc=next(desc for desc,bc in r.GetUserDataContainer() if bc[c4d.DESC_NAME]=='Progress')
                keyer(d,r,progress_desc,[(0,0),(30,1)])
            desc=c4d.DescID(c4d.DescLevel(c4d.ID_BASEOBJECT_REL_POSITION,c4d.DTYPE_VECTOR,0),c4d.DescLevel(c4d.VECTOR_X,c4d.DTYPE_REAL,0))
            keyer(d,local,desc,[(0,-150),(30,150)])
            samples={}
            for frame in (0,15.5,30,5.25,15.5):
                d.SetTime(c4d.BaseTime(int(frame*100),3000));evaluate();pointed_at(local)
                m=camera.GetMg();value=tuple(v for a in (m.off,m.v1,m.v2,m.v3) for v in (a.x,a.y,a.z))
                if frame in samples:assert max(abs(a-b) for a,b in zip(value,samples[frame]))<1e-7
                samples[frame]=value
            guard=load(ROOT/'prototypes/simple_camera/portability_acceptance.py').guarded
            for t in r.GetTags():
                if t.GetType()==c4d.Tpython:t[c4d.TPYTHON_CODE]=guard(t[c4d.TPYTHON_CODE])
            path=ROOT/'tests/artifacts'/('look_'+uuid.uuid4().hex+'.c4d')
            assert c4d.documents.SaveDocument(d,str(path),c4d.SAVEDOCUMENTFLAGS_DONTADDTORECENTLIST,c4d.FORMAT_C4DEXPORT)
            fresh=c4d.documents.LoadDocument(str(path),c4d.SCENEFILTER_OBJECTS|c4d.SCENEFILTER_MATERIALS,None);assert fresh;owned.append(fresh)
            fresh.ExecutePasses(None,True,True,True,c4d.BUILDFLAGS_NONE)
            node=fresh.GetFirstObject();role=10699101 if mode==3 else 10699220
            while node and node.GetDataInstance().GetInt32(role)!=1:node=node.GetNext()
            assert node
            assert all(t.GetDataInstance().GetInt32(10699104)==1 for t in node.GetTags() if t.GetType()==c4d.Tpython)
            m=node[ids['camera']].GetMg();value=tuple(v for a in (m.off,m.v1,m.v2,m.v3) for v in (a.x,a.y,a.z))
            assert max(abs(a-b) for a,b in zip(value,samples[15.5]))<1e-7
            rows.append({'mode':mode,'pass':True,'scene':str(path)})
        except Exception as error:rows.append({'mode':mode,'pass':False,'error':str(error)})
        finally:
            for d in reversed(owned):c4d.documents.KillDocument(d)
    return {'pass':all(r['pass'] for r in rows),'results':rows}
