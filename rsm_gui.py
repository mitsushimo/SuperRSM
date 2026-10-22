import importlib.util
import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import numpy as np
import pandas as pd

from scipy.optimize import LinearConstraint
import rsm_backend 


def format_linear_expression(coeffs_dict, operator, bound):
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
    def __init__(self, parent, input_cols, existing_constraint=None, on_save_callback=None):
        super().__init__(parent)
        self.title("Edit Linear Constraint" if existing_constraint else "Add Linear Constraint")
        self.geometry("520x460")
        self.minsize(450, 380)
        self.transient(parent)
        self.grab_set()

        self.input_cols = input_cols
        self.existing_constraint = existing_constraint
        self.on_save_callback = on_save_callback

        self.coeff_vars = {}
        self.operator_var = tk.StringVar(
            value=existing_constraint.get("operator", "<=") if existing_constraint else "<="
        )
        self.bound_var = tk.StringVar(
            value=f"{existing_constraint.get('bound', 0.0):g}" if existing_constraint else ""
        )
        self.preview_var = tk.StringVar(value="")

        self.create_widgets()
        self.update_preview()

    def create_widgets(self):
        container = ttk.Frame(self, padding="12")
        container.pack(fill=tk.BOTH, expand=True)

        info_lbl = ttk.Label(
            container,
            text="Define a linear combination of variables and set its constraint boundary:",
            wraplength=480
        )
        info_lbl.pack(anchor=tk.W, pady=(0, 10))

        # --- Coefficients Frame ---
        coeff_lf = ttk.LabelFrame(container, text="Variable Coefficients (c_i)", padding="8")
        coeff_lf.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        canvas = tk.Canvas(coeff_lf, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(coeff_lf, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        ttk.Label(scrollable_frame, text="Variable", font=("TkDefaultFont", 9, "bold")).grid(
            row=0, column=0, padx=8, pady=3, sticky=tk.W
        )
        ttk.Label(scrollable_frame, text="Coefficient", font=("TkDefaultFont", 9, "bold")).grid(
            row=0, column=1, padx=8, pady=3, sticky=tk.W
        )

        existing_coeffs = self.existing_constraint.get("coeffs", {}) if self.existing_constraint else {}

        for i, col in enumerate(self.input_cols):
            ttk.Label(scrollable_frame, text=col).grid(
                row=i + 1, column=0, padx=8, pady=3, sticky=tk.W
            )
            val = existing_coeffs.get(col, 0.0)
            val_str = f"{val:g}" if self.existing_constraint else ("1" if i == 0 else "0")
            var = tk.StringVar(value=val_str)
            var.trace_add("write", lambda *args: self.update_preview())
            self.coeff_vars[col] = var

            entry = ttk.Entry(scrollable_frame, textvariable=var, width=15)
            entry.grid(row=i + 1, column=1, padx=8, pady=3, sticky=tk.W)

        # --- Operator and Bound Frame ---
        cond_lf = ttk.LabelFrame(container, text="Constraint Condition", padding="8")
        cond_lf.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(cond_lf, text="Relation:").pack(side=tk.LEFT, padx=(0, 5))
        op_combo = ttk.Combobox(
            cond_lf,
            textvariable=self.operator_var,
            values=["<=", ">=", "=="],
            state="readonly",
            width=6
        )
        op_combo.pack(side=tk.LEFT, padx=(0, 15))
        op_combo.bind("<<ComboboxSelected>>", lambda e: self.update_preview())

        ttk.Label(cond_lf, text="Bound Value (RHS):").pack(side=tk.LEFT, padx=(0, 5))
        bound_entry = ttk.Entry(cond_lf, textvariable=self.bound_var, width=15)
        bound_entry.pack(side=tk.LEFT)
        self.bound_var.trace_add("write", lambda *args: self.update_preview())

        # --- Preview Frame ---
        preview_lf = ttk.LabelFrame(container, text="Live Expression Preview", padding="8")
        preview_lf.pack(fill=tk.X, pady=(0, 10))

        preview_lbl = ttk.Label(
            preview_lf,
            textvariable=self.preview_var,
            foreground="darkblue",
            wraplength=480,
            font=("TkDefaultFont", 9, "italic")
        )
        preview_lbl.pack(anchor=tk.W)

        # --- Buttons ---
        btn_frame = ttk.Frame(container)
        btn_frame.pack(fill=tk.X)

        save_btn = ttk.Button(btn_frame, text="Save Constraint", command=self.on_save)
        save_btn.pack(side=tk.RIGHT, padx=(5, 0))

        cancel_btn = ttk.Button(btn_frame, text="Cancel", command=self.destroy)
        cancel_btn.pack(side=tk.RIGHT)

    def update_preview(self):
        coeffs = {}
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
                parts = []
                for k, v in non_zeros.items():
                    parts.append(f"{v:g}*{k}")
                self.preview_var.set(f"{' + '.join(parts)} {op} {bound_str}")

    def on_save(self):
        coeffs = {}
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
            "expression_str": expr_str
        }

        if self.on_save_callback:
            self.on_save_callback(constraint_data)

        self.destroy()


class RSMGui(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("RSM Optimization GUI")
        self.geometry("850x780")
        self.minsize(750, 650)

        self.df = None
        self.bound_entries = {}
        self.linear_constraints = []
        self.previous_input_cols = []
        self.result = None
        self.current_input_cols = None

        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- File Selection ---
        file_frame = ttk.LabelFrame(main_frame, text="1. Load Data", padding="5")
        file_frame.pack(fill=tk.X, pady=5)

        self.file_path_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.file_path_var, state="readonly").pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=5
        )
        ttk.Button(file_frame, text="Browse", command=self.browse_file).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(file_frame, text="Load", command=self.load_data).pack(
            side=tk.LEFT, padx=5
        )

        # --- Column Selection ---
        col_frame = ttk.LabelFrame(main_frame, text="2. Select Columns", padding="5")
        col_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Inputs (Listbox for multiple selection)
        input_frame = ttk.Frame(col_frame)
        input_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        ttk.Label(input_frame, text="Input Columns (Select multiple):").pack(
            anchor=tk.W
        )
        self.input_listbox = tk.Listbox(
            input_frame, selectmode=tk.MULTIPLE, exportselection=False
        )
        self.input_listbox.pack(fill=tk.BOTH, expand=True)
        self.input_listbox.bind("<<ListboxSelect>>", self.on_input_select)

        # Output (Combobox for single selection)
        output_frame = ttk.Frame(col_frame)
        output_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        ttk.Label(output_frame, text="Output Column:").pack(anchor=tk.W)
        self.output_combo = ttk.Combobox(output_frame, state="readonly")
        self.output_combo.pack(fill=tk.X)

        # --- Bounds Specification ---
        self.bounds_frame = ttk.LabelFrame(
            main_frame, text="3. Optimization Bounds (Optional)", padding="5"
        )
        self.bounds_frame.pack(fill=tk.X, pady=5)

        self.bounds_inner_frame = ttk.Frame(self.bounds_frame)
        self.bounds_inner_frame.pack(fill=tk.X)

        # --- Linear Constraints ---
        self.constraints_frame = ttk.LabelFrame(
            main_frame, text="4. Linear Constraints (Optional)", padding="5"
        )
        self.constraints_frame.pack(fill=tk.X, pady=5)

        c_btn_frame = ttk.Frame(self.constraints_frame)
        c_btn_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Button(
            c_btn_frame, text="Add a constraint", command=self.add_linear_constraint
        ).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(
            c_btn_frame, text="Edit Selected", command=self.edit_linear_constraint
        ).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(
            c_btn_frame, text="Delete Selected", command=self.delete_linear_constraint
        ).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(
            c_btn_frame, text="Clear All", command=self.clear_linear_constraints
        ).pack(side=tk.LEFT)

        tree_frame = ttk.Frame(self.constraints_frame)
        tree_frame.pack(fill=tk.X, expand=True)

        self.constraints_tree = ttk.Treeview(
            tree_frame,
            columns=("id", "expression", "operator", "bound"),
            show="headings",
            height=3,
            selectmode="browse"
        )
        self.constraints_tree.heading("id", text="#")
        self.constraints_tree.heading("expression", text="Linear Combination Expression")
        self.constraints_tree.heading("operator", text="Operator")
        self.constraints_tree.heading("bound", text="Bound")

        self.constraints_tree.column("id", width=35, anchor=tk.CENTER, stretch=False)
        self.constraints_tree.column("expression", width=420, anchor=tk.W)
        self.constraints_tree.column("operator", width=80, anchor=tk.CENTER, stretch=False)
        self.constraints_tree.column("bound", width=100, anchor=tk.E, stretch=False)

        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.constraints_tree.yview)
        self.constraints_tree.configure(yscrollcommand=tree_scroll.set)
        self.constraints_tree.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.constraints_tree.bind("<Double-1>", lambda event: self.edit_linear_constraint())

        # --- Model Settings ---
        self.settings_frame = ttk.LabelFrame(
            main_frame, text="5. Model Settings", padding="5"
        )
        self.settings_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(self.settings_frame, text="Method:").pack(side=tk.LEFT, padx=(0, 5))
        self.method_var = tk.StringVar(value="Gaussian Process")
        self.method_combo = ttk.Combobox(
            self.settings_frame,
            textvariable=self.method_var,
            values=rsm_backend.get_supported_methods(),
            state="readonly",
            width=18
        )
        self.method_combo.pack(side=tk.LEFT, padx=(0, 15))

        ttk.Label(self.settings_frame, text="Polynomial Degree:").pack(side=tk.LEFT, padx=(0, 5))
        self.degree_var = tk.IntVar(value=2)
        self.degree_spin = ttk.Spinbox(self.settings_frame, from_=0, to=10, textvariable=self.degree_var, width=5)
        self.degree_spin.pack(side=tk.LEFT)

        ttk.Label(self.settings_frame, text="Test Data Ratio:").pack(side=tk.LEFT, padx=(15, 5))
        self.test_size_var = tk.DoubleVar(value=0.20)
        self.test_size_spin = ttk.Spinbox(self.settings_frame, from_=0.01, to=0.99, increment=0.01, textvariable=self.test_size_var, width=5)
        self.test_size_spin.pack(side=tk.LEFT)

        # --- Run and Results ---
        run_frame = ttk.Frame(main_frame, padding="5")
        run_frame.pack(fill=tk.X, pady=5)

        ttk.Button(
            run_frame, text="Run RSM Optimization", command=self.run_optimization
        ).pack(fill=tk.X)
        
        self.plot_config_btn = ttk.Button(
            run_frame, text="Configure Plot", command=self.open_plot_config, state="disabled"
        )
        self.plot_config_btn.pack(fill=tk.X, pady=(5, 0))

        results_frame = ttk.LabelFrame(main_frame, text="Results", padding="5")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.results_text = tk.Text(results_frame, height=10, state="disabled")
        self.results_text.pack(fill=tk.BOTH, expand=True)

    def add_linear_constraint(self):
        selected_indices = self.input_listbox.curselection()
        input_cols = [self.input_listbox.get(i) for i in selected_indices]
        if not input_cols:
            messagebox.showwarning("Warning", "Please select input columns first before adding constraints.")
            return

        def save_callback(cdata):
            self.linear_constraints.append(cdata)
            self.refresh_constraints_tree()

        LinearConstraintDialog(self, input_cols, on_save_callback=save_callback)

    def edit_linear_constraint(self):
        selected_item = self.constraints_tree.selection()
        if not selected_item:
            messagebox.showinfo("Info", "Please select a constraint from the list to edit.")
            return

        item_id = selected_item[0]
        idx = int(self.constraints_tree.item(item_id, "values")[0]) - 1
        if 0 <= idx < len(self.linear_constraints):
            selected_indices = self.input_listbox.curselection()
            input_cols = [self.input_listbox.get(i) for i in selected_indices]

            def save_callback(cdata):
                self.linear_constraints[idx] = cdata
                self.refresh_constraints_tree()

            LinearConstraintDialog(
                self,
                input_cols,
                existing_constraint=self.linear_constraints[idx],
                on_save_callback=save_callback
            )

    def delete_linear_constraint(self):
        selected_item = self.constraints_tree.selection()
        if not selected_item:
            messagebox.showinfo("Info", "Please select a constraint from the list to delete.")
            return

        item_id = selected_item[0]
        idx = int(self.constraints_tree.item(item_id, "values")[0]) - 1
        if 0 <= idx < len(self.linear_constraints):
            del self.linear_constraints[idx]
            self.refresh_constraints_tree()

    def clear_linear_constraints(self):
        if not self.linear_constraints:
            return
        if messagebox.askyesno("Confirm", "Are you sure you want to remove all linear constraints?"):
            self.linear_constraints.clear()
            self.refresh_constraints_tree()

    def refresh_constraints_tree(self):
        for item in self.constraints_tree.get_children():
            self.constraints_tree.delete(item)

        for i, c in enumerate(self.linear_constraints, 1):
            self.constraints_tree.insert(
                "",
                tk.END,
                values=(i, c["expression_str"], c["operator"], f"{c['bound']:g}")
            )

    def browse_file(self):
        filepath = filedialog.askopenfilename(
            filetypes=[
                ("CSV Files", "*.csv"),
                ("Excel Files", "*.xlsx *.xls"),
                ("All Files", "*.*"),
            ]
        )
        if filepath:
            self.file_path_var.set(filepath)

    def load_data(self):
        filepath = self.file_path_var.get()
        if not filepath:
            messagebox.showwarning("Warning", "Please select a file first.")
            return

        try:
            if filepath.endswith(".csv"):
                self.df = pd.read_csv(filepath)
            else:
                self.df = pd.read_excel(filepath)

            columns = list(self.df.columns)

            # Update Listbox and Combobox
            self.input_listbox.delete(0, tk.END)
            for col in columns:
                self.input_listbox.insert(tk.END, col)

            self.output_combo["values"] = columns
            self.output_combo.set("")

            # Clear bounds and linear constraints
            self.linear_constraints.clear()
            self.refresh_constraints_tree()
            self.on_input_select()

            messagebox.showinfo(
                "Success",
                f"Loaded data with {len(self.df)} rows and {len(columns)} columns.",
            )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load data: {e!s}")

    def on_input_select(self, event=None):
        selected_indices = self.input_listbox.curselection()
        current_cols = [self.input_listbox.get(idx) for idx in selected_indices]

        # Reset constraints if the selected input columns have changed
        if self.linear_constraints and set(current_cols) != set(getattr(self, "previous_input_cols", [])):
            self.linear_constraints.clear()
            self.refresh_constraints_tree()
        self.previous_input_cols = current_cols

        # Clear existing bounds
        for widget in self.bounds_inner_frame.winfo_children():
            widget.destroy()
        self.bound_entries = {}

        if not selected_indices:
            ttk.Label(
                self.bounds_inner_frame, text="Select input columns to set bounds."
            ).pack()
            return

        # Headers
        ttk.Label(self.bounds_inner_frame, text="Parameter").grid(
            row=0, column=0, padx=5, pady=2, sticky=tk.W
        )
        ttk.Label(self.bounds_inner_frame, text="Min Bound").grid(
            row=0, column=1, padx=5, pady=2
        )
        ttk.Label(self.bounds_inner_frame, text="Max Bound").grid(
            row=0, column=2, padx=5, pady=2
        )

        for i, idx in enumerate(selected_indices):
            col_name = self.input_listbox.get(idx)
            ttk.Label(self.bounds_inner_frame, text=col_name).grid(
                row=i + 1, column=0, padx=5, pady=2, sticky=tk.W
            )

            min_var = tk.StringVar()
            max_var = tk.StringVar()

            ttk.Entry(self.bounds_inner_frame, textvariable=min_var, width=15).grid(
                row=i + 1, column=1, padx=5, pady=2
            )
            ttk.Entry(self.bounds_inner_frame, textvariable=max_var, width=15).grid(
                row=i + 1, column=2, padx=5, pady=2
            )

            self.bound_entries[col_name] = (min_var, max_var)

    def run_optimization(self):
        if self.df is None:
            messagebox.showwarning("Warning", "Please load data first.")
            return

        selected_indices = self.input_listbox.curselection()
        input_cols = [self.input_listbox.get(i) for i in selected_indices]
        output_col = self.output_combo.get()

        if not input_cols:
            messagebox.showwarning(
                "Warning", "Please select at least one input column."
            )
            return
        if not output_col:
            messagebox.showwarning("Warning", "Please select an output column.")
            return

        if output_col in input_cols:
            messagebox.showwarning(
                "Warning", "Output column cannot be in the input columns."
            )
            return

        bounds = []
        for col in input_cols:
            min_str, max_str = self.bound_entries[col]

            min_val = None
            if min_str.get().strip():
                try:
                    min_val = float(min_str.get().strip())
                except ValueError:
                    messagebox.showerror("Error", f"Invalid minimum bound for {col}")
                    return

            max_val = None
            if max_str.get().strip():
                try:
                    max_val = float(max_str.get().strip())
                except ValueError:
                    messagebox.showerror("Error", f"Invalid maximum bound for {col}")
                    return

            bounds.append((min_val, max_val))

        # Check if all bounds are (None, None), scipy minimize sometimes prefers None instead of list of (None, None)
        if all(b == (None, None) for b in bounds):
            bounds = None

        # Build scipy.optimize.LinearConstraint if constraints are defined
        scipy_constraints = None
        if self.linear_constraints:
            A_matrix = []
            lb_vec = []
            ub_vec = []
            for c in self.linear_constraints:
                row = [c["coeffs"].get(col, 0.0) for col in input_cols]
                A_matrix.append(row)
                op = c["operator"]
                b = c["bound"]
                if op == "<=":
                    lb_vec.append(-np.inf)
                    ub_vec.append(b)
                elif op == ">=":
                    lb_vec.append(b)
                    ub_vec.append(np.inf)
                elif op == "==":
                    lb_vec.append(b)
                    ub_vec.append(b)
            scipy_constraints = LinearConstraint(np.array(A_matrix), np.array(lb_vec), np.array(ub_vec))

        try:
            # 1. Fit the model using backend
            degree = self.degree_var.get()
            test_size = self.test_size_var.get()
            method = self.method_var.get()

            if method == "RidgeCV" and degree < 1:
                messagebox.showerror("Error", "Polynomial degree must be at least 1 for RidgeCV.")
                return

            result = rsm_backend.rsm_fromDF(
                self.df, input_cols, output_col, degree_fit=degree, test_size=test_size, method=method
            )

            # 2. Optimize
            initial_guess = np.zeros(len(input_cols))
            opt_params, opt_val = result.optimize(
                initial_guess=initial_guess, bounds=bounds, constraints=scipy_constraints
            )
            if hasattr(opt_val, 'item') and getattr(opt_val, 'ndim', 0) > 0:
                opt_val = opt_val.item()
            else:
                opt_val = float(opt_val)

            # 3. Display Results
            self.results_text.config(state="normal")
            self.results_text.delete(1.0, tk.END)

            self.results_text.insert(tk.END, "=== RSM Optimization Results ===\n\n")
            if hasattr(result, "last_opt_result") and result.last_opt_result is not None:
                opt_res = result.last_opt_result
                if opt_res.success:
                    self.results_text.insert(tk.END, "Optimizer Status: Converged successfully\n")
                else:
                    self.results_text.insert(tk.END, f"Optimizer Status: Warning - {opt_res.message}\n")

            self.results_text.insert(tk.END, f"Regression Method: {result.method}\n")
            self.results_text.insert(
                tk.END, f"Coefficient of Determination (R²): {result.R_sq:.4f}\n"
            )
            self.results_text.insert(
                tk.END, f"Mean Squared Error (MSE): {result.MSE:.6f}\n"
            )
            self.results_text.insert(
                tk.END, f"Root Mean Squared Error (RMSE): {result.RMSE:.6f}\n\n"
            )

            # Display Coefficients if available (e.g. for RidgeCV)
            if result.coeffs is not None and result.intercept is not None:
                self.results_text.insert(tk.END, "Model Coefficients:\n")
                self.results_text.insert(tk.END, f"  - Intercept: {result.intercept:.6f}\n")
                term_strings = rsm_backend.generate_term_strings(input_cols, result.model)
                for term, coeff in zip(term_strings, result.coeffs):
                    self.results_text.insert(tk.END, f"  - {term}: {coeff:.6f}\n")
                self.results_text.insert(tk.END, "\n")

            # Display mathematical expression if available (e.g. for Genetic Programming)
            if getattr(result, "expression_text", None):
                self.results_text.insert(tk.END, f"{result.expression_text}\n\n")

            self.results_text.insert(tk.END, "Optimized Input Parameters:\n")
            for col, val in zip(input_cols, opt_params):
                self.results_text.insert(tk.END, f"  - {col}: {val:.6f}\n")

            self.results_text.insert(
                tk.END,
                f"\nOptimized (Minimum) Output Value [{output_col}]: {opt_val:.6f}\n",
            )

            if self.linear_constraints:
                self.results_text.insert(tk.END, "\nLinear Constraint Verification:\n")
                for i, c in enumerate(self.linear_constraints, 1):
                    lhs_val = sum(c["coeffs"].get(col, 0.0) * val for col, val in zip(input_cols, opt_params))
                    op = c["operator"]
                    b = c["bound"]
                    tol = 1e-4
                    if op == "<=":
                        satisfied = lhs_val <= b + tol
                    elif op == ">=":
                        satisfied = lhs_val >= b - tol
                    elif op == "==":
                        satisfied = abs(lhs_val - b) <= tol
                    else:
                        satisfied = True

                    status_str = "Satisfied" if satisfied else "VIOLATED"
                    self.results_text.insert(
                        tk.END,
                        f"  [{i}] {c['expression_str']}\n"
                        f"      Evaluated LHS = {lhs_val:.6f} [{status_str}]\n"
                    )

            self.results_text.config(state="disabled")

            # Enable plotting configuration
            self.result = result
            self.current_input_cols = input_cols
            self.plot_config_btn.config(state="normal")

        except Exception as e:
            messagebox.showerror(
                "Error", f"An error occurred during RSM calculation:\n{e!s}"
            )
    def open_plot_config(self):
        if not self.result or not self.current_input_cols:
            return

        config_win = tk.Toplevel(self)
        config_win.title("Configure Plot")
        config_win.geometry("700x730")

        notebook = ttk.Notebook(config_win)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # TAB 1: Roles
        roles_frame = ttk.Frame(notebook, padding="10")
        notebook.add(roles_frame, text="Roles")
        
        ttk.Label(roles_frame, text="Assign roles to each parameter for plotting:").pack(anchor=tk.W, pady=(0, 10))

        self.plot_param_configs = {}
        roles = ["X-Axis", "Y-Axis", "Row-Axis (P)", "Column-Axis (Q)", "Fixed"]
        
        for idx, col in enumerate(self.current_input_cols):
            row_frame = ttk.Frame(roles_frame)
            row_frame.pack(fill=tk.X, pady=5)
            
            ttk.Label(row_frame, text=col, width=15).pack(side=tk.LEFT)
            
            role_var = tk.StringVar()
            role_combo = ttk.Combobox(row_frame, textvariable=role_var, values=roles, state="readonly", width=15)
            role_combo.pack(side=tk.LEFT, padx=5)
            
            input_frame = ttk.Frame(row_frame)
            input_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            
            self.plot_param_configs[col] = {
                "role_var": role_var,
                "input_frame": input_frame,
                "vars": {}
            }
            
            def on_role_change(event, c=col):
                self._update_plot_role_inputs(c)
                
            role_combo.bind("<<ComboboxSelected>>", on_role_change)
            
            if idx == 0:
                role_combo.set("X-Axis")
            elif idx == 1:
                role_combo.set("Y-Axis")
            else:
                role_combo.set("Fixed")
                
            self._update_plot_role_inputs(col)

        # TAB 2: Labels
        labels_frame = ttk.Frame(notebook, padding="10")
        notebook.add(labels_frame, text="Labels")

        def add_label_field(parent, text, default_val):
            frame = ttk.Frame(parent)
            frame.pack(fill=tk.X, pady=5)
            ttk.Label(frame, text=text, width=35).pack(side=tk.LEFT)
            var = tk.StringVar(value=default_val)
            ttk.Entry(frame, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True)
            return var
            
        self.plot_title_var = add_label_field(labels_frame, "Plot Title:", "RSM Contour Plot")
        self.x_label_var = add_label_field(labels_frame, "X-Axis Label (Leave empty to default):", "")
        self.y_label_var = add_label_field(labels_frame, "Y-Axis Label (Leave empty to default):", "")
        self.colorbar_label_var = add_label_field(labels_frame, "Colorbar Label:", "")
        self.p_label_prefix_var = add_label_field(labels_frame, "Row-Axis (P) Label Prefix:", "")
        self.p_label_suffix_var = add_label_field(labels_frame, "Row-Axis (P) Label Suffix:", "")
        self.q_label_prefix_var = add_label_field(labels_frame, "Column-Axis (Q) Label Prefix:", "")
        self.q_label_suffix_var = add_label_field(labels_frame, "Column-Axis (Q) Label Suffix:", "")
        
        # TAB 3: Advanced Settings
        adv_frame = ttk.Frame(notebook, padding="10")
        notebook.add(adv_frame, text="Advanced Settings")

        self.adv_settings_vars = {}
        self.adv_settings_widgets = {}
        
        def add_adv_field(parent, key, text, default_val, var_type=tk.StringVar, options=None):
            frame = ttk.Frame(parent)
            frame.pack(fill=tk.X, pady=2)
            ttk.Label(frame, text=text, width=25).pack(side=tk.LEFT)
            var = var_type(value=default_val)
            
            if var_type == tk.BooleanVar:
                widget = ttk.Checkbutton(frame, variable=var)
                if text.startswith("Plot Uncertainty") and not getattr(self.result, 'supports_uncertainty', False):
                    widget.config(state="disabled")
                widget.pack(side=tk.LEFT)
            elif options is not None:
                widget = ttk.Combobox(frame, textvariable=var, values=options, state="readonly")
                widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
            else:
                widget = ttk.Entry(frame, textvariable=var)
                widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.adv_settings_vars[key] = var
            self.adv_settings_widgets[key] = widget
            return var

        add_adv_field(adv_frame, "cmap", "Colormap (cmap):", "plasma")
        add_adv_field(adv_frame, "alpha", "Alpha (transparency):", 0.85, tk.DoubleVar)
        add_adv_field(adv_frame, "fill_levels", "Fill Levels:", 100, tk.IntVar)
        add_adv_field(adv_frame, "line_levels", "Line Levels:", 10, tk.IntVar)
        add_adv_field(adv_frame, "line_color", "Line Color:", "white")
        add_adv_field(adv_frame, "inline_color", "Inline Color:", "white")
        add_adv_field(adv_frame, "inline_fontsize", "Inline Fontsize:", 9, tk.IntVar)
        add_adv_field(adv_frame, "grid_color", "Grid Color:", "gray")
        add_adv_field(adv_frame, "grid_linestyle", "Grid Linestyle:", "--")
        add_adv_field(adv_frame, "inline_format", "Inline Format:", "%1.1f")
        add_adv_field(adv_frame, "uniform_cmap", "Uniform Colormap:", True, tk.BooleanVar)
        add_adv_field(adv_frame, "show_colorbar", "Show Colorbar:", False, tk.BooleanVar)
        
        cbar_lbl_frame = ttk.Frame(adv_frame)
        cbar_lbl_frame.pack(fill=tk.X, pady=2)
        ttk.Label(cbar_lbl_frame, text="Colorbar Label:", width=25).pack(side=tk.LEFT)
        ttk.Entry(cbar_lbl_frame, textvariable=self.colorbar_label_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.adv_settings_vars["colorbar_label"] = self.colorbar_label_var

        add_adv_field(adv_frame, "plot_uncertainty", "Plot Uncertainty (Secondary Window):", False, tk.BooleanVar)

        add_adv_field(adv_frame, "scatter_data", "Scatter-Plot Data:", False, tk.BooleanVar)
        add_adv_field(adv_frame, "scatter_size", "Scatter Marker Size:", 30.0, tk.DoubleVar)
        add_adv_field(
            adv_frame,
            "scatter_color_mode",
            "Scatter Color Mode:",
            "Fixed Color",
            options=["Fixed Color", "Output Value (Colormap)"]
        )
        add_adv_field(adv_frame, "scatter_color", "Scatter Marker Color:", "white")
        add_adv_field(adv_frame, "scatter_cmap", "Scatter Colormap (cmap):", "plasma")
        add_adv_field(adv_frame, "scatter_edgecolor", "Scatter Edge Color:", "black")
        add_adv_field(adv_frame, "scatter_marker", "Scatter Marker Style:", "o")

        self.adv_settings_widgets["scatter_color_mode"].bind(
            "<<ComboboxSelected>>", lambda e: self._update_scatter_color_state()
        )
        self._update_scatter_color_state()

        btn_frame = ttk.Frame(config_win, padding="10")
        btn_frame.pack(fill=tk.X, pady=20)
        ttk.Button(btn_frame, text="Load Settings", command=self.load_plot_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Save Settings", command=self.save_plot_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Generate Plot", command=self.generate_plot).pack(side=tk.RIGHT)

    def _update_scatter_color_state(self):
        if not hasattr(self, "adv_settings_vars") or not hasattr(self, "adv_settings_widgets"):
            return
        mode_var = self.adv_settings_vars.get("scatter_color_mode")
        color_entry = self.adv_settings_widgets.get("scatter_color")
        cmap_entry = self.adv_settings_widgets.get("scatter_cmap")
        if mode_var is None or color_entry is None or cmap_entry is None:
            return
        if mode_var.get() == "Output Value (Colormap)":
            color_entry.config(state="disabled")
            cmap_entry.config(state="normal")
        else:
            color_entry.config(state="normal")
            cmap_entry.config(state="disabled")

    def _update_plot_role_inputs(self, col):
        param_data = self.plot_param_configs[col]
        role = param_data["role_var"].get()
        input_frame = param_data["input_frame"]
        
        for widget in input_frame.winfo_children():
            widget.destroy()
            
        param_data["vars"] = {}
        
        if role in ["X-Axis", "Y-Axis"]:
            min_var = tk.StringVar(value="-1.0")
            max_var = tk.StringVar(value="1.0")
            steps_var = tk.StringVar(value="50")
            
            ttk.Label(input_frame, text="Min:").pack(side=tk.LEFT)
            ttk.Entry(input_frame, textvariable=min_var, width=8).pack(side=tk.LEFT, padx=(0,5))
            
            ttk.Label(input_frame, text="Max:").pack(side=tk.LEFT)
            ttk.Entry(input_frame, textvariable=max_var, width=8).pack(side=tk.LEFT, padx=(0,5))
            
            ttk.Label(input_frame, text="Steps:").pack(side=tk.LEFT)
            ttk.Entry(input_frame, textvariable=steps_var, width=5).pack(side=tk.LEFT)
            
            param_data["vars"]["min"] = min_var
            param_data["vars"]["max"] = max_var
            param_data["vars"]["steps"] = steps_var
            
        elif role in ["Row-Axis (P)", "Column-Axis (Q)"]:
            val_var = tk.StringVar(value="0, 1, 2")
            ttk.Label(input_frame, text="Values (comma-separated):").pack(side=tk.LEFT)
            ttk.Entry(input_frame, textvariable=val_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
            param_data["vars"]["values"] = val_var
            
        elif role == "Fixed":
            val_var = tk.StringVar(value="0.0")
            ttk.Label(input_frame, text="Value:").pack(side=tk.LEFT)
            ttk.Entry(input_frame, textvariable=val_var, width=10).pack(side=tk.LEFT)
            param_data["vars"]["value"] = val_var

    def generate_plot(self):
        config = {'fixed': []}
        x_count = y_count = p_count = q_count = 0
        
        label_arrays_p = None
        label_arrays_q = None
        
        x_col = None
        y_col = None
        
        try:
            for idx, col in enumerate(self.current_input_cols):
                param_data = self.plot_param_configs[col]
                role = param_data["role_var"].get()
                vars_dict = param_data["vars"]
                
                if role == "X-Axis":
                    x_count += 1
                    min_v = float(vars_dict["min"].get())
                    max_v = float(vars_dict["max"].get())
                    steps_v = int(vars_dict["steps"].get())
                    config['x'] = (idx, np.linspace(min_v, max_v, steps_v))
                    x_col = col
                elif role == "Y-Axis":
                    y_count += 1
                    min_v = float(vars_dict["min"].get())
                    max_v = float(vars_dict["max"].get())
                    steps_v = int(vars_dict["steps"].get())
                    config['y'] = (idx, np.linspace(min_v, max_v, steps_v))
                    y_col = col
                elif role == "Row-Axis (P)":
                    p_count += 1
                    val_strs = vars_dict["values"].get().split(",")
                    vals = [float(v.strip()) for v in val_strs if v.strip()]
                    config['p'] = (idx, vals)
                    
                    p_prefix = self.p_label_prefix_var.get().strip()
                    p_suffix = self.p_label_suffix_var.get().strip()
                    if not p_prefix:
                        p_prefix = f"{col}="
                    label_arrays_p = [f"{p_prefix}{v}{p_suffix}" for v in vals]
                    
                elif role == "Column-Axis (Q)":
                    q_count += 1
                    val_strs = vars_dict["values"].get().split(",")
                    vals = [float(v.strip()) for v in val_strs if v.strip()]
                    config['q'] = (idx, vals)
                    
                    q_prefix = self.q_label_prefix_var.get().strip()
                    q_suffix = self.q_label_suffix_var.get().strip()
                    if not q_prefix:
                        q_prefix = f"{col}="
                    label_arrays_q = [f"{q_prefix}{v}{q_suffix}" for v in vals]
                    
                elif role == "Fixed":
                    val = float(vars_dict["value"].get())
                    config['fixed'].append((idx, val))
                    
            if x_count != 1 or y_count != 1:
                messagebox.showerror("Error", "You must assign exactly one X-Axis and one Y-Axis.")
                return
            if p_count > 1 or q_count > 1:
                messagebox.showerror("Error", "You can assign at most one Row-Axis (P) and one Column-Axis (Q).")
                return
                
            x_label = self.x_label_var.get().strip()
            if not x_label:
                x_label = x_col
                
            y_label = self.y_label_var.get().strip()
            if not y_label:
                y_label = y_col
                
            title = self.plot_title_var.get().strip()
            if not title:
                title = "RSM Contour Plot"

            label_array = None
            if p_count > 0 or q_count > 0:
                p_labels = label_arrays_p if label_arrays_p else [""]
                q_labels = label_arrays_q if label_arrays_q else [""]
                label_array = []
                for p_lbl in p_labels:
                    row_labels = []
                    for q_lbl in q_labels:
                        if p_lbl and q_lbl:
                            row_labels.append(f"{p_lbl}, {q_lbl}")
                        else:
                            row_labels.append(p_lbl or q_lbl)
                    label_array.append(row_labels)
                    
            # Gather advanced plot settings
            plot_settings = {}
            for k, var in self.adv_settings_vars.items():
                plot_settings[k] = var.get()

            if plot_settings.get('plot_uncertainty', False) and not getattr(self.result, 'supports_uncertainty', False):
                messagebox.showerror("Error", f"Uncertainty plotting is not supported for {getattr(self.result, 'method', 'this model')}.")
                return

            self.result.visualize_rsm(config, title=title, xlabel=x_label, ylabel=y_label, label_array=label_array, plot_settings=plot_settings)
            
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")

    def save_plot_settings(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            title="Save Plot Settings"
        )
        if not filepath:
            return

        settings = {
            "roles": {},
            "labels": {
                "plot_title": self.plot_title_var.get(),
                "x_label": self.x_label_var.get(),
                "y_label": self.y_label_var.get(),
                "colorbar_label": self.colorbar_label_var.get(),
                "p_label_prefix": self.p_label_prefix_var.get(),
                "p_label_suffix": self.p_label_suffix_var.get(),
                "q_label_prefix": self.q_label_prefix_var.get(),
                "q_label_suffix": self.q_label_suffix_var.get(),
            },
            "advanced": {}
        }

        for col, config in self.plot_param_configs.items():
            role = config["role_var"].get()
            role_data = {"role": role, "vars": {}}
            for var_name, var_obj in config["vars"].items():
                role_data["vars"][var_name] = var_obj.get()
            settings["roles"][col] = role_data

        for key, var in self.adv_settings_vars.items():
            if key == "colorbar_label":
                continue
            settings["advanced"][key] = var.get()

        try:
            with open(filepath, "w") as f:
                json.dump(settings, f, indent=4)
            messagebox.showinfo("Success", f"Plot settings saved successfully to:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")

    def load_plot_settings(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            title="Load Plot Settings"
        )
        if not filepath:
            return

        try:
            with open(filepath, "r") as f:
                settings = json.load(f)

            if "labels" in settings:
                labels = settings["labels"]
                if "plot_title" in labels:
                    self.plot_title_var.set(labels["plot_title"])
                if "x_label" in labels:
                    self.x_label_var.set(labels["x_label"])
                if "y_label" in labels:
                    self.y_label_var.set(labels["y_label"])
                if "colorbar_label" in labels:
                    self.colorbar_label_var.set(labels["colorbar_label"])
                if "p_label_prefix" in labels:
                    self.p_label_prefix_var.set(labels["p_label_prefix"])
                if "p_label_suffix" in labels:
                    self.p_label_suffix_var.set(labels["p_label_suffix"])
                if "q_label_prefix" in labels:
                    self.q_label_prefix_var.set(labels["q_label_prefix"])
                if "q_label_suffix" in labels:
                    self.q_label_suffix_var.set(labels["q_label_suffix"])

            if "advanced" in settings:
                for key, val in settings["advanced"].items():
                    if key in self.adv_settings_vars:
                        if key == "plot_uncertainty" and val:
                            if not getattr(self.result, "supports_uncertainty", False):
                                self.adv_settings_vars[key].set(False)
                                method_name = getattr(self.result, "method", "this model")
                                messagebox.showinfo(
                                    "Setting Overridden",
                                    f"Uncertainty plotting was enabled in the loaded configuration, "
                                    f"but the current model ({method_name}) does not support uncertainty prediction. "
                                    f"The setting has been overridden to False."
                                )
                                continue
                        self.adv_settings_vars[key].set(val)
                self._update_scatter_color_state()

            if "roles" in settings:
                for col, role_data in settings["roles"].items():
                    if col in self.plot_param_configs:
                        config = self.plot_param_configs[col]
                        config["role_var"].set(role_data.get("role", "Fixed"))
                        self._update_plot_role_inputs(col)
                        if "vars" in role_data:
                            for var_name, var_val in role_data["vars"].items():
                                if var_name in config["vars"]:
                                    config["vars"][var_name].set(var_val)

            messagebox.showinfo("Success", f"Plot settings loaded successfully from:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load settings: {e}")





if __name__ == "__main__":
    app = RSMGui()
    app.mainloop()
