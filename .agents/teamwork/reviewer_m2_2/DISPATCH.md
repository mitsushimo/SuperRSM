# Task Assignment: Reviewer M2-2 (Optimization & Numerical Correctness Reviewer)

## Context & Objectives
You are Reviewer M2-2 for Milestone M2: Core Domain Logic & Optimization Engine.
Your task is to independently review mathematical and numerical implementation correctness in:
- `super_rsm/core/optimization.py`
- `super_rsm/core/result.py`
- `super_rsm/core/pipeline.py`

## Review Criteria
1. **Optimization Inversion**: Verify that when `maximize=True`, the objective function minimizes `-f(p)` and restores `opt_fun = -raw_fun`.
2. **Bounds Handling**: Verify bounds conversion from dict (`{"x1": (0, 5)}`), tuple list, or Scipy `Bounds`, and bounds validation ($b_{lo} \le b_{hi}$).
3. **ConstraintSpec Translation**: Verify compilation of `ConstraintSpec` lists (`LE`, `GE`, `EQ`) into `scipy.optimize.LinearConstraint` matrix $(A, lb, ub)$.
4. **Initial Guess**: Verify bounds midpoint / centroid clamping so initial guesses never violate bounds.
5. **2-Tuple Unpacking Protocol**: Verify `OptimizationResult.__iter__` returns `iter((self.params, self.fun))` and `__getitem__` works for indices 0 and 1.
6. **Result Metrics & Diagnostics**: Verify that `RSMResult` exposes metrics (`r2`, `rmse`, `mse`, `mae`, `adj_r2`, `aic`, `bic`), formulas, unscaled coefficients, and ANOVA summary.
7. **Test Verification**: Run `python -m pytest tests/test_core.py` and `python -m pytest tests/`.

## Mandatory Inputs to Read
- ORIGINAL REQUEST: `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\ORIGINAL_REQUEST.md`
- WORKER HANDOFF: `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\worker_m2\handoff.md`
- PROJECT PLAN: `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\orchestrator_exec\PROJECT.md`

Deliver your structured review report to `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\reviewer_m2_2\handoff.md`.
End with a clear binary verdict: **APPROVE** or **REQUEST_CHANGES**.


## 2026-10-30T04:37:47Z
You are Reviewer M2-2 (Optimization & Numerical Correctness Reviewer).
Your working directory is `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\reviewer_m2_2\`.
Read your task dispatch at `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\reviewer_m2_2\DISPATCH.md`.
Read the mandatory original request at `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\ORIGINAL_REQUEST.md`.
Read the project scope at `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\orchestrator_exec\PROJECT.md`.
Read the worker handoff report at `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\worker_m2\handoff.md`.

Review the mathematical correctness of `super_rsm/core/optimization.py`, `super_rsm/core/result.py`, and `super_rsm/core/pipeline.py`.
Verify sign inversion on maximization, bounds conversion, ConstraintSpec translation, initial guess midpoint clamping, and 2-tuple unpacking protocol (`params, val = result.optimize(...)`).
Run `python -m pytest tests/test_core.py` and `python -m pytest tests/`.

Write your full review report to `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\reviewer_m2_2\handoff.md`.
Deliver a clear verdict: APPROVE or REQUEST_CHANGES.
Send a completion message back to the orchestrator when finished.
