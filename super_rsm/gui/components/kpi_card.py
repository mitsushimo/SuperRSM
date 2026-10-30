"""
super_rsm/gui/components/kpi_card.py

Reusable KPI metric summary card widget for SuperRSM GUI.
"""

import tkinter as tk
from typing import Any, Dict, Optional

from super_rsm.gui.styles.palette import PALETTE
from super_rsm.gui.styles.theme import get_ui_fonts


class KPICard(tk.Frame):
    """Metric card displaying a top accent bar, title caption, primary value, and subtitle."""

    def __init__(
        self,
        parent: tk.Misc,
        title: str,
        initial_val: str = "—",
        initial_sub: str = "",
        fonts: Optional[Dict[str, tuple]] = None,
    ):
        super().__init__(
            parent,
            bg=PALETTE["bg_card"],
            highlightbackground=PALETTE["border"],
            highlightthickness=1,
        )
        self.fonts = fonts or get_ui_fonts()

        self.accent_bar = tk.Frame(self, bg=PALETTE["accent"], height=3)
        self.accent_bar.pack(fill=tk.X, side=tk.TOP)

        body = tk.Frame(self, bg=PALETTE["bg_card"], padx=10, pady=6)
        body.pack(fill=tk.BOTH, expand=True)

        self.title_var = tk.StringVar(value=title)
        self.lbl_title = tk.Label(
            body,
            textvariable=self.title_var,
            bg=PALETTE["bg_card"],
            fg=PALETTE["text_muted"],
            font=self.fonts["kpi_label"],
            anchor=tk.W,
        )
        self.lbl_title.pack(fill=tk.X)

        self.val_var = tk.StringVar(value=initial_val)
        self.lbl_val = tk.Label(
            body,
            textvariable=self.val_var,
            bg=PALETTE["bg_card"],
            fg=PALETTE["text_main"],
            font=self.fonts["kpi_value"],
            anchor=tk.W,
        )
        self.lbl_val.pack(fill=tk.X, pady=(1, 1))

        self.sub_var = tk.StringVar(value=initial_sub)
        self.lbl_sub = tk.Label(
            body,
            textvariable=self.sub_var,
            bg=PALETTE["bg_card"],
            fg=PALETTE["text_muted"],
            font=self.fonts["small"],
            anchor=tk.W,
        )
        self.lbl_sub.pack(fill=tk.X)

    def set_value(self, value: str, subtitle: Optional[str] = None, accent_color: Optional[str] = None) -> None:
        """Update primary value, optional subtitle, and optional top bar color."""
        self.val_var.set(value)
        if subtitle is not None:
            self.sub_var.set(subtitle)
        if accent_color is not None:
            self.accent_bar.config(bg=accent_color)

    def set_title(self, title: str) -> None:
        self.title_var.set(title)

    def set_accent(self, color: str) -> None:
        self.accent_bar.config(bg=color)

    def __getitem__(self, key: str) -> Any:
        mapping = {
            "accent": self.accent_bar,
            "title_var": self.title_var,
            "val_var": self.val_var,
            "sub_var": self.sub_var,
            "val_lbl": self.lbl_val,
        }
        return mapping[key]

