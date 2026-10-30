"""
super_rsm/core/optimization.py: Continuous constrained optimization engine and result container.
"""

from dataclasses import dataclass
import logging
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple, Union
import numpy as np
from scipy.optimize import Bounds, LinearConstraint, NonlinearConstraint, minimize, OptimizeResult

from super_rsm.common.config import ConstraintSpec
from super_rsm.common.exceptions import OptimizationError
from super_rsm.common.types import ArrayLike, BoundsDict, BoundsList, ConstraintOperator
from super_rsm.models.base import BaseRSMModel

logger = logging.getLogger(__name__)


@dataclass
class OptimizationResult:
    """Result container supporting object attribute access and legacy 2-tuple unpacking."""
    params: np.ndarray
    fun: float
    success: bool
    message: str
    status: int = 0
    nit: int = 0
    raw_result: Optional[OptimizeResult] = None

    @property
    def scipy_result(self) -> Optional[OptimizeResult]: return self.raw_result
    @property
    def x(self) -> np.ndarray: return self.params

    def __iter__(self) -> Iterator[Any]:
        return iter((self.params, self.fun))

    def __getitem__(self, index: int) -> Any:
        if index == 0: return self.params
        if index == 1: return self.fun
        raise IndexError(f"OptimizationResult index out of range: {index}")

    def __len__(self) -> int: return 2

    def to_dict(self, feature_names: Optional[List[str]] = None) -> Dict[str, float]:
        if feature_names is not None and len(feature_names) == len(self.params):
            return {name: float(val) for name, val in zip(feature_names, self.params)}
        return {f"x{i + 1}": float(val) for i, val in enumerate(self.params)}

    def __str__(self) -> str:
        s = "Converged" if self.success else f"Failed ({self.message})"
        return f"OptimizationResult(status={s}, fun={self.fun:.6g}, nit={self.nit}, params={np.array2string(self.params, precision=4, suppress_small=True)})"


