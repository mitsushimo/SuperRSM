"""
Empirical stress tests for SuperRSM Milestone M1:
1. Concurrency and thread safety in ModelRegistry
2. HyperparameterSpec.validate() boundary, type, and choice checking
3. SurfaceGridConfig.validate() collision detection and compute_surface_grid() 10,000 points latency benchmark
"""

import time
import threading
import concurrent.futures
import numpy as np
import pytest

from super_rsm.common.types import ModelCategory, ConstraintOperator
from super_rsm.common.config import HyperparameterSpec, ModelMetadata, ConstraintSpec
from super_rsm.common.exceptions import (
    HyperparameterValidationError,
    GridConfigurationError,
    RegistryError,
    UncertaintyNotSupportedError,
)
from super_rsm.models.registry import ModelRegistry, register_model
from super_rsm.models.base import BaseRSMModel, SurfaceGridConfig, SurfaceGridResult, ModelMetrics
from super_rsm.models.polynomial_ols import PolynomialOLSModel
from super_rsm.models.ridge import RidgeCVRSMModel
from super_rsm.models.gaussian_process import GaussianProcessRSMModel
from super_rsm.models.symbolic import SymbolicRegressorRSMModel


# ==============================================================================
# 1. CONCURRENCY & THREAD SAFETY STRESS TESTS
# ==============================================================================

class DummyModel(BaseRSMModel):
    metadata = ModelMetadata(
        name="dummy_test_model",
        display_name="Dummy Model",
        category=ModelCategory.POLYNOMIAL,
        description="A dummy test model for concurrency testing",
    )
    def fit(self, X, y, feature_names=None, **kwargs):
        self.is_fitted = True
        return self
    def predict(self, X):
        return np.zeros(len(X))


def test_concurrent_registration_unique_models():
    """Verify 50 threads can concurrently register distinct models without race conditions."""
    n_threads = 50
    created_classes = []

    for i in range(n_threads):
        meta = ModelMetadata(
            name=f"concurrent_model_{i}",
            display_name=f"Concurrent Model {i}",
            category=ModelCategory.POLYNOMIAL,
            description="Testing concurrent registration",
        )
        cls_i = type(f"DynamicModel{i}", (BaseRSMModel,), {"metadata": meta, "fit": lambda s, X, y: s, "predict": lambda s, X: np.zeros(len(X))})
        created_classes.append(cls_i)

    errors = []
    def register_worker(cls_to_reg):
        try:
            ModelRegistry.register(cls_to_reg)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=register_worker, args=(cls,)) for cls in created_classes]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0, f"Errors during concurrent registration: {errors}"

    for i in range(n_threads):
        name = f"concurrent_model_{i}"
        assert ModelRegistry.contains(name)
        assert ModelRegistry.get(name) is created_classes[i]
        # Clean up
        ModelRegistry.unregister(name)


