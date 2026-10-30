"""
super_rsm/gui/components/param_form.py

Dynamic hyperparameter form generator driven by ModelMetadata.hyperparameters.
Enables zero-code UI expansion when new regression models are registered.
"""

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Dict, List, Optional

from super_rsm.common.config import HyperparameterSpec, ModelMetadata


class DynamicParamForm(ttk.Frame):
    """
    Dynamically builds parameter input widgets (Spinbox, Combobox, Checkbutton, Entry)
    from a list of HyperparameterSpec declarations on a registered model's metadata.
    """

    def __init__(
        self,
        parent: tk.Misc,
        on_change: Optional[Callable[[], None]] = None,
    ):
        super().__init__(parent, style="Card.TFrame")
        self.on_change = on_change
        self._specs: Dict[str, HyperparameterSpec] = {}
        self._vars: Dict[str, tk.Variable] = {}
        self._widgets: Dict[str, tk.Widget] = {}

    def populate_for_metadata(self, metadata: ModelMetadata) -> None:
        """Rebuild parameter controls for the selected model's metadata."""
        for child in self.winfo_children():
            child.destroy()
        self._specs.clear()
        self._vars.clear()
        self._widgets.clear()

        if not metadata.hyperparameters:
            lbl = ttk.Label(
                self,
                text="Default configuration (no user-required hyperparameters).",
                style="CardMuted.TLabel",
            )
            lbl.pack(side=tk.LEFT, pady=2)
            return

        # Display primary hyperparameters in a clean inline/grid layout
        for idx, spec in enumerate(metadata.hyperparameters):
            self._specs[spec.name] = spec

            item_frame = ttk.Frame(self, style="Card.TFrame")
            item_frame.pack(side=tk.LEFT, padx=(0, 12), pady=2)

            lbl_text = f"{spec.display_name}:"
            ttk.Label(item_frame, text=lbl_text, style="CardBold.TLabel").pack(
                side=tk.LEFT, padx=(0, 4)
            )

            var, widget = self._create_control(item_frame, spec)
            self._vars[spec.name] = var
            self._widgets[spec.name] = widget
            widget.pack(side=tk.LEFT)

            if self.on_change is not None:
                var.trace_add("write", lambda *args: self.on_change())

    def _create_control(
        self, parent: ttk.Frame, spec: HyperparameterSpec
    ) -> tuple[tk.Variable, tk.Widget]:
        if spec.param_type is bool:
            var = tk.BooleanVar(value=bool(spec.default))
            widget = ttk.Checkbutton(parent, variable=var)
            return var, widget

        if spec.choices:
            var = tk.StringVar(value=str(spec.default))
            str_choices = [str(c) for c in spec.choices]
            widget = ttk.Combobox(
                parent,
                textvariable=var,
                values=str_choices,
                state="readonly",
                width=max(8, min(18, max(len(s) for s in str_choices) + 2)),
            )
            return var, widget

        if spec.param_type is int:
            var = tk.StringVar(value=str(spec.default))
            lo = int(spec.min_val) if spec.min_val is not None else 0
            hi = int(spec.max_val) if spec.max_val is not None else 10000
            step = int(spec.step) if spec.step is not None else 1
            widget = ttk.Spinbox(
                parent,
                from_=lo,
                to=hi,
                increment=step,
                textvariable=var,
                width=6,
            )
            return var, widget

        if spec.param_type is float:
            var = tk.StringVar(value=str(spec.default))
            if spec.min_val is not None and spec.max_val is not None:
                step = float(spec.step) if spec.step is not None else 0.05
                widget = ttk.Spinbox(
                    parent,
                    from_=float(spec.min_val),
                    to=float(spec.max_val),
                    increment=step,
                    textvariable=var,
                    width=7,
                )
            else:
                widget = ttk.Entry(parent, textvariable=var, width=8)
            return var, widget

        var = tk.StringVar(value=str(spec.default) if spec.default is not None else "")
        widget = ttk.Entry(parent, textvariable=var, width=10)
        return var, widget

    def get_hyperparameters(self) -> Dict[str, Any]:
        """Extract and coerce typed hyperparameter values from the current UI controls."""
        result: Dict[str, Any] = {}
        for name, spec in self._specs.items():
            var = self._vars[name]
            raw = var.get()
            if spec.param_type is bool:
                result[name] = bool(raw)
            elif spec.param_type is int:
                raw_s = str(raw).strip()
                val = int(float(raw_s)) if raw_s else int(spec.default)
                spec.validate(val)
                result[name] = val
            elif spec.param_type is float:
                raw_s = str(raw).strip()
                val = float(raw_s) if raw_s else float(spec.default)
                spec.validate(val)
                result[name] = val
            else:
                val = str(raw).strip()
                if spec.choices and val not in [str(c) for c in spec.choices]:
                    spec.validate(val)
                result[name] = val
        return result

    def set_hyperparameter(self, name: str, value: Any) -> None:
        """Programmatically set a hyperparameter value in the form."""
        if name in self._vars:
            if isinstance(self._vars[name], tk.BooleanVar):
                self._vars[name].set(bool(value))
            else:
                self._vars[name].set(str(value))

