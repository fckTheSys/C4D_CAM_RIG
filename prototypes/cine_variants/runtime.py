"""Cine fixed-purpose portable expression. Mode is baked at construction.

No external package imports, scene edits or forced evaluation from expressions.
Generators: Prepare 100, native Align 110, inertia 115, native Target 120.
"""
import math
import c4d

ROLE_ID = 10699220  # Private object metadata, not a registered plugin command.
PARENTS = {3: 1, 5: 1, 9: 5, 12: 9, 6: 12, 7: 6, 13: 7, 8: 13}
PARENTS.update(({2: 1, 4: 1}, {10: 1}, {11: 1})[FIXED_MODE])


def resolve(root):
    found = {}
    stack = [root]
    while stack:
        node = stack.pop()
        role = node.GetDataInstance().GetInt32(ROLE_ID)
        if role:
            if role in found:
                raise ValueError('Duplicate rig role')
            found[role] = node
        stack.extend(node.GetChildren())
    expected = set(PARENTS) | {1}
    if set(found) != expected and not (FIXED_MODE == 1 and set(found) == expected - {10}):
        raise ValueError('Incomplete rig hierarchy')
    for role, parent in PARENTS.items():
        if role in found and found[role].GetUp() != found[parent]:
            raise ValueError('Rig hierarchy changed')
    return found


def read(root, name):
    if name == 'movement_mode':
        return FIXED_MODE
    return root[c4d.ID_USERDATA, UD[name]]


def number(root, name):
    value = float(read(root, name))
    if not math.isfinite(value):
        raise ValueError(name + ' must be finite')
    return value


def source_link(root, node, fallback, driven):
    if node is None:
        return fallback
    if not isinstance(node, c4d.BaseObject) or node.GetDocument() != root.GetDocument():
        raise ValueError('Controller link must reference an object in this document')
    parent = node
    while parent is not None:
        if any(parent == item for item in driven):
            raise ValueError('Controller cannot depend on the driven camera hierarchy')
        parent = parent.GetUp()
    return node


