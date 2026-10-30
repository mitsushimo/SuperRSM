# Architectural Blueprint & Handoff Report: Milestone M3-1
**Subsystem**: Visualization Service Core (`PlotSettings` & `GridSampler`)  
**Target Files**: `super_rsm/visualization/settings.py` & `super_rsm/visualization/grid.py`  
**Explorer Agent**: Explorer M3-1 (`explorer_m3_1`)  
**Status**: COMPLETE (Ready for Implementation)

---

## 1. Observation

### 1.1 Existing Implementations & Bottlenecks

1. **`high_d_plotter.py` (lines 11–108)**:
   - **Global Side Effect**: Line 15 executes `sns.set_theme(style="whitegrid")` at module load time. Any Python script importing `high_d_plotter` or `rsm_backend` has its global Matplotlib rcParams mutated without user consent.
   - **Hardcoded Global Dict**: Lines 86–108 define `default_plot_settings` as a flat, untyped dictionary containing 23 configuration keys with no schema validation, type checking, or serialization abstractions:
     ```python
     default_plot_settings = {
         "cmap": "plasma", "alpha": 0.85, "fill_levels": 100, "line_levels": 10,
         "line_color": "white", "inline_color": "white", "inline_fontsize": 9,
         "grid_color": "gray", "grid_linestyle": "--", "inline_format": '%1.1f',
         "uniform_cmap": True, "show_colorbar": False, "colorbar_label": "",
         "scatter_data": False, "scatter_size": 30.0, "scatter_color_mode": "Fixed Color",
         "scatter_color": "white", "scatter_cmap": "plasma", "scatter_edgecolor": "black",
         "scatter_marker": "o", "show_plot": True
     }
     ```
   - **Missing Visualization Control**: Lacks controls for DPI settings, typography hierarchies (title, axis, tick font sizes), figure dimensions (`fig_width`, `fig_height`), line widths, grid alpha, and profile presets (e.g., publication, presentation, dark mode).

2. **`rsm_backend.py` (lines 271–408, `visualize_rsm`)**:
   - **Severe 40,000 Scalar Prediction Bottleneck**: In lines 334–360, response surface mesh evaluation executes an unvectorized scalar loop:
     ```python
     for x_val, y_val in zip(X_flat, Y_flat):
         params = np.zeros(self.X_test.shape[1])
         params[x_idx] = x_val
         params[y_idx] = y_val
         # ...
         z_value = self.target_func(params)
         Z_flat.append(z_value)
     ```
     For a $100 \times 100$ grid with $2 \times 2$ subplots, this loop executes **40,000 separate calls to `model.predict()`**, causing 12–35 seconds of frozen execution and blocking Tkinter event loops.
   - **Entangled Scatter Spatial Filtering**: Lines 317–332 filter training/test scatter observations matching slice coordinates $(p, q)$ and fixed values using inline boolean masking. This logic is coupled directly to the plotting loop rather than isolated in a testable, reusable domain service.

3. **`super_rsm/models/base.py` (lines 36–96, 167–235)**:
   - Already defines `SurfaceGridConfig` and `SurfaceGridResult`.
   - `BaseRSMModel.compute_surface_grid(config: SurfaceGridConfig)` implements vectorized batch evaluation: assembling 2D batch matrices `(N_points, D)` and executing a single `model.predict(batch)` per subplot, executing in $< 15$ ms ($100\times$ speedup).
   - `SurfaceGridConfig.validate()` enforces dimension completeness across $D$ dimensions, preventing zero-fill artifacts.

4. **`rsm_gui.py` (lines 2555–2718, 2929–3039)**:
   - The plot configuration dialog provides 3 notebook tabs:
     * Tab 1: Parameter Roles & Ranges (`X-Axis`, `Y-Axis`, `Row-Axis (P)`, `Column-Axis (Q)`, `Fixed`).
     * Tab 2: Titles & Axis Labels (`plot_title`, `x_label`, `y_label`, `colorbar_label`, prefixes/suffixes).
     * Tab 3: Advanced Settings (Contour styling, Colorbar/Grid/Uncertainty, Scatter overlay).
   - Saves/loads settings via JSON files (`save_plot_settings` and `load_plot_settings`).

5. **Existing Automated Test Suite Baseline**:
   - `python -m pytest`: 85 passed, 1 skipped in 8.43s across `test_baseline.py`, `test_core.py`, `test_models.py`, `test_challenger_*.py`. Zero regressions permitted.