class OptimizationEngine:
    """Headless mathematical engine coordinating continuous constrained optimization."""

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
        f_names = cls._infer_feature_names(model, dataset, feature_names, initial_guess, bounds)
        num_features = len(f_names)
        scipy_bounds, bounds_list = cls.convert_bounds(bounds, f_names, num_features)
        scipy_constraints = cls.translate_constraints(constraints, f_names, num_features)
        x0 = cls.determine_initial_guess(num_features, initial_guess, bounds_list, dataset, model)

        if method is None:
            method = "SLSQP" if scipy_constraints is not None else ("L-BFGS-B" if scipy_bounds is not None else "BFGS")

        def objective(p: np.ndarray) -> float:
            try:
                if hasattr(model, "evaluate_point"):
                    res = model.evaluate_point(p, return_std=False)
                    y_val = res[0] if isinstance(res, (tuple, list)) else res
                else:
                    y_val = model.predict(np.asarray(p, dtype=float).reshape(1, -1))[0]
                if np.isnan(y_val) or np.isinf(y_val): return 1e12
                return -float(y_val) if maximize else float(y_val)
            except Exception:
                return 1e12

        kwargs: Dict[str, Any] = {"method": method}
        if scipy_bounds is not None: kwargs["bounds"] = scipy_bounds
        if scipy_constraints is not None: kwargs["constraints"] = scipy_constraints
        if options is not None: kwargs["options"] = options

        best_res = minimize(objective, x0, **kwargs)
        if n_restarts > 0:
            rng = np.random.default_rng(random_state)
            for _ in range(n_restarts):
                cand_res = minimize(objective, cls._sample_restart_point(rng, x0, bounds_list), **kwargs)
                if cand_res.fun < best_res.fun: best_res = cand_res

        raw_fun = float(np.asarray(best_res.fun).ravel()[0]) if hasattr(best_res.fun, "__len__") or hasattr(best_res.fun, "shape") else float(best_res.fun)
        opt_fun = -raw_fun if maximize else raw_fun
        return OptimizationResult(
            params=np.asarray(best_res.x, dtype=float).ravel(),
            fun=opt_fun, success=bool(best_res.success), message=str(best_res.message),
            status=int(getattr(best_res, "status", 0)), nit=int(getattr(best_res, "nit", 0)), raw_result=best_res,
        )

    @classmethod
    def convert_bounds(
        cls,
        bounds: Optional[Union[BoundsDict, BoundsList, Sequence[Tuple[Optional[float], Optional[float]]], Bounds]],
        feature_names: List[str],
        num_features: int,
    ) -> Tuple[Optional[Union[List[Tuple[Optional[float], Optional[float]]], Bounds]], Optional[List[Tuple[Optional[float], Optional[float]]]]]:
        if bounds is None: return None, None
        if isinstance(bounds, Bounds):
            lb, ub = np.asarray(bounds.lb).ravel(), np.asarray(bounds.ub).ravel()
            return bounds, [(float(l) if np.isfinite(l) else None, float(u) if np.isfinite(u) else None) for l, u in zip(lb, ub)]

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

        for i, (b_lo, b_hi) in enumerate(bounds_list):
            if b_lo is not None and b_hi is not None and b_lo > b_hi:
                var_name = feature_names[i] if i < len(feature_names) else f"x{i + 1}"
                raise OptimizationError(f"Minimum bound ({b_lo}) exceeds maximum bound ({b_hi}) for '{var_name}'")

        if all(b == (None, None) for b in bounds_list): return None, bounds_list
        return bounds_list, bounds_list

    @classmethod
    def translate_constraints(
        cls,
        constraints: Optional[Union[ConstraintSpec, Sequence[ConstraintSpec], LinearConstraint, NonlinearConstraint, Dict[str, Any], Sequence[Dict[str, Any]]]],
        feature_names: List[str],
        num_features: int,
    ) -> Optional[Union[LinearConstraint, NonlinearConstraint, Dict[str, Any], List[Dict[str, Any]]]]:
        if constraints is None: return None
        if isinstance(constraints, (LinearConstraint, NonlinearConstraint)): return constraints
        if isinstance(constraints, dict) and "type" in constraints and "fun" in constraints: return constraints

        specs: List[ConstraintSpec] = []
        if isinstance(constraints, ConstraintSpec): specs = [constraints]
        elif isinstance(constraints, (list, tuple)):
            if len(constraints) == 0: return None
            first = constraints[0]
            if isinstance(first, ConstraintSpec): specs = list(constraints)
            elif isinstance(first, dict) and "coeffs" in first and "operator" in first and "bound" in first:
                specs = [ConstraintSpec(coeffs=c["coeffs"], operator=c["operator"], bound=c["bound"]) for c in constraints]
            elif isinstance(first, (dict, LinearConstraint, NonlinearConstraint)): return list(constraints)
            else: raise OptimizationError(f"Unsupported constraint specification list elements: {type(first)}")
        else: raise OptimizationError(f"Unsupported constraints type: {type(constraints)}")

        A_matrix, lb_vec, ub_vec = [], [], []
        for spec in specs:
            A_matrix.append([float(spec.coeffs.get(col, 0.0)) for col in feature_names])
            for var in spec.coeffs:
                if var not in feature_names and abs(spec.coeffs[var]) > 1e-12:
                    raise OptimizationError(f"Constraint references unknown variable '{var}'. Valid features: {feature_names}")
            op = spec.operator if isinstance(spec.operator, ConstraintOperator) else ConstraintOperator(spec.operator)
            b = float(spec.bound)
            if op == ConstraintOperator.LE: lb_vec.append(-np.inf); ub_vec.append(b)
            elif op == ConstraintOperator.GE: lb_vec.append(b); ub_vec.append(np.inf)
            elif op == ConstraintOperator.EQ: lb_vec.append(b); ub_vec.append(b)

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
        if initial_guess is not None:
            x0 = np.asarray(initial_guess, dtype=float).ravel()
            if len(x0) != num_features: raise OptimizationError(f"Initial guess dim ({len(x0)}) != {num_features}")
            if bounds_list is not None:
                for i, (b_lo, b_hi) in enumerate(bounds_list):
                    if b_lo is not None and x0[i] < b_lo: x0[i] = b_lo
                    if b_hi is not None and x0[i] > b_hi: x0[i] = b_hi
            return x0

        x0 = np.zeros(num_features, dtype=float)
        X_tr = getattr(dataset, "X_train", None) if dataset is not None else getattr(model, "X_train", None)
        for i in range(num_features):
            col_mean = float(np.mean(X_tr[:, i])) if (X_tr is not None and len(X_tr) > 0) else None
            if bounds_list is not None and i < len(bounds_list):
                b_lo, b_hi = bounds_list[i]
                if b_lo is not None and b_hi is not None and np.isfinite(b_lo) and np.isfinite(b_hi): x0[i] = 0.5 * (b_lo + b_hi)
                elif col_mean is not None:
                    val = col_mean
                    if b_lo is not None and np.isfinite(b_lo) and val < b_lo: val = b_lo
                    if b_hi is not None and np.isfinite(b_hi) and val > b_hi: val = b_hi
                    x0[i] = val
                elif b_lo is not None and np.isfinite(b_lo): x0[i] = b_lo
                elif b_hi is not None and np.isfinite(b_hi): x0[i] = b_hi
                else: x0[i] = col_mean if col_mean is not None else 0.0
            else: x0[i] = col_mean if col_mean is not None else 0.0
        return x0

    @classmethod
    def _infer_feature_names(
        cls, model: BaseRSMModel, dataset: Optional[Any], feature_names: Optional[List[str]],
        initial_guess: Optional[ArrayLike], bounds: Optional[Any],
    ) -> List[str]:
        if feature_names is not None: return list(feature_names)
        if dataset is not None and getattr(dataset, "feature_names", None): return list(dataset.feature_names)
        if getattr(model, "feature_names", None): return list(model.feature_names)
        if initial_guess is not None: return [f"x{i + 1}" for i in range(len(np.asarray(initial_guess).ravel()))]
        if bounds is not None and isinstance(bounds, (list, tuple)): return [f"x{i + 1}" for i in range(len(bounds))]
        X_tr = getattr(dataset, "X_train", None) if dataset is not None else getattr(model, "X_train", None)
        if X_tr is not None and len(X_tr) > 0: return [f"x{i + 1}" for i in range(X_tr.shape[1])]
        raise OptimizationError("Cannot infer feature names or input dimensionality for optimization.")

    @classmethod
    def _sample_restart_point(cls, rng: np.random.Generator, x0: np.ndarray, bounds_list: Optional[List[Tuple[Optional[float], Optional[float]]]]) -> np.ndarray:
        x_restart = np.zeros_like(x0)
        for i in range(len(x0)):
            if bounds_list is not None and i < len(bounds_list) and bounds_list[i][0] is not None and bounds_list[i][1] is not None:
                b_lo, b_hi = bounds_list[i]
                if np.isfinite(b_lo) and np.isfinite(b_hi):
                    x_restart[i] = rng.uniform(b_lo, b_hi)
                    continue
            x_restart[i] = x0[i] + rng.normal(0.0, max(1.0, 0.25 * abs(x0[i])))
        return x_restart
