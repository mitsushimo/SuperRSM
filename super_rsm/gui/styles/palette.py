"""
super_rsm/gui/styles/palette.py

Color palette tokens and plotting style option constants for SuperRSM GUI.
"""

from typing import Dict, List

PALETTE: Dict[str, str] = {
    "bg_main": "#F1F5F9",        # Slate 100 - main window background
    "bg_card": "#FFFFFF",        # Pure white - card / panel surface
    "bg_subtle": "#F8FAFC",      # Slate 50 - subtle secondary surface
    "bg_header": "#0F172A",      # Slate 900 - top header bar
    "text_main": "#0F172A",      # Slate 900 - primary text
    "text_secondary": "#334155", # Slate 700 - secondary text
    "text_muted": "#64748B",     # Slate 500 - muted captions / hints
    "accent": "#2563EB",         # Blue 600 - primary brand / action
    "accent_hover": "#1D4ED8",   # Blue 700 - hover state
    "accent_light": "#DBEAFE",   # Blue 100 - soft selection highlight
    "border": "#CBD5E1",         # Slate 300 - widget & card borders
    "border_light": "#E2E8F0",   # Slate 200 - subtle dividers
    "success": "#16A34A",        # Green 600 - converged / satisfied
    "success_bg": "#DCFCE7",     # Green 100
    "warning": "#D97706",        # Amber 600 - warning state
    "warning_bg": "#FEF3C7",     # Amber 100
    "danger": "#DC2626",         # Red 600 - destructive / violated
    "danger_hover": "#B91C1C",   # Red 700
}

COMMON_CMAPS: List[str] = [
    "plasma",
    "viridis",
    "inferno",
    "magma",
    "cividis",
    "coolwarm",
    "YlGnBu",
    "Spectral",
    "RdYlBu_r",
    "turbo",
]

COMMON_LINESTYLES: List[str] = ["--", "-", ":", "-."]
COMMON_MARKERS: List[str] = ["o", "s", "^", "v", "D", "P", "*", "X", "x", "+"]

