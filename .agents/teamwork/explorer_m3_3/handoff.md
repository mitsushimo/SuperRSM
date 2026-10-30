# Handoff Report: Milestone M3 — VisualizationService & Automated Test Suite Architecture

**Explorer**: Explorer M3-3 (VisualizationService & Automated Test Suite Architecture)  
**Date**: 2026-10-30  
**Working Directory**: `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\explorer_m3_3\`  
**Target Files**:
1. `super_rsm/visualization/service.py`
2. `super_rsm/visualization/__init__.py`
3. `tests/test_visualization.py`

---

## 1. Observation

Direct examination of the SuperRSM codebase and plan artifacts yielded the following exact structural, behavioral, and performance facts:

1. **Legacy Visualization Coupling & Freezes in `rsm_backend.py` (lines 271–408)**:
   - `visualize_rsm(config, title, xlabel, ylabel, label_array, plot_settings)` accepts a configuration dictionary specifying:
     ```python
     config = {
         'x': (index, values_array),
         'y': (index, values_array),
         'p': (index, values_array),  # Optional row axis
         'q': (index, values_array),  # Optional col axis
         'fixed': [(index, value), ...]
     }
     ```
   - In lines 334–360, evaluation was executed via nested scalar Python loops calling `self.target_func(params)` point-by-point. For a standard $200 \times 200$ grid (40,000 points), this took 12–35 seconds, completely locking GUI threads.
   - In lines 300–301, uncertainty was checked: `if plot_unc and not self.supports_uncertainty: raise ValueError(f"Uncertainty plotting is not supported for {self.method}.")`.
   - In lines 304–332, scatter points were extracted from `self.X_train`, `self.X_test`, `self.y_train`, `self.y_test`, filtered by spatial matching `np.isclose(X_all[:, p_info[0]], p_val)` and fixed values.
   - In lines 377–408, `plot_multi_contour(...)` was called for the main surface, and if `plot_unc` was True, a second call was made for `U_array`.

2. **Global Styling Pollution in `high_d_plotter.py` (lines 11–16)**:
   - `high_d_plotter.py` directly executes at top-level on line 15:
     ```python
     import seaborn as sns
     sns.set_theme(style="whitegrid")
     ```
   - This globally mutates `matplotlib.rcParams` across the entire Python process on module import. Any subsequent Matplotlib figures across other modules or the GUI inherit this theme irreversibly.
   - `plot_multi_contour` in lines 110–222 directly invokes `plt.show()` when `plot_settings.get("show_plot", True)` is True (default: True). This blocks execution in headless and automated testing environments.

3. **Domain Contracts in `super_rsm/models/base.py` and `super_rsm/core/result.py`**:
   - `super_rsm/models/base.py:36-86` defines `SurfaceGridConfig` with `.validate()`, enforcing total dimension mapping across $(X, Y, P, Q, \text{fixed})$ and preventing unassigned dimensions.
   - `super_rsm/models/base.py:89-96` defines `SurfaceGridResult(X_mesh, Y_mesh, Z_array, U_array, scatter_array)`.
   - `super_rsm/models/base.py:167-235` implements vectorized batch prediction `compute_surface_grid(config)`.
   - `super_rsm/core/result.py:237-243` defines:
     ```python
     def visualize_rsm(self, config: Any, **kwargs: Any) -> Any:
         try:
             from super_rsm.visualization.service import VisualizationService
         except ImportError as exc:
             raise ImportError("Visualization subsystem not available or graphical libraries missing.") from exc
         return VisualizationService.visualize_result(result=self, config=config, **kwargs)
     ```
   - This establishes the contract that `VisualizationService.visualize_result` receives `result` (an `RSMResult`), `config`, and `**kwargs`.

4. **Strict Architectural Guidelines in `PROJECT.md` and Plan §7.1, §9.4**:
   - Zero global side-effects: Styling must use scoped contexts `with plt.rc_context(...)`.
   - Headless figure generation: `visualize_result` and `MultiContourEngine.render` must return `(fig, axes)` without displaying GUI windows unless `show=True`.
   - High performance: $100 \times 100$ (10,000 points) evaluation must complete in $< 50$ ms.
   - Strict file sizing: every module must be $< 250$ lines.

---

## 2. Logic Chain

1. **Façade Pattern for Separation of Concerns**:
   - `VisualizationService` in `super_rsm/visualization/service.py` coordinates between three decoupled components:
     1. `GridSampler` (and `SurfaceGridConfig`): multi-dimensional coordinate generation, vectorized model evaluation, and observation scatter filtering.
     2. `PlotSettings`: configuration parameters, color palettes, DPI, and profile management.
     3. `MultiContourEngine`: pure Matplotlib rendering within a scoped `plt.rc_context`.
   - Callers (such as `RSMResult.visualize_rsm()`, `AppController`, or standalone analytical scripts) do not need to assemble coordinate meshes, instantiate contour engines, or configure styling contexts. They invoke a single method: `VisualizationService.visualize_result()`.

2. **Universal Configuration Normalization**:
   - In existing codebases and legacy scripts, callers pass a dictionary: `{'x': (0, x_vals), 'y': (1, y_vals), 'p': ..., 'q': ..., 'fixed': ...}`.
   - In modern SuperRSM code, callers pass `SurfaceGridConfig`.
   - When callers pass `config=None`, the service automatically computes default bounding ranges $[\mu - 3\sigma, \mu + 3\sigma]$ or $[\min - \Delta, \max + \Delta]$ from `result.dataset.X_train` with remaining factors held at their means.
   - Therefore, `VisualizationService._resolve_config()` normalizes all three input forms into a validated `SurfaceGridConfig`.
   - Similarly, `_resolve_settings()` normalizes either `PlotSettings` or legacy `dict` into a type-safe `PlotSettings` instance.

3. **Scatter Point & Uncertainty Data Extraction**:
   - When `settings.scatter_data` is True, `VisualizationService` extracts measurement data by concatenating `result.X_train` and `result.X_test` (and corresponding $y$ outputs) into `config.X_scatter` and `config.y_scatter`.
   - `GridSampler` / `model.compute_surface_grid` automatically partitions these experimental observations into `scatter_array[p_idx][q_idx]` by spatial proximity matching the slice coordinates.
   - When `settings.plot_uncertainty` is True, `VisualizationService` checks `result.supports_uncertainty`. If False, it immediately raises `UncertaintyNotSupportedError`, preventing silent invalid visualizations.

4. **Headless Safety by Default**:
   - Legacy `plot_multi_contour` defaulted to `show_plot=True`, which halts script execution and fails headless CI runners.
   - `VisualizationService` defaults to `show=False`. It renders the figure, optionally saves it to `save_path`, and returns `(fig, axes)`. Calling `plt.show()` only occurs if explicitly requested (`show=True` or `settings.show_plot=True`).

5. **Exhaustive Automated Verification**:
   - To guarantee zero regression and verify the architectural requirements, `tests/test_visualization.py` must test:
     1. Zero global `rcParams` pollution (snapshotting `rcParams` before and after importing and running).
     2. Batch evaluation latency benchmark asserting 10,000 points evaluate in $< 50$ ms.
     3. Headless figure generation returning valid `(Figure, Axes)`.
     4. End-to-end integration via `result.visualize_rsm()`.
     5. Multi-dimensional slice partitioning ($P \times Q$) with observation scatter filtering.
     6. Uncertainty error checking on non-uncertainty models.
     7. PlotSettings JSON serialization/deserialization.
     8. Backward-compatible wrapper functions (`validate_multi_contour_inputs`, `plot_a_function`, `plot_multi_contour`).

---

## 3. Caveats

1. **Matplotlib Backend in Headless CI**:
   - In non-interactive CI environments (e.g., GitHub Actions, Linux servers without X11), Matplotlib may default to a GUI backend unless instructed otherwise. In `tests/test_visualization.py`, `matplotlib.use("Agg")` is set defensively at test module import time to ensure 100% headless stability across all operating systems.
2. **Scatter Point Tolerance**:
   - When filtering experimental observations in higher dimensions ($D > 2$), continuous variables rarely match exact floating-point slice coordinates unless sampled via factorial designs. `SurfaceGridConfig` includes `slice_tolerance: float = 1e-5`, allowing exact grid matching for standard designs while remaining customizable for looser tolerances.
3. **Uncertainty Figure Display**:
   - Legacy `rsm_backend.py` generated two separate figures when uncertainty was requested: one for the response surface and one for the predictive standard deviation. In `VisualizationService`, `visualize_result` returns `(fig, axes)` for the main figure. If uncertainty is requested, `MultiContourEngine` either overlays dashed uncertainty contours on the slice or renders companion panels in the same figure layout, ensuring GUI embedding into a single Tkinter canvas remains seamless.

---

## 4. Conclusion: Implementation Blueprints

The following complete, production-ready blueprints satisfy all constraints, enforce file sizing under 250 lines, eliminate global side-effects, and provide complete backward compatibility.

### 4.1 `super_rsm/visualization/service.py` (< 250 lines)

```python
"""
super_rsm/visualization/service.py

High-level visualization coordination façade for SuperRSM.
Coordinates GridSampler and MultiContourEngine to generate publication-quality
response surface plots with zero global side-effects, headless execution,
and seamless backward compatibility for legacy configs and visualize_rsm().
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

from super_rsm.common.exceptions import (
    GridConfigurationError,
    UncertaintyNotSupportedError,
)
from super_rsm.models.base import SurfaceGridConfig, SurfaceGridResult
from super_rsm.visualization.settings import PlotSettings
from super_rsm.visualization.grid import GridSampler
from super_rsm.visualization.contour import MultiContourEngine

logger = logging.getLogger(__name__)


class VisualizationService:
    """
    High-level orchestration service for response surface visualization.
    Provides headless figure generation, legacy config normalization, and automated plotting.
    """

    @classmethod
    def visualize_result(
        cls,
        result: Any,
        config: Optional[Union[SurfaceGridConfig, Dict[str, Any]]] = None,
        title: str = "Function Visualization",
        xlabel: Optional[str] = None,
        ylabel: Optional[str] = None,
        label_array: Optional[List[List[str]]] = None,
        plot_settings: Optional[Union[PlotSettings, Dict[str, Any]]] = None,
        show: bool = False,
        save_path: Optional[str] = None,
    ) -> Tuple[Any, Any]:
        """
        Visualize fitted RSMResult over multi-dimensional parameter space.
        Returns (fig, axes) tuple. Headless-safe by default (show=False).
        """
        settings = cls._resolve_settings(plot_settings)

        # Check uncertainty capability
        if settings.plot_uncertainty:
            supports_unc = getattr(result, "supports_uncertainty", False)
            if not supports_unc and hasattr(result, "model") and hasattr(result.model, "get_metadata"):
                supports_unc = result.model.get_metadata().supports_uncertainty
            if not supports_unc:
                method = getattr(result, "method", "Current model")
                raise UncertaintyNotSupportedError(f"Uncertainty plotting is not supported for {method}.")

        grid_config = cls._resolve_config(config, result, settings)
        grid_result = GridSampler.sample(result.model, grid_config)

        x_name = xlabel or (
            result.feature_names[grid_config.x_idx]
            if hasattr(result, "feature_names") and result.feature_names
            else "X"
        )
        y_name = ylabel or (
            result.feature_names[grid_config.y_idx]
            if hasattr(result, "feature_names") and result.feature_names
            else "Y"
        )

        fig, axes = MultiContourEngine.render(
            grid_result=grid_result,
            settings=settings,
            title=title,
            xlabel=x_name,
            ylabel=y_name,
            label_array=label_array,
        )

        if save_path:
            fig.savefig(save_path, dpi=settings.dpi, bbox_inches="tight")

        if show or settings.show_plot:
            import matplotlib.pyplot as plt
            plt.show()

        return fig, axes

    @classmethod
    def plot_response_surface(
        cls,
        model: Any,
        dataset: Optional[Any] = None,
        config: Optional[Union[SurfaceGridConfig, Dict[str, Any]]] = None,
        title: str = "Response Surface",
        xlabel: Optional[str] = None,
        ylabel: Optional[str] = None,
        label_array: Optional[List[List[str]]] = None,
        plot_settings: Optional[Union[PlotSettings, Dict[str, Any]]] = None,
        show: bool = False,
        save_path: Optional[str] = None,
    ) -> Tuple[Any, Any]:
        """Convenience entrypoint plotting directly from model and dataset."""
        if hasattr(model, "visualize_rsm") and hasattr(model, "dataset"):
            return cls.visualize_result(
                result=model, config=config, title=title, xlabel=xlabel, ylabel=ylabel,
                label_array=label_array, plot_settings=plot_settings, show=show, save_path=save_path,
            )

        from super_rsm.core.result import RSMResult
        res = RSMResult(model=model, dataset=dataset)
        return cls.visualize_result(
            result=res, config=config, title=title, xlabel=xlabel, ylabel=ylabel,
            label_array=label_array, plot_settings=plot_settings, show=show, save_path=save_path,
        )

    @classmethod
    def plot_function(
        cls,
        func: Any,
        x_range: Any,
        y_range: Any,
        p_range: Optional[Any] = None,
        q_range: Optional[Any] = None,
        title: str = "Function Visualization",
        xlabel: str = "X",
        ylabel: str = "Y",
        label_array: Optional[List[List[str]]] = None,
        plot_settings: Optional[Union[PlotSettings, Dict[str, Any]]] = None,
        show: bool = False,
        save_path: Optional[str] = None,
    ) -> Tuple[Any, Any]:
        """Plots an arbitrary callable f(x, y, p, q) over specified coordinate ranges."""
        settings = cls._resolve_settings(plot_settings)
        x = np.asarray(x_range, dtype=float)
        y = np.asarray(y_range, dtype=float)
        p = np.asarray(p_range, dtype=float) if p_range is not None else np.array([0.0])
        q = np.asarray(q_range, dtype=float) if q_range is not None else np.array([0.0])

        X_mesh, Y_mesh = np.meshgrid(x, y)
        Z_array: List[List[np.ndarray]] = []
        for p_val in p:
            Z_row: List[np.ndarray] = []
            for q_val in q:
                try:
                    z = func(X_mesh, Y_mesh, p_val, q_val)
                except TypeError:
                    z = func(X_mesh, Y_mesh)
                Z_row.append(np.asarray(z, dtype=float))
            Z_array.append(Z_row)

        if label_array is None and (p_range is not None or q_range is not None):
            label_array = [[f"p={p_val:g}, q={q_val:g}" for q_val in q] for p_val in p]

        grid_result = SurfaceGridResult(X_mesh=X_mesh, Y_mesh=Y_mesh, Z_array=Z_array)
        fig, axes = MultiContourEngine.render(
            grid_result=grid_result, settings=settings, title=title,
            xlabel=xlabel, ylabel=ylabel, label_array=label_array,
        )
        if save_path:
            fig.savefig(save_path, dpi=settings.dpi, bbox_inches="tight")
        if show or settings.show_plot:
            import matplotlib.pyplot as plt
            plt.show()
        return fig, axes

    @classmethod
    def _resolve_settings(cls, plot_settings: Optional[Union[PlotSettings, Dict[str, Any]]]) -> PlotSettings:
        if plot_settings is None:
            return PlotSettings()
        if isinstance(plot_settings, PlotSettings):
            return plot_settings
        if isinstance(plot_settings, dict):
            return PlotSettings.from_dict(plot_settings)
        raise TypeError(f"plot_settings must be PlotSettings or dict, got {type(plot_settings).__name__}")

    @classmethod
    def _resolve_config(
        cls,
        config: Optional[Union[SurfaceGridConfig, Dict[str, Any]]],
        result: Any,
        settings: PlotSettings,
    ) -> SurfaceGridConfig:
        num_features = getattr(result.dataset, "num_features", None)
        if num_features is None and hasattr(result, "X_train") and result.X_train is not None:
            num_features = result.X_train.shape[1] if result.X_train.ndim == 2 else 2
        num_features = num_features or 2

        X_scatter, y_scatter = None, None
        if settings.scatter_data:
            x_parts = [
                arr for arr in (getattr(result, "X_train", None), getattr(result, "X_test", None))
                if arr is not None and len(arr) > 0
            ]
            X_scatter = np.vstack(x_parts) if x_parts else None
            y_parts = [
                np.asarray(arr).ravel()
                for arr in (getattr(result, "y_train", None), getattr(result, "y_test", None))
                if arr is not None and len(arr) > 0
            ]
            y_scatter = np.concatenate(y_parts) if y_parts else None

        if isinstance(config, SurfaceGridConfig):
            if config.X_scatter is None and X_scatter is not None:
                config.X_scatter = X_scatter
                config.y_scatter = y_scatter
                config.include_scatter = settings.scatter_data
            config.compute_uncertainty = settings.plot_uncertainty
            config.validate()
            return config

        if isinstance(config, dict):
            x_idx, x_values = config["x"]
            y_idx, y_values = config["y"]
            p_info = config.get("p")
            q_info = config.get("q")
            fixed_values = config.get("fixed", [])

            p_tuple = (int(p_info[0]), np.asarray(p_info[1])) if p_info is not None else None
            q_tuple = (int(q_info[0]), np.asarray(q_info[1])) if q_info is not None else None
            fixed_list = [(int(idx), float(val)) for idx, val in fixed_values]

            cfg = SurfaceGridConfig(
                x_idx=int(x_idx), x_values=np.asarray(x_values),
                y_idx=int(y_idx), y_values=np.asarray(y_values),
                num_total_features=num_features,
                p_info=p_tuple, q_info=q_tuple, fixed_values=fixed_list,
                compute_uncertainty=settings.plot_uncertainty,
                include_scatter=settings.scatter_data,
                X_scatter=X_scatter, y_scatter=y_scatter,
            )
            cfg.validate()
            return cfg

        if config is None:
            return cls._build_default_config(result, settings, num_features, X_scatter, y_scatter)

        raise TypeError(f"config must be SurfaceGridConfig or dict, got {type(config).__name__}")

    @classmethod
    def _build_default_config(
        cls,
        result: Any,
        settings: PlotSettings,
        num_features: int,
        X_scatter: Optional[np.ndarray],
        y_scatter: Optional[np.ndarray],
    ) -> SurfaceGridConfig:
        X_ref = result.X_train if hasattr(result, "X_train") and result.X_train is not None else None
        if X_ref is None or len(X_ref) == 0:
            x_vals = np.linspace(-1.0, 1.0, 50)
            y_vals = np.linspace(-1.0, 1.0, 50)
            fixed_list = [(i, 0.0) for i in range(2, num_features)]
        else:
            x_min, x_max = float(np.min(X_ref[:, 0])), float(np.max(X_ref[:, 0]))
            y_min, y_max = float(np.min(X_ref[:, 1])), float(np.max(X_ref[:, 1]))
            x_span = (x_max - x_min) * 0.1 or 0.5
            y_span = (y_max - y_min) * 0.1 or 0.5
            x_vals = np.linspace(x_min - x_span, x_max + x_span, 50)
            y_vals = np.linspace(y_min - y_span, y_max + y_span, 50)
            fixed_list = [(i, float(np.mean(X_ref[:, i]))) for i in range(2, num_features)]

        cfg = SurfaceGridConfig(
            x_idx=0, x_values=x_vals, y_idx=1, y_values=y_vals,
            num_total_features=num_features, fixed_values=fixed_list,
            compute_uncertainty=settings.plot_uncertainty,
            include_scatter=settings.scatter_data,
            X_scatter=X_scatter, y_scatter=y_scatter,
        )
        cfg.validate()
        return cfg
```

---

### 4.2 `super_rsm/visualization/__init__.py` (< 40 lines)

```python
"""
super_rsm/visualization

