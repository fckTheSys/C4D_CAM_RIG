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
    """Добавляет директорию плагина в sys.path для import camrig. Возвращает корень плагина."""
    try:
        script_path = os.path.abspath(__file__)
    except Exception:
        script_path = os.path.abspath(os.path.join(os.getcwd(), "cam_rig_builder.pyp"))
    this_dir = os.path.dirname(script_path)
    paths_to_add = [this_dir]
    parent = os.path.dirname(this_dir)
    if parent and parent not in paths_to_add:
        paths_to_add.append(parent)
    for p in paths_to_add:
        if p and p not in sys.path:
            sys.path.insert(0, p)
    return this_dir


_PLUGIN_ROOT = _setup_plugin_path()

config = None
build_cam_rig = None
reset_rig_to_defaults = None
reset_rig_params = None
break_rig_user_data = None

if os.path.isdir(os.path.join(_PLUGIN_ROOT, "camrig")):
    try:
        from camrig import config as _config
        from camrig.rig_builder import build_cam_rig as _build_cam_rig
        from camrig.rig_builder import reset_rig_to_defaults as _reset_all
        from camrig.rig_builder import reset_rig_params as _reset_params
        from camrig.rig_builder import break_rig_user_data as _break_ud
        from camrig.rig_builder import validate_ud_template_vs_config as _validate_ud_template
        from camrig.diagnostics import (
            run_self_check as _run_self_check,
            inspect_rig as _inspect_rig,
            repair_selected_rig as _repair_selected_rig,
        )
        try:
            from camrig import tag_embedded as _tag_embedded
            _emb = getattr(_tag_embedded, "EMBEDDED_RUNTIME_VERSION", None)
            if _emb != _config.PLUGIN_VERSION:
                c4d.GePrint(
                    "[CamRig] WARNING: tag_embedded EMBEDDED_RUNTIME_VERSION (%s) != PLUGIN_VERSION (%s) — sync versions."
                    % (_emb, _config.PLUGIN_VERSION)
                )
        except Exception:
            pass
        _validate_ud_template()
        config = _config
        build_cam_rig = _build_cam_rig
        reset_rig_to_defaults = _reset_all
        reset_rig_params = _reset_params
        break_rig_user_data = _break_ud
        c4d.GePrint("[CamRig] v%s loaded" % _config.PLUGIN_VERSION)
    except Exception as e:
        _log_err("Import failed: " + str(e))
        _log_err(
            "Проверьте: рядом с .pyp лежит camrig/ с __init__.py и .pyc (production), "
            "и Python версии C4D совпадает со сборкой bytecode."
        )
        traceback.print_exc()
else:
    _log_err(
        "Папка camrig/ не найдена рядом с cam_rig_builder.pyp. "
        "Скопируйте в plugins весь каталог плагина (cam_rig_builder.pyp + camrig/), не один только .pyp."
    )



def _find_rig(doc):
    """Ищет Cam_Rig в иерархии от выбранного объекта вверх, затем в корне сцены."""
    if config is None:
        return None
    if not doc:
        return None
    active = doc.GetActiveObject()
    if active:
        obj = active
        while obj:
            name = obj.GetName()
            if name == config.RIG_ROOT_NAME or name.startswith(config.RIG_ROOT_NAME + "_"):
                return obj
            obj = obj.GetUp()
    # Запасной вариант: первый риг в корне сцены
    root = doc.GetFirstObject()
    while root:
        name = root.GetName()
        if name == config.RIG_ROOT_NAME or name.startswith(config.RIG_ROOT_NAME + "_"):
            return root
        root = root.GetNext()
    return None


def _load_camrig_icon():
    """Загружает встроенную иконку камеры C4D для CamRigRoot."""
    try:
        return c4d.bitmaps.InitResourceBitmap(c4d.Ocamera)
    except (AttributeError, TypeError):
        return None


# ------------------------------------------------
# OBJECTDATA: CamRigRoot (null с иконкой камеры)
# ------------------------------------------------

class CamRigRootData(plugins.ObjectData):
    """Null-подобный объект с иконкой камеры для корня Cam_Rig."""

    def Init(self, op, isCloneInit=False):
        # C4D 2024+ NodeData.Init(node, isCloneInit); обязателен в 2025.0
        return True