def execute(tag):
    root = tag.GetObject()
    objects = resolve(root)  # Re-resolve every pass, including after Undo/clone.
    for node in objects.values():
        if (node.GetRelScale() - c4d.Vector(1)).GetLength() > 1e-8:
            raise ValueError('Prototype requires rig scale 1')
        if (node.GetFrozenPos().GetLength() > 1e-8 or
                node.GetFrozenRot().GetLength() > 1e-8 or
                (node.GetFrozenScale() - c4d.Vector(1)).GetLength() > 1e-8):
            raise ValueError('Prototype does not support frozen transforms')
    if root.GetUp() is not None:
        raise ValueError('Prototype requires a top-level rig; move or rotate its root')
    circle = objects.get(4)
    motion, aim, frame, camera = (objects[i] for i in range(5, 9))
    align = motion.GetTag(c4d.Taligntospline)
    target = aim.GetTag(c4d.Ttargetexpression)
    if align is None or target is None:
        raise ValueError('Required Align or Target tag is missing')
    driven = (circle, motion, objects[9], objects[12], aim, frame, objects[13], camera)
    look = source_link(root, read(root, 'target'), objects[3], driven)
    rotation = c4d.Vector(*(math.radians(number(root, name)) for name in ('pan', 'tilt', 'roll')))
    offset = c4d.Vector(*(number(root, 'offset_' + axis) for axis in ('x', 'y', 'z')))
    mode = read(root, 'movement_mode')
    if mode not in (0, 1, 2):
        raise ValueError('Unknown movement mode')
    for key in ('aim_mode',):
        desc = c4d.DescID(c4d.DescLevel(c4d.ID_USERDATA, c4d.DTYPE_SUBCONTAINER, 0),
                          c4d.DescLevel(UD[key], c4d.DTYPE_LONG, 0))
        if root.FindCTrack(desc):
            raise ValueError('Choose modes per shot; animated mode changes are unsupported')
    if mode == 0:
        center = source_link(root, read(root, 'center'), objects[2], driven)
        angle, radius, height = (number(root, name) for name in ('angle', 'radius', 'height'))
        if radius <= 0:
            raise ValueError('Radius must be greater than zero')
        circle.SetRelPos(~root.GetMg() * center.GetMg().off + c4d.Vector(0, height, 0))
        circle[c4d.PRIM_CIRCLE_RADIUS] = radius
        path, progress = circle, (angle % 360.0) / 360.0
    elif mode == 1:
        path = source_link(root, read(root, 'path'), None, driven)
        evaluated_path(path, root, driven)
        progress = max(0., min(1., number(root, 'progress')))
    else:
        free = source_link(root, read(root, 'free'), objects[11], driven)
        matrix = free.GetMg()
        if any(abs(axis.GetLength() - 1.) > 1e-8 for axis in (matrix.v1, matrix.v2, matrix.v3)):
            raise ValueError('Free controller world scale must be 1')
    # Read evaluated/live UD directly: do not replace an unkeyed UI edit with
    # CCurve.GetValue(). C4D owns key interpolation and subframe evaluation.
    align[c4d.EXPRESSION_ENABLE] = mode != 2
    if mode == 2:
        # Clear the link as well: native Align can still be scheduled in this
        # evaluation pass when its enable flag changes in an earlier tag.
        align[c4d.ALIGNTOSPLINETAG_LINK] = None
        motion.SetMg(matrix)
    else:
        motion.SetRelRot(c4d.Vector())
        align[c4d.ALIGNTOSPLINETAG_LINK] = path
        align[c4d.ALIGNTOSPLINETAG_POSITION] = progress
    align[c4d.ALIGNTOSPLINETAG_TANGENTIAL] = False
    objects[9].SetRelPos(offset)
    target[c4d.TARGETEXPRESSIONTAG_LINK] = look if read(root, 'aim_mode') == 1 else None
    # Clear previous target orientation so Manual is independent of seek history.
    aim.SetRelRot(c4d.Vector())
    frame.SetRelRot(rotation)
    apply_effects(root, objects[13])


def apply_effects(root, node):
    position, rotation = c4d.Vector(), c4d.Vector()
    time = root.GetDocument().GetTime().Get()
    for prefix, salt in (('shake', 0), ('drift', 100)):
        strength = number(root, prefix + '_strength')
        if strength <= 0:
            continue
        frequency = number(root, prefix + '_frequency')
        require_constant(root, prefix + '_frequency')
        require_constant(root, 'seed')
        seed = int(read(root, 'seed')) + salt
        amplitude = number(root, prefix + '_position') * strength
        degrees = number(root, prefix + '_rotation') * strength
        if amplitude:
            position += c4d.Vector(*(noise(time * frequency, seed + axis) * amplitude for axis in range(3)))
        if degrees:
            rotation += c4d.Vector(*(math.radians(noise(time * frequency, seed + axis + 3) * degrees) for axis in range(3)))
    node.SetRelPos(position)
    node.SetRelRot(rotation)


def main():
    root = op.GetObject()
    try:
        if op.GetDataInstance().GetInt32(ROLE_ID) == 2:
            if str(read(root, 'status')).startswith('Stopped:'):
                return
            execute_inertia(root, resolve(root))
        else:
            execute(op)
        message = ('Orbit', 'Trajectory', 'Free')[read(root, 'movement_mode')] + ' prototype: ready'
    except Exception as error:
        message = 'Stopped: ' + str(error)
        if op.GetDataInstance().GetInt32(ROLE_ID) != 2:
            # Do not continue animating the previously linked path after an invalid edit.
            try:
                motion = resolve(root)[5]
                motion.GetTag(c4d.Taligntospline)[c4d.ALIGNTOSPLINETAG_LINK] = None
            except Exception:
                pass
    slot = (c4d.ID_USERDATA, UD['status'])
    if root[slot] != message:
        root[slot] = message
