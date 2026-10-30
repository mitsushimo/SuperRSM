# Task Assignment: Worker M2 (Core Domain Logic & Optimization Implementation)

## Context & Objectives
You are Worker M2 for Milestone M2: Core Domain Logic & Optimization Engine.
Your task is to implement the entire `super_rsm.core` package and comprehensive automated unit tests in `tests/test_core.py` using the specifications and blueprints prepared by Explorers M2-1, M2-2, and M2-3.

## Exclusive File Ownership
You exclusively own and may create/edit these files:
- `super_rsm/core/__init__.py`
- `super_rsm/core/dataset.py`
- `super_rsm/core/result.py`
- `super_rsm/core/optimization.py`
- `super_rsm/core/pipeline.py`
- `tests/test_core.py`

DO NOT modify any files in `super_rsm/common/`, `super_rsm/models/`, or other test files unless fixing an import bug.

## Mandatory Inputs to Read Before Writing Code
1. `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\ORIGINAL_REQUEST.md`
2. `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\explorer_m2_1\handoff.md` (Blueprints for `dataset.py` & `result.py`)
3. `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\explorer_m2_2\handoff.md` (Blueprint for `optimization.py`)
4. `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\explorer_m2_3\handoff.md` (Blueprints for `pipeline.py`, `__init__.py`, and `test_core.py`)

## Core Requirements & Constraints
1. **Strict File Sizing**: Each file must remain <250 lines of code.
2. **Headless Execution**: ZERO load-time imports of `tkinter`, `matplotlib`, or `seaborn` in `super_rsm/core/`.
3. **Dual Unpacking Protocol**: `OptimizationResult` MUST implement `__iter__` returning `iter((self.params, self.fun))` so that `params, val = result.optimize(...)` unpacks seamlessly as a 2-tuple.
4. **Sign Inversion in Optimization**: When `maximize=True`, solve `minimize(-f(x))` and return `fun = -res.fun`.
5. **Constraint Translation**: `OptimizationEngine.translate_constraints()` compiles `ConstraintSpec` lists into Scipy `LinearConstraint` without requiring the GUI to do constraint math.
6. **Bounds & Centroid Initial Guess**: Feasible starting point clamped to bounds or midpoint if not provided.
7. **Comprehensive Unit Tests**: In `tests/test_core.py`, write tests covering:
   - `RSMDataset` splitting, validation, NaN rejection.
   - `RSMResult` metrics, summary, formula/coeff accessors, point evaluation.
   - `OptimizationEngine` unconstrained, bounded, and linear inequality constraints with 2-tuple unpacking.
   - `fit_rsm`, `fit_rsm2`, `rsm_fromDF` pipelines.
   - Headless verification (asserting no tkinter or matplotlib imports).
8. **Test Execution**: Run `python -m pytest tests/` and verify all tests pass (existing 41 tests + new tests in `test_core.py`).

## MANDATORY INTEGRITY WARNING
> DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Delivery
Write your handoff report to `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\worker_m2\handoff.md`.
Include build/compilation check and exact pytest results.
Send a completion message back to the orchestrator when finished.

## 2026-10-30T04:23:23Z
You are Worker M2 (Core Domain Logic & Optimization Implementation Worker).
Your working directory is `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\worker_m2\`.
Read your task dispatch at `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\worker_m2\DISPATCH.md`.
Read the mandatory original request at `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\ORIGINAL_REQUEST.md`.
Read the blueprints from the 3 Explorers:
- `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\explorer_m2_1\handoff.md` (dataset.py, result.py)
- `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\explorer_m2_2\handoff.md` (optimization.py)
- `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\explorer_m2_3\handoff.md` (pipeline.py, __init__.py, test_core.py)

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Implement:
1. `super_rsm/core/dataset.py` (<250 lines)
2. `super_rsm/core/result.py` (<250 lines)
3. `super_rsm/core/optimization.py` (<250 lines)
4. `super_rsm/core/pipeline.py` (<250 lines)
5. `super_rsm/core/__init__.py` (<50 lines)
6. `tests/test_core.py` (<250 lines)

Run tests (`python -m pytest tests/test_core.py` and `python -m pytest tests/`).
Write your handoff report to `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\worker_m2\handoff.md`.
Send a completion message back to the orchestrator when finished.