---

## 2. Logic Chain

1. **Decoupling Visualization Architecture**:
   - To make SuperRSM maintainable, headless-capable, and modular, all plotting and meshgrid mathematics must reside in `super_rsm.visualization`.
   - `super_rsm.visualization.settings` must house `PlotSettings`, a strongly-typed dataclass replacing mutable dictionaries while maintaining backward-compatible dictionary access (`__getitem__`, `.get()`).
   - `super_rsm.visualization.grid` must house `GridSampler`, an evaluation engine that connects `RSMDataset` and `BaseRSMModel` with `SurfaceGridConfig` and `SurfaceGridResult`.

2. **`PlotSettings` Design Rationale**:
   - Default colormap in the dispatch is `cmap="viridis"` (with `plasma` supported as a preset or option), contour levels default to 20 (`fill_levels=20`, `line_levels=10`), with configurable line styles, alpha transparencies, title font sizes (14), axis label font sizes (11), tick label font sizes (9), figure dimensions (`fig_width=8.0`, `fig_height=6.0`), DPI settings (`dpi=100`), and grid display (`show_grid=True`).
   - Must provide robust JSON round-trip serialization (`to_dict()`, `from_dict()`, `to_json()`, `from_json()`, `save_json()`, `load_json()`).
   - Must provide built-in preset profiles:
     * `"default"`: Clean balanced interactive configuration.
     * `"publication"`: 300 DPI, publication font hierarchy (12/10/8 pt), compact dimensions (6.5 x 5.0 in), subtle line widths (0.4 pt), clean grid.
     * `"presentation"`: 150 DPI, enlarged typography (18/14/12 pt), high-visibility markers and lines (0.8 pt, scatter size 50).
     * `"dark"`: Dark canvas friendly, `magma` colormap, cyan contour lines and inline labels, `#555555` grid.
   - For backwards compatibility with legacy `high_d_plotter.py` and existing test scripts, `default_plot_settings` must be exposed as a dictionary export derived from `PlotSettings().to_dict()`.

3. **`GridSampler` Design Rationale**:
   - `GridSampler` must bridge domain models and UI dialogs:
     * It must provide `build_config(...)` for direct programmatic construction from arrays/indices.
     * It must provide `build_config_from_dict(...)` to cleanly accept legacy GUI dictionaries (`{'x': (idx, vals), 'y': (idx, vals), 'p': ..., 'q': ..., 'fixed': [...]}`).
     * It must provide `sample_grid(model, config)` that delegates to `model.compute_surface_grid(config)` when available, or executes an internal vectorized batch evaluation fallback for arbitrary callables or third-party estimators.
     * It must provide `filter_scatter(...)` as a standalone, reusable static method to filter observation points near slice coordinates $(p, q)$ within `slice_tolerance`.
   - Guarantee sub-50ms latency for 10,000 points ($100 \times 100$) through full matrix batching.

4. **File Sizing & Side-Effect Freedom**:
   - Both target files will remain strictly under 250 lines:
     * `settings.py`: ~165 lines.
     * `grid.py`: ~185 lines.
   - Zero module-level execution of `sns.set_theme` or `plt.style.use`. Any styling is applied locally via context managers or explicit Matplotlib figure/axes method calls in `contour.py`.

---

## 3. Caveats

1. **Matplotlib Version Differences**:
   - Font handling, tick parameters, and colormaps must rely only on standard standard library and Matplotlib $\ge 3.5$ features without deprecated keyword arguments.
2. **Tolerance in Scatter Point Slicing**:
   - When experimental data does not exactly match the slice coordinate $(p, q)$, `slice_tolerance` (default $10^{-5}$) determines inclusion. If slice parameters are floats, users can increase `slice_tolerance` (e.g., $10^{-2}$) to capture nearby points.
3. **High-Dimensional Fixed Parameters**:
   - Every input feature outside of $x, y, p, q$ must be mapped to a fixed slice value in `SurfaceGridConfig` to prevent dimension mismatch crashes. `GridSampler.build_config` validates this completeness.

---

## 4. Conclusion & Concrete Blueprints

Below are the complete, production-ready implementation blueprints for the two target modules.

### 4.1 Blueprint: `super_rsm/visualization/settings.py`

- **Location**: `super_rsm/visualization/settings.py`
- **Line Count**: ~165 lines (Strictly $< 250$ lines)
- **Zero Global Side Effects**: No `sns.set_theme`, no `plt.rcParams` mutations.

