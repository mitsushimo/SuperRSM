"""
super_rsm/core/pipeline.py

Headless pipeline orchestration for Response Surface Methodology (RSM) models.
Provides unified training, metric computation, and evaluation workflows without GUI coupling.
"""

from typing import Any, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from super_rsm.common.exceptions import DataValidationError, ModelFitError, RegistryError
from super_rsm.models.base import BaseRSMModel, ModelMetrics
from super_rsm.models.registry import ModelRegistry
from super_rsm.core.dataset import RSMDataset
from super_rsm.core.result import RSMResult


def fit_rsm(
    dataset: RSMDataset,
    method: str = "Polynomial OLS",
    **hyperparameters: Any,
) -> RSMResult:
    """Fit a Response Surface Model using a pre-configured RSMDataset container."""
    if not isinstance(dataset, RSMDataset):
        raise DataValidationError(f"Expected dataset to be an RSMDataset instance, got {type(dataset).__name__}")
    if len(dataset.X_train) == 0:
        raise DataValidationError("dataset.X_train cannot be empty.")

    try:
        model: BaseRSMModel = ModelRegistry.create(method, **hyperparameters)
    except RegistryError:
        raise
    except Exception as exc:
        raise ModelFitError(f"Failed to instantiate model '{method}': {exc}") from exc

    try:
        model.fit(dataset.X_train, dataset.y_train, feature_names=dataset.feature_names)
    except Exception as exc:
        raise ModelFitError(f"Failed to fit model '{method}': {exc}") from exc

    if len(dataset.X_test) > 0 and len(dataset.y_test) > 0:
        try:
            y_pred = model.predict(dataset.X_test)
            y_test = dataset.y_test
            n_test = len(y_test)
            rss = float(np.sum((y_test - y_pred) ** 2))
            tss = float(np.sum((y_test - np.mean(y_test)) ** 2))
            r2 = 1.0 - (rss / tss) if tss > 1e-12 else 0.0
            mse = rss / n_test if n_test > 0 else 0.0
            rmse = float(np.sqrt(mse))
            mae = float(np.mean(np.abs(y_test - y_pred))) if n_test > 0 else 0.0

            train_metrics = getattr(model, "metrics", None)
            metrics = ModelMetrics(
                r2=r2,
                rmse=rmse,
                mse=mse,
                mae=mae,
                adj_r2=train_metrics.adj_r2 if train_metrics else None,
                aic=train_metrics.aic if train_metrics else None,
                bic=train_metrics.bic if train_metrics else None,
                term_p_values=train_metrics.term_p_values if train_metrics else None,
                term_t_stats=train_metrics.term_t_stats if train_metrics else None,
                term_std_errors=train_metrics.term_std_errors if train_metrics else None,
                anova_table=train_metrics.anova_table if train_metrics else None,
            )
        except Exception as exc:
            raise ModelFitError(f"Failed to evaluate test metrics for model '{method}': {exc}") from exc
    else:
        metrics = model.get_metrics()

    return RSMResult(model=model, dataset=dataset, metrics=metrics, method=method)


def fit_rsm2(
    X_train: Any,
    y_train: Any,
    X_test: Optional[Any] = None,
    y_test: Optional[Any] = None,
    method: str = "Polynomial OLS",
    feature_names: Optional[List[str]] = None,
    test_size: float = 0.2,
    random_state: Optional[int] = 42,
    **kwargs: Any,
) -> RSMResult:
    """Fit a Response Surface Model from array-like inputs (pre-split or unsplit)."""
    if X_test is not None and y_test is not None:
        dataset = RSMDataset.from_arrays(
            X_train=X_train,
            y_train=y_train,
            X_test=X_test,
            y_test=y_test,
            feature_names=feature_names,
        )
    else:
        dataset = RSMDataset.from_unsplit_arrays(
            X=X_train,
            y=y_train,
            test_size=test_size,
            random_state=random_state,
            feature_names=feature_names,
        )
    return fit_rsm(dataset=dataset, method=method, **kwargs)


def rsm_fromDF(
    df: pd.DataFrame,
    input_columns: List[str],
    output_column: str,
    method: str = "Polynomial OLS",
    test_size: float = 0.2,
    random_state: Optional[int] = 42,
    **kwargs: Any,
) -> RSMResult:
    """Fit a Response Surface Model directly from a pandas DataFrame."""
    dataset = RSMDataset.from_dataframe(
        df=df,
        input_columns=input_columns,
        output_column=output_column,
        test_size=test_size,
        random_state=random_state,
    )
    return fit_rsm(dataset=dataset, method=method, **kwargs)


def build_data(
    df: pd.DataFrame,
    input_columns: List[str],
    output_column: str,
) -> Tuple[np.ndarray, np.ndarray]:
    """Extract numpy feature matrix X and target vector y from a pandas DataFrame."""
    if not isinstance(df, pd.DataFrame):
        raise DataValidationError(f"Expected pandas DataFrame, got {type(df).__name__}")
    missing_inputs = [c for c in input_columns if c not in df.columns]
    if missing_inputs:
        raise DataValidationError(f"Missing input columns in DataFrame: {missing_inputs}")
    if output_column not in df.columns:
        raise DataValidationError(f"Missing output column in DataFrame: '{output_column}'")
    X = df[input_columns].to_numpy(dtype=float)
    y = df[output_column].to_numpy(dtype=float).ravel()
    return X, y
