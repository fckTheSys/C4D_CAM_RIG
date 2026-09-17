"""Small creation/navigation palette. No custom scene object or render dependency."""
import ast
import importlib.util
import colorsys
import random
from pathlib import Path
import c4d

PLUGIN_ID = 10699230
VERSION = '0.5.7'
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
    names={node.GetName() for node in scene_objects(document)}
    if mode == 3:
        number=1
        while 'CK_CAM_%03d'%number in names:
            number+=1
        # Builder names Camera and targets after the root and owns L_CAM_RIG.
        root, objects, ids = builder(True).build(document, 'CK_CAM_%03d'%number)
        root[c4d.ID_BASEOBJECT_USECOLOR]=c4d.ID_BASEOBJECT_USECOLOR_ALWAYS
        root[c4d.ID_BASEOBJECT_COLOR]=c4d.Vector(*colorsys.hsv_to_rgb(random.random(),.65,.9))
        document.SetActiveObject(root)
        c4d.EventAdd()
        return root, objects, ids
    root, objects, ids = builder().build(document, mode)
    camera=objects[8]
    base=root.GetName();number=1
    while base+' %03d'%number in names or 'CAM | '+base+' %03d'%number in names:
        number+=1
    root.SetName(base+' %03d'%number)
    camera.SetName('CAM | '+root.GetName())
    objects[3].SetName('World Target | '+root.GetName())
    objects[14].SetName('Local Target | '+root.GetName())
    root[c4d.ID_BASEOBJECT_USECOLOR]=c4d.ID_BASEOBJECT_USECOLOR_ALWAYS
    root[c4d.ID_BASEOBJECT_COLOR]=c4d.Vector(*colorsys.hsv_to_rgb(random.random(),.65,.9))
    document.SetActiveObject(root)
    c4d.EventAdd()
    return root, objects, ids


def scene_objects(document):
    """Real document objects only, never generator cache or stored stale wrappers."""
    if document is None:return
    stack=list(reversed(document.GetObjects()))
    while stack:
        node=stack.pop()
        yield node
        stack.extend(reversed(node.GetChildren()))


def owning_rig(node):
    while node is not None:
        if any(node.GetDataInstance().GetInt32(role)==1 for role in (ROLE_ID,CK_ROLE_ID)):
            return node
        node=node.GetUp()
    return None


def scene_cameras(document):
    rows=[]
    for camera in scene_objects(document):
        if not bundle_camera(camera):continue
        root=owning_rig(camera)
        names=[];node=camera
        while node is not None:
            names.append(node.GetName());node=node.GetUp()
        path=' / '.join(reversed(names))
        label=root.GetName() if root and root.GetName()==camera.GetName() else (root.GetName()+' / '+camera.GetName()) if root else path
        rows.append({'id':str(camera.GetGUID()),'label':label,'path':path,
                     'rig':root.GetName() if root else '', 'camera':camera.GetName()})
    counts={}
    for row in rows:counts[row['label']]=counts.get(row['label'],0)+1
    for row in rows:
        if counts[row['label']]>1:row['label']+=' ['+row['id'][-8:]+']'
    return rows


def bundle_camera(camera):
    if camera is None or camera.GetType() not in (c4d.Ocamera,1057516):return False
    root=owning_rig(camera)
    if root is None:return False
    return any(camera.GetDataInstance().GetInt32(role)==output and root.GetDataInstance().GetInt32(role)==1
               for role,output in ((ROLE_ID,8),(CK_ROLE_ID,9)))


def active_bundle_camera(document):
    draw=document.GetActiveBaseDraw() if document else None
    camera=draw.GetSceneCamera(document) if draw else None
    return str(camera.GetGUID()) if bundle_camera(camera) else None


def filter_cameras(rows,query):
    terms=query.casefold().split()
    return [row for row in rows if all(term in row['path'].casefold() for term in terms)]


def resolve_camera(document,ident):
    for node in scene_objects(document):
        if bundle_camera(node) and str(node.GetGUID())==ident:return node
    raise ValueError('Camera is no longer in this document. Refresh the camera list.')


def switch_camera(document,ident):
    if document is None:raise ValueError('Open a document first')
    camera=None if ident is None else resolve_camera(document,ident)
    draw=document.GetActiveBaseDraw()
    if draw is None:raise ValueError('No active viewport')
    draw.SetSceneCamera(camera)
    c4d.EventAdd()
    return camera


def select_camera_rig(document,ident):
    camera=resolve_camera(document,ident)
    node=owning_rig(camera) or camera
    document.SetActiveObject(node)
    c4d.EventAdd()
    return node


