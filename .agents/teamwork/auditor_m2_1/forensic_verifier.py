"""
Forensic Integrity Verification Script for SuperRSM Core Milestone M2.
Tests scipy delegation, mathematical correctness of optimization and metrics,
and detects any facade or hardcoded logic.
"""

import os
import sys
sys.path.insert(0, os.path.abspath("."))

import unittest.mock
import numpy as np
import scipy.optimize
from super_rsm.core.dataset import RSMDataset
from super_rsm.core.result import RSMResult
from super_rsm.core.optimization import OptimizationEngine, OptimizationResult
from super_rsm.core.pipeline import fit_rsm
from super_rsm.common.config import ConstraintSpec, ConstraintOperator
from super_rsm.models.polynomial_ols import PolynomialOLSModel


def test_scipy_delegation():
    print("=== 1. SCIPY MINIMIZE DELEGATION VERIFICATION ===")
    called_args = []
    orig_minimize = scipy.optimize.minimize

    def spy_minimize(*args, **kwargs):
        called_args.append((args, kwargs))
        return orig_minimize(*args, **kwargs)

    with unittest.mock.patch("super_rsm.core.optimization.minimize", side_effect=spy_minimize):
        # 1D quadratic: y = (x - 7.5)^2 + 4.2
        X = np.linspace(0, 15, 60).reshape(-1, 1)
        y = (X.ravel() - 7.5) ** 2 + 4.2
        ds = RSMDataset.from_unsplit_arrays(X, y, test_size=0.2, random_state=42, feature_names=["x1"])
        model = PolynomialOLSModel(degree_fit=2)
        model.fit(ds.X_train, ds.y_train, ds.feature_names)

        res = RSMResult(model=model, dataset=ds)
        opt = res.optimize(initial_guess=[1.0], bounds={"x1": (0.0, 15.0)}, maximize=False)

        assert len(called_args) >= 1, "scipy.optimize.minimize was NEVER called!"
        print(f"scipy.optimize.minimize call count: {len(called_args)}")
        print(f"Method used: {called_args[0][1].get('method')}")
        print(f"Initial guess x0: {called_args[0][0][1]}")
        print(f"Discovered optimum: params={opt.params[0]:.4f}, fun={opt.fun:.4f}")
        assert abs(opt.params[0] - 7.5) < 1e-2, f"Expected param ~7.5, got {opt.params[0]}"
        assert abs(opt.fun - 4.2) < 1e-2, f"Expected fun ~4.2, got {opt.fun}"

    print("Result: GENUINE SCIPY DELEGATION CONFIRMED.\n")


def test_dynamic_metric_computation():
    print("=== 2. DYNAMIC METRIC INTEGRITY CHECK ===")
    # Generate arbitrary synthetic data with varying noise and check R2/RMSE calculations against raw numpy
    rng = np.random.default_rng(12345)
    X = rng.uniform(-2, 2, size=(50, 2))
    # True function: y = 2*x1 + 3*x2 + noise
    noise = rng.normal(0, 0.5, size=50)
    y = 2.0 * X[:, 0] + 3.0 * X[:, 1] + noise

    ds = RSMDataset.from_unsplit_arrays(X, y, test_size=0.3, random_state=99, feature_names=["a", "b"])

    # Path A: Via fit_rsm pipeline
    res_pipe = fit_rsm(ds, method="Polynomial OLS", degree_fit=1)
    y_test_pred = res_pipe.model.predict(ds.X_test)
    y_test = ds.y_test
    rss = float(np.sum((y_test - y_test_pred) ** 2))
    tss = float(np.sum((y_test - np.mean(y_test)) ** 2))
    expected_r2 = float(1.0 - (rss / tss))
    expected_rmse = float(np.sqrt(np.mean((y_test - y_test_pred) ** 2)))
    expected_mse = float(np.mean((y_test - y_test_pred) ** 2))

    print(f"[Pipeline] Computed R2: {res_pipe.r2:.6f} vs Expected: {expected_r2:.6f}")
    print(f"[Pipeline] Computed RMSE: {res_pipe.rmse:.6f} vs Expected: {expected_rmse:.6f}")
    print(f"[Pipeline] Computed MSE: {res_pipe.mse:.6f} vs Expected: {expected_mse:.6f}")

    assert abs(res_pipe.r2 - expected_r2) < 1e-9, "Pipeline R2 does not match independent calculation!"
    assert abs(res_pipe.rmse - expected_rmse) < 1e-9, "Pipeline RMSE does not match independent calculation!"
    assert abs(res_pipe.mse - expected_mse) < 1e-9, "Pipeline MSE does not match independent calculation!"

    # Path B: Via RSMResult._compute_test_metrics() directly
    class CustomPredictModel:
        supports_uncertainty = False
        def predict(self, X_eval, **kwargs):
            return 1.8 * X_eval[:, 0] + 3.2 * X_eval[:, 1]

    raw_model = CustomPredictModel()
    res_custom = RSMResult(model=raw_model, dataset=ds)
    y_custom_pred = raw_model.predict(ds.X_test)
    rss_custom = float(np.sum((y_test - y_custom_pred) ** 2))
    exp_r2_custom = float(1.0 - (rss_custom / tss))
    exp_rmse_custom = float(np.sqrt(np.mean((y_test - y_custom_pred) ** 2)))

    print(f"[RSMResult direct] Computed R2: {res_custom.r2:.6f} vs Expected: {exp_r2_custom:.6f}")
    print(f"[RSMResult direct] Computed RMSE: {res_custom.rmse:.6f} vs Expected: {exp_rmse_custom:.6f}")
    assert abs(res_custom.r2 - exp_r2_custom) < 1e-9
    assert abs(res_custom.rmse - exp_rmse_custom) < 1e-9

    print("Result: DYNAMIC METRICS EMPIRICALLY CONFIRMED (NO HARDCODING).\n")


