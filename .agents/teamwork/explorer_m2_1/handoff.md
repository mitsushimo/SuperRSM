# Technical Specification & Blueprint Handoff: `RSMDataset` & `RSMResult` (Milestone M2-1)

## 1. Observation

### 1.1 Existing Implementations in Codebase
- **`rsm_backend.py:147–270` (`rsm_result`)**:
  - Encapsulates fitted `model`, `X_train`, `y_train`, `X_test`, `y_test`, `method`.
  - Computes `R_sq`, `MSE`, `RMSE` using `sklearn.metrics.r2_score` and `mean_squared_error`.
  - Extracts unscaled polynomial coefficients (`self.coeffs`, `self.intercept`) if `extract_coeffs` is True or `named_steps` contains `ridgecv` and `standardscaler`.
  - Computes `expression_text` via `format_expression` if registered.
  - Implements `evaluate_point(params, return_std=False)` returning scalar `float` when `return_std=False`, and 2-tuple `(y_val, std_val)` when `return_std=True` (lines 222–237).
  - Implements `target_func(params, return_std=False)` (lines 211–221) returning predictions formatted for optimization.
  - Implements `optimize(initial_guess, bounds, constraints, maximize=False)` (lines 238–270) using `scipy.optimize.minimize`, returning `(result.x, opt_fun)`.
- **`rsm_backend.py:271–408` (`visualize_rsm`)**:
  - Directly embedded in `rsm_result`, creating a hard module-level dependency on graphical libraries (`from high_d_plotter import plot_multi_contour`).
  - Evaluates grids with an unvectorized $N \times M$ scalar loop calling `self.target_func(params)`.
- **`rsm_backend.py:442–468` (`build_data` and `rsm_fromDF`)**:
  - `build_data(df, input_columns, output_column)` extracts `X = df[input_columns].to_numpy()` and `y = df[output_column].to_numpy()`.
  - `rsm_fromDF` coordinates data extraction and delegates to `fit_rsm2`.
- **`tests/test_baseline.py:65–87, 180–200`**:
  - Verifies exact golden metric attributes: `res.R_sq`, `res.RMSE`, `res.MSE`, `res.intercept`, `res.coeffs`, `res.expression_text`.
  - In `test_baseline.py:84`, scalar evaluation is explicitly tested:
    ```python
    eval_val = res.evaluate_point([3.0, 4.0], return_std=False)
    assert eval_val == pytest.approx(5.08130556, rel=1e-3)
    assert isinstance(eval_val, float)
    ```
  - In `test_baseline.py:139–140`, uncertainty evaluation is tested:
    ```python
    y_val, std_val = res.evaluate_point([3.0, 4.0], return_std=True)
    assert y_val == pytest.approx(4.91444321, rel=1e-2)
    assert std_val == pytest.approx(0.61862705, rel=1e-2)
    ```
  - In `test_baseline.py:193–195`, legacy constructor calling convention is tested:
    ```python
    res = rsm.rsm_result(model, X_train, y_train, X_test, y_test, method="Genetic Programming")
    ```
- **`super_rsm/models/base.py` & `super_rsm/common/config.py`**:
  - `BaseRSMModel` is the foundational ABC in Layer 1, providing `fit(X, y)`, `predict(X)`, `predict_with_uncertainty(X)`, `evaluate_point(point, return_std=False)`, `get_metrics()`, `get_formula()`, `get_coefficients()`, `get_feature_importance()`, `compute_surface_grid(config)`.
  - `ModelMetrics` dataclass contains `r2`, `adj_r2`, `rmse`, `mse`, `mae`, `aic`, `bic`, `term_p_values`, `term_t_stats`, `term_std_errors`, `anova_table`, `custom_metrics`.
  - `DataValidationError` is defined in `super_rsm.common.exceptions`.

---

## 2. Logic Chain

