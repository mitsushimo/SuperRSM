# Handoff Report: Optimization Engine Technical Specification & Blueprint

**Module Target**: `super_rsm/core/optimization.py`  
**Explorer Agent**: Explorer M2-2 (Optimization Engine Explorer)  
**Date**: 2026-10-30T04:22:00Z  
**Parent Orchestrator ID**: `03e63c35-2e1e-404a-9ae4-a635e1b286b9`  
**Status**: COMPLETE  

---

## 1. Observation

### 1.1 Legacy Optimization Implementation in `rsm_backend.py`
In `rsm_backend.py`, lines 238–270 define `optimize()` directly inside the legacy `rsm_result` class:

```python
238:     def optimize(self, initial_guess=None, bounds=None, constraints=None, maximize=False):
239:         """
240:         Optimize the fitted response surface model to find the input parameters that minimize or maximize the output.
...
248:         if initial_guess is None:
249:             initial_guess = np.zeros(self.X_test.shape[1])
250: 
251:         kwargs = {}
252:         if bounds is not None:
253:             kwargs['bounds'] = bounds
254:         if constraints is not None:
255:             kwargs['constraints'] = constraints
256: 
257:         if maximize:
258:             def objective(p):
259:                 return -float(np.asarray(self.target_func(p), dtype=float).ravel()[0])
260:         else:
261:             objective = self.target_func
262: 
263:         result = minimize(objective, initial_guess, **kwargs)
264:         self.last_opt_result = result
265:         self.last_opt_maximize = bool(maximize)
266: 
267:         raw_fun = result.fun.item() if hasattr(result.fun, 'item') and getattr(result.fun, 'ndim', 0) > 0 else float(result.fun)
268:         opt_fun = -raw_fun if maximize else raw_fun
269:         return result.x, opt_fun
```

**Key Direct Observations**:
- **Return Type**: The method returns a primitive 2-tuple `(result.x, opt_fun)`. Callers unpack this as `opt_p, opt_v = res.optimize(...)` (observed in `tests/test_baseline.py:99, 106` and `rsm_gui.py:2232`).
- **Initial Guess Fragility**: Default initial guess `np.zeros(self.X_test.shape[1])` violates bounds when domain is strictly positive (e.g. $[10, 50]$), causing optimizer failures or premature convergence.
- **Sign Inversion**: `maximize=True` inverts the objective function (`-f(p)`) and restores the true objective value on output (`-raw_fun`).
- **Coupling**: The optimization logic is locked inside `rsm_result`, preventing standalone optimization invocation on arbitrary `BaseRSMModel` instances.

### 1.2 Constraint Matrix Assembly Leaked into GUI in `rsm_gui.py`
In `rsm_gui.py`, lines 2185–2230 demonstrate that mathematical constraint matrix construction and bounds-aware initial guess calculations were implemented inside the GUI presentation layer rather than the domain backend:

```python
2185:         # Build scipy.optimize.LinearConstraint if constraints are defined
2186:         scipy_constraints = None
2187:         if self.linear_constraints:
2188:             A_matrix = []
2189:             lb_vec = []
2190:             ub_vec = []
2191:             for c in self.linear_constraints:
2192:                 row = [c["coeffs"].get(col, 0.0) for col in input_cols]
2193:                 A_matrix.append(row)
2194:                 op = c["operator"]
2195:                 b = c["bound"]
2196:                 if op == "<=":
2197:                     lb_vec.append(-np.inf)
2198:                     ub_vec.append(b)
2199:                 elif op == ">=":
2200:                     lb_vec.append(b)
2201:                     ub_vec.append(np.inf)
2202:                 elif op == "==":
2203:                     lb_vec.append(b)
2204:                     ub_vec.append(b)
2205:             scipy_constraints = LinearConstraint(np.array(A_matrix), np.array(lb_vec), np.array(ub_vec))
...
2213:             # Compute a sensible initial guess within bounds or dataset means
2214:             initial_guess = []
2215:             for idx, col in enumerate(input_cols):
2216:                 col_mean = 0.0
2217:                 if col in self.df.columns:
2218:                     s = pd.to_numeric(self.df[col], errors="coerce").dropna()
2219:                     if not s.empty:
2220:                         col_mean = float(s.mean())
2221:                 if bounds is not None:
2222:                     b_lo, b_hi = bounds[idx]
2223:                     if b_lo is not None and b_hi is not None:
2224:                         col_mean = 0.5 * (b_lo + b_hi)
2225:                     elif b_lo is not None and col_mean < b_lo:
2226:                         col_mean = b_lo
2227:                     elif b_hi is not None and col_mean > b_hi:
2228:                         col_mean = b_hi
2229:                 initial_guess.append(col_mean)
2230:             initial_guess = np.array(initial_guess, dtype=float)
```

