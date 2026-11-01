"""
ElasticNetCV Regressor with Polynomial Features, automatic L1 term pruning,
analytical unscaling, active-set t-statistics, and effective-DF ANOVA.
"""

from typing import Any, ClassVar, Dict, List, Optional
import warnings
import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import ElasticNet, ElasticNetCV
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
class ElasticNetCVRSMModel(BaseRSMModel):
    """
    Sparse polynomial regression combining L1 (Lasso) and L2 (Ridge) regularization
    with cross-validation. Automatically zeroes out insignificant polynomial terms.
    """

    metadata: ClassVar[ModelMetadata] = ModelMetadata(
        name="ElasticNetCV",
        display_name="ElasticNetCV (Sparse L1+L2 Polynomial)",
        category=ModelCategory.POLYNOMIAL,
        description="Sparse L1+L2 polynomial regression with automatic term pruning, active-set t-scores, and ANOVA.",
        supports_uncertainty=False,
        supports_coefficients=True,
        supports_feature_importance=True,
        supports_formula=True,
        has_anova=True,
        hyperparameters=[
            HyperparameterSpec("degree_fit", "Polynomial Degree", int, default=2, min_val=1, max_val=4, step=1,
                               tooltip="Degree of polynomial feature expansions"),
            HyperparameterSpec("l1_ratio", "L1 Ratio (1.0=Lasso)", float, default=0.5, min_val=0.05, max_val=1.0, step=0.05,
                               tooltip="Mix between L1 sparsity (1.0) and L2 ridge stability (0.0)"),
            HyperparameterSpec("cv", "CV Folds", int, default=5, min_val=2, max_val=10, step=1,
                               tooltip="Number of cross-validation folds"),
            HyperparameterSpec("max_iter", "Max Iterations", int, default=2000, min_val=200, max_val=10000, step=200,
                               tooltip="Maximum coordinate descent iterations"),
        ],
    )

    def __init__(
        self,
        degree_fit: int = 2,
        l1_ratio: float = 0.5,
        cv: Optional[int] = 5,
        max_iter: int = 2000,
        random_state: int = 42,
        **kwargs: Any,
    ):
        super().__init__(
            degree_fit=degree_fit,
            l1_ratio=l1_ratio,
            cv=cv,
            max_iter=max_iter,
            random_state=random_state,
            **kwargs,
        )
        self.degree_fit = degree_fit
        self.l1_ratio = l1_ratio
        self.cv = cv
        self.max_iter = max_iter
        self.random_state = random_state
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
    ) -> "ElasticNetCVRSMModel":
        """Fit ElasticNetCV polynomial pipeline, unscale coefficients, and compute active-set ANOVA/t-stats."""
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
        l1_val = float(np.clip(self.l1_ratio, 0.01, 1.0))
        if n_samples < 4:
            reg = ElasticNet(alpha=0.01, l1_ratio=l1_val, max_iter=int(self.max_iter), random_state=self.random_state)
        else:
            cv_folds = min(int(self.cv or 5), n_samples)
            reg = ElasticNetCV(
                l1_ratio=l1_val,
                cv=max(2, cv_folds),
                max_iter=int(self.max_iter),
                random_state=self.random_state,
            )

        self.pipeline = make_pipeline(
            PolynomialFeatures(degree=self.degree_fit, include_bias=False),
            StandardScaler(),
            reg,
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ConvergenceWarning)
            self.pipeline.fit(X_arr, y_arr)

        self.X_train = X_arr
        self.y_train = y_arr
        self.is_fitted = True

        poly = self.pipeline.named_steps["polynomialfeatures"]
        scaler = self.pipeline.named_steps["standardscaler"]
        enet = self.pipeline.steps[-1][1]

        self.term_names = _generate_polynomial_term_names(self.feature_names, poly)
        safe_scale = np.where(scaler.scale_ > 1e-12, scaler.scale_, 1.0)
        self.unscaled_coeffs = enet.coef_ / safe_scale
        self.unscaled_intercept = float(enet.intercept_ - np.dot(self.unscaled_coeffs, scaler.mean_))

        y_pred = self.pipeline.predict(X_arr)
        mse = float(mean_squared_error(y_arr, y_pred))
        rmse = float(np.sqrt(mse))
        mae = float(np.mean(np.abs(y_arr - y_pred)))
        r2 = float(r2_score(y_arr, y_pred))

        alpha_opt = float(getattr(enet, "alpha_", getattr(enet, "alpha", 0.01)))
        active_mask = np.abs(enet.coef_) > 1e-10
        l2_eff = float(n_samples * alpha_opt * (1.0 - l1_val))
        Z_std = scaler.transform(poly.transform(X_arr))

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
            active_mask=active_mask,
        )
        anova_df = build_anova_table(y_arr, y_pred, df_model=diag["df_model"], X=X_arr)
        n_active = int(np.sum(active_mask))
        n_total = len(self.term_names)

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
                "Selected Alpha (α*)": f"{alpha_opt:.5g}",
                "L1 Ratio": f"{l1_val:.2f}",
                "Active / Total Terms": f"{n_active} / {n_total} ({n_total - n_active} pruned)",
                "Effective Model DF": f"{diag['df_model']:.2f}",
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

    def get_coefficients(self) -> Dict[str, float]:
        """Return dictionary mapping physical term names to unscaled coefficients."""
        self._ensure_fitted()
        coeffs: Dict[str, float] = {"Intercept": float(self.unscaled_intercept)}
        for term, coeff in zip(self.term_names, self.unscaled_coeffs):
            coeffs[term] = float(coeff)
        return coeffs

    def get_formula(self) -> str:
        """Return human-readable sparse algebraic equation (omitting L1-pruned zero terms)."""
        self._ensure_fitted()
        parts = [f"{self.unscaled_intercept:.4f}"]
        for term, coeff in zip(self.term_names, self.unscaled_coeffs):
            if abs(coeff) < 1e-8:
                continue
            sign = "+" if coeff > 0 else "-"
            parts.append(f"{sign} {abs(coeff):.4f}*{term}")
        return f"y = {' '.join(parts)}"

    def get_feature_importance(self) -> Dict[str, float]:
        """Return normalized relative importances based on standardized coefficients."""
        self._ensure_fitted()
        enet = self.pipeline.steps[-1][1]
        abs_c = np.abs(enet.coef_)
        total = float(np.sum(abs_c))
        if total == 0:
            total = 1.0
        return {term: float(c / total) for term, c in zip(self.term_names, abs_c)}

