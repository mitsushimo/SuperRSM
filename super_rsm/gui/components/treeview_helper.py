"""
super_rsm/gui/components/treeview_helper.py

Helper utilities for creating, clearing, and copying TTK Treeview tables.
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Sequence, Tuple


def create_scrolled_treeview(
    parent: tk.Misc,
    columns: Sequence[Tuple[str, str, int, str, bool]],
    height: int = 5,
    selectmode: str = "browse",
) -> Tuple[ttk.Frame, ttk.Treeview]:
    """
    Create a Frame containing a configured ttk.Treeview and vertical Scrollbar.

    Parameters
    ----------
    columns : Sequence of (col_id, heading_text, width, anchor, stretch)
    """
    wrap = ttk.Frame(parent, style="Card.TFrame")
    col_ids = [c[0] for c in columns]

    tree = ttk.Treeview(
        wrap,
        columns=col_ids,
        show="headings",
        height=height,
        selectmode=selectmode,
    )
    for col_id, heading, width, anchor, stretch in columns:
        tree.heading(col_id, text=heading)
        tree.column(col_id, width=width, anchor=anchor, stretch=stretch)

    scroll = ttk.Scrollbar(wrap, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scroll.pack(side=tk.RIGHT, fill=tk.Y)

    return wrap, tree


def clear_treeview(tree: ttk.Treeview) -> None:
    """Remove all rows from a Treeview widget."""
    for item in tree.get_children():
        tree.delete(item)


def treeview_to_tsv(tree: ttk.Treeview, headers: Sequence[str]) -> str:
    """Format all rows of a Treeview as tab-separated values."""
    lines: List[str] = ["\t".join(headers)]
    for item_id in tree.get_children():
        vals = tree.item(item_id, "values")
        lines.append("\t".join(str(v) for v in vals))
    return "\n".join(lines)

