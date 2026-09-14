# -*- coding: utf-8 -*-
"""Chiken_CAM command plugin for Cinema 4D 2026.

Private development plugin ID. Request a PluginCafe ID before distribution.
"""
from pathlib import Path
import runpy
import traceback

import c4d
from c4d import plugins


PLUGIN_ID = 10699111
PLUGIN_NAME = "Chiken_CAM (CK_CAM)"
PLUGIN_HELP = "Create the CK_CAM path camera rig"
VERSION = "0.1.0"


def _builder():
    root = Path(__file__).resolve().parent
    installed = root / "prototypes" / "simple_camera" / "builder.py"
    development = root.parent / "prototypes" / "simple_camera" / "builder.py"
    path = installed if installed.is_file() else development
    if not path.is_file():
        raise RuntimeError("Missing CK_CAM runtime: prototypes/simple_camera/builder.py")
    return runpy.run_path(str(path))


class ChikenCamCommand(plugins.CommandData):
    def Execute(self, document):
        if document is None:
            c4d.gui.MessageDialog("Open the target document before creating CK_CAM.")
            return False
        try:
            root, unused_objects, unused_ids = _builder()["build"](document)
            document.SetActiveObject(root, c4d.SELECTION_NEW)
            c4d.EventAdd()
            c4d.GePrint("[CK_CAM] Created Chiken_CAM v" + VERSION)
            return True
        except Exception as error:
            c4d.GePrint("[CK_CAM] ERROR: " + str(error))
            traceback.print_exc()
            c4d.gui.MessageDialog("CK_CAM could not create the rig:\n" + str(error))
            return False


def PluginStart():
    try:
        registered = plugins.RegisterCommandPlugin(
            id=PLUGIN_ID,
            str=PLUGIN_NAME,
            info=0,
            icon=None,
            help=PLUGIN_HELP,
            dat=ChikenCamCommand(),
        )
        if registered:
            c4d.GePrint("[CK_CAM] Chiken_CAM v" + VERSION + " loaded")
        else:
            c4d.GePrint("[CK_CAM] ERROR: command registration failed")
        return registered
    except Exception as error:
        c4d.GePrint("[CK_CAM] ERROR: PluginStart failed: " + str(error))
        traceback.print_exc()
        return False


if __name__ == "__main__":
    PluginStart()
