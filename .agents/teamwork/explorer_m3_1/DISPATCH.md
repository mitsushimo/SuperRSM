# Task Assignment: Explorer M3-1 (PlotSettings & GridSampler Architecture)

## Context & Objectives
You are Explorer M3-1 for Milestone M3: Visualization Service.
Your task is to investigate and produce the implementation blueprints for:
1. `super_rsm/visualization/settings.py`:
   - `PlotSettings` dataclass encapsulating:
     * Color palettes, colormaps (`cmap`, default "viridis"), contour levels (default 20), line styles.
     * Alpha transparencies, title font size, axis label font sizes, tick label sizes.
     * DPI settings, figure dimensions (`fig_width`, `fig_height`), grid display (`show_grid: bool`).
     * JSON serialization and deserialization (`to_dict()`, `from_dict()`, `to_json()`, `from_json()`).
     * Built-in preset profiles (e.g., "publication", "presentation", "dark", "default").
2. `super_rsm/visualization/grid.py`:
   - `GridSampler`:
     * Coordinates batch grid generation across multi-dimensional parameter spaces.
     * Integrates with `SurfaceGridConfig` and `model.compute_surface_grid()` / `model.predict()`.
     * Vectorized batch evaluation guaranteeing sub-50ms latency for 10,000 points.
     * Scatter point spatial filtering: extracts observation points from `RSMDataset.X_train` or `X_scatter` that fall near the slice coordinates $(p, q)$ within slice tolerance.

## Mandatory Inputs to Read
- ORIGINAL REQUEST: `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\ORIGINAL_REQUEST.md`
- PROJECT PLAN: `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\orchestrator_exec\PROJECT.md`
- PLAN ARTIFACT: `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\SUPER_RSM_REORGANIZATION_PLAN.md` (§7.1, §9.4)
- EXISTING CODE: `high_d_plotter.py` (lines 17–108 for `default_plot_settings` and `validate_multi_contour_inputs`), `super_rsm/models/base.py` (`SurfaceGridConfig`, `SurfaceGridResult`)

## Constraints & Requirements
- Read-only exploration. DO NOT modify any source code files.
- Ensure strict file sizing (<250 lines per file).
- ZERO global side-effects (no global `sns.set_theme`).
- Write your structured report to `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\explorer_m3_1\handoff.md`.
