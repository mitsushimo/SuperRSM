# Task Assignment: Worker M3 (Visualization Service Implementation)

## Context & Objectives
You are Worker M3 for Milestone M3: Visualization Service.
Your task is to implement the entire `super_rsm.visualization` package and comprehensive automated unit tests in `tests/test_visualization.py` using the specifications and blueprints prepared by Explorers M3-1, M3-2, and M3-3.

## Exclusive File Ownership
You exclusively own and may create/edit these files:
- `super_rsm/visualization/__init__.py`
- `super_rsm/visualization/settings.py`
- `super_rsm/visualization/grid.py`
- `super_rsm/visualization/contour.py`
- `super_rsm/visualization/service.py`
- `tests/test_visualization.py`

DO NOT modify any files in `super_rsm/common/`, `super_rsm/models/`, `super_rsm/core/`, or existing test files unless fixing an import bug.

## Mandatory Inputs to Read Before Writing Code
1. `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\ORIGINAL_REQUEST.md`
2. `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\explorer_m3_1\handoff.md` (Blueprints for `settings.py` and `grid.py`)
3. `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\explorer_m3_2\handoff.md` (Blueprint for `contour.py`)
4. `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\explorer_m3_3\handoff.md` (Blueprints for `service.py`, `__init__.py`, and `test_visualization.py`)

## Core Requirements & Constraints
1. **Strict File Sizing**: Each file must remain strictly <250 lines of code.
2. **ZERO Global Side-Effects**: NO global `sns.set_theme(style="whitegrid")` or global matplotlib rcParams mutation at module load time! All plot styling MUST use scoped contexts (`with plt.rc_context(settings.to_rc_params()):`).
3. **Headless Execution**: `MultiContourEngine` and `VisualizationService` must generate and return `(fig, axes)` without calling blocking `plt.show()` when `show=False` or when running headlessly.
4. **Vectorized Mesh Evaluation**: Integrate with `BaseRSMModel.compute_surface_grid()` or batch evaluation ensuring 10,000 points evaluate in <50ms.
5. **Scatter Point Filtering**: Spatially filter observations that project onto sliced coordinates within tolerance.
6. **Comprehensive Unit Tests**: In `tests/test_visualization.py`, write tests covering:
   - Verification that importing `super_rsm.visualization` does NOT alter global `matplotlib.rcParams`.
   - 10,000 points grid evaluation benchmark (<50ms).
   - Headless figure generation (returning valid Figure and Axes).
   - End-to-end integration with `RSMResult.visualize_rsm()`.
   - Scatter point overlay and uncertainty visualization modes.
   - PlotSettings JSON serialization/deserialization.
7. **Test Execution**: Run `python -m pytest tests/test_visualization.py` and `python -m pytest tests/` and verify all tests pass (existing 85 tests + new visualization tests).

## MANDATORY INTEGRITY WARNING
> DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Delivery
Write your handoff report to `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\worker_m3\handoff.md`.
Include build/compilation check and exact pytest results.
Send a completion message back to the orchestrator when finished.


## 2026-10-30T05:09:48Z
You are Worker M3 (Visualization Service Implementation Worker).
Your working directory is `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\worker_m3\`.
Read your task dispatch at `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\worker_m3\DISPATCH.md`.
Read the mandatory original request at `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\ORIGINAL_REQUEST.md`.
Read the blueprints from the 3 Explorers:
- `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\explorer_m3_1\handoff.md` (settings.py, grid.py)
- `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\explorer_m3_2\handoff.md` (contour.py)
- `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\explorer_m3_3\handoff.md` (service.py, __init__.py, test_visualization.py)

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Implement:
1. `super_rsm/visualization/settings.py` (<250 lines)
2. `super_rsm/visualization/grid.py` (<250 lines)
3. `super_rsm/visualization/contour.py` (<250 lines)
4. `super_rsm/visualization/service.py` (<250 lines)
5. `super_rsm/visualization/__init__.py` (<50 lines)
6. `tests/test_visualization.py` (<250 lines)

Run tests (`python -m pytest tests/test_visualization.py` and `python -m pytest tests/`).
Write your handoff report to `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\worker_m3\handoff.md`.
Send a completion message back to the orchestrator when finished.
