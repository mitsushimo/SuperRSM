"""
super_rsm/gui/dialogs/constraint_dialog.py

Modal dialog and expression formatter for creating and editing linear inequality/equality constraints.
"""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable, Dict, List, Optional

from super_rsm.gui.components.scrollable_panel import ScrollablePanel
from super_rsm.gui.styles.palette import PALETTE
from super_rsm.gui.styles.theme import get_ui_fonts


def format_linear_expression(coeffs_dict: Dict[str, float], operator: str, bound: float) -> str:
    """
    Format a linear combination expression string from a dictionary of variable coefficients,
    comparison operator, and RHS bound value.
    """
    terms = []
    for col, coeff in coeffs_dict.items():
        if abs(coeff) < 1e-12:
            continue
        coeff_str = f"{coeff:g}"
        terms.append((col, coeff, coeff_str))

    if not terms:
        return f"(No non-zero terms) {operator} {bound:g}"

    expr_parts = []
    for i, (col, coeff, coeff_str) in enumerate(terms):
        if i == 0:
            if coeff == 1.0:
                expr_parts.append(f"{col}")
            elif coeff == -1.0:
                expr_parts.append(f"-{col}")
            else:
                expr_parts.append(f"{coeff_str}*{col}")
        else:
            if coeff > 0:
                if coeff == 1.0:
                    expr_parts.append(f"+ {col}")
                else:
                    expr_parts.append(f"+ {coeff_str}*{col}")
            else:
                if coeff == -1.0:
                    expr_parts.append(f"- {col}")
                else:
                    abs_str = f"{abs(coeff):g}"
                    expr_parts.append(f"- {abs_str}*{col}")

    return f"{' '.join(expr_parts)} {operator} {bound:g}"


