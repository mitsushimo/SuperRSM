"""
tests/test_empirical_stress.py

Empirical stress testing harness for Milestone M1 models.
Covers:
1. Collinear and rank-deficient datasets (identical columns, linear combinations, coded units)
2. Boundary conditions (N < P, N = P, N = P + 1, zero variance features, zero variance targets, negative targets)
3. Dimensionality edge cases (1D, 5D, 10D inputs)
4. Model polymorphism, uncertainty, and surface grid evaluation
"""

import numpy as np
import pytest

from super_rsm.common.exceptions import GridConfigurationError
from super_rsm.models import (
    GaussianProcessRSMModel,
    PolynomialOLSModel,
    RidgeCVRSMModel,
    SurfaceGridConfig,
    SymbolicRegressorRSMModel,
)


# =============================================================================
# 1. Collinear and Rank-Deficient Datasets
# =============================================================================

def test_ols_identical_columns_pseudo_inverse_stability():
    """Verify PolynomialOLSModel handles perfectly identical columns without singular matrix crash."""
    np.random.seed(42)
    n = 40
    x1 = np.random.uniform(1.0, 10.0, size=n)
    # x2 and x3 are exact copies of x1
    X = np.column_stack([x1, x1, x1])
    y = 5.0 + 2.0 * x1 - 0.5 * (x1**2) + np.random.normal(0, 0.05, size=n)

    ols = PolynomialOLSModel(degree_fit=2, coded_units=False)
    ols.fit(X, y, feature_names=["x1", "x2", "x3"])

    assert ols.is_fitted
    pred = ols.predict(X)
    assert pred.shape == (n,)
    assert not np.isnan(pred).any()
    assert not np.isinf(pred).any()

    metrics = ols.get_metrics()
    assert metrics.r2 > 0.90
    assert not np.isnan(metrics.rmse)

    # Verify coefficients and standard errors are finite
    coeffs = ols.get_coefficients()
    assert len(coeffs) > 0
    for term, val in coeffs.items():
        assert not np.isnan(val), f"Coefficient for {term} is NaN"

    for term, se in metrics.term_std_errors.items():
        assert not np.isnan(se), f"Std error for {term} is NaN"

    for term, p in metrics.term_p_values.items():
        assert not np.isnan(p), f"p-value for {term} is NaN"


def test_ols_linear_combination_columns():
    """Verify PolynomialOLSModel handles linear combinations: x3 = 2*x1 - 3*x2."""
    np.random.seed(123)
    n = 50
    x1 = np.random.uniform(-5.0, 5.0, size=n)
    x2 = np.random.uniform(0.0, 10.0, size=n)
    x3 = 2.0 * x1 - 3.0 * x2
    X = np.column_stack([x1, x2, x3])
    y = 10.0 + 1.5 * x1 - 2.0 * x2 + 0.1 * (x1**2) + np.random.normal(0, 0.1, size=n)

    ols = PolynomialOLSModel(degree_fit=2, coded_units=False)
    ols.fit(X, y, feature_names=["x1", "x2", "x3"])

    assert ols.is_fitted
    pred = ols.predict(X)
    assert not np.isnan(pred).any()
    assert ols.get_metrics().r2 > 0.95

    anova = ols.get_metrics().anova_table
    assert anova is not None
    assert not np.isnan(anova.loc[0, "SS"])


def test_ols_collinear_with_coded_units():
    """Verify coded_units=True scales properly even with collinear columns."""
    np.random.seed(99)
    n = 35
    x1 = np.random.uniform(10.0, 50.0, size=n)
    x2 = x1 * 4.0  # strictly collinear
    X = np.column_stack([x1, x2])
    y = 100.0 - 1.2 * x1 + 0.05 * (x1**2)

    ols = PolynomialOLSModel(degree_fit=2, coded_units=True)
    ols.fit(X, y, feature_names=["x1", "x2"])

    assert ols.is_fitted
    pred = ols.predict(X)
    assert not np.isnan(pred).any()
    assert ols.get_metrics().r2 > 0.99


def test_ridgecv_and_gp_on_collinear_data():
    """Verify RidgeCV and GP handle collinear data gracefully."""
    np.random.seed(42)
    n = 30
    x1 = np.random.uniform(0.0, 10.0, size=n)
    X = np.column_stack([x1, 2.0 * x1])
    y = 3.0 + 1.5 * x1 + np.random.normal(0, 0.1, size=n)

    # RidgeCV with L2 penalty
    ridge = RidgeCVRSMModel(degree_fit=2)
    ridge.fit(X, y)
    assert ridge.is_fitted
    pred_r = ridge.predict(X)
    assert not np.isnan(pred_r).any()

    # GP
    gp = GaussianProcessRSMModel(degree_fit=0, noise_level=0.1)
    gp.fit(X, y)
    assert gp.is_fitted
    pred_g, std_g = gp.predict_with_uncertainty(X)
    assert not np.isnan(pred_g).any()
    assert not np.isnan(std_g).any()