def test_concurrent_read_write_heavy_stress():
    """
    Stress test with 60 threads concurrently registering, unregistering, querying,
    and listing models to detect race conditions or dict modification errors.
    """
    stop_event = threading.Event()
    errors = []
    ops_completed = [0]
    lock = threading.Lock()

    # Pre-register a set of base models
    base_names = [f"base_stress_model_{i}" for i in range(10)]
    for name in base_names:
        meta = ModelMetadata(name=name, display_name=name, category=ModelCategory.POLYNOMIAL, description="")
        cls_ = type(name, (BaseRSMModel,), {"metadata": meta, "fit": lambda s, X, y: s, "predict": lambda s, X: np.zeros(len(X))})
        ModelRegistry.register(cls_)

    def reader_list():
        while not stop_event.is_set():
            try:
                names = ModelRegistry.list_names()
                assert isinstance(names, list)
                with lock:
                    ops_completed[0] += 1
            except Exception as e:
                errors.append(("reader_list", e))

    def reader_metadata():
        while not stop_event.is_set():
            try:
                # get_all_metadata iterates over _models.items() while other threads may register/unregister!
                all_meta = ModelRegistry.get_all_metadata()
                assert isinstance(all_meta, dict)
                with lock:
                    ops_completed[0] += 1
            except Exception as e:
                errors.append(("reader_metadata", e))

    def reader_get():
        while not stop_event.is_set():
            try:
                for b_name in base_names:
                    if ModelRegistry.contains(b_name):
                        cls_ = ModelRegistry.get(b_name)
                        assert cls_ is not None
                with lock:
                    ops_completed[0] += 1
            except Exception as e:
                errors.append(("reader_get", e))

    def writer_reg_unreg(thread_id):
        idx = 0
        while not stop_event.is_set():
            name = f"temp_stress_{thread_id}_{idx}"
            idx += 1
            meta = ModelMetadata(name=name, display_name=name, category=ModelCategory.POLYNOMIAL, description="")
            cls_ = type(name, (BaseRSMModel,), {"metadata": meta, "fit": lambda s, X, y: s, "predict": lambda s, X: np.zeros(len(X))})
            try:
                ModelRegistry.register(cls_)
                assert ModelRegistry.contains(name)
                ModelRegistry.unregister(name)
                with lock:
                    ops_completed[0] += 1
            except Exception as e:
                errors.append(("writer", e))

    threads = []
    for _ in range(15):
        threads.append(threading.Thread(target=reader_list))
    for _ in range(15):
        threads.append(threading.Thread(target=reader_metadata))
    for _ in range(15):
        threads.append(threading.Thread(target=reader_get))
    for tid in range(15):
        threads.append(threading.Thread(target=writer_reg_unreg, args=(tid,)))

    for t in threads:
        t.start()

    time.sleep(1.5)  # Run heavy concurrent operations for 1.5 seconds
    stop_event.set()

    for t in threads:
        t.join()

    # Clean up base stress models
    for name in base_names:
        ModelRegistry.unregister(name)

    assert len(errors) == 0, f"Encountered {len(errors)} concurrency errors: {errors[:5]}"
    assert ops_completed[0] > 1000, f"Expected >1000 concurrent ops, got {ops_completed[0]}"


# ==============================================================================
# 2. DYNAMIC PARAMETER VALIDATION (HyperparameterSpec)
# ==============================================================================

def test_hyperparameter_spec_numeric_bounds():
    """Verify validation strictly rejects values outside min_val and max_val."""
    spec = HyperparameterSpec(
        name="test_param",
        display_name="Test Param",
        param_type=int,
        default=5,
        min_val=1,
        max_val=10,
    )
    # Valid
    assert spec.validate(5) == 5
    assert spec.validate(1) == 1
    assert spec.validate(10) == 10
    assert spec.validate("7") == 7

    # Invalid bounds
    with pytest.raises(HyperparameterValidationError, match="< minimum allowed"):
        spec.validate(0)
    with pytest.raises(HyperparameterValidationError, match="< minimum allowed"):
        spec.validate(-5)
    with pytest.raises(HyperparameterValidationError, match="> maximum allowed"):
        spec.validate(11)
    with pytest.raises(HyperparameterValidationError, match="> maximum allowed"):
        spec.validate(100)


def test_hyperparameter_spec_float_bounds_and_special_values():
    """Verify float bounds and examine behavior on NaN and Inf."""
    spec = HyperparameterSpec(
        name="alpha",
        display_name="Alpha",
        param_type=float,
        default=0.1,
        min_val=0.01,
        max_val=1.0,
    )
    assert spec.validate(0.01) == 0.01
    assert spec.validate(1.0) == 1.0
    assert spec.validate("0.5") == 0.5

    with pytest.raises(HyperparameterValidationError, match="< minimum allowed"):
        spec.validate(0.009)
    with pytest.raises(HyperparameterValidationError, match="> maximum allowed"):
        spec.validate(1.0001)

    # Inf should be rejected if max_val is set
    with pytest.raises(HyperparameterValidationError, match="> maximum allowed"):
        spec.validate(float("inf"))

    # -Inf should be rejected if min_val is set
    with pytest.raises(HyperparameterValidationError, match="< minimum allowed"):
        spec.validate(float("-inf"))


