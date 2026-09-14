"""Historical source sampling adapted from CamRig 1.6 and CK_CAM live previews.

Only direct coordinate/UD keys and static editable geometry are supported.
No SetTime/ExecutePasses, scene mutation, or retained live object references.
"""
import math
import c4d

_INERTIA = {'signature': None, 'states': []}
_UNIT_CIRCLE = None


def xyz(vector):
    return vector.x, vector.y, vector.z


def ud_desc(key):
    return c4d.DescID(c4d.DescLevel(c4d.ID_USERDATA, c4d.DTYPE_SUBCONTAINER, 0),
                     c4d.DescLevel(UD[key], c4d.DTYPE_LONG if key == 'seed' else c4d.DTYPE_REAL, 0))


def require_constant(root, key):
    if root.FindCTrack(ud_desc(key)):
        raise ValueError(key + ' is a per-shot setting; animate Strength instead')


def historical_reader(node, desc, document):
    live = float(node[desc])
    track = node.FindCTrack(desc)
    if not math.isfinite(live):
        raise ValueError('Non-finite motion source')
    if track is None:
        return lambda time: live, ('value', live)
    if track.GetBefore() != c4d.CLOOP_CONSTANT or track.GetAfter() != c4d.CLOOP_CONSTANT:
        raise ValueError('Inertia requires constant key extrapolation')
    curve = track.GetCurve()
    keyed = curve.GetValue(document.GetTime(), document.GetFps())
    if not math.isclose(live, keyed, rel_tol=1e-8, abs_tol=1e-8):
        return lambda time: live, ('preview', live)
    signature = tuple((curve.GetKey(i).GetTime().Get(), curve.GetKey(i).GetValue(),
                       curve.GetKey(i).GetInterpolation(), curve.GetKey(i).GetTimeLeft().Get(),
                       curve.GetKey(i).GetTimeRight().Get(), curve.GetKey(i).GetValueLeft(),
                       curve.GetKey(i).GetValueRight()) for i in range(curve.GetKeyCount()))
    def sample(time):
        value = curve.GetValue(c4d.BaseTime(int(round(time * 1000000)), 1000000), document.GetFps())
        if not math.isfinite(value):
            raise ValueError('Non-finite historical key value')
        return value
    return sample, ('keys', signature)


def transform_reader(node, root, signature):
    if node is None:
        return lambda time: c4d.Matrix()
    for tag in node.GetTags():
        if tag.GetInfo() & c4d.TAG_EXPRESSION:
            if not (node == root and tag.GetType() == c4d.Tpython and
                    tag.GetDataInstance().GetInt32(ROLE_ID) in (1, 2)):
                raise ValueError('Inertia source has an expression driver: ' + node.GetName())
    if node.GetFrozenPos().GetLength() > 1e-8 or node.GetFrozenRot().GetLength() > 1e-8 or (node.GetFrozenScale()-c4d.Vector(1)).GetLength() > 1e-8:
        raise ValueError('Inertia source has frozen transforms')
    if (node.GetRelScale()-c4d.Vector(1)).GetLength() > 1e-8:
        raise ValueError('Inertia source scale must be 1')
    for track in node.GetCTracks():
        if track.GetDescriptionID()[0].id not in (c4d.ID_USERDATA, c4d.ID_BASEOBJECT_REL_POSITION, c4d.ID_BASEOBJECT_REL_ROTATION):
            raise ValueError('Inertia source supports direct position/rotation keys only')
    readers = []
    signature.append(('node', str(node.GetGUID()), node.GetRotationOrder()))
    for base in (c4d.ID_BASEOBJECT_REL_POSITION, c4d.ID_BASEOBJECT_REL_ROTATION):
        for axis in (c4d.VECTOR_X, c4d.VECTOR_Y, c4d.VECTOR_Z):
            desc = c4d.DescID(c4d.DescLevel(base, c4d.DTYPE_VECTOR, 0), c4d.DescLevel(axis, c4d.DTYPE_REAL, 0))
            reader, stamp = historical_reader(node, desc, root.GetDocument())
            readers.append(reader)
            signature.append(stamp)
    parent = transform_reader(node.GetUp(), root, signature)
    order = node.GetRotationOrder()
    def sample(time):
        matrix = c4d.utils.HPBToMatrix(c4d.Vector(*(fn(time) for fn in readers[3:])), order)
        matrix.off = c4d.Vector(*(fn(time) for fn in readers[:3]))
        return parent(time) * matrix
    return sample


