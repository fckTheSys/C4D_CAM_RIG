"""Cinema 4D source sampler and deterministic Follow Spring cache."""
import math
import c4d
from . import config
from .spring_math import SPRING_HZ, parameters, step_vector
from .tag_embedded import _spring_time

_DESC_COMPONENTS = (c4d.VECTOR_X, c4d.VECTOR_Y, c4d.VECTOR_Z)
def _vector_tuple(value):
    return (value.x, value.y, value.z)

def _desc(base, component):
    return c4d.DescID(c4d.DescLevel(base, c4d.DTYPE_VECTOR, 0), c4d.DescLevel(component, c4d.DTYPE_REAL, 0))

def sample_parameter(obj, desc, time, doc, default=0.0):
    if obj is None or desc is None:
        return default
    track = obj.FindCTrack(desc)
    try:
        if track is not None:
            return track.GetValue(doc, time, doc.GetFps())
        value = obj[desc]
        return default if value is None else value
    except (AttributeError, TypeError, ValueError):
        return default

def sample_component(obj, base, component, time, doc, default=0.0):
    from .tag_embedded import _spring_component
    return _spring_component(obj, base, component, time, doc, default)

def sample_transform(obj, time, doc):
    """Sample local transform tracks without changing document time."""
    if obj is None:
        return c4d.Matrix()
    pos = c4d.Vector(*[sample_component(obj, c4d.ID_BASEOBJECT_REL_POSITION, c, time, doc) for c in _DESC_COMPONENTS])
    rot = c4d.Vector(*[sample_component(obj, c4d.ID_BASEOBJECT_REL_ROTATION, c, time, doc) for c in _DESC_COMPONENTS])
    scale = c4d.Vector(*[sample_component(obj, c4d.ID_BASEOBJECT_REL_SCALE, c, time, doc, 1.0) for c in _DESC_COMPONENTS])
    matrix = c4d.utils.HPBToMatrix(rot)
    matrix.v1 *= scale.x
    matrix.v2 *= scale.y
    matrix.v3 *= scale.z
    matrix.off = pos
    return matrix

def sample_world_transform(obj, time, doc):
    local = sample_transform(obj, time, doc)
    parent = obj.GetUp() if obj is not None else None
    return sample_world_transform(parent, time, doc) * local if parent is not None else local

def source_supported(objs):
    from .tag_embedded import _spring_source_supported
    return _spring_source_supported(objs)

def _ud_desc(rig, name):
    for desc, bc in rig.GetUserDataContainer():
        if bc[c4d.DESC_NAME] == name and desc[-1].dtype != c4d.DTYPE_GROUP:
            return desc
    return None

def sample_ud(rig, name, time, doc, default=0.0):
    return sample_parameter(rig, _ud_desc(rig, name), time, doc, default)

_UNIT_CIRCLE = None

def _unit_sampler():
    from .tag_embedded import _spring_sampler
    return _spring_sampler()

_AXIS_FIX = c4d.Matrix()
_AXIS_FIX.v1 = c4d.Vector(0, 0, -1)
_AXIS_FIX.v2 = c4d.Vector(0, -1, 0)
_AXIS_FIX.v3 = c4d.Vector(-1, 0, 0)

