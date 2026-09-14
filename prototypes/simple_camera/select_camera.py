"""Select the sole camera of the selected Simple Camera rig, without switching view.

Open the saved file in C4D Script Manager. A normal runpy import is inert.
Pass an owned document to main(document) for testing without changing active docs.
"""
import c4d

ROLE_ID = 10699101


def main(document=None):
    if not c4d.threading.GeIsMainThread():
        raise RuntimeError('Select Camera must run on the C4D main thread')
    if document is None:
        document = c4d.documents.GetActiveDocument()
    if document is None:
        raise RuntimeError('Open a document and select a Simple Camera rig or its child')
    root = document.GetActiveObject()
    while root is not None and root.GetDataInstance().GetInt32(ROLE_ID) != 1:
        root = root.GetUp()
    if root is None or root.GetDocument() != document:
        raise RuntimeError('Select the Simple Camera root or one of its descendants')
    cameras = []
    stack = list(root.GetChildren())
    while stack:
        node = stack.pop()
        if node.GetDataInstance().GetInt32(ROLE_ID) == 9:
            cameras.append(node)
        stack.extend(node.GetChildren())
    if len(cameras) != 1 or cameras[0].GetDocument() != document:
        raise RuntimeError('The selected rig must contain exactly one output camera')
    camera = cameras[0]
    document.SetActiveObject(camera, c4d.SELECTION_NEW)
    c4d.EventAdd()
    return camera


if __name__ == '__main__':
    main()
