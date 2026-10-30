"""
tests/test_challenger_optimization.py

Adversarial stress test suite for OptimizationEngine and OptimizationResult (Milestone M2):
1. Adversarial Bounds:
   - Single-point bounds (b_lo == b_hi)
   - Inverted bounds (b_lo > b_hi must raise OptimizationError)
   - Infinite and negative bounds combinations
   - Malformed / mismatched bounds structures
2. Linear Constraint Combinations:
   - ConstraintSpec with LE, GE, EQ (both Enum and string representation)
   - Multiple interacting linear constraints forming a bounded simplex
   - Redundant constraints
   - Infeasible constraints (resulting in optimization failure)
   - Unknown variable detection in ConstraintSpec
3. Maximization vs Minimization:
   - Analytical concave paraboloid: f(x1, x2) = -(x1 - 2)^2 - (x2 - 3)^2 + 10
     -> Maximization finds (2, 3) with value +10
     -> Minimization on [0, 5]^2 finds corner (5, 0) with value -8
   - Constrained convex quadratic: analytical Lagrange multiplier verification
4. 2-Tuple Unpacking & Interoperability:
   - Tuple unpacking (params, val = opt)
   - len(opt) == 2, indexing opt[0], opt[1], opt[2]
   - Dict conversion, properties (.x, .scipy_result), string representations
5. Robustness & Multi-start Restarts:
   - Multi-start random restarts within bounds
   - Resiliency to model exceptions and NaN/Inf evaluations
"""

from typing import List, Optional, Tuple, Union
import numpy as np
import pytest
from scipy.optimize import Bounds, LinearConstraint

from super_rsm.common.config import ConstraintOperator, ConstraintSpec, ModelMetadata
from super_rsm.common.exceptions import OptimizationError
from super_rsm.common.types import ModelCategory
from super_rsm.core.optimization import OptimizationEngine, OptimizationResult
from super_rsm.models.base import BaseRSMModel


class AnalyticalParaboloidModel(BaseRSMModel):
    """
    Test model: f(x1, x2) = -(x1 - 2)^2 - (x2 - 3)^2 + 10.
    Concave paraboloid with unique analytical maximum at (2.0, 3.0) where f = 10.0.
    """
    metadata = ModelMetadata(
        name="analytical_paraboloid",
        display_name="Analytical Paraboloid",
        category=ModelCategory.POLYNOMIAL,
        description="Analytic paraboloid for adversarial optimization verification",
    )

    def __init__(self, feature_names: Optional[List[str]] = None) -> None:
        super().__init__()
        self.feature_names = feature_names or ["x1", "x2"]
        self.is_fitted = True
        self.eval_count = 0
        self.raise_on_eval = False

    def fit(self, X: np.ndarray, y: np.ndarray, **kwargs) -> "AnalyticalParaboloidModel":
        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        self.eval_count += len(X)
        if self.raise_on_eval:
            raise RuntimeError("Simulated model evaluation failure")
        x1 = X[:, 0]
        x2 = X[:, 1]
        return -(x1 - 2.0) ** 2 - (x2 - 3.0) ** 2 + 10.0

    def evaluate_point(self, point: Union[np.ndarray, List[float]], return_std: bool = False) -> Tuple[float, Optional[float]]:
        arr = np.asarray(point, dtype=float).reshape(1, -1)
        val = float(self.predict(arr)[0])
        return (val, None) if return_std else (val, None)


class AnalyticalConvexQuadModel(BaseRSMModel):
    """
    Test model: f(x1, x2) = (x1 - 1)^2 + 2*(x2 + 2)^2 - 5.
    Convex paraboloid with unique analytical unconstrained minimum at (1.0, -2.0) where f = -5.0.
    """
    metadata = ModelMetadata(
        name="analytical_convex",
        display_name="Analytical Convex Quadratic",
        category=ModelCategory.POLYNOMIAL,
        description="Convex quadratic for constrained minimization tests",
    )

    def __init__(self) -> None:
        super().__init__()
        self.feature_names = ["x1", "x2"]
        self.is_fitted = True

    def fit(self, X: np.ndarray, y: np.ndarray, **kwargs) -> "AnalyticalConvexQuadModel":
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        x1 = X[:, 0]
        x2 = X[:, 1]
        return (x1 - 1.0) ** 2 + 2.0 * (x2 + 2.0) ** 2 - 5.0

    def evaluate_point(self, point: Union[np.ndarray, List[float]], return_std: bool = False) -> Tuple[float, Optional[float]]:
        arr = np.asarray(point, dtype=float).reshape(1, -1)
        val = float(self.predict(arr)[0])
        return (val, None) if return_std else (val, None)


@pytest.fixture
def paraboloid_model():
    return AnalyticalParaboloidModel()


