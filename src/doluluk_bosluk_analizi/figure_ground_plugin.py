#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Figure-Ground & Solid-Void Analyzer Plugin Entry Point
======================================================
"""

import os
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

try:
    from .figure_ground_dialog import FigureGroundDialog
except ImportError:
    from figure_ground_dialog import FigureGroundDialog


class FigureGroundPlugin:
    """QGIS Plugin for Urban Figure-Ground and Solid-Void Ratio Analysis."""

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.action = None
        self.menu = "&Figure-Ground Analyzer"
        self.dlg = None

    def tr(self, message: str) -> str:
        return QCoreApplication.translate("FigureGroundPlugin", message)

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, "icon.svg")
        icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()

        self.action = QAction(
            icon,
            self.tr("Figure-Ground & Solid-Void Analyzer (EPSG:5253)"),
            self.iface.mainWindow(),
        )
        self.action.setStatusTip(
            self.tr("Calculate building footprint coverage and solid-void ratios in EPSG:5253")
        )
        self.action.triggered.connect(self.run)

        # Add to Vector menu and Plugins toolbar
        self.iface.addVectorToolBarIcon(self.action)
        self.iface.addPluginToVectorMenu(self.tr("Urban Density & Analysis"), self.action)

    def unload(self):
        if self.action:
            self.iface.removePluginVectorMenu(self.tr("Urban Density & Analysis"), self.action)
            self.iface.removeVectorToolBarIcon(self.action)
            del self.action
            self.action = None

    def run(self):
        # Default to Turkish if user environment or QGIS locale is Turkish, else English
        locale = QCoreApplication.instance().property("locale") or ""
        lang = "tr" if "tr" in str(locale).lower() else "tr"  # Default TR for local workstation
        self.dlg = FigureGroundDialog(self.iface.mainWindow(), self.iface, language=lang)
        self.dlg.exec()
