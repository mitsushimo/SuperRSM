"""
super_rsm/core/result.py

RSMResult container: encapsulates fitted surrogate model, evaluation metrics,
point/batch prediction, optimization delegator, and lazy visualization shims.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple, Union, TYPE_CHECKING
import numpy as np

from super_rsm.common.exceptions import UncertaintyNotSupportedError
from super_rsm.core.dataset import RSMDataset
from super_rsm.models.base import BaseRSMModel, ModelMetrics

if TYPE_CHECKING:
    from super_rsm.core.optimization import OptimizationResult


class RSMResult:
    """Canonical result container holding trained surrogate model, dataset, and metrics."""

    def __init__(
        self,
        model: Any,
        dataset_or_X_train: Any = None,
        y_train: Optional[np.ndarray] = None,
        X_test: Optional[np.ndarray] = None,
        y_test: Optional[np.ndarray] = None,
        method: str = "Gaussian Process",
        metrics: Optional[ModelMetrics] = None,
        dataset: Optional[RSMDataset] = None,
    ):
        self.model = model
        self.method = method
        self.last_opt_result: Optional["OptimizationResult"] = None
        self.last_opt_maximize: bool = False

        target_ds = dataset if dataset is not None else dataset_or_X_train
        if isinstance(target_ds, RSMDataset):
            self.dataset: RSMDataset = target_ds
        else:
            self.dataset = RSMDataset.from_arrays(
                X_train=target_ds,
                y_train=y_train if y_train is not None else np.empty((0,)),
                X_test=X_test,
                y_test=y_test,
            )

        if hasattr(model, "get_metadata"):
            self.supports_uncertainty: bool = model.get_metadata().supports_uncertainty
        elif hasattr(model, "supports_uncertainty"):
            self.supports_uncertainty = bool(model.supports_uncertainty)
        else:
            self.supports_uncertainty = False

        self.sigma_test: Optional[np.ndarray] = None
        if metrics is not None:
            self.metrics: ModelMetrics = metrics
        elif hasattr(model, "metrics") and model.metrics is not None:
            self.metrics = model.metrics
        else:
            self.metrics = self._compute_test_metrics()

        self.coeffs: Optional[np.ndarray] = None
        self.intercept: Optional[float] = None
        self.expression_text: Optional[str] = None
        self._extract_model_diagnostics()

    def _compute_test_metrics(self) -> ModelMetrics:
        eval_X = self.dataset.X_test if self.dataset.has_test_set else self.dataset.X_train
        eval_y = self.dataset.y_test if self.dataset.has_test_set else self.dataset.y_train
        if len(eval_X) == 0:
            return ModelMetrics(r2=0.0, rmse=0.0, mse=0.0, mae=0.0)

        if self.supports_uncertainty:
            try:
                y_pred, sigma = self.model.predict(eval_X, return_std=True)
                if self.dataset.has_test_set:
                    self.sigma_test = sigma
            except TypeError:
                y_pred = self.model.predict(eval_X)
        else:
            y_pred = self.model.predict(eval_X)

        y_pred = np.asarray(y_pred, dtype=float).ravel()
        rss = float(np.sum((eval_y - y_pred) ** 2))
        tss = float(np.sum((eval_y - np.mean(eval_y)) ** 2))
        r2 = float(1.0 - (rss / tss)) if tss > 0 else 0.0
        mse = float(np.mean((eval_y - y_pred) ** 2))
        return ModelMetrics(r2=r2, rmse=float(np.sqrt(mse)), mse=mse, mae=float(np.mean(np.abs(eval_y - y_pred))))

    def _extract_model_diagnostics(self) -> None:
        if hasattr(self.model, "get_formula"):
            self.expression_text = self.model.get_formula()
        if hasattr(self.model, "get_coefficients"):
            c_dict = self.model.get_coefficients()
            if c_dict is not None:
                self.intercept = c_dict.get("Intercept", None)
                self.coeffs = np.array([v for k, v in c_dict.items() if k != "Intercept"], dtype=float)

        if self.coeffs is None and hasattr(self.model, "named_steps"):
            try:
                scaler = self.model.named_steps.get("standardscaler")
                ridge = self.model.named_steps.get("ridgecv")
                if scaler is not None and ridge is not None:
                    self.coeffs = ridge.coef_ / scaler.scale_
                    self.intercept = float(ridge.intercept_ - np.dot(self.coeffs, scaler.mean_))
            except Exception:
                pass

    @property
    def r2(self) -> float: return self.metrics.r2
    @property
    def R_sq(self) -> float: return self.metrics.r2
    @property
    def R2(self) -> float: return self.metrics.r2
    @property
    def rmse(self) -> float: return self.metrics.rmse
    @property
    def RMSE(self) -> float: return self.metrics.rmse
    @property
    def mse(self) -> float: return self.metrics.mse
    @property
    def MSE(self) -> float: return self.metrics.mse
    @property
    def mae(self) -> Optional[float]: return self.metrics.mae
    @property
    def MAE(self) -> Optional[float]: return self.metrics.mae
    @property
    def X_train(self) -> np.ndarray: return self.dataset.X_train
    @property
    def y_train(self) -> np.ndarray: return self.dataset.y_train
    @property
    def X_test(self) -> np.ndarray: return self.dataset.X_test
    @property
    def y_test(self) -> np.ndarray: return self.dataset.y_test
    @property
    def feature_names(self) -> List[str]: return self.dataset.feature_names
    @property
    def target_name(self) -> str: return self.dataset.target_name

    def evaluate_point(
        self,
        point: Union[np.ndarray, Sequence[float]],
        return_std: bool = False,
    ) -> Union[float, Tuple[float, Optional[float]]]:
        X_eval = np.asarray(point, dtype=float).reshape(1, -1)
        if return_std:
            if not self.supports_uncertainty:
                y_pred = self.model.predict(X_eval)
                return float(np.asarray(y_pred, dtype=float).ravel()[0]), None
            if hasattr(self.model, "predict_with_uncertainty"):
                y_pred, sigma = self.model.predict_with_uncertainty(X_eval)
            elif hasattr(self.model, "evaluate_point"):
                res = self.model.evaluate_point(point, return_std=True)
                return float(res[0]), float(res[1]) if res[1] is not None else None
            else:
                y_pred, sigma = self.model.predict(X_eval, return_std=True)
            return float(np.asarray(y_pred, dtype=float).ravel()[0]), float(np.asarray(sigma, dtype=float).ravel()[0])

        if hasattr(self.model, "evaluate_point"):
            res = self.model.evaluate_point(point, return_std=False)
            val = res[0] if isinstance(res, (tuple, list)) else res
            return float(val)
        y_pred = self.model.predict(X_eval)
        return float(np.asarray(y_pred, dtype=float).ravel()[0])

    def evaluate_batch(
        self,
        X_batch: Union[np.ndarray, Sequence[Sequence[float]]],
        return_std: bool = False,
    ) -> Union[np.ndarray, Tuple[np.ndarray, np.ndarray]]:
        X_arr = np.asarray(X_batch, dtype=float)
        if return_std:
            if not self.supports_uncertainty:
                raise UncertaintyNotSupportedError(f"Model '{self.method}' does not support predictive uncertainty.")
            if hasattr(self.model, "predict_with_uncertainty"):
                return self.model.predict_with_uncertainty(X_arr)
            return self.model.predict(X_arr, return_std=True)
        return self.model.predict(X_arr)

    def target_func(self, params: Any, return_std: bool = False) -> Any:
        return self.evaluate_point(params, return_std=return_std)

    def optimize(
        self,
        initial_guess: Optional[Any] = None,
        bounds: Optional[Any] = None,
        constraints: Optional[Any] = None,
        maximize: bool = False,
        **kwargs: Any,
    ) -> "OptimizationResult":
        from super_rsm.core.optimization import OptimizationEngine
        res = OptimizationEngine.optimize(
            model=self.model, dataset=self.dataset, initial_guess=initial_guess,
            bounds=bounds, constraints=constraints, maximize=maximize, **kwargs,
        )
        self.last_opt_result = res
        self.last_opt_maximize = bool(maximize)
        return res

    def get_formula(self) -> Optional[str]: return self.expression_text
    def get_coefficients(self) -> Optional[Dict[str, float]]:
        return self.model.get_coefficients() if hasattr(self.model, "get_coefficients") else None
    def get_feature_importance(self) -> Optional[Dict[str, float]]:
        return self.model.get_feature_importance() if hasattr(self.model, "get_feature_importance") else None

    def summary(self) -> str:
        lines = [
            f"SuperRSM Model Summary: {self.method}", f"{'=' * 50}",
            f"Target Variable: {self.target_name}",
            f"Input Factors ({len(self.feature_names)}): {', '.join(self.feature_names)}",
            f"Training Samples: {self.dataset.n_train} | Testing Samples: {self.dataset.n_test}",
            f"{'-' * 50}", "Goodness-of-Fit Metrics (Test Set):",
            f"  R²:       {self.metrics.r2:.5f}", f"  RMSE:     {self.metrics.rmse:.5f}", f"  MSE:      {self.metrics.mse:.5f}",
        ]
        if self.metrics.mae is not None: lines.append(f"  MAE:      {self.metrics.mae:.5f}")
        if self.metrics.adj_r2 is not None: lines.append(f"  Adj. R²:  {self.metrics.adj_r2:.5f}")
        if self.metrics.aic is not None: lines.append(f"  AIC:      {self.metrics.aic:.2f} | BIC: {self.metrics.bic:.2f}")
        if self.expression_text: lines.extend([f"{'-' * 50}", f"Model Expression: {self.expression_text}"])
        if self.metrics.anova_table is not None: lines.extend([f"{'-' * 50}", "ANOVA Table:", str(self.metrics.anova_table)])
        return "\n".join(lines)

    def __str__(self) -> str:
        parts = [f"Regression Method: {self.method}"]
        if self.expression_text: parts.append(self.expression_text)
        if self.intercept is not None and self.coeffs is not None:
            parts.append(f"Intercept: {self.intercept}, Coefficients: {self.coeffs}")
        parts.append(f"Coefficient of Determination (R2): {self.R_sq}")
        parts.append(f"Mean Squared Error (MSE): {self.MSE}")
        parts.append(f"Root Mean Squared Error (RMSE): {self.RMSE}")
        return "\n".join(parts)

    def __repr__(self) -> str:
        return f"RSMResult(method='{self.method}', R2={self.metrics.r2:.4f}, RMSE={self.metrics.rmse:.4f})"

    def visualize_rsm(self, config: Any, **kwargs: Any) -> Any:
        try:
            from super_rsm.visualization.service import VisualizationService
        except ImportError as exc:
            raise ImportError("Visualization subsystem not available or graphical libraries missing.") from exc
        return VisualizationService.visualize_result(result=self, config=config, **kwargs)


rsm_result = RSMResult
