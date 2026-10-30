"""
tests/test_core.py

Comprehensive headless unit test suite for SuperRSM Core:
- RSMDataset validation, train/test splitting, NaN/Inf rejection, summary stats
- Headless pipeline execution across models (fit_rsm, fit_rsm2, rsm_fromDF, build_data)
- RSMResult metrics, legacy aliases, formula/coeff accessors, point/batch evaluation
- OptimizationEngine unconstrained, bounded, maximization, LinearConstraint, ConstraintSpec
- 2-tuple unpacking and indexing protocol
- Headless isolation verification
"""

from pathlib import Path
import sys
import unittest.mock
import numpy as np
import pandas as pd
import pytest
from scipy.optimize import LinearConstraint

from super_rsm.common.config import ConstraintOperator, ConstraintSpec
from super_rsm.common.exceptions import DataValidationError, RegistryError
from super_rsm.core import (
    RSMDataset, RSMResult, OptimizationEngine, OptimizationResult,
    fit_rsm, fit_rsm2, rsm_fromDF, build_data,
)


@pytest.fixture(scope="module")
def sample_df():
    path = Path(__file__).resolve().parent.parent / "sample_data.csv"
    assert path.exists(), f"sample_data.csv not found at {path}"
    return pd.read_csv(path)


@pytest.fixture(scope="module")
def sample_dataset(sample_df):
    return RSMDataset.from_dataframe(sample_df, ["x1", "x2"], "y", test_size=0.20, random_state=42)


@pytest.fixture(scope="module")
def fitted_ols(sample_dataset):
    return fit_rsm(sample_dataset, method="Polynomial OLS", degree_fit=2)


@pytest.fixture(scope="module")
def fitted_gp(sample_dataset):
    return fit_rsm(sample_dataset, method="Gaussian Process", degree_fit=0, noise_level=0.1)


# -----------------------------------------------------------------------------
# 1. RSMDataset Tests
# -----------------------------------------------------------------------------

def test_dataset_dataframe_and_arrays(sample_df):
    ds = RSMDataset.from_dataframe(sample_df, ["x1", "x2"], "y", test_size=0.20, random_state=42)
    assert ds.X_train.shape == (80, 2) and ds.X_test.shape == (20, 2)
    assert ds.num_features == 2 and ds.feature_names == ["x1", "x2"]
    assert ds.summary_stats()["num_features"] == 2

    ds_arr = RSMDataset.from_arrays(ds.X_train, ds.y_train, ds.X_test, ds.y_test)
    assert ds_arr.num_train == 80 and ds_arr.num_test == 20
    assert ds_arr.feature_names == ["x1", "x2"]


def test_dataset_validation_errors(sample_df):
    with pytest.raises(DataValidationError, match="Missing input columns"):
        RSMDataset.from_dataframe(sample_df, ["x1", "bad"], "y")
    with pytest.raises(DataValidationError, match="Missing output column"):
        RSMDataset.from_dataframe(sample_df, ["x1", "x2"], "bad")
    with pytest.raises(DataValidationError, match="test_size"):
        RSMDataset.from_dataframe(sample_df, ["x1", "x2"], "y", test_size=1.5)
    with pytest.raises(DataValidationError, match="NaN"):
        RSMDataset.from_unsplit_arrays(np.array([[1.0, np.nan], [2.0, 3.0]]), np.array([1.0, 2.0]))
    with pytest.raises(DataValidationError, match="Inf"):
        RSMDataset.from_unsplit_arrays(np.array([[1.0, np.inf], [2.0, 3.0]]), np.array([1.0, 2.0]))
    with pytest.raises(DataValidationError, match="Feature dimension mismatch"):
        RSMDataset.from_arrays(np.zeros((10, 3)), np.zeros(10), np.zeros((2, 2)), np.zeros(2))
    with pytest.raises(DataValidationError, match="Sample count mismatch"):
        RSMDataset.from_arrays(np.zeros((10, 2)), np.zeros(8))


# -----------------------------------------------------------------------------
# 2. Pipeline Execution Tests
# -----------------------------------------------------------------------------

@pytest.mark.parametrize("method, kwargs", [
    ("Polynomial OLS", {"degree_fit": 2}),
    ("RidgeCV", {"degree_fit": 2}),
    ("Gaussian Process", {"degree_fit": 0, "noise_level": 0.1}),
    ("Genetic Programming", {"population_size": 30, "generations": 2}),
])
def test_fit_rsm_methods(sample_dataset, method, kwargs):
    res = fit_rsm(sample_dataset, method=method, **kwargs)
    assert isinstance(res, RSMResult) and res.model.is_fitted
    assert isinstance(res.r2, float) and res.rmse >= 0.0


def test_pipeline_wrappers(sample_df, sample_dataset):
    X, y = build_data(sample_df, ["x1", "x2"], "y")
    assert X.shape == (100, 2) and y.shape == (100,)

    res_split = fit_rsm2(X[:80], y[:80], X[80:], y[80:], method="Polynomial OLS", degree_fit=2)
    assert res_split.r2 > 0.99 and len(res_split.X_train) == 80

    res_unsplit = fit_rsm2(X, y, test_size=0.20, random_state=42, method="RidgeCV", degree_fit=2)
    assert res_unsplit.R_sq > 0.99 and len(res_unsplit.X_test) == 20

    res_df = rsm_fromDF(sample_df, ["x1", "x2"], "y", method="Polynomial OLS", degree_fit=2)
    assert res_df.r2 > 0.99 and res_df.metrics.anova_table is not None

    with pytest.raises(RegistryError):
        fit_rsm(sample_dataset, method="NonexistentMethod")


