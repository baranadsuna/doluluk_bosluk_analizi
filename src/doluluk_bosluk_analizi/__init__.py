#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Figure-Ground & Solid-Void Analyzer Plugin Initializer
"""


def classFactory(iface):
    """Load FigureGroundPlugin class from file figure_ground_plugin."""
    try:
        from .figure_ground_plugin import FigureGroundPlugin
    except ImportError:
        from figure_ground_plugin import FigureGroundPlugin
    return FigureGroundPlugin(iface)
