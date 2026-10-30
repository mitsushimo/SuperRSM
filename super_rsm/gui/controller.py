"""
super_rsm/gui/controller.py

AppController: coordinates GUI events, reactive AppState, report formatting,
and thread-safe asynchronous execution (_run_async) with window-destruction guards.
"""

import logging
import threading
import tkinter as tk
from typing import Any, Callable, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from super_rsm.common.config import ConstraintSpec
from super_rsm.common.types import ConstraintOperator
from super_rsm.core.pipeline import rsm_fromDF
from super_rsm.core.result import RSMResult
from super_rsm.gui.state import AppState

logger = logging.getLogger(__name__)


class AppController:
    """Presenter/Controller managing asynchronous execution and domain coordination."""

    def __init__(self, root: Optional[tk.Misc], app: Any, state: AppState):
        self.root = root
        self.app = app
        self.state = state
        self._current_task_id: int = 0
        self._is_shutting_down = threading.Event()

        if self.root is not None and hasattr(self.root, "protocol"):
            try:
                self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            except tk.TclError:
                pass

    def _run_async(
        self,
        task_fn: Callable[..., Any],
        *args: Any,
        on_success: Optional[Callable[[Any], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
        busy_message: str = "Processing...",
        synchronous: bool = False,
        **kwargs: Any,
    ) -> bool:
        """
        Execute a task in a daemon background thread (or synchronously when requested)
        with defensive array snapshotting, task ID tracking, and window-close guards.
        """
        if self._is_shutting_down.is_set():
            return False

        snap_args = [a.copy() if isinstance(a, (np.ndarray, pd.DataFrame)) else a for a in args]
        snap_kwargs = {
            k: (v.copy() if isinstance(v, (np.ndarray, pd.DataFrame)) else v)
            for k, v in kwargs.items()
        }

        self._current_task_id += 1
        task_id = self._current_task_id
        self.state.set_busy(True, busy_message)

        if synchronous or self.root is None:
            try:
                res = task_fn(*snap_args, **snap_kwargs)
                self._handle_success(task_id, on_success, res)
            except Exception as exc:
                self._handle_error(task_id, on_error, exc)
            return True

        def worker() -> None:
            try:
                result = task_fn(*snap_args, **snap_kwargs)
                if not self._is_shutting_down.is_set():
                    try:
                        self.root.after(0, lambda: self._handle_success(task_id, on_success, result))
                    except (tk.TclError, RuntimeError):
                        pass
            except Exception as exc:
                logger.exception("Async worker task failed with exception.")
                if not self._is_shutting_down.is_set():
                    try:
                        self.root.after(0, lambda e=exc: self._handle_error(task_id, on_error, e))
                    except (tk.TclError, RuntimeError):
                        pass

        thread = threading.Thread(target=worker, daemon=True, name=f"SuperRSM-Worker-{task_id}")
        thread.start()
        return True

    def _handle_success(self, task_id: int, callback: Optional[Callable[[Any], None]], result: Any) -> None:
        if self._is_shutting_down.is_set() or task_id != self._current_task_id:
            return
        self.state.set_busy(False)
        if callback is not None:
            callback(result)

    def _handle_error(self, task_id: int, callback: Optional[Callable[[Exception], None]], exc: Exception) -> None:
        if self._is_shutting_down.is_set() or task_id != self._current_task_id:
            return
        self.state.set_busy(False)
        if callback is not None:
            callback(exc)
        elif self.app is not None and hasattr(self.app, "show_error"):
            self.app.show_error("Execution Error", str(exc))

    def on_closing(self) -> None:
        """Set shutdown event so background workers never touch destroyed widgets."""
        self._is_shutting_down.set()
        if self.root is not None:
            try:
                self.root.destroy()
            except tk.TclError:
                pass

    # ------------------------------------------------------------------
    # Domain Task Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def execute_fit(
        df: pd.DataFrame,
        input_cols: List[str],
        output_col: str,
        method: str,
        test_size: float,
        hyperparameters: Dict[str, Any],
    ) -> RSMResult:
        """Fit surrogate model via headless core pipeline."""
        return rsm_fromDF(
            df=df,
            input_columns=input_cols,
            output_column=output_col,
            method=method,
            test_size=test_size,
            **hyperparameters,
        )

    @staticmethod
    def build_constraint_specs(raw_constraints: List[Dict[str, Any]]) -> Optional[List[ConstraintSpec]]:
        """Convert UI constraint dictionaries into domain ConstraintSpec DTOs."""
        if not raw_constraints:
            return None
        specs: List[ConstraintSpec] = []
        for c in raw_constraints:
            op = ConstraintOperator(c["operator"])
            specs.append(ConstraintSpec(coeffs=dict(c["coeffs"]), operator=op, bound=float(c["bound"])))
        return specs

    @staticmethod
    def evaluate_constraints_at_point(
        raw_constraints: List[Dict[str, Any]],
        input_cols: List[str],
        opt_params: np.ndarray,
        tol: float = 1e-4,
    ) -> Tuple[int, List[Tuple[int, str, float, str, str]], List[str]]:
        """
        Evaluate linear constraints at optimal parameter vector.
        Returns (n_violated, tree_rows, report_lines).
        """
        n_violated = 0
        tree_rows: List[Tuple[int, str, float, str, str]] = []
        report_lines: List[str] = []

        for i, c in enumerate(raw_constraints, 1):
            lhs_val = float(sum(c["coeffs"].get(col, 0.0) * val for col, val in zip(input_cols, opt_params)))
            op = c["operator"]
            b = float(c["bound"])
            if op == "<=":
                satisfied = lhs_val <= b + tol
            elif op == ">=":
                satisfied = lhs_val >= b - tol
            elif op == "==":
                satisfied = abs(lhs_val - b) <= tol
            else:
                satisfied = True

            if not satisfied:
                n_violated += 1
            status_str = "Satisfied" if satisfied else "VIOLATED"
            tag = "satisfied" if satisfied else "violated"
            tree_rows.append((i, c["expression_str"], lhs_val, status_str, tag))
            report_lines.append(
                f"  [{i}] {c['expression_str']}\n"
                f"      Evaluated LHS = {lhs_val:.6f} [{status_str}]\n"
            )
        return n_violated, tree_rows, report_lines

    @staticmethod
    def format_full_report(
        result: Optional[RSMResult],
        input_cols: List[str],
        output_col: str,
        last_opt_report_text: str = "",
    ) -> str:
        """Format complete diagnostic report including coefficients, formula, p-values, and ANOVA."""
        if result is None or not input_cols:
            return ""

        lines = [
            "=== Surrogate Model Fit Summary ===\n",
            f"Target Output Variable: {output_col}",
            f"Input Factors ({len(input_cols)}): {', '.join(input_cols)}",
            f"Regression Method: {result.method}",
            f"Coefficient of Determination (R²): {result.R_sq:.4f}",
        ]
        if result.metrics.adj_r2 is not None:
            lines.append(f"Adjusted R²: {result.metrics.adj_r2:.4f}")
        lines.append(f"Mean Squared Error (MSE): {result.MSE:.6f}")
        lines.append(f"Root Mean Squared Error (RMSE): {result.RMSE:.6f}")
        if result.metrics.aic is not None and result.metrics.bic is not None:
            lines.append(f"AIC: {result.metrics.aic:.2f}  |  BIC: {result.metrics.bic:.2f}")
        lines.append("")

        coeffs_dict = result.get_coefficients()
        if coeffs_dict:
            lines.append("Model Coefficients:")
            p_vals = result.metrics.term_p_values or {}
            t_stats = result.metrics.term_t_stats or {}
            for term, coeff in coeffs_dict.items():
                if term in p_vals and term in t_stats:
                    lines.append(f"  - {term}: {coeff:.6f}  (t = {t_stats[term]:.3f}, p = {p_vals[term]:.4g})")
                else:
                    lines.append(f"  - {term}: {coeff:.6f}")
            lines.append("")

        if getattr(result, "expression_text", None):
            lines.append(f"{result.expression_text}\n")

        if result.metrics.anova_table is not None:
            lines.append("ANOVA Table:")
            lines.append(result.metrics.anova_table.to_string(index=False))
            lines.append("")

        if last_opt_report_text:
            lines.append(last_opt_report_text.rstrip())

        return "\n".join(lines) + "\n"

