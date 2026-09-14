"""Three fixed-purpose Cine rigs; the universal P3 builder stays frozen."""
from pathlib import Path
import c4d

ROLE_ID = 10699220
VERSION = '0.4.0-prototype'


def group(root, name, parent=None):
    bc = c4d.GetCustomDataTypeDefault(c4d.DTYPE_GROUP)
    bc[c4d.DESC_NAME] = name
    bc[c4d.DESC_TITLEBAR] = True
    # All sections share the native User Data panel.
    bc[c4d.DESC_PARENTGROUP] = c4d.DescID(c4d.DescLevel(c4d.ID_USERDATA)) if parent is None else parent
    bc[c4d.DESC_GUIOPEN] = True
    return root.AddUserData(bc)


def controls(root, mode):
    movement = group(root, 'Main')
    orbit = group(root, 'Orbit') if mode == 0 else None
    path = group(root, 'Trajectory') if mode == 1 else None
    free = group(root, 'Free') if mode == 2 else None
    look = group(root, 'Look')
    optics = group(root, 'Camera')
    effects = group(root, 'Effects')
    inertia = group(root, 'Inertia', effects)
    shake = group(root, 'Shake', effects)
    drift = group(root, 'Drift', effects)
    ids = {}

    def add(key, label, dtype, parent, default=None, minimum=None, maximum=None):
        if key == 'movement_mode' or key.endswith('_hint'):
            return
        sections = {0: ('angle','radius','height','center'), 1: ('path','progress'), 2: ('free',)}
        if any(key in keys and mode != owner for owner, keys in sections.items()):
            return
        bc = c4d.GetCustomDataTypeDefault(dtype)
        bc[c4d.DESC_NAME] = label
        bc[c4d.DESC_PARENTGROUP] = parent
        if dtype == c4d.DTYPE_REAL:
            bc[c4d.DESC_CUSTOMGUI] = c4d.CUSTOMGUI_REALSLIDER
            bc[c4d.DESC_MINSLIDER] = minimum
            bc[c4d.DESC_MAXSLIDER] = maximum
            bc[c4d.DESC_STEP] = 1.0
            if key == 'radius':
                bc[c4d.DESC_MIN] = 0.001
        else:
            bc[c4d.DESC_ANIMATE] = c4d.DESC_ANIMATE_OFF
        if dtype == c4d.DTYPE_BASELISTLINK:
            bc[c4d.DESC_CUSTOMGUI] = c4d.CUSTOMGUI_LINKBOX
        if dtype == c4d.DTYPE_STRING:
            bc[c4d.DESC_CUSTOMGUI] = c4d.CUSTOMGUI_STATICTEXT
            bc[c4d.DESC_EDITABLE] = False
        if key == 'camera':
            bc[c4d.DESC_EDITABLE] = False
        if key in ('aim_mode', 'movement_mode'):
            cycle = c4d.BaseContainer()
            names = ('Manual', 'Target') if key == 'aim_mode' else ('Orbit', 'Trajectory', 'Free')
            for index, name in enumerate(names):
                cycle[index] = name
            bc[c4d.DESC_CYCLE] = cycle
        if key == 'progress':
            bc[c4d.DESC_UNIT] = c4d.DESC_UNIT_PERCENT
            bc[c4d.DESC_MIN], bc[c4d.DESC_MAX] = 0., 1.
            bc[c4d.DESC_STEP] = .01
        if key.startswith(('spring_', 'shake_', 'drift_')):
            bc[c4d.DESC_MIN] = 0.
            bc[c4d.DESC_STEP] = .01
            if key.endswith('strength'):
                bc[c4d.DESC_MAX] = 1.
            if key in ('spring_response', 'spring_damping') or key.endswith('frequency'):
                bc[c4d.DESC_ANIMATE] = c4d.DESC_ANIMATE_OFF
            if key in ('spring_response', 'spring_damping'):
                bc[c4d.DESC_MAX] = 100.
        desc = root.AddUserData(bc)
        ids[key] = desc
        if default is not None:
            root[desc] = default

    add('movement_mode', 'Movement mode', c4d.DTYPE_LONG, movement, 0)
    for key, label, parent in (('orbit_hint', 'Orbit', orbit), ('path_hint', 'Trajectory', path), ('free_hint', 'Free', free)):
        add(key, 'Mode', c4d.DTYPE_STRING, parent,
            'These settings apply only when Main > Movement mode is ' + label + '.')
    add('angle', 'Orbit angle (deg)', c4d.DTYPE_REAL, orbit, 0., -360., 360.)
    add('radius', 'Radius (cm)', c4d.DTYPE_REAL, orbit, 500., 1., 1500.)
    add('height', 'Height above center (cm)', c4d.DTYPE_REAL, orbit, 150., -500., 500.)
    add('center', 'Orbit center', c4d.DTYPE_BASELISTLINK, orbit)
    add('path', 'Trajectory spline', c4d.DTYPE_BASELISTLINK, path)
    add('progress', 'Progress', c4d.DTYPE_REAL, path, 0., 0., 1.)
    add('free', 'Free controller', c4d.DTYPE_BASELISTLINK, free)
    for axis in ('x', 'y', 'z'):
        add('offset_' + axis, 'Local offset ' + axis.upper() + ' (cm)',
            c4d.DTYPE_REAL, movement, 0., -200., 200.)
    add('aim_mode', 'Aim mode', c4d.DTYPE_LONG, look, 1)
    add('target', 'Look target', c4d.DTYPE_BASELISTLINK, look)
    for key, label in (('pan', 'Pan (deg)'), ('tilt', 'Tilt (deg)'), ('roll', 'Roll (deg)')):
        add(key, label, c4d.DTYPE_REAL, look, 0., -180., 180.)
    add('camera', 'Output camera', c4d.DTYPE_BASELISTLINK, optics)
    add('optics', 'Lens / Focus', c4d.DTYPE_STRING, optics,
        'Select Output camera: native focal length, focus distance, DOF and exposure.')
    add('status', 'Status', c4d.DTYPE_STRING, movement, 'Waiting for evaluation')
    add('spring_strength', 'Strength (0-1)', c4d.DTYPE_REAL, inertia, 0., 0., 1.)
    add('spring_response', 'Response (0-100)', c4d.DTYPE_REAL, inertia, 60., 0., 100.)
    add('spring_damping', 'Damping (0-100)', c4d.DTYPE_REAL, inertia, 80., 0., 100.)
    for prefix, parent, frequency, position, rotation in (('shake', shake, 2., .5, .3), ('drift', drift, .15, 1., .5)):
        for suffix, label, value, maximum in (('strength', 'Strength (0-1)', 0., 1.),
                ('frequency', 'Frequency (Hz)', frequency, 10.),
                ('position', 'Position (cm)', position, 10.), ('rotation', 'Rotation (deg)', rotation, 10.)):
            add(prefix + '_' + suffix, label, c4d.DTYPE_REAL, parent, value, 0., maximum)
    add('seed', 'Pattern seed', c4d.DTYPE_LONG, shake, 1)
    return ids


