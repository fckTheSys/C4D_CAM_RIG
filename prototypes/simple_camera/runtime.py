"""Portable adapter; builder prepends pure math sources to this file."""
import c4d
import math

ROLE_ID = 10699101
_cache = {}


def scalar_controls(root):
    return [(desc, bc) for desc, bc in root.GetUserDataContainer()
            if desc[desc.GetDepth()-1].dtype in (c4d.DTYPE_REAL, c4d.DTYPE_LONG, c4d.DTYPE_BOOL)]


def nodes(root):
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
    if set(found) not in (set(range(1, 11)), set(range(1, 11)) - {2}):
        raise ValueError('Incomplete rig hierarchy')
    for role, parent in ((2,1),(3,1),(4,1),(5,4),(10,5),(6,5),(7,6),(8,7),(9,8)):
        if role in found and found[role].GetUp() != found[parent]:
            raise ValueError('Rig hierarchy changed')
    return found


def seconds(value):
    return c4d.BaseTime(int(round(value * 1000000)), 1000000)


def controls(root, document):
    ids = {bc[c4d.DESC_NAME]: desc for desc, bc in scalar_controls(root)
           if bc[c4d.DESC_NAME]}
    tracks = {name: root.FindCTrack(desc) for name, desc in ids.items()}
    values = {name: root[desc] for name, desc in ids.items()}
    # C4D keeps an unkeyed Attribute Manager edit in the live parameter while
    # its CCurve still contains the old animation. Preview that live value.
    # Compare at the exact host time, not our rounded historical sample time.
    previews = {}
    for name, desc in ids.items():
        track = tracks[name]
        if track is not None:
            keyed = track.GetCurve().GetValue(document.GetTime(), document.GetFps())
            live = root[desc]
            if not math.isclose(live, keyed, rel_tol=1e-9, abs_tol=1e-9):
                previews[name] = live
    def read(name, t):
        desc = ids[name]
        track = tracks[name]
        if name in previews:
            # Temporary constant preview also updates integrated step/frequency
            # inputs. Recording a key or reevaluating animation removes it.
            value = previews[name]
        elif track is not None:
            value = track.GetCurve().GetValue(seconds(t), document.GetFps())
        else:
            value = values[name]
        if not math.isfinite(value):
            raise ValueError(name+' must be finite')
        return value
    read.preview_signature = tuple(sorted(previews.items()))
    read.tracks = tracks
    read.constant = lambda name: previews.get(name, values[name]) if name in previews or tracks[name] is None else None
    signatures = {}
    def input_signature(name):
        if name not in signatures:
            value = read.constant(name)
            track = tracks[name]
            if value is not None:
                signatures[name] = ('constant', value)
            else:
                curve = track.GetCurve()
                signatures[name] = (track.GetBefore(), track.GetAfter(), tuple(
                    (curve.GetKey(i).GetTime().Get(), curve.GetKey(i).GetValue(),
                     curve.GetKey(i).GetInterpolation(), curve.GetKey(i).GetTimeLeft().Get(),
                     curve.GetKey(i).GetTimeRight().Get(), curve.GetKey(i).GetValueLeft(),
                     curve.GetKey(i).GetValueRight()) for i in range(curve.GetKeyCount())))
        return signatures[name]
    read.signature = input_signature
    return ids, read


def selected_path(root, objects):
    desc = next(desc for desc, bc in root.GetUserDataContainer() if bc[c4d.DESC_NAME] == 'Path')
    return root[desc]


def prepare_data(path, matrix):
    global _cache
    sig = (path_geometry_stamp(path), path_matrix_stamp(matrix))
    if _cache.get('geometry') != sig:
        def point(u):
            p = matrix * path.GetSplinePoint(u)
            return (p.x, p.y, p.z)
        if path[c4d.SPLINEOBJECT_TYPE] == c4d.SPLINETYPE_LINEAR:
            points = [path_vector_stamp(matrix*p) for p in path.GetAllPoints()]
            if path.IsClosed(): points.append(points[0])
            table = ArcTable.from_polyline(points)
        else:
            table = ArcTable(point)
        if not table.converged:
            raise ValueError('Arc approximation failed: '+str(table.diagnostics))
        if table.length <= 1e-8:
            raise ValueError('Path has zero length')
        # ArcTable needs its callback only during construction. Do not retain a
        # generator cache object: C4D replaces it after controller edits.
        table._point = None
        _cache = {'geometry': sig, 'table': table, 'integrals': {}}
    return _cache