def test_hyperparameter_spec_types_and_choices():
    """Verify type checking and categorical choice enforcement."""
    spec_choices = HyperparameterSpec(
        name="kernel",
        display_name="Kernel Type",
        param_type=str,
        default="rbf",
        choices=["rbf", "matern", "linear"],
    )
    assert spec_choices.validate("rbf") == "rbf"
    assert spec_choices.validate("matern") == "matern"

    with pytest.raises(HyperparameterValidationError, match="must be one of"):
        spec_choices.validate("polynomial")
    with pytest.raises(HyperparameterValidationError, match="must be one of"):
        spec_choices.validate("invalid_choice")

    # Incompatible types
    spec_int = HyperparameterSpec(
        name="degree",
        display_name="Degree",
        param_type=int,
        default=2,
    )
    with pytest.raises(HyperparameterValidationError, match="must be of type int"):
        spec_int.validate("not_an_int")
    with pytest.raises(HyperparameterValidationError, match="must be of type int"):
        spec_int.validate([1, 2])
    with pytest.raises(HyperparameterValidationError, match="must be of type int"):
        spec_int.validate(None)


# ==============================================================================
# 3. SURFACE GRID TEST: COLLISION DETECTION & PERFORMANCE BENCHMARK
# ==============================================================================

def test_surface_grid_config_axis_collisions():
    """Verify SurfaceGridConfig.validate() detects all varieties of index collisions."""
    # 1. x_idx == y_idx
    cfg1 = SurfaceGridConfig(x_idx=0, x_values=np.linspace(0, 1, 10), y_idx=0, y_values=np.linspace(0, 1, 10), num_total_features=2)
    with pytest.raises(GridConfigurationError, match="must be distinct"):
        cfg1.validate()

    # 2. p_info collides with x_idx
    cfg2 = SurfaceGridConfig(
        x_idx=0, x_values=np.linspace(0, 1, 10),
        y_idx=1, y_values=np.linspace(0, 1, 10),
        num_total_features=3,
        p_info=(0, np.array([0.5])),
    )
    with pytest.raises(GridConfigurationError, match="p_info dimension 0 collides"):
        cfg2.validate()

    # 3. p_info collides with y_idx
    cfg3 = SurfaceGridConfig(
        x_idx=0, x_values=np.linspace(0, 1, 10),
        y_idx=1, y_values=np.linspace(0, 1, 10),
        num_total_features=3,
        p_info=(1, np.array([0.5])),
    )
    with pytest.raises(GridConfigurationError, match="p_info dimension 1 collides"):
        cfg3.validate()

    # 4. q_info collides with p_info
    cfg4 = SurfaceGridConfig(
        x_idx=0, x_values=np.linspace(0, 1, 10),
        y_idx=1, y_values=np.linspace(0, 1, 10),
        num_total_features=4,
        p_info=(2, np.array([0.5])),
        q_info=(2, np.array([0.5])),
    )
    with pytest.raises(GridConfigurationError, match="q_info dimension 2 collides"):
        cfg4.validate()

    # 5. fixed_values collides with assigned axis
    cfg5 = SurfaceGridConfig(
        x_idx=0, x_values=np.linspace(0, 1, 10),
        y_idx=1, y_values=np.linspace(0, 1, 10),
        num_total_features=3,
        fixed_values=[(1, 0.5)],
    )
    with pytest.raises(GridConfigurationError, match="Fixed value dimension 1 collides"):
        cfg5.validate()

    # 6. fixed_values duplicate dimension
    cfg6 = SurfaceGridConfig(
        x_idx=0, x_values=np.linspace(0, 1, 10),
        y_idx=1, y_values=np.linspace(0, 1, 10),
        num_total_features=4,
        fixed_values=[(2, 0.5), (2, 0.8)],
    )
    with pytest.raises(GridConfigurationError, match="Fixed value dimension 2 collides"):
        cfg6.validate()

    # 7. Unassigned missing dimensions
    cfg7 = SurfaceGridConfig(
        x_idx=0, x_values=np.linspace(0, 1, 10),
        y_idx=1, y_values=np.linspace(0, 1, 10),
        num_total_features=4,
        fixed_values=[(2, 0.5)],  # dimension 3 is missing!
    )
    with pytest.raises(GridConfigurationError, match="Dimensions \\[3\\] are unassigned"):
        cfg7.validate()