def priority(tag, value):
    data = c4d.PriorityData()
    data.SetPriorityValue(c4d.PRIORITYVALUE_MODE, c4d.CYCLE_EXPRESSION)
    data.SetPriorityValue(c4d.PRIORITYVALUE_PRIORITY, value)
    data.SetPriorityValue(c4d.PRIORITYVALUE_CAMERADEPENDENT, False)
    tag[c4d.EXPRESSION_PRIORITY] = data


def build(document, mode=0, use_redshift=True):
    if type(mode) is not int or mode not in (0, 1, 2):
        raise ValueError('Mode must be 0 (Orbit), 1 (Trajectory), or 2 (Free)')
    if not c4d.threading.GeIsMainThread():
        raise RuntimeError('Builder requires the C4D main thread')
    camera_type = c4d.Ocamera
    if use_redshift and c4d.plugins.FindPlugin(1057516, c4d.PLUGINTYPE_OBJECT):
        camera_type = 1057516
    root = c4d.BaseObject(c4d.Onull)
    root.SetName('Cine ' + ('Orbit', 'Trajectory', 'Free')[mode])
    root.GetDataInstance().SetInt32(ROLE_ID, 1)
    objects = {1: root}
    layout = ((2, 'Orbit Center', 1, c4d.Onull), (3, 'Look Target', 1, c4d.Onull),
              (4, 'Orbit Path', 1, c4d.Osplinecircle), (5, 'Motion', 1, c4d.Onull),
              (9, 'Position Offset', 5, c4d.Onull),
              (12, 'Inertia', 9, c4d.Onull),
              (6, 'Aim', 12, c4d.Onull), (7, 'Frame', 6, c4d.Onull),
              (13, 'Motion FX', 7, c4d.Onull),
              (8, 'Camera', 13, camera_type), (11, 'Free Controller', 1, c4d.Onull))
    for role, name, parent, type_id in layout:
        if role in (2, 4) and mode != 0 or role == 11 and mode != 2:
            continue
        node = c4d.BaseObject(type_id)
        if node is None:
            raise RuntimeError('Required native object unavailable: ' + name)
        node.SetName(name)
        node.GetDataInstance().SetInt32(ROLE_ID, role)
        node.InsertUnderLast(objects[parent])
        objects[role] = node
    if mode == 1:
        path = c4d.SplineObject(3, c4d.SPLINETYPE_BEZIER)
        path.SetName('Trajectory')
        path.GetDataInstance().SetInt32(ROLE_ID, 10)
        path.InsertUnderLast(root)
        path.SetAllPoints([c4d.Vector(-500, 150, -300), c4d.Vector(0, 220, -600), c4d.Vector(500, 150, -300)])
        for index, tangent in enumerate((c4d.Vector(150, 0, -120), c4d.Vector(200, 0, 0), c4d.Vector(150, 0, 120))):
            path.SetTangent(index, -tangent, tangent)
        path.Message(c4d.MSG_UPDATE)
        objects[10] = path
    if mode == 2:
        objects[11].SetRelPos(c4d.Vector(500, 150, 0))
    if mode == 0:
        objects[4][c4d.PRIM_PLANE] = c4d.PRIM_PLANE_XZ
        objects[4][c4d.PRIM_CIRCLE_RADIUS] = 500.
    ids = controls(root, mode)
    for key, role in (('center', 2), ('target', 3), ('camera', 8), ('path', 10), ('free', 11)):
        if key in ids:
            root[ids[key]] = objects[role]
    camera = objects[8]
    focal_id = c4d.RSCAMERAOBJECT_FOCAL_LENGTH if camera_type == 1057516 else c4d.CAMERA_FOCUS
    camera[focal_id] = 36.
    align = c4d.BaseTag(c4d.Taligntospline)
    objects[5].InsertTag(align)
    align[c4d.ALIGNTOSPLINETAG_LINK] = objects.get(4) if mode == 0 else objects.get(10)
    align[c4d.ALIGNTOSPLINETAG_TANGENTIAL] = False
    priority(align, -20)
    target = c4d.BaseTag(c4d.Ttargetexpression)
    objects[6].InsertTag(target)
    target[c4d.TARGETEXPRESSIONTAG_LINK] = objects[3]
    priority(target, -10)
    slots = {key: desc[desc.GetDepth() - 1].id for key, desc in ids.items()}
    folder = Path(__file__).parent
    code = 'UD = ' + repr(slots) + '\nFIXED_MODE = ' + repr(mode) + '\n' + '\n\n'.join(
        (folder / name).read_text(encoding='utf-8') for name in ('effects_math.py', 'inertia.py', 'runtime.py'))
    compile(code, 'Cine Prepare', 'exec')
    tag = c4d.BaseTag(c4d.Tpython)
    tag.SetName('Cine Prepare ' + VERSION)
    tag[c4d.TPYTHON_CODE] = code
    root.InsertTag(tag)
    tag.GetDataInstance().SetInt32(ROLE_ID, 1)
    priority(tag, -30)
    spring = c4d.BaseTag(c4d.Tpython)
    spring.SetName('Cine Inertia ' + VERSION)
    spring[c4d.TPYTHON_CODE] = code
    spring.GetDataInstance().SetInt32(ROLE_ID, 2)
    root.InsertTag(spring)
    priority(spring, -15)
    # Build detached first: errors above leave the document untouched.
    document.StartUndo()
    try:
        document.InsertObject(root)
        document.AddUndo(c4d.UNDOTYPE_NEWOBJ, root)
    finally:
        document.EndUndo()
    return root, objects, ids


if __name__ == '__main__':
    root, _, _ = build(c4d.documents.GetActiveDocument())
    c4d.documents.GetActiveDocument().SetActiveObject(root)
    c4d.EventAdd()