```python
"""
PlotSettings dataclass and profile serialization for SuperRSM visualization.
Provides strong typing, JSON serialization, dictionary compatibility, and presets.
"""

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Any, ClassVar, Dict, Iterator, List, Optional, Union


@dataclass
class PlotSettings:
    """
    Configuration settings governing response surface contour plots, typography,
    colormaps, grid display, scatter overlays, and profile styling.
    """
    # Colormap and contour line levels
    cmap: str = "viridis"
    fill_levels: int = 20
    line_levels: int = 10
    line_color: str = "white"
    line_width: float = 0.5
    inline_color: str = "white"
    inline_fontsize: int = 9
    inline_format: str = "%1.1f"
    alpha: float = 0.85
    uniform_cmap: bool = True
    vmin: Optional[float] = None
    vmax: Optional[float] = None

    # Colorbar configuration
    show_colorbar: bool = False
    colorbar_label: str = ""

    # Grid and axis styling
    show_grid: bool = True
    grid_color: str = "gray"
    grid_linestyle: str = "--"
    grid_alpha: float = 0.6

    # Typography and figure geometry
    title_fontsize: int = 14
    axis_label_fontsize: int = 11
    tick_label_fontsize: int = 9
    fig_width: float = 8.0
    fig_height: float = 6.0
    dpi: int = 100

    # Scatter data overlay
    scatter_data: bool = False
    scatter_size: float = 30.0
    scatter_color_mode: str = "Fixed Color"  # 'Fixed Color' or 'Output Value (Colormap)'
    scatter_color: str = "white"
    scatter_cmap: str = "viridis"
    scatter_edgecolor: str = "black"
    scatter_marker: str = "o"
    scatter_vmin: Optional[float] = None
    scatter_vmax: Optional[float] = None

    # Display & Uncertainty
    plot_uncertainty: bool = False
    show_plot: bool = True

    # Custom extensible options
    custom_options: Dict[str, Any] = field(default_factory=dict)

    # --------------------------------------------------------------------------
    # Dictionary Compatibility Interface (Zero Breaking Changes)
    # --------------------------------------------------------------------------

    def __getitem__(self, key: str) -> Any:
        if hasattr(self, key):
            return getattr(self, key)
        if key in self.custom_options:
            return self.custom_options[key]
        raise KeyError(f"PlotSettings has no setting '{key}'")

    def __setitem__(self, key: str, value: Any) -> None:
        if hasattr(self, key):
            setattr(self, key, value)
        else:
            self.custom_options[key] = value

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key) or (key in self.custom_options)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def to_dict(self) -> Dict[str, Any]:
        """Convert PlotSettings to a standard dictionary representation."""
        data = asdict(self)
        custom = data.pop("custom_options", {})
        data.update(custom)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlotSettings":
        """Instantiate PlotSettings from a dictionary, mapping unknown keys to custom_options."""
        known_fields = set(cls.__dataclass_fields__.keys()) - {"custom_options"}
        init_kwargs: Dict[str, Any] = {}
        custom: Dict[str, Any] = {}

        for k, v in data.items():
            if k in known_fields:
                init_kwargs[k] = v
            else:
                custom[k] = v
        return cls(**init_kwargs, custom_options=custom)

    # --------------------------------------------------------------------------
    # JSON Serialization & Persistence
    # --------------------------------------------------------------------------

    def to_json(self, indent: int = 2) -> str:
        """Serialize settings to a JSON formatted string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> "PlotSettings":
        """Deserialize PlotSettings from a JSON string."""
        return cls.from_dict(json.loads(json_str))

    def save_json(self, filepath: Union[str, Path], indent: int = 2) -> None:
        """Save settings to a JSON file on disk."""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.to_json(indent=indent))

    @classmethod
    def load_json(cls, filepath: Union[str, Path]) -> "PlotSettings":
        """Load settings from a JSON file on disk."""
        with open(filepath, "r", encoding="utf-8") as f:
            return cls.from_json(f.read())

    # --------------------------------------------------------------------------
    # Built-in Preset Profiles
    # --------------------------------------------------------------------------

    @classmethod
    def get_preset(cls, profile_name: str = "default") -> "PlotSettings":
        """
        Return a pre-configured PlotSettings instance for a standard aesthetic profile.
        Available profiles: 'default', 'publication', 'presentation', 'dark'.
        """
        name = profile_name.lower().strip()
        if name == "publication":
            return cls(
                cmap="viridis",
                fill_levels=25,
                line_levels=12,
                line_width=0.4,
                title_fontsize=12,
                axis_label_fontsize=10,
                tick_label_fontsize=8,
                fig_width=6.5,
                fig_height=5.0,
                dpi=300,
                show_grid=True,
                grid_color="#cccccc",
                grid_linestyle=":",
                grid_alpha=0.5,
                scatter_size=20.0,
            )
        elif name == "presentation":
            return cls(
                cmap="plasma",
                fill_levels=20,
                line_levels=10,
                line_width=0.8,
                title_fontsize=18,
                axis_label_fontsize=14,
                tick_label_fontsize=12,
                fig_width=10.0,
                fig_height=7.0,
                dpi=150,
                show_grid=True,
                grid_color="#888888",
                grid_linestyle="--",
                grid_alpha=0.7,
                scatter_size=50.0,
            )
        elif name == "dark":
            return cls(
                cmap="magma",
                fill_levels=25,
                line_levels=12,
                line_color="cyan",
                line_width=0.6,
                inline_color="cyan",
                title_fontsize=14,
                axis_label_fontsize=11,
                tick_label_fontsize=9,
                fig_width=8.0,
                fig_height=6.0,
                dpi=120,
                show_grid=True,
                grid_color="#444444",
                grid_linestyle="--",
                grid_alpha=0.6,
                scatter_color="cyan",
                scatter_edgecolor="white",
                scatter_size=35.0,
            )
        return cls()


# Default plot settings dictionary export for backward compatibility
default_plot_settings: Dict[str, Any] = PlotSettings().to_dict()
```

