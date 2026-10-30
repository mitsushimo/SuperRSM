"""
super_rsm/gui/views/model_config_view.py

Step 3: Model selection and dynamic hyperparameter configuration view.
Introspects ModelRegistry.get_metadata() to dynamically build controls for any registered model.
"""

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Dict, Optional

from super_rsm.gui.components.param_form import DynamicParamForm
from super_rsm.gui.styles.palette import PALETTE
from super_rsm.gui.styles.theme import get_ui_fonts
from super_rsm.models.registry import ModelRegistry, get_supported_methods


class ModelConfigView(ttk.LabelFrame):
    """Step 3: Surrogate model selection, dynamic parameters, test split, and fit trigger."""

    def __init__(
        self,
        parent: tk.Misc,
        on_fit: Callable[[], Any],
        on_settings_changed: Optional[Callable[[], None]] = None,
        fonts: Optional[Dict[str, tuple]] = None,
    ):
        super().__init__(parent, text="3. Model & Fit Settings", padding=(10, 8))
        self.fonts = fonts or get_ui_fonts()
        self.on_settings_changed = on_settings_changed

        top_row = ttk.Frame(self, style="Card.TFrame")
        top_row.pack(fill=tk.X)

        ttk.Label(top_row, text="Method:", style="CardBold.TLabel").pack(side=tk.LEFT, padx=(0, 5))
        methods = get_supported_methods()
        default_method = "Gaussian Process" if "Gaussian Process" in methods else (methods[0] if methods else "")
        self.method_var = tk.StringVar(value=default_method)
        self.method_combo = ttk.Combobox(
            top_row,
            textvariable=self.method_var,
            values=methods,
            state="readonly",
            width=20,
        )
        self.method_combo.pack(side=tk.LEFT, padx=(0, 12))
        self.method_combo.bind("<<ComboboxSelected>>", self._on_method_selected)

        ttk.Label(top_row, text="Test Ratio:", style="CardBold.TLabel").pack(side=tk.LEFT, padx=(0, 5))
        self.test_size_var = tk.DoubleVar(value=0.20)
        self.test_size_spin = ttk.Spinbox(
            top_row,
            from_=0.01,
            to=0.99,
            increment=0.05,
            textvariable=self.test_size_var,
            width=5,
        )
        self.test_size_spin.pack(side=tk.LEFT)

        # Dynamic Hyperparameter Form (populated from ModelRegistry.get_metadata)
        self.param_form = DynamicParamForm(self, on_change=self._notify_change)
        self.param_form.pack(fill=tk.X, pady=(6, 2))

        self.method_hint_var = tk.StringVar()
        ttk.Label(
            self,
            textvariable=self.method_hint_var,
            style="CardMuted.TLabel",
            wraplength=440,
        ).pack(anchor=tk.W, pady=(2, 6))

        fit_action_row = ttk.Frame(self, style="Card.TFrame")
        fit_action_row.pack(fill=tk.X)

        self.fit_btn = ttk.Button(
            fit_action_row,
            text="▶  Fit Surrogate Model",
            style="Primary.TButton",
            command=on_fit,
        )
        self.fit_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.fit_status_var = tk.StringVar(value="Model not fitted yet.")
        self.fit_status_lbl = tk.Label(
            fit_action_row,
            textvariable=self.fit_status_var,
            bg=PALETTE["bg_card"],
            fg=PALETTE["text_muted"],
            font=self.fonts["small_bold"],
            anchor=tk.W,
        )
        self.fit_status_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._refresh_metadata_ui()
        self.test_size_var.trace_add("write", lambda *args: self._notify_change())

    def refresh_methods(self) -> None:
        """Refresh combobox list if new models were registered dynamically."""
        methods = get_supported_methods()
        self.method_combo["values"] = methods
        if self.method_var.get() not in methods and methods:
            self.method_var.set(methods[0])
        self._refresh_metadata_ui()

    def _on_method_selected(self, event: Optional[tk.Event] = None) -> None:
        self._refresh_metadata_ui()
        self._notify_change()

    def _refresh_metadata_ui(self) -> None:
        method = self.method_var.get()
        if not method or not ModelRegistry.contains(method):
            return
        meta = ModelRegistry.get_metadata(method)
        self.method_hint_var.set(meta.description)
        self.param_form.populate_for_metadata(meta)

    def _notify_change(self) -> None:
        if self.on_settings_changed is not None:
            self.on_settings_changed()

    def get_hyperparameters(self) -> Dict[str, Any]:
        return self.param_form.get_hyperparameters()