class CameraBrowser:
    """Pending list selection is separate from the active viewport camera."""
    def __init__(self):
        self.document=None;self.rows=[];self.filtered=[];self.pending=None
        self.query='';self.last_active=None

    def refresh(self,document):
        if document!=self.document:
            self.pending=None;self.last_active=None
        self.document=document;self.rows=scene_cameras(document)
        self.filter(self.query)
        self.sync_active()

    def filter(self,query):
        self.query=query;self.filtered=filter_cameras(self.rows,query)
        visible={row['id'] for row in self.filtered}
        if self.pending not in visible:
            active=active_bundle_camera(self.document)
            self.pending=active if active in visible else None

    def sync_active(self):
        active=active_bundle_camera(self.document)
        if active!=self.last_active and any(row['id']==active for row in self.filtered):
            self.pending=active
        self.last_active=active
        return active

    def choose(self,ident,confirm=False):
        if not any(row['id']==ident for row in self.filtered):raise ValueError('Choose a camera from the current list')
        resolve_camera(self.document,ident)
        self.pending=ident
        if confirm or active_bundle_camera(self.document) is not None:
            switch_camera(self.document,ident)
            self.last_active=ident
            return True
        return False

    def neighbour(self,step):
        ids=[row['id'] for row in self.filtered]
        index=ids.index(self.pending) if self.pending in ids else -1
        destination=index+step
        return ids[destination] if 0<=destination<len(ids) else None

    def move(self,step):
        ident=self.neighbour(step)
        if ident is not None:return self.choose(ident)
        return False


def inspect_ck(root):
    objects, stack = {}, [root]
    parents = {2:1,3:1,4:1,5:4,6:5,7:6,8:7,9:8}
    native = {bc[c4d.DESC_NAME]:desc for desc,bc in root.GetUserDataContainer()}
    if 'Aim Mode' in native: parents[10]=5
    while stack:
        node = stack.pop()
        role = node.GetDataInstance().GetInt32(CK_ROLE_ID)
        if role:
            if role in objects:
                raise ValueError('Duplicate CK_CAM role')
            objects[role] = node
        stack.extend(node.GetChildren())
    expected=set(parents)|{1}
    if set(objects) not in (expected,expected-{2}) or any(objects[r].GetUp()!=objects[p] for r,p in parents.items() if r in objects):
        raise ValueError('Incomplete CK_CAM hierarchy')
    native = {bc[c4d.DESC_NAME]:desc for desc,bc in root.GetUserDataContainer()}
    names = {'camera':'Camera','target':'Target','path':'Path','status':'Status','aim_mode':'Aim Mode' if 'Aim Mode' in native else 'Use Target',
        'offset_x':'Body X','offset_y':'Body Y','offset_z':'Body Z',
        'pan':'Pan','tilt':'Tilt','roll':'Roll','walk_strength':'Walk Strength',
        'shake_strength':'Shake Strength','drift_strength':'Drift Strength'}
    if any(name not in native for name in names.values()):
        raise ValueError('Missing CK_CAM controls')
    ids = {key:native[name] for key,name in names.items()}
    if root[ids['camera']] != objects[9]:
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
    expected = set(parents) | {1}
    if 14 in objects:
        parents[14]=12
        expected.add(14)
    if set(objects) != expected and not (mode == 1 and set(objects) == expected - {10}):
        raise ValueError('Incomplete rig hierarchy')
    if any(objects[role].GetUp()!=objects[parent] for role,parent in parents.items() if role in objects):
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
        aim_mode=int(root[ids['aim_mode']])
        if aim_mode==0:
            raise ValueError('Manual aim is active. Choose World Target or Local Target in rig controls to use a look target.')
        node = root if aim_mode==0 else objects.get(10 if mode==3 else 14) if aim_mode==2 else root[ids['target']]
    elif destination == 'motion':
        role = (2,10,11,2)[mode]
        node = root[ids[('center','path','free','path')[mode]]]
        if mode in (0,2) and node is None:
            node = objects.get(role)
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


def selected_ck(document):
    root=selected(document)
    if root.GetDataInstance().GetInt32(CK_ROLE_ID)!=1:
        raise ValueError('Select a CK_CAM rig')
    return root


def sync_names(root):
    """Camera and targets follow the root name; one Undo step."""
    ck=builder(True);obj=ck.rig_nodes(root);document=root.GetDocument()
    document.StartUndo()
    try:
        for role in (9,3,10):
            if role in obj:document.AddUndo(c4d.UNDOTYPE_CHANGE_SMALL,obj[role])
        ck.apply_names(obj,root.GetName())
    finally:
        document.EndUndo()
    c4d.EventAdd()


