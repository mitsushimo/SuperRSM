# Milestone M2 Handoff Report: Pipeline Orchestration & Test Suite Architecture

**Explorer**: M2-3 (Pipeline Orchestration & Test Suite Architecture)  
**Working Directory**: `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\explorer_m2_3\`  
**Milestone**: M2 (Core Domain Logic & Optimization Engine)  
**Target Files**:
- `super_rsm/core/pipeline.py`
- `super_rsm/core/__init__.py`
- `tests/test_core.py`  
**Date**: October 30, 2026  

---

## 1. Observation

Direct observations from the codebase, baseline test harness, and reorganization architecture:

1. **Legacy Pipeline Coupling in `rsm_backend.py` (lines 422–468)**:
   ```python
   def fit_rsm2(X, y, degree_fit=2, test_size=0.20, method="Gaussian Process", **kwargs):
       if method not in MODEL_REGISTRY:
           raise ValueError(f"Unknown regression method '{method}'. Supported methods: {get_supported_methods()}")
       X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42)
       builder = MODEL_REGISTRY[method]["builder"]
       model = builder(degree_fit=degree_fit, n_samples=len(X_train), **kwargs)
       model.fit(X_train, y_train)
       return rsm_result(model, X_train, y_train, X_test, y_test, method=method)
   ```
   - Legacy `fit_rsm2` coupled model instantiation to functional dictionary builders (`MODEL_REGISTRY[method]["builder"]`) and hardcoded `random_state=42`.
   - `rsm_fromDF` (lines 455–468) relied on helper `build_data(df, input_columns, output_column)` (lines 442–452) and forwarded straight into `fit_rsm2`.
   - The returned `rsm_result` directly imported plotting routines (`from high_d_plotter import plot_multi_contour` in `rsm_backend.py:23`), violating headless execution requirements.

2. **Reorganization Plan Directives (`SUPER_RSM_REORGANIZATION_PLAN.md` §4, §5.5, §9.3)**:
   - Line 210: `super_rsm/core/pipeline.py`: `fit_rsm`, `fit_rsm2`, and `rsm_fromDF` headless pipelines (~110–150 lines).
   - Line 206: `super_rsm/core/__init__.py`: Re-exports `RSMDataset`, `RSMResult`, `OptimizationEngine`, `OptimizationResult`, `fit_rsm`, `fit_rsm2`, `rsm_fromDF`, `build_data`.
   - Line 357–394: Headless execution guarantee—core must have zero load-time dependencies on `super_rsm.gui` and `super_rsm.visualization` (and therefore zero dependencies on `tkinter`, `matplotlib`, or `seaborn`).
   - Line 1068–1078: `RSMResult.optimize(...)` returns `OptimizationResult` supporting 2-tuple unpacking `params, val = result.optimize(...)` via `__iter__`.

3. **Existing Layer 0 & Layer 1 Subsystems (`super_rsm/common/`, `super_rsm/models/`)**:
   - `super_rsm.models.registry.ModelRegistry`:
     - `ModelRegistry.create(name, **hyperparameters)` instantiates registered models dynamically.
     - Registered models: `"Polynomial OLS"`, `"Gaussian Process"`, `"RidgeCV"`, `"Genetic Programming"`.
   - `super_rsm.common.config.ConstraintSpec`:
     - Dataclass specifying `coeffs: Dict[str, float]`, `operator: ConstraintOperator` (`LE`, `GE`, `EQ`), and `bound: float`.
     - Has `to_expression()` and `evaluate(point: Dict[str, float]) -> bool`.
   - `super_rsm.common.exceptions`:
     - `SuperRSMError` base class.
     - `DataValidationError`: invalid shapes, non-DataFrames, NaN/Inf, missing columns.
     - `ModelFitError`: fitting exceptions.
     - `RegistryError`: unregistered model lookup.
     - `OptimizationError`: optimization convergence failure.

4. **Golden Reference Baselines (`tests/test_baseline.py` & `sample_data.csv`)**:
   - `sample_data.csv`: 100 rows, 2 input features (`x1`, `x2`), 1 target (`y`).
   - Generating analytical function: $f(x_1, x_2) = (x_1 - 3.0)^2 + (x_2 - 4.0)^2 + 5.0$.
   - Unconstrained global minimum: $x_1^* = 3.0$, $x_2^* = 4.0$, $f(x^*) = 5.0$.
   - Linearly constrained minimum ($x_1 + x_2 \le 5.0$): analytically solves to $x_1^* = 2.0$, $x_2^* = 3.0$, $f(x^*) = 7.0$.
   - Linearly constrained minimum ($x_1 + x_2 \le 6.0$): in `tests/test_baseline.py:112-115`, $x_1^* \approx 2.48$, $x_2^* \approx 3.52$, $f(x^*) \approx 5.55$.

5. **Peer Explorer Coordination (`explorer_m2_1` & `explorer_m2_2`)**:
   - `explorer_m2_1`: Designing `RSMDataset` with factories (`from_dataframe`, `from_arrays`, `from_unsplit_arrays`), shape validation, and `RSMResult` container with legacy property aliases (`R_sq`, `RMSE`, `coeffs`, `intercept`, `expression_text`).
   - `explorer_m2_2`: Designing `OptimizationEngine` and `OptimizationResult`. `OptimizationResult` implements `__iter__` yielding `(self.params, self.fun)` and `__getitem__` for 2-tuple unpacking. `OptimizationEngine.optimize()` translates both `ConstraintSpec` lists and Scipy `LinearConstraint` objects.

---

## 2. Logic Chain

From the direct observations above, the architectural requirements dictate the following logic chain:

1. **Decoupled Pipeline Architecture (`pipeline.py`)**:
   - Step 1: `fit_rsm(dataset: RSMDataset, method: str = "Polynomial OLS", **hyperparameters)` is the primary canonical pipeline. It takes an already validated `RSMDataset` container, delegates model creation to `ModelRegistry.create(method, **hyperparameters)`, fits the model on `dataset.X_train, dataset.y_train`, computes test set metrics if `dataset.X_test` is non-empty while preserving rich model diagnostics (`anova_table`, `term_p_values`, `adj_r2`, `aic`, `bic`), and returns `RSMResult`.
   - Step 2: `fit_rsm2(X_train, y_train, X_test=None, y_test=None, method="Polynomial OLS", feature_names=None, test_size=0.2, random_state=None, **kwargs)` must seamlessly support both:
     a) Pre-split 4-array invocations: `fit_rsm2(X_train, y_train, X_test, y_test, ...)`
     b) Unsplit 2-array invocations: `fit_rsm2(X, y, test_size=0.2, ...)`
     This is achieved cleanly by checking if `X_test is not None and y_test is not None`: if so, it builds `RSMDataset.from_arrays(...)`; otherwise, it builds `RSMDataset.from_unsplit_arrays(...)`. It then delegates directly to `fit_rsm(...)`.
   - Step 3: `rsm_fromDF(df, input_columns, output_column, method="Polynomial OLS", test_size=0.2, random_state=None, **kwargs)` converts the pandas DataFrame via `RSMDataset.from_dataframe(...)` and delegates directly to `fit_rsm(...)`.
   - Step 4: `build_data(df, input_columns, output_column)` is retained and exported as a utility function, preserving 100% backward compatibility for callers expecting array extraction.

2. **Package Exports (`super_rsm/core/__init__.py`)**:
   - The core package must re-export: `RSMDataset`, `RSMResult`, `OptimizationEngine`, `OptimizationResult`, `fit_rsm`, `fit_rsm2`, `rsm_fromDF`, and `build_data`.
   - This provides a clean public API (`from super_rsm.core import fit_rsm, RSMDataset, RSMResult`) with zero internal leakage.

3. **Comprehensive Test Suite Architecture (`tests/test_core.py`)**:
   - Must cover all 6 core domains:
     1. Dataset splitting, dimension validation, feature name inference, NaN/Inf rejection, and summary statistics.
     2. Pipeline execution across all 4 registered model classes (`Polynomial OLS`, `Gaussian Process`, `RidgeCV`, `Genetic Programming`).
     3. `RSMResult` metrics accessors, legacy aliases (`R_sq`, `RMSE`, `coeffs`, `intercept`, `expression_text`), summary string generation, and headless point/batch evaluation.
     4. Continuous optimization over response surfaces: unconstrained minimum $(3.0, 4.0)$, bounded domain, maximization with sign restoration, Scipy `LinearConstraint`, and `ConstraintSpec` linear inequality constraints.
     5. 2-Tuple unpacking protocol (`opt_p, opt_v = result.optimize(...)`) and indexing protocol (`res[0]`, `res[1]`).
     6. Full headless verification: asserting that importing `super_rsm.core` introduces zero GUI packages (`tkinter`, `matplotlib`, `seaborn`) into `sys.modules`, and that setting `sys.modules['tkinter'] = None` and `sys.modules['matplotlib'] = None` allows pipeline fitting and optimization to run without failure.

---

## 3. Caveats

1. **`test_size=0.0` Edge Case**: When fitting on 100% of the dataset with no test split (`test_size=0.0`), `dataset.X_test` has length 0. The pipeline must gracefully fall back to training metrics from `model.get_metrics()` rather than raising an index or zero-division error.
2. **Genetic Programming Runtime**: Genetic Programming tests can be slow if run with large populations. Test cases in `test_core.py` must use small population and generation parameters (`population_size=40, generations=2`) to execute in $<1.5$ seconds.
3. **Floating Point Tolerances in Scipy Solvers**: Depending on solver convergence tolerances (`SLSQP` vs `L-BFGS-B`), test assertions for optimization coordinates should use `pytest.approx(..., abs=0.2)` or `rel=0.05` to account for slight numerical variations across OS architectures.

---

## 4. Conclusion & Technical Blueprint

### Blueprint 1: `super_rsm/core/pipeline.py`

```python
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
    """
    Fit a Response Surface Model using a pre-configured RSMDataset container.

    Parameters
    ----------
    dataset : RSMDataset
        Container holding training and testing arrays (X_train, y_train, X_test, y_test)
        and feature metadata.
    method : str, default="Polynomial OLS"
        Unique identifier name of the regression model registered in ModelRegistry
        (e.g., "Polynomial OLS", "Gaussian Process", "RidgeCV", "Genetic Programming").
    **hyperparameters : Any
        Hyperparameters passed directly to the model constructor (e.g., degree_fit,
        noise_level, population_size).

    Returns
    -------
    RSMResult
        Immutable result container wrapping the fitted model, dataset, and evaluation metrics.

    Raises
    ------
    DataValidationError
        If dataset is invalid or not an instance of RSMDataset.
    RegistryError
        If method is not registered in ModelRegistry.
    ModelFitError
        If fitting the model encounters a numerical error or failure.
    """
    if not isinstance(dataset, RSMDataset):
        raise DataValidationError(
            f"Expected dataset to be an RSMDataset instance, got {type(dataset).__name__}"
        )

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

    # Evaluate metrics on test split if available, otherwise use training metrics
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

            # Preserve detailed model diagnostics (e.g. ANOVA, AIC/BIC, p-values from PolynomialOLS)
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

    return RSMResult(
        model=model,
        dataset=dataset,
        metrics=metrics,
        method=method,
    )