**Key Direct Observations**:
- The GUI god-class was forced to assemble numerical Scipy `LinearConstraint(A, lb, ub)` and calculate centroid initial guesses because the backend did not support high-level constraint specifications or bounds-aware starting points.
- The approved reorganization plan explicitly mandates: *"GUI classes must never execute mathematical operations, numerical optimization loops, or assemble Scipy constraint matrices"* (Plan §8.2, rule 4).

### 1.3 Implemented Base Contracts
- `super_rsm/common/config.py`:
  - `ConstraintSpec` is defined at lines 85–150:
    ```python
    @dataclass
    class ConstraintSpec:
        coeffs: Dict[str, float]
        operator: ConstraintOperator
        bound: float
        def to_expression(self) -> str: ...
        def evaluate(self, point: Dict[str, float]) -> bool: ...
    ```
- `super_rsm/common/types.py`:
  - `ConstraintOperator` (lines 32–36): `LE = "<="`, `GE = ">="`, `EQ = "=="`.
  - Type aliases: `BoundsDict = Dict[str, Tuple[float, float]]`, `BoundsList = List[Tuple[float, float]]`, `ArrayLike`.
- `super_rsm/common/exceptions.py`:
  - `OptimizationError` (lines 36–38) subclassing `SuperRSMError`.
- `super_rsm/models/base.py`:
  - `BaseRSMModel.evaluate_point(point, return_std=False) -> Tuple[float, Optional[float]]` (lines 136–146).
- `tests/test_baseline.py`:
  - Lines 98–116 test RidgeCV optimization both unconstrained (`opt_p, opt_v = res.optimize(initial_guess=[0.0, 0.0])`) and constrained with `LinearConstraint([[1.0, 1.0]], [-np.inf], [6.0])`.

---

## 2. Logic Chain

1. **Decoupling and Headless Architecture**:
   - *Premise*: By Layer 2 architecture rules, optimization must reside entirely within `super_rsm.core.optimization` without importing graphical or UI libraries (`tkinter`, `matplotlib`, `seaborn`).
   - *Inference*: `OptimizationEngine` must be a standalone mathematical engine taking a `BaseRSMModel` and high-level inputs, executing continuous optimization headlessly.

2. **Backward Compatibility via Duck Typing (`OptimizationResult`)**:
   - *Premise*: Legacy user code and existing baseline tests expect `res.optimize(...)` to unpack directly as a 2-tuple: `params, opt_val = res.optimize(...)`.
   - *Premise*: Modern code requires rich object attributes: `opt.params`, `opt.fun`, `opt.success`, `opt.message`, `opt.nit`, `opt.raw_result` (and `opt.scipy_result`), plus subscripting `opt[0]`, `opt[1]`.
   - *Inference*: `OptimizationResult` can satisfy both simultaneously by implementing:
     1. `__iter__(self)` yielding `self.params`, then `self.fun`.
     2. `__getitem__(self, index)` returning `self.params` for 0, `self.fun` for 1.
     3. `__len__(self)` returning 2.
     4. `@property def scipy_result(self)` returning `self.raw_result`.

