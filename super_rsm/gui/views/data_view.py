"""
super_rsm/gui/views/data_view.py

Views for Step 1 (Dataset Source File Bar) and Step 2 (Variable Selection).
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, List, Optional

from super_rsm.gui.styles.palette import PALETTE
from super_rsm.gui.styles.theme import get_ui_fonts


class FileSourceBar(ttk.LabelFrame):
    """Step 1: Dataset file selection bar."""

    def __init__(
        self,
        parent: tk.Misc,
        on_browse: Callable[[], None],
        on_reload: Callable[[], None],
    ):
        super().__init__(parent, text="1. Dataset Source", padding=(10, 6))
        ttk.Label(self, text="Data File:", style="CardBold.TLabel").pack(side=tk.LEFT, padx=(0, 6))

        self.file_path_var = tk.StringVar()
        self.file_entry = ttk.Entry(self, textvariable=self.file_path_var, state="readonly")
        self.file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        ttk.Button(
            self,
            text="Browse & Load...",
            style="Secondary.TButton",
            command=on_browse,
        ).pack(side=tk.LEFT, padx=(0, 6))

        ttk.Button(self, text="Reload", command=on_reload).pack(side=tk.LEFT)


class DataView(ttk.LabelFrame):
    """Step 2: Input factors multi-select listbox and target output combobox."""

    def __init__(
        self,
        parent: tk.Misc,
        on_input_select: Callable[[], None],
        on_output_select: Callable[[], None],
        on_select_all: Callable[[], None],
        on_clear_selection: Callable[[], None],
        fonts: Optional[Dict[str, tuple]] = None,
    ):
        super().__init__(parent, text="2. Select Variables", padding=(10, 8))
        self.fonts = fonts or get_ui_fonts()
        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=2)
        self.rowconfigure(1, weight=1)

        input_hdr = ttk.Frame(self, style="Card.TFrame")
        input_hdr.grid(row=0, column=0, sticky=tk.EW, padx=(0, 8), pady=(0, 4))
        ttk.Label(input_hdr, text="Input Factors (Multi-select):", style="CardBold.TLabel").pack(side=tk.LEFT)
        ttk.Button(input_hdr, text="Clear", style="Small.TButton", command=on_clear_selection).pack(
            side=tk.RIGHT, padx=(3, 0)
        )
        ttk.Button(input_hdr, text="Select All", style="Small.TButton", command=on_select_all).pack(side=tk.RIGHT)

        lb_container = tk.Frame(self, bg=PALETTE["border"], bd=1, relief=tk.FLAT)
        lb_container.grid(row=1, column=0, sticky=tk.NSEW, padx=(0, 8))
        lb_scroll = ttk.Scrollbar(lb_container, orient=tk.VERTICAL)
        self.input_listbox = tk.Listbox(
            lb_container,
            selectmode=tk.MULTIPLE,
            exportselection=False,
            height=4,
            bg="#FFFFFF",
            fg=PALETTE["text_main"],
            selectbackground=PALETTE["accent_light"],
            selectforeground=PALETTE["accent"],
            highlightthickness=0,
            bd=0,
            font=self.fonts["body"],
            activestyle="none",
            yscrollcommand=lb_scroll.set,
        )
        lb_scroll.config(command=self.input_listbox.yview)
        self.input_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=1, pady=1)
        lb_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.input_listbox.bind("<<ListboxSelect>>", lambda e: on_input_select())

        output_frame = ttk.Frame(self, style="Card.TFrame")
        output_frame.grid(row=0, column=1, rowspan=2, sticky=tk.NSEW)

        ttk.Label(output_frame, text="Target Output Response:", style="CardBold.TLabel").pack(
            anchor=tk.W, pady=(2, 4)
        )
        self.output_combo = ttk.Combobox(output_frame, state="readonly")
        self.output_combo.pack(fill=tk.X, pady=(0, 8))
        self.output_combo.bind("<<ComboboxSelected>>", lambda e: on_output_select())

        self.col_selection_hint_var = tk.StringVar(
            value="Load a dataset to populate columns.\nGoal: Minimize Target Output."
        )
        ttk.Label(
            output_frame,
            textvariable=self.col_selection_hint_var,
            style="CardMuted.TLabel",
            wraplength=190,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, fill=tk.X)

    def get_selected_inputs(self) -> List[str]:
        return [self.input_listbox.get(i) for i in self.input_listbox.curselection()]

    def get_selected_output(self) -> str:
        return self.output_combo.get()

    def set_columns(self, columns: List[str]) -> None:
        self.input_listbox.delete(0, tk.END)
        for col in columns:
            self.input_listbox.insert(tk.END, col)
        self.output_combo["values"] = columns
        self.output_combo.set("")

