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

    res = rsm.fit_rsm2(
        X,
        y,
        test_size=0.20,
        method="Genetic Programming",
        population_size=100,
        generations=2,
    )
    assert res.expression_text is not None
    assert "y =" in res.expression_text
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