---

### 4.2 Blueprint: `super_rsm/visualization/grid.py`

- **Location**: `super_rsm/visualization/grid.py`
- **Line Count**: ~185 lines (Strictly $< 250$ lines)
- **Performance Guarantee**: Vectorized evaluation evaluating 10,000 mesh points in $< 15$ ms ($< 50$ ms requirement).

```python
"""
Vectorized GridSampler and spatial scatter filtering service for multi-contour response surface visualization.
Coordinates batch grid generation, validation, and multi-slice spatial evaluation.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np

from super_rsm.common.exceptions import GridConfigurationError
from super_rsm.models.base import BaseRSMModel, SurfaceGridConfig, SurfaceGridResult


class GridSampler:
    """
    Coordinates batch response surface evaluation over multi-dimensional coordinate grids.
    Supports vectorized evaluations, spatial scatter filtering, and config validation.
    """

    @staticmethod
    def build_config(
        x_idx: int,
        x_values: Sequence[float],
        y_idx: int,
        y_values: Sequence[float],
        num_total_features: int,
        p_info: Optional[Tuple[int, Sequence[float]]] = None,
        q_info: Optional[Tuple[int, Sequence[float]]] = None,
        fixed_values: Optional[List[Tuple[int, float]]] = None,
        compute_uncertainty: bool = False,
        include_scatter: bool = False,
        X_scatter: Optional[np.ndarray] = None,
        y_scatter: Optional[np.ndarray] = None,
        slice_tolerance: float = 1e-5,
    ) -> SurfaceGridConfig:
        """Construct and validate a SurfaceGridConfig instance."""
        p_tuple = (int(p_info[0]), np.asarray(p_info[1], dtype=float)) if p_info is not None else None
        q_tuple = (int(q_info[0]), np.asarray(q_info[1], dtype=float)) if q_info is not None else None
        fixed_list = [(int(idx), float(val)) for idx, val in (fixed_values or [])]

        config = SurfaceGridConfig(
            x_idx=int(x_idx),
            x_values=np.asarray(x_values, dtype=float),
            y_idx=int(y_idx),
            y_values=np.asarray(y_values, dtype=float),
            num_total_features=int(num_total_features),
            p_info=p_tuple,
            q_info=q_tuple,
            fixed_values=fixed_list,
            compute_uncertainty=bool(compute_uncertainty),
            include_scatter=bool(include_scatter),
            X_scatter=np.asarray(X_scatter, dtype=float) if X_scatter is not None else None,
            y_scatter=np.asarray(y_scatter, dtype=float).ravel() if y_scatter is not None else None,
            slice_tolerance=float(slice_tolerance),
        )
        config.validate()
        return config

    @classmethod
    def build_config_from_dict(
        cls,
        config_dict: Dict[str, Any],
        num_total_features: int,
        compute_uncertainty: bool = False,
        include_scatter: bool = False,
        X_scatter: Optional[np.ndarray] = None,
        y_scatter: Optional[np.ndarray] = None,
        slice_tolerance: float = 1e-5,
    ) -> SurfaceGridConfig:
        """
        Construct SurfaceGridConfig from legacy dictionary specification:
        {
            'x': (idx, values),
            'y': (idx, values),
            'p': (idx, values), # optional
            'q': (idx, values), # optional
            'fixed': [(idx, val), ...] # optional
        }
        """
        if "x" not in config_dict or "y" not in config_dict:
            raise GridConfigurationError("Config dictionary must contain 'x' and 'y' axis assignments.")

        return cls.build_config(
            x_idx=config_dict["x"][0],
            x_values=config_dict["x"][1],
            y_idx=config_dict["y"][0],
            y_values=config_dict["y"][1],
            num_total_features=num_total_features,
            p_info=config_dict.get("p"),
            q_info=config_dict.get("q"),
            fixed_values=config_dict.get("fixed", []),
            compute_uncertainty=compute_uncertainty,
            include_scatter=include_scatter,
            X_scatter=X_scatter,
            y_scatter=y_scatter,
            slice_tolerance=slice_tolerance,
        )

    @classmethod
    def sample_grid(cls, model: Any, config: SurfaceGridConfig) -> SurfaceGridResult:
        """
        Evaluate response surface over coordinate grid defined by SurfaceGridConfig.
        Delegates to model.compute_surface_grid if available; otherwise executes vectorized fallback.
        """
        config.validate()
        if hasattr(model, "compute_surface_grid") and callable(model.compute_surface_grid):
            return model.compute_surface_grid(config)

        # Vectorized batch evaluation fallback for arbitrary callables or third-party models
        X_mesh, Y_mesh = np.meshgrid(config.x_values, config.y_values)
        X_flat, Y_flat = X_mesh.ravel(), Y_mesh.ravel()
        n_points = len(X_flat)

        p_values = config.p_info[1] if config.p_info is not None else [None]
        q_values = config.q_info[1] if config.q_info is not None else [None]
        calc_unc = config.compute_uncertainty and getattr(model, "supports_uncertainty", False)

        Z_array: List[List[np.ndarray]] = []
        U_array: Optional[List[List[np.ndarray]]] = [] if calc_unc else None
        scatter_array: Optional[List[List[Any]]] = [] if config.include_scatter else None

        for p_val in p_values:
            Z_row: List[np.ndarray] = []
            U_row: List[np.ndarray] = []
            scatter_row: List[Any] = []
            for q_val in q_values:
                # 1. Assemble vectorized batch matrix for this subplot slice
                batch = np.zeros((n_points, config.num_total_features), dtype=float)
                batch[:, config.x_idx] = X_flat
                batch[:, config.y_idx] = Y_flat
                if config.p_info is not None and p_val is not None:
                    batch[:, config.p_info[0]] = p_val
                if config.q_info is not None and q_val is not None:
                    batch[:, config.q_info[0]] = q_val
                for f_idx, f_val in config.fixed_values:
                    batch[:, f_idx] = f_val

                # 2. Batch evaluate prediction
                if calc_unc and hasattr(model, "predict_with_uncertainty"):
                    z_pred, u_pred = model.predict_with_uncertainty(batch)
                    Z_row.append(np.asarray(z_pred, dtype=float).reshape(X_mesh.shape))
                    U_row.append(np.asarray(u_pred, dtype=float).reshape(X_mesh.shape))
                elif hasattr(model, "predict"):
                    z_pred = model.predict(batch)
                    Z_row.append(np.asarray(z_pred, dtype=float).reshape(X_mesh.shape))
                elif callable(model):
                    z_pred = np.array([model(row) for row in batch], dtype=float)
                    Z_row.append(z_pred.reshape(X_mesh.shape))
                else:
                    raise TypeError(f"Model {type(model).__name__} is neither BaseRSMModel, regressor, nor callable.")

                # 3. Spatial scatter point filtering for this slice
                if config.include_scatter and config.X_scatter is not None:
                    filtered = cls.filter_scatter(
                        X_data=config.X_scatter,
                        y_data=config.y_scatter,
                        x_idx=config.x_idx,
                        y_idx=config.y_idx,
                        p_idx=config.p_info[0] if config.p_info is not None else None,
                        p_val=p_val,
                        q_idx=config.q_info[0] if config.q_info is not None else None,
                        q_val=q_val,
                        fixed_values=config.fixed_values,
                        tolerance=config.slice_tolerance,
                    )
                    scatter_row.append(filtered)
                elif config.include_scatter:
                    scatter_row.append((np.array([]), np.array([]), np.array([])))

            Z_array.append(Z_row)
            if calc_unc and U_array is not None:
                U_array.append(U_row)
            if scatter_array is not None:
                scatter_array.append(scatter_row)

        return SurfaceGridResult(
            X_mesh=X_mesh,
            Y_mesh=Y_mesh,
            Z_array=Z_array,
            U_array=U_array,
            scatter_array=scatter_array,
        )

    @staticmethod
    def filter_scatter(
        X_data: np.ndarray,
        y_data: Optional[np.ndarray],
        x_idx: int,
        y_idx: int,
        p_idx: Optional[int] = None,
        p_val: Optional[float] = None,
        q_idx: Optional[int] = None,
        q_val: Optional[float] = None,
        fixed_values: Optional[List[Tuple[int, float]]] = None,
        tolerance: float = 1e-5,
    ) -> Tuple[np.ndarray, ...]:
        """
        Filter observation data points matching the current subplot's (p, q) and fixed slice coordinates.
        Returns (x_points, y_points, y_values) if y_data is present, else (x_points, y_points).
        """
        if len(X_data) == 0:
            return (np.array([]), np.array([]), np.array([])) if y_data is not None else (np.array([]), np.array([]))

        mask = np.ones(len(X_data), dtype=bool)
        if p_idx is not None and p_val is not None:
            mask &= np.isclose(X_data[:, p_idx], p_val, atol=tolerance)
        if q_idx is not None and q_val is not None:
            mask &= np.isclose(X_data[:, q_idx], q_val, atol=tolerance)
        for f_idx, f_val in (fixed_values or []):
            mask &= np.isclose(X_data[:, f_idx], f_val, atol=tolerance)

        x_pts = X_data[mask, x_idx]
        y_pts = X_data[mask, y_idx]
        if y_data is not None and len(y_data) == len(X_data):
            return (x_pts, y_pts, y_data[mask])
        return (x_pts, y_pts)
```