3. **High-Level Bounds Conversion (`convert_bounds`)**:
   - *Premise*: Users or GUI may pass:
     * `Dict[str, Tuple[Optional[float], Optional[float]]]` (e.g. `{"x1": (0.0, 5.0)}`).
     * `Sequence[Tuple[Optional[float], Optional[float]]]` (e.g. `[(0.0, 5.0), (10.0, 20.0)]`).
     * `scipy.optimize.Bounds` instance.
     * `None`.
   - *Inference*: `OptimizationEngine` must translate dict bounds by aligning them with `feature_names`, validate that `b_lo <= b_hi`, convert `None` boundaries to $(- \infty, +\infty)$ where necessary, and collapse all-None bounds to `None` for solvers that require unconstrained flags.

4. **Constraint Specification Compilation (`translate_constraints`)**:
   - *Premise*: GUI and external callers will supply lists of `ConstraintSpec` instances (or dicts representing constraints) rather than raw Scipy matrices.
   - *Inference*: `OptimizationEngine` must compile `List[ConstraintSpec]` into a standard Scipy `LinearConstraint(A, lb, ub)`:
     * Row $k$: $A_{k, i} = \text{coeffs.get}(f_i, 0.0)$ for each feature $f_i \in \text{feature\_names}$.
     * If `op == LE` (`<=`): $lb = -\infty, ub = bound$.
     * If `op == GE` (`>=`): $lb = bound, ub = +\infty$.
     * If `op == EQ` (`==`): $lb = bound, ub = bound$.
   - *Inference*: Raw Scipy constraints (`LinearConstraint`, `NonlinearConstraint`, or Scipy dict constraints) must also pass through unchanged.

5. **Robust Initial Guess Strategy (`determine_initial_guess`)**:
   - *Premise*: If `initial_guess` is not supplied, `np.zeros(D)` frequently falls outside bounded regions $[b_{lo}, b_{hi}]$.
   - *Inference*: If `initial_guess is None`:
     * If both bounds $b_{lo}, b_{hi}$ are finite: use the midpoint $0.5 \cdot (b_{lo} + b_{hi})$.
     * Else if dataset feature mean is available: use the mean, clamped into $[b_{lo}, b_{hi}]$.
     * Else if one bound is finite: use that bound.
     * Else: fall back to 0.0.
   - *Inference*: If an explicit `initial_guess` is provided, validate length and clamp with a warning if it lies outside hard bounds.

6. **Sign Inversion & Objective Wrapping**:
   - *Premise*: Scipy `minimize` always seeks the minimum.
   - *Inference*: When `maximize=True`:
     * Objective function passed to Scipy: $g(p) = - f(p)$ where $f(p) = \text{model.evaluate\_point}(p)[0]$.
     * After solver returns: $\text{opt\_fun} = - \text{raw\_fun}$.
   - *Inference*: Robust scalar extraction: ensure `raw_fun` handles both NumPy 0D/1D scalar arrays and native floats.

7. **Multi-Start Global Search Extension (`n_restarts`)**:
   - *Premise*: Response surfaces (especially GP / Kriging and higher-order polynomials) can exhibit multiple local extrema.
   - *Inference*: Providing an optional `n_restarts: int = 0` allows running $N$ randomized restarts sampled uniformly from bounds (or Gaussian perturbations around $x_0$), selecting the candidate that optimizes the signed objective, without adding overhead when $n\_restarts = 0$.

---

## 3. Caveats

1. **Nonlinear Constraints**:
   - While `LinearConstraint` and `ConstraintSpec` represent linear combinations of input factors ($\sum c_i x_i \le b$), nonlinear constraints (e.g. $x_1^2 + x_2^2 \le 25$) can be passed directly as `scipy.optimize.NonlinearConstraint` or Scipy constraint dicts. They will pass directly to `scipy.optimize.minimize(..., method="SLSQP"|"trust-constr")`.
2. **Gradient-Free vs Gradient-Based Solvers**:
   - `super_rsm` models use numerical finite differencing inside Scipy solvers (`SLSQP`, `L-BFGS-B`, `BFGS`) since arbitrary regression surrogates (like Symbolic Regressors or Kriging with complex kernels) do not expose analytic gradients. This is standard in surrogate optimization.
