"""Independent prototype builder. Run in C4D; never modifies legacy rigs."""
from pathlib import Path
import c4d

ROLE_ID=10699101
DEFAULTS={'Progress':0.0,'Height':170.0,'Body X':0.0,'Body Y':0.0,'Body Z':0.0,
          'Pan':0.0,'Tilt':0.0,'Roll':0.0,'Walk Strength':1.0,'Step Length':70.0,
          'Walk Amplitude':2.0,'Walk Lean':1.0,'Softness':0.8,
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
        elif name.startswith('Walk ') or name in ('Step Length', 'Softness'):
            parent = walk_group
            if name == 'Step Length':
                low, high, step, label = 10.0, 150.0, 1.0, 'Step Length (cm)'
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
        if name == 'Step Length':
            bc[c4d.DESC_MIN] = .001
        elif name == 'Softness':
            bc[c4d.DESC_MIN], bc[c4d.DESC_MAX] = 0.0, 1.0
        elif name not in ('Progress', 'Height', 'Pan', 'Tilt', 'Roll', 'Seed') and not name.startswith('Body '):
            bc[c4d.DESC_MIN] = 0.0
        ids[name] = root.AddUserData(bc)
        root[ids[name]] = value
    bc = c4d.GetCustomDataTypeDefault(c4d.DTYPE_BOOL)
    bc[c4d.DESC_NAME] = 'Use Target'
    bc[c4d.DESC_PARENTGROUP] = look
    bc[c4d.DESC_ANIMATE] = c4d.DESC_ANIMATE_OFF
    ids['Use Target'] = root.AddUserData(bc)
    root[ids['Use Target']] = True
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
        bc[c4d.DESC_EDITABLE] = name == 'Path'
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
                       (helpers,folder/'motion_math.py',folder/'path_math.py',folder/'curve_math.py',folder/'runtime.py'))


def priority(tag,value):
    data=c4d.PriorityData()
    data.SetPriorityValue(c4d.PRIORITYVALUE_MODE,c4d.CYCLE_GENERATORS)
    data.SetPriorityValue(c4d.PRIORITYVALUE_PRIORITY,130+value)
    tag[c4d.EXPRESSION_PRIORITY]=data


def build(document):
    root=c4d.BaseObject(c4d.Onull);root.SetName('Simple Camera PROTOTYPE')
    root.GetDataInstance().SetInt32(ROLE_ID,1)
    obj={1:root}
    for role,name,parent in [(2,'Path',1),(3,'Target',1),(4,'Route',1),(5,'Body',4),
                              (6,'Aim',5),(7,'Look',6),(8,'FX',7),(9,'Camera',8)]:
        node=c4d.SplineObject(3,c4d.SPLINETYPE_BEZIER) if role==2 else c4d.BaseObject(1057516 if role==9 else c4d.Onull)
        if node is None: raise RuntimeError('Required native object unavailable')
        node.SetName(name);node.GetDataInstance().SetInt32(ROLE_ID,role)
        node.InsertUnder(obj[parent]);obj[role]=node
    path=obj[2]
    path.SetAllPoints([c4d.Vector(0),c4d.Vector(100,0,300),c4d.Vector(-50,0,1200)])
    for i,left,right in [(0,c4d.Vector(0,0,-20),c4d.Vector(0,0,20)),
                         (1,c4d.Vector(-60,0,-150),c4d.Vector(60,0,150)),
                         (2,c4d.Vector(120,0,-350),c4d.Vector(-120,0,350))]:
        path.SetTangent(i,left,right)
    path.Message(c4d.MSG_UPDATE)
    obj[3].SetRelPos(c4d.Vector(250,170,1800))
    ids=_controls(root)
    for name, role in (('Path',2),('Target',3),('Camera',9)):
        root[ids[name]]=obj[role]
    align=c4d.BaseTag(c4d.Taligntospline);obj[4].InsertTag(align)
    align[c4d.ALIGNTOSPLINETAG_LINK]=path;align[c4d.ALIGNTOSPLINETAG_TANGENTIAL]=False
    priority(align,-20)
    target=c4d.BaseTag(c4d.Ttargetexpression);obj[6].InsertTag(target)
    target[c4d.TARGETEXPRESSIONTAG_LINK]=obj[3];priority(target,-10)
    code=source()
    for role,value,name in [(1,-30,'Prepare'),(2,10,'Finish')]:
        tag=c4d.BaseTag(c4d.Tpython);root.InsertTag(tag);tag.SetName('Simple Camera '+name)
        tag.GetDataInstance().SetInt32(ROLE_ID,role);tag[c4d.TPYTHON_CODE]=code;priority(tag,value)
    document.StartUndo()
    try:
        document.InsertObject(root);document.AddUndo(c4d.UNDOTYPE_NEWOBJ,root)
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
