"""
super_rsm/gui/dialogs/plot_config_dialog.py

Multi-tab plot configuration modal window for response surface contour visualization.
"""

import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from super_rsm.gui.components.scrollable_panel import ScrollablePanel
from super_rsm.gui.styles.palette import COMMON_CMAPS, COMMON_LINESTYLES, COMMON_MARKERS, PALETTE


class PlotConfigDialog(tk.Toplevel):
    """Modal configuration window for multi-dimensional contour plotting."""

    def __init__(
        self,
        parent: tk.Misc,
        input_cols: List[str],
        output_col: str,
        result: Any,
        df: Optional[pd.DataFrame] = None,
        opt_params_dict: Optional[Dict[str, float]] = None,
        on_generate_plot: Optional[Callable[..., None]] = None,
    ):
        super().__init__(parent)
        self.title("Configure Multi-Dimensional Contour Plot")
        self.geometry("780x720")
        self.minsize(680, 600)
        self.configure(bg=PALETTE["bg_main"])

        self.input_cols = input_cols
        self.output_col = output_col or "Response"
        self.result = result
        self.df = df
        self.opt_params_dict = opt_params_dict or {}
        self.on_generate_plot = on_generate_plot

        self.plot_param_configs: Dict[str, Dict[str, Any]] = {}
        self.adv_settings_vars: Dict[str, tk.Variable] = {}
        self.adv_settings_widgets: Dict[str, tk.Widget] = {}

        self._build_ui()

    def _get_col_range_str(self, col_name: str) -> str:
        if self.df is None or col_name not in self.df.columns:
            return "—"
        s = pd.to_numeric(self.df[col_name], errors="coerce").dropna()
        return "—" if s.empty else f"[{float(s.min()):.4g}, {float(s.max()):.4g}]"

    def _get_col_plot_defaults(self, col: str) -> Tuple[str, str, str, str]:
        min_v, max_v, mean_v = -1.0, 1.0, 0.0
        if self.df is not None and col in self.df.columns:
            s = pd.to_numeric(self.df[col], errors="coerce").dropna()
            if not s.empty:
                min_v, max_v, mean_v = float(s.min()), float(s.max()), float(s.mean())
                if np.isclose(min_v, max_v):
                    min_v, max_v = min_v - 1.0, max_v + 1.0
        opt_v = self.opt_params_dict.get(col, mean_v)
        q25, q50, q75 = (min_v + f * (max_v - min_v) for f in (0.25, 0.50, 0.75))
        return f"{min_v:.4g}", f"{max_v:.4g}", f"{opt_v:.6g}", f"{q25:.4g}, {q50:.4g}, {q75:.4g}"

    def _build_ui(self) -> None:
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=(12, 6))
        self._build_roles_tab(notebook)
        self._build_labels_tab(notebook)
        self._build_advanced_tab(notebook)

        btn_frame = ttk.Frame(self, padding=(12, 6, 12, 12))
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="Load Settings...", command=self.load_plot_settings).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_frame, text="Save Settings...", command=self.save_plot_settings).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="▶  Generate Plot", style="Primary.TButton", command=self.generate_plot).pack(side=tk.RIGHT)

    def _build_roles_tab(self, notebook: ttk.Notebook) -> None:
        roles_frame = ttk.Frame(notebook, style="Card.TFrame", padding="14")
        notebook.add(roles_frame, text="  1. Parameter Roles & Ranges  ")

        roles_top = ttk.Frame(roles_frame, style="Card.TFrame")
        roles_top.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(roles_top, text="Assign each input variable to a plot axis, subplot grid (P/Q), or fixed slice value:", style="CardBold.TLabel").pack(side=tk.LEFT)

        roles_actions = ttk.Frame(roles_frame, style="Card.TFrame")
        roles_actions.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(roles_actions, text="Reset X/Y Ranges to Data [Min, Max]", style="Small.TButton", command=self._reset_plot_axes_to_data).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(roles_actions, text="Set Fixed Values to Optimal Solution", style="Small.TButton", command=self._set_plot_fixed_to_optimal).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(roles_actions, text="Set Fixed Values to Data Mean", style="Small.TButton", command=self._set_plot_fixed_to_mean).pack(side=tk.LEFT)

        panel = ScrollablePanel(roles_frame)
        panel.pack(fill=tk.BOTH, expand=True)
        roles = ["X-Axis", "Y-Axis", "Row-Axis (P)", "Column-Axis (Q)", "Fixed"]
        for idx, col in enumerate(self.input_cols):
            row_frame = ttk.Frame(panel.inner_frame, style="Card.TFrame")
            row_frame.pack(fill=tk.X, pady=5)
            ttk.Label(row_frame, text=col, width=16, style="CardBold.TLabel").pack(side=tk.LEFT)
            role_var = tk.StringVar()
            role_combo = ttk.Combobox(row_frame, textvariable=role_var, values=roles, state="readonly", width=15)
            role_combo.pack(side=tk.LEFT, padx=6)
            input_frame = ttk.Frame(row_frame, style="Card.TFrame")
            input_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
            self.plot_param_configs[col] = {"role_var": role_var, "input_frame": input_frame, "vars": {}}
            role_combo.bind("<<ComboboxSelected>>", lambda e, c=col: self._update_plot_role_inputs(c))
            role_combo.set("X-Axis" if idx == 0 else ("Y-Axis" if idx == 1 else "Fixed"))
            self._update_plot_role_inputs(col)

    def _build_labels_tab(self, notebook: ttk.Notebook) -> None:
        labels_frame = ttk.Frame(notebook, style="Card.TFrame", padding="14")
        notebook.add(labels_frame, text="  2. Titles & Axis Labels  ")

        def add_label_field(text: str, default_val: str) -> tk.StringVar:
            frame = ttk.Frame(labels_frame, style="Card.TFrame")
            frame.pack(fill=tk.X, pady=6)
            ttk.Label(frame, text=text, width=36, style="Card.TLabel").pack(side=tk.LEFT)
            var = tk.StringVar(value=default_val)
            ttk.Entry(frame, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True)
            return var

        self.plot_title_var = add_label_field("Plot Title:", f"RSM Contour Plot — {self.output_col}")
        self.x_label_var = add_label_field("X-Axis Label (Leave empty for column name):", "")
        self.y_label_var = add_label_field("Y-Axis Label (Leave empty for column name):", "")
        self.colorbar_label_var = add_label_field("Colorbar Label:", self.output_col)
        self.p_label_prefix_var = add_label_field("Row-Axis (P) Label Prefix:", "")
        self.p_label_suffix_var = add_label_field("Row-Axis (P) Label Suffix:", "")
        self.q_label_prefix_var = add_label_field("Column-Axis (Q) Label Prefix:", "")
        self.q_label_suffix_var = add_label_field("Column-Axis (Q) Label Suffix:", "")

    def _build_advanced_tab(self, notebook: ttk.Notebook) -> None:
        adv_frame = ttk.Frame(notebook, style="Card.TFrame", padding="12")
        notebook.add(adv_frame, text="  3. Styling, Scatter & Uncertainty  ")
        adv_frame.columnconfigure(0, weight=1)
        adv_frame.columnconfigure(1, weight=1)

        def add_adv_field(parent: tk.Misc, key: str, text: str, default_val: Any, var_type: type = tk.StringVar, options: Optional[List[str]] = None, readonly_options: bool = True) -> tk.Variable:
            frame = ttk.Frame(parent, style="Card.TFrame")
            frame.pack(fill=tk.X, pady=3)
            ttk.Label(frame, text=text, width=24, style="Card.TLabel").pack(side=tk.LEFT)
            var = var_type(value=default_val)
            if var_type == tk.BooleanVar:
                widget = ttk.Checkbutton(frame, variable=var)
                if text.startswith("Plot Uncertainty") and not getattr(self.result, "supports_uncertainty", False):
                    widget.config(state="disabled")
                widget.pack(side=tk.LEFT)
            elif options is not None:
                widget = ttk.Combobox(frame, textvariable=var, values=options, state="readonly" if readonly_options else "normal", width=16)
                widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
            else:
                widget = ttk.Entry(frame, textvariable=var, width=16)
                widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.adv_settings_vars[key] = var
            self.adv_settings_widgets[key] = widget
            return var

        contour_group = ttk.LabelFrame(adv_frame, text="Contour & Surface Styling", padding="10")
        contour_group.grid(row=0, column=0, sticky=tk.NSEW, padx=(0, 6), pady=(0, 8))
        add_adv_field(contour_group, "cmap", "Colormap (cmap):", "plasma", options=COMMON_CMAPS, readonly_options=False)
        add_adv_field(contour_group, "alpha", "Alpha (transparency):", 0.85, tk.DoubleVar)
        add_adv_field(contour_group, "fill_levels", "Fill Levels:", 100, tk.IntVar)
        add_adv_field(contour_group, "line_levels", "Line Levels:", 10, tk.IntVar)
        add_adv_field(contour_group, "line_color", "Line Color:", "white")
        add_adv_field(contour_group, "inline_color", "Inline Color:", "white")
        add_adv_field(contour_group, "inline_fontsize", "Inline Fontsize:", 9, tk.IntVar)
        add_adv_field(contour_group, "inline_format", "Inline Format:", "%1.1f")

        scale_group = ttk.LabelFrame(adv_frame, text="Colorbar, Grid & Uncertainty", padding="10")
        scale_group.grid(row=1, column=0, sticky=tk.NSEW, padx=(0, 6), pady=(0, 4))
        add_adv_field(scale_group, "uniform_cmap", "Uniform Colormap:", True, tk.BooleanVar)
        add_adv_field(scale_group, "show_colorbar", "Show Colorbar:", False, tk.BooleanVar)

        cbar_lbl_frame = ttk.Frame(scale_group, style="Card.TFrame")
        cbar_lbl_frame.pack(fill=tk.X, pady=3)
        ttk.Label(cbar_lbl_frame, text="Colorbar Label:", width=24, style="Card.TLabel").pack(side=tk.LEFT)
        ttk.Entry(cbar_lbl_frame, textvariable=self.colorbar_label_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.adv_settings_vars["colorbar_label"] = self.colorbar_label_var

        add_adv_field(scale_group, "grid_color", "Grid Color:", "gray")
        add_adv_field(scale_group, "grid_linestyle", "Grid Linestyle:", "--", options=COMMON_LINESTYLES, readonly_options=False)
        add_adv_field(scale_group, "plot_uncertainty", "Plot Uncertainty:", False, tk.BooleanVar)

        scatter_group = ttk.LabelFrame(adv_frame, text="Measurement Data Scatter Overlay", padding="10")
        scatter_group.grid(row=0, column=1, rowspan=2, sticky=tk.NSEW, padx=(6, 0), pady=(0, 4))
        add_adv_field(scatter_group, "scatter_data", "Scatter-Plot Data:", False, tk.BooleanVar)
        add_adv_field(scatter_group, "scatter_size", "Scatter Marker Size:", 30.0, tk.DoubleVar)
        add_adv_field(scatter_group, "scatter_color_mode", "Scatter Color Mode:", "Fixed Color", options=["Fixed Color", "Output Value (Colormap)"], readonly_options=True)
        add_adv_field(scatter_group, "scatter_color", "Scatter Marker Color:", "white")
        add_adv_field(scatter_group, "scatter_cmap", "Scatter Colormap:", "plasma", options=COMMON_CMAPS, readonly_options=False)
        add_adv_field(scatter_group, "scatter_edgecolor", "Scatter Edge Color:", "black")
        add_adv_field(scatter_group, "scatter_marker", "Scatter Marker Style:", "o", options=COMMON_MARKERS, readonly_options=False)

        self.adv_settings_widgets["scatter_color_mode"].bind("<<ComboboxSelected>>", lambda e: self._update_scatter_color_state())
        self._update_scatter_color_state()

    def _reset_plot_axes_to_data(self) -> None:
        for col, param_data in self.plot_param_configs.items():
            if param_data["role_var"].get() in ("X-Axis", "Y-Axis"):
                min_s, max_s, _, _ = self._get_col_plot_defaults(col)
                if "min" in param_data["vars"]: param_data["vars"]["min"].set(min_s)
                if "max" in param_data["vars"]: param_data["vars"]["max"].set(max_s)

    def _set_plot_fixed_to_optimal(self) -> None:
        for col, param_data in self.plot_param_configs.items():
            if param_data["role_var"].get() == "Fixed" and "value" in param_data["vars"]:
                param_data["vars"]["value"].set(self._get_col_plot_defaults(col)[2])

    def _set_plot_fixed_to_mean(self) -> None:
        for col, param_data in self.plot_param_configs.items():
            if param_data["role_var"].get() == "Fixed" and "value" in param_data["vars"]:
                mean_v = 0.0
                if self.df is not None and col in self.df.columns:
                    s = pd.to_numeric(self.df[col], errors="coerce").dropna()
                    if not s.empty: mean_v = float(s.mean())
                param_data["vars"]["value"].set(f"{mean_v:.6g}")

    def _update_scatter_color_state(self) -> None:
        mode_var = self.adv_settings_vars.get("scatter_color_mode")
        color_entry = self.adv_settings_widgets.get("scatter_color")
        cmap_entry = self.adv_settings_widgets.get("scatter_cmap")
        if mode_var and color_entry and cmap_entry:
            is_cmap = mode_var.get() == "Output Value (Colormap)"
            color_entry.config(state="disabled" if is_cmap else "normal")
            cmap_entry.config(state="normal" if is_cmap else "disabled")

    def _update_plot_role_inputs(self, col: str) -> None:
        param_data = self.plot_param_configs[col]
        role, input_frame = param_data["role_var"].get(), param_data["input_frame"]
        for widget in input_frame.winfo_children():
            widget.destroy()
        param_data["vars"] = {}
        min_def, max_def, fixed_def, pq_def = self._get_col_plot_defaults(col)

        if role in ["X-Axis", "Y-Axis"]:
            min_var, max_var, steps_var = tk.StringVar(value=min_def), tk.StringVar(value=max_def), tk.StringVar(value="50")
            for lbl, var, w, pad in [("Min:", min_var, 9, (3, 8)), ("Max:", max_var, 9, (3, 8)), ("Steps:", steps_var, 6, (3, 0))]:
                ttk.Label(input_frame, text=lbl, style="Card.TLabel").pack(side=tk.LEFT)
                ttk.Entry(input_frame, textvariable=var, width=w).pack(side=tk.LEFT, padx=pad)
            param_data["vars"].update({"min": min_var, "max": max_var, "steps": steps_var})
        elif role in ["Row-Axis (P)", "Column-Axis (Q)"]:
            val_var = tk.StringVar(value=pq_def)
            ttk.Label(input_frame, text="Values (comma-separated):", style="Card.TLabel").pack(side=tk.LEFT, padx=(0, 4))
            ttk.Entry(input_frame, textvariable=val_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
            param_data["vars"]["values"] = val_var
        elif role == "Fixed":
            val_var = tk.StringVar(value=fixed_def)
            ttk.Label(input_frame, text="Hold Value:", style="Card.TLabel").pack(side=tk.LEFT, padx=(0, 4))
            ttk.Entry(input_frame, textvariable=val_var, width=12).pack(side=tk.LEFT)
            ttk.Label(input_frame, text=f"  (Data: {self._get_col_range_str(col)})", style="CardMuted.TLabel").pack(side=tk.LEFT, padx=(6, 0))
            param_data["vars"]["value"] = val_var

    def generate_plot(self) -> None:
        config: Dict[str, Any] = {"fixed": []}
        x_count = y_count = p_count = q_count = 0
        label_arrays_p: Optional[List[str]] = None
        label_arrays_q: Optional[List[str]] = None
        x_col = y_col = None

        try:
            for idx, col in enumerate(self.input_cols):
                role = self.plot_param_configs[col]["role_var"].get()
                vars_dict = self.plot_param_configs[col]["vars"]
                if role == "X-Axis":
                    x_count += 1; x_col = col
                    config["x"] = (idx, np.linspace(float(vars_dict["min"].get()), float(vars_dict["max"].get()), int(vars_dict["steps"].get())))
                elif role == "Y-Axis":
                    y_count += 1; y_col = col
                    config["y"] = (idx, np.linspace(float(vars_dict["min"].get()), float(vars_dict["max"].get()), int(vars_dict["steps"].get())))
                elif role == "Row-Axis (P)":
                    p_count += 1
                    vals = [float(v.strip()) for v in vars_dict["values"].get().split(",") if v.strip()]
                    config["p"] = (idx, vals)
                    p_pre, p_suf = self.p_label_prefix_var.get().strip() or f"{col}=", self.p_label_suffix_var.get().strip()
                    label_arrays_p = [f"{p_pre}{v}{p_suf}" for v in vals]
                elif role == "Column-Axis (Q)":
                    q_count += 1
                    vals = [float(v.strip()) for v in vars_dict["values"].get().split(",") if v.strip()]
                    config["q"] = (idx, vals)
                    q_pre, q_suf = self.q_label_prefix_var.get().strip() or f"{col}=", self.q_label_suffix_var.get().strip()
                    label_arrays_q = [f"{q_pre}{v}{q_suf}" for v in vals]
                elif role == "Fixed":
                    config["fixed"].append((idx, float(vars_dict["value"].get())))

            if x_count != 1 or y_count != 1:
                messagebox.showerror("Error", "You must assign exactly one X-Axis and one Y-Axis.", parent=self); return
            if p_count > 1 or q_count > 1:
                messagebox.showerror("Error", "You can assign at most one Row-Axis (P) and one Column-Axis (Q).", parent=self); return

            x_label = self.x_label_var.get().strip() or x_col or "X"
            y_label = self.y_label_var.get().strip() or y_col or "Y"
            title = self.plot_title_var.get().strip() or "RSM Contour Plot"
            label_array = None
            if p_count > 0 or q_count > 0:
                p_labels, q_labels = label_arrays_p or [""], label_arrays_q or [""]
                label_array = [[f"{p_lbl}, {q_lbl}" if (p_lbl and q_lbl) else (p_lbl or q_lbl) for q_lbl in q_labels] for p_lbl in p_labels]

            plot_settings = {k: var.get() for k, var in self.adv_settings_vars.items()}
            plot_settings["show_plot"] = True
            if plot_settings.get("plot_uncertainty", False) and not getattr(self.result, "supports_uncertainty", False):
                messagebox.showerror("Error", f"Uncertainty plotting is not supported for {getattr(self.result, 'method', 'this model')}.", parent=self); return

            if self.on_generate_plot:
                self.on_generate_plot(config, title, x_label, y_label, label_array, plot_settings)
            else:
                self.result.visualize_rsm(config, title=title, xlabel=x_label, ylabel=y_label, label_array=label_array, plot_settings=plot_settings, show=True)
        except Exception as e:
            messagebox.showerror("Error", f"Invalid plot configuration: {e}", parent=self)

    def save_plot_settings(self) -> None:
        filepath = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")], title="Save Plot Settings", parent=self)
        if not filepath: return
        settings = {
            "roles": {col: {"role": cfg["role_var"].get(), "vars": {k: v.get() for k, v in cfg["vars"].items()}} for col, cfg in self.plot_param_configs.items()},
            "labels": {"plot_title": self.plot_title_var.get(), "x_label": self.x_label_var.get(), "y_label": self.y_label_var.get(), "colorbar_label": self.colorbar_label_var.get(), "p_label_prefix": self.p_label_prefix_var.get(), "p_label_suffix": self.p_label_suffix_var.get(), "q_label_prefix": self.q_label_prefix_var.get(), "q_label_suffix": self.q_label_suffix_var.get()},
            "advanced": {k: v.get() for k, v in self.adv_settings_vars.items() if k != "colorbar_label"},
        }
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4)
            messagebox.showinfo("Success", f"Plot settings saved successfully to:\n{filepath}", parent=self)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}", parent=self)

    def load_plot_settings(self) -> None:
        filepath = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")], title="Load Plot Settings", parent=self)
        if not filepath: return
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                settings = json.load(f)
            labels = settings.get("labels", {})
            for key, var in [("plot_title", self.plot_title_var), ("x_label", self.x_label_var), ("y_label", self.y_label_var), ("colorbar_label", self.colorbar_label_var), ("p_label_prefix", self.p_label_prefix_var), ("p_label_suffix", self.p_label_suffix_var), ("q_label_prefix", self.q_label_prefix_var), ("q_label_suffix", self.q_label_suffix_var)]:
                if key in labels: var.set(labels[key])
            for key, val in settings.get("advanced", {}).items():
                if key in self.adv_settings_vars:
                    if key == "plot_uncertainty" and val and not getattr(self.result, "supports_uncertainty", False):
                        self.adv_settings_vars[key].set(False); continue
                    self.adv_settings_vars[key].set(val)
            self._update_scatter_color_state()
            for col, role_data in settings.get("roles", {}).items():
                if col in self.plot_param_configs:
                    cfg = self.plot_param_configs[col]
                    cfg["role_var"].set(role_data.get("role", "Fixed"))
                    self._update_plot_role_inputs(col)
                    for k, v in role_data.get("vars", {}).items():
                        if k in cfg["vars"]: cfg["vars"][k].set(v)
            messagebox.showinfo("Success", f"Plot settings loaded successfully from:\n{filepath}", parent=self)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load settings: {e}", parent=self)
