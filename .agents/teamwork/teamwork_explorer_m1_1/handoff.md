# Milestone M1 Baseline Test Harness & Existing Model Behavior Specification

**Investigator**: Explorer 1 (`teamwork_explorer_m1_1`)  
**Target Milestone**: M1 (Foundations, Baseline & Models Subsystem)  
**Target File**: `tests/test_baseline.py`  
**Date**: 2026-10-30T03:45:00Z  
**Context**: Pre-refactoring baseline characterization using `sample_data.csv` and `rsm_backend.py`.

---

## 1. Observation

### 1.1 Dataset Properties (`sample_data.csv`)
- **Location**: `sample_data.csv` in workspace root (`5,605` bytes).
- **Format**: 100 rows, 3 columns (`x1, x2, y`). Line 1 is header, lines 2–101 are numeric data, line 102 is trailing empty newline.
- **Analytical Truth**: Points were generated from the true quadratic paraboloid:
  $$y = (x_1 - 3.0)^2 + (x_2 - 4.0)^2 + 5.0 = x_1^2 + x_2^2 - 6 x_1 - 8 x_2 + 30.0$$
  - Theoretical global minimum: $\mathbf{x}^* = (3.0, 4.0)$ with $y^* = 5.0$.
- **Train/Test Splitting**:
  - `train_test_split(X, y, test_size=0.20, random_state=42)` produces:
    - `X_train.shape = (80, 2)`, `y_train.shape = (80,)`
    - `X_test.shape = (20, 2)`, `y_test.shape = (20,)`

---

### 1.2 Exact Empirical Baseline Metrics on `sample_data.csv`

The following empirical measurements were recorded directly from running `rsm_backend.fit_rsm2` and `rsm_result` methods on `sample_data.csv`:

#### A. RidgeCV (`degree_fit=2`, default `test_size=0.20`)
- **Fit Quality**:
  - Test $R^2$: `0.99914587`
  - Test MSE: `0.21175413`
  - Test RMSE: `0.46016751`
- **Unscaled Coefficients & Intercept** (`rsm_result.coeffs`, `rsm_result.intercept`):
  - Intercept ($\beta_0$): `29.61519176` (Theoretical: `30.0`)
  - $x_1$: `-5.81921897` (Theoretical: `-6.0`)
  - $x_2$: `-7.94330688` (Theoretical: `-8.0`)
  - $x_1^2$: `0.98312801` (Theoretical: `1.0`)
  - $x_1 x_2$: `-0.00442790` (Theoretical: `0.0`)
  - $x_2^2$: `0.99387381` (Theoretical: `1.0`)
- **Point Evaluation at Known Minimum $(3.0, 4.0)$**:
  - `evaluate_point([3.0, 4.0], return_std=False)`: `5.08130556` (Theoretical: `5.00000000`)
- **Unconstrained Minimization** (Initial guess `[0.0, 0.0]`, method `minimize`):
  - Optimal coordinates: $\mathbf{x}^* = [2.96855682, 4.00274702]$
  - Optimal value: $y^* = 5.08032568$
- **Constrained Minimization**:
  - Constraint: $x_1 + x_2 \le 6.0$ via `LinearConstraint([[1.0, 1.0]], [-np.inf], [6.0])`
  - Parameter bounds: $[(0.0, 10.0), (0.0, 10.0)]$
  - Initial guess: `[1.0, 1.0]`
  - Optimal coordinates: $\mathbf{x}^* = [2.48027093, 3.51972907]$
  - Sum $x_1^* + x_2^*$: `6.00000000` (Active constraint boundary satisfied to machine precision)
  - Optimal value: $y^* = 5.54555911$

---

#### B. Gaussian Process Regressor
`rsm_backend.py` supports two modes based on `degree_fit`:

1. **Ordinary Kriging (`degree_fit=0`)**:
   - Kernel: `1.0 * RBF(length_scale=1.0) + WhiteKernel(noise_level=0.1)`, `normalize_y=True`
   - Test $R^2$: `0.99892255`
   - Test MSE: `0.26711941`
   - Test RMSE: `0.51683596`
   - Point Evaluation at $(3.0, 4.0)$ with uncertainty:
     - Mean prediction: `4.91444321`
     - Standard error ($\sigma$): `0.61862705`
   - Unconstrained Minimization (Initial guess `[0.0, 0.0]`):
     - Optimal coordinates: $\mathbf{x}^* = [3.02551088, 4.01643430]$
     - Optimal value: $y^* = 4.91495471$