def upgrade_ck(root):
    c4d.StopAllThreads()
    result=builder(True).upgrade(root.GetDocument(),root)
    c4d.EventAdd()
    if not result['changed']:
        return root.GetName()+': runtime is already current. Service nodes are on L_CAM_RIG.'
    basis='its top-level copy' if result['reference']=='top_level_copy' else 'the previous runtime'
    detail='camera matches %s on %d frames (max error %.2g)'%(basis,len(result['frames']),result['max_error'])
    return root.GetName()+': upgraded to CK_CAM '+builder(True).VERSION+'; '+detail+'.'


def report(root):
    mode, objects, ids = inspect(root)
    return '\n'.join((root.GetName(), 'Type: '+('Orbit','Trajectory','Free','CK_CAM POV')[mode],
        'Hierarchy: OK ('+str(len(objects))+' objects)', 'Embedded stages: 2',
        'Runtime: '+str(root[ids['status']]),
        'Scene has no Cine plugin dependency. Render/farm acceptance is separate.'))


class CineMenu(c4d.gui.GeDialog):
    def refresh_browser(self,document,rescan=True):
        if not hasattr(self,'browser'):self.browser=CameraBrowser()
        if rescan:
            self.browser.refresh(document)
        self.browser.filter(self.GetString(301))
        rows=self.browser.filtered
        self._camera_choices={index+1:row['id'] for index,row in enumerate(rows)}
        self.FreeChildren(302)
        self.AddChild(302,0,'Choose camera')
        for index,row in enumerate(rows):self.AddChild(302,index+1,row['label'])
        self.browser_status(document)

    def browser_status(self,document):
        active=self.browser.sync_active()
        ident=self.browser.pending
        selected=next((i for i,guid in getattr(self,'_camera_choices',{}).items() if guid==ident),0)
        self.SetInt32(302,selected)
        total=len(self.browser.rows);shown=len(self.browser.filtered)
        self.SetString(305,'%d cameras / %d matches | %s'%(total,shown,'Live switching' if active else 'Choose, then Activate camera'))
        self.Enable(304,bool(selected))
        self.Enable(310,bool(selected) and ident!=active)
        self.Enable(308,self.browser.neighbour(-1) is not None)
        self.Enable(309,self.browser.neighbour(1) is not None)

    def section(self, ident, title, columns):
        self.GroupBegin(ident,c4d.BFH_SCALEFIT,cols=columns,rows=0,title=title)
        self.GroupBorder(c4d.BORDER_GROUP_IN)
        self.GroupBorderSpace(8,6,8,6)

    def buttons(self, entries):
        for ident, label in entries:
            self.AddButton(ident,c4d.BFH_SCALEFIT,name=label)

    def CreateLayout(self):
        self.layout_version=VERSION
        self.SetTitle('Camera Rigs '+VERSION)
        self.GroupBegin(90,c4d.BFH_SCALEFIT|c4d.BFV_TOP,cols=1,rows=0)
        self.GroupBorderSpace(8,6,8,6)
        self.section(100,'Create rig',4)
        self.buttons(((101,'Orbit'),(102,'Trajectory'),(103,'Free'),(104,'CK_CAM')))
        self.GroupEnd()
        self.section(200,'Selected rig',1)
        self.AddStaticText(210,c4d.BFH_SCALEFIT,name='Select a rig')
        self.GroupBegin(211,c4d.BFH_SCALEFIT,cols=2,rows=0)
        self.buttons(((201,'Rig controls'),(202,'Movement'),(203,'Active look target'),(204,'Camera / Lens')))
        self.GroupEnd()
        self.GroupEnd()
        self.section(220,'Viewport',1)
        self.buttons(((205,'Look through camera'),))
        self.GroupEnd()
        self.section(300,'Camera Rigs in scene',1)
        self.AddStaticText(306,c4d.BFH_SCALEFIT,name='Search camera or rig name')
        self.AddEditText(301,c4d.BFH_SCALEFIT)
        self.GroupBegin(311,c4d.BFH_SCALEFIT,cols=3,rows=0)
        self.AddButton(308,c4d.BFH_LEFT,initw=28,name='←')
        self.AddComboBox(302,c4d.BFH_SCALEFIT,initw=260)
        self.AddButton(309,c4d.BFH_RIGHT,initw=28,name='→')
        self.GroupEnd()
        self.AddStaticText(305,c4d.BFH_SCALEFIT,name='Refresh to find scene cameras')
        self.GroupBegin(307,c4d.BFH_SCALEFIT,cols=2,rows=0)
        self.buttons(((310,'Activate camera'),(304,'Select camera rig')))
        self.GroupEnd()
        self.buttons(((303,'Refresh cameras'),))
        self.GroupEnd()
        self.section(230,'Tools',2)
        self.buttons(((206,'Inspect rig'),(209,'Help / Parameters'),(250,'Sync CK_CAM names'),(251,'Upgrade CK_CAM')))
        self.GroupEnd()
        self.section(240,'Reset  /  Key protection',2)
        self.buttons(((207,'Reset framing'),(208,'Disable effects')))
        self.GroupEnd()
        self.GroupEnd()
        self.SetTimer(300)
        return True

    def InitValues(self):
        self.refresh_browser(c4d.documents.GetActiveDocument())
        return True

    def Timer(self, message):
        try:
            document = c4d.documents.GetActiveDocument()
            if not hasattr(self,'browser') or document!=self.browser.document:
                self.refresh_browser(document)
            else:
                self.browser_status(document)
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
        for button in (*range(201,209),250,251):
            self.Enable(button,enabled)

    def Command(self, button, message):
        try:
            document = c4d.documents.GetActiveDocument()
            if button in (301,302,303,304,308,309,310):
                if not hasattr(self,'browser') or document!=self.browser.document:
                    self.refresh_browser(document)
                    return True
                if button in (301,303):
                    self.refresh_browser(document,rescan=button==303)
                else:
                    index=self.GetInt32(302)
                    if button in (308,309):self.browser.move(-1 if button==308 else 1)
                    elif button==310 and self.browser.pending:self.browser.choose(self.browser.pending,confirm=True)
                    elif button==304 and self.browser.pending:select_camera_rig(document,self.browser.pending)
                    elif button==302 and index in self._camera_choices:self.browser.choose(self._camera_choices[index])
                    self.browser_status(document)
                return True
            if button in (101,102,103,104):
                root,_,_ = create(document,button-101)
                self.SetString(210,'Created '+root.GetName())
                self.refresh_browser(document)
                return True
            if button == 209:
                c4d.gui.MessageDialog('Create Orbit, Trajectory, Free or CK_CAM POV. Edit native root User Data.\n\n'
                    'CK_CAM: animate Progress; walking follows speed. Body Y adds jumps.\n'
                    'Orbit: angle/radius/height. Trajectory: Progress. Free: animate Free Controller.\n'
                    'Lens and focus: Select Camera. Effects: Strength=0 disables computation.\n\n'
                    'Reset Framing clears offsets and pan/tilt/roll. Disable Effects sets the three strengths to zero.\n'
                    'Both refuse controls with animation keys; neither deletes keys.\n\n'
                    'Aim mode: Manual / World Target / Local Target. Target button selects the active look controller. '
                    'Move/key Local Target XYZ; farther Z gives gentler aiming. Pan/Tilt/Roll add offsets. '
                    'CK_CAM may sit inside static Null groups (no transform keys, scale 1). '
                    'Service nulls live on layer L_CAM_RIG: keep its Expressions/Animation/Generators on. '
                    'Sync CK_CAM names renames Camera and targets after the rig. Upgrade CK_CAM updates an older rig after checking the camera is unchanged.\n\n'
                    'Saved rigs need no Camera Rigs plugin. CK_CAM requires Redshift. See README.md in the plugin folder.')
                return True
            root = selected(document)
            if button in (201,202,203,204,205):
                navigate(document,root,{201:'rig',202:'motion',203:'target',204:'camera',205:'view'}[button])
            elif button == 206:
                c4d.gui.MessageDialog(report(root))
            elif button in (207,208):
                reset(root,'framing' if button==207 else 'effects')
            elif button == 250:
                sync_names(selected_ck(document))
            elif button == 251:
                c4d.gui.MessageDialog(upgrade_ck(selected_ck(document)))
            self.SetString(210,root.GetName())
        except Exception as error:
            self.SetString(210,str(error))
            c4d.gui.MessageDialog(str(error))
        return True


class CineCommand(c4d.plugins.CommandData):
    dialog = None

    def Execute(self, document):
        if self.dialog is None or getattr(self.dialog,'layout_version',None)!=VERSION:
            if self.dialog is not None:self.dialog.Close()
            self.dialog = CineMenu()
        return self.dialog.Open(c4d.DLG_TYPE_ASYNC,pluginid=PLUGIN_ID,defaultw=340,defaulth=0)

    def RestoreLayout(self, secret):
        if self.dialog is None or getattr(self.dialog,'layout_version',None)!=VERSION:
            self.dialog = CineMenu()
        return self.dialog.Restore(pluginid=PLUGIN_ID,secret=secret)
