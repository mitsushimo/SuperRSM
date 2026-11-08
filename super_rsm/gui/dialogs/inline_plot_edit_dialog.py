"""
super_rsm/gui/dialogs/inline_plot_edit_dialog.py

Modal dialog for customizing inline diagnostic plots (Plot Title, X/Y Axis Labels,
Parameter/Term Display Names, and Series Legend Labels).
"""

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Dict, Optional

from super_rsm.gui.components.scrollable_panel import ScrollablePanel
from super_rsm.gui.styles.palette import PALETTE


class InlinePlotEditDialog(tk.Toplevel):
    """Modal configuration dialog for editing inline analysis plot labels and parameter names."""

    def __init__(
        self,
        parent: tk.Misc,
        plot_key: str,
        plot_caption: str,
        defaults: Dict[str, Any],
        current_overrides: Optional[Dict[str, Any]] = None,
        on_apply: Optional[Callable[[Dict[str, Any], bool], None]] = None,
    ):
        super().__init__(parent)
        self.title(f"Edit Inline Plot — {plot_caption}")
        self.geometry("560x520")
        self.minsize(480, 420)
        self.configure(bg=PALETTE["bg_main"])
        self.transient(parent.winfo_toplevel())

        self.plot_key = plot_key
        self.defaults = defaults or {}
        self.current_overrides = current_overrides or {}
        self.on_apply = on_apply

        self.title_var = tk.StringVar()
        self.xlabel_var = tk.StringVar()
        self.ylabel_var = tk.StringVar()
        self.sync_terms_var = tk.BooleanVar(value=True)
        self.term_vars: Dict[str, tk.StringVar] = {}
        self.legend_vars: Dict[str, tk.StringVar] = {}

        self._build_ui()
        self._populate_values(use_overrides=True)

    def _build_ui(self) -> None:
        main_frame = ttk.Frame(self, padding="14")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. Titles & Axis Labels Group
        axes_group = ttk.LabelFrame(main_frame, text="Plot Title & Axis Labels", padding="10")
        axes_group.pack(fill=tk.X, pady=(0, 10))

        for lbl_text, var in [
            ("Plot Title:", self.title_var),
            ("X-Axis Label:", self.xlabel_var),
            ("Y-Axis Label:", self.ylabel_var),
        ]:
            row = ttk.Frame(axes_group, style="Card.TFrame")
            row.pack(fill=tk.X, pady=4)
            ttk.Label(row, text=lbl_text, width=16, style="CardBold.TLabel").pack(side=tk.LEFT)
            entry = ttk.Entry(row, textvariable=var)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            entry.bind("<Return>", lambda e: self.apply_changes())

        # 2. Parameter / Term Names or Legend Series Labels Group
        default_terms: Dict[str, str] = self.defaults.get("term_labels") or {}
        default_legends: Dict[str, str] = self.defaults.get("legend_labels") or {}

        if default_terms:
            terms_group = ttk.LabelFrame(main_frame, text="Parameter / Term Display Names", padding="10")
            terms_group.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

            hdr_row = ttk.Frame(terms_group, style="Card.TFrame")
            hdr_row.pack(fill=tk.X, pady=(0, 4))
            ttk.Label(hdr_row, text="Original Term", width=22, style="CardBold.TLabel").pack(side=tk.LEFT)
            ttk.Label(hdr_row, text="Custom Display Label", style="CardBold.TLabel").pack(side=tk.LEFT)

            panel = ScrollablePanel(terms_group, height=180)
            panel.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

            for orig_term in default_terms:
                r_frame = ttk.Frame(panel.inner_frame, style="Card.TFrame")
                r_frame.pack(fill=tk.X, pady=3)
                ttk.Label(r_frame, text=orig_term, width=22, style="Card.TLabel").pack(side=tk.LEFT)
                t_var = tk.StringVar()
                t_entry = ttk.Entry(r_frame, textvariable=t_var)
                t_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
                t_entry.bind("<Return>", lambda e: self.apply_changes())
                self.term_vars[orig_term] = t_var

            ttk.Checkbutton(
                terms_group,
                text="Apply parameter/term name changes to all diagnostic bar plots",
                variable=self.sync_terms_var,
            ).pack(anchor=tk.W, pady=(4, 0))

        elif default_legends:
            leg_group = ttk.LabelFrame(main_frame, text="Series Legend Labels", padding="10")
            leg_group.pack(fill=tk.X, pady=(0, 10))

            legend_titles = {
                "ideal": "1:1 Reference Line:",
                "train": "Training Partition:",
                "test": "Test Partition:",
            }
            for leg_key in default_legends:
                r_frame = ttk.Frame(leg_group, style="Card.TFrame")
                r_frame.pack(fill=tk.X, pady=4)
                ttk.Label(
                    r_frame,
                    text=legend_titles.get(leg_key, f"{leg_key}:"),
                    width=20,
                    style="CardBold.TLabel",
                ).pack(side=tk.LEFT)
                l_var = tk.StringVar()
                l_entry = ttk.Entry(r_frame, textvariable=l_var)
                l_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
                l_entry.bind("<Return>", lambda e: self.apply_changes())
                self.legend_vars[leg_key] = l_var

        # 3. Action Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(6, 0))
        ttk.Button(
            btn_frame,
            text="Reset to Defaults",
            style="Small.TButton",
            command=self.reset_to_defaults,
        ).pack(side=tk.LEFT)
        ttk.Button(
            btn_frame,
            text="✓  Apply Changes",
            style="Primary.TButton",
            command=self.apply_changes,
        ).pack(side=tk.RIGHT)
        ttk.Button(
            btn_frame,
            text="Cancel",
            command=self.destroy,
        ).pack(side=tk.RIGHT, padx=(0, 8))

    def _populate_values(self, use_overrides: bool = True) -> None:
        ovr = self.current_overrides if use_overrides else {}
        self.title_var.set(ovr.get("title") or self.defaults.get("title", ""))
        self.xlabel_var.set(ovr.get("xlabel") or self.defaults.get("xlabel", ""))
        self.ylabel_var.set(ovr.get("ylabel", self.defaults.get("ylabel", "")))

        default_terms: Dict[str, str] = self.defaults.get("term_labels") or {}
        ovr_terms: Dict[str, str] = (ovr.get("term_labels") or {}) if use_overrides else {}
        for orig_term, var in self.term_vars.items():
            var.set(ovr_terms.get(orig_term) or default_terms.get(orig_term, orig_term))

        default_legends: Dict[str, str] = self.defaults.get("legend_labels") or {}
        ovr_legends: Dict[str, str] = (ovr.get("legend_labels") or {}) if use_overrides else {}
        for leg_key, var in self.legend_vars.items():
            var.set(ovr_legends.get(leg_key) or default_legends.get(leg_key, ""))

    def reset_to_defaults(self) -> None:
        self._populate_values(use_overrides=False)

    def get_overrides_dict(self) -> Dict[str, Any]:
        """Collect current user edits into a clean overrides dictionary."""
        result_ovr: Dict[str, Any] = {
            "title": self.title_var.get().strip(),
            "xlabel": self.xlabel_var.get().strip(),
            "ylabel": self.ylabel_var.get().strip(),
        }
        if self.term_vars:
            result_ovr["term_labels"] = {
                orig: (var.get().strip() or orig)
                for orig, var in self.term_vars.items()
            }
        if self.legend_vars:
            default_legends: Dict[str, str] = self.defaults.get("legend_labels") or {}
            result_ovr["legend_labels"] = {
                k: (var.get().strip() or default_legends.get(k, k))
                for k, var in self.legend_vars.items()
            }
        return result_ovr

    def apply_changes(self) -> None:
        overrides = self.get_overrides_dict()
        sync_terms = bool(self.sync_terms_var.get()) if self.term_vars else False
        if self.on_apply is not None:
            self.on_apply(overrides, sync_terms)
        self.destroy()


def merge_plot_overrides(
    all_overrides: Dict[str, Dict[str, Any]],
    plot_key: str,
    new_overrides: Dict[str, Any],
    sync_terms: bool = True,
) -> Dict[str, Dict[str, Any]]:
    """Update overrides for plot_key and optionally sync term_labels across bar plots."""
    all_overrides[plot_key] = dict(new_overrides)
    if sync_terms and "term_labels" in new_overrides:
        shared_terms = dict(new_overrides["term_labels"])
        for bar_key in ("t_value", "p_value", "importance"):
            if bar_key != plot_key:
                entry = dict(all_overrides.get(bar_key, {}))
                existing_terms = dict(entry.get("term_labels", {}))
                existing_terms.update(shared_terms)
                entry["term_labels"] = existing_terms
                all_overrides[bar_key] = entry
    return all_overrides