2. **Universal Kriging (`degree_fit=2`)**:
   - Kernel: `DotProduct(sigma_0=1.0) + RBF(length_scale=1.0) + WhiteKernel(noise_level=0.1)`, with `PolynomialFeatures(degree=2, include_bias=False)`
   - Test $R^2$: `0.46498835`
   - Test MSE: `132.63914649`
   - Test RMSE: `11.51690698`
   - Point Evaluation at $(3.0, 4.0)$:
     - Mean prediction: `18.15437702`
     - Standard error ($\sigma$): `9.48129335`
   - Optimization note: In scikit-learn, fitting degree 2 polynomial features into DotProduct + RBF triggers a `ConvergenceWarning` on the lower length-scale bound (`1e-5`), explaining the reduced test score compared to Ordinary Kriging.

---

#### C. Genetic Programming Symbolic Regressor (`degree_fit=2`, default parameters)
- **Parameters**: `population_size=5000`, `generations=30`, `random_state=42`, custom primitive `piecewise_function`.
- **Fit Quality**:
  - Test $R^2$: `-41.72123783`
  - Test MSE: `10591.37415799`
  - Test RMSE: `102.91440209`
- **Resulting Program Expression String**:
  ```
  add(log(sub(sqrt(-1.829), log(X1))), add(sqrt(div(add(piecewise(-17.193, sqrt(log(17.448)), X0), sub(div(div(X1, X0), sqrt(sqrt(X0))), log(X1))), mul(X1, X1))), add(log(sub(sqrt(-1.829), log(X1))), add(sqrt(div(add(mul(sub(-0.153, X1), piecewise(X1, X1, X0)), add(sqrt(add(log(sub(sqrt(-1.829), log(X1))), add(piecewise(-17.193, X0, X0), div(div(X1, X0), 12.099)))), piecewise(-12.046, X0, 16.026))), mul(X1, log(sub(sqrt(-1.829), log(X1)))))), add(log(sub(sqrt(-1.829), log(X0))), add(log(sub(sqrt(-1.829), log(X0))), add(sub(sqrt(-1.829), sqrt(X1)), add(mul(sqrt(X0), add(X1, X0)), div(div(X1, X0), sqrt(sqrt(X0)))))))))))
  ```
- **Point Evaluation at $(3.0, 4.0)$**:
  - Value: `3.45031311`
- **Unconstrained Minimization**:
  - Parameters: `[0.0, 0.0]`, Value: `5.55998701`
- **Constrained Minimization** ($x_1 + x_2 \le 6.0$, bounds $[0, 10]^2$):
  - Parameters: `[0.96010626, 0.00099990]`, Value: `5.53047477`
- **Runtime**: Full evaluation takes ~3 minutes 10 seconds.

---

#### D. Reference Classical OLS Model (Benchmark for `PolynomialOLSModel`)
Fitting quadratic polynomial regression via least-squares:
- Test $R^2$: `0.99921880`
- Test RMSE: `0.44008496`
- Point Evaluation at $(3.0, 4.0)$: `5.03864360`
- Estimated Parameters:
  - Intercept: `29.76647090`
  - $x_1$: `-5.85971730`
  - $x_2$: `-7.98845690`
  - $x_1^2$: `0.98665215`
  - $x_1 x_2$: `-0.00325412`
  - $x_2^2$: `0.99777077`

---

## 2. Logic Chain

1. **Golden Baseline Purpose**:
   - The refactoring reorganization moves code from `rsm_backend.py` to `super_rsm/models/` and `super_rsm/core/`.
   - `tests/test_baseline.py` must lock in the numerical correctness of the legacy baseline and serve as an immutable regression check.
   - Any refactoring change that alters RidgeCV coefficients by more than `0.01` or shifts the constrained optimization minimum indicates an algorithmic drift or bug.

2. **Selecting Model Verification Targets**:
   - **RidgeCV** is the mathematical anchor: It is closed-form, deterministic, and hits $R^2 = 0.99915$ on this quadratic data. Testing its unscaled coefficients ensures the scaler transformation equation:
     $$\beta_{\text{unscaled}} = \beta_{\text{scaled}} / \sigma, \quad \beta_{0, \text{unscaled}} = \beta_{0, \text{scaled}} - \beta_{\text{unscaled}} \cdot \mu$$
     remains 100% intact.
   - **Gaussian Process Ordinary Kriging (`degree_fit=0`)** is the primary Kriging anchor: It fits with $R^2 = 0.99892$, yielding meaningful point prediction ($4.914 \pm 0.619$) and optimization ($[3.025, 4.016] \approx [3.0, 4.0]$). Universal Kriging (`degree_fit=2`) should also be tested to verify polynomial feature handling.
   - **Constrained Optimization**:
     - The true minimum is $(3.0, 4.0)$ where $x_1 + x_2 = 7.0$.
     - Imposing $x_1 + x_2 \le 6.0$ makes the constraint strictly active.
     - Analytically for $f(x) = (x_1 - 3)^2 + (x_2 - 4)^2 + 5$, minimizing subject to $x_1 + x_2 = 6$ yields $x_1^* = 2.5, x_2^* = 3.5, y^* = 5.5$.
     - RidgeCV yields $\mathbf{x}^* = [2.480, 3.520], y^* = 5.546$. This provides an exact verification point for Scipy `LinearConstraint` integration.