class LinearConstraintDialog(tk.Toplevel):
    """
    Modal dialog allowing the user to specify a linear combination of input variables
    and a constraint condition (<=, >=, == bound).
    """

    def __init__(
        self,
        parent: tk.Misc,
        input_cols: List[str],
        existing_constraint: Optional[Dict[str, Any]] = None,
        on_save_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        super().__init__(parent)
        self.title("Edit Linear Constraint" if existing_constraint else "Add Linear Constraint")
        self.geometry("560x540")
        self.minsize(480, 440)
        self.configure(bg=PALETTE["bg_main"])
        self.transient(parent)
        self.grab_set()

        self.fonts = get_ui_fonts()
        self.input_cols = input_cols
        self.existing_constraint = existing_constraint
        self.on_save_callback = on_save_callback

        self.coeff_vars: Dict[str, tk.StringVar] = {}
        self.operator_var = tk.StringVar(
            value=existing_constraint.get("operator", "<=") if existing_constraint else "<="
        )
        self.bound_var = tk.StringVar(
            value=f"{existing_constraint.get('bound', 0.0):g}" if existing_constraint else ""
        )
        self.preview_var = tk.StringVar(value="")

        self.create_widgets()
        self.update_preview()

    def create_widgets(self) -> None:
        container = ttk.Frame(self, padding="12")
        container.pack(fill=tk.BOTH, expand=True)

        btn_frame = ttk.Frame(container)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(8, 0))

        save_btn = ttk.Button(
            btn_frame, text="Save Constraint", style="Primary.TButton", command=self.on_save
        )
        save_btn.pack(side=tk.RIGHT, padx=(6, 0))

        cancel_btn = ttk.Button(btn_frame, text="Cancel", command=self.destroy)
        cancel_btn.pack(side=tk.RIGHT)

        preview_lf = ttk.LabelFrame(container, text="Live Expression Preview", padding="8")
        preview_lf.pack(side=tk.BOTTOM, fill=tk.X, pady=(0, 6))

        preview_lbl = ttk.Label(
            preview_lf,
            textvariable=self.preview_var,
            foreground=PALETTE["accent"],
            background=PALETTE["bg_card"],
            wraplength=510,
            font=self.fonts["mono_bold"],
        )
        preview_lbl.pack(anchor=tk.W)

        cond_lf = ttk.LabelFrame(container, text="Constraint Condition", padding="8")
        cond_lf.pack(side=tk.BOTTOM, fill=tk.X, pady=(0, 6))

        ttk.Label(cond_lf, text="Relation:", style="Card.TLabel").pack(side=tk.LEFT, padx=(0, 6))
        op_combo = ttk.Combobox(
            cond_lf,
            textvariable=self.operator_var,
            values=["<=", ">=", "=="],
            state="readonly",
            width=6,
        )
        op_combo.pack(side=tk.LEFT, padx=(0, 18))
        op_combo.bind("<<ComboboxSelected>>", lambda e: self.update_preview())

        ttk.Label(cond_lf, text="Bound Value (RHS):", style="Card.TLabel").pack(side=tk.LEFT, padx=(0, 6))
        bound_entry = ttk.Entry(cond_lf, textvariable=self.bound_var, width=16)
        bound_entry.pack(side=tk.LEFT)
        self.bound_var.trace_add("write", lambda *args: self.update_preview())

        info_lbl = ttk.Label(
            container,
            text="Define a linear combination of input variables (∑ cᵢ · xᵢ) and set its boundary condition:",
            wraplength=520,
        )
        info_lbl.pack(side=tk.TOP, anchor=tk.W, pady=(0, 6))

        coeff_lf = ttk.LabelFrame(container, text="Variable Coefficients (cᵢ)", padding="8")
        coeff_lf.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(0, 6))

        panel = ScrollablePanel(coeff_lf, height=130)
        panel.pack(fill=tk.BOTH, expand=True)
        scrollable_frame = panel.inner_frame

        ttk.Label(scrollable_frame, text="Variable", style="CardBold.TLabel").grid(
            row=0, column=0, padx=10, pady=(2, 6), sticky=tk.W
        )
        ttk.Label(scrollable_frame, text="Coefficient (cᵢ)", style="CardBold.TLabel").grid(
            row=0, column=1, padx=10, pady=(2, 6), sticky=tk.W
        )

        existing_coeffs = self.existing_constraint.get("coeffs", {}) if self.existing_constraint else {}

        for i, col in enumerate(self.input_cols):
            lbl = ttk.Label(scrollable_frame, text=col, style="Card.TLabel")
            lbl.grid(row=i + 1, column=0, padx=10, pady=4, sticky=tk.W)
            panel.bind_mousewheel(lbl)

            val = existing_coeffs.get(col, 0.0)
            val_str = f"{val:g}" if self.existing_constraint else ("1" if i == 0 else "0")
            var = tk.StringVar(value=val_str)
            var.trace_add("write", lambda *args: self.update_preview())
            self.coeff_vars[col] = var

            entry = ttk.Entry(scrollable_frame, textvariable=var, width=18)
            entry.grid(row=i + 1, column=1, padx=10, pady=4, sticky=tk.W)
            panel.bind_mousewheel(entry)

    def update_preview(self) -> None:
        coeffs: Dict[str, float] = {}
        for col, var in self.coeff_vars.items():
            text = var.get().strip()
            try:
                coeffs[col] = float(text) if text else 0.0
            except ValueError:
                coeffs[col] = 0.0

        op = self.operator_var.get()
        bound_text = self.bound_var.get().strip()
        try:
            bound_val = float(bound_text) if bound_text else 0.0
            bound_str = f"{bound_val:g}"
        except ValueError:
            bound_str = bound_text if bound_text else "?"

        non_zeros = {k: v for k, v in coeffs.items() if abs(v) > 1e-12}
        if not non_zeros:
            self.preview_var.set("(All coefficients are 0 - enter at least one non-zero coefficient)")
        else:
            try:
                b_val = float(bound_str)
                self.preview_var.set(format_linear_expression(coeffs, op, b_val))
            except ValueError:
                parts = [f"{v:g}*{k}" for k, v in non_zeros.items()]
                self.preview_var.set(f"{' + '.join(parts)} {op} {bound_str}")

    def on_save(self) -> None:
        coeffs: Dict[str, float] = {}
        for col, var in self.coeff_vars.items():
            text = var.get().strip()
            if not text:
                coeffs[col] = 0.0
                continue
            try:
                coeffs[col] = float(text)
            except ValueError:
                messagebox.showerror("Error", f"Invalid coefficient for '{col}'. Please enter a valid number.", parent=self)
                return

        if not any(abs(v) > 1e-12 for v in coeffs.values()):
            messagebox.showerror("Error", "At least one variable coefficient must be non-zero.", parent=self)
            return

        bound_text = self.bound_var.get().strip()
        if not bound_text:
            messagebox.showerror("Error", "Please enter a numeric bound value.", parent=self)
            return

        try:
            bound_val = float(bound_text)
        except ValueError:
            messagebox.showerror("Error", "Invalid bound value. Please enter a valid number.", parent=self)
            return

        op = self.operator_var.get()
        expr_str = format_linear_expression(coeffs, op, bound_val)

        constraint_data = {
            "coeffs": coeffs,
            "operator": op,
            "bound": bound_val,
            "expression_str": expr_str,
        }

        if self.on_save_callback:
            self.on_save_callback(constraint_data)

        self.destroy()