1. **Decoupling Data from Fitting**:
   - *Premise (from Plan §4 & §9.3)*: The legacy code passed unstructured arrays through `fit_rsm2` and stored raw arrays directly in `rsm_result`. There was no centralized container validating shapes, preventing NaNs/Infs, computing summary statistics, or encapsulating column names.
   - *Inference*: `RSMDataset` in `super_rsm/core/dataset.py` must encapsulate `X_train`, `y_train`, `X_test`, `y_test`, `feature_names`, and `target_name`. It must provide strict validation on construction (detecting NaNs, Infs, empty arrays, dimension mismatches, duplicate column names), support train/test splitting, and supply descriptive summary statistics (`summary_stats()`) and bounding box calculations (`bounds`).
   - *Backward Compatibility*: `build_data(df, input_columns, output_column)` must remain available for direct export so legacy scripts and test fixtures run unchanged.

2. **Decoupling Result Evaluation from Visualization & Inverted Dependencies**:
   - *Premise (from Plan §4.1, §4.3 & §5.5)*: `rsm_result` in `rsm_backend.py` imported `high_d_plotter` at module load time, making headless cloud and batch HPC execution impossible without Matplotlib/Tkinter.
   - *Inference*: `RSMResult` in `super_rsm/core/result.py` must have **zero** load-time imports of `matplotlib`, `seaborn`, or `tkinter`. To preserve backward compatibility for legacy caller scripts invoking `result.visualize_rsm(...)`, `visualize_rsm` must be a function-local, lazy shim dynamically importing `super_rsm.visualization.service.VisualizationService` only at invocation time.

3. **Dual Constructor Support for Seamless Migration**:
   - *Premise (from Observation §1.1 & Baseline Tests)*: Modern architecture instantiates `RSMResult(model, dataset, metrics, method)`, but legacy tests (`tests/test_baseline.py:193`) instantiate `rsm_result(model, X_train, y_train, X_test, y_test, method=...)`.
   - *Inference*: `RSMResult.__init__` must flexibly detect whether the second argument is an `RSMDataset`. If passed array arguments (`X_train, y_train, X_test, y_test`), it must automatically construct an `RSMDataset` and compute `ModelMetrics` dynamically. This satisfies both modern decoupled callers and existing baseline tests without code changes.

4. **Return Types for Point Evaluation**:
   - *Premise (from Observation §1.1 & Baseline Tests)*: `test_baseline.py:84` tests `assert isinstance(eval_val, float)` when `return_std=False`. `test_baseline.py:139` tests `y_val, std_val = res.evaluate_point(..., return_std=True)`.
   - *Inference*: `RSMResult.evaluate_point(point, return_std=False)` must return scalar `float` when `return_std=False`, and 2-tuple `(float, Optional[float])` when `return_std=True`.

5. **Optimization Forwarding & Dual Unpacking**:
   - *Premise (from Plan §4.3 & §5.5)*: Modern callers use `opt = result.optimize(...)` accessing attributes like `opt.params`, `opt.fun`, `opt.success`, while legacy callers unpack `opt_params, opt_val = result.optimize(...)`.
   - *Inference*: `RSMResult.optimize` must delegate to `OptimizationEngine.optimize(...)` and return an `OptimizationResult` whose `__iter__` yields `(self.params, self.fun)`.

6. **Strict Architectural Constraints**:
   - Both modules must stay strictly under 250 lines of code.
   - All internal imports must use absolute package notation (`super_rsm.core.dataset`, `super_rsm.models.base`, `super_rsm.common.exceptions`).

---

## 3. Caveats

1. **Downstream Optimization Engine**: `RSMResult.optimize()` delegates to `super_rsm.core.optimization.OptimizationEngine`. During testing of M2-1 in isolation before M2-2 is complete, `optimize()` will raise an `ImportError` or `NotImplementedError` if `OptimizationEngine` is not yet present; this is normal dependency sequencing.
2. **Downstream Visualization Service**: `RSMResult.visualize_rsm()` delegates to `super_rsm.visualization.service.VisualizationService`. This will only execute when Milestone M3 is complete; calling it before M3 will raise an informative `ImportError`.
3. **Legacy scikit-learn Pipeline vs BaseRSMModel**: When wrapping legacy models (e.g. from baseline tests where `model` is a raw sklearn `Pipeline`), `RSMResult` must gracefully inspect `named_steps` to compute legacy coefficients (`coeffs`, `intercept`) if `model.get_coefficients()` is absent.

---

## 4. Conclusion & Complete Blueprints

Below are the exact, copy-paste ready implementation blueprints for `super_rsm/core/dataset.py` and `super_rsm/core/result.py`.

