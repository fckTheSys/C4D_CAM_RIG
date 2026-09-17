"""Independent prototype builder. Run in C4D; never modifies legacy rigs."""
import hashlib
from pathlib import Path
import c4d

ROLE_ID=10699101
VERSION='0.5.7'
# Service nodes live on one shared layer: hidden in managers and viewport, but
# still evaluated. Root, Camera, World Target and Local Target stay visible.
LAYER_NAME='L_CAM_RIG'
SERVICE_ROLES=(2,4,5,6,7,8)
# Embedded runtimes that upgrade_runtime() may replace; nothing else is touched.
UPGRADABLE_RUNTIMES={'88b13ae03be446b6ecb3f671e0e89fa5b9657f52d5d6412a4551b43931b7e3e0':'0.5.6'}
DEFAULTS={'Progress':0.0,'Height':170.0,'Body X':0.0,'Body Y':0.0,'Body Z':0.0,
          'Pan':0.0,'Tilt':0.0,'Roll':0.0,'Walk Strength':1.0,'Step Length':70.0,
          'Walk Amplitude':2.0,'Walk Lean':1.0,'Softness':0.8,'Full Walk Speed':40.0,
          'Shake Strength':0.0,'Shake Frequency':2.0,'Shake Position':0.5,'Shake Rotation':0.3,
          'Drift Strength':0.0,'Drift Frequency':0.15,'Drift Position':0.5,'Drift Rotation':0.3,'Seed':1.0}


def _group(root, name, parent=None):
    """Adapted from CamRig ud_build.add_group; no legacy module dependency."""
    bc = c4d.GetCustomDataTypeDefault(c4d.DTYPE_GROUP)
    bc[c4d.DESC_NAME] = name
    bc[c4d.DESC_TITLEBAR] = True
    if parent is not None:
        bc[c4d.DESC_PARENTGROUP] = parent
    return root.AddUserData(bc)


