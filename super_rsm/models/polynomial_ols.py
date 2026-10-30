"""
Classical Response Surface Methodology: Polynomial Ordinary Least Squares.
Features coded units, SVD least-squares, Moore-Penrose pseudo-inversion for collinear
robustness, full ANOVA table decomposition, term t-stats, p-values, and AIC/BIC.
"""

from typing import Any, ClassVar, Dict, List, Optional
import numpy as np
import pandas as pd
import scipy.stats as stats
from sklearn.preprocessing import PolynomialFeatures

from super_rsm.common.config import HyperparameterSpec, ModelMetadata
from super_rsm.common.types import ModelCategory
from super_rsm.models.base import BaseRSMModel, ModelMetrics
from super_rsm.models.registry import register_model


def _generate_ols_term_names(column_names: List[str], poly: PolynomialFeatures) -> List[str]:
    """Generate term names including Intercept for include_bias=True."""
    terms = []
    for power in poly.powers_:
        if np.all(power == 0):
            terms.append("Intercept")
            continue
        term = []
        for col, p in zip(column_names, power):
            if p == 1:
                term.append(col)
            elif p > 1:
                term.append(f"{col}^{p}")
        terms.append(" ".join(term))
    return terms


@register_model
class PolynomialOLSModel(BaseRSMModel):
    """
    Classical RSM polynomial model fitted via Ordinary Least Squares.
    Uses Moore-Penrose pseudo-inversion to ensure robustness against collinearity.
    """

    metadata: ClassVar[ModelMetadata] = ModelMetadata(
        name="Polynomial OLS",
        display_name="Polynomial OLS (with p-values & ANOVA)",
        category=ModelCategory.POLYNOMIAL,
        description="Classical RSM OLS polynomial with coded units, pinv, ANOVA table, and p-values.",
        supports_uncertainty=False,
        supports_coefficients=True,
        supports_feature_importance=True,
        supports_formula=True,
        has_anova=True,
        hyperparameters=[
            HyperparameterSpec("degree_fit", "Polynomial Degree", int, default=2, min_val=1, max_val=4, step=1,
                               tooltip="Degree of polynomial response surface"),
            HyperparameterSpec("coded_units", "Coded Units [-1, +1]", bool, default=False,
                               tooltip="Scale inputs to [-1, +1] coded domain"),
        ],
    )

    def __init__(self, degree_fit: int = 2, coded_units: bool = False, **kwargs: Any):
        super().__init__(degree_fit=degree_fit, coded_units=coded_units, **kwargs)
        self.degree_fit = degree_fit
        self.coded_units = coded_units
        self.poly: Optional[PolynomialFeatures] = None
        self.term_names: List[str] = []
        self.beta: Optional[np.ndarray] = None
        self._x_mins: Optional[np.ndarray] = None
        self._x_maxs: Optional[np.ndarray] = None

    def _transform_inputs(self, X: np.ndarray, fit: bool = False) -> np.ndarray:
        """Apply coded units [-1, +1] transformation if enabled."""
        if not self.coded_units:
            return X
        if fit:
            self._x_mins = np.min(X, axis=0)
            self._x_maxs = np.max(X, axis=0)
        span = np.where(self._x_maxs > self._x_mins, self._x_maxs - self._x_mins, 1.0)
        center = (self._x_maxs + self._x_mins) / 2.0
        return 2.0 * (X - center) / span

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> "PolynomialOLSModel":
        """Fit polynomial OLS model, calculate ANOVA decomposition, and term p-values."""
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)
                self.hyperparameters[k] = v

        X_arr = np.asarray(X, dtype=float)
        y_arr = np.asarray(y, dtype=float).ravel()
        if X_arr.ndim == 1:
            X_arr = X_arr.reshape(-1, 1)

        n_samples = len(X_arr)
        self.feature_names = (
            list(feature_names) if feature_names is not None else [f"x{i+1}" for i in range(X_arr.shape[1])]
        )

        X_coded = self._transform_inputs(X_arr, fit=True)
        self.poly = PolynomialFeatures(degree=self.degree_fit, include_bias=True)
        Phi = self.poly.fit_transform(X_coded)
        p_terms = Phi.shape[1]

        if n_samples <= p_terms:
            raise ValueError(
                f"Sample size (N={n_samples}) must exceed number of polynomial terms (P={p_terms}). "
                "Reduce polynomial degree or collect more experimental runs."
            )

        self.beta, _, _, _ = np.linalg.lstsq(Phi, y_arr, rcond=None)
        y_pred = Phi @ self.beta
        self.term_names = _generate_ols_term_names(self.feature_names, self.poly)

        df_resid = n_samples - p_terms
        rss = float(np.sum((y_arr - y_pred) ** 2))
        s_sq = rss / df_resid if df_resid > 0 else 0.0
        tss = float(np.sum((y_arr - np.mean(y_arr)) ** 2))
        ss_reg = max(0.0, tss - rss)

        cov_matrix = np.linalg.pinv(Phi.T @ Phi)
        diag_var = np.maximum(0.0, np.diag(cov_matrix))
        se = np.sqrt(diag_var * s_sq)
        with np.errstate(divide="ignore", invalid="ignore"):
            t_stats = np.where(se > 1e-12, self.beta / se, 0.0)
        p_vals = 2.0 * (1.0 - stats.t.cdf(np.abs(t_stats), df=df_resid))

        df_model = p_terms - 1
        ms_reg = ss_reg / df_model if df_model > 0 else 0.0
        f_stat = ms_reg / s_sq if (s_sq > 0 and df_model > 0) else np.nan
        f_p_val = 1.0 - stats.f.cdf(f_stat, df_model, df_resid) if (s_sq > 0 and df_model > 0) else np.nan

        anova_df = pd.DataFrame({
            "Source": ["Model (Regression)", "Residual (Error)", "Total"],
            "SS": [ss_reg, rss, tss],
            "df": [df_model, df_resid, n_samples - 1],
            "MS": [ms_reg, s_sq, np.nan],
            "F-Value": [f_stat, np.nan, np.nan],
            "p-Value": [f_p_val, np.nan, np.nan],
        })

        r2 = 1.0 - (rss / tss) if tss > 0 else 0.0
        adj_r2 = 1.0 - (1.0 - r2) * ((n_samples - 1) / df_resid) if (df_resid > 0 and tss > 0) else r2
        mse = rss / n_samples
        rmse = float(np.sqrt(mse))
        mae = float(np.mean(np.abs(y_arr - y_pred)))
        aic = float(n_samples * np.log(max(1e-12, mse)) + 2 * p_terms)
        bic = float(n_samples * np.log(max(1e-12, mse)) + p_terms * np.log(n_samples))

        self.metrics = ModelMetrics(
            r2=float(r2),
            adj_r2=float(adj_r2),
            rmse=rmse,
            mse=float(mse),
            mae=mae,
            aic=aic,
            bic=bic,
            term_p_values={t: float(p) for t, p in zip(self.term_names, p_vals)},
            term_t_stats={t: float(t_val) for t, t_val in zip(self.term_names, t_stats)},
            term_std_errors={t: float(s_val) for t, s_val in zip(self.term_names, se)},
            anova_table=anova_df,
        )

        self.X_train = X_arr
        self.y_train = y_arr
        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Compute predicted output using the fitted polynomial model."""
        self._ensure_fitted()
        X_arr = np.asarray(X, dtype=float)
        if X_arr.ndim == 1:
            X_arr = X_arr.reshape(1, -1) if len(X_arr) == len(self.feature_names) else X_arr.reshape(-1, 1)
        X_coded = self._transform_inputs(X_arr, fit=False)
        Phi = self.poly.transform(X_coded)
        return np.asarray(Phi @ self.beta, dtype=float).ravel()

    def get_coefficients(self) -> Dict[str, float]:
        """Return dictionary mapping model term names to fitted beta coefficients."""
        self._ensure_fitted()
        return {term: float(c) for term, c in zip(self.term_names, self.beta)}

    def get_formula(self) -> str:
        """Return algebraic equation string."""
        self._ensure_fitted()
        parts = []
        for i, (term, coeff) in enumerate(zip(self.term_names, self.beta)):
            if i == 0 and term == "Intercept":
                parts.append(f"{coeff:.4f}")
            else:
                if abs(coeff) < 1e-8:
                    continue
                sign = "+" if coeff >= 0 else "-"
                parts.append(f"{sign} {abs(coeff):.4f}*{term}")
        return f"y = {' '.join(parts)}"

    def get_feature_importance(self) -> Dict[str, float]:
        """Return normalized relative importance based on term absolute t-statistics."""
        self._ensure_fitted()
        t_stats = self.metrics.term_t_stats or {}
        # Exclude Intercept from relative feature importance
        non_intercept = {k: abs(v) for k, v in t_stats.items() if k != "Intercept"}
        total = sum(non_intercept.values())
        if total == 0:
            total = 1.0
        return {k: v / total for k, v in non_intercept.items()}