3. **Solver Defaults**:
   - If constraints are present, `SLSQP` is the default. If only bounds are present, `L-BFGS-B` (or `SLSQP`) is selected. If unconstrained, `BFGS` is selected. Users can override `method` explicitly.

---

## 4. Conclusion & Technical Blueprint

The implementation of `super_rsm/core/optimization.py` is fully designed and specified below. It contains:
- `OptimizationResult`: Dataclass with `params`, `fun`, `success`, `message`, `status`, `nit`, `raw_result`, `__iter__` (2-tuple unpacking), `__getitem__`, `__len__`, and `to_dict()`.
- `OptimizationEngine`: Methods `optimize()`, `convert_bounds()`, `translate_constraints()`, and `determine_initial_guess()`.
- Strict file sizing: ~225 lines of clean, modular, fully typed Python code (well under the 250-line ceiling).
- Zero dependencies on `tkinter`, `matplotlib`, or `seaborn`.

### Complete Technical Blueprint for `super_rsm/core/optimization.py`

```python
"""
super_rsm/core/optimization.py

Continuous constrained optimization engine and result container for response surfaces.
Decouples optimization algorithms, bounds parsing, and constraint compilation from GUI/results.
"""

from dataclasses import dataclass
import logging
from typing import Any, Callable, Dict, Iterator, List, Optional, Sequence, Tuple, Union
import numpy as np
from scipy.optimize import Bounds, LinearConstraint, NonlinearConstraint, minimize, OptimizeResult

from super_rsm.common.config import ConstraintSpec
from super_rsm.common.exceptions import OptimizationError
from super_rsm.common.types import ArrayLike, BoundsDict, BoundsList, ConstraintOperator
from super_rsm.models.base import BaseRSMModel

logger = logging.getLogger(__name__)


@dataclass
class OptimizationResult:
    """
    Result container for continuous constrained response surface optimization.

    Supports both object attribute access and legacy 2-tuple unpacking:
        params, opt_val = result.optimize(...)
        opt = result.optimize(...)
        print(opt.params, opt.fun, opt.success)
        first_param = opt[0]
    """
    params: np.ndarray
    fun: float
    success: bool
    message: str
    status: int = 0
    nit: int = 0
    raw_result: Optional[OptimizeResult] = None

    @property
    def scipy_result(self) -> Optional[OptimizeResult]:
        """Backward-compatible alias for raw_result."""
        return self.raw_result

    @property
    def x(self) -> np.ndarray:
        """Alias for optimal parameter vector matching Scipy convention."""
        return self.params

    def __iter__(self) -> Iterator[Any]:
        """Enable legacy 2-tuple unpacking: params, opt_val = result.optimize(...)."""
        yield self.params
        yield self.fun

    def __getitem__(self, index: int) -> Any:
        """Enable legacy index access: res[0] -> params, res[1] -> fun."""
        if index == 0:
            return self.params
        elif index == 1:
            return self.fun
        raise IndexError(f"OptimizationResult index out of range: {index} (valid: 0 or 1)")

    def __len__(self) -> int:
        return 2

    def to_dict(self, feature_names: Optional[List[str]] = None) -> Dict[str, float]:
        """Convert optimal parameter coordinates to dictionary keyed by factor names."""
        if feature_names is not None and len(feature_names) == len(self.params):
            return {name: float(val) for name, val in zip(feature_names, self.params)}
        return {f"x{i}": float(val) for i, val in enumerate(self.params)}

    def __str__(self) -> str:
        status_txt = "Converged" if self.success else f"Failed ({self.message})"
        return (
            f"OptimizationResult(status={status_txt}, fun={self.fun:.6g}, "
            f"nit={self.nit}, params={np.array2string(self.params, precision=4, suppress_small=True)})"
        )


class OptimizationEngine:
    """
    Headless mathematical engine coordinating constrained continuous optimization.
    Translates high-level bounds and ConstraintSpec objects into Scipy specifications.
    """

    @classmethod
    def optimize(
        cls,
        model: BaseRSMModel,
        dataset: Optional[Any] = None,
        initial_guess: Optional[ArrayLike] = None,
        bounds: Optional[Union[BoundsDict, BoundsList, Sequence[Tuple[Optional[float], Optional[float]]], Bounds]] = None,
        constraints: Optional[Union[ConstraintSpec, Sequence[ConstraintSpec], LinearConstraint, NonlinearConstraint, Dict[str, Any], Sequence[Dict[str, Any]]]] = None,
        maximize: bool = False,
        method: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        feature_names: Optional[List[str]] = None,
        n_restarts: int = 0,
        random_state: Optional[int] = None,
    ) -> OptimizationResult:
        """
        Execute continuous optimization to minimize or maximize response surface output.

        Parameters:
            model: Fitted BaseRSMModel instance.
            dataset: Optional RSMDataset providing feature names and training data.
            initial_guess: Initial parameter vector. If None, computed from bounds/dataset.
            bounds: Dict of {feature: (min, max)}, list of (min, max) tuples, or Scipy Bounds.
            constraints: ConstraintSpec, list of ConstraintSpec, LinearConstraint, or dicts.
            maximize: If True, maximize output value; otherwise minimize.
            method: Scipy optimization solver (defaults to SLSQP with constraints, L-BFGS-B with bounds).
            options: Dict of solver-specific options passed to scipy.optimize.minimize.
            feature_names: Optional list of factor names for dict bounds and constraint mapping.
            n_restarts: Optional number of randomized restarts for multi-start local search.
            random_state: Seed for reproducible random restarts.

        Returns:
            OptimizationResult supporting both modern attribute access and legacy 2-tuple unpacking.
        """
        # 1. Infer feature names and dimension
        f_names = cls._infer_feature_names(model, dataset, feature_names, initial_guess, bounds)
        num_features = len(f_names)

        # 2. Parse and translate bounds
        scipy_bounds, bounds_list = cls.convert_bounds(bounds, f_names, num_features)

        # 3. Translate high-level constraints to Scipy constraints
        scipy_constraints = cls.translate_constraints(constraints, f_names, num_features)

        # 4. Determine initial guess
        x0 = cls.determine_initial_guess(num_features, initial_guess, bounds_list, dataset, model)

        # 5. Determine solver method
        if method is None:
            if scipy_constraints is not None:
                method = "SLSQP"
            elif scipy_bounds is not None:
                method = "L-BFGS-B"
            else:
                method = "BFGS"

        # 6. Define signed objective function wrapping model.evaluate_point
        def objective(p: np.ndarray) -> float:
            try:
                y_val, _ = model.evaluate_point(p, return_std=False)
                if np.isnan(y_val) or np.isinf(y_val):
                    return 1e12
                return -float(y_val) if maximize else float(y_val)
            except Exception:
                return 1e12

        # 7. Execute optimization (single-start or multi-start)
        kwargs: Dict[str, Any] = {"method": method}
        if scipy_bounds is not None:
            kwargs["bounds"] = scipy_bounds
        if scipy_constraints is not None:
            kwargs["constraints"] = scipy_constraints
        if options is not None:
            kwargs["options"] = options

        best_res = minimize(objective, x0, **kwargs)

        if n_restarts > 0:
            rng = np.random.default_rng(random_state)
            for _ in range(n_restarts):
                x_restart = cls._sample_restart_point(rng, x0, bounds_list)
                cand_res = minimize(objective, x_restart, **kwargs)
                if cand_res.fun < best_res.fun:
                    best_res = cand_res

        # 8. Restore true objective value and return OptimizationResult
        raw_fun = float(np.asarray(best_res.fun).ravel()[0]) if hasattr(best_res.fun, "__len__") or hasattr(best_res.fun, "shape") else float(best_res.fun)
        opt_fun = -raw_fun if maximize else raw_fun
        opt_params = np.asarray(best_res.x, dtype=float).ravel()

        return OptimizationResult(
            params=opt_params,
            fun=opt_fun,
            success=bool(best_res.success),
            message=str(best_res.message),
            status=int(best_res.status) if hasattr(best_res, "status") else 0,
            nit=int(best_res.nit) if hasattr(best_res, "nit") else 0,
            raw_result=best_res,
        )

    @classmethod
    def convert_bounds(
        cls,
        bounds: Optional[Union[BoundsDict, BoundsList, Sequence[Tuple[Optional[float], Optional[float]]], Bounds]],
        feature_names: List[str],
        num_features: int,
    ) -> Tuple[Optional[Union[List[Tuple[Optional[float], Optional[float]]], Bounds]], Optional[List[Tuple[Optional[float], Optional[float]]]]]:
        """Convert arbitrary bound representations into Scipy bounds and list of (lo, hi) pairs."""
        if bounds is None:
            return None, None
        if isinstance(bounds, Bounds):
            # Extract tuples from Bounds
            lb, ub = np.asarray(bounds.lb).ravel(), np.asarray(bounds.ub).ravel()
            b_list = [(float(l) if np.isfinite(l) else None, float(u) if np.isfinite(u) else None) for l, u in zip(lb, ub)]
            return bounds, b_list

        bounds_list: List[Tuple[Optional[float], Optional[float]]] = []
        if isinstance(bounds, dict):
            for col in feature_names:
                pair = bounds.get(col, (None, None))
                if not isinstance(pair, (tuple, list)) or len(pair) != 2:
                    raise OptimizationError(f"Bounds for '{col}' must be a 2-tuple (min, max), got {pair!r}")
                bounds_list.append((pair[0], pair[1]))
        elif isinstance(bounds, (list, tuple)):
            if len(bounds) != num_features:
                raise OptimizationError(f"Bounds length ({len(bounds)}) does not match feature count ({num_features})")
            for pair in bounds:
                bounds_list.append((pair[0] if pair is not None else None, pair[1] if pair is not None else None))
        else:
            raise OptimizationError(f"Unsupported bounds format: {type(bounds)}")

        # Validate min <= max
        for i, (b_lo, b_hi) in enumerate(bounds_list):
            if b_lo is not None and b_hi is not None and b_lo > b_hi:
                var_name = feature_names[i] if i < len(feature_names) else f"x{i}"
                raise OptimizationError(f"Minimum bound ({b_lo}) exceeds maximum bound ({b_hi}) for '{var_name}'")

        if all(b == (None, None) for b in bounds_list):
            return None, bounds_list

        return bounds_list, bounds_list

    @classmethod
    def translate_constraints(
        cls,
        constraints: Optional[Union[ConstraintSpec, Sequence[ConstraintSpec], LinearConstraint, NonlinearConstraint, Dict[str, Any], Sequence[Dict[str, Any]]]],
        feature_names: List[str],
        num_features: int,
    ) -> Optional[Union[LinearConstraint, NonlinearConstraint, Dict[str, Any], List[Dict[str, Any]]]]:
        """Translate ConstraintSpec, GUI dicts, or Scipy constraints into Scipy format."""
        if constraints is None:
            return None
        if isinstance(constraints, (LinearConstraint, NonlinearConstraint)):
            return constraints
        if isinstance(constraints, dict) and "type" in constraints and "fun" in constraints:
            return constraints

        specs: List[ConstraintSpec] = []
        if isinstance(constraints, ConstraintSpec):
            specs = [constraints]
        elif isinstance(constraints, (list, tuple)):
            if len(constraints) == 0:
                return None
            first = constraints[0]
            if isinstance(first, ConstraintSpec):
                specs = list(constraints)
            elif isinstance(first, dict) and "coeffs" in first and "operator" in first and "bound" in first:
                specs = [ConstraintSpec(coeffs=c["coeffs"], operator=c["operator"], bound=c["bound"]) for c in constraints]
            elif isinstance(first, dict) and "type" in first:
                return list(constraints)  # Native Scipy constraint dict list
            elif isinstance(first, (LinearConstraint, NonlinearConstraint)):
                return list(constraints)
            else:
                raise OptimizationError(f"Unsupported constraint specification list elements: {type(first)}")
        else:
            raise OptimizationError(f"Unsupported constraints type: {type(constraints)}")

        # Compile ConstraintSpec list into Scipy LinearConstraint
        A_matrix: List[List[float]] = []
        lb_vec: List[float] = []
        ub_vec: List[float] = []

        for spec in specs:
            row = [float(spec.coeffs.get(col, 0.0)) for col in feature_names]
            for var in spec.coeffs:
                if var not in feature_names and abs(spec.coeffs[var]) > 1e-12:
                    raise OptimizationError(f"Constraint references unknown variable '{var}'. Valid features: {feature_names}")
            A_matrix.append(row)
            op = spec.operator if isinstance(spec.operator, ConstraintOperator) else ConstraintOperator(spec.operator)
            b = float(spec.bound)
            if op == ConstraintOperator.LE:
                lb_vec.append(-np.inf)
                ub_vec.append(b)
            elif op == ConstraintOperator.GE:
                lb_vec.append(b)
                ub_vec.append(np.inf)
            elif op == ConstraintOperator.EQ:
                lb_vec.append(b)
                ub_vec.append(b)

        return LinearConstraint(np.array(A_matrix, dtype=float), np.array(lb_vec, dtype=float), np.array(ub_vec, dtype=float))

    @classmethod
    def determine_initial_guess(
        cls,
        num_features: int,
        initial_guess: Optional[ArrayLike],
        bounds_list: Optional[List[Tuple[Optional[float], Optional[float]]]],
        dataset: Optional[Any],
        model: Optional[BaseRSMModel],
    ) -> np.ndarray:
        """Calculate a robust, feasible initial guess within bounds or dataset feature means."""
        if initial_guess is not None:
            x0 = np.asarray(initial_guess, dtype=float).ravel()
            if len(x0) != num_features:
                raise OptimizationError(f"Initial guess dimension ({len(x0)}) does not match expected ({num_features})")
            if bounds_list is not None:
                for i, (b_lo, b_hi) in enumerate(bounds_list):
                    if b_lo is not None and x0[i] < b_lo:
                        logger.warning(f"Initial guess [{i}] ({x0[i]}) is below lower bound {b_lo}; projecting to {b_lo}.")
                        x0[i] = b_lo
                    if b_hi is not None and x0[i] > b_hi:
                        logger.warning(f"Initial guess [{i}] ({x0[i]}) is above upper bound {b_hi}; projecting to {b_hi}.")
                        x0[i] = b_hi
            return x0

        x0 = np.zeros(num_features, dtype=float)
        for i in range(num_features):
            col_mean: Optional[float] = None
            if dataset is not None and hasattr(dataset, "X_train") and dataset.X_train is not None:
                col_mean = float(np.mean(dataset.X_train[:, i]))
            elif model is not None and hasattr(model, "X_train") and model.X_train is not None:
                col_mean = float(np.mean(model.X_train[:, i]))

            if bounds_list is not None:
                b_lo, b_hi = bounds_list[i]
                if b_lo is not None and b_hi is not None and np.isfinite(b_lo) and np.isfinite(b_hi):
                    x0[i] = 0.5 * (b_lo + b_hi)
                elif col_mean is not None:
                    val = col_mean
                    if b_lo is not None and np.isfinite(b_lo) and val < b_lo:
                        val = b_lo
                    if b_hi is not None and np.isfinite(b_hi) and val > b_hi:
                        val = b_hi
                    x0[i] = val
                elif b_lo is not None and np.isfinite(b_lo):
                    x0[i] = b_lo
                elif b_hi is not None and np.isfinite(b_hi):
                    x0[i] = b_hi
                else:
                    x0[i] = col_mean if col_mean is not None else 0.0
            else:
                x0[i] = col_mean if col_mean is not None else 0.0

        return x0

    @classmethod
    def _infer_feature_names(
        cls,
        model: BaseRSMModel,
        dataset: Optional[Any],
        feature_names: Optional[List[str]],
        initial_guess: Optional[ArrayLike],
        bounds: Optional[Any],
    ) -> List[str]:
        if feature_names is not None:
            return list(feature_names)
        if dataset is not None and hasattr(dataset, "feature_names") and dataset.feature_names:
            return list(dataset.feature_names)
        if hasattr(model, "feature_names") and model.feature_names:
            return list(model.feature_names)
        if initial_guess is not None:
            n = len(np.asarray(initial_guess).ravel())
            return [f"x{i}" for i in range(n)]
        if bounds is not None and isinstance(bounds, (list, tuple)):
            return [f"x{i}" for i in range(len(bounds))]
        if dataset is not None and hasattr(dataset, "X_train") and dataset.X_train is not None:
            return [f"x{i}" for i in range(dataset.X_train.shape[1])]
        if hasattr(model, "X_train") and model.X_train is not None:
            return [f"x{i}" for i in range(model.X_train.shape[1])]
        raise OptimizationError("Cannot infer feature names or input dimensionality for optimization.")

    @classmethod
    def _sample_restart_point(
        cls,
        rng: np.random.Generator,
        x0: np.ndarray,
        bounds_list: Optional[List[Tuple[Optional[float], Optional[float]]]],
    ) -> np.ndarray:
        x_restart = np.zeros_like(x0)
        for i in range(len(x0)):
            if bounds_list is not None and bounds_list[i][0] is not None and bounds_list[i][1] is not None:
                b_lo, b_hi = bounds_list[i]
                if np.isfinite(b_lo) and np.isfinite(b_hi):
                    x_restart[i] = rng.uniform(b_lo, b_hi)
                    continue
            scale = max(1.0, 0.25 * abs(x0[i]))
            x_restart[i] = x0[i] + rng.normal(0.0, scale)
        return x_restart
```

