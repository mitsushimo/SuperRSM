"""
tests/test_gui.py

Unit and architectural tests for Layer 4 (super_rsm.gui):
- AppState reactive state container
- AppController async concurrency, task ID tracking, and window-close guards
- Report formatting (including PolynomialOLS ANOVA and p-values) and constraint verification
- Linear constraint expression formatting
- Architectural DAG and 350-line module size verification across the entire super_rsm package
"""

import ast
from pathlib import Path
import time
import numpy as np
import pandas as pd
import pytest

from super_rsm.core.persistence import load_rsm_project, save_rsm_project
from super_rsm.core.pipeline import rsm_fromDF
from super_rsm.core.reporting import format_full_report_markdown
from super_rsm.gui.components.report_viewer import compile_markdown_to_html
from super_rsm.gui.controller import AppController
from super_rsm.gui.dialogs.constraint_dialog import format_linear_expression
from super_rsm.gui.state import AppState
from super_rsm.gui.styles.palette import PALETTE, COMMON_CMAPS
from super_rsm.gui.styles.theme import get_ui_fonts
from super_rsm.visualization.diagnostic_plots import (
    build_report_figures,
    figure_to_png_bytes,
    save_figure,
)


# =============================================================================
# 1. AppState Tests
# =============================================================================

def test_app_state_listeners_and_column_helpers():
    state = AppState()
    busy_events = []
    status_events = []

    state.add_busy_listener(lambda b, m: busy_events.append((b, m)))
    state.add_status_listener(lambda s: status_events.append(s))

    state.set_busy(True, "Fitting model...")
    assert state.is_busy is True
    assert state.busy_message == "Fitting model..."
    assert busy_events[-1] == (True, "Fitting model...")
    assert status_events[-1] == "Fitting model..."

    state.set_busy(False)
    assert state.is_busy is False
    assert state.busy_message == ""

    df = pd.DataFrame({"x1": [1.0, 2.0, 3.0], "x2": [10.0, 20.0, 30.0], "y": [5.0, 6.0, 7.0]})
    state.df = df
    assert state.get_col_range_str("x1") == "[1, 3]"
    assert state.get_col_mean_str("x2") == "20"
    assert state.get_col_range_str("missing") == "—"
    assert state.get_col_mean_str("missing") == "0"


# =============================================================================
# 2. AppController Concurrency & Lifecycle Tests
# =============================================================================

class DummyRoot:
    """Lightweight mock of tk.Tk for deterministic testing of _run_async."""

    def __init__(self):
        self.scheduled = []
        self.destroyed = False

    def protocol(self, name, fn):
        self._close_fn = fn

    def after(self, delay_ms, callback):
        self.scheduled.append(callback)

    def flush_scheduled(self):
        while self.scheduled:
            cb = self.scheduled.pop(0)
            cb()

    def destroy(self):
        self.destroyed = True


def test_controller_run_async_synchronous_and_threaded():
    root = DummyRoot()
    state = AppState()
    ctrl = AppController(root, None, state)

    results = []
    arr = np.array([1.0, 2.0, 3.0])

    def mutate_and_sum(x):
        x[0] = 999.0  # Should only mutate the defensive snapshot!
        return float(np.sum(x))

    # Synchronous execution
    ctrl._run_async(
        mutate_and_sum,
        arr,
        on_success=lambda r: results.append(r),
        synchronous=True,
    )
    assert arr[0] == 1.0  # Original array untouched due to defensive snapshotting
    assert results == [1004.0]
    assert state.is_busy is False

    # Threaded execution
    threaded_res = []
    ctrl._run_async(
        lambda a, b: a + b,
        10,
        25,
        on_success=lambda r: threaded_res.append(r),
        synchronous=False,
    )
    deadline = time.time() + 2.0
    while not root.scheduled and time.time() < deadline:
        time.sleep(0.01)
    root.flush_scheduled()
    assert threaded_res == [35]
    assert state.is_busy is False


def test_controller_stale_task_rejection_and_window_close_guard():
    root = DummyRoot()
    state = AppState()
    ctrl = AppController(root, None, state)

    called = []
    # Simulate stale task ID
    ctrl._current_task_id = 5
    ctrl._handle_success(4, lambda r: called.append(r), "stale")
    assert called == []

    # Current task ID succeeds
    ctrl._handle_success(5, lambda r: called.append(r), "fresh")
    assert called == ["fresh"]

    # Window destruction guard prevents further execution or callbacks
    ctrl.on_closing()
    assert root.destroyed is True
    assert ctrl._run_async(lambda: 42, on_success=lambda r: called.append(r)) is False
    ctrl._handle_success(5, lambda r: called.append(r), "after_close")
    assert called == ["fresh"]