def sample_base_position(objs, time, doc, sampler=None):
    sampler = sampler or _unit_sampler()
    phase = (float(sample_ud(objs.rig, config.UD_ORBIT, time, doc, 0.0)) % 360.0) / 360.0
    radius = max(0.0, float(sample_ud(objs.rig, config.UD_RADIUS, time, doc, config.DEFAULT_RADIUS)))
    root = sample_world_transform(objs.rig, time, doc)
    center = c4d.Vector(
        sample_ud(objs.rig, config.UD_CENTER_X, time, doc, 0.0),
        sample_ud(objs.rig, config.UD_HEIGHT, time, doc, 0.0),
        sample_ud(objs.rig, config.UD_CENTER_Z, time, doc, 0.0),
    )
    linked_desc = _ud_desc(objs.rig, config.UD_ORBIT_CENTER)
    linked = objs.rig[linked_desc] if linked_desc is not None else None
    if isinstance(linked, c4d.BaseObject) and linked.GetDocument() == doc:
        center += (~root * sample_world_transform(linked, time, doc)).off
    plane = c4d.utils.HPBToMatrix(c4d.Vector(
        math.radians(sample_ud(objs.rig, config.UD_PLANE_H, time, doc, 0.0)),
        math.radians(sample_ud(objs.rig, config.UD_PLANE_P, time, doc, 0.0)),
        math.radians(sample_ud(objs.rig, config.UD_PLANE_B, time, doc, 0.0)),
    ))
    plane.off = center
    spline = sampler.GetMatrix(phase)
    follow = spline * _AXIS_FIX
    follow.off *= radius
    offset = c4d.Matrix()
    offset.off = c4d.Vector(
        sample_ud(objs.rig, config.UD_OFFSET_X, time, doc, 0.0),
        sample_ud(objs.rig, config.UD_OFFSET_Y, time, doc, 0.0),
        sample_ud(objs.rig, config.UD_OFFSET_Z, time, doc, 0.0),
    )
    return (root * plane * follow * offset).off

class SpringCache:
    def __init__(self):
        self.signature = None
        self.states = {}
        self.sampler = None

    def invalidate(self, signature):
        if signature != self.signature:
            self.signature = signature
            self.states = {}
            self.sampler = None

    def evaluate(self, objs, time, doc, amount, response, damping, signature):
        if amount <= 0.0 or time.Get() < doc.GetMinTime().Get():
            return sample_base_position(objs, time, doc), sample_base_position(objs, time, doc)
        self.invalidate((signature, doc.GetMinTime().Get(), doc.GetFps()))
        if self.sampler is None:
            self.sampler = _unit_sampler()
        start = doc.GetMinTime().Get()
        requested = max(start, time.Get())
        step = 1.0 / SPRING_HZ
        index = int(math.floor((requested - start) / step + 1e-9))
        state = self.states.get(0)
        if state is None:
            base = sample_base_position(objs, _spring_time(start), doc, self.sampler)
            state = (base, c4d.Vector(0))
            self.states[0] = state
        for current in range(max(self.states), index):
            state = self.states[current]
            t0 = start + current * step
            t1 = t0 + step
            q0 = sample_base_position(objs, _spring_time(t0), doc, self.sampler)
            q1 = sample_base_position(objs, _spring_time(t1), doc, self.sampler)
            mid = _spring_time((t0 + t1) * 0.5)
            omega, zeta = parameters(sample_ud(objs.rig, config.UD_SPRING_RESPONSE, mid, doc, 60.0), sample_ud(objs.rig, config.UD_SPRING_DAMPING, mid, doc, 65.0))
            p, v = step_vector(_vector_tuple(state[0]), _vector_tuple(state[1]), _vector_tuple(q0), _vector_tuple(q1), step, omega, zeta)
            state = (c4d.Vector(*p), c4d.Vector(*v))
            self.states[current + 1] = state
        t0 = start + index * step
        state = self.states[index]
        fraction = requested - t0
        q0 = sample_base_position(objs, _spring_time(t0), doc, self.sampler)
        q1 = sample_base_position(objs, _spring_time(t0 + step), doc, self.sampler)
        mid = _spring_time(t0 + step * 0.5)
        q1 = q0 + (q1 - q0) * (fraction / step)
        omega, zeta = parameters(sample_ud(objs.rig, config.UD_SPRING_RESPONSE, mid, doc, 60.0), sample_ud(objs.rig, config.UD_SPRING_DAMPING, mid, doc, 65.0))
        p, _ = step_vector(_vector_tuple(state[0]), _vector_tuple(state[1]), _vector_tuple(q0), _vector_tuple(q1), fraction, omega, zeta)
        target = sample_base_position(objs, time, doc, self.sampler)
        blended = target + (c4d.Vector(*p) - target) * (max(0.0, min(100.0, float(amount))) / 100.0)
        return target, blended
