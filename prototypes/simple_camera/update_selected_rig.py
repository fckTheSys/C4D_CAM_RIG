"""Explicit, bounded upgrade of the selected Simple Camera private v001 rig.

Open in C4D Script Manager and Execute. Only the two verified embedded sources
change; normal runpy loading is inert. No scene save or camera selection.
"""
import hashlib
from pathlib import Path
import runpy

import c4d

ROLE_ID = 10699101
# package_v001/SimpleCamera_private_candidate.zip: builder.source() text join,
# UTF-8 and universal-newline decoding, in motion/path/curve/runtime order.
ACCEPTED_V001_SHA256 = '849f3650fc8bc6b8b74869f68f62c0889272793e9a890a3683d5c8121d8f7437'
ACCEPTED_V002_SHA256 = 'b12bba1205d1cf2b211c4e0d9adf72804c48f26a0ff7dd4a0db50e9d2815d396'


def _digest(source):
    return hashlib.sha256(source.encode('utf-8')).hexdigest()


def _resolve(document):
    root = document.GetActiveObject()
    while root is not None and root.GetDataInstance().GetInt32(ROLE_ID) != 1:
        root = root.GetUp()
    if root is None or root.GetDocument() != document or root.GetUp() is not None:
        raise RuntimeError('Select the top-level Simple Camera root or its descendant')
    objects = {}
    stack = [root]
    while stack:
        node = stack.pop()
        role = node.GetDataInstance().GetInt32(ROLE_ID)
        if role not in range(1, 10) or role in objects or node.GetDocument() != document:
            raise RuntimeError('Unknown or duplicate object role; refuse rig update')
        objects[role] = node
        stack.extend(node.GetChildren())
    if set(objects) != set(range(1, 10)):
        raise RuntimeError('Incomplete native rig; refuse update')
    for role, parent in ((2, 1), (3, 1), (4, 1), (5, 4), (6, 5), (7, 6), (8, 7), (9, 8)):
        if objects[role].GetUp() != objects[parent]:
            raise RuntimeError('Rig hierarchy differs from the supported prototype')
    if not objects[2].CheckType(c4d.Ospline) or objects[9].GetType() != 1057516:
        raise RuntimeError('Expected native spline and Redshift output camera')
    if any(objects[role].GetType() != c4d.Onull for role in (1, 3, 4, 5, 6, 7, 8)):
        raise RuntimeError('Unexpected rig controller type')
    align = objects[4].GetTag(c4d.Taligntospline)
    target = objects[6].GetTag(c4d.Ttargetexpression)
    if (align is None or target is None or
            align[c4d.ALIGNTOSPLINETAG_LINK] != objects[2] or
            target[c4d.TARGETEXPRESSIONTAG_LINK] not in (None, objects[3]) or
            align[c4d.ALIGNTOSPLINETAG_TANGENTIAL]):
        raise RuntimeError('Native route/target configuration differs from supported rig')
    tags = [tag for tag in root.GetTags() if tag.GetType() == c4d.Tpython]
    if len(tags) != 2 or sorted(tag.GetDataInstance().GetInt32(ROLE_ID) for tag in tags) != [1, 2]:
        raise RuntimeError('Expected exactly Prepare and Finish runtime tags')
    return sorted(tags, key=lambda tag: tag.GetDataInstance().GetInt32(ROLE_ID))


def main(document=None):
    if not c4d.threading.GeIsMainThread():
        raise RuntimeError('Rig update requires the C4D main thread')
    if document is None:
        document = c4d.documents.GetActiveDocument()
    if document is None:
        raise RuntimeError('Open a document and select the intended Simple Camera rig')
    tags = _resolve(document)
    builder = runpy.run_path(str(Path(__file__).resolve().with_name('builder.py')))
    current = builder['source']()
    compile(current, '<Simple Camera embedded runtime>', 'exec')
    previous = [tag[c4d.TPYTHON_CODE] for tag in tags]
    if all(source == current for source in previous):
        return {'status': 'UNCHANGED', 'updated_tags': 0, 'sha256': _digest(current)}
    old_hashes={_digest(source) for source in previous if isinstance(source,str)}
    if (not all(isinstance(source,str) for source in previous) or len(old_hashes)!=1 or
            not old_hashes.issubset({ACCEPTED_V001_SHA256, ACCEPTED_V002_SHA256})):
        raise RuntimeError('Unknown or mixed embedded runtime; no tags changed')
    if not document.StartUndo():
        raise RuntimeError('Could not start the rig update Undo transaction')
    try:
        # Record both before writing either: failed Undo registration has no edit.
        for tag in tags:
            if not document.AddUndo(c4d.UNDOTYPE_CHANGE, tag):
                raise RuntimeError('Could not record tag Undo; no update performed')
        try:
            for tag in tags:
                tag[c4d.TPYTHON_CODE] = current
            if any(tag[c4d.TPYTHON_CODE] != current for tag in tags):
                raise RuntimeError('Embedded source verification failed')
        except Exception:
            for tag, old_source in zip(tags, previous):
                tag[c4d.TPYTHON_CODE] = old_source
            if any(tag[c4d.TPYTHON_CODE] != old for tag, old in zip(tags, previous)):
                raise RuntimeError('RECOVERY_REQUIRED: could not restore original runtime sources')
            raise
    finally:
        document.EndUndo()
        c4d.EventAdd()
    return {'status': 'UPDATED', 'updated_tags': 2,
            'from_sha256': next(iter(old_hashes)), 'sha256': _digest(current)}


if __name__ == '__main__':
    main()