# =============================================================================
# 2. Boundary Conditions
# =============================================================================

def test_ols_underdetermined_sample_size_strict_rejection():
    """Verify strict rejection when N < P and N == P."""
    # Degree 2 with 2 features gives 1 + 2 + 3 = 6 terms
    X = np.ones((5, 2))
    y = np.ones(5)
    with pytest.raises(ValueError, match="Sample size .* must exceed number of polynomial terms"):
        PolynomialOLSModel(degree_fit=2).fit(X, y)

    # Exactly N == P (6 samples, 6 terms)
    X6 = np.ones((6, 2))
    y6 = np.ones(6)
    with pytest.raises(ValueError, match="Sample size .* must exceed number of polynomial terms"):
        PolynomialOLSModel(degree_fit=2).fit(X6, y6)


def test_ols_minimal_overdetermined_sample_size_n_eq_p_plus_1():
    """Verify N = P + 1 (df_resid = 1) fits successfully and calculates valid statistics."""
    # 2 features, degree 2 -> P = 6 terms.
    # Set N = 7 (P + 1)
    np.random.seed(77)
    n = 7
    X = np.random.uniform(1.0, 5.0, size=(n, 2))
    y = 2.0 + 3.0 * X[:, 0] - 1.5 * X[:, 1] + 0.5 * (X[:, 0]**2)

    ols = PolynomialOLSModel(degree_fit=2)
    ols.fit(X, y, feature_names=["x1", "x2"])

    assert ols.is_fitted
    metrics = ols.get_metrics()
    assert metrics.anova_table.loc[1, "df"] == 1  # df_resid == 1
    assert not np.isnan(metrics.rmse)
    assert not np.isnan(metrics.r2)

    # Predictions must be valid
    pred = ols.predict(X)
    assert len(pred) == 7
    assert not np.isnan(pred).any()


def test_zero_variance_feature():
    """Verify handling when an input feature has zero variance (constant column)."""
    np.random.seed(88)
    n = 25
    x1 = np.full(n, 7.5)  # constant zero-variance feature
    x2 = np.random.uniform(1.0, 10.0, size=n)
    X = np.column_stack([x1, x2])
    y = 4.0 + 2.0 * x2 + np.random.normal(0, 0.1, size=n)

    # 1. PolynomialOLS without coded units
    ols_raw = PolynomialOLSModel(degree_fit=2, coded_units=False)
    ols_raw.fit(X, y, feature_names=["x1", "x2"])
    pred_raw = ols_raw.predict(X[:5])
    assert not np.isnan(pred_raw).any()

    # 2. PolynomialOLS with coded units (tests span zero division guard)
    ols_coded = PolynomialOLSModel(degree_fit=2, coded_units=True)
    ols_coded.fit(X, y, feature_names=["x1", "x2"])
    pred_coded = ols_coded.predict(X[:5])
    assert not np.isnan(pred_coded).any()
    assert ols_coded.get_metrics().r2 > 0.90

    # 3. RidgeCV (tests StandardScaler zero variance guard)
    ridge = RidgeCVRSMModel(degree_fit=2)
    ridge.fit(X, y, feature_names=["x1", "x2"])
    pred_ridge = ridge.predict(X[:5])
    assert not np.isnan(pred_ridge).any()
    assert not np.isnan(ridge.unscaled_intercept)

    # 4. GaussianProcess
    gp = GaussianProcessRSMModel(degree_fit=0, noise_level=0.1)
    gp.fit(X, y, feature_names=["x1", "x2"])
    pred_gp = gp.predict(X[:5])
    assert not np.isnan(pred_gp).any()


def test_zero_variance_target():
    """Verify behavior when response y is constant (zero variance target)."""
    n = 20
    X = np.random.uniform(0.0, 5.0, size=(n, 2))
    y = np.full(n, 42.0)

    # OLS
    ols = PolynomialOLSModel(degree_fit=2)
    ols.fit(X, y)
    assert ols.is_fitted
    pred = ols.predict(X[:4])
    assert np.allclose(pred, 42.0, atol=1e-5)
    # In zero-variance target, tss = 0, R2 should be defined safely as 0.0
    assert ols.get_metrics().r2 == 0.0
    assert not np.isnan(ols.get_metrics().rmse)

    # RidgeCV
    ridge = RidgeCVRSMModel(degree_fit=1)
    ridge.fit(X, y)
    assert np.allclose(ridge.predict(X[:4]), 42.0, atol=1e-3)


