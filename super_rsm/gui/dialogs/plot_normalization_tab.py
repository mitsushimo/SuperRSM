"""
super_rsm/gui/dialogs/plot_normalization_tab.py

Tab 4 ("Axis & Plot Normalization") widget for PlotConfigDialog.
Provides a unified UI for configuring presentation-only normalization across
Contour, Uncertainty, and Inline Parity plots without affecting upstream operations.
"""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable, Dict, Optional
import numpy as np

from super_rsm.visualization.normalization import (
    ALL_AXIS_KEYS,
    AXIS_DISPLAY_NAMES,
    NORM_METHODS,
    RANGE_SOURCES,
    RATIO_SOURCES,
    AxisNormalizationSpec,
    PlotNormalizationConfig,
    resolve_axis_transform,
)

_METHOD_LABEL_TO_KEY = {v: k for k, v in NORM_METHODS.items()}
_RANGE_LABEL_TO_KEY = {v: k for k, v in RANGE_SOURCES.items()}
_RATIO_LABEL_TO_KEY = {v: k for k, v in RATIO_SOURCES.items()}


class PlotNormalizationTab(ttk.Frame):
    """Self-contained Normalization configuration tab for PlotConfigDialog."""

    def __init__(
        self,
        parent: tk.Misc,
        output_col: str,
        initial_config: Optional[PlotNormalizationConfig] = None,
        result: Any = None,
        get_opt_output_val: Optional[Callable[[], Optional[float]]] = None,
        on_apply_to_report: Optional[Callable[[PlotNormalizationConfig], None]] = None,
    ):
        super().__init__(parent, style="Card.TFrame", padding="14")
        self.output_col = output_col or "Response"
        self.result = result
        self._get_opt_output_val = get_opt_output_val
        self._on_apply_to_report = on_apply_to_report
        self._initial_cfg = (
            PlotNormalizationConfig.from_dict(initial_config)
            if initial_config is not None
            else PlotNormalizationConfig()
        )
        self.axis_controls: Dict[str, Dict[str, Any]] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        ttk.Label(
            self,
            text=(
                "Presentation-only normalization: scales plot ticks, colorbars, contour labels, "
                "and slice titles without affecting upstream model fitting, evaluation, or optimization."
            ),
            style="CardMuted.TLabel",
            wraplength=740,
            justify=tk.LEFT,
        ).pack(fill=tk.X, pady=(0, 10))

        # 1. Target Plots
        targets_group = ttk.LabelFrame(self, text="Target Plots", padding="10")
        targets_group.pack(fill=tk.X, pady=(0, 10))
        t_row = ttk.Frame(targets_group, style="Card.TFrame")
        t_row.pack(fill=tk.X)

        self.apply_contour_var = tk.BooleanVar(value=self._initial_cfg.apply_to_contour)
        self.apply_uncertainty_var = tk.BooleanVar(value=self._initial_cfg.apply_to_uncertainty)
        self.apply_parity_var = tk.BooleanVar(value=self._initial_cfg.apply_to_parity)
        self.append_suffix_var = tk.BooleanVar(value=self._initial_cfg.append_unit_suffix)

        for lbl, var in [
            ("Main Contour Plot", self.apply_contour_var),
            ("Uncertainty Plot (scales σ)", self.apply_uncertainty_var),
            ("Inline Parity Plot (Report)", self.apply_parity_var),
            ("Append unit hint to labels", self.append_suffix_var),
        ]:
            ttk.Checkbutton(t_row, text=lbl, variable=var, command=self._refresh_preview).pack(
                side=tk.LEFT, padx=(0, 14)
            )

        # 2. Quick Setup
        quick_group = ttk.LabelFrame(self, text="Quick Setup", padding="8")
        quick_group.pack(fill=tk.X, pady=(0, 10))
        q_row = ttk.Frame(quick_group, style="Card.TFrame")
        q_row.pack(fill=tk.X)

        ttk.Label(q_row, text="Method:", style="Card.TLabel").pack(side=tk.LEFT, padx=(0, 4))
        self.global_method_var = tk.StringVar(value=NORM_METHODS["minmax_01"])
        self.global_method_cb = ttk.Combobox(
            q_row, textvariable=self.global_method_var,
            values=list(NORM_METHODS.values()), state="readonly", width=16,
        )
        self.global_method_cb.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(q_row, text="Reference:", style="Card.TLabel").pack(side=tk.LEFT, padx=(0, 4))
        self.global_ref_var = tk.StringVar(value=RANGE_SOURCES["dataset"])
        self.global_ref_cb = ttk.Combobox(
            q_row, textvariable=self.global_ref_var,
            values=list(RANGE_SOURCES.values()), state="readonly", width=18,
        )
        self.global_ref_cb.pack(side=tk.LEFT, padx=(0, 10))
        self.global_method_cb.bind("<<ComboboxSelected>>", lambda e: self._on_global_method_changed())

        ttk.Button(q_row, text="Apply to Enabled", style="Small.TButton", command=self._apply_global_to_enabled).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(q_row, text="Enable All", style="Small.TButton", command=lambda: self._set_all_axes(True)).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(q_row, text="Disable All (Raw)", style="Small.TButton", command=lambda: self._set_all_axes(False)).pack(side=tk.LEFT)

        # 3. Per-Axis Matrix
        axes_group = ttk.LabelFrame(self, text="Per-Axis Normalization", padding="10")
        axes_group.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        hdr = ttk.Frame(axes_group, style="Card.TFrame")
        hdr.pack(fill=tk.X, pady=(0, 6))
        for text, w in [
            ("On", 4), ("Axis", 22), ("Method", 17), ("Reference", 19), ("Custom Min / Ref", 15), ("Custom Max", 13),
        ]:
            ttk.Label(hdr, text=text, width=w, style="CardBold.TLabel").pack(side=tk.LEFT, padx=(0, 4))

        for axis_key in ALL_AXIS_KEYS:
            row = ttk.Frame(axes_group, style="Card.TFrame")
            row.pack(fill=tk.X, pady=4)
            en_var = tk.BooleanVar(value=False)
            ttk.Checkbutton(row, variable=en_var, command=lambda k=axis_key: self._update_row_state(k)).pack(side=tk.LEFT, padx=(0, 8))
            axis_lbl_var = tk.StringVar(value=AXIS_DISPLAY_NAMES[axis_key])
            ttk.Label(row, textvariable=axis_lbl_var, width=22, style="CardBold.TLabel").pack(side=tk.LEFT, padx=(0, 4))
            method_var = tk.StringVar(value=NORM_METHODS["minmax_01"])
            method_cb = ttk.Combobox(row, textvariable=method_var, values=list(NORM_METHODS.values()), state="readonly", width=15)
            method_cb.pack(side=tk.LEFT, padx=(0, 6))
            ref_var = tk.StringVar(value=RANGE_SOURCES["dataset"])
            ref_cb = ttk.Combobox(row, textvariable=ref_var, values=list(RANGE_SOURCES.values()), state="readonly", width=17)
            ref_cb.pack(side=tk.LEFT, padx=(0, 6))
            c1_var, c2_var = tk.StringVar(value=""), tk.StringVar(value="")
            c1_entry = ttk.Entry(row, textvariable=c1_var, width=13)
            c1_entry.pack(side=tk.LEFT, padx=(0, 6))
            c2_entry = ttk.Entry(row, textvariable=c2_var, width=12)
            c2_entry.pack(side=tk.LEFT)

            self.axis_controls[axis_key] = {
                "enabled_var": en_var, "label_var": axis_lbl_var,
                "method_var": method_var, "method_cb": method_cb,
                "ref_var": ref_var, "ref_cb": ref_cb,
                "custom1_var": c1_var, "custom1_entry": c1_entry,
                "custom2_var": c2_var, "custom2_entry": c2_entry,
            }
            method_cb.bind("<<ComboboxSelected>>", lambda e, k=axis_key: self._on_axis_method_changed(k))
            ref_cb.bind("<<ComboboxSelected>>", lambda e, k=axis_key: self._update_row_state(k))

        # 4. Preview & Apply-to-Report Bar
        footer = ttk.Frame(self, style="Card.TFrame")
        footer.pack(fill=tk.X, pady=(4, 0))
        self.preview_var = tk.StringVar(value="All plots using raw units.")
        ttk.Label(footer, textvariable=self.preview_var, style="CardMuted.TLabel", wraplength=540, justify=tk.LEFT).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(footer, text="✓  Apply to Inline Report", style="Secondary.TButton", command=self.apply_to_report).pack(side=tk.RIGHT, padx=(8, 0))

        self.load_config(self._initial_cfg)

    def _on_global_method_changed(self) -> None:
        m_key = _METHOD_LABEL_TO_KEY.get(self.global_method_var.get(), "minmax_01")
        vals = list((RATIO_SOURCES if m_key == "ratio" else RANGE_SOURCES).values())
        self.global_ref_cb.config(values=vals)
        if self.global_ref_var.get() not in vals:
            self.global_ref_var.set(vals[0])

    def _apply_global_to_enabled(self) -> None:
        m_lbl, r_lbl = self.global_method_var.get(), self.global_ref_var.get()
        for k, ctrl in self.axis_controls.items():
            if ctrl["enabled_var"].get():
                ctrl["method_var"].set(m_lbl)
                self._on_axis_method_changed(k)
                if r_lbl in ctrl["ref_cb"]["values"]:
                    ctrl["ref_var"].set(r_lbl)
                self._update_row_state(k)
        self._refresh_preview()

    def _set_all_axes(self, enabled: bool) -> None:
        for k, ctrl in self.axis_controls.items():
            ctrl["enabled_var"].set(enabled)
            self._update_row_state(k)
        self._refresh_preview()

    def _on_axis_method_changed(self, axis_key: str) -> None:
        ctrl = self.axis_controls[axis_key]
        m_key = _METHOD_LABEL_TO_KEY.get(ctrl["method_var"].get(), "minmax_01")
        vals = list((RATIO_SOURCES if m_key == "ratio" else RANGE_SOURCES).values())
        ctrl["ref_cb"].config(values=vals)
        if ctrl["ref_var"].get() not in vals:
            ctrl["ref_var"].set(vals[0])
        self._update_row_state(axis_key)

    def _update_row_state(self, axis_key: str) -> None:
        ctrl = self.axis_controls[axis_key]
        enabled = bool(ctrl["enabled_var"].get())
        m_key = _METHOD_LABEL_TO_KEY.get(ctrl["method_var"].get(), "minmax_01")
        ref_map = _RATIO_LABEL_TO_KEY if m_key == "ratio" else _RANGE_LABEL_TO_KEY
        r_key = ref_map.get(ctrl["ref_var"].get(), "dataset")

        ctrl["method_cb"].config(state="readonly" if enabled else "disabled")
        ctrl["ref_cb"].config(state="readonly" if enabled else "disabled")
        if enabled and r_key == "custom":
            ctrl["custom1_entry"].config(state="normal")
            ctrl["custom2_entry"].config(state="disabled" if m_key == "ratio" else "normal")
        else:
            ctrl["custom1_entry"].config(state="disabled")
            ctrl["custom2_entry"].config(state="disabled")
        self._refresh_preview()

    def refresh_axis_labels(self, role_map: Dict[str, str]) -> None:
        full_map = dict(role_map)
        full_map["z_axis"] = self.output_col
        for k, ctrl in self.axis_controls.items():
            col = full_map.get(k)
            base = AXIS_DISPLAY_NAMES[k]
            ctrl["label_var"].set(f"{base} ({col})" if col else base)

    def _refresh_preview(self) -> None:
        if not hasattr(self, "preview_var"):
            return
        try:
            desc = self.get_config(strict=False).describe_active_normalization()
            self.preview_var.set(desc if desc else "All plots using raw units.")
        except Exception:
            self.preview_var.set("Check custom normalization values.")

    def load_config(self, cfg: PlotNormalizationConfig) -> None:
        self.apply_contour_var.set(bool(cfg.apply_to_contour))
        self.apply_uncertainty_var.set(bool(cfg.apply_to_uncertainty))
        self.apply_parity_var.set(bool(cfg.apply_to_parity))
        self.append_suffix_var.set(bool(cfg.append_unit_suffix))
        for k in ALL_AXIS_KEYS:
            spec = cfg.get_axis_spec(k)
            ctrl = self.axis_controls[k]
            ctrl["enabled_var"].set(bool(spec.enabled))
            ctrl["method_var"].set(NORM_METHODS.get(spec.method, NORM_METHODS["minmax_01"]))
            sources = RATIO_SOURCES if spec.method == "ratio" else RANGE_SOURCES
            ctrl["ref_cb"].config(values=list(sources.values()))
            default_ref = "dataset_max" if spec.method == "ratio" else "dataset"
            ctrl["ref_var"].set(sources.get(spec.reference, sources[default_ref]))
            if spec.method == "ratio":
                ctrl["custom1_var"].set("" if spec.custom_ref is None else f"{spec.custom_ref:g}")
                ctrl["custom2_var"].set("")
            else:
                ctrl["custom1_var"].set("" if spec.custom_min is None else f"{spec.custom_min:g}")
                ctrl["custom2_var"].set("" if spec.custom_max is None else f"{spec.custom_max:g}")
            self._update_row_state(k)
        self._refresh_preview()

    def get_config(self, strict: bool = True) -> PlotNormalizationConfig:
        specs: Dict[str, AxisNormalizationSpec] = {}
        for k in ALL_AXIS_KEYS:
            ctrl = self.axis_controls[k]
            enabled = bool(ctrl["enabled_var"].get())
            m_key = _METHOD_LABEL_TO_KEY.get(ctrl["method_var"].get(), "minmax_01")
            ref_map = _RATIO_LABEL_TO_KEY if m_key == "ratio" else _RANGE_LABEL_TO_KEY
            r_key = ref_map.get(ctrl["ref_var"].get(), "dataset_max" if m_key == "ratio" else "dataset")
            c1_s, c2_s = ctrl["custom1_var"].get().strip(), ctrl["custom2_var"].get().strip()
            c_min = c_max = c_ref = None
            if m_key == "ratio":
                if c1_s:
                    try: c_ref = float(c1_s)
                    except ValueError:
                        if strict and enabled and r_key == "custom":
                            raise ValueError(f"{AXIS_DISPLAY_NAMES[k]}: Invalid custom reference '{c1_s}'.")
            else:
                for val_s, name in ((c1_s, "Min"), (c2_s, "Max")):
                    if val_s:
                        try: parsed = float(val_s)
                        except ValueError:
                            if strict and enabled and r_key == "custom":
                                raise ValueError(f"{AXIS_DISPLAY_NAMES[k]}: Invalid custom {name} '{val_s}'.")
                            parsed = None
                        if name == "Min": c_min = parsed
                        else: c_max = parsed
            specs[k] = AxisNormalizationSpec(
                enabled=enabled, method=m_key, reference=r_key,
                custom_min=c_min, custom_max=c_max, custom_ref=c_ref,
            )
        return PlotNormalizationConfig(
            apply_to_contour=bool(self.apply_contour_var.get()),
            apply_to_uncertainty=bool(self.apply_uncertainty_var.get()),
            apply_to_parity=bool(self.apply_parity_var.get()),
            append_unit_suffix=bool(self.append_suffix_var.get()),
            **specs,
        )

    def apply_to_report(self) -> None:
        try:
            norm_cfg = self.get_config(strict=True)
            if norm_cfg.is_parity_normalized() and self.result is not None and getattr(self.result, "dataset", None) is not None:
                ds = self.result.dataset
                raw_y = np.concatenate([ds.y_train, ds.y_test]) if ds.has_test_set and len(ds.y_test) > 0 else ds.y_train
                opt_val = self._get_opt_output_val() if self._get_opt_output_val else None
                resolve_axis_transform(
                    norm_cfg.z_axis, data_values=raw_y, plot_values=raw_y,
                    opt_value=opt_val, axis_name="Z-Axis (Output)",
                )
        except Exception as exc:
            messagebox.showerror("Invalid Normalization", str(exc), parent=self.winfo_toplevel())
            return
        if self._on_apply_to_report is not None:
            self._on_apply_to_report(norm_cfg)
        self._refresh_preview()


