"""
super_rsm/gui/views/constraints_view.py

Step 5: Linear inequality/equality constraints table and bottom action buttons.
"""

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Dict, List

from super_rsm.gui.components.treeview_helper import clear_treeview, create_scrolled_treeview


class ConstraintsView(ttk.LabelFrame):
    """Step 5: Linear constraints management table."""

    def __init__(
        self,
        parent: tk.Misc,
        on_add: Callable[[], None],
        on_edit: Callable[[], None],
        on_delete: Callable[[], None],
        on_clear: Callable[[], None],
    ):
        super().__init__(parent, text="5. Linear Constraints (Optional)", padding=(10, 6))

        c_btn_frame = ttk.Frame(self, style="Card.TFrame")
        c_btn_frame.pack(fill=tk.X, pady=(0, 6))

        ttk.Button(c_btn_frame, text="+ Add Constraint", style="Small.TButton", command=on_add).pack(
            side=tk.LEFT, padx=(0, 5)
        )
        ttk.Button(c_btn_frame, text="Edit Selected", style="Small.TButton", command=on_edit).pack(
            side=tk.LEFT, padx=(0, 5)
        )
        ttk.Button(c_btn_frame, text="Delete Selected", style="Small.TButton", command=on_delete).pack(
            side=tk.LEFT, padx=(0, 5)
        )
        ttk.Button(c_btn_frame, text="Clear All", style="Danger.TButton", command=on_clear).pack(
            side=tk.RIGHT
        )

        columns = [
            ("id", "#", 32, tk.CENTER, False),
            ("expression", "Linear Combination Expression", 250, tk.W, True),
            ("operator", "Operator", 65, tk.CENTER, False),
            ("bound", "Bound", 80, tk.E, False),
        ]
        tree_wrap, self.constraints_tree = create_scrolled_treeview(self, columns=columns, height=3)
        tree_wrap.pack(fill=tk.X, expand=True)
        self.constraints_tree.bind("<Double-1>", lambda e: on_edit())

    def refresh(self, constraints: List[Dict[str, Any]]) -> None:
        clear_treeview(self.constraints_tree)
        for i, c in enumerate(constraints, 1):
            self.constraints_tree.insert(
                "",
                tk.END,
                values=(i, c["expression_str"], c["operator"], f"{c['bound']:g}"),
            )