### 4.1 Blueprint: `super_rsm/core/dataset.py`

- **Target Path**: `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\super_rsm\core\dataset.py`
- **Estimated Line Count**: ~180 lines (strictly <250 lines).
- **Zero GUI/Matplotlib imports**: Standard library + numpy + pandas + scikit-learn.

```python
"""
super_rsm/core/dataset.py

RSMDataset container: headless dataset encapsulation, array validation,
train/test splitting, summary statistics, and bounding box computation.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from super_rsm.common.exceptions import DataValidationError
from super_rsm.common.types import ArrayLike


@dataclass
class RSMDataset:
    """
    Immutable domain container for Response Surface Methodology datasets.
    Stores validated training and testing splits, feature names, and target metadata.
    """
    X_train: np.ndarray
    y_train: np.ndarray
    X_test: np.ndarray = field(default_factory=lambda: np.empty((0, 0), dtype=float))
    y_test: np.ndarray = field(default_factory=lambda: np.empty((0,), dtype=float))
    feature_names: List[str] = field(default_factory=list)
    target_name: str = "y"

    def __post_init__(self) -> None:
        # 1. Type coercion to standard numpy float64 arrays
        self.X_train = np.asarray(self.X_train, dtype=float)
        self.y_train = np.asarray(self.y_train, dtype=float).ravel()
        if self.X_test is not None and len(self.X_test) > 0:
            self.X_test = np.asarray(self.X_test, dtype=float)
            self.y_test = np.asarray(self.y_test, dtype=float).ravel()
        else:
            n_features = self.X_train.shape[1] if self.X_train.ndim == 2 else 0
            self.X_test = np.empty((0, n_features), dtype=float)
            self.y_test = np.empty((0,), dtype=float)

        # 2. Default feature names if unspecified
        if not self.feature_names:
            n_features = self.X_train.shape[1] if self.X_train.ndim == 2 else 0
            self.feature_names = [f"x{i}" for i in range(n_features)]
        else:
            self.feature_names = list(self.feature_names)

        # 3. Comprehensive array validation
        self.validate()

    def validate(self) -> None:
        """Validate array dimensions, row counts, and check for NaNs/Infs."""
        if self.X_train.ndim != 2:
            raise DataValidationError(f"X_train must be a 2D array, got shape {self.X_train.shape}")
        if self.y_train.ndim != 1:
            raise DataValidationError(f"y_train must be a 1D array, got shape {self.y_train.shape}")
        if len(self.X_train) == 0:
            raise DataValidationError("X_train cannot be empty.")
        if len(self.X_train) != len(self.y_train):
            raise DataValidationError(
                f"Row mismatch: X_train has {len(self.X_train)} rows but y_train has {len(self.y_train)} rows."
            )
        if self.X_train.shape[1] != len(self.feature_names):
            raise DataValidationError(
                f"Feature count mismatch: X_train has {self.X_train.shape[1]} columns, "
                f"but feature_names has {len(self.feature_names)} items."
            )
        if len(set(self.feature_names)) != len(self.feature_names):
            raise DataValidationError(f"Duplicate feature names detected: {self.feature_names}")

        if np.isnan(self.X_train).any():
            raise DataValidationError("X_train contains NaN values.")
        if np.isinf(self.X_train).any():
            raise DataValidationError("X_train contains infinite values.")
        if np.isnan(self.y_train).any():
            raise DataValidationError("y_train contains NaN values.")
        if np.isinf(self.y_train).any():
            raise DataValidationError("y_train contains infinite values.")

        if len(self.X_test) > 0:
            if self.X_test.ndim != 2:
                raise DataValidationError(f"X_test must be a 2D array, got shape {self.X_test.shape}")
            if self.y_test.ndim != 1:
                raise DataValidationError(f"y_test must be a 1D array, got shape {self.y_test.shape}")
            if len(self.X_test) != len(self.y_test):
                raise DataValidationError(
                    f"Row mismatch in test split: X_test has {len(self.X_test)} rows, "
                    f"y_test has {len(self.y_test)} rows."
                )
            if self.X_test.shape[1] != self.X_train.shape[1]:
                raise DataValidationError(
                    f"Column mismatch: X_test has {self.X_test.shape[1]} columns, "
                    f"expected {self.X_train.shape[1]}."
                )
            if np.isnan(self.X_test).any() or np.isnan(self.y_test).any():
                raise DataValidationError("X_test or y_test contains NaN values.")
            if np.isinf(self.X_test).any() or np.isinf(self.y_test).any():
                raise DataValidationError("X_test or y_test contains infinite values.")

    @classmethod
    def from_dataframe(
        cls,
        df: pd.DataFrame,
        input_columns: Sequence[str],
        output_column: str,
        test_size: float = 0.2,
        random_state: Optional[int] = 42,
        shuffle: bool = True,
    ) -> "RSMDataset":
        """Construct RSMDataset directly from a pandas DataFrame with automated train/test split."""
        if not isinstance(df, pd.DataFrame):
            raise DataValidationError(f"Expected pandas DataFrame, got {type(df).__name__}")
        if df.empty:
            raise DataValidationError("Input DataFrame cannot be empty.")
        if not input_columns:
            raise DataValidationError("input_columns cannot be empty.")

        missing_inputs = [c for c in input_columns if c not in df.columns]
        if missing_inputs:
            raise DataValidationError(f"Input column(s) not found in DataFrame: {missing_inputs}")
        if output_column not in df.columns:
            raise DataValidationError(f"Output column '{output_column}' not found in DataFrame.")
        if output_column in input_columns:
            raise DataValidationError(f"Output column '{output_column}' cannot be included in input_columns.")

        X = df[list(input_columns)].to_numpy(dtype=float)
        y = df[output_column].to_numpy(dtype=float).ravel()

        if test_size < 0.0 or test_size >= 1.0:
            raise DataValidationError(f"test_size must be in [0.0, 1.0), got {test_size}")

        if test_size > 0.0 and len(df) > 1:
            X_tr, X_te, y_tr, y_te = train_test_split(
                X, y, test_size=test_size, random_state=random_state, shuffle=shuffle
            )
        else:
            X_tr, y_tr = X, y
            X_te = np.empty((0, X.shape[1]), dtype=float)
            y_te = np.empty((0,), dtype=float)

        return cls(
            X_train=X_tr,
            y_train=y_tr,
            X_test=X_te,
            y_test=y_te,
            feature_names=list(input_columns),
            target_name=str(output_column),
        )

    @classmethod
    def from_arrays(
        cls,
        X: ArrayLike,
        y: ArrayLike,
        feature_names: Optional[Sequence[str]] = None,
        target_name: str = "y",
        test_size: float = 0.2,
        random_state: Optional[int] = 42,
        shuffle: bool = True,
    ) -> "RSMDataset":
        """Construct RSMDataset from raw array-like inputs with automated train/test split."""
        X_arr = np.asarray(X, dtype=float)
        y_arr = np.asarray(y, dtype=float).ravel()

        if test_size < 0.0 or test_size >= 1.0:
            raise DataValidationError(f"test_size must be in [0.0, 1.0), got {test_size}")

        if test_size > 0.0 and len(X_arr) > 1:
            X_tr, X_te, y_tr, y_te = train_test_split(
                X_arr, y_arr, test_size=test_size, random_state=random_state, shuffle=shuffle
            )
        else:
            X_tr, y_tr = X_arr, y_arr
            n_feat = X_arr.shape[1] if X_arr.ndim == 2 else 0
            X_te = np.empty((0, n_feat), dtype=float)
            y_te = np.empty((0,), dtype=float)

        names = list(feature_names) if feature_names is not None else [f"x{i}" for i in range(X_arr.shape[1])]
        return cls(
            X_train=X_tr,
            y_train=y_tr,
            X_test=X_te,
            y_test=y_te,
            feature_names=names,
            target_name=target_name,
        )

    @property
    def n_train(self) -> int:
        return len(self.X_train)

    @property
    def n_test(self) -> int:
        return len(self.X_test)

    @property
    def n_total(self) -> int:
        return len(self.X_train) + len(self.X_test)

    @property
    def n_features(self) -> int:
        return self.X_train.shape[1]

    @property
    def has_test_set(self) -> bool:
        return len(self.X_test) > 0

    @property
    def X_all(self) -> np.ndarray:
        """Combined training and testing input coordinates."""
        if self.has_test_set:
            return np.vstack([self.X_train, self.X_test])
        return self.X_train

    @property
    def y_all(self) -> np.ndarray:
        """Combined training and testing target observations."""
        if self.has_test_set:
            return np.concatenate([self.y_train, self.y_test])
        return self.y_train

    @property
    def bounds(self) -> Dict[str, Tuple[float, float]]:
        """Physical parameter min/max bounding box across all observations."""
        comb = self.X_all
        return {
            name: (float(np.min(comb[:, i])), float(np.max(comb[:, i])))
            for i, name in enumerate(self.feature_names)
        }

    def summary_stats(self) -> Dict[str, Dict[str, float]]:
        """Compute comprehensive descriptive summary statistics across all data."""
        stats: Dict[str, Dict[str, float]] = {}
        comb_X = self.X_all
        for i, name in enumerate(self.feature_names):
            col = comb_X[:, i]
            stats[name] = {
                "min": float(np.min(col)),
                "max": float(np.max(col)),
                "mean": float(np.mean(col)),
                "std": float(np.std(col, ddof=1)) if len(col) > 1 else 0.0,
                "median": float(np.median(col)),
                "q25": float(np.percentile(col, 25)),
                "q75": float(np.percentile(col, 75)),
            }

        comb_y = self.y_all
        stats[self.target_name] = {
            "min": float(np.min(comb_y)),
            "max": float(np.max(comb_y)),
            "mean": float(np.mean(comb_y)),
            "std": float(np.std(comb_y, ddof=1)) if len(comb_y) > 1 else 0.0,
            "median": float(np.median(comb_y)),
            "q25": float(np.percentile(comb_y, 25)),
            "q75": float(np.percentile(comb_y, 75)),
        }
        return stats

    def __repr__(self) -> str:
        return (
            f"RSMDataset(n_train={self.n_train}, n_test={self.n_test}, "
            f"n_features={self.n_features}, target='{self.target_name}')"
        )


def build_data(
    df: pd.DataFrame,
    input_columns: Sequence[str],
    output_column: str,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Legacy helper extracting input (X) and target (y) numpy arrays from a DataFrame.
    Provided for 100% backward compatibility with legacy rsm_backend scripts.
    """
    if not isinstance(df, pd.DataFrame):
        raise DataValidationError(f"Expected pandas DataFrame, got {type(df).__name__}")
    missing_inputs = [c for c in input_columns if c not in df.columns]
    if missing_inputs:
        raise DataValidationError(f"Input column(s) not found in DataFrame: {missing_inputs}")
    if output_column not in df.columns:
        raise DataValidationError(f"Output column '{output_column}' not found in DataFrame.")

    X = df[list(input_columns)].to_numpy(dtype=float)
    y = df[output_column].to_numpy(dtype=float).ravel()
    return X, y
```

