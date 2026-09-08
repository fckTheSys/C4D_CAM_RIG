"""Break User Data: перенос анимации с rig на объекты, удаление Python Tag."""
import c4d
from .scene_support import add_undo

from . import config
from . import log
from .rig_objects import get_rig_objects
from .ud_utils import get_ud_desc_name


def _copy_float_track(
    doc: c4d.documents.BaseDocument,
    source: c4d.BaseList2D,
    source_desc_id: c4d.DescID,
    dest: c4d.BaseList2D,
    dest_desc_id: c4d.DescID,
    transform_fn,
) -> None:
    """Copy animated values from source track to dest track, with optional value transform."""
    track_src = source.FindCTrack(source_desc_id)
    if track_src is None:
        return
    curve_src = track_src.GetCurve()
    if curve_src is None:
        return
    track_dest = dest.FindCTrack(dest_desc_id)
    if track_dest is None:
        try:
            track_dest = c4d.CTrack(dest, dest_desc_id)
            dest.InsertTrackSorted(track_dest)
        except Exception:
            return
    curve_dest = track_dest.GetCurve()
    if curve_dest is None:
        return
    try:
        n = curve_src.GetKeyCount()
    except Exception:
        return
    for i in range(n):
        try:
            key_src = curve_src.GetKey(i)
            t = key_src.GetTime()
            val = key_src.GetValue(curve_src)
            new_val = transform_fn(val)
            key_dict = curve_dest.AddKey(t)
            if key_dict is None:
                continue
            key_dest = key_dict.get("key")
            nidx = key_dict.get("nidx", 0)
            if key_dest is not None:
                key_dest.SetValue(curve_dest, new_val)
                try:
                    curve_dest.SetKeyDefault(doc, nidx)
                except Exception:
                    pass
        except Exception:
            continue


def _copy_vector_track_from_three_ud(
    doc: c4d.documents.BaseDocument,
    rig: c4d.BaseObject,
    desc_id_x: c4d.DescID,
    desc_id_y: c4d.DescID,
    desc_id_z: c4d.DescID,
    dest: c4d.BaseList2D,
    dest_param_id: int,
    vector_from_xyz,
) -> None:
    """Sample three float UD tracks at key times and write one vector track on dest."""
    tr_x = rig.FindCTrack(desc_id_x)
    tr_y = rig.FindCTrack(desc_id_y)
    tr_z = rig.FindCTrack(desc_id_z)
    if tr_x is None and tr_y is None and tr_z is None:
        return
    curve_x = tr_x.GetCurve() if tr_x else None
    curve_y = tr_y.GetCurve() if tr_y else None
    curve_z = tr_z.GetCurve() if tr_z else None
    times = set()
    for curve in (curve_x, curve_y, curve_z):
        if curve is not None:
            try:
                for i in range(curve.GetKeyCount()):
                    times.add(curve.GetKey(i).GetTime())
            except Exception:
                pass
    if not times:
        return
    try:
        fps = doc.GetFps()
        desc_id = c4d.DescID(dest_param_id)
        track_dest = dest.FindCTrack(desc_id)
        if track_dest is None:
            track_dest = c4d.CTrack(dest, desc_id)
            dest.InsertTrackSorted(track_dest)
        curve_dest = track_dest.GetCurve()
        if curve_dest is None:
            return
        for t in sorted(times, key=lambda bt: bt.Get()):
            try:
                vx = curve_x.GetValue(t, fps) if curve_x else 0.0
            except Exception:
                vx = 0.0
            try:
                vy = curve_y.GetValue(t, fps) if curve_y else 0.0
            except Exception:
                vy = 0.0
            try:
                vz = curve_z.GetValue(t, fps) if curve_z else 0.0
            except Exception:
                vz = 0.0
            vec = vector_from_xyz(vx, vy, vz)
            key_dict = curve_dest.AddKey(t)
            if key_dict is None:
                continue
            key_dest = key_dict.get("key")
            nidx = key_dict.get("nidx", 0)
            if key_dest is not None:
                key_dest.SetValue(curve_dest, vec)
                try:
                    curve_dest.SetKeyDefault(doc, nidx)
                except Exception:
                    pass
    except Exception:
        pass


