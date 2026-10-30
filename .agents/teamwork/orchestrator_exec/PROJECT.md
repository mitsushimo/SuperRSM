# Project: SuperRSM Modular Reorganization & Model Extensibility

## Architecture
- Layer 0: Pure contracts, typing, exceptions, DTOs (`super_rsm.common`)
- Layer 1: Extensible regression model subsystem (`super_rsm.models`)
- Layer 2: Core RSM domain mathematics, dataset management & optimization (`super_rsm.core`)
- Layer 3: Plotting and surface generation service (`super_rsm.visualization`)
- Layer 4: Model-View-Presenter (MVP) Desktop UI (`super_rsm.gui`)
- Layer 5: Automated test suite (`tests/`) & Documentation (`README.md`)

## Code Layout
```
super_rsm/
├── __init__.py
├── common/
│   ├── __init__.py
│   ├── types.py
│   ├── exceptions.py
│   └── config.py
├── models/
│   ├── __init__.py
│   ├── base.py
│   ├── registry.py
│   ├── gaussian_process.py
│   ├── ridge.py
│   ├── symbolic.py
│   └── polynomial_ols.py
├── core/
│   ├── __init__.py
│   ├── dataset.py
│   ├── result.py
│   ├── optimization.py
│   └── pipeline.py
├── visualization/
│   ├── __init__.py
│   ├── settings.py
│   ├── grid.py
│   ├── contour.py
│   └── service.py
└── gui/
    ├── __init__.py
    ├── app.py
    ├── controller.py
    ├── state.py
    ├── styles/
    │   ├── __init__.py
    │   ├── palette.py
    │   └── theme.py
    ├── components/
    │   ├── __init__.py
    │   ├── kpi_card.py
    │   ├── scrollable_panel.py
    │   ├── treeview_helper.py
    │   └── param_form.py
    ├── dialogs/
    │   ├── __init__.py
    │   ├── constraint_dialog.py
    │   └── plot_config_dialog.py
    └── views/
        ├── __init__.py
        ├── header_view.py
        ├── data_view.py
        ├── model_config_view.py
        ├── bounds_view.py
        ├── constraints_view.py
        ├── kpi_strip_view.py
        └── results_view.py
```

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Baseline Test Harness | Pre-refactoring golden outputs and test fixtures | M0 | Plan §9.1 |
| 2 | Common Types & Config | Enums, HyperparameterSpec, ModelMetadata, ConstraintSpec, exceptions | M1 | Plan §3.1, §5.1 |
| 3 | BaseRSMModel ABC | Abstract base class defining fit, predict, evaluate_point, get_formula, get_coefficients | M1 | Plan §5.2 |
| 4 | ModelRegistry | Standard registration mechanism, introspection, metadata retrieval | M1 | Plan §5.3 |
| 5 | Standard Models Implementation | GaussianProcessRSMModel, RidgeCVRSMModel, SymbolicRegressorRSMModel | M1 | Plan §5 |
| 6 | PolynomialOLSModel | Classical RSM model with coded units, pseudo-inversion, ANOVA, p-values | M1 | Plan §6 |
| 7 | RSMDataset & Splitting | Headless dataset container, train/test splitting, array validation | M2 | Plan §4, §9.3 |
| 8 | RSMResult Container | Metric calculation, summary reporting, headless evaluation | M2 | Plan §5.5, §9.3 |
| 9 | OptimizationEngine | Constrained continuous optimization, Scipy constraints, OptimizationResult | M2 | Plan §4, §9.3 |
| 10 | Pipelines | fit_rsm, fit_rsm2, rsm_fromDF headless pipelines | M2 | Plan §4, §9.3 |
| 11 | PlotSettings & Profiles | Dataclass settings, JSON serialization without side-effects | M3 | Plan §7.1, §9.4 |
| 12 | Vectorized GridSampler | Fast batch evaluation (sub-50ms), multi-slice coordinate generation | M3 | Plan §7.1, §9.4 |
| 13 | MultiContourEngine & Service | Pure Matplotlib figure generator, scoped styling without global side effects | M3 | Plan §7.1, §9.4 |
| 14 | GUI Styles & Components | Palette, theme, KPICard, ScrollablePanel, TreeviewHelper, ParamForm | M4 | Plan §4, §9.5 |
| 15 | GUI Dialogs & Views | ConstraintDialog, PlotConfigDialog, modular view panels | M4 | Plan §4, §9.5, §9.6 |
| 16 | AppState & Async Controller | Reactive state, non-blocking background threading, task cancellation | M4 | Plan §7.3, §9.5 |
| 17 | Main Application Shell | RSMApp window lifecycle, event wiring | M4 | Plan §4, §9.6 |
| 18 | Clean Entrypoints & Shims | Direct CLI/GUI entrypoints and clean root shims for easy invocation | M5 | Plan §9.7 & User Feedback |
| 19 | Comprehensive Automated Tests | Full unit and integration tests across all modules | M5 | Plan §9, Request |
| 20 | Updated Documentation | Updated README.md with modular architecture and model extension guide | M5 | Plan §3, Request |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Foundations, Baseline & Models | `tests/test_baseline.py`, `super_rsm.common` (types, config, exceptions), `super_rsm.models` (base, registry, gaussian_process, ridge, symbolic, polynomial_ols), `tests/test_models.py` | none | DONE |
| M2 | Core Domain & Optimization | `super_rsm.core` (dataset, result, optimization, pipeline) + `tests/test_core.py` | M1 | DONE |
| M3 | Visualization Service | `super_rsm.visualization` (settings, grid, contour, service) + `tests/test_visualization.py` | M2 | IN_PROGRESS |
| M4 | GUI MVP Architecture | `super_rsm.gui` (styles, components, dialogs, views, state, controller, app) + `tests/test_gui.py` | M3 | PLANNED |
| M5 | Integration, Shims, E2E & Docs | Clean root entrypoints, comprehensive E2E test suite, updated README.md | M4 | PLANNED |

## Interface Contracts
### `super_rsm.common` ↔ `super_rsm.models`
- Models implement `BaseRSMModel`
- Hyperparameters described using `HyperparameterSpec`
- Metadata defined using `ModelMetadata`
- Custom exceptions derive from `SuperRSMError`

### `super_rsm.models` ↔ `super_rsm.core`
- `RSMDataset` supplies `X_train`, `y_train`, `X_test`, `y_test`, feature/target names
- `BaseRSMModel.fit(dataset)` returns fitted model instance
- `BaseRSMModel.evaluate_point(point)` returns `(mean, std_err)`
- `OptimizationEngine` accepts `BaseRSMModel` and `RSMDataset`
- `RSMResult` wraps `BaseRSMModel`, `RSMDataset`, and computed `ModelMetrics`

### `super_rsm.core` ↔ `super_rsm.visualization`
- `VisualizationService.visualize_result(result, config, ...)` receives `RSMResult`
- `GridSampler` queries `model.evaluate_batch(X_batch)` for vectorized fast evaluation

### `super_rsm.gui` ↔ `super_rsm.core` & `super_rsm.visualization`
- `AppController` runs model fitting and optimization asynchronously via `_run_async`
- `AppState` stores current dataset, model metadata, parameters, optimization results
- Views communicate strictly with `AppState` and `AppController`, never importing heavy math directly