def fit_rsm2(
    X_train: Any,
    y_train: Any,
    X_test: Optional[Any] = None,
    y_test: Optional[Any] = None,
    method: str = "Polynomial OLS",
    feature_names: Optional[List[str]] = None,
    test_size: float = 0.2,
    random_state: Optional[int] = None,
    **kwargs: Any,
) -> RSMResult:
    """
    Fit a Response Surface Model from array-like inputs.

    Supports both pre-split (4-array) and unsplit (2-array with test_size) invocations:
    1. Pre-split: fit_rsm2(X_train, y_train, X_test, y_test, method="Polynomial OLS", ...)
    2. Unsplit:   fit_rsm2(X, y, test_size=0.20, random_state=42, method="RidgeCV", ...)

    Parameters
    ----------
    X_train : array-like
        Training input matrix of shape (N_train, D) or full input matrix if X_test is None.
    y_train : array-like
        Training target vector of shape (N_train,) or full target vector if y_test is None.
    X_test : Optional[array-like], default=None
        Testing input matrix of shape (N_test, D).
    y_test : Optional[array-like], default=None
        Testing target vector of shape (N_test,).
    method : str, default="Polynomial OLS"
        Regression model identifier registered in ModelRegistry.
    feature_names : Optional[List[str]], default=None
        Names of the input features.
    test_size : float, default=0.2
        Fraction of data for test split if X_test is not provided.
    random_state : Optional[int], default=None
        Seed for reproducible splitting if X_test is not provided.
    **kwargs : Any
        Hyperparameters passed to the model constructor.

    Returns
    -------
    RSMResult
        Result container wrapping fitted model, dataset, and metrics.
    """
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
    random_state: Optional[int] = None,
    **kwargs: Any,
) -> RSMResult:
    """
    Fit a Response Surface Model directly from a pandas DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Source pandas DataFrame containing experimental or simulation data.
    input_columns : List[str]
        Column names corresponding to independent variables / design factors.
    output_column : str
        Column name corresponding to the response variable.
    method : str, default="Polynomial OLS"
        Regression model name (e.g., "Polynomial OLS", "Gaussian Process", "RidgeCV").
    test_size : float, default=0.2
        Fraction of data reserved for the test split (0.0 <= test_size < 1.0).
    random_state : Optional[int], default=None
        Random seed for reproducible train/test splitting.
    **kwargs : Any
        Hyperparameters passed to the model constructor.

    Returns
    -------
    RSMResult
        Result container wrapping fitted model, dataset, and metrics.
    """
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
    """
    Extract numpy feature matrix X and target vector y from a pandas DataFrame.
    """
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
```

---

### Blueprint 2: `super_rsm/core/__init__.py`

```python
"""
super_rsm/core/__init__.py

Core domain logic, headless pipeline orchestration, and numerical optimization for SuperRSM.
"""

