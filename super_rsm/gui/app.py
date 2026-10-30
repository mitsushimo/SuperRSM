"""
super_rsm/gui/app.py

Main RSMApp desktop window shell assembling modular views, reactive AppState,
and non-blocking AppController.
"""

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Optional, Tuple
import pandas as pd

from super_rsm.gui.components.treeview_helper import clear_treeview
from super_rsm.gui.controller import AppController
from super_rsm.gui.dialogs.plot_config_dialog import PlotConfigDialog
from super_rsm.gui.state import AppState
from super_rsm.gui.styles.palette import PALETTE
from super_rsm.gui.styles.theme import configure_ttk_styles
from super_rsm.gui.views import (
    BoundsView,
    ConstraintsView,
    DataView,
    FileSourceBar,
    HeaderView,
    KPIStripView,
    ModelConfigView,
    ResultsView,
)
from super_rsm.gui.workflow_actions import RSMWorkflowMixin


class RSMApp(RSMWorkflowMixin, tk.Tk):
    """Main desktop GUI window for SuperRSM."""

    def __init__(self, async_tasks: bool = True):
        super().__init__()
        self.title("Super RSM — Response Surface Optimization & Visualization")
        self.geometry("1160x820")
        self.minsize(940, 680)

        self.fonts = configure_ttk_styles(self)
        self.async_tasks = async_tasks
        self.state = AppState()
        self.controller = AppController(self, self, self.state)
        self.plot_config_win: Optional[PlotConfigDialog] = None

        self._build_layout()
        self.state.add_status_listener(lambda msg: self.status_var.set(msg))
        self.state.add_busy_listener(self._on_busy_changed)
        self.on_input_select()

    df = property(lambda self: self.state.df, lambda self, v: setattr(self.state, "df", v))
    result = property(lambda self: self.state.result, lambda self, v: setattr(self.state, "result", v))
    current_input_cols = property(lambda self: self.state.current_input_cols)
    current_output_col = property(lambda self: self.state.current_output_col)
    linear_constraints = property(lambda self: self.state.linear_constraints)
    eval_history = property(lambda self: self.state.eval_history)
    opt_params_dict = property(lambda self: self.state.opt_params_dict)

    def _build_layout(self) -> None:
        self.header_view = HeaderView(self, fonts=self.fonts)
        self.header_view.pack(fill=tk.X)

        main_frame = ttk.Frame(self, padding=(12, 10, 12, 6))
        main_frame.pack(fill=tk.BOTH, expand=True)

        self.file_bar = FileSourceBar(main_frame, on_browse=self.browse_file, on_reload=lambda: self.load_data(False))
        self.file_bar.pack(fill=tk.X, pady=(0, 8))
        self.file_path_var = self.file_bar.file_path_var

        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        left_pane = ttk.Frame(paned, padding=(0, 0, 6, 0))
        right_pane = ttk.Frame(paned, padding=(6, 0, 0, 0))
        paned.add(left_pane, weight=11)
        paned.add(right_pane, weight=14)

        self.data_view = DataView(
            left_pane,
            on_input_select=self.on_input_select,
            on_output_select=self._on_output_selected,
            on_select_all=self.select_all_inputs,
            on_clear_selection=self.clear_input_selection,
            fonts=self.fonts,
        )
        self.data_view.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        self.input_listbox = self.data_view.input_listbox
        self.output_combo = self.data_view.output_combo

        self.model_view = ModelConfigView(
            left_pane, on_fit=self.fit_model, on_settings_changed=self._check_fit_settings_staleness, fonts=self.fonts
        )
        self.model_view.pack(fill=tk.X, pady=(0, 8))
        self.method_var = self.model_view.method_var
        self.test_size_var = self.model_view.test_size_var

        self.bounds_view = BoundsView(
            left_pane,
            on_goal_change=self._on_opt_goal_change,
            on_fill_from_data=self.fill_bounds_from_data,
            on_clear_bounds=self.clear_bounds_entries,
        )
        self.bounds_view.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        self.opt_goal_var = self.bounds_view.opt_goal_var
        self.bound_entries = self.bounds_view.bound_entries

        self.constraints_view = ConstraintsView(
            left_pane,
            on_add=self.add_linear_constraint,
            on_edit=self.edit_linear_constraint,
            on_delete=self.delete_linear_constraint,
            on_clear=self.clear_linear_constraints,
        )
        self.constraints_view.pack(fill=tk.X, pady=(0, 8))
        self.constraints_tree = self.constraints_view.constraints_tree

        run_frame = ttk.Frame(left_pane)
        run_frame.pack(fill=tk.X, pady=(2, 0))
        run_frame.columnconfigure(0, weight=3)
        run_frame.columnconfigure(1, weight=2)
        self.run_btn = ttk.Button(
            run_frame, text="▶  Run Optimization", style="Primary.TButton", command=self.run_optimization, state="disabled"
        )
        self.run_btn.grid(row=0, column=0, sticky=tk.EW, padx=(0, 5))
        self.plot_config_btn = ttk.Button(
            run_frame, text="⚙  Configure Plot...", style="Secondary.TButton", command=self.open_plot_config, state="disabled"
        )
        self.plot_config_btn.grid(row=0, column=1, sticky=tk.EW, padx=(5, 0))

        self.kpi_strip = KPIStripView(right_pane, fonts=self.fonts)
        self.kpi_strip.pack(fill=tk.X, pady=(0, 8))
        self.kpi_r2 = self.kpi_strip.kpi_r2
        self.kpi_rmse = self.kpi_strip.kpi_rmse
        self.kpi_opt = self.kpi_strip.kpi_opt
        self.kpi_status = self.kpi_strip.kpi_status

        self.results_view = ResultsView(
            right_pane,
            on_copy_report=self.copy_results_to_clipboard,
            on_eval_point=self.evaluate_custom_point,
            on_fill_eval_optimal=self.fill_eval_from_optimal,
            on_fill_eval_mean=self.fill_eval_from_mean,
            on_clear_eval=self.clear_eval_entries,
            on_copy_history=self.copy_eval_history,
            on_clear_history=self.clear_eval_history,
            on_history_double_click=self._on_eval_history_double_click,
            fonts=self.fonts,
        )
        self.results_view.pack(fill=tk.BOTH, expand=True)
        self.results_text = self.results_view.results_text
        self.eval_entries = self.results_view.eval_entries
        self.opt_params_tree = self.results_view.opt_params_tree
        self.constraint_eval_tree = self.results_view.constraint_eval_tree
        self.eval_history_tree = self.results_view.eval_history_tree

        status_bar = tk.Frame(
            self, bg=PALETTE["bg_card"], highlightbackground=PALETTE["border"], highlightthickness=1, padx=12, pady=4
        )
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_var = tk.StringVar(value=self.state.status_message)
        tk.Label(
            status_bar, textvariable=self.status_var, bg=PALETTE["bg_card"], fg=PALETTE["text_secondary"], font=self.fonts["small"], anchor=tk.W
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _on_busy_changed(self, busy: bool, message: str) -> None:
        self.model_view.fit_btn.config(state="disabled" if busy else "normal")
        state_val = "normal" if (self.state.result is not None and not busy) else "disabled"
        self.run_btn.config(state=state_val)
        self.plot_config_btn.config(state=state_val)
        self.results_view.eval_run_btn.config(state=state_val)

    def show_error(self, title: str, message: str) -> None:
        messagebox.showerror(title, message, parent=self)

    def browse_file(self) -> None:
        filepath = filedialog.askopenfilename(
            filetypes=[("CSV Files", "*.csv"), ("Excel Files", "*.xlsx *.xls"), ("All Files", "*.*")]
        )
        if filepath:
            self.file_path_var.set(filepath)
            self.load_data(show_popup=False)

    def load_data(self, show_popup: bool = False) -> None:
        filepath = self.file_path_var.get()
        if not filepath:
            messagebox.showwarning("Warning", "Please select a file first.", parent=self)
            return
        try:
            self.state.df = pd.read_csv(filepath) if filepath.lower().endswith(".csv") else pd.read_excel(filepath)
            self.state.filepath = filepath
            columns = list(self.state.df.columns)
            self.data_view.set_columns(columns)
            self.state.linear_constraints.clear()
            self.constraints_view.refresh(self.state.linear_constraints)
            self.clear_eval_history()
            self._invalidate_fitted_model("Dataset loaded — select columns and click 'Fit Surrogate Model'.")
            self.on_input_select()
            filename = Path(filepath).name
            self.header_view.set_dataset_status(filename, len(self.state.df), len(columns))
            self.state.set_status(
                f"Loaded '{filename}' ({len(self.state.df)} rows, {len(columns)} columns). Select input factors and target output."
            )
            if show_popup:
                messagebox.showinfo("Success", f"Loaded data with {len(self.state.df)} rows and {len(columns)} columns.", parent=self)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load data: {e!s}", parent=self)

    def _get_current_fit_signature(self) -> Optional[Tuple[Any, ...]]:
        if self.state.df is None:
            return None
        try:
            hparams = tuple(sorted(self.model_view.get_hyperparameters().items()))
            test_size = round(float(self.test_size_var.get()), 6)
        except Exception:
            return None
        return (
            id(self.state.df),
            tuple(self.data_view.get_selected_inputs()),
            self.data_view.get_selected_output(),
            self.method_var.get(),
            hparams,
            test_size,
        )

    def _check_fit_settings_staleness(self) -> None:
        if self.state.result is None or self.state.fitted_model_signature is None:
            return
        if self._get_current_fit_signature() != self.state.fitted_model_signature:
            self.model_view.fit_status_var.set(
                f"⚠ Settings changed (Active: {self.state.result.method}, R²={self.state.result.R_sq:.4f}) — click Fit to update."
            )
            self.model_view.fit_status_lbl.config(fg=PALETTE["warning"])
        else:
            self.model_view.fit_status_var.set(f"✓ Fitted: {self.state.result.method} (R² = {self.state.result.R_sq:.4f})")
            self.model_view.fit_status_lbl.config(fg=PALETTE["success"])

    def _invalidate_fitted_model(self, reason_msg: str = "Model not fitted yet.") -> None:
        self.state.invalidate_model()
        self.model_view.fit_status_var.set(reason_msg)
        self.model_view.fit_status_lbl.config(fg=PALETTE["text_muted"])
        self.run_btn.config(state="disabled")
        self.plot_config_btn.config(state="disabled")
        self.results_view.eval_run_btn.config(state="disabled")
        self.results_view.eval_pred_var.set("Predicted Output:  —")
        self.results_view.eval_unc_var.set("Fit a surrogate model to evaluate predictions at custom parameter combinations.")
        self.kpi_strip.reset_all()

    def _on_opt_goal_change(self) -> None:
        is_max = self.opt_goal_var.get() == "Maximize"
        self.kpi_opt.set_title("MAX OUTPUT VALUE" if is_max else "MIN OUTPUT VALUE")
        self.results_view.opt_table_hdr_var.set(
            f"Optimized Input Parameters ({'Maximizing' if is_max else 'Minimizing'} Target Output)"
        )
        self._update_column_selection_hint()

    def _on_output_selected(self) -> None:
        output_col = self.data_view.get_selected_output()
        changed = False
        for idx in list(self.input_listbox.curselection()):
            if self.input_listbox.get(idx) == output_col:
                self.input_listbox.selection_clear(idx)
                changed = True
        if changed:
            self.on_input_select()
        else:
            if self.state.result is not None and output_col != self.state.current_output_col:
                self._invalidate_fitted_model("Target output changed — click 'Fit Surrogate Model'.")
            self._update_column_selection_hint()

    def _update_column_selection_hint(self) -> None:
        n_in = len(self.input_listbox.curselection())
        out_col = self.data_view.get_selected_output()
        goal = self.opt_goal_var.get()
        if self.state.df is None:
            self.data_view.col_selection_hint_var.set(f"Load a dataset to populate columns.\nGoal: {goal} Target Output.")
        else:
            out_txt = f"'{out_col}'" if out_col else "None selected"
            self.data_view.col_selection_hint_var.set(f"Selected: {n_in} input factor(s)\nTarget: {out_txt} ({goal})")

    def select_all_inputs(self) -> None:
        if self.state.df is None:
            return
        output_col = self.data_view.get_selected_output()
        self.input_listbox.selection_clear(0, tk.END)
        for i in range(self.input_listbox.size()):
            if self.input_listbox.get(i) != output_col:
                self.input_listbox.selection_set(i)
        self.on_input_select()

    def clear_input_selection(self) -> None:
        self.input_listbox.selection_clear(0, tk.END)
        self.on_input_select()

    def on_input_select(self) -> None:
        current_cols = self.data_view.get_selected_inputs()
        if current_cols != self.state.previous_input_cols and self.state.result is not None:
            self._invalidate_fitted_model("Input factors changed — click 'Fit Surrogate Model'.")
        if self.state.linear_constraints and set(current_cols) != set(self.state.previous_input_cols):
            self.state.linear_constraints.clear()
            self.constraints_view.refresh(self.state.linear_constraints)
        self.state.previous_input_cols = current_cols
        self._update_column_selection_hint()
        self.bounds_view.rebuild_for_columns(current_cols, self.state.get_col_range_str)
        self.results_view.rebuild_eval_inputs(current_cols, self.state.get_col_range_str, self.state.get_col_mean_str)


RSMGui = RSMApp


def main() -> int:
    app = RSMApp()
    app.mainloop()
    return 0