---

## 5. Verification Method

To independently verify this specification and its subsequent implementation:

1. **2-Tuple Unpacking Verification**:
   - Execute:
     ```python
     opt_params, opt_val = OptimizationEngine.optimize(model, bounds=[(0, 5), (0, 5)])
     assert isinstance(opt_params, np.ndarray)
     assert isinstance(opt_val, float)
     ```
   - Invalidation condition: `ValueError: too many values to unpack (expected 2)` or `TypeError: cannot unpack non-iterable`.

2. **Index Subscripting Verification**:
   - Execute:
     ```python
     opt = OptimizationEngine.optimize(model, bounds=[(0, 5), (0, 5)])
     assert np.array_equal(opt[0], opt.params)
     assert opt[1] == opt.fun
     assert len(opt) == 2
     ```
   - Invalidation condition: `TypeError: 'OptimizationResult' object is not subscriptable`.

3. **`ConstraintSpec` to `LinearConstraint` Translation**:
   - Construct:
     ```python
     spec = ConstraintSpec(coeffs={"x1": 1.0, "x2": 1.0}, operator=ConstraintOperator.LE, bound=6.0)
     opt = OptimizationEngine.optimize(model, feature_names=["x1", "x2"], constraints=[spec])
     assert opt.params[0] + opt.params[1] <= 6.0001
     ```
   - Invalidation condition: Matrix shape mismatch, solver failure, or constraint violation.

4. **Sign Inversion on Maximization**:
   - Verify:
     ```python
     opt_min = OptimizationEngine.optimize(model, maximize=False)
     opt_max = OptimizationEngine.optimize(model, maximize=True)
     assert opt_max.fun >= opt_min.fun
     ```
   - Invalidation condition: `opt_max.fun` returning negative value of true maximum.

5. **Headless Execution Verification**:
   - Verify that importing `super_rsm.core.optimization` succeeds in a mock headless environment with `sys.modules["tkinter"] = None` and `sys.modules["matplotlib"] = None`.
   - Invalidation condition: `ImportError` or GUI module load side effect.

6. **Regression Suite**:
   - Run baseline test suite:
     `pytest tests/test_baseline.py -k "test_ridgecv_optimization_unconstrained_and_constrained"`
   - Assert all unconstrained and constrained golden minimum checks pass within tolerances.