# =============================================================================
# 3. Report Formatting, Constraints & Expression Tests
# =============================================================================

def test_format_linear_expression():
    expr = format_linear_expression({"x1": 1.0, "x2": -2.5, "x3": 0.0}, "<=", 10.0)
    assert expr == "x1 - 2.5*x2 <= 10"

    expr2 = format_linear_expression({"x1": -1.0, "x2": 1.0}, "==", 0.0)
    assert expr2 == "-x1 + x2 == 0"


def test_controller_report_formatting_and_constraint_evaluation():
    rng = np.random.default_rng(42)
    x1 = rng.uniform(0, 5, 40)
    x2 = rng.uniform(0, 5, 40)
    y = (x1 - 2.0) ** 2 + (x2 - 3.0) ** 2 + 1.0
    df = pd.DataFrame({"x1": x1, "x2": x2, "y": y})

    result = rsm_fromDF(df, ["x1", "x2"], "y", method="Polynomial OLS", degree_fit=2)
    report = AppController.format_full_report(result, ["x1", "x2"], "y")

    assert "=== Surrogate Model Fit Summary ===" in report
    assert "Polynomial OLS" in report
    assert "Adjusted R²:" in report
    assert "ANOVA Table:" in report
    assert "Model Coefficients:" in report
    assert "Training Set Fit:" in report

    # Verify RidgeCV, Bayesian Ridge, ElasticNetCV, and SVR report formatting with split_by_groups=True
    for method in ["RidgeCV", "Bayesian Ridge", "ElasticNetCV", "SVR"]:
        res_m = AppController.execute_fit(df, ["x1", "x2"], "y", method, 0.2, {}, split_by_groups=True)
        rep_m = AppController.format_full_report(res_m, ["x1", "x2"], "y")
        assert method in rep_m
        assert "Grouped by Unique Input Combinations" in rep_m
        assert "ANOVA Table:" in rep_m
        assert "Model Diagnostics & Hyperparameters:" in rep_m

    raw_constraints = [
        {"coeffs": {"x1": 1.0, "x2": 1.0}, "operator": "<=", "bound": 4.0, "expression_str": "x1 + x2 <= 4"},
    ]
    specs = AppController.build_constraint_specs(raw_constraints)
    assert len(specs) == 1
    opt_res = result.optimize(bounds=[(0.0, 5.0), (0.0, 5.0)], constraints=specs, maximize=False)

    n_violated, rows, lines = AppController.evaluate_constraints_at_point(
        raw_constraints, ["x1", "x2"], opt_res.params
    )
    assert n_violated == 0
    assert rows[0][3] == "Satisfied"


# =============================================================================
# 4. Architectural Cohesion & 350-Line Ceiling Verification
# =============================================================================

