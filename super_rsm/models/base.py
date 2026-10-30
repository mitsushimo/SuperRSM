"""
Abstract base class and grid evaluation schemas for all SuperRSM regression models.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, List, Optional, Sequence, Set, Tuple, Union
import numpy as np

from super_rsm.common.config import ModelMetadata
from super_rsm.common.exceptions import (
    GridConfigurationError,
    ModelNotFittedError,
    UncertaintyNotSupportedError,
)


@dataclass
class ModelMetrics:
    """Standardized goodness-of-fit and statistical evaluation metrics."""
    r2: float
    adj_r2: Optional[float] = None
    rmse: float = 0.0
    mse: float = 0.0
    mae: Optional[float] = None
    aic: Optional[float] = None
    bic: Optional[float] = None
    term_p_values: Optional[Dict[str, float]] = None
    term_t_stats: Optional[Dict[str, float]] = None
    term_std_errors: Optional[Dict[str, float]] = None
    anova_table: Optional[Any] = None
    custom_metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SurfaceGridConfig:
    """
    Configuration for vectorized multi-contour response surface grid generation.
    Enforces total dimension coverage to prevent silent zero-fill artifacts.
    """
    x_idx: int
    x_values: np.ndarray
    y_idx: int
    y_values: np.ndarray
    num_total_features: int
    p_info: Optional[Tuple[int, np.ndarray]] = None
    q_info: Optional[Tuple[int, np.ndarray]] = None
    fixed_values: List[Tuple[int, float]] = field(default_factory=list)
    compute_uncertainty: bool = False
    include_scatter: bool = False
    X_scatter: Optional[np.ndarray] = None
    y_scatter: Optional[np.ndarray] = None
    slice_tolerance: float = 1e-5

    def validate(self) -> None:
        """Validate dimension completeness and check for index collisions."""
        if self.x_idx == self.y_idx:
            raise GridConfigurationError(f"x_idx and y_idx must be distinct: {self.x_idx}")
        assigned: Set[int] = {self.x_idx, self.y_idx}

        if self.p_info is not None:
            if self.p_info[0] in assigned:
                raise GridConfigurationError(f"p_info dimension {self.p_info[0]} collides with assigned axes.")
            if len(self.p_info[1]) == 0:
                raise GridConfigurationError("p_info values array cannot be empty.")
            assigned.add(self.p_info[0])

        if self.q_info is not None:
            if self.q_info[0] in assigned:
                raise GridConfigurationError(f"q_info dimension {self.q_info[0]} collides with assigned axes.")
            if len(self.q_info[1]) == 0:
                raise GridConfigurationError("q_info values array cannot be empty.")
            assigned.add(self.q_info[0])

        for f_idx, _ in self.fixed_values:
            if f_idx in assigned:
                raise GridConfigurationError(f"Fixed value dimension {f_idx} collides with assigned axes.")
            assigned.add(f_idx)

        missing = set(range(self.num_total_features)) - assigned
        if missing:
            raise GridConfigurationError(
                f"Dimensions {sorted(list(missing))} are unassigned in SurfaceGridConfig for "
                f"{self.num_total_features}-D model. All dimensions must be mapped."
            )


@dataclass
class SurfaceGridResult:
    """Result of batch response surface grid evaluation."""
    X_mesh: np.ndarray
    Y_mesh: np.ndarray
    Z_array: List[List[np.ndarray]]
    U_array: Optional[List[List[np.ndarray]]] = None
    scatter_array: Optional[List[List[Any]]] = None


class BaseRSMModel(ABC):
    """
    Abstract Base Class that all SuperRSM regression models inherit from.
    Provides standard fitting, vectorized prediction, diagnostic metrics, and surface batching.
    """
    metadata: ClassVar[ModelMetadata]

    @classmethod
    def get_metadata(cls) -> ModelMetadata:
        """Return static model metadata describing capabilities and hyperparameter schema."""
        if not hasattr(cls, "metadata") or cls.metadata is None:
            raise NotImplementedError(f"Subclass {cls.__name__} must define a 'metadata' ClassVar.")
        return cls.metadata

    def __init__(self, **hyperparameters: Any):
        self.hyperparameters: Dict[str, Any] = hyperparameters
        self.is_fitted: bool = False
        self.feature_names: List[str] = []
        self.X_train: Optional[np.ndarray] = None
        self.y_train: Optional[np.ndarray] = None
        self.metrics: Optional[ModelMetrics] = None

    @abstractmethod
    def fit(self, X: np.ndarray, y: np.ndarray, feature_names: Optional[List[str]] = None, **kwargs: Any) -> "BaseRSMModel":
        """Fit model on training inputs X (N, D) and target output y (N,)."""
        pass

    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Compute predicted output values for a batch of input coordinates X of shape (N, D)."""
        pass

    def predict_with_uncertainty(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Compute predicted mean and predictive standard deviation for 2D batch X of shape (N, D)."""
        if not self.get_metadata().supports_uncertainty:
            raise UncertaintyNotSupportedError(f"Model '{self.get_metadata().name}' does not support predictive uncertainty.")
        raise NotImplementedError(f"Subclass {self.__class__.__name__} must implement predict_with_uncertainty.")

    def evaluate_point(self, point: Union[np.ndarray, Sequence[float]], return_std: bool = False) -> Tuple[float, Optional[float]]:
        """Evaluate fitted model at a single coordinate point and return scalar float outputs."""
        self._ensure_fitted()
        X_batch = np.asarray(point, dtype=float).reshape(1, -1)
        if return_std:
            if not self.get_metadata().supports_uncertainty:
                raise UncertaintyNotSupportedError(f"Model '{self.get_metadata().name}' does not support predictive uncertainty.")
            y_pred, sigma = self.predict_with_uncertainty(X_batch)
            return float(y_pred[0]), float(sigma[0])
        y_pred = self.predict(X_batch)
        return float(y_pred[0]), None

    def get_metrics(self) -> ModelMetrics:
        """Return cached goodness-of-fit and statistical evaluation metrics."""
        self._ensure_fitted()
        if self.metrics is None:
            raise RuntimeError("Model metrics have not been initialized.")
        return self.metrics

    def get_formula(self) -> Optional[str]:
        """Return human-readable equation or discovered symbolic expression."""
        return None

    def get_coefficients(self) -> Optional[Dict[str, float]]:
        """Return dictionary mapping physical variable/interaction term names to unscaled coefficients."""
        return None

    def get_feature_importance(self) -> Optional[Dict[str, float]]:
        """Return dictionary mapping feature names to normalized relative importances."""
        return None

    def compute_surface_grid(self, config: SurfaceGridConfig) -> SurfaceGridResult:
        """Fast vectorized multi-contour response surface batch evaluation."""
        self._ensure_fitted()
        config.validate()

        X_mesh, Y_mesh = np.meshgrid(config.x_values, config.y_values)
        X_flat, Y_flat = X_mesh.ravel(), Y_mesh.ravel()
        n_points = len(X_flat)

        p_values = config.p_info[1] if config.p_info is not None else [None]
        q_values = config.q_info[1] if config.q_info is not None else [None]
        calc_unc = config.compute_uncertainty and self.get_metadata().supports_uncertainty

        Z_array: List[List[np.ndarray]] = []
        U_array: Optional[List[List[np.ndarray]]] = [] if calc_unc else None
        scatter_array: Optional[List[List[Any]]] = [] if config.include_scatter else None

        for p_val in p_values:
            Z_row, U_row, scatter_row = [], [], []
            for q_val in q_values:
                batch = np.zeros((n_points, config.num_total_features), dtype=float)
                batch[:, config.x_idx], batch[:, config.y_idx] = X_flat, Y_flat
                if config.p_info is not None and p_val is not None:
                    batch[:, config.p_info[0]] = p_val
                if config.q_info is not None and q_val is not None:
                    batch[:, config.q_info[0]] = q_val
                for f_idx, f_val in config.fixed_values:
                    batch[:, f_idx] = f_val

                if calc_unc:
                    z_pred, u_pred = self.predict_with_uncertainty(batch)
                    Z_row.append(z_pred.reshape(X_mesh.shape))
                    U_row.append(u_pred.reshape(X_mesh.shape))
                else:
                    Z_row.append(self.predict(batch).reshape(X_mesh.shape))

                if config.include_scatter and config.X_scatter is not None:
                    mask = np.ones(len(config.X_scatter), dtype=bool)
                    if config.p_info is not None and p_val is not None:
                        mask &= np.isclose(config.X_scatter[:, config.p_info[0]], p_val, atol=config.slice_tolerance)
                    if config.q_info is not None and q_val is not None:
                        mask &= np.isclose(config.X_scatter[:, config.q_info[0]], q_val, atol=config.slice_tolerance)
                    for f_idx, f_val in config.fixed_values:
                        mask &= np.isclose(config.X_scatter[:, f_idx], f_val, atol=config.slice_tolerance)

                    if config.y_scatter is not None and len(config.y_scatter) == len(config.X_scatter):
                        scatter_row.append((
                            config.X_scatter[mask, config.x_idx],
                            config.X_scatter[mask, config.y_idx],
                            config.y_scatter[mask],
                        ))
                    else:
                        scatter_row.append((
                            config.X_scatter[mask, config.x_idx],
                            config.X_scatter[mask, config.y_idx],
                        ))
                else:
                    scatter_row.append((np.array([]), np.array([]), np.array([])))

            Z_array.append(Z_row)
            if calc_unc and U_array is not None:
                U_array.append(U_row)
            if scatter_array is not None:
                scatter_array.append(scatter_row)

        return SurfaceGridResult(
            X_mesh=X_mesh, Y_mesh=Y_mesh, Z_array=Z_array,
            U_array=U_array, scatter_array=scatter_array,
        )

    def _ensure_fitted(self) -> None:
        """Internal helper verifying that model is fitted."""
        if not self.is_fitted:
            raise ModelNotFittedError(f"Model '{self.get_metadata().name}' must be fitted before calling this method.")

