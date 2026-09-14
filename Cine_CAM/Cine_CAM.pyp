"""Private Cine Camera creation palette; saved rigs are portable."""
import importlib.util
from pathlib import Path
import sys
import c4d

name = 'cine_camera_menu'
if name not in sys.modules:
    spec = importlib.util.spec_from_file_location(name,Path(__file__).with_name('menu.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)

if __name__ == '__main__':
    module = sys.modules[name]
    if c4d.plugins.FindPlugin(module.PLUGIN_ID) is not None:
        raise RuntimeError('Private Cine Camera command ID is already in use')
    c4d.plugins.RegisterCommandPlugin(id=module.PLUGIN_ID,str='Camera Rigs (Cine + CK_CAM)',info=0,icon=None,
        help='Create Orbit, Trajectory, Free and CK_CAM POV; navigate and inspect rigs',dat=module.CineCommand())