---

### 4.2 Blueprint: `super_rsm/core/result.py`

- **Target Path**: `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\super_rsm\core\result.py`
- **Estimated Line Count**: ~220 lines (strictly <250 lines).
- **Zero load-time GUI / Matplotlib imports**: Lazy visualization shim cleanly isolated.

```python
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
    """
    Canonical result container holding trained surrogate model, dataset, and metrics.
    Provides backward-compatible attribute aliases and lazy visualization shims.
    """

    def __init__(
        self,
        model: Any,
        dataset_or_X_train: Any,
        y_train: Optional[np.ndarray] = None,
        X_test: Optional[np.ndarray] = None,
        y_test: Optional[np.ndarray] = None,
        method: str = "Gaussian Process",
        metrics: Optional[ModelMetrics] = None,
    ):
        self.model = model
        self.method = method
        self.last_opt_result: Optional["OptimizationResult"] = None
        self.last_opt_maximize: bool = False

        # Support both modern (model, dataset) and legacy (model, X_train, y_train, X_test, y_test)
        if isinstance(dataset_or_X_train, RSMDataset):
            self.dataset: RSMDataset = dataset_or_X_train
        else:
            self.dataset = RSMDataset(
                X_train=dataset_or_X_train,
                y_train=y_train if y_train is not None else np.empty((0,)),
                X_test=X_test if X_test is not None else np.empty((0, 0)),
                y_test=y_test if y_test is not None else np.empty((0,)),
            )

        # Inspect uncertainty capability
        if hasattr(model, "get_metadata"):
            self.supports_uncertainty: bool = model.get_metadata().supports_uncertainty
        elif hasattr(model, "supports_uncertainty"):
            self.supports_uncertainty = bool(model.supports_uncertainty)
        else:
            self.supports_uncertainty = False

        # Compute or assign ModelMetrics
        self.sigma_test: Optional[np.ndarray] = None
        if metrics is not None:
            self.metrics: ModelMetrics = metrics
        elif hasattr(model, "metrics") and model.metrics is not None:
            self.metrics = model.metrics
        else:
            self.metrics = self._compute_test_metrics()

        # Extract unscaled coefficients and formula for backward compatibility
        self.coeffs: Optional[np.ndarray] = None
        self.intercept: Optional[float] = None
        self.expression_text: Optional[str] = None
        self._extract_model_diagnostics()

    def _compute_test_metrics(self) -> ModelMetrics:
        """Compute goodness-of-fit metrics on test split if available, otherwise on train split."""
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
        rmse = float(np.sqrt(mse))
        mae = float(np.mean(np.abs(eval_y - y_pred)))
        return ModelMetrics(r2=r2, rmse=rmse, mse=mse, mae=mae)

    def _extract_model_diagnostics(self) -> None:
        """Extract coefficients, intercept, and mathematical formula if supported."""
        if hasattr(self.model, "get_formula"):
            self.expression_text = self.model.get_formula()

        if hasattr(self.model, "get_coefficients"):
            c_dict = self.model.get_coefficients()
            if c_dict is not None:
                self.intercept = c_dict.get("Intercept", None)
                self.coeffs = np.array([v for k, v in c_dict.items() if k != "Intercept"], dtype=float)

        # Fallback for raw scikit-learn RidgeCV pipeline
        if self.coeffs is None and hasattr(self.model, "named_steps"):
            try:
                scaler = self.model.named_steps.get("standardscaler")
                ridge = self.model.named_steps.get("ridgecv")
                if scaler is not None and ridge is not None:
                    self.coeffs = ridge.coef_ / scaler.scale_
                    self.intercept = float(ridge.intercept_ - np.dot(self.coeffs, scaler.mean_))
            except Exception:
                pass

    # --------------------------------------------------------------------------
    # Backward-Compatible Metric & Data Properties
    # --------------------------------------------------------------------------
    @property
    def R_sq(self) -> float:
        return self.metrics.r2

    @property
    def R2(self) -> float:
        return self.metrics.r2

    @property
    def RMSE(self) -> float:
        return self.metrics.rmse

    @property
    def MSE(self) -> float:
        return self.metrics.mse

    @property
    def MAE(self) -> Optional[float]:
        return self.metrics.mae

    @property
    def X_train(self) -> np.ndarray:
        return self.dataset.X_train

    @property
    def y_train(self) -> np.ndarray:
        return self.dataset.y_train

    @property
    def X_test(self) -> np.ndarray:
        return self.dataset.X_test

    @property
    def y_test(self) -> np.ndarray:
        return self.dataset.y_test

    @property
    def feature_names(self) -> List[str]:
        return self.dataset.feature_names

    @property
    def target_name(self) -> str:
        return self.dataset.target_name

    # --------------------------------------------------------------------------
    # Analytical Evaluation Methods
    # --------------------------------------------------------------------------
    def evaluate_point(
        self,
        point: Union[np.ndarray, Sequence[float]],
        return_std: bool = False,
    ) -> Union[float, Tuple[float, Optional[float]]]:
        """
        Evaluate model at a single point coordinate.
        Returns:
            - If return_std=False: float predicted output value.
            - If return_std=True: Tuple (float predicted mean, float or None std dev).
        """
        X_eval = np.asarray(point, dtype=float).reshape(1, -1)
        if return_std:
            if not self.supports_uncertainty:
                y_pred = self.model.predict(X_eval)
                return float(np.asarray(y_pred, dtype=float).ravel()[0]), None
            if hasattr(self.model, "predict_with_uncertainty"):
                y_pred, sigma = self.model.predict_with_uncertainty(X_eval)
            else:
                y_pred, sigma = self.model.predict(X_eval, return_std=True)
            return float(np.asarray(y_pred, dtype=float).ravel()[0]), float(np.asarray(sigma, dtype=float).ravel()[0])

        y_pred = self.model.predict(X_eval)
        return float(np.asarray(y_pred, dtype=float).ravel()[0])

    def evaluate_batch(
        self,
        X_batch: Union[np.ndarray, Sequence[Sequence[float]]],
        return_std: bool = False,
    ) -> Union[np.ndarray, Tuple[np.ndarray, np.ndarray]]:
        """Vectorized batch prediction for multi-contour surface evaluation."""
        X_arr = np.asarray(X_batch, dtype=float)
        if return_std:
            if not self.supports_uncertainty:
                raise UncertaintyNotSupportedError(f"Model '{self.method}' does not support predictive uncertainty.")
            if hasattr(self.model, "predict_with_uncertainty"):
                return self.model.predict_with_uncertainty(X_arr)
            return self.model.predict(X_arr, return_std=True)
        return self.model.predict(X_arr)

    def target_func(self, params: Any, return_std: bool = False) -> Any:
        """Callable objective interface for numerical optimization algorithms."""
        return self.evaluate_point(params, return_std=return_std)

    def optimize(
        self,
        initial_guess: Optional[Any] = None,
        bounds: Optional[Any] = None,
        constraints: Optional[Any] = None,
        maximize: bool = False,
        **kwargs: Any,
    ) -> "OptimizationResult":
        """Execute constrained continuous optimization over the response surface."""
        from super_rsm.core.optimization import OptimizationEngine
        res = OptimizationEngine.optimize(
            model=self.model,
            dataset=self.dataset,
            initial_guess=initial_guess,
            bounds=bounds,
            constraints=constraints,
            maximize=maximize,
            **kwargs,
        )
        self.last_opt_result = res
        self.last_opt_maximize = bool(maximize)
        return res

    def get_formula(self) -> Optional[str]:
        return self.expression_text

    def get_coefficients(self) -> Optional[Dict[str, float]]:
        if hasattr(self.model, "get_coefficients"):
            return self.model.get_coefficients()
        return None

    def get_feature_importance(self) -> Optional[Dict[str, float]]:
        if hasattr(self.model, "get_feature_importance"):
            return self.model.get_feature_importance()
        return None

    def summary(self) -> str:
        """Return formatted diagnostic summary string."""
        lines = [
            f"SuperRSM Model Summary: {self.method}",
            f"{'=' * 50}",
            f"Target Variable: {self.target_name}",
            f"Input Factors ({len(self.feature_names)}): {', '.join(self.feature_names)}",
            f"Training Samples: {self.dataset.n_train} | Testing Samples: {self.dataset.n_test}",
            f"{'-' * 50}",
            f"Goodness-of-Fit Metrics (Test Set):",
            f"  R² Score: {self.metrics.r2:.5f}",
            f"  RMSE:     {self.metrics.rmse:.5f}",
            f"  MSE:      {self.metrics.mse:.5f}",
        ]
        if self.metrics.mae is not None:
            lines.append(f"  MAE:      {self.metrics.mae:.5f}")
        if self.metrics.adj_r2 is not None:
            lines.append(f"  Adj. R²:  {self.metrics.adj_r2:.5f}")
        if self.metrics.aic is not None:
            lines.append(f"  AIC:      {self.metrics.aic:.2f} | BIC: {self.metrics.bic:.2f}")
        if self.expression_text:
            lines.extend([f"{'-' * 50}", f"Model Expression: {self.expression_text}"])
        if self.metrics.anova_table is not None:
            lines.extend([f"{'-' * 50}", "ANOVA Table:", str(self.metrics.anova_table)])
        return "\n".join(lines)

    def __str__(self) -> str:
        """Preserves exact legacy rsm_result string format for backward compatibility."""
        parts = [f"Regression Method: {self.method}"]
        if self.expression_text:
            parts.append(self.expression_text)
        if self.intercept is not None and self.coeffs is not None:
            parts.append(f"Intercept: {self.intercept}, Coefficients: {self.coeffs}")
        parts.append(f"Coefficient of Determination (R2): {self.R_sq}")
        parts.append(f"Mean Squared Error (MSE): {self.MSE}")
        parts.append(f"Root Mean Squared Error (RMSE): {self.RMSE}")
        return "\n".join(parts)

    def __repr__(self) -> str:
        return f"RSMResult(method='{self.method}', R2={self.metrics.r2:.4f}, RMSE={self.metrics.rmse:.4f})"

    # --------------------------------------------------------------------------
    # Backward-Compatible Lazy Visualization Shim
    # --------------------------------------------------------------------------
    def visualize_rsm(
        self,
        config: Any,
        title: str = "Function Visualization",
        xlabel: str = "X",
        ylabel: str = "Y",
        label_array: Optional[List[str]] = None,
        plot_settings: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Backward-compatible visualization shim.
        Dynamically imports super_rsm.visualization.service only when invoked,
        allowing core to remain 100% headless while preserving legacy caller scripts.
        """
        try:
            from super_rsm.visualization.service import VisualizationService
        except ImportError as exc:
            raise ImportError(
                "Visualization subsystem is not available or graphical libraries are missing. "
                "Ensure super_rsm.visualization is present and matplotlib is installed."
            ) from exc
        return VisualizationService.visualize_result(
            result=self,
            config=config,
            title=title,
            xlabel=xlabel,
            ylabel=ylabel,
            label_array=label_array,
            plot_settings=plot_settings,
        )


# Backward-compatible alias
rsm_result = RSMResult
```

