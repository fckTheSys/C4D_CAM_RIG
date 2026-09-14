"""Compare fixed variants against frozen universal P3 in owned documents."""
import importlib.util
from pathlib import Path
import uuid
import c4d


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run():
    folder = Path(__file__).parent
    new = load(folder/'builder.py', 'cine_fixed_test')
    legacy = load(folder.parent/'cine_camera'/'builder.py', 'cine_legacy_test')
    document = c4d.documents.BaseDocument()
    document.SetFps(30)
    passed = []
    roots = []
    def key(node, desc, samples):
        track = c4d.CTrack(node,desc)
        node.InsertTrackSorted(track)
        curve = track.GetCurve()
        for frame,value in samples:
            item = curve.AddKey(c4d.BaseTime(frame,30))['key']
            item.SetValue(curve,value)
            item.SetInterpolation(curve,c4d.CINTERPOLATION_LINEAR)
    def evaluate(frame):
        document.SetTime(c4d.BaseTime(int(frame*1000),30000))
        document.ExecutePasses(None,True,True,True,c4d.BUILDFLAGS_NONE)
    def near(a,b):
        for field in ('off','v1','v2','v3'):
            assert (getattr(a,field)-getattr(b,field)).GetLength() < 1e-6, field
    try:
        for mode in range(3):
            old, oo, oi = legacy.build(document)
            old[oi['movement_mode']] = mode
            root, objects, ids = new.build(document, mode)
            roots.append((root,objects,ids))
            assert 'movement_mode' not in ids
            all_motion = {'angle','radius','height','center','path','progress','free'}
            expected = ({'angle','radius','height','center'},{'path','progress'},{'free'})[mode]
            assert set(ids) & all_motion == expected
            assert set(objects) & {2,4,10,11} == ({2,4},{10},{11})[mode]
            assert sum(obj.GetType() in (1057516,c4d.Ocamera) for obj in objects.values()) == 1
            for node,table in ((old,oi),(root,ids)):
                node[table['spring_strength']] = .4
                node[table['shake_strength']] = .15
                node[table['drift_strength']] = .2
                node[table['pan']] = 3.
                if mode < 2:
                    motion = 'angle' if mode == 0 else 'progress'
                    key(node,table[motion],[(0,0.),(60,180. if mode == 0 else 1.),(120,180. if mode == 0 else 1.)])
            if mode == 2:
                desc = c4d.DescID(c4d.DescLevel(c4d.ID_BASEOBJECT_REL_POSITION,c4d.DTYPE_VECTOR,0),c4d.DescLevel(c4d.VECTOR_X,c4d.DTYPE_REAL,0))
                for node in (oo[11],objects[11]):
                    key(node,desc,[(0,500.),(60,800.),(120,800.)])
            for frame in (0,12.5,30,60,75.25,120,30,0):
                evaluate(frame)
                assert root[ids['status']].endswith('prototype: ready'), root[ids['status']]
                assert old[oi['status']].endswith('prototype: ready'), old[oi['status']]
                near(objects[8].GetMg(),oo[8].GetMg())
            passed.append(('Orbit','Trajectory','Free')[mode]+': UI/source pruning; animated camera matches legacy with all FX')
        evaluate(30)
        expected = {root.GetName():objects[8].GetMg() for root,objects,ids in roots}
        path = folder.parents[1]/'tests'/'artifacts'/('cine_variants_'+uuid.uuid4().hex+'.c4d')
        path.parent.mkdir(parents=True,exist_ok=True)
        assert c4d.documents.SaveDocument(document,str(path),c4d.SAVEDOCUMENTFLAGS_DONTADDTORECENTLIST,c4d.FORMAT_C4DEXPORT)
        loaded = c4d.documents.LoadDocument(str(path),c4d.SCENEFILTER_OBJECTS | c4d.SCENEFILTER_MATERIALS,None)
        assert loaded is not None
        try:
            loaded.SetTime(c4d.BaseTime(30,30))
            loaded.ExecutePasses(None,True,True,True,c4d.BUILDFLAGS_NONE)
            count = 0
            node = loaded.GetFirstObject()
            while node is not None:
                if node.GetName() in expected:
                    table = next(ids for root,objects,ids in roots if root.GetName()==node.GetName())
                    near(node[table['camera']].GetMg(),expected[node.GetName()])
                    count += 1
                node = node.GetNext()
            assert count == 3
        finally:
            c4d.documents.KillDocument(loaded)
        passed.append('all three fixed rigs reproduce camera after save/load with cold cache')
        return {'status':'PASS','checks':passed,'artifact':str(path),
                'boundary':'owned local C4D; no farm or render acceptance'}
    finally:
        c4d.documents.KillDocument(document)