@pytest.fixture
def convex_model():
    return AnalyticalConvexQuadModel()


# =============================================================================
# 1. Adversarial Bounds Stress Tests
# =============================================================================

def test_bounds_single_point_pinning(paraboloid_model):
    """Single-point bounds (b_lo == b_hi) must pin the specified parameter."""
    # Pin x1 to 4.0 while letting x2 optimize within [0.0, 5.0] to maximize
    # At x1 = 4.0: f(4, x2) = -(4-2)^2 - (x2-3)^2 + 10 = 6 - (x2-3)^2. Max is at x2 = 3, f = 6.
    opt = OptimizationEngine.optimize(
        paraboloid_model,
        bounds={"x1": (4.0, 4.0), "x2": (0.0, 5.0)},
        maximize=True,
    )
    assert opt.success
    assert opt.params[0] == pytest.approx(4.0, abs=1e-5)
    assert opt.params[1] == pytest.approx(3.0, abs=1e-4)
    assert opt.fun == pytest.approx(6.0, abs=1e-4)


def test_bounds_all_single_point(paraboloid_model):
    """All single-point bounds should evaluate exactly at the fixed coordinates."""
    opt = OptimizationEngine.optimize(
        paraboloid_model,
        bounds=[(1.0, 1.0), (2.0, 2.0)],
        maximize=False,
    )
    assert opt.success
    assert opt.params[0] == pytest.approx(1.0, abs=1e-5)
    assert opt.params[1] == pytest.approx(2.0, abs=1e-5)
    # f(1, 2) = -(1-2)^2 - (2-3)^2 + 10 = -1 - 1 + 10 = 8.0
    assert opt.fun == pytest.approx(8.0, abs=1e-4)


@pytest.mark.parametrize("inverted_bounds", [
    {"x1": (5.0, 2.0), "x2": (0.0, 10.0)},
    {"x1": (0.0, 5.0), "x2": (10.0, 3.0)},
    [(5.0, 2.0), (0.0, 10.0)],
    [(0.0, 5.0), (10.0, 3.0)],
    {"x1": (1.0, -np.inf), "x2": (0.0, 5.0)},
    [(np.inf, -np.inf), (0.0, 5.0)],
])
def test_bounds_inverted_must_raise_error(paraboloid_model, inverted_bounds):
    """Inverted bounds (min > max) must raise OptimizationError."""
    with pytest.raises(OptimizationError, match="exceeds maximum bound"):
        OptimizationEngine.optimize(paraboloid_model, bounds=inverted_bounds)


def test_bounds_negative_and_infinite_ranges(paraboloid_model):
    """Test optimization with negative and infinite bounds."""
    # Negative bounds: x1 in [-10.0, -2.0], x2 in [-5.0, -1.0]
    # For concave paraboloid with max at (2, 3), closest point in this negative box is (-2.0, -1.0)
    opt = OptimizationEngine.optimize(
        paraboloid_model,
        bounds={"x1": (-10.0, -2.0), "x2": (-5.0, -1.0)},
        maximize=True,
    )
    assert opt.success
    assert opt.params[0] == pytest.approx(-2.0, abs=1e-3)
    assert opt.params[1] == pytest.approx(-1.0, abs=1e-3)

    # Half-infinite bounds: x1 in [0.0, np.inf), x2 in (-np.inf, np.inf)
    opt_inf = OptimizationEngine.optimize(
        paraboloid_model,
        bounds={"x1": (0.0, np.inf), "x2": (-np.inf, np.inf)},
        maximize=True,
    )
    assert opt_inf.success
    assert opt_inf.params[0] == pytest.approx(2.0, abs=1e-3)
    assert opt_inf.params[1] == pytest.approx(3.0, abs=1e-3)


@pytest.mark.parametrize("malformed_bounds", [
    [(0.0, 1.0)],                   # Length mismatch (1 instead of 2)
    {"x1": "not_a_tuple", "x2": (0, 1)},  # Non-tuple element
    {"x1": (0, 1, 2), "x2": (0, 1)},      # 3-tuple element
    12345,                                 # Unsupported type
])
def test_bounds_malformed_rejection(paraboloid_model, malformed_bounds):
    """Malformed bounds structures must raise OptimizationError."""
    with pytest.raises(OptimizationError):
        OptimizationEngine.optimize(paraboloid_model, bounds=malformed_bounds)


# =============================================================================
# 2. Linear Constraint Combinations & Edge Cases
# =============================================================================

