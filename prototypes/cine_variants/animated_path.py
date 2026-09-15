"""Experimental historical Tracer reconstruction from direct Null position keys.

Only detached spline data is sampled. Never evaluates or changes document time.
"""
import c4d


def animated_tracer_sampler(root, source, spline, world, driven, signature):
    if source.GetType()!=TRACER_TYPE:
        raise ValueError('Experimental Animated Path requires Tracer Connect Objects')
    kind=spline[c4d.SPLINEOBJECT_TYPE]
    if kind not in (c4d.SPLINETYPE_LINEAR,c4d.SPLINETYPE_CUBIC,c4d.SPLINETYPE_AKIMA,c4d.SPLINETYPE_BSPLINE):
        raise ValueError('Experimental Animated Path: use Linear, Cubic, Akima or B-Spline (not Bezier)')
    links=source[c4d.MGTRACEROBJECT_OBJECTLIST]
    count=links.GetObjectCount()
    if not 2<=count<=64 or spline.GetPointCount()!=count:
        raise ValueError('Experimental Animated Path needs 2-64 direct Nulls, one point per Null')
    if source[c4d.MGTRACEROBJECT_MGMODE] not in (None,c4d.MGTRACEROBJECT_MGMODE_SINGLE):
        raise ValueError('Experimental Animated Path requires direct objects, not child expansion')
    readers=[]
    signature.append(('animated_tracer',str(source.GetGUID()),kind,spline.IsClosed(),path_matrix_stamp(world)))
    for i in range(count):
        node=links.ObjectFromIndex(root.GetDocument(),i)
        if node is None or node.GetType()!=c4d.Onull or node.GetChildren():
            raise ValueError('Experimental Animated Path controllers must be leaf Nulls')
        ancestor=node
        while ancestor is not None:
            if any(ancestor==item for item in driven):
                raise ValueError('Animated path cannot depend on the camera hierarchy')
            for track in ancestor.GetCTracks():
                base=track.GetDescriptionID()[0].id
                if base!=c4d.ID_BASEOBJECT_REL_POSITION and not (ancestor==root and base==c4d.ID_USERDATA):
                    raise ValueError('Experimental path controllers support Position keys only')
            ancestor=ancestor.GetUp()
        readers.append(transform_reader(node,root,signature,precision=1000000000))
    reverse=bool(source[c4d.MGTRACEROBJECT_REVERSESPLINE])
    signature.append(('reverse',reverse))
    if reverse:readers.reverse()
    temporary=c4d.SplineObject(count,kind)
    temporary[c4d.SPLINEOBJECT_CLOSED]=spline.IsClosed()
    inverse=~world
    last=[None]
    def sample(time,phase):
        if last[0]!=time:
            temporary.SetAllPoints([inverse*reader(time).off for reader in readers])
            temporary.Message(c4d.MSG_UPDATE)
            last[0]=time
        return world*temporary.GetSplinePoint(phase)
    # Validate the reconstruction against the native evaluated generator now.
    now=root.GetDocument().GetTime().Get()
    for phase in (0.,.37,1.):
        if (sample(now,phase)-world*spline.GetSplinePoint(phase)).GetLength()>.001:
            raise ValueError('Experimental Tracer reconstruction differs from native output; check Tracer settings')
    return sample