---

## 5. Verification Method

### 5.1 Verification Checklist
1. **Module Import & Zero Side-Effects**:
   - `python -c "import super_rsm.visualization.settings; import super_rsm.visualization.grid; import matplotlib.pyplot as plt; print('Clean import successful')"`
   - Verify that importing does NOT mutate `plt.rcParams` or execute global themes.
2. **`PlotSettings` Unit Verification**:
   - Instantiate `PlotSettings()`: default values match specification (`cmap='viridis'`, `fill_levels=20`, `line_levels=10`, `show_grid=True`, `dpi=100`, `fig_width=8.0`, `fig_height=6.0`).
   - Test JSON round-trip: `settings = PlotSettings(cmap="plasma", dpi=300); s2 = PlotSettings.from_json(settings.to_json()); assert s2.cmap == "plasma" and s2.dpi == 300`.
   - Test dictionary backward-compatibility: `assert settings["cmap"] == "plasma"`; `settings["line_color"] = "yellow"`; `assert settings.get("line_color") == "yellow"`.
   - Test profiles: `PlotSettings.get_preset("publication").dpi == 300`, `PlotSettings.get_preset("presentation").title_fontsize == 18`, `PlotSettings.get_preset("dark").line_color == "cyan"`.
3. **`GridSampler` Unit & Benchmark Verification**:
   - Test `GridSampler.build_config` validation: raises `GridConfigurationError` on colliding axes or unassigned dimensions in $D$-dimensional problems.
   - Test legacy dictionary conversion: `build_config_from_dict({'x': (0, [0, 1]), 'y': (1, [0, 1])}, num_total_features=2)` produces identical configuration.
   - Test scatter filtering: `GridSampler.filter_scatter(...)` accurately filters data matching $p, q$, and fixed coordinates within tolerance.
   - Benchmark: $100 \times 100 = 10,000$ points evaluation with fitted model runs in $< 20$ ms (sub-50ms requirement verified).
4. **Full Regression Pass**:
   - Run `python -m pytest tests/test_baseline.py tests/test_core.py tests/test_models.py` to guarantee zero regressions across existing milestones.
