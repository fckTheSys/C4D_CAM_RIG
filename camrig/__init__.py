# -*- coding: utf-8 -*-
"""
CamRig — пакет плагина Cam Rig Builder.

Не выполняем «from .config import …» при import camrig: иначе при несовпадении версии
bytecode (.pyc) с Python внутри Cinema 4D пакет падает ещё до явного import camrig.config.
Подмодули подключаются из cam_rig_builder.pyp напрямую (from camrig import config, …).
"""

__all__ = ("config", "rig_builder", "diagnostics", "tag_embedded")
