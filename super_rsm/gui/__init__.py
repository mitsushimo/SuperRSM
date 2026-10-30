"""
super_rsm/gui/__init__.py

Model-View-Presenter (MVP) Desktop GUI package for SuperRSM.
"""

from super_rsm.gui.app import RSMApp, RSMGui, main
from super_rsm.gui.controller import AppController
from super_rsm.gui.state import AppState

__all__ = [
    "RSMApp",
    "RSMGui",
    "AppController",
    "AppState",
    "main",
]