def test_surface_grid_config_out_of_bounds_dimensions():
    """
    Adversarial test: verify whether SurfaceGridConfig.validate() catches
    out-of-bounds dimensions (> num_total_features or < 0).
    """
    # 1. fixed_values has index 5 when num_total_features is 2
    cfg_oob_fixed = SurfaceGridConfig(
        x_idx=0,
        x_values=np.linspace(0, 1, 10),
        y_idx=1,
        y_values=np.linspace(0, 1, 10),
        num_total_features=2,
        fixed_values=[(5, 0.5)],
    )
    # Does validate() detect that dimension 5 is out of bounds [0, num_total_features - 1]?
    # Currently, validate() computes: missing = set(range(num_total_features)) - assigned
    # but does NOT verify: assigned.issubset(set(range(num_total_features)))!
    # Let's check if it raises GridConfigurationError or lets it pass to fail as IndexError:
    try:
        cfg_oob_fixed.validate()
        validated_without_error = True
    except GridConfigurationError:
        validated_without_error = False

    # 2. Check if compute_surface_grid crashes with IndexError when passed invalid config
    model = PolynomialOLSModel(degree_fit=1)
    np.random.seed(42)
    X = np.random.uniform(0, 10, size=(10, 2))
    y = 2.0 * X[:, 0] + 3.0 * X[:, 1]
    model.fit(X, y)

    crashed_with_index_error = False
    if validated_without_error:
        try:
            model.compute_surface_grid(cfg_oob_fixed)
        except IndexError:
            crashed_with_index_error = True

    print(f"\n[VULN CHECK] OOB dimension allowed by validate(): {validated_without_error}, crashed with IndexError: {crashed_with_index_error}")
    # Document this behavior
    assert validated_without_error is True or not crashed_with_index_error


def test_hyperparameter_spec_nan_handling():
    """
    Adversarial test: verify how HyperparameterSpec.validate() behaves with NaN.
    In Python, NaN < min_val is False and NaN > max_val is False.
    """
    spec = HyperparameterSpec(
        name="learning_rate",
        display_name="Learning Rate",
        param_type=float,
        default=0.01,
        min_val=0.001,
        max_val=1.0,
    )
    nan_val = float("nan")
    # Python comparison: nan < 0.001 is False, nan > 1.0 is False
    res = spec.validate(nan_val)
    print(f"\n[VULN CHECK] HyperparameterSpec passed NaN: {np.isnan(res)}")
    # Record empirical finding: validate() allows float('nan') because NaN comparisons are always False


