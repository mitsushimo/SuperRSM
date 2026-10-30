"""
super_rsm/gui/views/kpi_strip_view.py

Summary strip of 4 KPI metric cards at the top of the right results pane.
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Optional

from super_rsm.gui.components.kpi_card import KPICard
from super_rsm.gui.styles.palette import PALETTE
from super_rsm.gui.styles.theme import get_ui_fonts


class KPIStripView(ttk.Frame):
    """Strip containing 4 KPI cards: R², RMSE, Optimal Output, and Status."""

    def __init__(self, parent: tk.Misc, fonts: Optional[Dict[str, tuple]] = None):
        super().__init__(parent)
        self.fonts = fonts or get_ui_fonts()
        for col_idx in range(4):
            self.columnconfigure(col_idx, weight=1, uniform="kpi")

        self.kpi_r2 = KPICard(self, "R² FIT SCORE", "—", "Not fitted yet", fonts=self.fonts)
        self.kpi_r2.grid(row=0, column=0, sticky=tk.NSEW, padx=(0, 6))

        self.kpi_rmse = KPICard(self, "TEST RMSE", "—", "MSE: —", fonts=self.fonts)
        self.kpi_rmse.grid(row=0, column=1, sticky=tk.NSEW, padx=(0, 6))

        self.kpi_opt = KPICard(self, "MIN OUTPUT VALUE", "—", "Target: —", fonts=self.fonts)
        self.kpi_opt.grid(row=0, column=2, sticky=tk.NSEW, padx=(0, 6))

        self.kpi_status = KPICard(self, "MODEL & OPT STATUS", "Idle", "Fit model to begin", fonts=self.fonts)
        self.kpi_status.grid(row=0, column=3, sticky=tk.NSEW, padx=(0, 0))

    def reset_all(self) -> None:
        self.kpi_r2.set_value("—", "Not fitted yet", PALETTE["accent"])
        self.kpi_rmse.set_value("—", "MSE: —")
        self.kpi_opt.set_value("—", "Target: —")
        self.kpi_status.set_value("Idle", "Fit model to begin", PALETTE["accent"])