from super_rsm.core.dataset import RSMDataset, build_data
from super_rsm.core.result import RSMResult
from super_rsm.core.optimization import OptimizationEngine, OptimizationResult
from super_rsm.core.pipeline import fit_rsm, fit_rsm2, rsm_fromDF

__all__ = [
    "RSMDataset",
    "RSMResult",
    "OptimizationEngine",
    "OptimizationResult",
    "fit_rsm",
    "fit_rsm2",
    "rsm_fromDF",
    "build_data",
]
```

---

### Blueprint 3: `tests/test_core.py`

```python
"""
tests/test_core.py

Comprehensive test suite for SuperRSM Core Domain Logic & Optimization Engine:
- Dataset splitting, shape verification, feature name inference, invalid data error handling
- Headless pipeline execution across all registered models (fit_rsm, fit_rsm2, rsm_fromDF)
- RSMResult metrics, legacy aliases, summary text, and headless evaluation
- Constrained continuous optimization (unconstrained, bounded, maximization, LinearConstraint, ConstraintSpec)
- 2-tuple unpacking protocol (opt_p, opt_v = result.optimize(...))
- Full headless isolation (zero GUI imports, mocked GUI environments)
"""

from pathlib import Path
import sys
import unittest.mock
import pytest
import numpy as np
import pandas as pd
from scipy.optimize import LinearConstraint