def input_breaks(read, names, progress_extrema=False):
    breaks=set()
    for name in names:
        track=read.tracks[name]
        if track is None or read.constant(name) is not None:
            continue
        curve=track.GetCurve()
        breaks.update(curve.GetKey(i).GetTime().Get() for i in range(curve.GetKeyCount()))
        if progress_extrema and name=='Progress':
            for i in range(curve.GetKeyCount()-1):
                k0,k1=curve.GetKey(i),curve.GetKey(i+1)
                if k0.GetInterpolation()==c4d.CINTERPOLATION_SPLINE:
                    breaks.update(cubic_extrema_times(k0.GetTime().Get(),k1.GetTime().Get(),
                        k0.GetValue(),k1.GetValue(),k0.GetTimeRight().Get(),k0.GetValueRight(),
                        k1.GetTimeLeft().Get(),k1.GetValueLeft()))
    return sorted(breaks)


def cached_integral(data, key, signature, start, requested, interval):
    grid=1.0/120.0
    index=int(math.floor((requested-start)/grid+1e-9))
    if index>120000: raise ValueError('Prototype integration limit exceeded')
    cache=data['integrals']
    entry=cache.get(key)
    if entry is None or entry['signature']!=signature:
        entry={'signature':signature,'prefix':[0.0]}
        cache[key]=entry
    prefix=entry['prefix']
    while len(prefix)<=index:
        a=start+(len(prefix)-1)*grid
        prefix.append(prefix[-1]+interval(a,a+grid))
    a=start+index*grid
    return prefix[index]+interval(a,requested)


def motion_phases(data, read, document, t):
    start=document.GetMinTime().Get()
    requested=max(start,t)
    if requested-start>1000: raise ValueError('Prototype integration limit exceeded')
    origin=(start,document.GetFps())
    table=data['table']
    progress=lambda at:max(0.0,min(1.0,read('Progress',at)))
    path_sig=(origin,read.signature('Progress'))
    constant_length=read.constant('Step Length')
    # Constant/temporarily edited step length divides a reusable travel integral.
    # It does not require rebuilding history for each slider tick.
    if constant_length is not None:
        if constant_length<=0: raise ValueError('Step Length must be positive')
        if read.constant('Progress') is not None:
            travel=0.0
        else:
            breaks=input_breaks(read,('Progress',),True)
            def distance_interval(a,b):
                cuts=[a]+[v for v in breaks if a<v<b]+[b]
                return sum(abs(table.horizontal_distance(progress(right))-table.horizontal_distance(progress(left)))
                           for left,right in zip(cuts,cuts[1:]))
            travel=cached_integral(data,'travel',path_sig,start,requested,distance_interval)
        walk_phase=math.pi*travel/constant_length
    else:
        breaks=input_breaks(read,('Progress','Step Length'),True)
        def walk_interval(a,b):
            cuts=[a]+[v for v in breaks if a<v<b]+[b]
            total=0.0
            for left,right in zip(cuts,cuts[1:]):
                lengths=[read('Step Length',v) for v in (left,(left+right)/2,right)]
                if min(lengths)<=0: raise ValueError('Step Length must be positive')
                distance=abs(table.horizontal_distance(progress(right))-table.horizontal_distance(progress(left)))
                total+=math.pi*distance*(1/lengths[0]+4/lengths[1]+1/lengths[2])/6
            return total
        walk_phase=cached_integral(data,'walk',(path_sig,read.signature('Step Length')),
                                   start,requested,walk_interval)
    phases=[walk_phase]
    for name in ('Shake Frequency','Drift Frequency'):
        constant=read.constant(name)
        if constant is not None:
            phases.append((requested-start)*constant)
            continue
        breaks=input_breaks(read,(name,))
        def frequency_interval(a,b):
            cuts=[a]+[v for v in breaks if a<v<b]+[b]
            return sum((right-left)*(read(name,left)+4*read(name,(left+right)/2)+read(name,right))/6
                       for left,right in zip(cuts,cuts[1:]))
        phases.append(cached_integral(data,name,(origin,read.signature(name)),start,requested,frequency_interval))
    return phases


