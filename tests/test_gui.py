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

from super_rsm.core.pipeline import rsm_fromDF
from super_rsm.gui.controller import AppController
from super_rsm.gui.dialogs.constraint_dialog import format_linear_expression
from super_rsm.gui.state import AppState
from super_rsm.gui.styles.palette import PALETTE, COMMON_CMAPS
from super_rsm.gui.styles.theme import get_ui_fonts


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

