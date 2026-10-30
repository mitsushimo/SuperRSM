"""
super_rsm/gui/components/scrollable_panel.py

Reusable scrollable Canvas + inner Frame container with mousewheel bindings.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional

from super_rsm.gui.styles.palette import PALETTE


class ScrollablePanel(ttk.Frame):
    """Encapsulates a vertically scrollable Tkinter Canvas and inner ttk.Frame."""

    def __init__(
        self,
        parent: tk.Misc,
        height: Optional[int] = None,
        bg: str = PALETTE["bg_card"],
        frame_style: str = "Card.TFrame",
    ):
        super().__init__(parent, style=frame_style)

        canvas_kwargs = {
            "bg": bg,
            "bd": 0,
            "highlightthickness": 0,
        }
        if height is not None:
            canvas_kwargs["height"] = height

        self.canvas = tk.Canvas(self, **canvas_kwargs)
        self.scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        self.inner_frame = ttk.Frame(self.canvas, style=frame_style)

        self.inner_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self._win_id = self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfigure(self._win_id, width=e.width),
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.bind_mousewheel(self.canvas)
        self.bind_mousewheel(self.inner_frame)

    def bind_mousewheel(self, widget: tk.Misc) -> None:
        """Bind cross-platform mousewheel scrolling to a widget."""
        widget.bind("<MouseWheel>", self._on_mousewheel)
        widget.bind("<Button-4>", self._on_mousewheel)
        widget.bind("<Button-5>", self._on_mousewheel)

    def _on_mousewheel(self, event: tk.Event) -> None:
        if getattr(event, "delta", 0):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        elif getattr(event, "num", None) == 4:
            self.canvas.yview_scroll(-1, "units")
        elif getattr(event, "num", None) == 5:
            self.canvas.yview_scroll(1, "units")

    def clear(self) -> None:
        """Destroy all child widgets inside inner_frame."""
        for child in self.inner_frame.winfo_children():
            child.destroy()

