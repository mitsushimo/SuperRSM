"""
tests/test_models.py

Comprehensive test suite for SuperRSM regression models, registry,
uncertainty estimation, ANOVA, collinearity robustness, and contracts.
"""

from pathlib import Path
import pytest
import numpy as np
import pandas as pd

from super_rsm.common.config import ModelMetadata
from super_rsm.common.exceptions import (
    GridConfigurationError,
    ModelNotFittedError,
    RegistryError,
    UncertaintyNotSupportedError,
)
from super_rsm.models import (
    GaussianProcessRSMModel,
    ModelRegistry,
    PolynomialOLSModel,
    RidgeCVRSMModel,
    SurfaceGridConfig,
    SymbolicRegressorRSMModel,
)
from super_rsm.models.symbolic import piecewise_function


@pytest.fixture(scope="module")
def sample_data():
    """Load sample data for model tests."""
    path = Path(__file__).resolve().parent.parent / "sample_data.csv"
    df = pd.read_csv(path)
    return {"df": df, "X": df[["x1", "x2"]].to_numpy(), "y": df["y"].to_numpy()}


# =============================================================================
# 1. Registry & Introspection Tests
# =============================================================================

def test_registry_contains_all_models_and_introspection():
    names = ModelRegistry.list_names()
    for required in ["Gaussian Process", "RidgeCV", "Genetic Programming", "Polynomial OLS"]:
        assert required in names
    for name in names:
        meta = ModelRegistry.get_metadata(name)
        assert isinstance(meta, ModelMetadata)
        assert meta.name == name
        assert len(meta.hyperparameters) > 0
    with pytest.raises(RegistryError):
        ModelRegistry.get("NonExistentModel")


# =============================================================================
# 2. Gaussian Process Tests
# =============================================================================

def test_gaussian_process_ordinary_kriging_and_uncertainty(sample_data):
    gp = GaussianProcessRSMModel(degree_fit=0, noise_level=0.1, random_state=42)
    with pytest.raises(ModelNotFittedError):
        gp.predict(sample_data["X"][:5])

    gp.fit(sample_data["X"], sample_data["y"], feature_names=["x1", "x2"])
    assert gp.is_fitted
    assert gp.get_metrics().r2 > 0.95

    mean, std = gp.evaluate_point([3.0, 4.0], return_std=True)
    assert mean == pytest.approx(5.0, abs=0.5)
    assert 0.0 < std < 2.0

    y_pred, sigma = gp.predict_with_uncertainty(sample_data["X"][:10])
    assert y_pred.shape == (10,)
    assert sigma.shape == (10,)
    assert np.all(sigma >= 0.0)


# =============================================================================
# 3. RidgeCV Tests
# =============================================================================

def test_ridgecv_unscaled_coefficients_and_fallback(sample_data):
    ridge = RidgeCVRSMModel(degree_fit=2)
    ridge.fit(sample_data["X"], sample_data["y"], feature_names=["x1", "x2"])
    assert ridge.get_metrics().r2 > 0.99

    coeffs = ridge.get_coefficients()
    assert coeffs["Intercept"] == pytest.approx(30.0, abs=2.0)
    assert coeffs["x1"] == pytest.approx(-6.0, abs=1.0)
    assert coeffs["x2"] == pytest.approx(-8.0, abs=1.0)
    assert coeffs["x1^2"] == pytest.approx(1.0, abs=0.2)
    assert coeffs["x1 x2"] == pytest.approx(0.0, abs=0.1)
    assert coeffs["x2^2"] == pytest.approx(1.0, abs=0.2)

    formula = ridge.get_formula()
    assert formula.startswith("y =")
    importance = ridge.get_feature_importance()
    assert sum(importance.values()) == pytest.approx(1.0, abs=1e-5)

    # Low-sample fallback to Generalized LOOCV
    small_ridge = RidgeCVRSMModel(degree_fit=1, cv=5)
    small_ridge.fit(sample_data["X"][:4], sample_data["y"][:4])
    assert small_ridge.is_fitted


# =============================================================================
# 4. Symbolic Regressor Tests
# =============================================================================

def test_symbolic_regressor_fast_and_primitive(sample_data):
    cond = np.array([1.0, -1.0, 2.0])
    pw = piecewise_function(cond, np.array([10, 10, 10]), np.array([20, 20, 20]))
    np.testing.assert_array_equal(pw, [10, 20, 10])

    sym = SymbolicRegressorRSMModel(population_size=80, generations=2, random_state=42)
    sym.fit(sample_data["X"][:25], sample_data["y"][:25], feature_names=["x1", "x2"])
    assert sym.is_fitted
    assert sym.predict(sample_data["X"][:5]).shape == (5,)
    formula = sym.get_formula()
    assert formula is not None and formula.startswith("y =")
    assert "X0" not in formula and "X1" not in formula