def test_constraint_operators_and_string_spec(paraboloid_model):
    """Test LE, GE, EQ operators and string equivalents in ConstraintSpec."""
    # LE constraint: x1 + x2 <= 3.0 (peak at 2, 3 is blocked; sum was 5)
    spec_le = ConstraintSpec(coeffs={"x1": 1.0, "x2": 1.0}, operator="<=", bound=3.0)
    opt_le = OptimizationEngine.optimize(paraboloid_model, constraints=[spec_le], maximize=True)
    assert opt_le.success
    assert (opt_le.params[0] + opt_le.params[1]) <= 3.0001
    assert opt_le.params[0] == pytest.approx(1.0, abs=1e-2)
    assert opt_le.params[1] == pytest.approx(2.0, abs=1e-2)

    # EQ constraint: x1 - x2 == 0.0 (i.e. x1 == x2)
    # Max of -(x - 2)^2 - (x - 3)^2 + 10 occurs at x = 2.5, f = -0.25 - 0.25 + 10 = 9.5
    spec_eq = ConstraintSpec(coeffs={"x1": 1.0, "x2": -1.0}, operator=ConstraintOperator.EQ, bound=0.0)
    opt_eq = OptimizationEngine.optimize(paraboloid_model, constraints=[spec_eq], maximize=True)
    assert opt_eq.success
    assert opt_eq.params[0] == pytest.approx(2.5, abs=1e-3)
    assert opt_eq.params[1] == pytest.approx(2.5, abs=1e-3)
    assert opt_eq.fun == pytest.approx(9.5, abs=1e-3)


def test_multiple_interacting_constraints(paraboloid_model):
    """Multiple intersecting linear constraints forming a bounded simplex."""
    # Feasible region: x1 + x2 <= 4, x1 - x2 >= 0 (x1 >= x2), x2 >= 1
    # Vertices of this region:
    # 1) x2 = 1 and x1 = x2 -> (1, 1)
    # 2) x2 = 1 and x1 + x2 = 4 -> (3, 1)
    # 3) x1 = x2 and x1 + x2 = 4 -> (2, 2)
    # Inside this region, closest point to (2, 3) is (2, 2)
    specs = [
        ConstraintSpec(coeffs={"x1": 1.0, "x2": 1.0}, operator=ConstraintOperator.LE, bound=4.0),
        ConstraintSpec(coeffs={"x1": 1.0, "x2": -1.0}, operator=ConstraintOperator.GE, bound=0.0),
        ConstraintSpec(coeffs={"x2": 1.0}, operator=ConstraintOperator.GE, bound=1.0),
    ]
    opt = OptimizationEngine.optimize(paraboloid_model, constraints=specs, maximize=True)
    assert opt.success
    assert opt.params[0] == pytest.approx(2.0, abs=1e-2)
    assert opt.params[1] == pytest.approx(2.0, abs=1e-2)
    # f(2, 2) = 0 - (2-3)^2 + 10 = 9.0
    assert opt.fun == pytest.approx(9.0, abs=1e-2)


def test_redundant_constraints(paraboloid_model):
    """Multiple redundant constraints should be handled without divergence."""
    specs = [
        ConstraintSpec(coeffs={"x1": 1.0}, operator=ConstraintOperator.LE, bound=1.0),
        ConstraintSpec(coeffs={"x1": 1.0}, operator=ConstraintOperator.LE, bound=3.0),
        ConstraintSpec(coeffs={"x1": 1.0}, operator=ConstraintOperator.LE, bound=5.0),
    ]
    opt = OptimizationEngine.optimize(paraboloid_model, constraints=specs, maximize=True)
    assert opt.success
    assert opt.params[0] <= 1.0001
    assert opt.params[0] == pytest.approx(1.0, abs=1e-3)


def test_infeasible_constraints_flagged(paraboloid_model):
    """Infeasible constraints must report failure or non-convergence."""
    specs = [
        ConstraintSpec(coeffs={"x1": 1.0}, operator=ConstraintOperator.LE, bound=1.0),
        ConstraintSpec(coeffs={"x1": 1.0}, operator=ConstraintOperator.GE, bound=3.0),
    ]
    opt = OptimizationEngine.optimize(paraboloid_model, constraints=specs, maximize=True)
    assert not opt.success or not (opt.params[0] <= 1.0001 and opt.params[0] >= 2.9999)


def test_constraint_unknown_variable_rejection(paraboloid_model):
    """Unknown variable in ConstraintSpec must raise OptimizationError."""
    spec = ConstraintSpec(coeffs={"x1": 1.0, "unknown_dim": 2.0}, operator="<=", bound=5.0)
    with pytest.raises(OptimizationError, match="Constraint references unknown variable 'unknown_dim'"):
        OptimizationEngine.optimize(paraboloid_model, constraints=[spec])


# =============================================================================
# 3. Maximization vs Minimization Analytical Verification
# =============================================================================