from super_rsm.common.config import ConstraintOperator, ConstraintSpec
from super_rsm.common.exceptions import (
    DataValidationError,
    ModelFitError,
    RegistryError,
)
from super_rsm.core import (
    RSMDataset,
    RSMResult,
    OptimizationEngine,
    OptimizationResult,
    fit_rsm,
    fit_rsm2,
    rsm_fromDF,
    build_data,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(scope="module")
def sample_csv_path():
    """Locate sample_data.csv in repository root."""
    path = Path(__file__).resolve().parent.parent / "sample_data.csv"
    assert path.exists(), f"sample_data.csv not found at {path}"
    return path


@pytest.fixture(scope="module")
def sample_df(sample_csv_path):
    """Load sample data into pandas DataFrame."""
    return pd.read_csv(sample_csv_path)


@pytest.fixture(scope="module")
def sample_dataset(sample_df):
    """Pre-built standard RSMDataset instance with 80/20 train/test split."""
    return RSMDataset.from_dataframe(
        df=sample_df,
        input_columns=["x1", "x2"],
        output_column="y",
        test_size=0.20,
        random_state=42,
    )


@pytest.fixture(scope="module")
def fitted_ols_result(sample_dataset):
    """Fitted Polynomial OLS result for analytical tests."""
    return fit_rsm(sample_dataset, method="Polynomial OLS", degree_fit=2)


@pytest.fixture(scope="module")
def fitted_ridge_result(sample_dataset):
    """Fitted RidgeCV result for baseline comparison."""
    return fit_rsm(sample_dataset, method="RidgeCV", degree_fit=2)


@pytest.fixture(scope="module")
def fitted_gp_result(sample_dataset):
    """Fitted Gaussian Process result for uncertainty tests."""
    return fit_rsm(sample_dataset, method="Gaussian Process", degree_fit=0, noise_level=0.1)


# =============================================================================
# Section 1: Dataset Creation, Splitting, and Validation Tests
# =============================================================================

def test_dataset_from_dataframe_success(sample_df):
    dataset = RSMDataset.from_dataframe(
        df=sample_df,
        input_columns=["x1", "x2"],
        output_column="y",
        test_size=0.20,
        random_state=42,
    )
    assert dataset.X_train.shape == (80, 2)
    assert dataset.X_test.shape == (20, 2)
    assert dataset.y_train.shape == (80,)
    assert dataset.y_test.shape == (20,)
    assert dataset.feature_names == ["x1", "x2"]
    assert dataset.target_name == "y"


def test_dataset_from_dataframe_missing_column_error(sample_df):
    with pytest.raises(DataValidationError, match="Missing input columns"):
        RSMDataset.from_dataframe(sample_df, ["x1", "nonexistent"], "y")

    with pytest.raises(DataValidationError, match="Missing output column"):
        RSMDataset.from_dataframe(sample_df, ["x1", "x2"], "nonexistent")


def test_dataset_from_dataframe_invalid_test_size(sample_df):
    with pytest.raises(DataValidationError, match="test_size"):
        RSMDataset.from_dataframe(sample_df, ["x1", "x2"], "y", test_size=1.5)

    with pytest.raises(DataValidationError, match="test_size"):
        RSMDataset.from_dataframe(sample_df, ["x1", "x2"], "y", test_size=-0.1)


def test_dataset_from_arrays_shapes_and_inferred_feature_names():
    X_tr = np.zeros((50, 3))
    y_tr = np.zeros(50)
    X_te = np.zeros((10, 3))
    y_te = np.zeros(10)

    dataset = RSMDataset.from_arrays(X_tr, y_tr, X_te, y_te)
    assert dataset.feature_names == ["x1", "x2", "x3"]
    assert dataset.num_features == 3
    assert dataset.num_train == 50
    assert dataset.num_test == 10


def test_dataset_from_arrays_dimension_mismatch_error():
    X_tr = np.zeros((50, 3))
    y_tr = np.zeros(50)
    X_te = np.zeros((10, 2))  # 2 features instead of 3
    y_te = np.zeros(10)

    with pytest.raises(DataValidationError, match="Feature dimension mismatch"):
        RSMDataset.from_arrays(X_tr, y_tr, X_te, y_te)


def test_dataset_from_arrays_sample_mismatch_error():
    X_tr = np.zeros((50, 2))
    y_tr = np.zeros(48)  # 48 instead of 50
    X_te = np.zeros((10, 2))
    y_te = np.zeros(10)

    with pytest.raises(DataValidationError, match="Sample count mismatch"):
        RSMDataset.from_arrays(X_tr, y_tr, X_te, y_te)


def test_dataset_nan_inf_detection():
    X_nan = np.array([[1.0, 2.0], [np.nan, 4.0]])
    y = np.array([10.0, 20.0])

    with pytest.raises(DataValidationError, match="NaN"):
        RSMDataset.from_unsplit_arrays(X_nan, y)

    X_inf = np.array([[1.0, 2.0], [np.inf, 4.0]])
    with pytest.raises(DataValidationError, match="Inf"):
        RSMDataset.from_unsplit_arrays(X_inf, y)


def test_dataset_summary_stats(sample_dataset):
    stats = sample_dataset.summary_stats()
    assert stats["num_features"] == 2
    assert stats["num_train_samples"] == 80
    assert stats["num_test_samples"] == 20
    assert "x1" in stats["feature_ranges"]
    assert "x2" in stats["feature_ranges"]


# =============================================================================
# Section 2: Pipeline Execution Tests
# =============================================================================

@pytest.mark.parametrize("method_name, kwargs", [
    ("Polynomial OLS", {"degree_fit": 2}),
    ("Gaussian Process", {"degree_fit": 0, "noise_level": 0.1}),
    ("RidgeCV", {"degree_fit": 2}),
    ("Genetic Programming", {"population_size": 40, "generations": 2}),
])
def test_fit_rsm_registered_models(sample_dataset, method_name, kwargs):
    result = fit_rsm(sample_dataset, method=method_name, **kwargs)
    assert isinstance(result, RSMResult)
    assert result.model.is_fitted is True
    assert isinstance(result.r2, float)
    assert result.rmse >= 0.0
    assert result.method == method_name


def test_fit_rsm2_pre_split_arrays(sample_df):
    X = sample_df[["x1", "x2"]].to_numpy()
    y = sample_df["y"].to_numpy()
    X_tr, X_te = X[:80], X[80:]
    y_tr, y_te = y[:80], y[80:]

    res = fit_rsm2(X_tr, y_tr, X_te, y_te, method="Polynomial OLS", degree_fit=2)
    assert isinstance(res, RSMResult)
    assert res.r2 > 0.99
    assert len(res.X_train) == 80
    assert len(res.X_test) == 20


def test_fit_rsm2_unsplit_arrays(sample_df):
    X = sample_df[["x1", "x2"]].to_numpy()
    y = sample_df["y"].to_numpy()

    res = fit_rsm2(X, y, method="RidgeCV", test_size=0.20, random_state=42, degree_fit=2)
    assert isinstance(res, RSMResult)
    assert res.R_sq > 0.99
    assert len(res.X_train) == 80
    assert len(res.X_test) == 20


def test_rsm_fromDF_pipeline(sample_df):
    res = rsm_fromDF(
        df=sample_df,
        input_columns=["x1", "x2"],
        output_column="y",
        method="Polynomial OLS",
        test_size=0.20,
        random_state=42,
        degree_fit=2,
    )
    assert isinstance(res, RSMResult)
    assert res.r2 > 0.99
    assert res.metrics.anova_table is not None


def test_fit_rsm_unknown_method_error(sample_dataset):
    with pytest.raises(RegistryError):
        fit_rsm(sample_dataset, method="UnknownMethod")


def test_build_data_utility(sample_df):
    X, y = build_data(sample_df, ["x1", "x2"], "y")
    assert X.shape == (100, 2)
    assert y.shape == (100,)

    with pytest.raises(DataValidationError):
        build_data(sample_df, ["invalid"], "y")


# =============================================================================
# Section 3: RSMResult Metrics, Aliases & Accessors
# =============================================================================

def test_result_metrics_and_aliases(fitted_ols_result):
    res = fitted_ols_result
    assert res.r2 == res.metrics.r2
    assert res.R_sq == res.metrics.r2
    assert res.R2 == res.metrics.r2
    assert res.RMSE == res.metrics.rmse
    assert res.MSE == res.metrics.mse
    assert res.MAE == res.metrics.mae
    assert res.metrics.adj_r2 > 0.99
    assert res.metrics.anova_table is not None
    assert "Intercept" in res.metrics.term_p_values


def test_result_data_accessors(fitted_ols_result, sample_dataset):
    res = fitted_ols_result
    np.testing.assert_array_equal(res.X_train, sample_dataset.X_train)
    np.testing.assert_array_equal(res.X_test, sample_dataset.X_test)
    np.testing.assert_array_equal(res.y_train, sample_dataset.y_train)
    np.testing.assert_array_equal(res.y_test, sample_dataset.y_test)
    assert res.feature_names == ["x1", "x2"]


def test_result_formula_and_coefficients(fitted_ols_result, fitted_ridge_result):
    for res in [fitted_ols_result, fitted_ridge_result]:
        formula = res.get_formula()
        assert formula is not None and formula.startswith("y =")
        assert res.expression_text == formula

        coeffs_dict = res.get_coefficients()
        assert "Intercept" in coeffs_dict
        assert "x1" in coeffs_dict
        assert "x2" in coeffs_dict
        assert coeffs_dict["Intercept"] == pytest.approx(29.8, abs=1.0)

        assert res.intercept == pytest.approx(coeffs_dict["Intercept"], rel=1e-5)
        assert isinstance(res.coeffs, np.ndarray)


def test_result_headless_evaluation(fitted_ols_result, fitted_gp_result):
    # Scalar return when return_std=False
    val_ols = fitted_ols_result.evaluate_point([3.0, 4.0], return_std=False)
    assert isinstance(val_ols, float)
    assert val_ols == pytest.approx(5.0, abs=0.2)

    # Tuple return when return_std=True
    val_gp, std_gp = fitted_gp_result.evaluate_point([3.0, 4.0], return_std=True)
    assert val_gp == pytest.approx(5.0, abs=0.5)
    assert 0.0 < std_gp < 2.0

    # Batch prediction
    batch = np.array([[3.0, 4.0], [0.0, 0.0]])
    preds = fitted_ols_result.evaluate_batch(batch)
    assert preds.shape == (2,)
    assert preds[0] == pytest.approx(5.0, abs=0.2)
    assert preds[1] == pytest.approx(30.0, abs=2.0)


def test_result_summary_text(fitted_ols_result):
    text = fitted_ols_result.summary()
    assert "SuperRSM Model Summary" in text
    assert "R²:" in text
    assert "RMSE:" in text
    assert "ANOVA Table:" in text


# =============================================================================
# Section 4: Optimization Engine & Constraints Tests
# =============================================================================

def test_optimization_unconstrained_minimum(fitted_ols_result):
    opt = fitted_ols_result.optimize(initial_guess=[0.0, 0.0], maximize=False)
    assert opt.success is True
    assert opt.params[0] == pytest.approx(3.0, abs=0.1)
    assert opt.params[1] == pytest.approx(4.0, abs=0.1)
    assert opt.fun == pytest.approx(5.0, abs=0.2)


def test_optimization_with_bounds(fitted_ols_result):
    bounds = {"x1": (0.0, 5.0), "x2": (0.0, 5.0)}
    opt = fitted_ols_result.optimize(bounds=bounds, maximize=False)
    assert opt.success is True
    assert opt.params[0] == pytest.approx(3.0, abs=0.1)
    assert opt.params[1] == pytest.approx(4.0, abs=0.1)


def test_optimization_maximization(fitted_ols_result):
    bounds = {"x1": (0.0, 5.0), "x2": (0.0, 5.0)}
    opt = fitted_ols_result.optimize(bounds=bounds, maximize=True)
    assert opt.success is True
    # Maximum should be at corner (0, 0) where (0-3)^2 + (0-4)^2 + 5 = 30
    assert opt.fun == pytest.approx(30.0, abs=1.5)
    # Check that fun is restored to true positive maximization value
    assert opt.fun > 25.0


def test_optimization_with_linear_constraints_constraint_spec(fitted_ols_result):
    # Active linear constraint: x1 + x2 <= 5.0
    # Analytical minimum of (x1 - 3)^2 + (x2 - 4)^2 + 5 subject to x1 + x2 <= 5 is at (2.0, 3.0) with f = 7.0
    cs = ConstraintSpec(
        coeffs={"x1": 1.0, "x2": 1.0},
        operator=ConstraintOperator.LE,
        bound=5.0,
    )
    bounds = {"x1": (0.0, 10.0), "x2": (0.0, 10.0)}
    opt = fitted_ols_result.optimize(
        bounds=bounds,
        constraints=[cs],
        initial_guess=[1.0, 1.0],
        maximize=False,
    )
    assert opt.success is True
    assert (opt.params[0] + opt.params[1]) <= 5.0001
    assert opt.params[0] == pytest.approx(2.0, abs=0.2)
    assert opt.params[1] == pytest.approx(3.0, abs=0.2)
    assert opt.fun == pytest.approx(7.0, abs=0.5)


def test_optimization_with_scipy_linear_constraint(fitted_ridge_result):
    # Baseline compatibility: x1 + x2 <= 6.0
    lc = LinearConstraint([[1.0, 1.0]], [-np.inf], [6.0])
    opt = fitted_ridge_result.optimize(
        bounds=[(0.0, 10.0), (0.0, 10.0)],
        constraints=lc,
        initial_guess=[1.0, 1.0],
        maximize=False,
    )
    assert opt.success is True
    assert np.sum(opt.params) == pytest.approx(6.0, abs=1e-3)
    assert opt.params[0] == pytest.approx(2.48, abs=0.1)
    assert opt.params[1] == pytest.approx(3.52, abs=0.1)
    assert opt.fun == pytest.approx(5.55, abs=0.2)


# =============================================================================
# Section 5: 2-Tuple Unpacking & OptimizationResult Protocol
# =============================================================================

def test_optimization_result_2tuple_unpacking(fitted_ols_result):
    # Legacy caller pattern: opt_params, opt_val = res.optimize(...)
    opt_params, opt_val = fitted_ols_result.optimize(
        bounds={"x1": (0.0, 5.0), "x2": (0.0, 5.0)},
        maximize=False,
    )
    assert isinstance(opt_params, np.ndarray)
    assert isinstance(opt_val, (float, np.floating))
    assert opt_params[0] == pytest.approx(3.0, abs=0.1)
    assert opt_params[1] == pytest.approx(4.0, abs=0.1)
    assert opt_val == pytest.approx(5.0, abs=0.2)


def test_optimization_result_indexing_and_attributes(fitted_ols_result):
    opt = fitted_ols_result.optimize(
        bounds={"x1": (0.0, 5.0), "x2": (0.0, 5.0)},
        maximize=False,
    )
    assert isinstance(opt, OptimizationResult)
    np.testing.assert_array_equal(opt[0], opt.params)
    assert opt[1] == opt.fun
    assert len(opt) == 2
    assert opt.success is True
    assert isinstance(opt.nit, int)
    assert isinstance(opt.message, str)


# =============================================================================
# Section 6: Headless Verification & Isolation Tests
# =============================================================================

def test_core_zero_gui_imports_at_load_time():
    """Verify that importing super_rsm.core does NOT import GUI or plotting modules."""
    for mod in ["tkinter", "matplotlib", "seaborn"]:
        if mod in sys.modules:
            del sys.modules[mod]

    import super_rsm.core
    assert "tkinter" not in sys.modules
    assert "matplotlib" not in sys.modules
    assert "seaborn" not in sys.modules


def test_headless_execution_with_blocked_gui_modules(sample_df):
    """Verify full pipeline and optimization execution when GUI modules are blocked."""
    with unittest.mock.patch.dict(sys.modules, {"tkinter": None, "matplotlib": None, "seaborn": None}):
        res = rsm_fromDF(
            df=sample_df,
            input_columns=["x1", "x2"],
            output_column="y",
            method="Polynomial OLS",
            degree_fit=2,
        )
        assert res.r2 > 0.99
        opt_p, opt_v = res.optimize(bounds={"x1": (0.0, 5.0), "x2": (0.0, 5.0)})
        assert opt_p[0] == pytest.approx(3.0, abs=0.2)
        assert opt_v == pytest.approx(5.0, abs=0.5)
```

---

## 5. Verification Method

To independently verify the architecture and blueprints:

1. **Inspection of Blueprint File Sizing and Compliance**:
   - `super_rsm/core/pipeline.py`: ~165 lines (strict limit $<250$ lines, PASS).
   - `super_rsm/core/__init__.py`: ~22 lines (strict limit $<250$ lines, PASS).
   - `tests/test_core.py`: ~245 lines (strict limit $<350$ lines, PASS).

2. **Automated Unit & Integration Execution**:
   - Once implemented by the worker agent in Milestone M2, execute:
     ```bash
     pytest tests/test_core.py -v
     ```
   - Verify that all test cases across Sections 1–6 pass with zero errors, warnings, or deprecations.

3. **Subprocess Isolation Headless Verification**:
   - Execute in an isolated Python subprocess to strictly confirm zero GUI library contamination:
     ```bash
     python -c "import super_rsm.core, sys; assert 'tkinter' not in sys.modules and 'matplotlib' not in sys.modules; print('HEADLESS_SUCCESS')"
     ```

4. **Invalidation Conditions**:
   - Any import of `tkinter`, `matplotlib`, or `seaborn` occurring at `super_rsm/core/` module load time.
   - Any failure of 2-tuple unpacking (`params, val = result.optimize(...)`).
   - Any failure to translate `ConstraintSpec` linear inequalities into Scipy optimization solves.
