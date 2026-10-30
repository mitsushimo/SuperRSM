"""
super_rsm/gui/styles/__init__.py

UI styling tokens, color palettes, and TTK theme configuration.
"""

from super_rsm.gui.styles.palette import (
    PALETTE,
    COMMON_CMAPS,
    COMMON_LINESTYLES,
    COMMON_MARKERS,
)
from super_rsm.gui.styles.theme import get_ui_fonts, configure_ttk_styles

__all__ = [
    "PALETTE",
    "COMMON_CMAPS",
    "COMMON_LINESTYLES",
    "COMMON_MARKERS",
    "get_ui_fonts",
    "configure_ttk_styles",
]

