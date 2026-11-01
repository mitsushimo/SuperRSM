"""
Bayesian Ridge Polynomial Regressor with posterior parameter covariance and predictive uncertainty.
Provides closed-form unscaled polynomial equations, exact posterior t-statistics/p-values,
ANOVA table decomposition, and predictive standard deviation (±1σ).
"""

from typing import Any, ClassVar, Dict, List, Optional, Tuple
import numpy as np
from sklearn.linear_model import BayesianRidge
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

from super_rsm.common.config import HyperparameterSpec, ModelMetadata
from super_rsm.common.types import ModelCategory
from super_rsm.models.base import BaseRSMModel, ModelMetrics
from super_rsm.models.diagnostics import build_anova_table, compute_regularized_term_stats
from super_rsm.models.registry import register_model
from super_rsm.models.ridge import _generate_polynomial_term_names


@register_model
class BayesianRidgeRSMModel(BaseRSMModel):
    """
    Empirical Bayes polynomial regression model.
    Combines parametric polynomial interpretability (coefficients, formula, t-scores, ANOVA)
    with Bayesian predictive uncertainty estimation (±1σ).
    """

    metadata: ClassVar[ModelMetadata] = ModelMetadata(
        name="Bayesian Ridge",
        display_name="Bayesian Ridge (Probabilistic Polynomial)",
        category=ModelCategory.POLYNOMIAL,
        description="Bayesian polynomial regression with automatic evidence regularization, t-scores, ANOVA, and ±1σ uncertainty.",
        supports_uncertainty=True,
        supports_coefficients=True,
        supports_feature_importance=True,
        supports_formula=True,
        has_anova=True,
        hyperparameters=[
            HyperparameterSpec("degree_fit", "Polynomial Degree", int, default=2, min_val=1, max_val=4, step=1,
                               tooltip="Degree of polynomial feature expansions"),
            HyperparameterSpec("max_iter", "Max Iterations", int, default=300, min_val=50, max_val=2000, step=50,
                               tooltip="Maximum number of evidence maximization iterations"),
            HyperparameterSpec("tol", "Convergence Tolerance", float, default=1e-3, min_val=1e-6, max_val=1e-1, step=1e-3,
                               tooltip="Convergence threshold for marginal log-likelihood"),
        ],
    )

    def __init__(
        self,
        degree_fit: int = 2,
        max_iter: int = 300,
        tol: float = 1e-3,
        **kwargs: Any,
    ):
        super().__init__(degree_fit=degree_fit, max_iter=max_iter, tol=tol, **kwargs)
        self.degree_fit = degree_fit
        self.max_iter = max_iter
        self.tol = tol
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
    ) -> "BayesianRidgeRSMModel":
        """Fit Bayesian Ridge polynomial pipeline and compute posterior diagnostics."""
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

        self.pipeline = make_pipeline(
            PolynomialFeatures(degree=self.degree_fit, include_bias=False),
            StandardScaler(),
            BayesianRidge(max_iter=int(self.max_iter), tol=float(self.tol)),
        )
        self.pipeline.fit(X_arr, y_arr)
        self.X_train = X_arr
        self.y_train = y_arr
        self.is_fitted = True

        poly = self.pipeline.named_steps["polynomialfeatures"]
        scaler = self.pipeline.named_steps["standardscaler"]
        br = self.pipeline.named_steps["bayesianridge"]

        self.term_names = _generate_polynomial_term_names(self.feature_names, poly)
        safe_scale = np.where(scaler.scale_ > 1e-12, scaler.scale_, 1.0)
        self.unscaled_coeffs = br.coef_ / safe_scale
        self.unscaled_intercept = float(br.intercept_ - np.dot(self.unscaled_coeffs, scaler.mean_))

        y_pred = self.pipeline.predict(X_arr)
        mse = float(mean_squared_error(y_arr, y_pred))
        rmse = float(np.sqrt(mse))
        mae = float(np.mean(np.abs(y_arr - y_pred)))
        r2 = float(r2_score(y_arr, y_pred))

        Z_std = scaler.transform(poly.transform(X_arr))
        l2_eff = float(br.lambda_ / max(1e-15, br.alpha_))
        diag = compute_regularized_term_stats(
            Z_std=Z_std,
            y=y_arr,
            y_pred=y_pred,
            unscaled_intercept=self.unscaled_intercept,
            unscaled_coeffs=self.unscaled_coeffs,
            scaler_mean=scaler.mean_,
            scaler_scale=safe_scale,
            term_names=self.term_names,
            l2_penalty=l2_eff,
            cov_std_override=br.sigma_,
        )
        anova_df = build_anova_table(y_arr, y_pred, df_model=diag["df_model"], X=X_arr)

        self.metrics = ModelMetrics(
            r2=r2,
            adj_r2=diag["adj_r2"],
            rmse=rmse,
            mse=mse,
            mae=mae,
            aic=diag["aic"],
            bic=diag["bic"],
            term_p_values=diag["term_p_values"],
            term_t_stats=diag["term_t_stats"],
            term_std_errors=diag["term_std_errors"],
            anova_table=anova_df,
            custom_metrics={
                "Effective Model DF": f"{diag['df_model']:.2f}",
                "Effective Penalty (λ/α)": f"{l2_eff:.5g}",
                "Noise Precision (α)": f"{float(br.alpha_):.5g}",
                "Weight Precision (λ)": f"{float(br.lambda_):.5g}",
            },
        )
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Compute predicted mean output for input coordinates X."""
        self._ensure_fitted()
        X_arr = np.asarray(X, dtype=float)
        if X_arr.ndim == 1:
            X_arr = X_arr.reshape(1, -1) if len(X_arr) == len(self.feature_names) else X_arr.reshape(-1, 1)
        return np.asarray(self.pipeline.predict(X_arr), dtype=float).ravel()

    def predict_with_uncertainty(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Compute predicted mean and posterior predictive standard deviation (±1σ)."""
        self._ensure_fitted()
        X_arr = np.asarray(X, dtype=float)
        if X_arr.ndim == 1:
            X_arr = X_arr.reshape(1, -1) if len(X_arr) == len(self.feature_names) else X_arr.reshape(-1, 1)
        y_pred, sigma = self.pipeline.predict(X_arr, return_std=True)
        return np.asarray(y_pred, dtype=float).ravel(), np.asarray(sigma, dtype=float).ravel()

    def get_coefficients(self) -> Dict[str, float]:
        """Return dictionary mapping physical term names to unscaled posterior mean coefficients."""
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
            sign = "+" if coeff > 0 else "-"
            parts.append(f"{sign} {abs(coeff):.4f}*{term}")
        return f"y = {' '.join(parts)}"

    def get_feature_importance(self) -> Dict[str, float]:
        """Return normalized relative importances based on standardized posterior mean magnitudes."""
        self._ensure_fitted()
        br = self.pipeline.named_steps["bayesianridge"]
        abs_c = np.abs(br.coef_)
        total = float(np.sum(abs_c))
        if total == 0:
            total = 1.0
        return {term: float(c / total) for term, c in zip(self.term_names, abs_c)}