3. **Managing Genetic Programming Test Duration**:
   - Full 5,000 population $\times$ 30 generations takes 190 seconds. Running this on every `pytest` invocation would unacceptably slow developer turnaround.
   - **Strategy**:
     - Define a fast baseline smoke test (`generations=2`, `population_size=100`, takes $< 2$ seconds) verifying `SymbolicRegressor` executes, computes metrics, extracts `_program`, and evaluates points.
     - Include the full golden test marked with `@pytest.mark.slow` or enabled via an environment flag `RUN_SLOW_BASELINE=1`, verifying the exact program expression and metrics recorded above.

4. **Integration with `tests/test_baseline.py`**:
   - The test file will directly import from `rsm_backend` (or `super_rsm.core` / `super_rsm.models` once shims/modules are in place).
   - Fixture `sample_dataset` reads `sample_data.csv` using `Path(__file__).parent.parent / "sample_data.csv"`.

---

## 3. Caveats

1. **Floating-Point Tolerances Across Platforms & Scipy Versions**:
   - Numerical optimization (L-BFGS-B, SLSQP) and cross-validation splits can exhibit minute differences in the 5th or 6th decimal place across OS platforms and scikit-learn versions.
   - All assertions must use `pytest.approx` or `numpy.testing.assert_allclose` with appropriate relative (`rtol=1e-3`) and absolute (`atol=1e-3`) tolerances rather than strict equality `==`.
2. **Genetic Programming Non-Determinism on Different Python Versions**:
   - While `random_state=42` is fixed, bytecode or hashing differences in different minor versions of Python or gplearn could perturb symbolic tree selection in late generations. Tolerances for GP evaluation should be looser (`rtol=0.1`).
3. **Kriging Convergence Warning**:
   - As observed in Section 1.2, Universal Kriging (`degree_fit=2`) raises a `ConvergenceWarning` on scikit-learn's RBF length_scale. Tests should expect or suppress this warning cleanly using `warnings.catch_warnings()`.

---

## 4. Conclusion: Complete Specification of `tests/test_baseline.py`

Below is the complete, self-contained specification for `tests/test_baseline.py` to be created by Worker 1 in Milestone M1.