def format_slice_labels(
    col: str,
    vals: Any,
    prefix: str,
    suffix: str,
    norm_cfg: PlotNormalizationConfig,
    axis_spec: AxisNormalizationSpec,
    df: Any = None,
    opt_params_dict: Optional[Dict[str, float]] = None,
    axis_label: str = "Slice-Axis",
    decimals: int = 2,
) -> list:
    """Format P or Q subplot slice labels with fixed decimal places, normalizing display values when enabled."""
    dec = max(0, int(decimals))
    pre = prefix.strip() or f"{col}="
    suf = suffix.strip()
    disp_vals = [float(v) for v in vals]
    if norm_cfg.apply_to_contour and axis_spec.enabled:
        data_vals = None
        if df is not None and col in df.columns:
            import pandas as pd
            s = pd.to_numeric(df[col], errors="coerce").dropna()
            if not s.empty:
                data_vals = s.to_numpy(dtype=float)
        tf = resolve_axis_transform(
            axis_spec, data_values=data_vals, plot_values=vals,
            opt_value=(opt_params_dict or {}).get(col), axis_name=f"{axis_label} ({col})",
        )
        if tf is not None:
            disp_vals = [float(tf.transform(v)) for v in vals]
    return [f"{pre}{v:.{dec}f}{suf}" for v in disp_vals]