def _controls(root):
    """Keep runtime lookup names stable; ranges affect sliders, not position keys."""
    route = _group(root, 'Route / Body')
    body = _group(root, 'Body Offset - jump (cm)', route)
    look = _group(root, 'Look')
    motion = _group(root, 'Motion')
    walk_group = _group(root, 'Walk', motion)
    shake = _group(root, 'Shake', motion)
    drift = _group(root, 'Drift', motion)
    camera = _group(root, 'Camera')
    ids = {}
    for name, value in DEFAULTS.items():
        parent, low, high, step, label = motion, 0.0, 1.0, .01, name
        if name == 'Progress':
            parent, label = route, 'Progress'
        elif name == 'Height' or name.startswith('Body '):
            parent = route if name == 'Height' else body
            low, high, step, label = -200.0, 300.0, 1.0, name + ' (cm)'
        elif name in ('Pan', 'Tilt', 'Roll'):
            parent, low, high, step, label = look, -180.0, 180.0, 1.0, name + ' (deg)'
        elif name.startswith('Walk ') or name in ('Step Length', 'Softness', 'Full Walk Speed'):
            parent = walk_group
            if name == 'Step Length':
                low, high, step, label = 10.0, 150.0, 1.0, 'Step Length (cm)'
            elif name == 'Full Walk Speed':
                low, high, step, label = 1.0, 200.0, 1.0, 'Full Walk Speed (cm/s)'
            elif name == 'Walk Amplitude':
                high, step, label = 10.0, .1, 'Amplitude (cm)'
            elif name == 'Walk Lean':
                high, step, label = 10.0, .1, 'Lean (deg)'
            elif name == 'Walk Strength':
                label = 'Strength (0-1)'
        elif name.startswith(('Shake ', 'Drift ')):
            parent = shake if name.startswith('Shake ') else drift
            label = name.split(' ', 1)[1]
            if name.endswith('Frequency'):
                high = 10.0 if parent == shake else 1.0
                label += ' (Hz)'
            elif name.endswith('Position'):
                high, step, label = 10.0, .1, label + ' (cm)'
            elif name.endswith('Rotation'):
                high, step, label = 10.0, .1, label + ' (deg)'
        elif name == 'Seed':
            high, step = 1000.0, 1.0
        bc = c4d.GetCustomDataTypeDefault(c4d.DTYPE_REAL)
        bc[c4d.DESC_NAME] = name
        bc[c4d.DESC_SHORT_NAME] = label
        bc[c4d.DESC_PARENTGROUP] = parent
        bc[c4d.DESC_CUSTOMGUI] = c4d.CUSTOMGUI_REALSLIDER
        bc[c4d.DESC_MINSLIDER] = low
        bc[c4d.DESC_MAXSLIDER] = high
        bc[c4d.DESC_STEP] = step
        if name == 'Progress':
            bc[c4d.DESC_UNIT] = c4d.DESC_UNIT_PERCENT
        # No DESC_MIN/MAX on spatial/angle/progress controls: overshoot and
        # multi-turn keys remain available. Runtime validates motion domains.
        if name in ('Step Length', 'Full Walk Speed'):
            bc[c4d.DESC_MIN] = .001
        elif name == 'Softness':
            bc[c4d.DESC_MIN], bc[c4d.DESC_MAX] = 0.0, 1.0
        elif name not in ('Progress', 'Height', 'Pan', 'Tilt', 'Roll', 'Seed') and not name.startswith('Body '):
            bc[c4d.DESC_MIN] = 0.0
        ids[name] = root.AddUserData(bc)
        root[ids[name]] = value
    bc = c4d.GetCustomDataTypeDefault(c4d.DTYPE_LONG)
    bc[c4d.DESC_NAME] = 'Aim Mode'
    bc[c4d.DESC_PARENTGROUP] = look
    bc[c4d.DESC_ANIMATE] = c4d.DESC_ANIMATE_OFF
    cycle=c4d.BaseContainer()
    for i,name in enumerate(('Manual','World Target','Local Target')): cycle[i]=name
    bc[c4d.DESC_CYCLE]=cycle
    ids['Aim Mode'] = root.AddUserData(bc)
    root[ids['Aim Mode']] = 1
    bc = c4d.GetCustomDataTypeDefault(c4d.DTYPE_STRING)
    bc[c4d.DESC_NAME] = 'Lens controls'
    bc[c4d.DESC_PARENTGROUP] = camera
    bc[c4d.DESC_CUSTOMGUI] = c4d.CUSTOMGUI_STATICTEXT
    info = root.AddUserData(bc)
    root[info] = 'Select Camera in the hierarchy: lens, exposure and DOF are native Redshift settings.'
    for name, parent in (('Path', route), ('Target', look), ('Camera', camera)):
        bc = c4d.GetCustomDataTypeDefault(c4d.DTYPE_BASELISTLINK)
        bc[c4d.DESC_NAME] = name
        bc[c4d.DESC_PARENTGROUP] = parent
        bc[c4d.DESC_CUSTOMGUI] = c4d.CUSTOMGUI_LINKBOX
        bc[c4d.DESC_ANIMATE] = c4d.DESC_ANIMATE_OFF
        bc[c4d.DESC_EDITABLE] = name in ('Path','Target')
        if name=='Target': bc[c4d.DESC_SHORT_NAME]='World Target'
        ids[name] = root.AddUserData(bc)
    bc = c4d.GetCustomDataTypeDefault(c4d.DTYPE_STRING)
    bc[c4d.DESC_NAME] = 'Status'
    bc[c4d.DESC_PARENTGROUP] = route
    bc[c4d.DESC_CUSTOMGUI] = c4d.CUSTOMGUI_STATICTEXT
    bc[c4d.DESC_EDITABLE] = False
    bc[c4d.DESC_ANIMATE] = c4d.DESC_ANIMATE_OFF
    ids['Status'] = root.AddUserData(bc)
    root[ids['Status']] = ''
    return ids


def source():
    folder=Path(__file__).parent
    helpers=folder/'path_source.py'
    if not helpers.is_file(): helpers=folder.parent/'path_source.py'
    return '\n\n'.join(p.read_text(encoding='utf-8') for p in
                       (helpers,helpers.with_name('look_source.py'),folder/'motion_math.py',folder/'path_math.py',folder/'curve_math.py',folder/'runtime.py'))


def runtime_sha(text):
    return hashlib.sha256((text or '').replace(chr(13)+chr(10),chr(10)).replace(chr(13),chr(10)).encode('utf-8')).hexdigest()


def rig_layer(document,create=True):
    """Return (layer, created). A created layer is already inserted: record Undo."""
    stack=[document.GetLayerObjectRoot().GetDown()]
    while stack:
        layer=stack.pop()
        while layer is not None:
            if layer.GetName()==LAYER_NAME:
                return layer,False
            stack.append(layer.GetDown());layer=layer.GetNext()
    if not create:
        return None,False
    layer=c4d.documents.LayerObject();layer.SetName(LAYER_NAME)
    layer.InsertUnderLast(document.GetLayerObjectRoot())
    layer.SetLayerData(document,{'solo':False,'view':False,'render':True,'manager':False,
                                 'locked':False,'generators':True,'deformers':True,
                                 'expressions':True,'animation':True,'xref':True})
    layer[c4d.ID_LAYER_COLOR]=c4d.Vector(.35)
    return layer,True


