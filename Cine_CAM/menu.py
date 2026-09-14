"""Small creation/navigation palette. No custom scene object or render dependency."""
import ast
import importlib.util
from pathlib import Path
import c4d

PLUGIN_ID = 10699230
VERSION = '0.5.2'
CK_ROLE_ID = 10699101
ROLE_ID = 10699220


def builder(ck=False):
    folder = Path(__file__).parent
    path = folder / ('ck_runtime' if ck else 'runtime') / 'builder.py'
    if not path.is_file():
        path = folder.parent / 'prototypes' / ('simple_camera' if ck else 'cine_variants') / 'builder.py'
    spec = importlib.util.spec_from_file_location('cine_menu_builder', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def create(document, mode):
    if document is None:
        raise ValueError('Open a document first')
    root, objects, ids = builder(True).build(document) if mode == 3 else builder().build(document, mode)
    if mode == 3:
        root.SetName('CK_CAM POV')
    document.SetActiveObject(root)
    c4d.EventAdd()
    return root, objects, ids


def inspect_ck(root):
    objects, stack = {}, [root]
    parents = {2:1,3:1,4:1,5:4,6:5,7:6,8:7,9:8}
    while stack:
        node = stack.pop()
        role = node.GetDataInstance().GetInt32(CK_ROLE_ID)
        if role:
            if role in objects:
                raise ValueError('Duplicate CK_CAM role')
            objects[role] = node
        stack.extend(node.GetChildren())
    if set(objects) != set(range(1,10)) or any(objects[r].GetUp()!=objects[p] for r,p in parents.items()):
        raise ValueError('Incomplete CK_CAM hierarchy')
    native = {bc[c4d.DESC_NAME]:desc for desc,bc in root.GetUserDataContainer()}
    names = {'camera':'Camera','target':'Target','path':'Path','status':'Status',
        'offset_x':'Body X','offset_y':'Body Y','offset_z':'Body Z',
        'pan':'Pan','tilt':'Tilt','roll':'Roll','walk_strength':'Walk Strength',
        'shake_strength':'Shake Strength','drift_strength':'Drift Strength'}
    if any(name not in native for name in names.values()):
        raise ValueError('Missing CK_CAM controls')
    ids = {key:native[name] for key,name in names.items()}
    if any(root[ids[key]] != objects[role] for key,role in (('camera',9),('target',3),('path',2))):
        raise ValueError('CK_CAM links changed')
    if len([t for t in root.GetTags() if t.GetType()==c4d.Tpython]) != 2:
        raise ValueError('Expected two embedded CK_CAM stages')
    return 3, objects, ids


def inspect(root):
    if root is not None and root.GetDataInstance().GetInt32(CK_ROLE_ID)==1:
        return inspect_ck(root)
    if root is None or root.GetDataInstance().GetInt32(ROLE_ID) != 1:
        raise ValueError('Select a Cine Orbit, Trajectory or Free rig')
    tags = [tag for tag in root.GetTags() if tag.GetType() == c4d.Tpython]
    if len(tags) != 2:
        raise ValueError('Expected exactly two Cine Python Tags')
    headers = []
    for tag in tags:
        source = tag[c4d.TPYTHON_CODE] or ''
        lines = source.splitlines()
        if len(lines) < 2 or not lines[0].startswith('UD = ') or not lines[1].startswith('FIXED_MODE = '):
            raise ValueError('Universal/legacy rig: use its original menu')
        headers.append((ast.literal_eval(lines[0][5:]), ast.literal_eval(lines[1][13:])))
    if headers[0] != headers[1]:
        raise ValueError('Inconsistent embedded stage settings')
    ids, mode = headers[0]
    if type(mode) is not int or mode not in (0,1,2) or not isinstance(ids,dict):
        raise ValueError('Invalid Cine schema')
    parents = {3:1,5:1,9:5,12:9,6:12,7:6,13:7,8:13}
    parents.update(({2:1,4:1},{10:1},{11:1})[mode])
    objects, stack = {}, [root]
    while stack:
        node = stack.pop()
        role = node.GetDataInstance().GetInt32(ROLE_ID)
        if role:
            if role in objects:
                raise ValueError('Duplicate role in rig hierarchy')
            objects[role] = node
        stack.extend(node.GetChildren())
    if set(objects) != set(parents) | {1}:
        raise ValueError('Incomplete rig hierarchy')
    if any(objects[role].GetUp()!=objects[parent] for role,parent in parents.items()):
        raise ValueError('Rig hierarchy changed')
    descriptors = {desc[desc.GetDepth()-1].id:desc for desc,_ in root.GetUserDataContainer()}
    if any(type(slot) is not int or slot not in descriptors for slot in ids.values()):
        raise ValueError('Missing User Data')
    if root[c4d.ID_USERDATA,ids['camera']] != objects[8]:
        raise ValueError('Output camera link changed')
    return mode, objects, {key:descriptors[slot] for key,slot in ids.items()}


def selected(document):
    node = document.GetActiveObject()
    while node is not None and node.GetDataInstance().GetInt32(ROLE_ID) != 1 and node.GetDataInstance().GetInt32(CK_ROLE_ID) != 1:
        node = node.GetUp()
    inspect(node)
    return node


def navigate(document, root, destination):
    mode, objects, ids = inspect(root)
    if destination == 'view':
        document.GetActiveBaseDraw().SetSceneCamera(objects[9 if mode == 3 else 8])
        node = objects[9 if mode == 3 else 8]
    elif destination == 'rig':
        node = root
    elif destination == 'camera':
        node = objects[9 if mode == 3 else 8]
    elif destination == 'target':
        node = root[ids['target']] or objects[3]
    elif destination == 'motion':
        role = (2,10,11,2)[mode]
        node = root[ids[('center','path','free','path')[mode]]] or objects[role]
    else:
        raise ValueError('Unknown navigation action')
    if not isinstance(node,c4d.BaseObject) or node.GetDocument()!=document:
        raise ValueError('Controller link is unavailable in this document')
    document.SetActiveObject(node)
    c4d.EventAdd()
    return node


def reset(root, action):
    mode, _, ids = inspect(root)
    keys = {'framing':('offset_x','offset_y','offset_z','pan','tilt','roll'),
            'effects':(('walk_strength' if mode == 3 else 'spring_strength'),'shake_strength','drift_strength')}[action]
    keyed = [key for key in keys if root.FindCTrack(ids[key]) is not None]
    if keyed:
        raise ValueError('Reset stopped: these controls have animation keys: ' + ', '.join(keyed))
    document = root.GetDocument()
    c4d.StopAllThreads()
    document.StartUndo()
    try:
        document.AddUndo(c4d.UNDOTYPE_CHANGE,root)
        for key in keys:
            root[ids[key]] = 0.
    finally:
        document.EndUndo()
    c4d.EventAdd()


def report(root):
    mode, objects, ids = inspect(root)
    return '\n'.join((root.GetName(), 'Type: '+('Orbit','Trajectory','Free','CK_CAM POV')[mode],
        'Hierarchy: OK ('+str(len(objects))+' objects)', 'Embedded stages: 2',
        'Runtime: '+str(root[ids['status']]),
        'Scene has no Cine plugin dependency. Render/farm acceptance is separate.'))


class CineMenu(c4d.gui.GeDialog):
    def section(self, ident, title, columns):
        self.GroupBegin(ident,c4d.BFH_SCALEFIT,cols=columns,rows=0,title=title)
        self.GroupBorder(c4d.BORDER_GROUP_IN)
        self.GroupBorderSpace(8,6,8,6)

    def buttons(self, entries):
        for ident, label in entries:
            self.AddButton(ident,c4d.BFH_SCALEFIT,name=label)

    def CreateLayout(self):
        self.SetTitle('Camera Rigs '+VERSION)
        self.GroupBegin(90,c4d.BFH_SCALEFIT|c4d.BFV_TOP,cols=1,rows=0)
        self.GroupBorderSpace(8,6,8,6)
        self.section(100,'Create rig',4)
        self.buttons(((101,'Orbit'),(102,'Trajectory'),(103,'Free'),(104,'CK_CAM')))
        self.GroupEnd()
        self.section(200,'Selected rig',1)
        self.AddStaticText(210,c4d.BFH_SCALEFIT,name='Select a rig')
        self.GroupBegin(211,c4d.BFH_SCALEFIT,cols=2,rows=0)
        self.buttons(((201,'Rig controls'),(202,'Movement'),(203,'Target'),(204,'Camera / Lens')))
        self.GroupEnd()
        self.GroupEnd()
        self.section(220,'Viewport',1)
        self.buttons(((205,'Look through camera'),))
        self.GroupEnd()
        self.section(230,'Tools',2)
        self.buttons(((206,'Inspect rig'),(209,'Help / Parameters')))
        self.GroupEnd()
        self.section(240,'Reset  /  Key protection',2)
        self.buttons(((207,'Reset framing'),(208,'Disable effects')))
        self.GroupEnd()
        self.GroupEnd()
        self.SetTimer(300)
        return True

    def Timer(self, message):
        try:
            document = c4d.documents.GetActiveDocument()
            root = document.GetActiveObject() if document else None
            while root is not None and not any(root.GetDataInstance().GetInt32(role)==1 for role in (ROLE_ID,CK_ROLE_ID)):
                root = root.GetUp()
            if root is None:
                raise ValueError('No rig selected')
            label = root.GetName()
            enabled = True
        except Exception:
            label, enabled = 'Select a rig', False
        self.SetString(210,label)
        for button in range(201,209):
            self.Enable(button,enabled)

    def Command(self, button, message):
        try:
            document = c4d.documents.GetActiveDocument()
            if button in (101,102,103,104):
                root,_,_ = create(document,button-101)
                self.SetString(210,'Created '+root.GetName())
                return True
            if button == 209:
                c4d.gui.MessageDialog('Create Orbit, Trajectory, Free or CK_CAM POV. Edit native root User Data.\n\n'
                    'CK_CAM: animate Progress; walking follows speed. Body Y adds jumps.\n'
                    'Orbit: angle/radius/height. Trajectory: Progress. Free: animate Free Controller.\n'
                    'Lens and focus: Select Camera. Effects: Strength=0 disables computation.\n\n'
                    'Reset Framing clears offsets and pan/tilt/roll. Disable Effects sets the three strengths to zero.\n'
                    'Both refuse controls with animation keys; neither deletes keys.\n\n'
                    'Saved rigs need no Camera Rigs plugin. CK_CAM requires Redshift. See README.md in the plugin folder.')
                return True
            root = selected(document)
            if button in (201,202,203,204,205):
                navigate(document,root,{201:'rig',202:'motion',203:'target',204:'camera',205:'view'}[button])
            elif button == 206:
                c4d.gui.MessageDialog(report(root))
            elif button in (207,208):
                reset(root,'framing' if button==207 else 'effects')
            self.SetString(210,root.GetName())
        except Exception as error:
            self.SetString(210,str(error))
            c4d.gui.MessageDialog(str(error))
        return True


class CineCommand(c4d.plugins.CommandData):
    dialog = None

    def Execute(self, document):
        if self.dialog is None:
            self.dialog = CineMenu()
        return self.dialog.Open(c4d.DLG_TYPE_ASYNC,pluginid=PLUGIN_ID,defaultw=340,defaulth=0)

    def RestoreLayout(self, secret):
        if self.dialog is None:
            self.dialog = CineMenu()
        return self.dialog.Restore(pluginid=PLUGIN_ID,secret=secret)
