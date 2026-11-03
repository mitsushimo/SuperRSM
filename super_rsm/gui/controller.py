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
from super_rsm.core.reporting import format_full_report_markdown, format_full_report_text
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
        try:
            if callback is not None:
                callback(result)
        finally:
            self.state.set_busy(False)

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
        split_by_groups: bool = False,
    ) -> RSMResult:
        """Fit surrogate model via headless core pipeline."""
        return rsm_fromDF(
            df=df,
            input_columns=input_cols,
            output_column=output_col,
            method=method,
            test_size=test_size,
            split_by_groups=split_by_groups,
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
        return format_full_report_text(result, input_cols, output_col, last_opt_report_text)

    @staticmethod
    def format_markdown_report(
        result: Optional[RSMResult],
        input_cols: List[str],
        output_col: str,
        last_opt_report_text: str = "",
    ) -> str:
        """Format complete diagnostic report in Markdown format."""
        return format_full_report_markdown(result, input_cols, output_col, last_opt_report_text)

