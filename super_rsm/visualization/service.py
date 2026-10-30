"""
High-level visualization coordination façade for SuperRSM.
Coordinates GridSampler and MultiContourEngine to generate publication-quality
response surface plots with zero global side-effects, headless execution,
and seamless backward compatibility for legacy configs and visualize_rsm().
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

from super_rsm.common.exceptions import UncertaintyNotSupportedError
from super_rsm.models.base import SurfaceGridConfig, SurfaceGridResult
from super_rsm.visualization.contour import MultiContourEngine
from super_rsm.visualization.grid import GridSampler
from super_rsm.visualization.settings import PlotSettings

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

        if settings.plot_uncertainty:
            supports_unc = getattr(result, "supports_uncertainty", False)
            if not supports_unc and hasattr(result, "model") and hasattr(result.model, "get_metadata"):
                supports_unc = result.model.get_metadata().supports_uncertainty
            if not supports_unc:
                method = getattr(result, "method", "Current model")
                raise UncertaintyNotSupportedError(f"Uncertainty plotting is not supported for {method}.")

        grid_config = cls._resolve_config(config, result, settings)
        model = getattr(result, "model", result)
        grid_result = GridSampler.sample(model, grid_config)

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
            show=show,
            save_path=save_path,
        )
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
        return MultiContourEngine.render(
            grid_result=grid_result, settings=settings, title=title,
            xlabel=xlabel, ylabel=ylabel, label_array=label_array,
            show=show, save_path=save_path,
        )

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
        num_features = getattr(getattr(result, "dataset", None), "num_features", None)
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
            return GridSampler.build_config_from_dict(
                config_dict=config,
                num_total_features=num_features,
                compute_uncertainty=settings.plot_uncertainty,
                include_scatter=settings.scatter_data,
                X_scatter=X_scatter,
                y_scatter=y_scatter,
            )

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