# =============================================================================
# 5. Polynomial OLS & ANOVA Tests
# =============================================================================

def test_polynomial_ols_anova_and_p_values(sample_data):
    ols = PolynomialOLSModel(degree_fit=2, coded_units=False)
    ols.fit(sample_data["X"], sample_data["y"], feature_names=["x1", "x2"])
    m = ols.get_metrics()

    assert m.r2 > 0.99
    assert m.adj_r2 > 0.99
    assert m.anova_table is not None

    ss_model = m.anova_table.loc[0, "SS"]
    ss_resid = m.anova_table.loc[1, "SS"]
    ss_total = m.anova_table.loc[2, "SS"]
    assert (ss_model + ss_resid) == pytest.approx(ss_total, rel=1e-4)

    p_vals = m.term_p_values
    assert p_vals["Intercept"] < 0.01
    assert p_vals["x1"] < 0.01
    assert p_vals["x2"] < 0.01
    assert p_vals["x1^2"] < 0.01
    assert p_vals["x2^2"] < 0.01
    assert p_vals["x1 x2"] > 0.05  # Interaction term is statistically insignificant

    coeffs = ols.get_coefficients()
    assert coeffs["Intercept"] == pytest.approx(29.83, abs=0.5)
    assert coeffs["x1"] == pytest.approx(-5.91, abs=0.3)
    assert coeffs["x2"] == pytest.approx(-7.99, abs=0.3)


def test_polynomial_ols_collinear_and_coded_units(sample_data):
    # Collinear data: x2 = 2 * x1
    x1 = sample_data["X"][:, 0:1]
    X_collinear = np.hstack([x1, 2.0 * x1])
    ols_collinear = PolynomialOLSModel(degree_fit=2)
    ols_collinear.fit(X_collinear, sample_data["y"])
    pred = ols_collinear.predict(X_collinear[:5])
    assert pred.shape == (5,)
    assert not np.isnan(pred).any()

    # Coded units
    ols_coded = PolynomialOLSModel(degree_fit=2, coded_units=True)
    ols_coded.fit(sample_data["X"], sample_data["y"])
    assert ols_coded.get_metrics().r2 > 0.99

    # Underdetermined sample size error
    with pytest.raises(ValueError, match="Sample size .* must exceed"):
        PolynomialOLSModel(degree_fit=2).fit(sample_data["X"][:5], sample_data["y"][:5])


# =============================================================================
# 6. Polymorphic Model & Surface Grid Contracts
# =============================================================================

def test_polymorphic_evaluate_and_surface_grid(sample_data):
    models = [
        GaussianProcessRSMModel(degree_fit=0, noise_level=0.1),
        RidgeCVRSMModel(degree_fit=2),
        PolynomialOLSModel(degree_fit=2),
    ]
    for model in models:
        model.fit(sample_data["X"], sample_data["y"], feature_names=["x1", "x2"])
        val, unc = model.evaluate_point([3.0, 4.0])
        assert isinstance(val, float)
        assert unc is None or isinstance(unc, float)
        assert model.predict(sample_data["X"][:6]).shape == (6,)

    # SurfaceGridConfig validation
    with pytest.raises(GridConfigurationError):
        SurfaceGridConfig(x_idx=0, x_values=np.linspace(0, 1, 5), y_idx=0, y_values=np.linspace(0, 1, 5), num_total_features=2).validate()

    with pytest.raises(GridConfigurationError):
        SurfaceGridConfig(x_idx=0, x_values=np.linspace(0, 1, 5), y_idx=1, y_values=np.linspace(0, 1, 5), num_total_features=3).validate()

    # Vectorized compute_surface_grid
    cfg = SurfaceGridConfig(
        x_idx=0, x_values=np.linspace(0, 5, 10),
        y_idx=1, y_values=np.linspace(0, 5, 10),
        num_total_features=2,
    )
    res = models[1].compute_surface_grid(cfg)
    assert res.X_mesh.shape == (10, 10)
    assert len(res.Z_array) == 1 and res.Z_array[0][0].shape == (10, 10)

    # Uncertainty unsupported check on RidgeCV
    with pytest.raises(UncertaintyNotSupportedError):
        models[1].predict_with_uncertainty(sample_data["X"][:5])
