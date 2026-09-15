"""Embedded path helpers shared by Cine and CK; no plugin import at playback."""
import c4d

TRACER_TYPE = 1018655


def path_vector_stamp(v):
    return v.x, v.y, v.z


def path_matrix_stamp(m):
    return tuple(path_vector_stamp(v) for v in (m.off, m.v1, m.v2, m.v3))


def path_geometry_stamp(spline):
    # Only Bezier stores editable tangent handles. Linear/B-Spline raise on GetTangent.
    tangents = ()
    if spline[c4d.SPLINEOBJECT_TYPE] == c4d.SPLINETYPE_BEZIER:
        tangents = tuple((path_vector_stamp(spline.GetTangent(i)['vl']),
                          path_vector_stamp(spline.GetTangent(i)['vr']))
                         for i in range(spline.GetPointCount()))
    return (spline[c4d.SPLINEOBJECT_TYPE], spline.IsClosed(),
            tuple(path_vector_stamp(v) for v in spline.GetAllPoints()), tangents)


def path_static_node(node, root, driven):
    while node is not None:
        if any(node == item for item in driven):
            raise ValueError('Path cannot depend on the driven camera hierarchy')
        if node.GetCTracks():
            # Rig UD keys are camera controls, not animated source geometry.
            if node != root or any(t.GetDescriptionID()[0].id != c4d.ID_USERDATA for t in node.GetCTracks()):
                raise ValueError('Path must be static; animate camera Progress instead')
        if any(t.GetInfo() & c4d.TAG_EXPRESSION and not
               (node.GetType() == TRACER_TYPE and t.GetType() == 1019326)
               for t in node.GetTags()) and node != root:
            raise ValueError('Static path controllers cannot have expression drivers')
        node = node.GetUp()


def evaluated_path(source, root, driven=(), require_static=False, animated=False):
    if not isinstance(source, c4d.BaseObject) or source.GetDocument() != root.GetDocument():
        raise ValueError('Assign Path to a spline or Tracer in this document')
    node = source
    while node is not None:
        if any(node == item for item in driven):
            raise ValueError('Path cannot depend on the driven camera hierarchy')
        node = node.GetUp()
    if source.GetDeformCache() is not None:
        raise ValueError('Deformed paths are unsupported')
    if source.GetType() == TRACER_TYPE:
        if source[c4d.MGTRACEROBJECT_MODE] != c4d.MGTRACEROBJECT_MODE_LINK:
            raise ValueError('Tracer Path requires Connect Objects mode (static route)')
        path_static_node(source, root, driven)
        links = source[c4d.MGTRACEROBJECT_OBJECTLIST]
        if links is None or links.GetObjectCount() < 2:
            raise ValueError('Tracer needs at least two linked route controllers')
        for i in range(links.GetObjectCount()):
            controller = links.ObjectFromIndex(root.GetDocument(), i)
            if controller is None:
                raise ValueError('Tracer contains a missing controller')
            stack = [controller]
            while stack:
                item = stack.pop()
                if not animated:
                    path_static_node(item, root, driven)
                # Child modes can consume descendants as well as direct links.
                if source[c4d.MGTRACEROBJECT_MGMODE] != c4d.MGTRACEROBJECT_MGMODE_SINGLE:
                    stack.extend(item.GetChildren())
        found = []
        stack = [source.GetCache()]
        while stack:
            item = stack.pop()
            if item is None:
                continue
            if isinstance(item, c4d.SplineObject):
                found.append(item)
            else:
                stack.extend(item.GetChildren())
        if len(found) != 1:
            raise ValueError('Tracer must generate exactly one spline; check its links and mode')
        spline = found[0]
    elif isinstance(source, c4d.SplineObject):
        if require_static:
            path_static_node(source, root, driven)
        if source.GetChildren():
            raise ValueError('Path spline must not have deformers or child generators')
        spline = source
    else:
        raise ValueError('Path requires an editable spline or Tracer Connect Objects')
    if spline.GetSegmentCount() > 1 or spline.GetPointCount() < 2:
        raise ValueError('Path requires one segment with at least two points')
    points = spline.GetAllPoints()
    if all((v-points[0]).GetLength() < 1e-8 for v in points[1:]):
        raise ValueError('Path has zero length')
    # Cache GetMg includes its generator and all cache hierarchy transforms.
    return spline, spline.GetMg()
