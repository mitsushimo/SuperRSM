"""
Gaussian Process Regressor (Kriging) with uncertainty estimation.
Supports Ordinary Kriging (degree=0) and Universal Kriging (degree>0).
"""

from typing import Any, ClassVar, List, Optional, Tuple
import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import DotProduct, RBF, WhiteKernel
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

from super_rsm.common.config import HyperparameterSpec, ModelMetadata
from super_rsm.common.types import ModelCategory
from super_rsm.models.base import BaseRSMModel, ModelMetrics
from super_rsm.models.registry import register_model


@register_model
class GaussianProcessRSMModel(BaseRSMModel):
    """
    Gaussian Process Regressor (Kriging) supporting Ordinary (degree=0)
    and Universal Kriging (degree>0) with predictive uncertainty estimation.
    """

    metadata: ClassVar[ModelMetadata] = ModelMetadata(
        name="Gaussian Process",
        display_name="Gaussian Process (Kriging)",
        category=ModelCategory.KERNEL,
        description="Gaussian Process Regressor supporting Ordinary (degree=0) and Universal Kriging (degree>0).",
        supports_uncertainty=True,
        supports_coefficients=False,
        supports_feature_importance=False,
        supports_formula=False,
        has_anova=False,
        hyperparameters=[
            HyperparameterSpec("degree_fit", "Polynomial Degree", int, default=2, min_val=0, max_val=4, step=1,
                               tooltip="Polynomial trend degree (0=Ordinary Kriging, >0=Universal Kriging)"),
            HyperparameterSpec("length_scale", "RBF Length Scale", float, default=1.0, min_val=0.01, max_val=100.0, step=0.5,
                               tooltip="Initial RBF length scale parameter"),
            HyperparameterSpec("noise_level", "Noise Level", float, default=0.1, min_val=1e-5, max_val=10.0, step=0.05,
                               tooltip="WhiteKernel observation noise variance level"),
            HyperparameterSpec("n_restarts_optimizer", "Optimizer Restarts", int, default=0, min_val=0, max_val=10, step=1,
                               tooltip="Number of kernel hyperparameter optimizer restarts"),
            HyperparameterSpec("random_state", "Random State", int, default=42, min_val=0, max_val=99999, step=1,
                               tooltip="Random seed for search reproducibility"),
        ],
    )

    def __init__(
        self,
        degree_fit: int = 2,
        length_scale: float = 1.0,
        noise_level: float = 0.1,
        n_restarts_optimizer: int = 0,
        random_state: int = 42,
        **kwargs: Any,
    ):
        super().__init__(
            degree_fit=degree_fit,
            length_scale=length_scale,
            noise_level=noise_level,
            n_restarts_optimizer=n_restarts_optimizer,
            random_state=random_state,
            **kwargs,
        )
        self.degree_fit = degree_fit
        self.length_scale = length_scale
        self.noise_level = noise_level
        self.n_restarts_optimizer = n_restarts_optimizer
        self.random_state = random_state
        self.pipeline: Optional[Any] = None

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> "GaussianProcessRSMModel":
        """Fit Gaussian Process model on training data."""
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)
                self.hyperparameters[k] = v

        X_arr = np.asarray(X, dtype=float)
        y_arr = np.asarray(y, dtype=float).ravel()
        if X_arr.ndim == 1:
            X_arr = X_arr.reshape(-1, 1)

        self.feature_names = (
            list(feature_names) if feature_names is not None else [f"x{i+1}" for i in range(X_arr.shape[1])]
        )

        if self.degree_fit == 0:
            kernel = 1.0 * RBF(length_scale=self.length_scale) + WhiteKernel(noise_level=self.noise_level)
            gp = GaussianProcessRegressor(
                kernel=kernel,
                normalize_y=True,
                n_restarts_optimizer=self.n_restarts_optimizer,
                random_state=self.random_state,
            )
            self.pipeline = make_pipeline(StandardScaler(), gp)
        else:
            kernel = (
                DotProduct(sigma_0=1.0)
                + RBF(length_scale=self.length_scale)
                + WhiteKernel(noise_level=self.noise_level)
            )
            gp = GaussianProcessRegressor(
                kernel=kernel,
                normalize_y=False,
                n_restarts_optimizer=self.n_restarts_optimizer,
                random_state=self.random_state,
            )
            self.pipeline = make_pipeline(
                PolynomialFeatures(degree=self.degree_fit, include_bias=False),
                StandardScaler(),
                gp,
            )

        self.pipeline.fit(X_arr, y_arr)
        self.X_train = X_arr
        self.y_train = y_arr
        self.is_fitted = True

        y_pred = self.pipeline.predict(X_arr)
        mse = mean_squared_error(y_arr, y_pred)
        rmse = float(np.sqrt(mse))
        r2 = r2_score(y_arr, y_pred)
        self.metrics = ModelMetrics(r2=float(r2), rmse=rmse, mse=float(mse))
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Compute predicted mean output for input coordinates X."""
        self._ensure_fitted()
        X_arr = np.asarray(X, dtype=float)
        if X_arr.ndim == 1:
            X_arr = X_arr.reshape(1, -1) if len(X_arr) == len(self.feature_names) else X_arr.reshape(-1, 1)
        y_pred = self.pipeline.predict(X_arr)
        return np.asarray(y_pred, dtype=float).ravel()

    def predict_with_uncertainty(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Compute predicted mean and predictive standard deviation."""
        self._ensure_fitted()
        X_arr = np.asarray(X, dtype=float)
        if X_arr.ndim == 1:
            X_arr = X_arr.reshape(1, -1) if len(X_arr) == len(self.feature_names) else X_arr.reshape(-1, 1)
        y_pred, sigma = self.pipeline.predict(X_arr, return_std=True)
        return np.asarray(y_pred, dtype=float).ravel(), np.asarray(sigma, dtype=float).ravel()
