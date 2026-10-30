# Project: SuperRSM Architecture Reorganization & Model Extensibility

## Architecture Overview
SuperRSM is being reorganized from a 3-file monolithic script collection (`rsm_gui.py` [3,039 lines], `rsm_backend.py` [518 lines], `high_d_plotter.py` [242 lines]) into a modular, production-grade Python package (`super_rsm`) structured in 5 strict inward-dependent layers:
- **Layer 0 (`super_rsm.common`)**: Shared typing, data contracts, exceptions, and configuration dataclasses.
- **Layer 1 (`super_rsm.models`)**: Extensible regression model subsystem (`BaseRSMModel` ABC, `ModelRegistry`, standard estimators, dynamic UI metadata descriptors).
- **Layer 2 (`super_rsm.core`)**: Core response surface methodology pipeline (`RSMDataset`, `RSMResult`, `OptimizationEngine`, constraints). Completely decoupled from GUI and graphics libraries, enabling 100% headless execution.
- **Layer 3 (`super_rsm.visualization`)**: Plotting and surface generation service (`MultiContourEngine`, `GridSampler`, typed `PlotConfig`). Pure visualization returning Matplotlib figure/axes without side effects or blocking `plt.show()`.
- **Layer 4 (`super_rsm.gui`)**: Decoupled Model-View-Presenter (MVP) desktop application with non-blocking background workers (`_run_async`), modular views, dialogs, styling, and reusable UI components.
- **Root Shims**: Zero-breaking-change backward compatibility shims (`rsm_gui.py`, `rsm_backend.py`, `high_d_plotter.py`).

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Modular Package Architecture | Target directory tree separating models, core RSM, visualization, GUI, and utilities | M1 | ORIGINAL_REQUEST §R1, Survey E1 |
| 2 | Human & AI Context Optimization | File sizing (<350-400 lines), cohesion, explicit public interfaces, self-contained submodules | M1 | ORIGINAL_REQUEST §R1, Survey E1/E3 |
| 3 | Strict Dependency Hierarchy | Layered import structure guaranteeing zero circular imports and headless execution | M1 | ORIGINAL_REQUEST §R1, Survey E1/E3 |
| 4 | Standard Model Protocol & ABC | `BaseRSMModel` ABC with `fit`, `predict`, `get_metrics`, `get_formula`, `get_coefficients`, `get_feature_importance`, `compute_surface_grid` | M2 | ORIGINAL_REQUEST §R2, Survey E2 |
| 5 | Dynamic Model Registry & Schema | Introspectable `ModelRegistry` with `@register_rsm_model` decorator, hyperparameter specs, and UI hints | M2 | ORIGINAL_REQUEST §R2, Survey E2/E3 |
| 6 | Statistical Diagnostics & ANOVA | Add Adjusted R², MAE, AIC/BIC, p-values, t-stats, and ANOVA table calculation to RSM results | M2 | Survey E2 |
| 7 | Vectorized Surface Grid Evaluation | Replace 40,000-iteration scalar prediction loop with batch matrix prediction ($100\times$ speedup) | M2 | Survey E2 |
| 8 | Model Extension Walkthroughs | Complete, concrete code examples (Polynomial OLS, XGBoost, Gaussian Process) showing how users add models cleanly | M2 | ORIGINAL_REQUEST §R2, Survey E2 |
| 9 | UI Monolith Decomposition | Decompose 3,039-line `rsm_gui.py` into MVP pattern: `views/`, `dialogs/`, `components/`, `controllers/`, `styles/` | M3 | ORIGINAL_REQUEST §R1, Survey E3 |
| 10 | Non-Blocking UI Execution | Background threading (`_run_async`) for long-running fits and optimizations with `root.after` UI updates | M3 | Survey E3 |
| 11 | Visualization Service Decoupling | Decouple `high_d_plotter.py` into `super_rsm.visualization`, removing global side-effects and backend inversion | M3 | Survey E1/E3 |
| 12 | Backward Compatibility Root Shims | Preserve `rsm_backend.py`, `rsm_gui.py`, and `high_d_plotter.py` as transparent wrappers | M4 | ORIGINAL_REQUEST §R3, Survey E1 |
| 13 | Step-by-Step Refactoring Roadmap | Phased migration plan with entry/exit gates, test verification checkpoints, and rollback strategies | M4 | ORIGINAL_REQUEST §R3 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Architectural Design & Package Layout | Package tree, boundaries, layer contracts, dependency flow analysis, context guidelines | Survey | DONE |
| M2 | Regression Model Subsystem & Registry Specification | `BaseRSMModel` ABC, `ModelRegistry`, schema introspection, vectorized grid evaluation, model walkthroughs | M1 | DONE |
| M3 | Core & GUI Decoupling Specification | MVP architecture, async controller, visualization service, dialogs and reusable widgets | M1, M2 | DONE |
| M4 | Comprehensive Implementation Plan Artifact & Roadmap | Full unified artifact integrating M1-M3, phased refactoring roadmap, risk mitigation, verification plan | M1, M2, M3 | IN_PROGRESS |