```python
"""
tests/test_baseline.py

Pre-refactoring golden baseline test suite for SuperRSM.
Verifies numerical outputs and behavior against known golden metrics on sample_data.csv.
"""

from pathlib import Path
import os
import pytest
import numpy as np
import pandas as pd
from scipy.optimize import LinearConstraint

import rsm_backend as rsm


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(scope="module")
def sample_data_path():
    """Locate sample_data.csv relative to repository root."""
    path = Path(__file__).resolve().parent.parent / "sample_data.csv"
    assert path.exists(), f"sample_data.csv not found at {path}"
    return path


@pytest.fixture(scope="module")
def sample_dataset(sample_data_path):
    """Load sample data and extract input and target arrays."""
    df = pd.read_csv(sample_data_path)
    X, y = rsm.build_data(df, ["x1", "x2"], "y")
    return {"df": df, "X": X, "y": y}


# =============================================================================
# 1. Dataset Integrity Tests
# =============================================================================

def test_sample_dataset_dimensions(sample_dataset):
    """Assert sample dataset has 100 rows, 2 input features, and 1 target."""
    X = sample_dataset["X"]
    y = sample_dataset["y"]
    assert X.shape == (100, 2)
    assert y.shape == (100,)
    assert list(sample_dataset["df"].columns) == ["x1", "x2", "y"]


# =============================================================================
# 2. RidgeCV Golden Baseline Tests
# =============================================================================

def test_ridgecv_baseline_metrics_and_coefficients(sample_dataset):
    """
    Verify RidgeCV model metrics, unscaled coefficients, and point evaluation.
    Golden metrics:
      R2 approx 0.9991
      RMSE approx 0.4602
      Intercept approx 29.615
      Linear coeffs: x1 ~= -5.819, x2 ~= -7.943
      Quadratic coeffs: x1^2 ~= 0.983, x1*x2 ~= -0.004, x2^2 ~= 0.994
    """
    X = sample_dataset["X"]
    y = sample_dataset["y"]
    res = rsm.fit_rsm2(X, y, degree_fit=2, test_size=0.20, method="RidgeCV")

    assert res.R_sq == pytest.approx(0.99914587, rel=1e-3)
    assert res.RMSE == pytest.approx(0.46016751, rel=1e-3)
    assert res.MSE == pytest.approx(0.21175413, rel=1e-3)

    assert res.intercept == pytest.approx(29.61519176, rel=1e-2)
    terms = rsm.generate_term_strings(["x1", "x2"], res.model)
    coeff_dict = dict(zip(terms, res.coeffs))

    assert coeff_dict["x1"] == pytest.approx(-5.81921897, rel=1e-2)
    assert coeff_dict["x2"] == pytest.approx(-7.94330688, rel=1e-2)
    assert coeff_dict["x1^2"] == pytest.approx(0.98312801, rel=1e-2)
    assert coeff_dict["x1 x2"] == pytest.approx(-0.00442790, abs=0.05)
    assert coeff_dict["x2^2"] == pytest.approx(0.99387381, rel=1e-2)

    # Point evaluation at known minimum (3.0, 4.0)
    eval_val = res.evaluate_point([3.0, 4.0], return_std=False)
    assert eval_val == pytest.approx(5.08130556, rel=1e-3)


def test_ridgecv_optimization_unconstrained_and_constrained(sample_dataset):
    """
    Verify RidgeCV optimization finds the unconstrained and linearly constrained minima.
    Unconstrained minimum: (x1 ~= 2.969, x2 ~= 4.003), val ~= 5.080
    Constrained minimum (x1 + x2 <= 6.0): (x1 ~= 2.480, x2 ~= 3.520), val ~= 5.546
    """
    X = sample_dataset["X"]
    y = sample_dataset["y"]
    res = rsm.fit_rsm2(X, y, degree_fit=2, test_size=0.20, method="RidgeCV")

    # Unconstrained
    opt_p, opt_v = res.optimize(initial_guess=[0.0, 0.0], maximize=False)
    assert opt_p[0] == pytest.approx(2.96855682, rel=1e-2)
    assert opt_p[1] == pytest.approx(4.00274702, rel=1e-2)
    assert opt_v == pytest.approx(5.08032568, rel=1e-2)

    # Constrained: x1 + x2 <= 6.0
    lc = LinearConstraint([[1.0, 1.0]], [-np.inf], [6.0])
    c_p, c_v = res.optimize(
        initial_guess=[1.0, 1.0],
        bounds=[(0.0, 10.0), (0.0, 10.0)],
        constraints=lc,
        maximize=False,
    )
    assert np.sum(c_p) == pytest.approx(6.0, abs=1e-4)
    assert c_p[0] == pytest.approx(2.48027093, rel=1e-2)
    assert c_p[1] == pytest.approx(3.51972907, rel=1e-2)
    assert c_v == pytest.approx(5.54555911, rel=1e-2)


# =============================================================================
# 3. Gaussian Process Golden Baseline Tests
# =============================================================================

def test_gaussian_process_ordinary_kriging_baseline(sample_dataset):
    """
    Verify Ordinary Kriging (degree_fit=0) metrics, uncertainty estimation, and minimum.
    Golden metrics:
      R2 approx 0.9989
      RMSE approx 0.5168
      Point evaluation at (3.0, 4.0): y ~= 4.914, std ~= 0.619
      Optimization minimum: (x1 ~= 3.026, x2 ~= 4.016), val ~= 4.915
    """
    X = sample_dataset["X"]
    y = sample_dataset["y"]
    res = rsm.fit_rsm2(X, y, degree_fit=0, test_size=0.20, method="Gaussian Process")

    assert res.supports_uncertainty is True
    assert res.R_sq == pytest.approx(0.99892255, rel=1e-3)
    assert res.RMSE == pytest.approx(0.51683596, rel=1e-3)

    y_val, std_val = res.evaluate_point([3.0, 4.0], return_std=True)
    assert y_val == pytest.approx(4.91444321, rel=1e-2)
    assert std_val == pytest.approx(0.61862705, rel=1e-2)

    opt_p, opt_v = res.optimize(initial_guess=[0.0, 0.0], maximize=False)
    assert opt_p[0] == pytest.approx(3.02551088, rel=2e-2)
    assert opt_p[1] == pytest.approx(4.01643430, rel=2e-2)
    assert opt_v == pytest.approx(4.91495471, rel=2e-2)


def test_gaussian_process_universal_kriging_baseline(sample_dataset):
    """
    Verify Universal Kriging (degree_fit=2) executes and returns uncertainty.
    Golden metrics:
      R2 approx 0.4650
      RMSE approx 11.5169
      Point evaluation at (3.0, 4.0): y ~= 18.154, std ~= 9.481
    """
    X = sample_dataset["X"]
    y = sample_dataset["y"]
    res = rsm.fit_rsm2(X, y, degree_fit=2, test_size=0.20, method="Gaussian Process")

    assert res.supports_uncertainty is True
    assert res.R_sq == pytest.approx(0.46498835, rel=5e-2)
    assert res.RMSE == pytest.approx(11.51690698, rel=5e-2)

    y_val, std_val = res.evaluate_point([3.0, 4.0], return_std=True)
    assert y_val == pytest.approx(18.15437702, rel=5e-2)
    assert std_val == pytest.approx(9.48129335, rel=5e-2)


# =============================================================================
# 4. Genetic Programming Baseline Tests
# =============================================================================

def test_genetic_programming_smoke_run(sample_dataset):
    """
    Fast smoke test for Genetic Programming symbolic regressor.
    Verifies that SymbolicRegressor fits, exports expression text, and evaluates.
    Runs with reduced generations/population to execute in < 2 seconds.
    """
    X = sample_dataset["X"]
    y = sample_dataset["y"]

    # Retrieve builder and patch for fast execution
    builder = rsm.MODEL_REGISTRY["Genetic Programming"]["builder"]
    model = builder()
    model.set_params(population_size=100, generations=2)

    X_train, X_test, y_train, y_test = rsm.train_test_split(
        X, y, test_size=0.20, random_state=42
    )
    model.fit(X_train, y_train)

    res = rsm.rsm_result(
        model, X_train, y_train, X_test, y_test, method="Genetic Programming"
    )
    assert res.expression_text is not None
    assert "Mathematical Expression" in res.expression_text
    eval_val = res.evaluate_point([3.0, 4.0], return_std=False)
    assert isinstance(eval_val, float)


@pytest.mark.slow
@pytest.mark.skipif(
    os.environ.get("RUN_SLOW_BASELINE", "0") != "1",
    reason="Full GP baseline takes ~3 minutes; run with RUN_SLOW_BASELINE=1",
)
def test_genetic_programming_full_golden_baseline(sample_dataset):
    """
    Full golden baseline test for Genetic Programming with population=5000, generations=30.
    Golden metrics:
      R2 approx -41.72
      Point evaluation at (3.0, 4.0) approx 3.450
      Optimized min approx 5.560
    """
    X = sample_dataset["X"]
    y = sample_dataset["y"]
    res = rsm.fit_rsm2(X, y, degree_fit=2, test_size=0.20, method="Genetic Programming")

    assert res.expression_text is not None
    assert "add" in res.expression_text
    assert res.R_sq == pytest.approx(-41.72123783, rel=0.1)
    eval_val = res.evaluate_point([3.0, 4.0], return_std=False)
    assert eval_val == pytest.approx(3.45031311, rel=0.1)


# =============================================================================
# 5. Pipeline Helper Tests
# =============================================================================

def test_rsm_from_df_pipeline(sample_dataset):
    """Verify rsm_fromDF convenience pipeline produces identical results to fit_rsm2."""
    df = sample_dataset["df"]
    res = rsm.rsm_fromDF(
        df,
        input_columns=["x1", "x2"],
        output_column="y",
        degree_fit=2,
        test_size=0.20,
        method="RidgeCV",
    )
    assert res.R_sq == pytest.approx(0.99914587, rel=1e-3)
    assert res.RMSE == pytest.approx(0.46016751, rel=1e-3)
```

---

## 5. Verification Method

To verify the test suite independently:

1. **Test Execution Command**:
   ```bash
   pytest -v tests/test_baseline.py
   ```
   - Should execute 6 passed tests in under 3.5 seconds (fast smoke suite, skipping slow 3-minute GP test).
2. **Full Baseline Verification (including slow GP)**:
   ```bash
   RUN_SLOW_BASELINE=1 pytest -v tests/test_baseline.py
   ```
   - All 7 tests pass.
3. **Invalidation Conditions**:
   - RidgeCV $R^2 < 0.998$ or RMSE $> 0.50$ on `sample_data.csv`.
   - RidgeCV unscaled coefficients differ by $> 2\%$ from golden values.
   - Constrained optimization minimum does not satisfy $x_1 + x_2 = 6.0 \pm 10^{-4}$.
   - Ordinary Kriging $R^2 < 0.998$ or point prediction at $(3.0, 4.0)$ differs from $4.914$ by $> 0.1$.