def service_nodes(obj):
    return [obj[role] for role in SERVICE_ROLES if role in obj]


def assign_layer(document,obj,undo=None):
    """Put unlayered service nodes on L_CAM_RIG; a user's own layer choice is kept."""
    nodes=[node for node in service_nodes(obj) if node.GetLayerObject(document) is None]
    if not nodes:
        return None,False
    layer,created=rig_layer(document)
    if undo is not None:
        if created: undo(c4d.UNDOTYPE_NEWOBJ,layer)
        for node in nodes: undo(c4d.UNDOTYPE_CHANGE_SMALL,node)
    for node in nodes:
        node[c4d.ID_LAYER_LINK]=layer
    return layer,created


def apply_names(obj,name):
    """Camera shares the rig name so viewport camera menus stay readable."""
    name=(name or '').strip()
    if not name: raise ValueError('Rig name cannot be empty')
    obj[1].SetName(name);obj[9].SetName(name)
    obj[3].SetName(name+'_TGT')
    if 10 in obj: obj[10].SetName(name+'_LTGT')


def names_synced(obj):
    name=obj[1].GetName()
    return (obj[9].GetName()==name and obj[3].GetName()==name+'_TGT' and
            (10 not in obj or obj[10].GetName()==name+'_LTGT'))


def runtime_tags(root):
    tags=[tag for tag in root.GetTags() if tag.GetType()==c4d.Tpython]
    if len(tags)!=2 or sorted(tag.GetDataInstance().GetInt32(ROLE_ID) for tag in tags)!=[1,2]:
        raise ValueError('Expected exactly Prepare and Finish runtime tags')
    return tags


def upgrade_runtime(root,code=None):
    """Replace a known older embedded runtime. Caller owns Undo and evaluation."""
    code=source() if code is None else code
    tags=runtime_tags(root)
    digests={runtime_sha(tag[c4d.TPYTHON_CODE]) for tag in tags}
    if digests=={runtime_sha(code)}:
        return False
    if len(digests)!=1 or not digests<=set(UPGRADABLE_RUNTIMES):
        raise ValueError('Unknown embedded CK_CAM runtime; refusing to overwrite it')
    for tag in tags:
        tag[c4d.TPYTHON_CODE]=code
    return True


def _walk(node):
    while node:
        yield node
        yield from _walk(node.GetDown())
        node=node.GetNext()


def rig_nodes(root):
    obj,stack={},[root]
    while stack:
        node=stack.pop();role=node.GetDataInstance().GetInt32(ROLE_ID)
        if role:
            if role in obj: raise ValueError('Duplicate CK_CAM role')
            obj[role]=node
        stack.extend(node.GetChildren())
    if 1 not in obj or 3 not in obj or 9 not in obj or obj[1]!=root:
        raise ValueError('Select a CK_CAM root')
    return obj


def _control(root,name):
    return next((desc for desc,bc in root.GetUserDataContainer() if bc[c4d.DESC_NAME]==name),None)


def _index(document,root):
    return next(i for i,node in enumerate(_walk(document.GetFirstObject())) if node==root)


