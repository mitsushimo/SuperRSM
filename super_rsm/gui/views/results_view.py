"""
super_rsm/gui/views/results_view.py

3-Tab Results Notebook (Tab 1: Optimal Solution & Constraints, Tab 2: Full Report & Equation,
Tab 3: Evaluate Model at Custom Point & History).
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, List, Optional

from super_rsm.gui.components.scrollable_panel import ScrollablePanel
from super_rsm.gui.components.treeview_helper import create_scrolled_treeview
from super_rsm.gui.styles.palette import PALETTE
from super_rsm.gui.styles.theme import get_ui_fonts


class ResultsView(ttk.Notebook):
    """3-Tab results notebook displaying optimization tables, diagnostic report, and point evaluator."""

    def __init__(
        self,
        parent: tk.Misc,
        on_copy_report: Callable[[], None],
        on_eval_point: Callable[[], None],
        on_fill_eval_optimal: Callable[[], None],
        on_fill_eval_mean: Callable[[], None],
        on_clear_eval: Callable[[], None],
        on_copy_history: Callable[[], None],
        on_clear_history: Callable[[], None],
        on_history_double_click: Callable[[], None],
        fonts: Optional[Dict[str, tuple]] = None,
    ):
        super().__init__(parent)
        self.fonts = fonts or get_ui_fonts()
        self.eval_entries: Dict[str, tk.StringVar] = {}
        self.on_eval_point = on_eval_point

        self._build_tables_tab()
        self._build_report_tab(on_copy_report)
        self._build_eval_tab(
            on_eval_point,
            on_fill_eval_optimal,
            on_fill_eval_mean,
            on_clear_eval,
            on_copy_history,
            on_clear_history,
            on_history_double_click,
        )

    def _build_tables_tab(self) -> None:
        tables_tab = ttk.Frame(self, style="Card.TFrame", padding=10)
        self.add(tables_tab, text="  Optimal Solution & Constraints  ")

        opt_lbl_frame = ttk.Frame(tables_tab, style="Card.TFrame")
        opt_lbl_frame.pack(fill=tk.X, pady=(0, 4))
        self.opt_table_hdr_var = tk.StringVar(
            value="Optimized Input Parameters (Minimizing Target Output)"
        )
        ttk.Label(opt_lbl_frame, textvariable=self.opt_table_hdr_var, style="CardBold.TLabel").pack(
            side=tk.LEFT
        )

        opt_cols = [
            ("param", "Parameter", 130, tk.W, True),
            ("opt_val", "Optimal Value", 120, tk.E, True),
            ("bounds", "Applied Bounds", 130, tk.CENTER, True),
            ("data_range", "Dataset [Min, Max]", 140, tk.CENTER, True),
        ]
        opt_tree_wrap, self.opt_params_tree = create_scrolled_treeview(tables_tab, opt_cols, height=6)
        opt_tree_wrap.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        ver_lbl_frame = ttk.Frame(tables_tab, style="Card.TFrame")
        ver_lbl_frame.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(
            ver_lbl_frame,
            text="Linear Constraint Verification at Optimal Point",
            style="CardBold.TLabel",
        ).pack(side=tk.LEFT)

        ver_cols = [
            ("id", "#", 35, tk.CENTER, False),
            ("expr", "Constraint Expression", 230, tk.W, True),
            ("lhs", "Evaluated LHS", 110, tk.E, True),
            ("status", "Status", 95, tk.CENTER, False),
        ]
        ver_tree_wrap, self.constraint_eval_tree = create_scrolled_treeview(
            tables_tab, ver_cols, height=4
        )
        ver_tree_wrap.pack(fill=tk.BOTH, expand=True)
        self.constraint_eval_tree.tag_configure("satisfied", foreground=PALETTE["success"])
        self.constraint_eval_tree.tag_configure("violated", foreground=PALETTE["danger"])

    def _build_report_tab(self, on_copy_report: Callable[[], None]) -> None:
        report_tab = ttk.Frame(self, style="Card.TFrame", padding=10)
        self.add(report_tab, text="  Model Equation & Full Report  ")

        report_toolbar = ttk.Frame(report_tab, style="Card.TFrame")
        report_toolbar.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(
            report_toolbar,
            text="Detailed Model Summary, Coefficients / Symbolic Expression, ANOVA & Diagnostics",
            style="CardBold.TLabel",
        ).pack(side=tk.LEFT)
        ttk.Button(
            report_toolbar, text="Copy Report", style="Small.TButton", command=on_copy_report
        ).pack(side=tk.RIGHT)

        text_wrap = tk.Frame(report_tab, bg=PALETTE["border"], bd=1, relief=tk.FLAT)
        text_wrap.pack(fill=tk.BOTH, expand=True)
        text_scroll = ttk.Scrollbar(text_wrap, orient=tk.VERTICAL)
        self.results_text = tk.Text(
            text_wrap,
            height=12,
            state="disabled",
            bg=PALETTE["bg_subtle"],
            fg=PALETTE["text_main"],
            font=self.fonts["mono"],
            bd=0,
            padx=10,
            pady=8,
            wrap=tk.WORD,
            yscrollcommand=text_scroll.set,
        )
        text_scroll.config(command=self.results_text.yview)
        self.results_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        text_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _build_eval_tab(
        self,
        on_eval_point: Callable[[], None],
        on_fill_eval_optimal: Callable[[], None],
        on_fill_eval_mean: Callable[[], None],
        on_clear_eval: Callable[[], None],
        on_copy_history: Callable[[], None],
        on_clear_history: Callable[[], None],
        on_history_double_click: Callable[[], None],
    ) -> None:
        eval_tab = ttk.Frame(self, style="Card.TFrame", padding=10)
        self.add(eval_tab, text="  Evaluate Model  ")

        eval_toolbar = ttk.Frame(eval_tab, style="Card.TFrame")
        eval_toolbar.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(eval_toolbar, text="Specify Input Parameter Values:", style="CardBold.TLabel").pack(
            side=tk.LEFT
        )
        ttk.Button(eval_toolbar, text="Clear", style="Small.TButton", command=on_clear_eval).pack(
            side=tk.RIGHT, padx=(4, 0)
        )
        ttk.Button(
            eval_toolbar, text="Fill with Data Mean", style="Small.TButton", command=on_fill_eval_mean
        ).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(
            eval_toolbar,
            text="Fill from Optimal Solution",
            style="Small.TButton",
            command=on_fill_eval_optimal,
        ).pack(side=tk.RIGHT)

        self.eval_panel = ScrollablePanel(eval_tab, height=115)
        self.eval_panel.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        self.eval_inputs_inner_frame = self.eval_panel.inner_frame

        eval_result_bar = tk.Frame(
            eval_tab,
            bg=PALETTE["bg_subtle"],
            highlightbackground=PALETTE["border"],
            highlightthickness=1,
            padx=12,
            pady=8,
        )
        eval_result_bar.pack(fill=tk.X, pady=(0, 8))

        self.eval_run_btn = ttk.Button(
            eval_result_bar,
            text="▶  Evaluate Output",
            style="Primary.TButton",
            command=on_eval_point,
            state="disabled",
        )
        self.eval_run_btn.pack(side=tk.LEFT, padx=(0, 14))

        eval_readout_box = tk.Frame(eval_result_bar, bg=PALETTE["bg_subtle"])
        eval_readout_box.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.eval_pred_var = tk.StringVar(value="Predicted Output:  —")
        tk.Label(
            eval_readout_box,
            textvariable=self.eval_pred_var,
            bg=PALETTE["bg_subtle"],
            fg=PALETTE["accent"],
            font=self.fonts["title"],
            anchor=tk.W,
        ).pack(fill=tk.X)

        self.eval_unc_var = tk.StringVar(
            value="Fit a surrogate model to evaluate predictions at custom parameter combinations."
        )
        tk.Label(
            eval_readout_box,
            textvariable=self.eval_unc_var,
            bg=PALETTE["bg_subtle"],
            fg=PALETTE["text_secondary"],
            font=self.fonts["small"],
            anchor=tk.W,
        ).pack(fill=tk.X)

        hist_hdr_frame = ttk.Frame(eval_tab, style="Card.TFrame")
        hist_hdr_frame.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(
            hist_hdr_frame,
            text="Evaluated Points History (Double-click a row to reload its inputs)",
            style="CardBold.TLabel",
        ).pack(side=tk.LEFT)
        ttk.Button(
            hist_hdr_frame, text="Clear History", style="Danger.TButton", command=on_clear_history
        ).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(
            hist_hdr_frame, text="Copy History", style="Small.TButton", command=on_copy_history
        ).pack(side=tk.RIGHT)

        hist_cols = [
            ("id", "#", 35, tk.CENTER, False),
            ("inputs", "Input Parameter Combination", 260, tk.W, True),
            ("predicted", "Predicted Output", 115, tk.E, True),
            ("uncertainty", "Std Dev (±σ)", 110, tk.E, True),
        ]
        hist_tree_wrap, self.eval_history_tree = create_scrolled_treeview(
            eval_tab, hist_cols, height=4
        )
        hist_tree_wrap.pack(fill=tk.BOTH, expand=True)
        self.eval_history_tree.bind("<Double-1>", lambda e: on_history_double_click())

    def rebuild_eval_inputs(
        self,
        input_cols: List[str],
        get_col_range_str: Callable[[str], str],
        get_col_mean_str: Callable[[str], str],
    ) -> None:
        existing_eval = {k: v.get() for k, v in self.eval_entries.items()}
        self.eval_panel.clear()
        self.eval_entries.clear()

        if not input_cols:
            ttk.Label(
                self.eval_inputs_inner_frame,
                text="Select input factors and fit the model to evaluate outputs at custom points.",
                style="CardMuted.TLabel",
            ).pack(anchor=tk.W, padx=4, pady=12)
            return

        self.eval_inputs_inner_frame.columnconfigure(0, weight=2)
        self.eval_inputs_inner_frame.columnconfigure(1, weight=2)
        self.eval_inputs_inner_frame.columnconfigure(2, weight=3)
        for c_idx, text in enumerate(["Parameter", "Dataset [Min, Max]", "Evaluation Value"]):
            ttk.Label(self.eval_inputs_inner_frame, text=text, style="CardBold.TLabel").grid(
                row=0, column=c_idx, padx=4, pady=(0, 4), sticky=tk.W
            )

        for i, col_name in enumerate(input_cols):
            range_str = get_col_range_str(col_name)
            ttk.Label(self.eval_inputs_inner_frame, text=col_name, style="Card.TLabel").grid(
                row=i + 1, column=0, padx=4, pady=2, sticky=tk.W
            )
            ttk.Label(self.eval_inputs_inner_frame, text=range_str, style="CardMuted.TLabel").grid(
                row=i + 1, column=1, padx=4, pady=2, sticky=tk.W
            )
            default_eval = existing_eval.get(col_name, get_col_mean_str(col_name))
            eval_var = tk.StringVar(value=default_eval)
            eval_entry = ttk.Entry(self.eval_inputs_inner_frame, textvariable=eval_var, width=16)
            eval_entry.grid(row=i + 1, column=2, padx=4, pady=2, sticky=tk.EW)
            eval_entry.bind("<Return>", lambda e: self.on_eval_point())
            self.eval_entries[col_name] = eval_var

    def set_report_text(self, text: str) -> None:
        self.results_text.config(state="normal")
        self.results_text.delete("1.0", tk.END)
        if text:
            self.results_text.insert(tk.END, text)
        self.results_text.config(state="disabled")