def validate(root, objects):
    if root.GetUp() is not None or (root.GetRelScale()-c4d.Vector(1)).GetLength()>1e-10:
        raise ValueError('Prototype requires top-level root with scale 1')
    for tr in root.GetCTracks():
        if tr.GetBefore()!=c4d.CLOOP_CONSTANT or tr.GetAfter()!=c4d.CLOOP_CONSTANT:
            raise ValueError('Prototype requires constant track extrapolation')
        if tr.GetDescriptionID()[0].id != c4d.ID_USERDATA:
            raise ValueError('Animated root transform unsupported')
    for node in objects.values():
        if (node.GetFrozenPos().GetLength()>1e-10 or node.GetFrozenRot().GetLength()>1e-10 or
                (node.GetFrozenScale()-c4d.Vector(1)).GetLength()>1e-10):
            raise ValueError('Frozen transforms unsupported')
    for role in (4,5,6,7,8,9):
        node=objects[role]
        if any(tr.GetDescriptionID()[0].id in (c4d.ID_BASEOBJECT_REL_POSITION,
                c4d.ID_BASEOBJECT_REL_ROTATION,c4d.ID_BASEOBJECT_REL_SCALE)
                for tr in node.GetCTracks()):
            raise ValueError('Use root controls; direct transform keys on driven nodes unsupported')
        if (node.GetRelScale()-c4d.Vector(1)).GetLength()>1e-10:
            raise ValueError('Driven node scale must be 1')
        allowed = c4d.Taligntospline if role==4 else c4d.Ttargetexpression if role==6 else None
        expressions=[tag for tag in node.GetTags() if tag.GetInfo() & c4d.TAG_EXPRESSION]
        if any(tag.GetType()!=allowed for tag in expressions) or len(expressions) != (1 if allowed else 0):
            raise ValueError('Unexpected expression on driven node')
    if objects[9].GetRelPos().GetLength()>1e-10 or objects[9].GetRelRot().GetLength()>1e-10:
        raise ValueError('Camera transform must be identity; use root controls')
    ids={bc[c4d.DESC_NAME]:desc for desc,bc in scalar_controls(root)}
    mode_track=root.FindCTrack(ids['Aim Mode'])
    if mode_track is not None: raise ValueError('Animated aim mode unsupported')
    progress_track=root.FindCTrack(ids['Progress'])
    if progress_track is not None:
        curve=progress_track.GetCurve()
        if any(curve.GetKey(i).GetInterpolation()==c4d.CINTERPOLATION_STEP for i in range(curve.GetKeyCount())):
            raise ValueError('Progress teleport/Step keys unsupported')
    for tag in root.GetTags():
        if tag.GetInfo() & c4d.TAG_EXPRESSION:
            if tag.GetType()!=c4d.Tpython or tag.GetDataInstance().GetInt32(ROLE_ID) not in (1,2):
                raise ValueError('External root expression driver unsupported')
    stages=[tag.GetDataInstance().GetInt32(ROLE_ID) for tag in root.GetTags()
            if tag.GetInfo() & c4d.TAG_EXPRESSION]
    if sorted(stages)!=[1,2]:
        raise ValueError('Expected exactly Prepare and Finish stages')


