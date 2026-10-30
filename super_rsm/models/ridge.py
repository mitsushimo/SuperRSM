"""
RidgeCV Regressor with Polynomial Features and analytical unscaling.
Extracts true physical coefficients and handles cross-validation.
"""

from typing import Any, ClassVar, Dict, List, Optional
import numpy as np
from sklearn.linear_model import RidgeCV
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

from super_rsm.common.config import HyperparameterSpec, ModelMetadata
from super_rsm.common.types import ModelCategory
from super_rsm.models.base import BaseRSMModel, ModelMetrics
from super_rsm.models.registry import register_model


def _generate_polynomial_term_names(column_names: List[str], poly: PolynomialFeatures) -> List[str]:
    """Generate standardized term name strings from polynomial feature powers."""
    terms = []
    for power in poly.powers_:
        term = []
        for col, p in zip(column_names, power):
            if p == 1:
                term.append(col)
            elif p > 1:
                term.append(f"{col}^{p}")
        terms.append(" ".join(term))
    return terms


@register_model
class RidgeCVRSMModel(BaseRSMModel):
    """
    Ridge regression with cross-validation on polynomial features.
    Extracts unscaled physical coefficients and prevents overfitting.
    """

    metadata: ClassVar[ModelMetadata] = ModelMetadata(
        name="RidgeCV",
        display_name="RidgeCV (L2 Regularized Polynomial)",
        category=ModelCategory.POLYNOMIAL,
        description="Ridge regression with cross-validation on polynomial features and analytical unscaling.",
        supports_uncertainty=False,
        supports_coefficients=True,
        supports_feature_importance=True,
        supports_formula=True,
        has_anova=False,
        hyperparameters=[
            HyperparameterSpec("degree_fit", "Polynomial Degree", int, default=2, min_val=1, max_val=4, step=1,
                               tooltip="Degree of polynomial feature expansions"),
            HyperparameterSpec("alphas_count", "Alpha Grid Count", int, default=13, min_val=5, max_val=50, step=1,
                               tooltip="Number of log-spaced alpha penalty values"),
            HyperparameterSpec("cv", "CV Folds", int, default=5, min_val=2, max_val=10, step=1,
                               tooltip="Number of cross-validation folds"),
        ],
    )

    def __init__(
        self,
        degree_fit: int = 2,
        alphas_count: int = 13,
        cv: Optional[int] = 5,
        **kwargs: Any,
    ):
        super().__init__(degree_fit=degree_fit, alphas_count=alphas_count, cv=cv, **kwargs)
        self.degree_fit = degree_fit
        self.alphas_count = alphas_count
        self.cv = cv
        self.pipeline: Optional[Any] = None
        self.unscaled_coeffs: Optional[np.ndarray] = None
        self.unscaled_intercept: Optional[float] = None
        self.term_names: List[str] = []

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> "RidgeCVRSMModel":
        """Fit RidgeCV pipeline with polynomial expansion and unscale coefficients."""
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)
                self.hyperparameters[k] = v

        if self.degree_fit < 1:
            raise ValueError(f"degree_fit must be >= 1, got {self.degree_fit}")

        X_arr = np.asarray(X, dtype=float)
        y_arr = np.asarray(y, dtype=float).ravel()
        if X_arr.ndim == 1:
            X_arr = X_arr.reshape(-1, 1)

        self.feature_names = (
            list(feature_names) if feature_names is not None else [f"x{i+1}" for i in range(X_arr.shape[1])]
        )

        n_samples = len(X_arr)
        cv_actual = None if (self.cv is None or n_samples < 5) else self.cv
        alphas = np.logspace(-6, 6, self.alphas_count)

        self.pipeline = make_pipeline(
            PolynomialFeatures(degree=self.degree_fit, include_bias=False),
            StandardScaler(),
            RidgeCV(alphas=alphas, cv=cv_actual),
        )
        self.pipeline.fit(X_arr, y_arr)
        self.X_train = X_arr
        self.y_train = y_arr
        self.is_fitted = True

        scaler = self.pipeline.named_steps["standardscaler"]
        ridge = self.pipeline.named_steps["ridgecv"]
        poly = self.pipeline.named_steps["polynomialfeatures"]

        self.term_names = _generate_polynomial_term_names(self.feature_names, poly)
        safe_scale = np.where(scaler.scale_ > 1e-12, scaler.scale_, 1.0)
        self.unscaled_coeffs = ridge.coef_ / safe_scale
        self.unscaled_intercept = float(ridge.intercept_ - np.dot(self.unscaled_coeffs, scaler.mean_))

        y_pred = self.pipeline.predict(X_arr)
        mse = mean_squared_error(y_arr, y_pred)
        rmse = float(np.sqrt(mse))
        r2 = r2_score(y_arr, y_pred)
        self.metrics = ModelMetrics(r2=float(r2), rmse=rmse, mse=float(mse))
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Compute predicted output for input coordinates X."""
        self._ensure_fitted()
        X_arr = np.asarray(X, dtype=float)
        if X_arr.ndim == 1:
            X_arr = X_arr.reshape(1, -1) if len(X_arr) == len(self.feature_names) else X_arr.reshape(-1, 1)
        y_pred = self.pipeline.predict(X_arr)
        return np.asarray(y_pred, dtype=float).ravel()

    def get_coefficients(self) -> Dict[str, float]:
        """Return dictionary mapping physical term names to unscaled coefficients."""
        self._ensure_fitted()
        coeffs: Dict[str, float] = {"Intercept": float(self.unscaled_intercept)}
        for term, coeff in zip(self.term_names, self.unscaled_coeffs):
            coeffs[term] = float(coeff)
        return coeffs

    def get_formula(self) -> str:
        """Return human-readable algebraic equation."""
        self._ensure_fitted()
        parts = [f"{self.unscaled_intercept:.4f}"]
        for term, coeff in zip(self.term_names, self.unscaled_coeffs):
            if abs(coeff) < 1e-8:
                continue
            if coeff > 0:
                parts.append(f"+ {coeff:.4f}*{term}")
            else:
                parts.append(f"- {abs(coeff):.4f}*{term}")
        return f"y = {' '.join(parts)}"

    def get_feature_importance(self) -> Dict[str, float]:
        """Return normalized relative importances based on standardized coefficients."""
        self._ensure_fitted()
        ridge = self.pipeline.named_steps["ridgecv"]
        abs_c = np.abs(ridge.coef_)
        total = np.sum(abs_c)
        if total == 0:
            total = 1.0
        return {term: float(c / total) for term, c in zip(self.term_names, abs_c)}