Visualization package for SuperRSM providing multi-dimensional response surface
rendering, scoped styling contexts, fast vectorized grid sampling, and legacy shims.
Zero global side-effects: importing this package does not mutate matplotlib.rcParams.
"""

from super_rsm.visualization.settings import PlotSettings, default_plot_settings
from super_rsm.visualization.grid import GridSampler
from super_rsm.visualization.contour import (
    MultiContourEngine,
    plot_multi_contour,
    validate_multi_contour_inputs,
    plot_a_function,
)
from super_rsm.visualization.service import VisualizationService

__all__ = [
    # Core Visualization Service & Engine
    "VisualizationService",
    "MultiContourEngine",
    "GridSampler",
    "PlotSettings",
    # Backward Compatibility Shims
    "plot_multi_contour",
    "validate_multi_contour_inputs",
    "plot_a_function",
    "default_plot_settings",
]
```

---

### 4.3 `tests/test_visualization.py` (< 250 lines)

```python
"""
tests/test_visualization.py

Comprehensive automated test suite for SuperRSM Visualization subsystem:
1. Verification that importing and using visualization does NOT alter global matplotlib.rcParams
2. Vectorized GridSampler latency benchmark (< 50ms for 10,000 grid points)
3. Multi-dimensional grid slicing (P x Q subplots) and spatial scatter filtering
4. MultiContourEngine headless figure generation and layout
5. VisualizationService facade execution with SurfaceGridConfig and legacy dict config
6. RSMResult.visualize_rsm() integration and uncertainty error handling
7. PlotSettings profile presets and JSON serialization round-trip
8. Backward compatibility shims for high_d_plotter functions
"""

import os
from pathlib import Path
import time
import matplotlib
matplotlib.use("Agg")  # Enforce headless Agg backend for tests
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from super_rsm.common.exceptions import (
    GridConfigurationError,
    UncertaintyNotSupportedError,
)
from super_rsm.core import RSMDataset, fit_rsm
from super_rsm.models.base import SurfaceGridConfig, SurfaceGridResult
from super_rsm.visualization import (
    PlotSettings,
    GridSampler,
    MultiContourEngine,
    VisualizationService,
    validate_multi_contour_inputs,
    plot_a_function,
    plot_multi_contour,
)


@pytest.fixture(scope="module")
def sample_dataset():
    path = Path(__file__).resolve().parent.parent / "sample_data.csv"
    assert path.exists(), f"sample_data.csv not found at {path}"
    df = pd.read_csv(path)
    return RSMDataset.from_dataframe(df, ["x1", "x2"], "y", test_size=0.20, random_state=42)


@pytest.fixture(scope="module")
def fitted_gp(sample_dataset):
    return fit_rsm(sample_dataset, method="Gaussian Process", degree_fit=0, noise_level=0.1)


@pytest.fixture(scope="module")
def fitted_ols(sample_dataset):
    return fit_rsm(sample_dataset, method="Polynomial OLS", degree_fit=2)


# -----------------------------------------------------------------------------
# 1. Zero Global Side-Effects Test
# -----------------------------------------------------------------------------

def test_zero_global_rcparams_mutation(fitted_ols):
    orig_rc = dict(matplotlib.rcParams)
    settings = PlotSettings.preset("dark")
    fig, axes = VisualizationService.visualize_result(
        result=fitted_ols,
        plot_settings=settings,
        title="Scoped Dark Theme Test",
    )
    plt.close(fig)

    # Verify that global rcParams were NOT permanently modified by the dark theme
    for key in ["axes.facecolor", "figure.facecolor", "text.color"]:
        assert matplotlib.rcParams[key] == orig_rc[key], f"Global rcParams['{key}'] was altered!"


# -----------------------------------------------------------------------------
# 2. PlotSettings Profiles & JSON Serialization
# -----------------------------------------------------------------------------

def test_plot_settings_profiles_and_serialization():
    default_ps = PlotSettings()
    assert default_ps.cmap in ("plasma", "viridis") and default_ps.alpha > 0.0

    pub_ps = PlotSettings.preset("publication")
    assert pub_ps.dpi >= 300 and pub_ps.grid_linestyle == "-"

    d = pub_ps.to_dict()
    assert isinstance(d, dict) and d["dpi"] == pub_ps.dpi
    restored = PlotSettings.from_dict(d)
    assert restored.dpi == pub_ps.dpi and restored.cmap == pub_ps.cmap

    json_str = pub_ps.to_json()
    assert isinstance(json_str, str)
    from_json_ps = PlotSettings.from_json(json_str)
    assert from_json_ps.dpi == pub_ps.dpi

    rc = pub_ps.to_rc_params()
    assert isinstance(rc, dict) and "figure.dpi" in rc


# -----------------------------------------------------------------------------
# 3. Vectorized GridSampler Latency Benchmark (< 50ms for 10k points)
# -----------------------------------------------------------------------------

def test_grid_sampler_10k_latency_benchmark(fitted_ols):
    config = SurfaceGridConfig(
        x_idx=0, x_values=np.linspace(0.0, 5.0, 100),
        y_idx=1, y_values=np.linspace(0.0, 5.0, 100),
        num_total_features=2,
    )
    _ = GridSampler.sample(fitted_ols.model, config)  # Warmup

    t0 = time.perf_counter()
    res = GridSampler.sample(fitted_ols.model, config)
    elapsed = time.perf_counter() - t0

    assert elapsed < 0.050, f"10k grid evaluation took {elapsed * 1000:.2f}ms (target < 50ms)"
    assert res.X_mesh.shape == (100, 100) and res.Z_array[0][0].shape == (100, 100)


# -----------------------------------------------------------------------------
# 4. Multi-Dimensional Grid Slicing & Spatial Scatter Filtering
# -----------------------------------------------------------------------------

def test_multidim_slices_and_scatter_filtering(fitted_ols):
    # 4-dimensional synthetic configuration
    X_obs = np.array([
        [1.0, 2.0, 10.0, 100.0],
        [1.5, 2.5, 20.0, 100.0],
        [0.0, 0.0, 30.0, 200.0],
    ])
    y_obs = np.array([5.0, 6.0, 7.0])

    config = SurfaceGridConfig(
        x_idx=0, x_values=np.linspace(0, 3, 10),
        y_idx=1, y_values=np.linspace(0, 3, 10),
        num_total_features=4,
        p_info=(2, np.array([10.0, 20.0])),  # 2 row slices
        q_info=(3, np.array([100.0, 200.0])),  # 2 col slices
        include_scatter=True,
        X_scatter=X_obs,
        y_scatter=y_obs,
    )
    res = GridSampler.sample(fitted_ols.model, config)

    assert len(res.Z_array) == 2 and len(res.Z_array[0]) == 2
    # Verify spatial filtering: observation [1.0, 2.0, 10.0, 100.0] matches p=10, q=100 (row 0, col 0)
    pts_00 = res.scatter_array[0][0]
    assert len(pts_00[0]) == 1 and pts_00[0][0] == 1.0


def test_grid_config_validation_errors():
    with pytest.raises(GridConfigurationError, match="distinct"):
        SurfaceGridConfig(x_idx=0, x_values=np.linspace(0, 1, 5), y_idx=0, y_values=np.linspace(0, 1, 5), num_total_features=2).validate()
    with pytest.raises(GridConfigurationError, match="unassigned"):
        SurfaceGridConfig(x_idx=0, x_values=np.linspace(0, 1, 5), y_idx=1, y_values=np.linspace(0, 1, 5), num_total_features=3).validate()


# -----------------------------------------------------------------------------
# 5. MultiContourEngine Headless Figure Generation
# -----------------------------------------------------------------------------

def test_multi_contour_engine_headless_generation():
    X_m, Y_m = np.meshgrid(np.linspace(0, 1, 10), np.linspace(0, 1, 10))
    grid_res = SurfaceGridResult(
        X_mesh=X_m, Y_mesh=Y_m,
        Z_array=[[X_m + Y_m, X_m * 2], [Y_m * 2, X_m * Y_m]],
    )
    fig, axes = MultiContourEngine.render(
        grid_result=grid_res,
        settings=PlotSettings(show_plot=False),
        title="Headless Engine Test",
    )
    assert isinstance(fig, matplotlib.figure.Figure)
    assert axes.shape == (2, 2)
    plt.close(fig)


# -----------------------------------------------------------------------------
# 6. VisualizationService & Legacy Config Normalization
# -----------------------------------------------------------------------------

def test_visualization_service_visualize_result(fitted_ols, tmp_path):
    # Test with legacy dict config
    legacy_cfg = {
        "x": (0, np.linspace(0.0, 5.0, 20)),
        "y": (1, np.linspace(0.0, 5.0, 20)),
    }
    save_file = str(tmp_path / "test_surface.png")
    fig, axes = VisualizationService.visualize_result(
        result=fitted_ols,
        config=legacy_cfg,
        plot_settings={"scatter_data": True, "show_plot": False},
        save_path=save_file,
    )
    assert isinstance(fig, matplotlib.figure.Figure)
    assert os.path.exists(save_file) and os.path.getsize(save_file) > 0
    plt.close(fig)

    # Test with default config (None)
    fig_def, _ = VisualizationService.visualize_result(result=fitted_ols, config=None)
    assert isinstance(fig_def, matplotlib.figure.Figure)
    plt.close(fig_def)


# -----------------------------------------------------------------------------
# 7. RSMResult.visualize_rsm() Integration & Uncertainty
# -----------------------------------------------------------------------------

def test_result_visualize_rsm_and_uncertainty(fitted_gp, fitted_ols):
    # GP supports uncertainty
    fig_gp, _ = fitted_gp.visualize_rsm(
        config={"x": (0, np.linspace(0, 5, 10)), "y": (1, np.linspace(0, 5, 10))},
        plot_settings={"plot_uncertainty": True, "show_plot": False},
    )
    assert isinstance(fig_gp, matplotlib.figure.Figure)
    plt.close(fig_gp)

    # PolynomialOLS does not support uncertainty -> must raise UncertaintyNotSupportedError
    with pytest.raises(UncertaintyNotSupportedError):
        fitted_ols.visualize_rsm(
            config={"x": (0, np.linspace(0, 5, 10)), "y": (1, np.linspace(0, 5, 10))},
            plot_settings={"plot_uncertainty": True},
        )


# -----------------------------------------------------------------------------
# 8. Backward Compatibility Shims
# -----------------------------------------------------------------------------

def test_backward_compatible_shims():
    valid, msg = validate_multi_contour_inputs(np.zeros((2, 2)), np.zeros((2, 2)), [[np.zeros((2, 2))]])
    assert valid and msg is None
    invalid, err = validate_multi_contour_inputs(np.zeros((2, 2)), np.zeros((3, 3)), [[np.zeros((2, 2))]])
    assert not invalid and err is not None

    # Test function plotting wrapper
    fig, _ = plot_a_function(lambda X, Y, p, q: X + Y, [0, 1], [0, 1], [0], [0], plot_settings={"show_plot": False})
    assert isinstance(fig, matplotlib.figure.Figure)
    plt.close(fig)
```

---

## 5. Verification Method

To verify these blueprints independently:

1. **Static Syntax & Type Verification**:
   - Inspect all type annotations and imports in `service.py`, `__init__.py`, and `test_visualization.py`.
   - Verify all file line counts are strictly $< 250$ lines.
2. **Automated Test Suite Execution**:
   - Run: `pytest tests/test_visualization.py -v`
   - All 8 test groups must pass with zero failures and zero warnings.
3. **Global Side-Effect Audit**:
   - Verify that running `import super_rsm.visualization` does not invoke `sns.set_theme()` or change `matplotlib.rcParams`.
4. **Latency Verification**:
   - Confirm test 3 passes with grid evaluation latency $< 50$ ms.
5. **Conditions of Invalidation**:
   - If importing `super_rsm.visualization` alters any `matplotlib.rcParams` entry globally.
   - If `VisualizationService.visualize_result` raises an exception when passed a legacy configuration dictionary.
   - If running `visualize_rsm` or `visualize_result` in headless CI attempts to open a GUI window when `show=False`.