def execute(tag):
    root = tag.GetObject()
    document = root.GetDocument()
    obj = nodes(root)
    ids, read = controls(root, document)
    validate(root, obj)
    t = document.GetTime().Get()
    source = selected_path(root, obj)
    spline, world = evaluated_path(source, root, tuple(obj[i] for i in range(4,10)), require_static=True)
    # Walk uses root-horizontal distance and direction; external path transforms
    # therefore participate in both the distance cache and tangent calculation.
    path_matrix = ~root.GetMg() * world
    data = prepare_data(spline, path_matrix)
    table = data['table']
    progress = lambda at: max(0.0, min(1.0, read('Progress', at)))
    align = obj[4].GetTag(c4d.Taligntospline)
    target_tag = obj[6].GetTag(c4d.Ttargetexpression)
    aim_mode=root[ids['Aim Mode']]
    world_desc=next(desc for desc,bc in root.GetUserDataContainer() if bc[c4d.DESC_NAME]=='Target')
    look=look_source(root,aim_mode,root[world_desc],obj[10],obj[6])
    if tag.GetDataInstance().GetInt32(ROLE_ID)==1:
        natural = table.parameter(progress(t))
        # Live native Bezier fixture: Align consumes GetSplinePoint's natural u.
        align[c4d.ALIGNTOSPLINETAG_POSITION]=natural
        align[c4d.ALIGNTOSPLINETAG_LINK]=source
        align[c4d.ALIGNTOSPLINETAG_TANGENTIAL]=False
        obj[5].SetRelPos(c4d.Vector(read('Body X',t),read('Height',t)+read('Body Y',t),read('Body Z',t)))
        # Keep native Target scheduled; a null link bypasses aiming in manual mode.
        # Toggling EXPRESSION_ENABLE here delays re-enabling until a later pass.
        target_tag[c4d.TARGETEXPRESSIONTAG_LINK]=look
        obj[6].SetRelRot(c4d.Vector(0))
        return
    # Native expression enable changes may be observed only on the next pass.
    # Finish owns the manual identity after the native Target's priority.
    if aim_mode==0: obj[6].SetMl(c4d.Matrix())
    obj[7].SetMl(c4d.utils.MatrixRotY(math.radians(read('Pan',t))) *
                    c4d.utils.MatrixRotX(math.radians(read('Tilt',t))) *
                    c4d.utils.MatrixRotZ(math.radians(read('Roll',t))))
    if all(read(name,t)==0 for name in ('Walk Strength','Shake Strength','Drift Strength')):
        obj[8].SetMl(c4d.Matrix())
        return
    def speed(at):
        h=0.0001
        return abs(table.horizontal_distance(progress(at+h))-table.horizontal_distance(progress(at-h)))/(2*h)
    phase=motion_phases(data,read,document,t)
    lateral,vertical,lean=walk(phase[0],speed(t),read('Walk Strength',t),read('Walk Amplitude',t),read('Walk Lean',t),read('Softness',t),read('Full Walk Speed',t))
    u=table.parameter(progress(t))
    tangent=path_matrix.MulV(spline.GetSplineTangent(u))
    side=c4d.Vector(tangent.z,0,-tangent.x)
    if side.GetLength()<1e-8: side=c4d.Vector(1,0,0)
    side.Normalize()
    world_walk=root.GetMg().MulV(side*lateral+c4d.Vector(0,vertical,0))
    local_walk=(~obj[7].GetMg()).MulV(world_walk)
    offset=local_walk
    rotation=c4d.utils.MatrixRotZ(lean)
    seed=int(read('Seed',t))
    for layer,p in (('Shake',phase[1]),('Drift',phase[2])):
        strength=read(layer+' Strength',t)
        delta=c4d.Vector(*(noise(p,seed+j*37+(0 if layer=='Shake' else 500)) for j in range(3)))
        offset+=delta*strength*read(layer+' Position',t)
        angles=delta*(strength*math.radians(read(layer+' Rotation',t)))
        rotation=rotation*c4d.utils.HPBToMatrix(angles)
    rotation.off=offset
    obj[8].SetMl(rotation)


def main():
    message='Ready'
    try:
        execute(op)
        op.GetDataInstance().SetString(ROLE_ID+1,'')
    except Exception as error:
        # Explicit diagnostic; never silently claim a stale frame is valid.
        print('Simple Camera ERROR: '+str(error))
        op.GetDataInstance().SetString(ROLE_ID+1,str(error))
        message='ERROR: '+str(error)
        try:
            nodes(op.GetObject())[6].GetTag(c4d.Ttargetexpression)[c4d.TARGETEXPRESSIONTAG_LINK] = None
        except Exception:
            pass
        try:
            nodes(op.GetObject())[4].GetTag(c4d.Taligntospline)[c4d.ALIGNTOSPLINETAG_LINK] = None
        except Exception:
            pass
    for desc,bc in op.GetObject().GetUserDataContainer():
        if bc[c4d.DESC_NAME]=='Status':
            if op.GetObject()[desc]!=message:
                op.GetObject()[desc]=message
            break
