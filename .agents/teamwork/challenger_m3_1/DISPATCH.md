# Task Assignment: Challenger M3-1 (Visualization Latency & Scoped Styling Challenger)

## Context & Objectives
You are Challenger M3-1 for Milestone M3: Visualization Service.
Your task is to adversarially stress-test `super_rsm/visualization/`:
1. **Global Mutation Attack**: Emulate multiple sequential rendering calls across different presets ("dark", "publication", custom) and verify in a standalone test that global `matplotlib.rcParams` is bit-for-bit unchanged before and after.
2. **Extreme Grid Performance**: Test mesh evaluations at scaling thresholds: 10,000 points, 25,000 points, and 40,000 points (the legacy loop size) across different models (`PolynomialOLSModel`, `GaussianProcessRSMModel`, `RidgeCVRSMModel`). Verify that batch prediction avoids freezing.
3. **Invalid Config Attacks**: Test mismatched dimensions, colliding axis assignments, invalid colormaps, negative levels, and empty slice values. Ensure appropriate errors are raised.

Write an empirical test script under `tests/` (e.g. `tests/test_challenger_visualization_stress.py`), run via `python -m pytest`, and measure results.
Deliver your report to `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\challenger_m3_1\handoff.md`.
End with a clear binary verdict: **APPROVE** or **REQUEST_CHANGES**.

## 2026-10-30T05:23:15Z
You are Challenger M3-1 (Visualization Latency & Scoped Styling Challenger).
Your working directory is `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\challenger_m3_1\`.
Read your task dispatch at `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\challenger_m3_1\DISPATCH.md`.
Read the mandatory original request at `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\ORIGINAL_REQUEST.md`.
Read the project scope at `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\orchestrator_exec\PROJECT.md`.
Read the worker handoff report at `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\worker_m3\handoff.md`.

Adversarially stress-test `super_rsm/visualization/`:
1. Global Mutation Attack: Sequentially apply multiple preset profiles and custom configurations; verify in a standalone subprocess or test that global `matplotlib.rcParams` is bit-for-bit identical before and after.
2. Grid Performance: Test evaluation speeds across 10,000, 25,000, and 40,000 grid points across different models.
3. Invalid Config Attacks: Test axis index collisions, out-of-bounds indices, and invalid parameters.
Write an empirical test script under `tests/` (e.g. `tests/test_challenger_visualization_stress.py`), execute via `python -m pytest`, and measure results.

Write your full report to `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\challenger_m3_1\handoff.md`.
Deliver a clear verdict: APPROVE or REQUEST_CHANGES.
Send a completion message back to the orchestrator when finished.