def test_package_file_sizing_and_layer_boundaries():
    pkg_root = Path(__file__).resolve().parent.parent / "super_rsm"
    py_files = list(pkg_root.rglob("*.py"))
    assert len(py_files) >= 24

    for py_file in py_files:
        lines = py_file.read_text(encoding="utf-8").splitlines()
        assert len(lines) <= 355, f"{py_file.name} exceeds size ceiling ({len(lines)} lines)"

        # Verify that common, models, and core never import tkinter or matplotlib at module level
        rel_parts = py_file.relative_to(pkg_root).parts
        if rel_parts[0] in ("common", "models", "core"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
            for node in tree.body:
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    mod = getattr(node, "module", "") or ""
                    names = [a.name for a in node.names]
                    for token in [mod, *names]:
                        assert not token.startswith(("tkinter", "matplotlib", "seaborn")), (
                            f"Headless violation in {py_file}: top-level import of '{token}'"
                        )


def test_styles_and_fonts_headless():
    fonts = get_ui_fonts()
    assert "title" in fonts and "mono" in fonts
    assert "accent" in PALETTE
    assert "viridis" in COMMON_CMAPS


def test_controller_callback_runs_before_busy_false():
    """Ensure state.result updated inside on_success is visible to busy_listeners when busy becomes False."""
    root = DummyRoot()
    state = AppState()
    ctrl = AppController(root, None, state)

    observed_results_on_unbusy = []
    state.add_busy_listener(lambda busy, _msg: observed_results_on_unbusy.append(state.result) if not busy else None)

    def fake_fit():
        return "fitted_model_object"

    def on_fit_done(res):
        state.result = res

    ctrl._run_async(fake_fit, on_success=on_fit_done, synchronous=True)
    assert observed_results_on_unbusy == ["fitted_model_object"]


# =============================================================================
# 5. Markdown/HTML Report, Inline Diagnostic Plots & .rsm Persistence Tests
# =============================================================================

def test_markdown_and_html_report_with_inline_diagnostic_plots(tmp_path):
    rng = np.random.default_rng(123)
    x1 = rng.uniform(0, 5, 40)
    x2 = rng.uniform(0, 5, 40)
    y = (x1 - 2.0) ** 2 + (x2 - 3.0) ** 2 + 1.0 + rng.normal(0, 0.05, 40)
    df = pd.DataFrame({"x1": x1, "x2": x2, "y": y})

    result = rsm_fromDF(df, ["x1", "x2"], "y", method="Polynomial OLS", degree_fit=2)
    md_report = format_full_report_markdown(result, ["x1", "x2"], "y")

    assert "# Surrogate Model Fit Summary" in md_report
    assert "- **Regression Method**: **Polynomial OLS**" in md_report
    assert "| Term | Estimate | Std. Error | t-Value | p-Value | Rel. Importance | Sig. |" in md_report
    assert "| Source | SS | df | MS | F-Value | p-Value |" in md_report
    assert "<!-- PLOT:parity -->" in md_report
    assert "<!-- PLOT:significance -->" in md_report
    assert "<!-- PLOT:importance -->" in md_report

    figures = build_report_figures(result)
    assert set(figures.keys()) == {"parity", "significance", "importance"}
    for key, fig in figures.items():
        png_bytes = figure_to_png_bytes(fig)
        assert png_bytes.startswith(b"\x89PNG")
        out_img = tmp_path / f"{key}.png"
        save_figure(fig, str(out_img), dpi=150)
        assert out_img.exists() and out_img.stat().st_size > 1000

    html_doc = compile_markdown_to_html(md_report, figures=figures)
    assert "<table>" in html_doc
    assert "<strong>Polynomial OLS</strong>" in html_doc
    assert "data:image/png;base64," in html_doc
    assert 'href="save_plot:significance"' in html_doc
    assert 'href="save_plot:importance"' in html_doc
    assert 'href="save_plot:parity"' in html_doc


def test_rsm_project_save_and_load_survives_deleted_source_csv(tmp_path):
    csv_path = tmp_path / "original_data.csv"
    df_orig = pd.DataFrame({
        "x1": [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 1.5, 2.5, 3.5, 4.5],
        "x2": [5.0, 4.0, 3.0, 2.0, 1.0, 0.0, 2.5, 3.5, 1.5, 0.5],
        "y": [26.0, 13.0, 6.0, 5.0, 10.0, 21.0, 7.5, 5.5, 8.5, 16.5],
    })
    df_orig.to_csv(csv_path, index=False)

    loaded_df = pd.read_csv(csv_path)
    result = rsm_fromDF(loaded_df, ["x1", "x2"], "y", method="RidgeCV", degree_fit=2, test_size=0.2)
    pred_before = result.evaluate_point([3.0, 2.0], return_std=False)

    state_dict = {
        "original_filepath": str(csv_path),
        "selected_inputs": ["x1", "x2"],
        "selected_output": "y",
        "input_cols": ["x1", "x2"],
        "output_col": "y",
        "method": "RidgeCV",
        "test_size": 0.2,
        "split_by_groups": True,
        "hyperparameters": {"degree_fit": 2, "alphas_count": 13, "cv": 5},
        "opt_goal": "Minimize",
        "bounds": {"x1": ["0", "5"], "x2": ["0", "5"]},
        "linear_constraints": [
            {"coeffs": {"x1": 1.0, "x2": 1.0}, "operator": "<=", "bound": 6.0, "expression_str": "x1 + x2 <= 6"}
        ],
        "opt_params_dict": {"x1": 2.5, "x2": 3.5},
        "last_opt_report_text": "## RSM Optimization Results",
        "eval_entries": {"x1": "3.0", "x2": "2.0"},
        "eval_history": [
            {"id": 1, "params_dict": {"x1": 3.0, "x2": 2.0}, "inputs_str": "x1=3, x2=2", "pred_val": pred_before, "std_val": None, "pred_str": f"{pred_before:.6g}", "std_str": "—"}
        ],
    }

    rsm_path = tmp_path / "saved_work.rsm"
    saved_file = save_rsm_project(str(rsm_path), df=loaded_df, state_dict=state_dict, result=result)
    assert saved_file.exists() and saved_file.suffix == ".rsm"

    # Delete the original CSV file from disk to verify self-contained .rsm resilience
    csv_path.unlink()
    assert not csv_path.exists()

    restored = load_rsm_project(str(saved_file))
    assert restored["df"] is not None
    pd.testing.assert_frame_equal(restored["df"], df_orig)
    assert restored["result"] is not None
    pred_after = restored["result"].evaluate_point([3.0, 2.0], return_std=False)
    assert pred_after == pytest.approx(pred_before, rel=1e-6)
    assert restored["state"]["bounds"] == {"x1": ["0", "5"], "x2": ["0", "5"]}
    assert len(restored["state"]["linear_constraints"]) == 1
    assert len(restored["state"]["eval_history"]) == 1


def test_rsm_app_menubar_and_full_project_roundtrip(tmp_path, monkeypatch):
    import tkinter as tk
    from tkinter import messagebox
    from super_rsm.gui.app import RSMApp

    errors = []
    monkeypatch.setattr(messagebox, "showerror", lambda title, msg, **kw: errors.append((title, msg)))
    monkeypatch.setattr(messagebox, "showwarning", lambda title, msg, **kw: errors.append((title, msg)))
    monkeypatch.setattr(messagebox, "showinfo", lambda title, msg, **kw: None)

    try:
        app = RSMApp(async_tasks=False)
        app.withdraw()
    except tk.TclError:
        pytest.skip("Tkinter display unavailable in this environment.")

    rsm_file = tmp_path / "full_gui_session.rsm"
    csv_file = tmp_path / "temp_exp.csv"
    try:
        # 1. Verify top menu bar has only "File" with "Save", "Save as", "Load"
        assert hasattr(app, "menubar") and hasattr(app, "file_menu")
        top_labels = [
            app.menubar.entrycget(i, "label")
            for i in range(app.menubar.index("end") + 1)
        ]
        assert top_labels == ["File"]
        file_items = [
            app.file_menu.entrycget(i, "label")
            for i in range(app.file_menu.index("end") + 1)
        ]
        assert file_items == ["Save", "Save as", "Load"]

        # 2. Create dataset, load into app, fit, optimize, evaluate, and save .rsm
        rng = np.random.default_rng(7)
        x1 = rng.uniform(0.0, 6.0, 30)
        x2 = rng.uniform(0.0, 6.0, 30)
        y = (x1 - 2.0) ** 2 + (x2 - 3.0) ** 2 + 5.0
        pd.DataFrame({"x1": x1, "x2": x2, "y": y}).to_csv(csv_file, index=False)

        app.file_path_var.set(str(csv_file))
        app.load_data(show_popup=False)
        app.output_combo.set("y")
        app.select_all_inputs()
        app.method_var.set("Polynomial OLS")
        app.model_view._refresh_metadata_ui()
        app.fit_model(synchronous=True)
        app.fill_bounds_from_data()
        app.run_optimization(synchronous=True)
        app.fill_eval_from_optimal()
        app.evaluate_custom_point()

        assert app.save_project(filepath=str(rsm_file)) is True, f"Errors: {errors}"
        assert rsm_file.exists()
        assert errors == []
    finally:
        app.controller.on_closing()

    # Delete the original CSV file
    csv_file.unlink()
    assert not csv_file.exists()

    # 3. Load into a fresh RSMApp instance and verify state restoration
    app2 = RSMApp(async_tasks=False)
    app2.withdraw()
    try:
        assert app2.load_project(filepath=str(rsm_file)) is True, f"Errors: {errors}"
        assert errors == []
        assert app2.state.df is not None and len(app2.state.df) == 30
        assert app2.data_view.get_selected_inputs() == ["x1", "x2"]
        assert app2.data_view.get_selected_output() == "y"
        assert app2.state.result is not None and app2.state.result.method == "Polynomial OLS"
        assert len(app2.state.eval_history) == 1
        assert "# Surrogate Model Fit Summary" in app2.results_view.report_viewer.get_markdown_text()
        assert "data:image/png;base64," in app2.results_view.report_viewer.get_html_text()
    finally:
        app2.controller.on_closing()




