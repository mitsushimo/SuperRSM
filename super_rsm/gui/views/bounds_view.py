"""
super_rsm/gui/views/bounds_view.py

Step 4: Optimization goal and scrollable parameter bounds view.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, List, Optional, Tuple

from super_rsm.gui.components.scrollable_panel import ScrollablePanel


class BoundsView(ttk.LabelFrame):
    """Step 4: Optimization goal (Minimize/Maximize) and per-factor min/max bounds."""

    def __init__(
        self,
        parent: tk.Misc,
        on_goal_change: Callable[[], None],
        on_fill_from_data: Callable[[], None],
        on_clear_bounds: Callable[[], None],
    ):
        super().__init__(parent, text="4. Optimization Goal & Bounds (Optional)", padding=(10, 6))
        self.bound_entries: Dict[str, Tuple[tk.StringVar, tk.StringVar]] = {}

        toolbar = ttk.Frame(self, style="Card.TFrame")
        toolbar.pack(fill=tk.X, pady=(0, 4))

        ttk.Label(toolbar, text="Optimization Goal:", style="CardBold.TLabel").pack(
            side=tk.LEFT, padx=(0, 6)
        )
        self.opt_goal_var = tk.StringVar(value="Minimize")
        self.opt_goal_combo = ttk.Combobox(
            toolbar,
            textvariable=self.opt_goal_var,
            values=["Minimize", "Maximize"],
            state="readonly",
            width=10,
        )
        self.opt_goal_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.opt_goal_combo.bind("<<ComboboxSelected>>", lambda e: on_goal_change())

        ttk.Button(toolbar, text="Clear", style="Small.TButton", command=on_clear_bounds).pack(
            side=tk.RIGHT, padx=(4, 0)
        )
        ttk.Button(
            toolbar,
            text="Fill from Data Range",
            style="Small.TButton",
            command=on_fill_from_data,
        ).pack(side=tk.RIGHT)

        self.panel = ScrollablePanel(self, height=85)
        self.panel.pack(fill=tk.BOTH, expand=True)
        self.bounds_inner_frame = self.panel.inner_frame

    def rebuild_for_columns(
        self,
        input_cols: List[str],
        get_col_range_str: Callable[[str], str],
    ) -> None:
        existing_bounds = {
            k: (v[0].get(), v[1].get()) for k, v in self.bound_entries.items()
        }
        self.panel.clear()
        self.bound_entries.clear()

        if not input_cols:
            ttk.Label(
                self.bounds_inner_frame,
                text="Select input factors above to configure optional min/max bounds.",
                style="CardMuted.TLabel",
            ).pack(anchor=tk.W, padx=4, pady=12)
            return

        for col_idx in range(4):
            self.bounds_inner_frame.columnconfigure(col_idx, weight=2)

        headers = ["Parameter", "Data [Min, Max]", "Min Bound", "Max Bound"]
        for c_idx, text in enumerate(headers):
            ttk.Label(self.bounds_inner_frame, text=text, style="CardBold.TLabel").grid(
                row=0, column=c_idx, padx=4, pady=(0, 4), sticky=tk.W
            )

        for i, col_name in enumerate(input_cols):
            range_str = get_col_range_str(col_name)
            ttk.Label(self.bounds_inner_frame, text=col_name, style="Card.TLabel").grid(
                row=i + 1, column=0, padx=4, pady=2, sticky=tk.W
            )
            ttk.Label(self.bounds_inner_frame, text=range_str, style="CardMuted.TLabel").grid(
                row=i + 1, column=1, padx=4, pady=2, sticky=tk.W
            )

            prev_min, prev_max = existing_bounds.get(col_name, ("", ""))
            min_var = tk.StringVar(value=prev_min)
            max_var = tk.StringVar(value=prev_max)

            ttk.Entry(self.bounds_inner_frame, textvariable=min_var, width=11).grid(
                row=i + 1, column=2, padx=4, pady=2, sticky=tk.EW
            )
            ttk.Entry(self.bounds_inner_frame, textvariable=max_var, width=11).grid(
                row=i + 1, column=3, padx=4, pady=2, sticky=tk.EW
            )
            self.bound_entries[col_name] = (min_var, max_var)

