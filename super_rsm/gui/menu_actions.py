"""
super_rsm/gui/menu_actions.py

Top application menu bar ("File" -> "Save", "Save as", "Load") and
self-contained .rsm project state serialization/restoration mixin for RSMApp.
"""

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Any, Dict, List, Optional

from super_rsm.core.persistence import load_rsm_project, save_rsm_project
from super_rsm.gui.components.treeview_helper import clear_treeview
from super_rsm.gui.controller import AppController
from super_rsm.gui.styles.palette import PALETTE


class RSMMenuMixin:
    """Mixin providing top File menu bar and .rsm project save/load workflows for RSMApp."""

    def _build_menubar(self) -> None:
        """Create top-of-window menu bar with the 'File' menu ('Save', 'Save as', 'Load')."""
        self.menubar = tk.Menu(self, tearoff=0)
        self.file_menu = tk.Menu(self.menubar, tearoff=0)
        self.file_menu.add_command(
            label="Save",
            accelerator="Ctrl+S",
            command=lambda: self.save_project(save_as=False),
        )
        self.file_menu.add_command(
            label="Save as",
            accelerator="Ctrl+Shift+S",
            command=lambda: self.save_project(save_as=True),
        )
        self.file_menu.add_command(
            label="Load",
            accelerator="Ctrl+O",
            command=lambda: self.load_project(),
        )
        self.menubar.add_cascade(label="File", menu=self.file_menu)
        self.config(menu=self.menubar)

        self.bind_all("<Control-s>", lambda e: self.save_project(save_as=False))
        self.bind_all("<Control-S>", lambda e: self.save_project(save_as=True))
        self.bind_all("<Control-o>", lambda e: self.load_project())

    def _collect_project_state_dict(self) -> Dict[str, Any]:
        """Collect complete GUI and workflow state into a JSON-serializable dictionary."""
        try:
            hparams = self.model_view.get_hyperparameters()
        except Exception:
            hparams = {}
        try:
            test_size = float(self.test_size_var.get())
        except Exception:
            test_size = 0.20

        return {
            "original_filepath": self.state.filepath,
            "selected_inputs": self.data_view.get_selected_inputs(),
            "selected_output": self.data_view.get_selected_output(),
            "input_cols": list(self.state.current_input_cols),
            "output_col": self.state.current_output_col,
            "method": self.method_var.get(),
            "test_size": test_size,
            "split_by_groups": bool(self.split_by_groups_var.get()),
            "hyperparameters": hparams,
            "opt_goal": self.opt_goal_var.get(),
            "bounds": {
                col: [min_v.get(), max_v.get()]
                for col, (min_v, max_v) in self.bound_entries.items()
            },
            "linear_constraints": list(self.state.linear_constraints),
            "opt_params_dict": dict(self.state.opt_params_dict),
            "last_opt_report_text": self.state.last_opt_report_text,
            "eval_entries": {col: var.get() for col, var in self.eval_entries.items()},
            "eval_history": list(self.state.eval_history),
            "eval_pred_str": self.results_view.eval_pred_var.get(),
            "eval_unc_str": self.results_view.eval_unc_var.get(),
        }

    def save_project(self, filepath: Optional[str] = None, save_as: bool = False) -> bool:
        """Save the entirety of work progress (including dataset) to a .rsm file."""
        target = filepath
        if not target:
            if not save_as and self.state.project_filepath:
                target = self.state.project_filepath
            else:
                default_name = (
                    Path(self.state.project_filepath).name
                    if self.state.project_filepath
                    else (f"{Path(self.state.filepath).stem}.rsm" if self.state.filepath else "project.rsm")
                )
                target = filedialog.asksaveasfilename(
                    defaultextension=".rsm",
                    initialfile=default_name,
                    filetypes=[("SuperRSM Project (*.rsm)", "*.rsm"), ("All Files", "*.*")],
                    title="Save Project As" if save_as else "Save Project",
                    parent=self,
                )
        if not target:
            return False

        try:
            state_dict = self._collect_project_state_dict()
            saved_path = save_rsm_project(
                filepath=target,
                df=self.state.df,
                state_dict=state_dict,
                result=self.state.result,
            )
            self.state.project_filepath = str(saved_path)
            self.state.set_status(f"Saved project progress to '{saved_path.name}'.")
            return True
        except Exception as exc:
            messagebox.showerror("Save Error", f"Failed to save project:\n{exc!s}", parent=self)
            return False

    def load_project(self, filepath: Optional[str] = None) -> bool:
        """Load work progress and embedded dataset from a .rsm file."""
        source = filepath
        if not source:
            source = filedialog.askopenfilename(
                filetypes=[("SuperRSM Project (*.rsm)", "*.rsm"), ("All Files", "*.*")],
                title="Load Project (.rsm)",
                parent=self,
            )
        if not source:
            return False

        try:
            payload = load_rsm_project(source)
            self._apply_loaded_project(source, payload)
            return True
        except Exception as exc:
            messagebox.showerror("Load Error", f"Failed to load .rsm project:\n{exc!s}", parent=self)
            return False

    def _apply_loaded_project(self, source_path: str, payload: Dict[str, Any]) -> None:
        """Restore DataFrame, UI selections, fitted model, optimization tables, and history."""
        df = payload.get("df")
        result = payload.get("result")
        st: Dict[str, Any] = payload.get("state", {})

        self.state.project_filepath = str(Path(source_path))
        self.state.df = df
        orig_fp = st.get("original_filepath", "")
        self.state.filepath = orig_fp
        self.file_path_var.set(orig_fp if orig_fp else f"[Embedded in {Path(source_path).name}]")

        # 1. Restore Dataset & Column Selections
        if df is not None:
            columns = list(df.columns)
            self.data_view.set_columns(columns)
            sel_out = st.get("selected_output", "")
            if sel_out in columns:
                self.output_combo.set(sel_out)
            sel_ins = set(st.get("selected_inputs", []))
            self.input_listbox.selection_clear(0, tk.END)
            for idx, col_name in enumerate(columns):
                if col_name in sel_ins:
                    self.input_listbox.selection_set(idx)
            src_label = Path(orig_fp).name if orig_fp else Path(source_path).name
            self.header_view.set_dataset_status(src_label, len(df), len(columns))
        else:
            self.data_view.set_columns([])

        # 2. Restore Model & Fit Settings
        method = st.get("method", "")
        if method and method in self.model_view.method_combo["values"]:
            self.method_var.set(method)
            self.model_view._refresh_metadata_ui()
        if "test_size" in st:
            self.test_size_var.set(float(st["test_size"]))
        if "split_by_groups" in st:
            self.split_by_groups_var.set(bool(st["split_by_groups"]))
        for hp_name, hp_val in st.get("hyperparameters", {}).items():
            self.model_view.param_form.set_hyperparameter(hp_name, hp_val)

        # 3. Rebuild Bounds & Evaluation Inputs for selected columns
        selected_cols = self.data_view.get_selected_inputs()
        self.state.previous_input_cols = selected_cols
        self.bounds_view.rebuild_for_columns(selected_cols, self.state.get_col_range_str)
        self.results_view.rebuild_eval_inputs(selected_cols, self.state.get_col_range_str, self.state.get_col_mean_str)

        if "opt_goal" in st:
            self.opt_goal_var.set(st["opt_goal"])
        self._on_opt_goal_change()

        for col, pair in st.get("bounds", {}).items():
            if col in self.bound_entries and isinstance(pair, (list, tuple)) and len(pair) == 2:
                self.bound_entries[col][0].set(str(pair[0]))
                self.bound_entries[col][1].set(str(pair[1]))

        for col, val_str in st.get("eval_entries", {}).items():
            if col in self.eval_entries:
                self.eval_entries[col].set(str(val_str))

        # 4. Restore Linear Constraints & Evaluation History
        self.state.linear_constraints = list(st.get("linear_constraints", []))
        self.constraints_view.refresh(self.state.linear_constraints)

        self.clear_eval_history()
        for rec in st.get("eval_history", []):
            self.state.eval_history.append(rec)
            self.eval_history_tree.insert(
                "", tk.END, values=(rec["id"], rec["inputs_str"], rec["pred_str"], rec["std_str"])
            )

        # 5. Restore Fitted Model, Optimization Results, and Markdown/HTML Report
        if result is not None:
            self.state.result = result
            self.state.current_input_cols = list(st.get("input_cols", selected_cols))
            self.state.current_output_col = st.get("output_col", self.data_view.get_selected_output())
            self.state.fitted_model_signature = self._get_current_fit_signature()
            self.state.opt_params_dict = {k: float(v) for k, v in st.get("opt_params_dict", {}).items()}
            self.state.last_opt_report_text = st.get("last_opt_report_text", "")

            r2_color = (
                PALETTE["success"] if result.R_sq >= 0.8 else (PALETTE["warning"] if result.R_sq >= 0.5 else PALETTE["danger"])
            )
            self.kpi_r2.set_value(f"{result.R_sq:.4f}", f"Method: {result.method}", r2_color)
            self.kpi_rmse.set_value(f"{result.RMSE:.5g}", f"MSE: {result.MSE:.5g}")
            self.model_view.fit_status_var.set(f"✓ Fitted: {result.method} (R² = {result.R_sq:.4f})")
            self.model_view.fit_status_lbl.config(fg=PALETTE["success"])

            self._restore_optimization_tables(st)
            if "eval_pred_str" in st:
                self.results_view.eval_pred_var.set(st["eval_pred_str"])
            if "eval_unc_str" in st:
                self.results_view.eval_unc_var.set(st["eval_unc_str"])
            self._render_full_report()
            self._on_busy_changed(False, "")
        else:
            self._invalidate_fitted_model("Project loaded — click 'Fit Surrogate Model' when ready.")

        self.state.set_status(f"Loaded project '{Path(source_path).name}' successfully.")

    def _restore_optimization_tables(self, st: Dict[str, Any]) -> None:
        """Restore Optimal Parameters and Constraint Verification tables from saved project state."""
        clear_treeview(self.opt_params_tree)
        clear_treeview(self.constraint_eval_tree)
        input_cols: List[str] = self.state.current_input_cols
        output_col = self.state.current_output_col or "Output"

        if self.state.opt_params_dict and self.state.result is not None:
            opt_vec = [self.state.opt_params_dict.get(c, 0.0) for c in input_cols]
            opt_val = float(self.state.result.evaluate_point(opt_vec, return_std=False))
            self.kpi_opt.set_value(f"{opt_val:.6g}", f"Target: {output_col}")

            bounds_map = st.get("bounds", {})
            for col, val in zip(input_cols, opt_vec):
                pair = bounds_map.get(col, ["", ""])
                min_s, max_s = str(pair[0]).strip(), str(pair[1]).strip()
                b_disp = "Unconstrained" if (not min_s and not max_s) else f"[{min_s or '-∞'}, {max_s or '+∞'}]"
                self.opt_params_tree.insert("", tk.END, values=(col, f"{val:.6f}", b_disp, self.state.get_col_range_str(col)))

            n_viol, rows, _ = AppController.evaluate_constraints_at_point(
                self.state.linear_constraints, input_cols, opt_vec
            )
            for r_id, expr, lhs, st_str, tag in rows:
                self.constraint_eval_tree.insert("", tk.END, values=(r_id, expr, f"{lhs:.6f}", st_str), tags=(tag,))
            self.kpi_status.set_value(
                "Converged" if n_viol == 0 else "Check Status",
                "Restored from .rsm project",
                PALETTE["success"] if n_viol == 0 else PALETTE["warning"],
            )
        else:
            self.kpi_opt.set_value("—", f"Target: {output_col}")
            self.kpi_status.set_value("Model Fitted", "Ready to optimize / evaluate", PALETTE["accent"])
            for i, c in enumerate(self.state.linear_constraints, 1):
                self.constraint_eval_tree.insert("", tk.END, values=(i, c["expression_str"], "—", "Pending"))