def test_negative_target_and_features():
    """Verify models support strictly negative target values and negative features."""
    np.random.seed(101)
    n = 30
    X = np.random.uniform(-10.0, -2.0, size=(n, 2))
    # Target strictly negative
    y = -100.0 + 3.0 * X[:, 0] - 2.0 * X[:, 1] + np.random.normal(0, 0.2, size=n)
    assert np.all(y < 0.0)

    # OLS
    ols = PolynomialOLSModel(degree_fit=2, coded_units=True)
    ols.fit(X, y)
    assert np.all(ols.predict(X[:5]) < 0.0)
    assert ols.get_metrics().r2 > 0.95

    # RidgeCV
    ridge = RidgeCVRSMModel(degree_fit=2)
    ridge.fit(X, y)
    assert np.all(ridge.predict(X[:5]) < 0.0)

    # Gaussian Process
    gp = GaussianProcessRSMModel(degree_fit=0, noise_level=0.1)
    gp.fit(X, y)
    assert np.all(gp.predict(X[:5]) < 0.0)

    # Symbolic Regressor
    sym = SymbolicRegressorRSMModel(population_size=100, generations=2, random_state=42)
    sym.fit(X, y)
    pred_sym = sym.predict(X[:5])
    assert not np.isnan(pred_sym).any()


# =============================================================================
# 3. Dimensionality Edge Cases (1D, 5D, 10D)
# =============================================================================

def test_1d_input_edge_case():
    """Verify models support 1-dimensional input feature space."""
    np.random.seed(111)
    n = 25
    x = np.random.uniform(0.0, 10.0, size=n)
    y = 5.0 - 2.0 * x + 0.3 * (x**2) + np.random.normal(0, 0.1, size=n)

    # 1. PolynomialOLS with 1D input (passed as 1D array shape (N,))
    ols = PolynomialOLSModel(degree_fit=2)
    ols.fit(x, y, feature_names=["x1"])
    assert ols.is_fitted
    assert len(ols.term_names) == 3  # Intercept, x1, x1^2

    # Predict with 1D array and evaluate_point
    pred = ols.predict(x[:5])
    assert pred.shape == (5,)
    val, unc = ols.evaluate_point([4.0])
    assert isinstance(val, float)
    assert unc is None

    # 2. RidgeCV with 1D input
    ridge = RidgeCVRSMModel(degree_fit=2)
    ridge.fit(x, y, feature_names=["x1"])
    assert ridge.is_fitted
    pred_r = ridge.predict(x[:5])
    assert pred_r.shape == (5,)

    # 3. GaussianProcess with 1D input
    gp = GaussianProcessRSMModel(degree_fit=0, noise_level=0.1)
    gp.fit(x, y, feature_names=["x1"])
    assert gp.is_fitted
    val_gp, std_gp = gp.evaluate_point([4.0], return_std=True)
    assert isinstance(val_gp, float)
    assert isinstance(std_gp, float)


def test_5d_input_edge_case():
    """Verify models support 5-dimensional feature space (degree 2 -> 21 terms)."""
    np.random.seed(555)
    n = 60
    X = np.random.uniform(0.0, 5.0, size=(n, 5))
    names = [f"feat_{i+1}" for i in range(5)]
    # True quadratic response
    y = (
        10.0
        + 1.0 * X[:, 0]
        - 2.0 * X[:, 1]
        + 0.5 * (X[:, 2]**2)
        - 1.5 * (X[:, 3] * X[:, 4])
        + np.random.normal(0, 0.1, size=n)
    )

    ols = PolynomialOLSModel(degree_fit=2, coded_units=True)
    ols.fit(X, y, feature_names=names)
    assert len(ols.term_names) == 21  # 1 + 5 + 5 + 10
    assert ols.get_metrics().r2 > 0.95

    # Feature importance
    importance = ols.get_feature_importance()
    assert len(importance) == 20  # excludes Intercept
    assert sum(importance.values()) == pytest.approx(1.0, abs=1e-5)

    # Multi-contour surface grid on 5D space with 3 fixed dimensions
    cfg = SurfaceGridConfig(
        x_idx=0,
        x_values=np.linspace(1, 4, 8),
        y_idx=1,
        y_values=np.linspace(1, 4, 8),
        num_total_features=5,
        fixed_values=[(2, 2.5), (3, 2.5), (4, 2.5)],
    )
    res = ols.compute_surface_grid(cfg)
    assert res.X_mesh.shape == (8, 8)
    assert res.Z_array[0][0].shape == (8, 8)


