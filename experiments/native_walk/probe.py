"""Owned, detached native-camera feasibility probe. Run on C4D main thread.

No imports from or changes to the legacy CamRig runtime.
"""
import c4d
import math
import time


def priority(tag, value):
    data = c4d.PriorityData()
    data.SetPriorityValue(c4d.PRIORITYVALUE_MODE, c4d.CYCLE_EXPRESSION)
    data.SetPriorityValue(c4d.PRIORITYVALUE_PRIORITY, value)
    tag[c4d.EXPRESSION_PRIORITY] = data


def build(height=170.0, intensity=1.0, count=1):
    document = c4d.documents.BaseDocument()
    document.SetFps(30)
    document.SetMaxTime(c4d.BaseTime(180, 30))
    rigs = []
    for i in range(count):
        root = c4d.BaseObject(c4d.Onull)
        root.SetName('Native Walk Prototype %s' % i)
        document.InsertObject(root)
        spline = c4d.SplineObject(2, c4d.SPLINETYPE_LINEAR)
        spline.SetName('Route')
        spline.SetAllPoints([c4d.Vector(0, 0, 0), c4d.Vector(0, 0, 1200)])
        spline.Message(c4d.MSG_UPDATE)
        spline.InsertUnder(root)
        source = c4d.BaseObject(c4d.Onull)
        source.SetName('Route and Aim')
        source.InsertUnder(root)
        align = c4d.BaseTag(c4d.Taligntospline)
        source.InsertTag(align)
        align[c4d.ALIGNTOSPLINETAG_LINK] = spline
        align[c4d.ALIGNTOSPLINETAG_TANGENTIAL] = False
        priority(align, -20)
        track = c4d.CTrack(align, c4d.DescID(c4d.DescLevel(c4d.ALIGNTOSPLINETAG_POSITION, c4d.DTYPE_REAL, 0)))
        align.InsertTrackSorted(track)
        curve = track.GetCurve()
        for frame, value in [(0, 0), (15, 0), (45, .12), (120, .85), (150, 1), (180, 1)]:
            key = curve.AddKey(c4d.BaseTime(frame, 30))['key']
            key.SetValue(curve, value)
            key.SetInterpolation(curve, c4d.CINTERPOLATION_LINEAR)
        target = c4d.BaseObject(c4d.Onull)
        target.SetName('Look Target')
        target.SetRelPos(c4d.Vector(200, 0, 2000))
        target.InsertUnder(root)
        aim = c4d.BaseTag(c4d.Ttargetexpression)
        source.InsertTag(aim)
        aim[c4d.TARGETEXPRESSIONTAG_LINK] = target
        priority(aim, -10)
        camera = c4d.BaseObject(1057516)
        if camera is None:
            raise RuntimeError('Redshift camera unavailable')
        camera.SetName('Camera OUTPUT')
        camera.InsertUnder(root)
        motion = c4d.BaseTag(c4d.Tmotioncam)
        camera.InsertTag(motion)
        motion[c4d.TMOTIONCAM_BASE_LINK] = source
        motion[c4d.TMOTIONCAM_BASE_INHERITPARAMS] = False
        motion[c4d.TMOTIONCAM_BASE_OVERRIDE_RIGHEIGHT] = False
        motion[c4d.TMOTIONCAM_RIG_HEIGHT] = height
        motion[c4d.TMOTIONCAM_RIG_PARALLAX] = c4d.Vector(0)
        for field in ('TARGET_ENABLED', 'SPLINE_ENABLED', 'FOLLOW_ENABLED', 'AUTOBANKING_ENABLED', 'FOOT_DYN_ENABLED', 'HEAD_DYN_ENABLED', 'CAM_DYN_ENABLED', 'FOCUS_DYN_ENABLED', 'FOCUS_ENABLED'):
            motion[getattr(c4d, 'TMOTIONCAM_' + field)] = False
        for field in ('HEAD_ROT_INTENSITY', 'CAM_ROT_INTENSITY', 'CAM_POS_INTENSITY'):
            motion[getattr(c4d, 'TMOTIONCAM_NMOTION_' + field)] = 0.0
        motion[c4d.TMOTIONCAM_NMOTION_FOOT_INTENSITY] = intensity
        motion[c4d.TMOTIONCAM_NMOTION_FOOT_FREQ] = 1.0
        priority(motion, 0)
        rigs.append((source, camera, motion))
    return document, rigs


def sample(document, rigs, frame):
    document.SetTime(c4d.BaseTime(int(round(frame * 1000)), 30000))
    document.ExecutePasses(None, True, True, True, c4d.BUILDFLAGS_NONE)
    source, camera, tag = rigs[0]
    matrix = camera.GetMg()
    p = matrix.off
    delta = p - source.GetMg().off
    return {'frame': frame, 'position': [p.x, p.y, p.z],
            'delta': [delta.x, delta.y, delta.z],
            'axis': [matrix.v3.x, matrix.v3.y, matrix.v3.z],
            'speed': tag[c4d.TMOTIONCAM_EXPORT_SPEED]}


def run():
    rows = []
    for height in (170.0, 15.0):
        for intensity in (0.0, 1.0):
            document, rigs = build(height, intensity)
            begin = time.perf_counter()
            seq = {f: sample(document, rigs, f) for f in range(181)}
            elapsed = time.perf_counter() - begin
            random_rows = [sample(document, rigs, f) for f in (90, 30, 150, 60, 90)]
            error = max(math.dist(row['position'], seq[row['frame']]['position']) for row in random_rows)
            rows.append({'height': height, 'intensity': intensity, 'sequential_ms': elapsed * 1000,
                         'random_position_error_cm': error,
                         'samples': [seq[f] for f in (0, 15, 30, 60, 90, 120, 150, 180)],
                         'max_offset_cm': max(math.sqrt(sum(v*v for v in row['delta'])) for row in seq.values())})
    return rows


if __name__ == '__main__':
    result = run()