def test_constrained_optimization_and_maximization():
    print("=== 3. CONSTRAINED OPTIMIZATION & MAXIMIZATION CHECK ===")
    class CustomParaboloid:
        feature_names = ["x1", "x2"]
        supports_uncertainty = False

        def predict(self, X):
            X = np.atleast_2d(X)
            return -(X[:, 0] - 2.0) ** 2 - (X[:, 1] - 3.0) ** 2 + 10.0

        def evaluate_point(self, p, return_std=False):
            val = self.predict(np.asarray(p).reshape(1, -1))[0]
            return (val, None) if return_std else val

    model = CustomParaboloid()

    # Test Unconstrained Maximization
    opt_max = OptimizationEngine.optimize(
        model=model,
        initial_guess=[0.0, 0.0],
        maximize=True,
        feature_names=["x1", "x2"],
    )
    print(f"Maximization optimum: params={opt_max.params}, fun={opt_max.fun}")
    assert abs(opt_max.params[0] - 2.0) < 1e-3
    assert abs(opt_max.params[1] - 3.0) < 1e-3
    assert abs(opt_max.fun - 10.0) < 1e-3

    # Test Active Linear Constraint: x1 + x2 <= 4.0
    spec = ConstraintSpec(coeffs={"x1": 1.0, "x2": 1.0}, operator=ConstraintOperator.LE, bound=4.0)
    opt_constr = OptimizationEngine.optimize(
        model=model,
        initial_guess=[0.5, 0.5],
        constraints=[spec],
        maximize=True,
        feature_names=["x1", "x2"],
    )
    print(f"Constrained maximization optimum: params={opt_constr.params}, fun={opt_constr.fun}")
    assert abs(opt_constr.params[0] - 1.5) < 1e-2
    assert abs(opt_constr.params[1] - 2.5) < 1e-2
    assert abs(opt_constr.fun - 9.5) < 1e-2
    print("Result: CONSTRAINED OPTIMIZATION & MAXIMIZATION MATHEMATICALLY RIGOROUS.\n")


def test_dataset_array_validation():
    print("=== 4. DATASET VALIDATION INTEGRITY CHECK ===")
    from super_rsm.common.exceptions import DataValidationError

    # Check 1D X rejection
    try:
        RSMDataset(X_train=np.array([1, 2, 3]), y_train=np.array([1, 2, 3]))
        assert False, "Failed to reject 1D X_train"
    except DataValidationError:
        pass

    # Check sample mismatch rejection
    try:
        RSMDataset(X_train=np.zeros((5, 2)), y_train=np.zeros(4))
        assert False, "Failed to reject sample length mismatch"
    except DataValidationError:
        pass

    # Check duplicate feature name rejection
    try:
        RSMDataset(X_train=np.zeros((5, 2)), y_train=np.zeros(5), feature_names=["col", "col"])
        assert False, "Failed to reject duplicate feature names"
    except DataValidationError:
        pass

    # Check NaN rejection
    try:
        RSMDataset(X_train=np.array([[1.0, np.nan], [2.0, 3.0]]), y_train=np.array([1.0, 2.0]))
        assert False, "Failed to reject NaN values"
    except DataValidationError:
        pass

    # Check Inf rejection
    try:
        RSMDataset(X_train=np.array([[1.0, np.inf], [2.0, 3.0]]), y_train=np.array([1.0, 2.0]))
        assert False, "Failed to reject Inf values"
    except DataValidationError:
        pass

    print("Result: DATASET VALIDATION THOROUGH AND ROBUST.\n")


def test_dual_unpacking_and_indexing():
    print("=== 5. OPTIMIZATION RESULT UNPACKING & INDEXING ===")
    opt = OptimizationResult(
        params=np.array([1.23, 4.56]),
        fun=7.89,
        success=True,
        message="Optimization terminated successfully.",
        nit=10,
    )
    p, f = opt
    assert np.allclose(p, [1.23, 4.56])
    assert abs(f - 7.89) < 1e-9
    assert np.allclose(opt[0], [1.23, 4.56])
    assert abs(opt[1] - 7.89) < 1e-9
    assert len(opt) == 2
    d = opt.to_dict(["alpha", "beta"])
    assert d == {"alpha": 1.23, "beta": 4.56}
    print("Result: UNPACKING AND INDEXING COMPLIANT.\n")


if __name__ == "__main__":
    test_scipy_delegation()
    test_dynamic_metric_computation()
    test_constrained_optimization_and_maximization()
    test_dataset_array_validation()
    test_dual_unpacking_and_indexing()
    print("ALL FORENSIC CHECKS PASSED EMPIRICALLY!")
