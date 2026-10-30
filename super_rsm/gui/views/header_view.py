"""
super_rsm/gui/views/header_view.py

Top application banner view displaying branding and dataset status pill.
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Optional

from super_rsm.gui.styles.theme import get_ui_fonts


class HeaderView(ttk.Frame):
    """Top header bar displaying SuperRSM title and active dataset badge."""

    def __init__(self, parent: tk.Misc, fonts: Optional[Dict[str, tuple]] = None):
        super().__init__(parent, style="Header.TFrame", padding=(16, 10))
        self.fonts = fonts or get_ui_fonts()

        title_box = ttk.Frame(self, style="Header.TFrame")
        title_box.pack(side=tk.LEFT)

        ttk.Label(title_box, text="Super RSM", style="HeaderTitle.TLabel").pack(side=tk.LEFT)
        ttk.Label(
            title_box,
            text="  |  Multi-Method Response Surface Modeling & Constrained Optimization",
            style="HeaderSub.TLabel",
        ).pack(side=tk.LEFT, pady=(2, 0))

        self.dataset_badge_var = tk.StringVar(value="No dataset loaded")
        self.dataset_badge_lbl = tk.Label(
            self,
            textvariable=self.dataset_badge_var,
            bg="#1E293B",
            fg="#94A3B8",
            font=self.fonts["small_bold"],
            padx=10,
            pady=3,
        )
        self.dataset_badge_lbl.pack(side=tk.RIGHT)

    def set_dataset_status(self, filename: str, num_rows: int, num_cols: int) -> None:
        """Update dataset badge pill when a dataset is loaded."""
        self.dataset_badge_var.set(f"{filename}  •  {num_rows} rows × {num_cols} cols")
        self.dataset_badge_lbl.config(bg="#1E3A8A", fg="#DBEAFE")