# -----------------------------------------------------------------------------
# 3. RSMResult Accessors & Evaluation Tests
# -----------------------------------------------------------------------------

def test_result_metrics_and_evaluation(fitted_ols, fitted_gp):
    res = fitted_ols
    assert res.r2 == res.metrics.r2 == res.R_sq == res.R2
    assert res.rmse == res.metrics.rmse == res.RMSE
    assert res.mse == res.metrics.mse == res.MSE and res.mae == res.MAE
    assert "SuperRSM Model Summary" in res.summary()
    assert res.get_formula().startswith("y =") and res.expression_text == res.get_formula()
    assert "Intercept" in res.get_coefficients() and res.coeffs is not None

    val_scalar = res.evaluate_point([3.0, 4.0], return_std=False)
    assert isinstance(val_scalar, float) and val_scalar == pytest.approx(5.0, abs=0.2)

    val_gp, std_gp = fitted_gp.evaluate_point([3.0, 4.0], return_std=True)
    assert val_gp == pytest.approx(5.0, abs=0.5) and 0.0 < std_gp < 2.0

    batch_preds = res.evaluate_batch(np.array([[3.0, 4.0], [0.0, 0.0]]))
    assert batch_preds.shape == (2,) and batch_preds[0] == pytest.approx(5.0, abs=0.2)


# -----------------------------------------------------------------------------
# 4. Optimization Engine & Constraints Tests
# -----------------------------------------------------------------------------

def test_optimization_unconstrained_and_bounds(fitted_ols):
    opt = fitted_ols.optimize(initial_guess=[0.0, 0.0], maximize=False)
    assert opt.success and opt.params[0] == pytest.approx(3.0, abs=0.1)
    assert opt.params[1] == pytest.approx(4.0, abs=0.1) and opt.fun == pytest.approx(5.0, abs=0.2)

    opt_b = fitted_ols.optimize(bounds={"x1": (0.0, 5.0), "x2": (0.0, 5.0)}, maximize=False)
    assert opt_b.success and opt_b.params[0] == pytest.approx(3.0, abs=0.1)

    opt_max = fitted_ols.optimize(bounds={"x1": (0.0, 5.0), "x2": (0.0, 5.0)}, maximize=True)
    assert opt_max.success and opt_max.fun > 25.0


def test_optimization_constraints_and_specs(fitted_ols):
    # Active linear inequality: x1 + x2 <= 5.0 -> constrained minimum at (2.0, 3.0), f = 7.0
    spec = ConstraintSpec(coeffs={"x1": 1.0, "x2": 1.0}, operator=ConstraintOperator.LE, bound=5.0)
    opt = fitted_ols.optimize(
        bounds={"x1": (0.0, 10.0), "x2": (0.0, 10.0)},
        constraints=[spec],
        initial_guess=[1.0, 1.0],
        maximize=False,
    )
    assert opt.success and (opt.params[0] + opt.params[1]) <= 5.0001
    assert opt.params[0] == pytest.approx(2.0, abs=0.2)
    assert opt.params[1] == pytest.approx(3.0, abs=0.2)
    assert opt.fun == pytest.approx(7.0, abs=0.5)

    # Scipy LinearConstraint: x1 + x2 <= 6.0
    lc = LinearConstraint([[1.0, 1.0]], [-np.inf], [6.0])
    opt_scipy = fitted_ols.optimize(
        bounds=[(0.0, 10.0), (0.0, 10.0)],
        constraints=lc,
        initial_guess=[1.0, 1.0],
    )
    assert opt_scipy.success and np.sum(opt_scipy.params) == pytest.approx(6.0, abs=1e-3)


# -----------------------------------------------------------------------------
# 5. 2-Tuple Unpacking & Protocol Tests
# -----------------------------------------------------------------------------

def test_optimization_unpacking_and_indexing(fitted_ols):
    params, opt_val = fitted_ols.optimize(bounds={"x1": (0.0, 5.0), "x2": (0.0, 5.0)})
    assert isinstance(params, np.ndarray) and isinstance(opt_val, (float, np.floating))
    assert params[0] == pytest.approx(3.0, abs=0.1) and opt_val == pytest.approx(5.0, abs=0.2)

    opt = fitted_ols.optimize(bounds={"x1": (0.0, 5.0), "x2": (0.0, 5.0)})
    assert isinstance(opt, OptimizationResult) and len(opt) == 2
    np.testing.assert_array_equal(opt[0], opt.params)
    assert opt[1] == opt.fun and opt.x is opt.params and opt.scipy_result is not None


# -----------------------------------------------------------------------------
# 6. Headless Verification Tests
# -----------------------------------------------------------------------------

def test_headless_import_and_execution(sample_df):
    saved_mods = {
        k: v
        for k, v in list(sys.modules.items())
        if k.startswith(("tkinter", "matplotlib", "seaborn"))
    }
    try:
        for k in saved_mods:
            del sys.modules[k]

        import super_rsm.core
        assert "tkinter" not in sys.modules
        assert "matplotlib" not in sys.modules

        with unittest.mock.patch.dict(sys.modules, {"tkinter": None, "matplotlib": None, "seaborn": None}):
            res = rsm_fromDF(sample_df, ["x1", "x2"], "y", method="Polynomial OLS", degree_fit=2)
            assert res.r2 > 0.99
            p, v = res.optimize(bounds={"x1": (0.0, 5.0), "x2": (0.0, 5.0)})
            assert p[0] == pytest.approx(3.0, abs=0.2) and v == pytest.approx(5.0, abs=0.5)
    finally:
        sys.modules.update(saved_mods)