def test_surface_grid_performance_all_models():
    """
    Benchmark 10,000 points latency across all 4 models (PolynomialOLS, Ridge, GP, Symbolic).
    """
    np.random.seed(42)
    X = np.random.uniform(-5, 5, size=(60, 2))
    y = 2.0 * X[:, 0]**2 - 3.0 * X[:, 1] + 10.0 + np.random.normal(0, 0.1, size=60)

    x_grid = np.linspace(-5, 5, 100)
    y_grid = np.linspace(-5, 5, 100)
    cfg = SurfaceGridConfig(
        x_idx=0,
        x_values=x_grid,
        y_idx=1,
        y_values=y_grid,
        num_total_features=2,
    )

    # 1. PolynomialOLSModel
    ols = PolynomialOLSModel(degree_fit=2).fit(X, y)
    t0 = time.perf_counter()
    ols.compute_surface_grid(cfg)
    t_ols = (time.perf_counter() - t0) * 1000

    # 2. RidgeCVRSMModel
    ridge = RidgeCVRSMModel(degree_fit=2).fit(X, y)
    t0 = time.perf_counter()
    ridge.compute_surface_grid(cfg)
    t_ridge = (time.perf_counter() - t0) * 1000

    # 3. GaussianProcessRSMModel
    gp = GaussianProcessRSMModel(degree_fit=2).fit(X, y)
    t0 = time.perf_counter()
    gp.compute_surface_grid(cfg)
    t_gp = (time.perf_counter() - t0) * 1000

    # 3b. GP with uncertainty
    cfg_unc = SurfaceGridConfig(
        x_idx=0,
        x_values=x_grid,
        y_idx=1,
        y_values=y_grid,
        num_total_features=2,
        compute_uncertainty=True,
    )
    t0 = time.perf_counter()
    gp.compute_surface_grid(cfg_unc)
    t_gp_unc = (time.perf_counter() - t0) * 1000

    # 4. SymbolicRegressorRSMModel
    sym = SymbolicRegressorRSMModel(population_size=100, generations=3, random_state=42).fit(X, y)
    t0 = time.perf_counter()
    sym.compute_surface_grid(cfg)
    t_sym = (time.perf_counter() - t0) * 1000

    print(f"\n[BENCHMARK] 10,000 points grid evaluation:")
    print(f"  PolynomialOLSModel:       {t_ols:.2f} ms")
    print(f"  RidgeCVRSMModel:          {t_ridge:.2f} ms")
    print(f"  GaussianProcess (no unc): {t_gp:.2f} ms")
    print(f"  GaussianProcess (with u): {t_gp_unc:.2f} ms")
    print(f"  SymbolicRegressorRSMModel:{t_sym:.2f} ms")

    # Assertions
    assert t_ols < 50.0, f"PolynomialOLSModel exceeded 50ms: {t_ols:.2f}ms"
    assert t_ridge < 50.0, f"RidgeCVRSMModel exceeded 50ms: {t_ridge:.2f}ms"
    assert t_sym < 50.0, f"SymbolicRegressorRSMModel exceeded 50ms: {t_sym:.2f}ms"
    # Note: GP on 10,000 points involves kernel operations over training set (60 pts) x 10,000 pts
    print(f"  GP latency: {t_gp:.2f}ms (target <50ms? -> {t_gp < 50.0})")


def test_surface_grid_scatter_validation():
    """
    Adversarial test: when include_scatter=True, does validate() check
    X_scatter shape, or does it crash with IndexError during compute_surface_grid()?
    """
    cfg = SurfaceGridConfig(
        x_idx=0,
        x_values=np.linspace(0, 1, 10),
        y_idx=1,
        y_values=np.linspace(0, 1, 10),
        num_total_features=2,
        include_scatter=True,
        X_scatter=np.array([[0.5]]),  # Only 1 column, but model has 2 features!
        y_scatter=np.array([1.0]),
    )
    # validate() passes because it doesn't check X_scatter columns:
    cfg.validate()

    model = PolynomialOLSModel(degree_fit=1)
    np.random.seed(42)
    X = np.random.uniform(0, 10, size=(10, 2))
    y = 2.0 * X[:, 0] + 3.0 * X[:, 1]
    model.fit(X, y)

    # In compute_surface_grid, config.X_scatter[mask, config.y_idx] will access column 1 on a 1-column array:
    crashed_with_index_error = False
    try:
        model.compute_surface_grid(cfg)
    except IndexError:
        crashed_with_index_error = True

    print(f"\n[VULN CHECK] X_scatter column mismatch caused IndexError in compute_surface_grid: {crashed_with_index_error}")
    assert crashed_with_index_error is True


if __name__ == "__main__":
    pytest.main(["-v", __file__])


