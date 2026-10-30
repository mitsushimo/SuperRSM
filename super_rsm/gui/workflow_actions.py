"""
super_rsm/gui/workflow_actions.py

Action mixin for RSMApp handling model fitting, constrained optimization,
custom point evaluation, bounds/history helpers, and linear constraint CRUD.
"""

import tkinter as tk
from tkinter import messagebox
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from super_rsm.gui.components.treeview_helper import clear_treeview
from super_rsm.gui.controller import AppController
from super_rsm.gui.dialogs.constraint_dialog import LinearConstraintDialog
from super_rsm.gui.dialogs.plot_config_dialog import PlotConfigDialog
from super_rsm.gui.styles.palette import PALETTE


class RSMWorkflowMixin:
    """Mixin providing fit, optimize, evaluate, and constraint handlers for RSMApp."""

    def fill_bounds_from_data(self) -> None:
        if self.state.df is None or not self.bound_entries:
            return
        for col_name, (min_var, max_var) in self.bound_entries.items():
            if col_name in self.state.df.columns:
                s = pd.to_numeric(self.state.df[col_name], errors="coerce").dropna()
                if not s.empty:
                    min_var.set(f"{float(s.min()):.6g}")
                    max_var.set(f"{float(s.max()):.6g}")
        self.state.set_status("Populated optimization bounds from dataset [min, max] ranges.")

    def clear_bounds_entries(self) -> None:
        for min_var, max_var in self.bound_entries.values():
            min_var.set("")
            max_var.set("")
        self.state.set_status("Cleared optimization bounds.")

    def _render_full_report(self) -> None:
        self.results_view.set_report_text(
            AppController.format_full_report(
                self.state.result, self.state.current_input_cols, self.state.current_output_col, self.state.last_opt_report_text
            )
        )

    def copy_results_to_clipboard(self) -> None:
        content = self.results_text.get("1.0", tk.END).strip()
        if content:
            self.clipboard_clear()
            self.clipboard_append(content)
            self.state.set_status("Copied model report to clipboard.")

    def fill_eval_from_optimal(self) -> None:
        if not self.state.opt_params_dict:
            messagebox.showinfo("Info", "Run optimization first to populate optimal parameter values.", parent=self)
            return
        for col, var in self.eval_entries.items():
            if col in self.state.opt_params_dict:
                var.set(f"{self.state.opt_params_dict[col]:.6g}")
        self.state.set_status("Populated evaluation inputs from the latest optimal solution.")

    def fill_eval_from_mean(self) -> None:
        for col, var in self.eval_entries.items():
            var.set(self.state.get_col_mean_str(col))
        self.state.set_status("Populated evaluation inputs with dataset column means.")

    def clear_eval_entries(self) -> None:
        for var in self.eval_entries.values():
            var.set("")
        self.state.set_status("Cleared evaluation input fields.")

    def clear_eval_history(self) -> None:
        self.state.eval_history.clear()
        clear_treeview(self.eval_history_tree)
        self.state.set_status("Cleared evaluation history.")

    def copy_eval_history(self) -> None:
        if not self.state.eval_history:
            return
        lines = [
            "#\tInputs\tPredicted Output\tStd Dev",
            *[f"{r['id']}\t{r['inputs_str']}\t{r['pred_str']}\t{r['std_str']}" for r in self.state.eval_history],
        ]
        self.clipboard_clear()
        self.clipboard_append("\n".join(lines))
        self.state.set_status("Copied evaluation history to clipboard.")

    def _on_eval_history_double_click(self) -> None:
        sel = self.eval_history_tree.selection()
        if not sel:
            return
        idx = int(self.eval_history_tree.item(sel[0], "values")[0]) - 1
        if 0 <= idx < len(self.state.eval_history):
            for col, val in self.state.eval_history[idx]["params_dict"].items():
                if col in self.eval_entries:
                    self.eval_entries[col].set(f"{val:.6g}")

    def add_linear_constraint(self) -> None:
        input_cols = self.data_view.get_selected_inputs()
        if not input_cols:
            messagebox.showwarning("Warning", "Please select input columns first before adding constraints.", parent=self)
            return
        LinearConstraintDialog(
            self, input_cols, on_save_callback=lambda c: (self.state.linear_constraints.append(c), self.constraints_view.refresh(self.state.linear_constraints))
        )

    def edit_linear_constraint(self) -> None:
        sel = self.constraints_tree.selection()
        if not sel:
            messagebox.showinfo("Info", "Please select a constraint from the list to edit.", parent=self)
            return
        idx = int(self.constraints_tree.item(sel[0], "values")[0]) - 1
        if 0 <= idx < len(self.state.linear_constraints):
            input_cols = self.data_view.get_selected_inputs()
            def _save(cdata: Dict[str, Any]) -> None:
                self.state.linear_constraints[idx] = cdata
                self.constraints_view.refresh(self.state.linear_constraints)
            LinearConstraintDialog(self, input_cols, existing_constraint=self.state.linear_constraints[idx], on_save_callback=_save)

    def delete_linear_constraint(self) -> None:
        sel = self.constraints_tree.selection()
        if not sel:
            messagebox.showinfo("Info", "Please select a constraint from the list to delete.", parent=self)
            return
        idx = int(self.constraints_tree.item(sel[0], "values")[0]) - 1
        if 0 <= idx < len(self.state.linear_constraints):
            del self.state.linear_constraints[idx]
            self.constraints_view.refresh(self.state.linear_constraints)

    def clear_linear_constraints(self) -> None:
        if self.state.linear_constraints and messagebox.askyesno(
            "Confirm", "Are you sure you want to remove all linear constraints?", parent=self
        ):
            self.state.linear_constraints.clear()
            self.constraints_view.refresh(self.state.linear_constraints)

    def fit_model(self, synchronous: Optional[bool] = None) -> bool:
        if self.state.df is None:
            messagebox.showwarning("Warning", "Please load data first.", parent=self)
            return False
        input_cols = self.data_view.get_selected_inputs()
        output_col = self.data_view.get_selected_output()
        if not input_cols:
            messagebox.showwarning("Warning", "Please select at least one input column.", parent=self)
            return False
        if not output_col:
            messagebox.showwarning("Warning", "Please select an output column.", parent=self)
            return False
        if output_col in input_cols:
            messagebox.showwarning("Warning", "Output column cannot be in the input columns.", parent=self)
            return False

        try:
            hparams = self.model_view.get_hyperparameters()
            test_size = float(self.test_size_var.get())
            method = self.method_var.get()
        except Exception as e:
            messagebox.showerror("Error", f"Invalid fit configuration:\n{e!s}", parent=self)
            return False

        self.model_view.fit_status_var.set(f"Fitting {method}...")
        self.model_view.fit_status_lbl.config(fg=PALETTE["accent"])
        sync_flag = (not self.async_tasks) if synchronous is None else synchronous

        def _on_fit_done(result: Any) -> None:
            self.state.result = result
            self.state.current_input_cols = input_cols
            self.state.current_output_col = output_col
            self.state.fitted_model_signature = self._get_current_fit_signature()
            self.state.last_opt_report_text = ""
            self.state.opt_params_dict.clear()

            r2_color = PALETTE["success"] if result.R_sq >= 0.8 else (PALETTE["warning"] if result.R_sq >= 0.5 else PALETTE["danger"])
            self.kpi_r2.set_value(f"{result.R_sq:.4f}", f"Method: {result.method}", r2_color)
            self.kpi_rmse.set_value(f"{result.RMSE:.5g}", f"MSE: {result.MSE:.5g}")
            self._on_opt_goal_change()
            self.kpi_opt.set_value("—", f"Target: {output_col}")
            self.kpi_status.set_value("Model Fitted", "Ready to optimize / evaluate", PALETTE["accent"])
            clear_treeview(self.opt_params_tree)
            clear_treeview(self.constraint_eval_tree)
            self.model_view.fit_status_var.set(f"✓ Fitted: {result.method} (R² = {result.R_sq:.4f})")
            self.model_view.fit_status_lbl.config(fg=PALETTE["success"])
            self.results_view.eval_pred_var.set(f"Predicted {output_col}:  —")
            self.results_view.eval_unc_var.set(
                f"Ready — {result.method} supports predictive uncertainty (±1σ & 95% CI)."
                if result.supports_uncertainty
                else "Ready — Enter parameter values above and click 'Evaluate Output'."
            )
            self._render_full_report()
            self.state.set_status(
                f"Model fit complete — {result.method} (R² = {result.R_sq:.4f}, RMSE = {result.RMSE:.5g}). Ready for optimization, evaluation, or plotting."
            )

        def _on_fit_err(exc: Exception) -> None:
            self.state.set_status("Model fitting failed — check error dialog.")
            self.model_view.fit_status_var.set("Fit failed.")
            self.model_view.fit_status_lbl.config(fg=PALETTE["danger"])
            messagebox.showerror("Error", f"An error occurred while fitting the surrogate model:\n{exc!s}", parent=self)

        return self.controller._run_async(
            AppController.execute_fit,
            self.state.df, input_cols, output_col, method, test_size, hparams,
            on_success=_on_fit_done, on_error=_on_fit_err,
            busy_message=f"Fitting {method} surrogate model...", synchronous=sync_flag,
        )

    def run_optimization(self, synchronous: Optional[bool] = None) -> None:
        if self.state.df is None or self.state.result is None or not self.state.current_input_cols:
            messagebox.showwarning("Warning", "Please fit the surrogate model first.", parent=self)
            return
        input_cols = self.state.current_input_cols
        output_col = self.state.current_output_col or self.data_view.get_selected_output()
        goal = self.opt_goal_var.get()
        is_maximize = goal == "Maximize"

        bounds: List[Tuple[Optional[float], Optional[float]]] = []
        bounds_display: Dict[str, str] = {}
        for col in input_cols:
            min_s, max_s = self.bound_entries[col][0].get().strip(), self.bound_entries[col][1].get().strip()
            try:
                min_v = float(min_s) if min_s else None
                max_v = float(max_s) if max_s else None
            except ValueError:
                messagebox.showerror("Error", f"Invalid bound for {col}", parent=self)
                return
            if min_v is not None and max_v is not None and min_v > max_v:
                messagebox.showerror("Error", f"Minimum bound cannot exceed maximum bound for '{col}'.", parent=self)
                return
            bounds.append((min_v, max_v))
            bounds_display[col] = (
                "Unconstrained"
                if (min_v is None and max_v is None)
                else f"[{f'{min_v:g}' if min_v is not None else '-∞'}, {f'{max_v:g}' if max_v is not None else '+∞'}]"
            )

        opt_bounds = None if all(b == (None, None) for b in bounds) else bounds
        constraint_specs = AppController.build_constraint_specs(self.state.linear_constraints)
        sync_flag = (not self.async_tasks) if synchronous is None else synchronous

        def _on_opt_done(opt_res: Any) -> None:
            opt_params, opt_val = opt_res.params, float(opt_res.fun)
            self.state.opt_params_dict = {col: float(val) for col, val in zip(input_cols, opt_params)}
            self._on_opt_goal_change()
            self.kpi_opt.set_value(f"{opt_val:.6g}", f"Target: {output_col}")

            clear_treeview(self.opt_params_tree)
            for col, val in zip(input_cols, opt_params):
                self.opt_params_tree.insert(
                    "", tk.END, values=(col, f"{val:.6f}", bounds_display.get(col, "Unconstrained"), self.state.get_col_range_str(col))
                )

            clear_treeview(self.constraint_eval_tree)
            n_violated, rows, c_lines = AppController.evaluate_constraints_at_point(
                self.state.linear_constraints, input_cols, opt_params
            )
            for r_id, expr, lhs, st_str, tag in rows:
                self.constraint_eval_tree.insert("", tk.END, values=(r_id, expr, f"{lhs:.6f}", st_str), tags=(tag,))

            if opt_res.success and n_violated == 0:
                sub = f"{len(self.state.linear_constraints)} constraint(s) satisfied" if self.state.linear_constraints else f"{goal}d successfully"
                self.kpi_status.set_value("Converged", sub, PALETTE["success"])
            else:
                self.kpi_status.set_value("Check Status", f"{n_violated} constraint violation(s)" if n_violated else "Optimizer warning", PALETTE["warning"])

            opt_lines = [
                "=== RSM Optimization Results ===\n\n",
                f"Optimization Goal: {goal} '{output_col}'\n",
                "Optimizer Status: Converged successfully\n\n" if opt_res.success else f"Optimizer Status: Warning - {opt_res.message}\n\n",
                "Optimized Input Parameters:\n",
                *[f"  - {col}: {val:.6f}\n" for col, val in zip(input_cols, opt_params)],
                f"\nOptimized ({'Maximum' if is_maximize else 'Minimum'}) Output Value [{output_col}]: {opt_val:.6f}\n",
            ]
            if c_lines:
                opt_lines.extend(["\nLinear Constraint Verification:\n", *c_lines])
            self.state.last_opt_report_text = "".join(opt_lines)
            self._render_full_report()
            self.state.set_status(f"Optimization complete — {self.state.result.method} ({'Max' if is_maximize else 'Min'} {output_col} = {opt_val:.6g}).")

        self.controller._run_async(
            self.state.result.optimize,
            bounds=opt_bounds, constraints=constraint_specs, maximize=is_maximize,
            on_success=_on_opt_done,
            busy_message=f"Running constrained {'maximization' if is_maximize else 'minimization'}...",
            synchronous=sync_flag,
        )

    def evaluate_custom_point(self) -> None:
        if self.state.result is None or not self.state.current_input_cols:
            messagebox.showwarning("Warning", "Please fit the surrogate model first.", parent=self)
            return
        param_vals, params_dict = [], {}
        for col in self.state.current_input_cols:
            txt = self.eval_entries[col].get().strip() if col in self.eval_entries else ""
            try:
                val = float(txt)
            except ValueError:
                messagebox.showerror("Error", f"Invalid numeric value for '{col}': '{txt}'.", parent=self)
                return
            param_vals.append(val)
            params_dict[col] = val

        y_val, std_val = self.state.result.evaluate_point(param_vals, return_std=True)
        out_col = self.state.current_output_col or "Output"
        self.results_view.eval_pred_var.set(f"Predicted {out_col}:  {y_val:.6g}")
        if std_val is not None:
            self.results_view.eval_unc_var.set(
                f"Predictive Std Dev (±1σ): ±{std_val:.5g}   |   95% CI: [{y_val - 1.96 * std_val:.5g}, {y_val + 1.96 * std_val:.5g}]"
            )
            std_str = f"±{std_val:.5g}"
        else:
            self.results_view.eval_unc_var.set(f"Model: {self.state.result.method} (Deterministic prediction — uncertainty N/A)")
            std_str = "—"
        inputs_str = ", ".join(f"{c}={v:.5g}" for c, v in params_dict.items())
        rec = {
            "id": len(self.state.eval_history) + 1,
            "params_dict": params_dict, "inputs_str": inputs_str,
            "pred_val": y_val, "std_val": std_val,
            "pred_str": f"{y_val:.6g}", "std_str": std_str,
        }
        self.state.eval_history.append(rec)
        self.eval_history_tree.insert("", tk.END, values=(rec["id"], inputs_str, rec["pred_str"], std_str))
        self.state.set_status(f"Evaluated {self.state.result.method} at ({inputs_str}) → {out_col} = {y_val:.6g}.")

    def open_plot_config(self) -> None:
        if not self.state.result or not self.state.current_input_cols:
            return
        if self.plot_config_win is not None and self.plot_config_win.winfo_exists():
            self.plot_config_win.destroy()
        self.plot_config_win = PlotConfigDialog(
            self, self.state.current_input_cols, self.state.current_output_col,
            self.state.result, self.state.df, self.state.opt_params_dict,
        )
