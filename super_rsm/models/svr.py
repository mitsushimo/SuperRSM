"""
Support Vector Regression (SVR) surrogate model with input/target standardization,
smooth kernel response surfaces, variance partition / Lack-of-Fit ANOVA, and factor sensitivity.
"""

from typing import Any, ClassVar, Dict, List, Optional
import numpy as np
from sklearn.compose import TransformedTargetRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

from super_rsm.common.config import HyperparameterSpec, ModelMetadata
from super_rsm.common.types import ModelCategory
from super_rsm.models.base import BaseRSMModel, ModelMetrics
from super_rsm.models.diagnostics import build_anova_table, compute_factor_sensitivity
from super_rsm.models.registry import register_model


@register_model
class SVRRSMModel(BaseRSMModel):
    """
    Support Vector Regression surrogate model with smooth kernel basis (RBF, Poly, Sigmoid)
    and epsilon-insensitive loss for outlier-resistant response surface modeling.
    """

    metadata: ClassVar[ModelMetadata] = ModelMetadata(
        name="SVR",
        display_name="Support Vector Regression (SVR)",
        category=ModelCategory.KERNEL,
        description="Outlier-robust kernel Support Vector Regression with smooth response surfaces and factor sensitivity.",
        supports_uncertainty=False,
        supports_coefficients=False,
        supports_feature_importance=True,
        supports_formula=False,
        has_anova=True,
        hyperparameters=[
            HyperparameterSpec("kernel", "Kernel Type", str, default="rbf", choices=["rbf", "poly", "sigmoid"],
                               tooltip="Kernel basis function type"),
            HyperparameterSpec("C", "Regularization (C)", float, default=10.0, min_val=0.01, max_val=1000.0, step=1.0,
                               tooltip="Box constraint penalty parameter C"),
            HyperparameterSpec("epsilon", "Epsilon Tube (ε)", float, default=0.05, min_val=0.0001, max_val=5.0, step=0.02,
                               tooltip="Epsilon-insensitive loss tube half-width (in standardized target units)"),
            HyperparameterSpec("degree_fit", "Poly Degree", int, default=3, min_val=1, max_val=5, step=1,
                               tooltip="Degree for 'poly' kernel (ignored for rbf/sigmoid)"),
        ],
    )

    def __init__(
        self,
        kernel: str = "rbf",
        C: float = 10.0,
        epsilon: float = 0.05,
        degree_fit: int = 3,
        **kwargs: Any,
    ):
        super().__init__(kernel=kernel, C=C, epsilon=epsilon, degree_fit=degree_fit, **kwargs)
        self.kernel = kernel
        self.C = C
        self.epsilon = epsilon
        self.degree_fit = degree_fit
        self.pipeline: Optional[Any] = None
        self._feature_importance: Optional[Dict[str, float]] = None

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> "SVRRSMModel":
        """Fit standardized SVR surrogate model and compute variance ANOVA & factor sensitivity."""
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

        svr = SVR(
            kernel=str(self.kernel),
            C=float(self.C),
            epsilon=float(self.epsilon),
            degree=int(self.degree_fit),
            gamma="scale",
        )
        base_pipe = make_pipeline(StandardScaler(), svr)
        self.pipeline = TransformedTargetRegressor(regressor=base_pipe, transformer=StandardScaler())
        self.pipeline.fit(X_arr, y_arr)

        self.X_train = X_arr
        self.y_train = y_arr
        self.is_fitted = True

        y_pred = self.predict(X_arr)
        mse = float(mean_squared_error(y_arr, y_pred))
        rmse = float(np.sqrt(mse))
        mae = float(np.mean(np.abs(y_arr - y_pred)))
        r2 = float(r2_score(y_arr, y_pred))

        fitted_svr = self.pipeline.regressor_.named_steps["svr"]
        n_sv = int(len(fitted_svr.support_))
        n_samples = len(X_arr)
        anova_df = build_anova_table(y_arr, y_pred, df_model=None, X=X_arr)
        self._feature_importance = compute_factor_sensitivity(self.predict, X_arr, self.feature_names)

        self.metrics = ModelMetrics(
            r2=r2,
            rmse=rmse,
            mse=mse,
            mae=mae,
            anova_table=anova_df,
            custom_metrics={
                "Kernel Type": str(self.kernel),
                "Regularization (C)": f"{float(self.C):.4g}",
                "Epsilon Tube (ε)": f"{float(self.epsilon):.4g}",
                "Support Vectors": f"{n_sv} / {n_samples} ({100.0 * n_sv / max(1, n_samples):.1f}%)",
            },
        )
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Compute predicted output for input coordinates X."""
        self._ensure_fitted()
        X_arr = np.asarray(X, dtype=float)
        if X_arr.ndim == 1:
            X_arr = X_arr.reshape(1, -1) if len(X_arr) == len(self.feature_names) else X_arr.reshape(-1, 1)
        return np.asarray(self.pipeline.predict(X_arr), dtype=float).ravel()

    def get_feature_importance(self) -> Optional[Dict[str, float]]:
        """Return first-order main-effect variance sensitivity across input factors."""
        self._ensure_fitted()
        return self._feature_importance