def _register_camrig_root():
    """Регистрирует ObjectData CamRigRoot."""
    try:
        icon = _load_camrig_icon()
        return plugins.RegisterObjectPlugin(
            id=config.PLUGIN_ID_CAMRIG_ROOT,
            str="Cam Rig Root",
            g=CamRigRootData,
            description="ocamrigroot",
            icon=icon,
            info=c4d.OBJECT_NULL,
        )
    except Exception as e:
        _log_err("CamRigRoot registration failed: " + str(e))
        return False


def _find_main_camera(doc):
    """По выделению находит Main_Camera (circle) рига. Сначала ищет rig, затем дочерний Main_Camera."""
    rig = _find_rig(doc)
    if not rig:
        return None
    child = rig.GetDown()
    while child:
        if child.GetName().startswith(config.MAIN_CAMERA_NAME):
            return child
        child = child.GetNext()
    return None


# ------------------------------------------------
# ID ДИАЛОГА
# ------------------------------------------------
ID_GROUP_MAIN         = 1000
ID_BTN_CREATE_RIG     = 1001
ID_GROUP_RESET        = 1010
ID_BTN_RESET_ORBIT    = 1011
ID_BTN_RESET_TRANSFORM = 1012
ID_BTN_RESET_CAMERA   = 1013
ID_BTN_RESET_TARGET   = 1014
ID_BTN_RESET_SHAKE    = 1015
ID_BTN_RESET_ALL      = 1016
ID_BTN_BREAK_UD       = 1020
ID_BTN_INSPECT_RIG    = 1021
ID_BTN_REPAIR_RIG     = 1022
ID_BTN_SELF_CHECK     = 1023

_RESET_BUTTONS = [
    (ID_BTN_RESET_ORBIT,    "orbit",    "Reset Orbit"),
    (ID_BTN_RESET_TRANSFORM, "transform", "Reset Transform"),
    (ID_BTN_RESET_CAMERA,   "camera",   "Reset Camera"),
    (ID_BTN_RESET_TARGET,   "target",   "Reset Target"),
    (ID_BTN_RESET_SHAKE,    "shake",    "Reset Shake"),
]