def _transfer_rig_ud_keys_to_targets(
    doc: c4d.documents.BaseDocument,
    rig: c4d.BaseObject,
    circle: c4d.BaseObject,
    objs,
) -> None:
    """Transfer animated UD from rig to the objects that use them (orbit->align, radius->circle, etc.)."""
    from c4d import utils

    id_rel_pos = getattr(c4d, "ID_BASEOBJECT_REL_POSITION", None)
    id_rel_rot = getattr(c4d, "ID_BASEOBJECT_REL_ROTATION", None)
    focal_id = getattr(c4d, "RSCAMERAOBJECT_FOCAL_LENGTH", None) or getattr(c4d, "CAMERA_FOCUS", None)
    if not objs or not objs.align or not objs.cam or not objs.fx:
        return
    ud_by_name = {}
    for desc_id, bc in rig.GetUserDataContainer():
        name = get_ud_desc_name(bc)
        if name:
            ud_by_name[name] = desc_id
    if config.UD_ORBIT in ud_by_name and objs.align:
        _copy_float_track(
            doc, rig, ud_by_name[config.UD_ORBIT],
            objs.align, c4d.DescID(c4d.ALIGNTOSPLINETAG_POSITION),
            lambda v: float(v) / 360.0,
        )
    if config.UD_RADIUS in ud_by_name:
        _copy_float_track(
            doc, rig, ud_by_name[config.UD_RADIUS],
            circle, c4d.DescID(c4d.PRIM_CIRCLE_RADIUS),
            float,
        )
    if id_rel_pos and config.UD_OFFSET_X in ud_by_name and config.UD_OFFSET_Y in ud_by_name and config.UD_OFFSET_Z in ud_by_name:
        _copy_vector_track_from_three_ud(
            doc, rig,
            ud_by_name[config.UD_OFFSET_X], ud_by_name[config.UD_OFFSET_Y], ud_by_name[config.UD_OFFSET_Z],
            objs.offset, id_rel_pos,
            lambda x, y, z: c4d.Vector(float(x), float(y), float(z)),
        )
    if id_rel_rot and config.UD_ROT_H in ud_by_name and config.UD_ROT_P in ud_by_name and config.UD_ROT_B in ud_by_name:
        _copy_vector_track_from_three_ud(
            doc, rig,
            ud_by_name[config.UD_ROT_H], ud_by_name[config.UD_ROT_P], ud_by_name[config.UD_ROT_B],
            objs.fx, id_rel_rot,
            lambda h, p, b: c4d.Vector(utils.DegToRad(h), utils.DegToRad(p), utils.DegToRad(b)),
        )
    if focal_id and config.UD_FOCAL in ud_by_name:
        desc_focal = c4d.DescID(focal_id)
        _copy_float_track(doc, rig, ud_by_name[config.UD_FOCAL], objs.cam, desc_focal, float)
        _copy_float_track(doc, rig, ud_by_name[config.UD_FOCAL], objs.fx, desc_focal, float)
    if objs.focus and config.UD_FOCUS_DISTANCE in ud_by_name:
        try:
            id_rel_pos_fd = getattr(c4d, "ID_BASEOBJECT_REL_POSITION", None)
            if id_rel_pos_fd is not None:
                desc_z = c4d.DescID(c4d.DescLevel(id_rel_pos_fd, c4d.DTYPE_VECTOR, 0), c4d.DescLevel(2, c4d.DTYPE_REAL, 0))
                _copy_float_track(doc, rig, ud_by_name[config.UD_FOCUS_DISTANCE], objs.focus, desc_z, float)
        except Exception:
            pass


def break_rig_user_data(doc: c4d.documents.BaseDocument, circle: c4d.BaseObject) -> None:
    """
    Break the link between the rig and User Data: transfer animated UD keys to target objects,
    remove rig objects from their layer, and remove the Python Tag from Main_Camera.
    """
    if not doc or not circle:
        return
    objs = get_rig_objects(circle, remove_vibrate=False)
    if not objs:
        log.error("Break: could not resolve rig objects from Main_Camera.")
        return
    from .commands import break_preflight
    break_preflight(objs.rig)
    for node in (circle, objs.follow, objs.offset, objs.cam, objs.fx, objs.look_target, objs.focus, objs.align):
        if node is not None:
            add_undo(doc, c4d.UNDOTYPE_CHANGE, node)
    _transfer_rig_ud_keys_to_targets(doc, objs.rig, circle, objs)
    for obj in (objs.follow, objs.offset, objs.cam, objs.fx, objs.look_target, objs.focus):
        if obj is not None:
            try:
                obj.SetLayerObject(None)
            except Exception:
                pass
    tag = circle.GetFirstTag()
    while tag is not None:
        next_tag = tag.GetNext()
        if tag.GetType() == c4d.Tpython:
            add_undo(doc, c4d.UNDOTYPE_DELETEOBJ, tag)
            tag.Remove()
        tag = next_tag
    c4d.EventAdd()
