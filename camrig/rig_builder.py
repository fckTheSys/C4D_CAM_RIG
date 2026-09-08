"""
Публичный API CamRig: сборка рига, сброс и Break User Data.
Детали — в camrig.rig_assemble, ud_build, rig_reset, rig_break.
"""
from . import config
from .ud_build import (
    add_bool,
    add_button,
    add_group,
    add_link,
    add_slider,
    validate_ud_template_vs_config,
)
from .rig_assemble import build_cam_rig
from .rig_reset import reset_rig_params, reset_rig_to_defaults
from .rig_break import break_rig_user_data

DEBUG_LOG = config.DEBUG_LOG

__all__ = [
    "DEBUG_LOG",
    "add_bool",
    "add_button",
    "add_group",
    "add_link",
    "add_slider",
    "build_cam_rig",
    "break_rig_user_data",
    "reset_rig_params",
    "reset_rig_to_defaults",
    "validate_ud_template_vs_config",
]