class CamRigDialog(c4d.gui.GeDialog):

    def Init(self, isCloneInit=False):
        return True

    def CreateLayout(self):
        self.SetTitle("%s v%s" % (config.PLUGIN_NAME, config.PLUGIN_VERSION))

        self.GroupBegin(id=ID_GROUP_MAIN, flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, cols=1)
        self.GroupBorderSpace(10, 10, 10, 10)

        self.GroupBegin(id=1001, flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, cols=2)
        self.AddButton(id=ID_BTN_CREATE_RIG, flags=c4d.BFH_SCALEFIT, initw=0, inith=0, name="Create Rig")
        self.AddButton(id=ID_BTN_BREAK_UD, flags=c4d.BFH_SCALEFIT, initw=0, inith=0, name="Break User Data")
        self.AddButton(id=ID_BTN_INSPECT_RIG, flags=c4d.BFH_SCALEFIT, initw=0, inith=0, name="Rig Inspector")
        self.AddButton(id=ID_BTN_REPAIR_RIG, flags=c4d.BFH_SCALEFIT, initw=0, inith=0, name="Repair Selected Rig")
        self.GroupEnd()
        self.AddButton(id=ID_BTN_SELF_CHECK, flags=c4d.BFH_SCALEFIT, initw=0, inith=0, name="Self check / diagnostics")

        self.AddSeparatorH(0)

        self.GroupBegin(id=ID_GROUP_RESET, flags=c4d.BFH_SCALEFIT, cols=3, title="Reset")
        self.GroupBorder(c4d.BORDER_GROUP_IN)
        self.GroupBorderSpace(6, 6, 6, 6)
        for btn_id, _, label in _RESET_BUTTONS:
            self.AddButton(btn_id, c4d.BFH_SCALEFIT, initw=0, inith=0, name=label)
        self.AddButton(id=ID_BTN_RESET_ALL, flags=c4d.BFH_SCALEFIT, initw=0, inith=0, name="Reset All")
        self.GroupEnd()

        self.GroupEnd()
        return super().CreateLayout()

    def Command(self, id, msg):
        if id == ID_BTN_CREATE_RIG:
            self._on_create_rig()
        elif id == ID_BTN_RESET_ALL:
            self._on_reset_all()
        elif id == ID_BTN_BREAK_UD:
            self._on_break_user_data()
        elif id == ID_BTN_INSPECT_RIG:
            self._on_inspect_rig()
        elif id == ID_BTN_REPAIR_RIG:
            self._on_repair_rig()
        elif id == ID_BTN_SELF_CHECK:
            self._on_self_check()
        else:
            for btn_id, group_key, _ in _RESET_BUTTONS:
                if id == btn_id:
                    self._on_reset_group(group_key)
                    break
        return True

    # --------------------------------------------------

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
        if active and (active.GetType() == c4d.Onull or active.GetType() == config.PLUGIN_ID_CAMRIG_ROOT):
            position_global = active.GetMg()
            _log("Using active null coordinates: " + active.GetName())
        else:
            _log("No null selected — rig will be created at origin.")
        try:
            rig = build_cam_rig(doc, position_global=position_global)
            if rig is not None:
                doc.SetSelection(rig, c4d.SELECTION_NEW)
            c4d.EventAdd()
            _log_ok("Rig created.")
            c4d.gui.MessageDialog("Rig created.")
        except Exception as e:
            _log_err("Create rig failed: " + str(e))
            traceback.print_exc()
            c4d.gui.MessageDialog("Error: " + str(e))

    def _on_reset_group(self, group_key):
        if reset_rig_params is None:
            c4d.gui.MessageDialog("Reset function not loaded.")
            return
        doc = c4d.documents.GetActiveDocument()
        rig = _find_rig(doc)
        if not rig:
            c4d.gui.MessageDialog("No Cam_Rig found. Select any object inside the rig first.")
            return
        doc.StartUndo()
        doc.AddUndo(c4d.UNDOTYPE_CHANGE, rig)
        reset_rig_params(rig, [group_key])
        doc.EndUndo()
        c4d.EventAdd()
        _log_ok("Reset %s: %s" % (group_key, rig.GetName()))

    def _on_reset_all(self):
        if reset_rig_to_defaults is None:
            c4d.gui.MessageDialog("Reset function not loaded.")
            return
        doc = c4d.documents.GetActiveDocument()
        rig = _find_rig(doc)
        if not rig:
            c4d.gui.MessageDialog("No Cam_Rig found. Select any object inside the rig first.")
            return
        doc.StartUndo()
        doc.AddUndo(c4d.UNDOTYPE_CHANGE, rig)
        reset_rig_to_defaults(rig)
        doc.EndUndo()
        c4d.EventAdd()
        _log_ok("Reset All: " + rig.GetName())

    def _on_break_user_data(self):
        if break_rig_user_data is None:
            c4d.gui.MessageDialog("Break User Data function not loaded.")
            return
        doc = c4d.documents.GetActiveDocument()
        if not doc:
            return
        circle = _find_main_camera(doc)
        if not circle:
            c4d.gui.MessageDialog(
                "No Cam Rig found. Select the Cam_Rig or any object inside the rig (e.g. Main_Camera), then click Break User Data."
            )
            return
        ok = c4d.gui.QuestionDialog(
            "Break User Data?\n\n"
            "Animated parameters will be baked onto the rig objects. "
            "The Python Tag will be removed and the rig will no longer be driven by User Data. "
            "Rig objects will be removed from their layer."
        )
        if not ok:
            return
        try:
            doc.StartUndo()
            doc.AddUndo(c4d.UNDOTYPE_CHANGE, circle)
            break_rig_user_data(doc, circle)
            doc.EndUndo()
            _log_ok("Break User Data done: " + circle.GetName())
            c4d.gui.MessageDialog("Break User Data completed.")
        except Exception as e:
            doc.EndUndo()
            _log_err("Break User Data failed: " + str(e))
            traceback.print_exc()
            c4d.gui.MessageDialog("Error: " + str(e))

    def _on_inspect_rig(self):
        doc = c4d.documents.GetActiveDocument()
        try:
            _, report = _inspect_rig(doc)
        except Exception as e:
            traceback.print_exc()
            report = "Rig Inspector failed: " + str(e)
        c4d.gui.MessageDialog(report)

    def _on_repair_rig(self):
        doc = c4d.documents.GetActiveDocument()
        try:
            _, report = _repair_selected_rig(doc)
        except Exception as e:
            traceback.print_exc()
            report = "Repair failed: " + str(e)
        c4d.gui.MessageDialog(report)

    def _on_self_check(self):
        try:
            c4d.gui.MessageDialog("\n".join(_run_self_check()))
        except Exception as e:
            c4d.gui.MessageDialog("Self check failed: " + str(e))


# ------------------------------------------------
# КОМАНДНЫЙ ПЛАГИН
# ------------------------------------------------

class CamRigCommand(plugins.CommandData):

    _dialog = None

    def Init(self, isCloneInit=False):
        return True

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
        _register_camrig_root()
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
