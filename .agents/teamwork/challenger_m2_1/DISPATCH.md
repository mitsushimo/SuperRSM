# Task Assignment: Challenger M2-1 (Optimization & Constraint Stress Challenger)

## Context & Objectives
You are Challenger M2-1 for Milestone M2: Core Domain Logic & Optimization Engine.
Your task is to adversarially stress-test `super_rsm/core/optimization.py` and `OptimizationEngine`.

## Empirical Verification Tasks
1. **Adversarial Bounds**: Test optimization with single-point bounds (`b_lo == b_hi`), negative bounds, infinite bounds, and inverted bounds (must raise `OptimizationError` or `ValueError`).
2. **Linear Constraint Combinations**: Test multiple interacting `ConstraintSpec` inequalities (`<=`, `>=`, `==`), redundant constraints, and infeasible constraints.
3. **Maximization vs Minimization**: Empirically verify with a known quadratic function (e.g., $f(x) = -(x_1 - 2)^2 - (x_2 - 3)^2 + 10$) that maximization finds $(2, 3)$ with value $+10$, and minimization finds the boundary minimum.
4. **Unpacking & Interoperability**: Empirically verify that `params, val = result.optimize(...)` returns `np.ndarray` and `float`, and that `len(opt) == 2`, `opt[0]`, `opt[1]` all operate identically to a 2-tuple.
5. Create a standalone test script under `tests/` (e.g. `tests/test_challenger_optimization.py`), run it via `python -m pytest`, and measure results.

## Mandatory Inputs to Read
- ORIGINAL REQUEST: `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\ORIGINAL_REQUEST.md`
- WORKER HANDOFF: `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\worker_m2\handoff.md`
- PROJECT PLAN: `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\orchestrator_exec\PROJECT.md`

Deliver your structured stress report to `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\challenger_m2_1\handoff.md`.
End with a clear binary verdict: **APPROVE** or **REQUEST_CHANGES**.


## 2026-10-30T04:37:53Z
You are Challenger M2-1 (Optimization & Constraint Stress Challenger).
Your working directory is `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\challenger_m2_1\`.
Read your task dispatch at `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\challenger_m2_1\DISPATCH.md`.
Read the mandatory original request at `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\ORIGINAL_REQUEST.md`.
Read the project scope at `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\orchestrator_exec\PROJECT.md`.
Read the worker handoff report at `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\worker_m2\handoff.md`.

Adversarially stress-test `super_rsm/core/optimization.py`:
- Test tight bounds, single-point bounds, inverted bounds (must raise error).
- Test multiple linear constraints (ConstraintSpec with LE, GE, EQ).
- Empirically verify maximization vs minimization with known test functions.
- Verify 2-tuple unpacking (`params, val = opt`), `len(opt) == 2`, `opt[0]`, `opt[1]`.
Write an empirical test script under `tests/` (e.g. `tests/test_challenger_optimization.py`), execute via `python -m pytest`, and measure results.

Write your full stress report to `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\challenger_m2_1\handoff.md`.
Deliver a clear verdict: APPROVE or REQUEST_CHANGES.
Send a completion message back to the orchestrator when finished.
