# Task Assignment: Explorer M2-2 (Optimization Engine Architecture)

## Context & Objectives
You are Explorer M2-2 for Milestone M2: Core Domain Logic & Optimization Engine.
Your task is to investigate and produce the precise implementation blueprint for:
`super_rsm/core/optimization.py`:
1. `OptimizationResult`:
   - Attributes: `params: np.ndarray`, `fun: float`, `success: bool`, `message: str`, `nit: int`, `raw_result: Any`.
   - Iteration / Unpacking: implement `__iter__` returning `iter((self.params, self.fun))` so that legacy caller code `opt_params, opt_val = result.optimize(...)` unpacks seamlessly!
   - Indexing: `__getitem__` support (`res[0] -> params`, `res[1] -> fun`).
2. `OptimizationEngine`:
   - Static/class methods: `optimize(model, dataset, initial_guess, bounds, constraints, maximize, method, ...)`
   - Objective function: Wraps `model.evaluate_point(p)[0]` or batch `model.predict(p.reshape(1, -1))[0]`. If `maximize=True`, inverts sign (minimizes `-f(x)` and restores `fun = -res.fun`).
   - Bounds handling: Converts dict or list bounds (e.g. `{"x1": (0.0, 5.0)}` or `[(0, 5), (0, 5)]`) to `scipy.optimize.Bounds` or sequence of tuples.
   - Constraint translation: Translates `ConstraintSpec` list (`coeffs`, `operator`, `bound`) to `scipy.optimize.LinearConstraint` or dictionary format compatible with `SLSQP`, `trust-constr`, etc.
   - Initial guess strategy: Default to midpoint of bounds, dataset mean/centroid, or user-provided point.
   - Multi-start strategy: Optional multi-start local search or robust single-start.

## Mandatory Inputs to Read
- ORIGINAL REQUEST: `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\ORIGINAL_REQUEST.md`
- PROJECT PLAN: `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\orchestrator_exec\PROJECT.md`
- PLAN ARTIFACT: `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\SUPER_RSM_REORGANIZATION_PLAN.md` (specifically §4, §5.1 `ConstraintSpec`, §5.5, §9.3)
- EXISTING CODE: `rsm_backend.py` (lines 201–270 for `optimize()` in `rsm_result`), `rsm_gui.py` (constraint matrix assembly in `RSMGui`)
- IMPLEMENTED BASE: `super_rsm/common/config.py` (`ConstraintSpec`, `ConstraintOperator`), `super_rsm/models/base.py`

## Constraints & Requirements
- Read-only exploration. DO NOT modify any source code files.
- Ensure strict file sizing (<250 lines per file).
- Zero dependencies on `tkinter`, `matplotlib`, `seaborn` at module load time.
- Write your structured report to `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\explorer_m2_2\handoff.md`.

## 2026-10-30T04:14:54Z
You are Explorer M2-2 (Optimization Engine Explorer).
Working directory: `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\explorer_m2_2\`.
Investigate and deliver a detailed technical specification and blueprint for `super_rsm/core/optimization.py`.
Write handoff report to `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\explorer_m2_2\handoff.md`.
