# Task Assignment: Forensic Auditor M3 (Integrity Verification)

## Context & Objectives
You are the Forensic Integrity Auditor for Milestone M3: Visualization Service.
Your task is to independently audit all code authored in `super_rsm/visualization/` and `tests/test_visualization.py` to ensure complete integrity, genuine implementation, and adherence to project rules.

## Mandatory Audit Checks
1. **No Cheating / No Hardcoding**:
   - Verify that mesh coordinate grids ($X, Y, Z, U$), contour levels, figure dimensions, and scatter points are dynamically computed from the underlying model and data (no pre-baked arrays).
   - Verify that `GridSampler` genuinely calls model prediction methods.
2. **Zero Global Side-Effects**:
   - Check AST imports in `super_rsm/visualization/`: verify zero calls to `sns.set_theme()` or direct top-level `matplotlib.rcParams[...] = ...` assignments.
   - Verify that all styling runs inside `with plt.rc_context(rc_params):`.
3. **Headless Execution**:
   - Verify that default methods do NOT call blocking `plt.show()` when `show=False` or running headlessly.
4. **File Sizing Limit**:
   - Verify that every file in `super_rsm/visualization/` and `tests/test_visualization.py` is <250 lines (<50 lines for `__init__.py`).

Deliver your forensic audit report to `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\auditor_m3_1\handoff.md`.
End with a clear binary verdict: **CLEAN** or **INTEGRITY VIOLATION**.
⚠️ HARD VETO: If you detect hardcoding, facade implementations, or circumvented requirements, issue an INTEGRITY VIOLATION verdict.

## 2026-10-30T05:23:29Z
You are the Forensic Integrity Auditor for Milestone M3: Visualization Service.
Your working directory is `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\auditor_m3_1\`.
Read your task dispatch at `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\auditor_m3_1\DISPATCH.md`.
Read the mandatory original request at `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\ORIGINAL_REQUEST.md`.
Read the project scope at `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\orchestrator_exec\PROJECT.md`.
Read the worker handoff report at `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\worker_m3\handoff.md`.

Perform comprehensive forensic integrity audit on `super_rsm/visualization/` and `tests/test_visualization.py`:
1. Check for hardcoding: verify that grids ($X, Y, Z, U$), contour levels, figure dimensions, and scatter points are dynamically computed from underlying models and data (no pre-baked or hardcoded arrays).
2. Check zero global side-effects: AST inspection must confirm zero top-level calls to `sns.set_theme()` or direct top-level `matplotlib.rcParams[...] = ...` mutations. Verify that styling runs inside `with plt.rc_context(rc_params):`.
3. Check headless execution: verify default rendering returns `(fig, axes)` without calling blocking `plt.show()`.
4. Check file sizing limits: verify all authored files in `super_rsm/visualization/` and `tests/test_visualization.py` are <250 lines (<50 lines for `__init__.py`).

Write your forensic audit report to `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\auditor_m3_1\handoff.md`.
Deliver a clear binary verdict: CLEAN or INTEGRITY VIOLATION.
⚠️ HARD VETO: If you detect hardcoding, facade implementations, or circumvented requirements, issue an INTEGRITY VIOLATION verdict.
Send a completion message back to the orchestrator when finished.
