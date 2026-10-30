# Task Assignment: Explorer M2-3 (Pipeline Orchestration & Test Suite Architecture)

## Context & Objectives
You are Explorer M2-3 for Milestone M2: Core Domain Logic & Optimization Engine.
Your task is to investigate and produce the precise implementation blueprint for:
1. `super_rsm/core/pipeline.py`:
   - Headless pipelines:
     * `fit_rsm(dataset: RSMDataset, method: str = "Polynomial OLS", **hyperparameters) -> RSMResult`
     * `fit_rsm2(X_train, y_train, X_test, y_test, method="Polynomial OLS", feature_names=None, **kwargs) -> RSMResult`
     * `rsm_fromDF(df: pd.DataFrame, input_columns: List[str], output_column: str, method: str = "Polynomial OLS", test_size: float = 0.2, random_state: Optional[int] = None, **kwargs) -> RSMResult`
   - Clean, modern design without legacy adapter bloat.
2. `super_rsm/core/__init__.py`:
   - Re-exports: `RSMDataset`, `RSMResult`, `OptimizationEngine`, `OptimizationResult`, `fit_rsm`, `fit_rsm2`, `rsm_fromDF`.
3. `tests/test_core.py`:
   - Comprehensive test design:
     * Dataset splitting, shape verification, feature name inference, invalid data error handling.
     * RSMResult metrics, formula, coefficient accessors, headless evaluation.
     * Optimization with unconstrained, bounded, and linear inequality constraints (`ConstraintSpec`).
     * 2-tuple unpacking (`params, val = result.optimize(...)`).
     * Full headless verification (mocking/asserting no tkinter or matplotlib imports).

## Mandatory Inputs to Read
- ORIGINAL REQUEST: `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\ORIGINAL_REQUEST.md`
- PROJECT PLAN: `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\orchestrator_exec\PROJECT.md`
- PLAN ARTIFACT: `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\SUPER_RSM_REORGANIZATION_PLAN.md` (specifically §4, §5.5, §9.3)
- EXISTING CODE: `rsm_backend.py` (lines 422–468 for `fit_rsm2` and `rsm_fromDF`)
- IMPLEMENTED BASE: `super_rsm/common/`, `super_rsm/models/`

## Constraints & Requirements
- Read-only exploration. DO NOT modify any source code files.
- Ensure strict file sizing (<250 lines per file).
- Zero dependencies on `tkinter`, `matplotlib`, `seaborn` at module load time.
- Write your structured report to `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\explorer_m2_3\handoff.md`.
