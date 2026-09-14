"""Open this saved file in C4D Script Manager and Execute to create one rig.

The explicitly active document receives a new rig. No save, camera switch or
legacy-rig modification. runpy.run_path() with its default name does not execute.
"""
from pathlib import Path
import runpy

import c4d


def main(document=None):
    if not c4d.threading.GeIsMainThread():
        raise RuntimeError('Create Simple Camera must run on the C4D main thread')
    if document is None:
        document = c4d.documents.GetActiveDocument()
    if document is None:
        raise RuntimeError('Open the intended Cinema 4D document before creating a rig')
    if '__file__' not in globals():
        raise RuntimeError('Open the saved create_simple_camera.py file in Script Manager')
    builder_path = Path(__file__).resolve().with_name('builder.py')
    builder = runpy.run_path(str(builder_path))
    root, objects, ids = builder['build'](document)
    document.SetActiveObject(root, c4d.SELECTION_NEW)
    c4d.EventAdd()
    return root


if __name__ == '__main__':
    main()