def test_10d_input_edge_case():
    """Verify models support 10-dimensional feature space (degree 2 -> 66 terms)."""
    np.random.seed(1010)
    n = 120  # N > 66
    X = np.random.uniform(0.0, 3.0, size=(n, 10))
    y = 5.0 + np.sum(X, axis=1) + 0.2 * np.sum(X**2, axis=1) + np.random.normal(0, 0.1, size=n)

    # 1. PolynomialOLS
    ols = PolynomialOLSModel(degree_fit=2)
    ols.fit(X, y)
    assert ols.is_fitted
    assert len(ols.term_names) == 66  # 1 + 10 + 10 + 45
    assert ols.get_metrics().r2 > 0.90
    assert ols.predict(X[:10]).shape == (10,)

    # 2. RidgeCV
    ridge = RidgeCVRSMModel(degree_fit=2)
    ridge.fit(X, y)
    assert ridge.is_fitted
    assert ridge.predict(X[:10]).shape == (10,)

    # 3. GaussianProcess
    gp = GaussianProcessRSMModel(degree_fit=0, noise_level=0.1)
    gp.fit(X, y)
    assert gp.is_fitted
    assert gp.predict(X[:10]).shape == (10,)


# =============================================================================
# 4. Surface Grid Dimension Completeness & Collision Validation
# =============================================================================

def test_surface_grid_enforces_all_dimensions_mapped():
    """Verify SurfaceGridConfig detects unassigned dimensions in higher-D models."""
    # 5D model where only dims 0, 1 are specified, dims 2, 3, 4 missing
    cfg_incomplete = SurfaceGridConfig(
        x_idx=0,
        x_values=np.linspace(0, 1, 5),
        y_idx=1,
        y_values=np.linspace(0, 1, 5),
        num_total_features=5,
        fixed_values=[],  # Missing dimensions 2, 3, 4
    )
    with pytest.raises(GridConfigurationError, match="Dimensions \\[2, 3, 4\\] are unassigned"):
        cfg_incomplete.validate()


# =============================================================================
# 5. Additional Adversarial Stress Tests
# =============================================================================

def test_ols_perfect_fit_zero_residual_stability():
    """Verify stability when model fits data perfectly (RSS=0, s_sq=0)."""
    np.random.seed(42)
    n = 20
    x1 = np.linspace(-2, 2, n)
    # Exact polynomial without noise
    y = 3.0 + 1.5 * x1 - 0.5 * (x1**2)
    X = x1.reshape(-1, 1)

    ols = PolynomialOLSModel(degree_fit=2)
    ols.fit(X, y, feature_names=["x1"])

    assert ols.is_fitted
    m = ols.get_metrics()
    assert m.r2 == pytest.approx(1.0, abs=1e-7)
    assert m.mse == pytest.approx(0.0, abs=1e-12)
    assert not np.isnan(m.aic)
    assert not np.isnan(m.bic)

    # All standard errors should be zero or near zero without crashing
    for t, se in m.term_std_errors.items():
        assert not np.isnan(se)


def test_ols_not_fitted_guard():
    """Verify ModelNotFittedError is raised when methods are called before fit."""
    from super_rsm.common.exceptions import ModelNotFittedError
    ols = PolynomialOLSModel()
    with pytest.raises(ModelNotFittedError):
        ols.predict(np.array([[1.0, 2.0]]))
    with pytest.raises(ModelNotFittedError):
        ols.get_coefficients()
    with pytest.raises(ModelNotFittedError):
        ols.get_formula()
    with pytest.raises(ModelNotFittedError):
        ols.get_feature_importance()


def test_large_magnitude_inputs_with_coded_units():
    """Verify coded_units handles large numerical magnitudes (e.g. 1e6 to 1e7) stably."""
    np.random.seed(1234)
    n = 30
    x1 = np.random.uniform(1e6, 2e6, size=n)
    x2 = np.random.uniform(10.0, 50.0, size=n)
    X = np.column_stack([x1, x2])
    y = 100.0 + 1e-4 * x1 - 2.0 * x2 + np.random.normal(0, 0.1, size=n)

    ols = PolynomialOLSModel(degree_fit=2, coded_units=True)
    ols.fit(X, y)
    assert ols.is_fitted
    pred = ols.predict(X[:5])
    assert not np.isnan(pred).any()
    assert ols.get_metrics().r2 > 0.95


def test_all_features_zero_variance():
    """Verify handling when ALL input features are constant."""
    n = 20
    X = np.full((n, 2), 5.0)
    y = np.full(n, 12.0)

    # OLS should fit without crashing (intercept only model)
    ols = PolynomialOLSModel(degree_fit=1, coded_units=True)
    ols.fit(X, y)
    pred = ols.predict(X[:5])
    assert np.allclose(pred, 12.0, atol=1e-5)

    # RidgeCV with all constant features
    ridge = RidgeCVRSMModel(degree_fit=1)
    ridge.fit(X, y)
    pred_r = ridge.predict(X[:5])
    assert np.allclose(pred_r, 12.0, atol=1e-4)