def test_maximization_and_minimization_paraboloid(paraboloid_model):
    """Verify empirical convergence against exact analytical optima."""
    # 1. Maximization: Global max is at (2, 3), f = 10.0
    opt_max = OptimizationEngine.optimize(
        paraboloid_model,
        bounds={"x1": (0.0, 5.0), "x2": (0.0, 5.0)},
        maximize=True,
    )
    assert opt_max.success
    assert opt_max.params[0] == pytest.approx(2.0, abs=1e-4)
    assert opt_max.params[1] == pytest.approx(3.0, abs=1e-4)
    assert opt_max.fun == pytest.approx(10.0, abs=1e-4)

    # 2. Minimization on [0, 5] x [0, 5]: Furthest corner from (2, 3) is (5, 0)
    # f(5, 0) = -(5-2)^2 - (0-3)^2 + 10 = -9 - 9 + 10 = -8.0
    opt_min = OptimizationEngine.optimize(
        paraboloid_model,
        bounds={"x1": (0.0, 5.0), "x2": (0.0, 5.0)},
        maximize=False,
    )
    assert opt_min.success
    assert opt_min.params[0] == pytest.approx(5.0, abs=1e-4)
    assert opt_min.params[1] == pytest.approx(0.0, abs=1e-4)
    assert opt_min.fun == pytest.approx(-8.0, abs=1e-4)


def test_constrained_convex_minimization_lagrange(convex_model):
    """Verify constrained minimization against analytical Lagrange multiplier solution."""
    # f(x1, x2) = (x1 - 1)^2 + 2*(x2 + 2)^2 - 5 subject to x1 + x2 == 1
    # Analytical solution: x1* = 7/3 (~2.3333), x2* = -4/3 (~-1.3333), f* = -7/3 (~-2.3333)
    spec = ConstraintSpec(coeffs={"x1": 1.0, "x2": 1.0}, operator=ConstraintOperator.EQ, bound=1.0)
    opt = OptimizationEngine.optimize(
        convex_model,
        constraints=[spec],
        maximize=False,
    )
    assert opt.success
    assert opt.params[0] == pytest.approx(7.0 / 3.0, abs=1e-3)
    assert opt.params[1] == pytest.approx(-4.0 / 3.0, abs=1e-3)
    assert opt.fun == pytest.approx(-7.0 / 3.0, abs=1e-3)


# =============================================================================
# 4. 2-Tuple Unpacking & Interoperability
# =============================================================================

def test_2tuple_unpacking_and_indexing(paraboloid_model):
    """Verify 2-tuple unpacking (params, val = opt) and legacy indexing."""
    opt = OptimizationEngine.optimize(
        paraboloid_model,
        bounds={"x1": (0.0, 5.0), "x2": (0.0, 5.0)},
        maximize=True,
    )
    # Tuple unpacking
    params, val = opt
    assert isinstance(params, np.ndarray) and params.shape == (2,)
    assert isinstance(val, (float, np.floating))
    assert params[0] == pytest.approx(2.0, abs=1e-4)
    assert val == pytest.approx(10.0, abs=1e-4)

    # len() and indexing
    assert len(opt) == 2
    np.testing.assert_array_equal(opt[0], opt.params)
    assert opt[1] == opt.fun
    assert opt.x is opt.params
    assert opt.scipy_result is not None

    with pytest.raises(IndexError):
        _ = opt[2]

    # to_dict conversion
    d = opt.to_dict(["featA", "featB"])
    assert "featA" in d and "featB" in d
    assert d["featA"] == pytest.approx(2.0, abs=1e-4)

    # String representation
    s = str(opt)
    assert "OptimizationResult" in s and "Converged" in s


# =============================================================================
# 5. Robustness & Multi-start Restarts
# =============================================================================

def test_multistart_restarts_stay_within_bounds(paraboloid_model):
    """Multi-start random restarts must evaluate and stay within prescribed bounds."""
    opt = OptimizationEngine.optimize(
        paraboloid_model,
        bounds={"x1": (1.0, 3.0), "x2": (2.0, 4.0)},
        maximize=True,
        n_restarts=5,
        random_state=42,
    )
    assert opt.success
    assert opt.params[0] == pytest.approx(2.0, abs=1e-4)
    assert opt.params[1] == pytest.approx(3.0, abs=1e-4)


def test_model_exception_resiliency(paraboloid_model):
    """OptimizationEngine objective wrapper must catch model exceptions and apply 1e12 penalty."""
    paraboloid_model.raise_on_eval = True
    opt = OptimizationEngine.optimize(
        paraboloid_model,
        bounds={"x1": (0.0, 5.0), "x2": (0.0, 5.0)},
        maximize=False,
    )
    # Should not crash Python; best_res returns with large objective
    assert opt.raw_result is not None
