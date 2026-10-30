"""
Vectorized GridSampler and spatial scatter filtering service for multi-contour response surface visualization.
Coordinates batch grid generation, validation, and multi-slice spatial evaluation.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple
import numpy as np

from super_rsm.common.exceptions import GridConfigurationError
from super_rsm.models.base import SurfaceGridConfig, SurfaceGridResult


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
        Construct SurfaceGridConfig from dictionary specification:
        {'x': (idx, values), 'y': (idx, values), 'p': ..., 'q': ..., 'fixed': ...}
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
                batch = np.zeros((n_points, config.num_total_features), dtype=float)
                batch[:, config.x_idx] = X_flat
                batch[:, config.y_idx] = Y_flat
                if config.p_info is not None and p_val is not None:
                    batch[:, config.p_info[0]] = p_val
                if config.q_info is not None and q_val is not None:
                    batch[:, config.q_info[0]] = q_val
                for f_idx, f_val in config.fixed_values:
                    batch[:, f_idx] = f_val

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

    @classmethod
    def sample(cls, model: Any, config: SurfaceGridConfig) -> SurfaceGridResult:
        """Alias for sample_grid."""
        return cls.sample_grid(model, config)

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
