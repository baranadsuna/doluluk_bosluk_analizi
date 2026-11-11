#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smoke and UI Lifecycle Tests for Figure-Ground & Solid-Void Analyzer
Validates instantiation, 4-language switching (EN, TR, ZH, ID), and cleanup.
"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qgis.core import QgsApplication
qgs = QgsApplication([], False)
qgs.initQgis()

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from figure_ground_plugin import FigureGroundPlugin
from figure_ground_dialog import FigureGroundDialog


class MockIface:
    def mainWindow(self):
        return None
    def addVectorToolBarIcon(self, a):
        pass
    def addPluginToVectorMenu(self, m, a):
        pass
    def removePluginVectorMenu(self, m, a):
        pass
    def removeVectorToolBarIcon(self, a):
        pass


iface = MockIface()
plugin = FigureGroundPlugin(iface)
plugin.initGui()

dlg = FigureGroundDialog(None, iface, language="tr")
print("TR Title:", dlg.windowTitle())
if "Doluluk Boşluk" not in dlg.windowTitle():
    raise AssertionError("Expected 'Doluluk Boşluk' in TR title")

dlg.lang_combo.setCurrentIndex(1)  # switch to EN
print("EN Title:", dlg.windowTitle())
if "Figure-Ground" not in dlg.windowTitle():
    raise AssertionError("Expected 'Figure-Ground' in EN title")

dlg.set_language("zh")  # switch to ZH
print("ZH Title:", dlg.windowTitle())
if "图底与实虚比" not in dlg.windowTitle():
    raise AssertionError("Expected '图底与实虚比' in ZH title")

dlg.set_language("id")  # switch to ID
print("ID Title:", dlg.windowTitle())
if "Solid-Void" not in dlg.windowTitle():
    raise AssertionError("Expected 'Solid-Void' in ID title")

plugin.unload()
qgs.exitQgis()
print("[OK] FigureGroundPlugin lifecycle and 4-language UI dialog verified successfully!")
