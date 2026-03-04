# -*- coding: utf-8 -*-
import os
import sys
import traceback

import c4d
from c4d import plugins

# ------------------------------------------------
# ЛОГ ДЛЯ ОТЛАДКИ (видно в Script Log / Консоль C4D)
# ------------------------------------------------

def _log(msg):
    """Печать в консоль C4D (Script Log)."""
    c4d.GePrint("[CamRig] " + str(msg))


def _log_ok(msg):
    c4d.GePrint("[CamRig] OK: " + str(msg))


def _log_err(msg):
    c4d.GePrint("[CamRig] ERROR: " + str(msg))


# ------------------------------------------------
# ПУТЬ И ИМПОРТЫ
# ------------------------------------------------

def _setup_plugin_path():
    """Добавляет директорию плагина в sys.path для import camrig."""
    try:
        script_path = os.path.abspath(__file__)
    except Exception:
        script_path = os.path.abspath(os.path.join(os.getcwd(), "cam_rig_builder.pyp"))
    this_dir = os.path.dirname(script_path)
    _log("Plugin script path: " + this_dir)
    paths_to_add = [this_dir]
    parent = os.path.dirname(this_dir)
    if parent and parent not in paths_to_add:
        paths_to_add.append(parent)
    for p in paths_to_add:
        if p and p not in sys.path:
            sys.path.insert(0, p)
            _log_ok("Added to sys.path: " + p)


_setup_plugin_path()

config = None
build_cam_rig = None
reset_rig_to_defaults = None

try:
    from camrig import config as _config
    from camrig.rig_builder import build_cam_rig as _build_cam_rig, reset_rig_to_defaults as _reset_rig_to_defaults
    config = _config
    build_cam_rig = _build_cam_rig
    reset_rig_to_defaults = _reset_rig_to_defaults
    _log_ok("Imports: camrig.config, camrig.rig_builder")
except Exception as e:
    _log_err("Import failed: " + str(e))
    traceback.print_exc()


# ------------------------------------------------
# ID КНОПОК ДИАЛОГА
# ------------------------------------------------
ID_GROUP_MAIN = 1000
ID_BTN_CREATE_RIG = 1001
ID_GROUP_RESET = 1002
ID_BTN_RESET_ALL = 1003


def _find_main_camera_from_selection(doc):
    """По активному объекту находит Main_Camera (circle) рига, если это риг или его потомок."""
    active = doc.GetActiveObject()
    if not active:
        return None
    obj = active
    while obj.GetUp():
        obj = obj.GetUp()
    if obj.GetName() == config.RIG_ROOT_NAME:
        child = obj.GetDown()
        while child:
            if child.GetName() == config.MAIN_CAMERA_NAME:
                return child
            child = child.GetNext()
    if active.GetName() == config.MAIN_CAMERA_NAME:
        return active
    return None


# ------------------------------------------------
# ДИАЛОГ С КНОПКОЙ CREATE RIG И RESET
# ------------------------------------------------

class CamRigDialog(c4d.gui.GeDialog):

    def CreateLayout(self):
        self.SetTitle(config.PLUGIN_NAME)
        self.GroupBegin(id=ID_GROUP_MAIN, flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, cols=1)
        self.GroupBorderSpace(10, 10, 10, 10)
        self.AddButton(id=ID_BTN_CREATE_RIG, flags=c4d.BFH_SCALEFIT, name="Create rig")
        self.GroupBegin(id=ID_GROUP_RESET, flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, cols=1, title="Rig controls")
        self.AddButton(id=ID_BTN_RESET_ALL, flags=c4d.BFH_SCALEFIT, name="Reset to defaults")
        self.GroupEnd()
        self.GroupEnd()
        return super().CreateLayout()

    def Command(self, id, msg):
        if id == ID_BTN_CREATE_RIG:
            self._on_create_rig()
        elif id == ID_BTN_RESET_ALL:
            self._on_reset_to_defaults()
        return True

    def _on_reset_to_defaults(self):
        if reset_rig_to_defaults is None:
            c4d.gui.MessageDialog("Cam Rig: reset not loaded. Check Script Log.")
            return
        doc = c4d.documents.GetActiveDocument()
        if not doc:
            return
        circle = _find_main_camera_from_selection(doc)
        if not circle:
            c4d.gui.MessageDialog("Select the Cam_Rig or Main_Camera object, then click Reset.")
            return
        try:
            reset_rig_to_defaults(circle)
            c4d.EventAdd()
            c4d.gui.MessageDialog("Parameters reset to defaults.")
        except Exception as e:
            _log_err("Reset failed: " + str(e))
            c4d.gui.MessageDialog("Error: " + str(e))

    def _on_create_rig(self):
        if build_cam_rig is None:
            _log_err("build_cam_rig not loaded.")
            c4d.gui.MessageDialog("Cam Rig: import error. Check Script Log.")
            return
        doc = c4d.documents.GetActiveDocument()
        if not doc:
            c4d.gui.MessageDialog("No active document.")
            return
        active = doc.GetActiveObject()
        position_global = None
        if active and active.GetType() == c4d.Onull:
            position_global = active.GetMg()
            _log("Using active null coordinates: " + active.GetName())
        else:
            _log("No null selected — rig will be created at origin.")
        try:
            build_cam_rig(doc, position_global=position_global)
            c4d.EventAdd()
            _log_ok("Rig created.")
            c4d.gui.MessageDialog("Rig created.")
        except Exception as e:
            _log_err("Create rig failed: " + str(e))
            traceback.print_exc()
            c4d.gui.MessageDialog("Error: " + str(e))


# ------------------------------------------------
# КОМАНДНЫЙ ПЛАГИН
# ------------------------------------------------

class CamRigCommand(plugins.CommandData):

    _dialog = None

    def Execute(self, doc):
        """
        Открывает диалог с кнопкой Create rig.
        Риг всегда создаётся в корне сцены; если выбран null — в его координатах.
        """
        if CamRigCommand._dialog is None:
            CamRigCommand._dialog = CamRigDialog()
        CamRigCommand._dialog.Open(c4d.DLG_TYPE_ASYNC, config.PLUGIN_ID)
        return True

    def RestoreLayout(self, secret):
        """Восстанавливает диалог при загрузке layout C4D."""
        if CamRigCommand._dialog is None:
            CamRigCommand._dialog = CamRigDialog()
        return CamRigCommand._dialog.Restore(config.PLUGIN_ID, secret)


# ------------------------------------------------
# РЕГИСТРАЦИЯ ПЛАГИНА
# ------------------------------------------------

def PluginStart():
    _log("PluginStart() called")
    if config is None:
        _log_err("Config not loaded. Plugin not registered.")
        return False
    try:
        result = plugins.RegisterCommandPlugin(
            id=config.PLUGIN_ID,
            str=config.PLUGIN_NAME,
            info=0,
            icon=None,
            help=config.PLUGIN_HELP,
            dat=CamRigCommand(),
        )
        if result:
            _log_ok("Registered: " + config.PLUGIN_NAME)
        else:
            _log_err("RegisterCommandPlugin returned False")
        return result
    except Exception as e:
        _log_err("PluginStart failed: " + str(e))
        traceback.print_exc()
        return False


if __name__ == "__main__":
    PluginStart()