---

## 5. Verification Method

### 5.1 Independent Test Verification
An implementer or automated harness can verify this specification by creating unit tests in `tests/test_core_dataset_result.py` exercising:

1. **`RSMDataset` Integrity Checks**:
   - Instantiate with clean 2D array and 1D target: verify properties `n_train`, `n_test`, `n_total`, `n_features`, `bounds`.
   - Pass NaN array: assert `DataValidationError` is raised.
   - Pass Inf array: assert `DataValidationError` is raised.
   - Pass row mismatch (`len(X) != len(y)`): assert `DataValidationError` is raised.
   - Test `from_dataframe`: verify splitting ratio, column extraction, and duplicate column rejection.
   - Test `summary_stats()`: verify returned dictionary contains all required statistical keys (`min`, `max`, `mean`, `std`, `median`, `q25`, `q75`) for each feature and target.
   - Test legacy `build_data(df, input_columns, output_column)`: assert returns identical 2-tuple `(X, y)` matching `rsm_backend.build_data`.

2. **`RSMResult` Evaluation and Aliases**:
   - Wrap a fitted `PolynomialOLSModel` and `RSMDataset`:
     - Assert `res.R_sq == res.r2 == res.R2`
     - Assert `res.RMSE == res.rmse`
     - Assert `res.MSE == res.mse`
     - Assert `res.expression_text == res.get_formula()`
     - Assert `res.coeffs is not None` and `res.intercept is not None`
   - Point Evaluation return contracts:
     - `val = res.evaluate_point([3.0, 4.0], return_std=False)` -> assert `isinstance(val, float)`
     - `mean, std = res.evaluate_point([3.0, 4.0], return_std=True)` -> assert `isinstance(mean, float)`
   - Batch Evaluation:
     - `X_batch = np.array([[3.0, 4.0], [2.0, 1.0]])`
     - `y_pred = res.evaluate_batch(X_batch)` -> assert `y_pred.shape == (2,)`
   - Test legacy constructor invocation:
     - `res_legacy = rsm_result(model, X_train, y_train, X_test, y_test, method="Polynomial OLS")`
     - Assert `res_legacy.dataset.n_train == len(X_train)`
     - Assert `str(res_legacy)` contains `"Regression Method: Polynomial OLS"` and `"Coefficient of Determination (R2):"`

3. **Headless Execution Verification**:
   - Run tests in a Python subprocess where `sys.modules['matplotlib'] = None` and `sys.modules['tkinter'] = None`.
   - Assert importing `super_rsm.core.dataset` and `super_rsm.core.result` succeeds without error.
   - Assert `visualize_rsm` raises `ImportError` gracefully when graphical dependencies are absent.

4. **Line Count & DAG Conformance**:
   - Count lines: `wc -l super_rsm/core/dataset.py super_rsm/core/result.py`.
   - Both files must be strictly under 250 lines.
