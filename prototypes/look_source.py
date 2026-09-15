"""Portable look selection; local target is a sibling of Aim, never its child."""
import c4d


def look_source(root, mode, world, local, aim):
    if mode == 0:
        return None
    if mode == 2:
        if local.GetRelPos().GetLength() < 1e-6:
            raise ValueError('Move Local Target away from the camera origin')
        return local
    if mode != 1:
        raise ValueError('Unknown Aim mode')
    if not isinstance(world,c4d.BaseObject) or world.GetDocument()!=root.GetDocument():
        raise ValueError('Assign a World Target in this document')
    node=world
    while node is not None:
        if node==aim:
            raise ValueError('World Target cannot be inside the driven Aim/Camera hierarchy')
        node=node.GetUp()
    return world