def motion_source(root, objects, signature):
    global _UNIT_CIRCLE
    document = root.GetDocument()
    takes = document.GetTakeData()
    if takes and takes.GetCurrentTake() != takes.GetMainTake():
        raise ValueError('Inertia requires Main Take')
    mode = read(root, 'movement_mode')
    keys = ['offset_x', 'offset_y', 'offset_z']
    keys += ['angle', 'radius', 'height'] if mode == 0 else ['progress'] if mode == 1 else []
    values = {}
    for key in keys:
        values[key], stamp = historical_reader(root, ud_desc(key), document)
        signature.append((key, stamp))
    root_at = transform_reader(root, root, signature)
    driven = tuple(objects[i] for i in (4, 5, 6, 7, 8, 9, 12, 13) if i in objects)
    if mode == 0:
        source = source_link(root, read(root, 'center'), objects[2], driven)
        transform = transform_reader(source, root, signature)
        if _UNIT_CIRCLE is None:
            circle = c4d.BaseObject(c4d.Osplinecircle)
            circle[c4d.PRIM_PLANE] = c4d.PRIM_PLANE_XZ
            circle[c4d.PRIM_CIRCLE_RADIUS] = 1.
            helper = c4d.utils.SplineHelp()
            if not helper.InitSplineWith(circle, c4d.SPLINEHELPFLAGS_NONE):
                raise ValueError('Cannot initialize inertia orbit sampler')
            spline = circle.GetRealSpline()
            length = c4d.utils.SplineLengthData()
            if not length.Init(spline):
                raise ValueError('Cannot initialize orbit length')
            _UNIT_CIRCLE = circle, helper, spline, length
        spline, length = _UNIT_CIRCLE[2:]
    elif mode == 1:
        source = source_link(root, read(root, 'path'), objects[10], driven)
        transform = transform_reader(source, root, signature)
        if source.GetChildren() or source.GetDeformCache() is not None:
            raise ValueError('Inertia requires a static undeformed spline')
        spline = source
        signature.append(('geometry', source[c4d.SPLINEOBJECT_TYPE], source.IsClosed(), tuple(xyz(p) for p in source.GetAllPoints()),
                          tuple((xyz(source.GetTangent(i)['vl']), xyz(source.GetTangent(i)['vr'])) for i in range(source.GetPointCount()))))
    else:
        source = source_link(root, read(root, 'free'), objects[11], driven)
        transform = transform_reader(source, root, signature)
    def sample(time):
        offset = c4d.Vector(*(values['offset_' + axis](time) for axis in ('x', 'y', 'z')))
        if mode == 2:
            return transform(time) * offset
        matrix = root_at(time)
        if mode == 0:
            phase = (values['angle'](time) % 360.) / 360.
            point = spline.GetSplinePoint(length.UniformToNatural(phase)) * max(.001, values['radius'](time))
            return transform(time).off + matrix.MulV(point + c4d.Vector(0, values['height'](time), 0) + offset)
        phase = min(1., max(0., values['progress'](time)))
        return transform(time) * spline.GetSplinePoint(phase) + matrix.MulV(offset)
    return sample


def execute_inertia(root, objects):
    amount = number(root, 'spring_strength')
    inertia = objects[12]
    if amount <= 0:
        inertia.SetRelPos(c4d.Vector())
        return
    require_constant(root, 'spring_response')
    require_constant(root, 'spring_damping')
    omega, damping = parameters(number(root, 'spring_response'), number(root, 'spring_damping'))
    document = root.GetDocument()
    start = document.GetMinTime().Get()
    if document.GetTime().Get() < start:
        inertia.SetRelPos(c4d.Vector())
        return
    time = max(start, document.GetTime().Get())
    index = int(math.floor((time - start) * 120 + 1e-8))
    if index > 60000:
        raise ValueError('Inertia prototype limit: 500 seconds from project start')
    signature = [str(root.GetGUID()), start, document.GetFps(), read(root, 'movement_mode'), omega, damping]
    source = motion_source(root, objects, signature)
    signature = tuple(signature)
    base = objects[9].GetMg().off
    current = source(time)
    if (current - base).GetLength() > .05:
        raise ValueError('Inertia source differs from native motion by %.3f cm at %.3f s (mode %s)' %
                         ((current-base).GetLength(), time, read(root, 'movement_mode')))
    if _INERTIA['signature'] != signature:
        _INERTIA['signature'] = signature
        _INERTIA['states'] = [(xyz(source(start)), (0., 0., 0.))]
    states = _INERTIA['states']
    for step in range(len(states)-1, index):
        t0 = start + step / 120.
        states.append(step_vector(*states[-1], xyz(source(t0)), xyz(source(t0 + 1/120.)), 1/120., omega, damping))
    position, velocity = states[index]
    t0 = start + index / 120.
    if time - t0 > 1e-9:
        position, velocity = step_vector(position, velocity, xyz(source(t0)), xyz(current), time-t0, omega, damping)
    desired = base + (c4d.Vector(*position) - current) * min(1., amount)
    inertia.SetRelPos(~objects[9].GetMg() * desired)