## Interface Contracts
### `super_rsm.models` ↔ `super_rsm.core`
- Models implement `BaseRSMModel` (or adhere to `RSMModelProtocol`).
- `core.pipeline` requests models via `ModelRegistry.get(name, **kwargs)`.
- Models return typed `ModelMetrics`, unscaled `coefficients: dict[str, float]`, symbolic formula `str`, and accept $(N, D)$ numpy arrays for batch prediction.

### `super_rsm.core` ↔ `super_rsm.gui`
- GUI invokes `AppController.fit_model(dataset_config)` and `AppController.optimize(opt_config)`.
- Core emits progress events/callbacks and returns immutable `RSMResult` dataclass.
- GUI never directly imports Scipy `LinearConstraint` or executes numerical loops.

### `super_rsm.visualization` ↔ `super_rsm.core` / `super_rsm.models`
- Visualization accepts prediction callables or `BaseRSMModel` instances + `PlotConfig`.
- Core never imports visualization modules (enabling headless runs).
- Visualization returns `(fig, axes)` without calling `plt.show()` unless explicitly requested.

## Code Layout (Target Architecture)
```
super_rsm/
├── __init__.py                  # Public exports: rsm_fromDF, RSMResult, ModelRegistry, etc.
├── common/                      # Layer 0: Pure types, contracts, utilities
│   ├── __init__.py
│   ├── types.py                 # Type aliases, Protocol definitions, Enums
│   ├── exceptions.py            # RSMError, ModelRegistrationError, OptimizationError
│   └── config.py                # HyperparameterSpec, ModelMetadata, PlotConfig
├── models/                      # Layer 1: Regression model subsystem
│   ├── __init__.py
│   ├── base.py                  # BaseRSMModel ABC & lifecycle interface
│   ├── registry.py              # ModelRegistry & @register_rsm_model decorator
│   ├── adapters.py              # LegacyBuilderAdapter for backward compatibility
│   ├── gaussian_process.py      # GaussianProcessRSMModel
│   ├── ridge.py                 # RidgeCVRSMModel
│   ├── symbolic.py              # SymbolicRegressorRSMModel
│   └── polynomial_ols.py        # PolynomialOLSModel (classical RSM with ANOVA/p-values)
├── core/                        # Layer 2: Core RSM math, data & optimization
│   ├── __init__.py
│   ├── dataset.py               # RSMDataset (input validation, scaling, splits)
│   ├── result.py                # RSMResult (metrics, formulas, persistence)
│   ├── optimization.py          # OptimizationEngine & LinearConstraint builder
│   └── pipeline.py              # rsm_fromDF pipeline coordinator
├── visualization/               # Layer 3: Plotting and surface generation
│   ├── __init__.py
│   ├── grid.py                  # Vectorized GridSampler (replaces 40k scalar loop)
│   ├── contour.py               # MultiContourEngine (pure figure generation)
│   └── service.py               # VisualizationService
└── gui/                         # Layer 4: Model-View-Presenter desktop GUI
    ├── __init__.py
    ├── app.py                   # Main Application window & event loop
    ├── controller.py            # AppController with async worker thread pool
    ├── state.py                 # AppState (reactive UI state)
    ├── styles/                  # Theme constants, fonts, color palettes
    ├── components/              # ScrollablePanel, KPICard, TreeviewHelper, DynamicParamForm
    ├── dialogs/                 # LinearConstraintDialog, PlotConfigDialog, ExportDialog
    └── views/                   # DataView, ModelConfigView, ResultsView, OptimizationView
```