def _frames(document,obj,limit=64):
    """Range ends, eighths, current time and every key +-1 frame of root and Local Target."""
    fps=document.GetFps()
    low,high=document.GetMinTime().GetFrame(fps),document.GetMaxTime().GetFrame(fps)
    frames={low,high,document.GetTime().GetFrame(fps)}|{low+(high-low)*i//8 for i in range(1,8)}
    for node in (obj[1],obj.get(10)):
        for track in (node.GetCTracks() if node is not None else ()):
            curve=track.GetCurve()
            for i in range(curve.GetKeyCount()):
                frame=curve.GetKey(i).GetTime().GetFrame(fps)
                frames.update((frame-1,frame,frame+1))
    frames=sorted(frames)
    if len(frames)>limit:
        step=(len(frames)-1)/(limit-1)
        frames=sorted({frames[round(i*step)] for i in range(limit)})
    return frames


def _sample(document,index,frames):
    root=list(_walk(document.GetFirstObject()))[index]
    camera,status,rows=rig_nodes(root)[9],_control(root,'Status'),[]
    for frame in frames:
        document.SetTime(c4d.BaseTime(frame,document.GetFps()))
        document.ExecutePasses(None,True,True,True,c4d.BUILDFLAGS_INTERNALRENDERER)
        m=camera.GetMg()
        rows.append(([c for v in (m.off,m.v1,m.v2,m.v3) for c in (v.x,v.y,v.z)],
                     str(root[status]) if status else ''))
    return rows


def _not_ready(rows,frames):
    return next(((frame,status) for frame,(_,status) in zip(frames,rows) if status.lower()!='ready'),None)


def _error(a,b):
    return max(abs(x-y) for (ma,_),(mb,_) in zip(a,b) for x,y in zip(ma,mb))


def _clone(document):
    clone=document.GetClone(c4d.COPYFLAGS_NONE)
    if clone is None: raise RuntimeError('Could not clone document for upgrade check')
    return clone


def _reference(document,root,frames):
    """Camera before upgrade on a detached copy.

    Every compared frame must be Ready. An old rig that is not Ready only because
    it already sits in groups is measured on a copy moved to top level with the
    same world matrix; any other failure refuses the upgrade."""
    index=_index(document,root)
    clone=_clone(document)
    try:
        rows=_sample(clone,index,frames)
        failure=_not_ready(rows,frames)
        if failure is None:
            return rows,'in_place'
    finally:
        c4d.documents.KillDocument(clone)
    if root.GetUp() is None:
        raise ValueError('Rig is not Ready at frame %d before upgrade (%s); fix it first'%failure)
    clone=_clone(document)
    try:
        copied=list(_walk(clone.GetFirstObject()))[index]
        world=copied.GetMg()
        copied.Remove();clone.InsertObject(copied);copied.SetMg(world)
        rows=_sample(clone,_index(clone,copied),frames)
        failure=_not_ready(rows,frames)
        if failure is not None:
            raise ValueError('Rig is not Ready at frame %d even outside its groups (%s); refusing'%failure)
        return rows,'top_level_copy'
    finally:
        c4d.documents.KillDocument(clone)


def verify_upgrade(document,root,tolerance=1e-4):
    """Upgrade a detached copy and compare it with the pre-upgrade camera.

    Returns (report, expected rows). The live document is untouched."""
    obj=rig_nodes(root)
    frames=_frames(document,obj)
    reference,basis=_reference(document,root,frames)
    index=_index(document,root)
    clone=_clone(document)
    try:
        copied=list(_walk(clone.GetFirstObject()))[index]
        changed=upgrade_runtime(copied)
        assign_layer(clone,rig_nodes(copied))
        after=_sample(clone,index,frames)
    finally:
        c4d.documents.KillDocument(clone)
    failure=_not_ready(after,frames)
    if failure is not None:
        raise ValueError('Upgraded rig is not Ready at frame %d (%s); refusing'%failure)
    error=_error(reference,after)
    if error>tolerance:
        raise ValueError('Upgrade changes the camera by %.6g; refusing'%error)
    return {'changed':changed,'frames':frames,'reference':basis,'max_error':error},after


def check_live(document,root,report,expected,tolerance=1e-4):
    """Compare the applied live upgrade with the verified copy on a detached clone."""
    clone=_clone(document)
    try:
        live=_sample(clone,_index(document,root),report['frames'])
    finally:
        c4d.documents.KillDocument(clone)
    failure=_not_ready(live,report['frames'])
    error=_error(expected,live)
    if failure is not None or error>tolerance:
        raise ValueError('Live upgrade differs from the verified copy (%.6g)'%error)
    return error


def verified_upgrade(document,root,tolerance=1e-4):
    return verify_upgrade(document,root,tolerance)[0]


def upgrade(document,root):
    """Verified, single-Undo upgrade of one rig; undone if the live result differs."""
    report,expected=verify_upgrade(document,root)
    obj=rig_nodes(root)
    document.StartUndo()
    try:
        for tag in runtime_tags(root): document.AddUndo(c4d.UNDOTYPE_CHANGE_SMALL,tag)
        upgrade_runtime(root)
        assign_layer(document,obj,document.AddUndo)
    finally:
        document.EndUndo()
    try:
        report['live_error']=check_live(document,root,report,expected)
    except Exception:
        document.DoUndo()
        raise
    return report


def priority(tag,value):
    data=c4d.PriorityData()
    data.SetPriorityValue(c4d.PRIORITYVALUE_MODE,c4d.CYCLE_GENERATORS)
    data.SetPriorityValue(c4d.PRIORITYVALUE_PRIORITY,130+value)
    tag[c4d.EXPRESSION_PRIORITY]=data


def build(document,name='CK_CAM'):
    root=c4d.BaseObject(c4d.Onull)
    root.GetDataInstance().SetInt32(ROLE_ID,1)
    obj={1:root}
    for role,label,parent in [(2,'Path',1),(3,'Target',1),(4,'Route',1),(5,'Body',4),
                              (10,'Local Target',5),(6,'Aim',5),(7,'Look',6),(8,'FX',7),(9,'Camera',8)]:
        node=c4d.SplineObject(3,c4d.SPLINETYPE_BEZIER) if role==2 else c4d.BaseObject(1057516 if role==9 else c4d.Onull)
        if node is None: raise RuntimeError('Required native object unavailable')
        node.SetName(label);node.GetDataInstance().SetInt32(ROLE_ID,role)
        node.InsertUnder(obj[parent]);obj[role]=node
    obj[10].SetRelPos(c4d.Vector(0,0,300))
    for role,shape,color in ((3,c4d.NULLOBJECT_DISPLAY_SPHERE,c4d.Vector(1,.65,.1)),(10,c4d.NULLOBJECT_DISPLAY_TRIANGLE,c4d.Vector(.1,.8,1))):
        obj[role][c4d.NULLOBJECT_DISPLAY]=shape
        obj[role][c4d.NULLOBJECT_RADIUS]=20.
        obj[role][c4d.ID_BASEOBJECT_USECOLOR]=c4d.ID_BASEOBJECT_USECOLOR_ALWAYS
        obj[role][c4d.ID_BASEOBJECT_COLOR]=color
    path=obj[2]
    path.SetAllPoints([c4d.Vector(0),c4d.Vector(100,0,300),c4d.Vector(-50,0,1200)])
    for i,left,right in [(0,c4d.Vector(0,0,-20),c4d.Vector(0,0,20)),
                         (1,c4d.Vector(-60,0,-150),c4d.Vector(60,0,150)),
                         (2,c4d.Vector(120,0,-350),c4d.Vector(-120,0,350))]:
        path.SetTangent(i,left,right)
    path.Message(c4d.MSG_UPDATE)
    obj[3].SetRelPos(c4d.Vector(250,170,1800))
    ids=_controls(root)
    for link, role in (('Path',2),('Target',3),('Camera',9)):
        root[ids[link]]=obj[role]
    align=c4d.BaseTag(c4d.Taligntospline);obj[4].InsertTag(align)
    align[c4d.ALIGNTOSPLINETAG_LINK]=path;align[c4d.ALIGNTOSPLINETAG_TANGENTIAL]=False
    priority(align,-20)
    target=c4d.BaseTag(c4d.Ttargetexpression);obj[6].InsertTag(target)
    target[c4d.TARGETEXPRESSIONTAG_LINK]=obj[3];priority(target,-10)
    code=source()
    for role,value,stage in [(1,-30,'Prepare'),(2,10,'Finish')]:
        tag=c4d.BaseTag(c4d.Tpython);root.InsertTag(tag);tag.SetName('CK_CAM '+stage)
        tag.GetDataInstance().SetInt32(ROLE_ID,role);tag[c4d.TPYTHON_CODE]=code;priority(tag,value)
    apply_names(obj,name)
    document.StartUndo()
    try:
        document.InsertObject(root);document.AddUndo(c4d.UNDOTYPE_NEWOBJ,root)
        _,created=assign_layer(document,obj)
        if created: document.AddUndo(c4d.UNDOTYPE_NEWOBJ,rig_layer(document,False)[0])
    finally: document.EndUndo()
    return root,obj,ids


def key(document,root,desc,values):
    if root.FindCTrack(desc): raise ValueError('Refuse replacement of existing track')
    track=c4d.CTrack(root,desc);root.InsertTrackSorted(track);curve=track.GetCurve()
    for frame,value in values:
        k=curve.AddKey(c4d.BaseTime(frame,document.GetFps()))['key']
        k.SetValue(curve,value);k.SetInterpolation(curve,c4d.CINTERPOLATION_LINEAR)


def fixture():
    document=c4d.documents.BaseDocument();document.SetFps(30)
    document.SetMaxTime(c4d.BaseTime(180,30))
    root,obj,ids=build(document)
    key(document,root,ids['Progress'],[(0,0),(15,0),(90,.8),(120,.8),(150,.5),(180,1)])
    key(document,root,ids['Body Y'],[(0,0),(120,0),(130,-8),(150,100),(170,0),(175,-5),(180,0)])
    key(document,root,ids['Walk Strength'],[(0,1),(125,1),(132,0),(170,0),(180,1)])
    root[ids['Shake Strength']]=0.2;root[ids['Drift Strength']]=0.2
    return document,root,obj,ids
