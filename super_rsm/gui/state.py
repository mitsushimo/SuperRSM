"""
super_rsm/gui/state.py

Centralized reactive state container for SuperRSM GUI.
Decouples domain state from Tkinter widgets for headless unit testing.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
import pandas as pd

from super_rsm.core.result import RSMResult


@dataclass
class AppState:
    """Centralized state container holding active dataset, fitted model, and UI status."""

    df: Optional[pd.DataFrame] = None
    filepath: str = ""
    current_input_cols: List[str] = field(default_factory=list)
    previous_input_cols: List[str] = field(default_factory=list)
    current_output_col: str = ""
    result: Optional[RSMResult] = None
    fitted_model_signature: Optional[Tuple[Any, ...]] = None
    last_opt_report_text: str = ""
    opt_params_dict: Dict[str, float] = field(default_factory=dict)
    linear_constraints: List[Dict[str, Any]] = field(default_factory=list)
    eval_history: List[Dict[str, Any]] = field(default_factory=list)

    is_busy: bool = False
    busy_message: str = ""
    status_message: str = "Ready — Browse and select a CSV or Excel dataset to begin."

    _busy_listeners: List[Callable[[bool, str], None]] = field(default_factory=list, repr=False)
    _status_listeners: List[Callable[[str], None]] = field(default_factory=list, repr=False)

    def add_busy_listener(self, callback: Callable[[bool, str], None]) -> None:
        self._busy_listeners.append(callback)

    def add_status_listener(self, callback: Callable[[str], None]) -> None:
        self._status_listeners.append(callback)

    def set_busy(self, busy: bool, message: str = "") -> None:
        self.is_busy = busy
        self.busy_message = message if busy else ""
        if busy and message:
            self.set_status(message)
        for listener in self._busy_listeners:
            listener(self.is_busy, self.busy_message)

    def set_status(self, message: str) -> None:
        self.status_message = message
        for listener in self._status_listeners:
            listener(self.status_message)

    def invalidate_model(self) -> None:
        """Clear active fitted model and downstream optimization results."""
        self.result = None
        self.current_input_cols = []
        self.current_output_col = ""
        self.fitted_model_signature = None
        self.last_opt_report_text = ""
        self.opt_params_dict.clear()

    def get_col_range_str(self, col_name: str) -> str:
        """Format [min, max] range string for a DataFrame column."""
        if self.df is None or col_name not in self.df.columns:
            return "—"
        series = pd.to_numeric(self.df[col_name], errors="coerce").dropna()
        if series.empty:
            return "—"
        return f"[{float(series.min()):.4g}, {float(series.max()):.4g}]"

    def get_col_mean_str(self, col_name: str) -> str:
        """Format mean value string for a DataFrame column."""
        if self.df is None or col_name not in self.df.columns:
            return "0"
        series = pd.to_numeric(self.df[col_name], errors="coerce").dropna()
        if series.empty:
            return "0"
        return f"{float(series.mean()):.6g}"

