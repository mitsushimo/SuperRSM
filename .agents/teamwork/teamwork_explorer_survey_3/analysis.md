# SuperRSM GUI, Plotting & Architecture Decoupling Survey

**Author**: Explorer 3 (GUI, Plotting & Architecture Decoupling Explorer)  
**Date**: 2026-10-30  
**Scope**: In-depth analysis of `rsm_gui.py` (121 KB, 3,039 lines), `high_d_plotter.py` (11.6 KB, 242 lines), backend interaction patterns, and architecture decoupling strategy for SuperRSM.

---

## 1. Executive Summary & Codebase Inventory

SuperRSM is a specialized scientific Python application providing Response Surface Methodology (RSM) surrogate modeling, constrained numerical optimization, and multi-dimensional contour visualization.

### Current Codebase Inventory

| File | Size (Bytes) | Lines | Primary Responsibility | Architectural Concerns |
|---|---|---|---|---|
| `rsm_gui.py` | 121,563 (~121 KB) | 3,039 | Entire Tkinter GUI application, styling, dialogs, state tracking, calculation triggers, and report generation | Monolithic god-class; tight coupling between UI widgets, domain state, and backend calculations; synchronous GUI blocking. |
| `high_d_plotter.py` | 11,612 (~11.6 KB) | 242 | Multi-contour subplot plotting engine over multidimensional parameter spaces | Procedural script; imports `seaborn` with global theme side-effect; calls blocking `plt.show()`; returns no figure objects; untyped settings dictionary. |
| `rsm_backend.py` | 21,332 (~21 KB) | 519 | Model fitting pipeline (`rsm_fromDF`), model registry, optimization wrapper, and `rsm_result` class | Directly imports `high_d_plotter` inside backend; embeds plotting execution within domain result object; limited model interface. |
| `requirements.txt` | 312 | 19 | Dependencies: numpy, scipy, pandas, openpyxl, scikit-learn, gplearn, matplotlib, seaborn | Standard Python stack; GUI uses built-in `tkinter`. |
| `sample_data.csv` | 5,605 | 102 | 3-column benchmark dataset (`x1`, `x2`, `y`) | Suitable for automated integration and UI regression tests. |

---

## 2. In-Depth Structural Breakdown of `rsm_gui.py` (3,039 Lines)

`rsm_gui.py` contains 3,039 lines in a single file containing two classes: `LinearConstraintDialog(tk.Toplevel)` and `RSMGui(tk.Tk)`.

### 2.1 Functional Section Inventory

```
rsm_gui.py (3,039 lines total)
│
├── Lines 1–55     : Imports & Theme Palette Constants (PALETTE dict, colormaps, line styles, markers)
├── Lines 56–307   : Fonts & TTK Styles (configure_ttk_styles, platform font resolution, clam theme rules)
├── Lines 308–347  : Expression Formatter Helper (format_linear_expression)
├── Lines 348–574  : LinearConstraintDialog Class (Modal Toplevel for ∑ cᵢ·xᵢ ≤ b with live preview)
├── Lines 575–600  : RSMGui.__init__ (App setup, instance variables, state container initialization)
├── Lines 601–1319 : RSMGui.create_widgets (Massive layout construction method: 719 lines!)
│   ├── 601–632    : Header bar & dataset status pill
│   ├── 639–664    : Step 1 — Dataset Source file selector bar
│   ├── 665–673    : PanedWindow setup (left deck vs right notebook)
│   ├── 678–754    : Step 2 — Variable Selection (input listbox, target response combo)
│   ├── 755–833    : Step 3 — Model & Fit Settings (method combo, degree/test_ratio spinboxes, fit button)
│   ├── 834–901    : Step 4 — Optimization Goal & Bounds (goal combo, canvas with dynamic entries)
│   ├── 902–964    : Step 5 — Linear Constraints (treeview, add/edit/delete/clear buttons)
│   ├── 965–988    : Action buttons bar ("Run Optimization", "Configure Plot...")
│   ├── 993–1011   : KPI Summary Strip (4 metric cards: R², RMSE, Min/Max Output, Status)
│   ├── 1012–1095  : Results Notebook Tab 1 — Optimal Solution & Constraint Verification Tables
│   ├── 1096–1133  : Results Notebook Tab 2 — Model Equation & Full Text Report
│   ├── 1134–1295  : Results Notebook Tab 3 — Evaluate Model at Custom Points & History Table
│   └── 1296–1319  : Bottom Status Bar
├── Lines 1320–1548: Helper UI Builders & State Callbacks (KPI card builder, fit staleness checker, selection clearers)
├── Lines 1549–1686: Point Evaluation Helpers (fill from mean/optimal, point evaluation trigger, history double-click)
├── Lines 1687–1756: Linear Constraints Management (add, edit, delete, clear, refresh treeview)
├── Lines 1757–1953: Data Loading & Column Selection (browse_file, load_data, on_input_select dynamic frame builder)
├── Lines 1954–2358: Model Fitting & Optimization Execution (fit_model, run_optimization, report formatting)
└── Lines 2359–3038: Plot Configuration Window & Plot Generation (open_plot_config, generate_plot, profile save/load)
```

### 2.2 UI Component & Widget Inventory

- **Notebooks & Tabs**:
  - **Results Notebook** (Main Right Pane): 3 Tabs:
    1. *Optimal Solution & Constraints* (Parameters Treeview + Constraint Verification Treeview)
    2. *Model Equation & Full Report* (Monospace Text widget + Copy to Clipboard)
    3. *Evaluate Model* (Custom inputs canvas + Prediction Readout + Evaluation History Treeview)
  - **Plot Configuration Notebook** (Modal Dialog Window): 3 Tabs:
    1. *Parameter Roles & Ranges* (Dynamic roles: X-Axis, Y-Axis, Row P, Col Q, Fixed)
    2. *Titles & Axis Labels* (Plot title, axis labels, colorbar label, P/Q prefixes/suffixes)
    3. *Styling, Scatter & Uncertainty* (Colormap, fill levels, line levels, scatter overlay, uncertainty mapping)
- **LabelFrames & Cards**:
  - 5 sequential left-pane configuration decks (numbered 1 through 5).
  - 4 KPI summary cards (R² fit score, Test RMSE, Optimal Response, Model/Optimizer status).
- **Treeviews**:
  - 4 distinct `ttk.Treeview` tables: Active Constraints table, Optimal Parameters table, Constraint Verification table, and Evaluation History table.
- **Scrollable Canvas Panels**:
  - 4 separate implementations of `tk.Canvas` + `ttk.Scrollbar` + inner `ttk.Frame` with window `<Configure>` and `<MouseWheel>` event handlers:
    1. Variable coefficients in `LinearConstraintDialog` (lines 441–475)
    2. Parameter bounds in left pane Step 4 (lines 876–900)
    3. Parameter point inputs in Tab 3 (lines 1169–1197)
    4. Parameter roles in Plot Configuration dialog (lines 2444–2467)
- **Event Handlers & Traces**:
  - Over 20 event bindings: `<<ListboxSelect>>`, `<<ComboboxSelected>>` (on 5 dropdowns), `<Double-1>` treeview activations, canvas resize hooks, and Tkinter variable write traces (`trace_add("write", ...)`).

### 2.3 Why `rsm_gui.py` Reached 121 KB (Monolith Causes)

1. **God-Class Anti-Pattern**: All logic from styling, widget construction, data loading, constraint math, SciPy optimization parameter translation, model evaluation, report text formatting, dialog management, and JSON profile serialization resides in `RSMGui`.
2. **Duplicated Canvas Scroll Boilerplate**: Each of the 4 scrollable entry panels repeats ~40 lines of boilerplate for canvas window creation, scrollregion bbox updating, and mousewheel handling.
3. **Inlined Dialog Subsystems**:
   - `LinearConstraintDialog` is 227 lines.
   - `open_plot_config` and its associated helpers (`generate_plot`, `save_plot_settings`, `load_plot_settings`, `_update_plot_role_inputs`) comprise **680 lines** (lines 2359–3038). This is an entire application dialog crammed into methods of `RSMGui`.
4. **Presentation Mixed with Domain Logic**: The GUI directly builds Scipy matrices ($A, lb, ub$) for `LinearConstraint`, validates bounding intervals, calculates data statistics (means, ranges, quartiles), and formats mathematical expressions.

---

## 3. GUI-Backend Interaction & Execution Model Analysis

### 3.1 Synchronous Blocking Execution (UI Freezing)

Every backend calculation in SuperRSM is executed **synchronously on the main Tkinter UI thread**:

```python
# rsm_gui.py lines 2041-2053 (fit_model)
self.status_var.set(f"Fitting {method} surrogate model...")
self.fit_status_var.set(f"Fitting {method}...")
self.update_idletasks() # Flush redraw

result = rsm_backend.rsm_fromDF( # BLOCKS GUI THREAD
    self.df, input_cols, output_col, degree_fit=degree, test_size=test_size, method=method
)
```

#### Profiling Long-Running Operations:
- **`fit_model()`**:
  - *RidgeCV*: Instantaneous (<0.1s for typical datasets).
  - *GaussianProcessRegressor* (Universal Kriging with RBF + DotProduct + WhiteKernel): 1–5 seconds.
  - *Genetic Programming* (`SymbolicRegressor` via `gplearn`): 15–60+ seconds for population=1000 and generations=20.
  - *Impact*: During symbolic regression or large datasets, Windows marks the window as **"Not Responding"**. The user cannot abort or view intermediate progress.
- **`run_optimization()`**:
  - Executes Scipy `minimize` (SLSQP). For non-linear surrogates with linear constraints, takes 0.5–5 seconds, blocking user input.
- **`generate_plot()`**:
  - Calls `self.result.visualize_rsm()`, which sequentially evaluates a 2D meshgrid across multiple $P \times Q$ subplots:
    $$\text{Total Points} = N_x \times N_y \times |P| \times |Q|$$
    For a $100 \times 100$ grid with $3 \times 3$ subplots, this requires **90,000 predictions**. In GP or symbolic models, this takes 10–30 seconds on the main thread, followed by Matplotlib rendering and a blocking `plt.show()` call.

### 3.2 State Flow & Reactivity

All application state is stored as untyped instance variables on `self`:
```
                  ┌───────────────────────────────────────────────┐
                  │                 Data Loading                  │
                  │  (self.df, self.file_path_var)                │
                  └───────────────────────┬───────────────────────┘
                                          │
                  ┌───────────────────────▼───────────────────────┐
                  │              Variable Selection               │
                  │  (input_cols, output_col)                     │
                  └───────────┬───────────────────────┬───────────┘
                              │                       │
      ┌───────────────────────▼───────┐       ┌───────▼───────────────────────┐
      │      Dynamic Bounds Canvas    │       │     Dynamic Eval Canvas       │
      │  (self.bound_entries)         │       │  (self.eval_entries)          │
      └───────────────┬───────────────┘       └───────┬───────────────────────┘
                      │                               │
                      │       ┌───────────────────────┤
                      │       │ Model Fitting         │
                      │       │ (self.result)         │
                      │       └───────┬───────────────┤
                      │               │               │
      ┌───────────────▼───────────────▼──┐    ┌───────▼───────────────────────┐
      │         Optimization             │    │       Point Evaluation        │
      │  (opt_params_dict, opt_val)      │    │  (eval_pred_var, eval_unc_var)│
      └───────────────┬──────────────────┘    └───────────────────────────────┘
                      │
      ┌───────────────▼──────────────────┐
      │       Plot Configuration         │
      │  (plot_param_configs, roles)     │
      └──────────────────────────────────┘
```

- **Staleness Tracking**: `RSMGui` tracks `self.fitted_model_signature` (`(input_cols, output_col, method, degree, test_size)`). If the user alters inputs, output, or settings, `_check_fit_settings_staleness()` marks the status label with a yellow warning: `⚠ Settings changed — click Fit to update`.
- **Downstream Enabling**: `fit_model()` enables the downstream action buttons (`run_btn`, `plot_config_btn`, `eval_run_btn`).

### 3.3 Hardcoded Model Checks (Impediment to R2 User-Expandability)

`rsm_gui.py` contains hardcoded `if-elif` logic checking specific model names:
- Lines 1449–1468 (`_on_method_change`):
  ```python
  if method == "Genetic Programming":
      self.degree_spin.config(state="disabled")
      self.method_hint_var.set("Symbolic regression via gplearn...")
  elif method == "RidgeCV":
      self.degree_spin.config(state="normal", from_=1, to=10)
      ...
  else: # Gaussian Process
      self.degree_spin.config(state="normal", from_=0, to=10)
  ```
- Line 1389: `degree = int(self.degree_var.get()) if method != "Genetic Programming" else 0`
- Line 2037: `if method == "RidgeCV" and degree < 1:`
- Line 2100: `if result.supports_uncertainty:`

**Problem**: If a user or developer registers a new model (e.g., Random Forest, XGBoost, or Support Vector Regression), the GUI has no way to know whether the model supports polynomial degrees, uncertainty estimation, or what hint text to show. **Model metadata must be exposed by the model interface/registry, not hardcoded into GUI callbacks.**

---

## 4. Comprehensive Analysis of `high_d_plotter.py` (~11.6 KB)

### 4.1 Libraries & Dependencies
- `numpy`: Array transformations, `meshgrid`, slicing, min/max calculations.
- `matplotlib.pyplot`: Subplot grid creation (`plt.subplots`), `contourf`, `contour`, `clabel`, `scatter`, `colorbar`, `suptitle`, `show`.
- `seaborn`: Global aesthetic theming (`sns.set_theme(style="whitegrid")`).

### 4.2 Current API Contract & Processing Flow

`high_d_plotter.py` exposes two primary functions:
1. `validate_multi_contour_inputs(X, Y, Z_array, label_array, scatter_array) -> tuple[bool, str | None]`
2. `plot_multi_contour(X, Y, Z_array, label_array=None, title=..., xlabel=..., ylabel=..., plot_settings=None, scatter_array=None)`
3. `plot_a_function(func, x_range, y_range, p_range, q_range, ...)` (wrapper over `plot_multi_contour`)

#### Processing Flow:
1. Validates dimensional consistency of `X`, `Y` (2D arrays) and `Z_array` (2D nested list of 2D arrays $M \times N$).
2. Merges user `plot_settings` dictionary with `default_plot_settings` using Python 3.9 dictionary union (`|`).
3. Computes global $Z_{\min}$ and $Z_{\max}$ if `uniform_cmap` or `show_colorbar` is active.
4. Creates subplots: `fig, axes = plt.subplots(m, n, sharex=True, sharey=True, squeeze=False)`.
5. Loops over each $(i, j)$ cell, calling `ax.contourf()`, `ax.contour()`, `ax.clabel()`, and optional `ax.scatter()`.
6. Appends colorbar and suptitle.
7. If `plot_settings.get("show_plot", True)`: invokes `plt.show()`.

### 4.3 Structural Flaws in `high_d_plotter.py`

| Flaw | Consequence | Proposed Remedy |
|---|---|---|
| **Module-Level Side-Effect** (`sns.set_theme` at line 15) | Modifies global Matplotlib rcParams on import, altering fonts and styles across the entire Python process. | Encapsulate styling inside a dedicated style context (`with plt.style.context(...)`). |
| **No Return Value** (`fig, axes` discarded) | Caller cannot embed the plot in a GUI, modify artists, or save to disk programmatically. | Always return `tuple[plt.Figure, np.ndarray[plt.Axes]]`. |
| **Blocking `plt.show()`** (line 221) | Spawns a blocking native Matplotlib event loop that interrupts or conflicts with Tkinter. | Separate figure creation from display. Allow embedding via `FigureCanvasTkAgg`. |
| **Untyped `plot_settings` Dict** | Prone to key typos, lacks validation, difficult for IDE/AI autocomplete. | Replace with strongly-typed `PlotConfig` dataclass with serialization. |
| **Coupling with `rsm_backend.py`** | `rsm_result.visualize_rsm` directly imports and calls `plot_multi_contour`. Backend cannot run headless without Matplotlib. | Invert dependency: visualization service accepts models or evaluated grids; backend core does not import visualization. |

### 4.4 Target Architecture for Plotting: `super_rsm.visualization`

Restructure `high_d_plotter.py` into a cohesive visualization service package:
```
super_rsm/visualization/
├── __init__.py            # Exposes plot_multi_contour, MultiContourEngine, PlotConfig
├── config.py              # Strongly-typed PlotConfig dataclass (serializable to JSON)
├── engine.py              # MultiContourEngine: pure Matplotlib rendering (returns fig, axes)
├── grid_sampler.py        # GridSampler: samples N-dimensional surrogate slices into 2D grids
├── style.py               # Colormaps, markers, linestyles, isolated Matplotlib style contexts
└── tk_canvas.py           # Optional embedded FigureCanvasTkAgg frame for Tkinter
```

---

## 5. Proposed Decoupled UI Architecture (MVP / Modular Components)

To eliminate the 3,039-line monolith, we propose a **Model-View-Presenter (MVP)** architecture using modular Tkinter components, an Application Controller, and background worker threads.

### 5.1 Architectural Components & File Sizing (<350 Lines/File)

```
super_rsm/gui/
├── __init__.py                       # Package exports
├── app.py                            # Main RSMApplication window setup (~180 lines)
├── state.py                          # SessionState & ViewModels (~140 lines)
├── controller.py                     # RSMController: coordinates UI actions & threading (~250 lines)
│
├── styles/
│   ├── __init__.py
│   ├── theme.py                      # PALETTE constants, TTK Style definitions (~120 lines)
│   └── fonts.py                      # Platform-aware font resolution (~50 lines)
│
├── components/
│   ├── __init__.py
│   ├── kpi_card.py                   # Reusable KPICard component (~70 lines)
│   ├── scrollable_panel.py           # Reusable Canvas + Scrollbar auto-resizing panel (~80 lines)
│   └── treeview_helper.py            # Treeview column configuration & clipboard utilities (~60 lines)
│
├── views/
│   ├── __init__.py
│   ├── header_view.py                # Top branding bar & dataset badge (~50 lines)
│   ├── data_source_view.py           # Step 1: File selection & reload (~70 lines)
│   ├── variable_selection_view.py    # Step 2: Input factors listbox & target response combo (~110 lines)
│   ├── model_settings_view.py        # Step 3: Method, degree, test ratio, fit action (~120 lines)
│   ├── bounds_view.py                # Step 4: Optimization goal & scrollable bounds (~120 lines)
│   ├── constraints_view.py           # Step 5: Linear constraints table & management (~110 lines)
│   ├── action_bar_view.py            # Optimization & Plot action buttons (~50 lines)
│   ├── kpi_strip_view.py             # Horizontal container for 4 KPI cards (~70 lines)
│   ├── status_bar_view.py            # Bottom status label & progress indicator (~50 lines)
│   └── results/
│       ├── __init__.py
│       ├── results_notebook.py       # Notebook shell (~60 lines)
│       ├── optimal_tab.py            # Tab 1: Optimal Solution & Constraints table (~130 lines)
│       ├── report_tab.py             # Tab 2: Full report text area & copy action (~70 lines)
│       └── evaluation_tab.py         # Tab 3: Model point evaluator & history table (~180 lines)
│
└── dialogs/
    ├── __init__.py
    ├── linear_constraint_dialog.py   # Modal dialog for defining ∑ cᵢ·xᵢ ≤ b (~230 lines)
    └── plot_config_dialog.py         # Multi-tab plot configuration modal window (~350 lines)
```

### 5.2 Responsibilities & Contracts

#### 1. `SessionState` (`gui/state.py`):
Centralized, observable state object containing:
- `dataset`: Pandas DataFrame, file path, column names.
- `selection`: List of selected input columns, target output column.
- `model_fit`: Current method, degree, test ratio, fitted model reference (`RSMResult`), fit metrics ($R^2$, RMSE, MSE), fit signature for staleness.
- `optimization`: Goal (`Minimize` or `Maximize`), bounds dictionary, linear constraints list, optimal parameters dictionary, optimal value, convergence status.
- `evaluation`: History list of point evaluations.
- `plot_config`: Active `PlotConfig` instance.

#### 2. `RSMController` (`gui/controller.py`):
Coordinates view events and dispatches backend tasks:
- `handle_load_dataset(filepath)`
- `handle_fit_model(method, degree, test_size)` (runs in background thread)
- `handle_run_optimization(goal, bounds, constraints)` (runs in background thread)
- `handle_evaluate_point(point_dict)`
- `handle_open_plot_config()`
- `handle_generate_plot(plot_config)`

#### 3. Threading Architecture (Preventing UI Freezes):
```python
def _run_async(self, worker_func, on_success, on_error, status_msg):
    self.view.status_bar.set_busy(status_msg)
    def thread_target():
        try:
            result = worker_func()
            self.app.after(0, lambda: on_success(result))
        except Exception as e:
            self.app.after(0, lambda: on_error(e))
        finally:
            self.app.after(0, self.view.status_bar.set_idle)
    threading.Thread(target=thread_target, daemon=True).start()
```
This guarantees the Tkinter main loop remains responsive even during heavy Genetic Programming or multi-panel contour rendering.

#### 4. Model Metadata Protocol (User-Expandability):
To eliminate hardcoded `if method == ...` checks, models in the registry provide a `ModelMetadata` descriptor:
```python
@dataclass
class ModelMetadata:
    name: str
    display_name: str
    description: str
    supports_degree: bool = True
    min_degree: int = 1
    max_degree: int = 10
    default_degree: int = 2
    supports_uncertainty: bool = False
    extracts_coefficients: bool = False
```
The GUI's `ModelSettingsView` dynamically queries `ModelMetadata` to configure spinbox limits, enabled states, and hint text without touching GUI code when a new regression model is registered.

---

## 6. Dependency Flow & Circular Dependency Prevention

### 6.1 Strict Layered Dependency Hierarchy

To guarantee zero circular dependencies and ensure headless backend testability, the system follows the **Inward Dependency Rule**:

```
┌─────────────────────────────────────────────────────────────┐
│ Level 4: GUI Presentation Layer                             │
│ (super_rsm.gui: views, dialogs, controllers, styles)        │
└──────────────┬───────────────────────────────┬──────────────┘
               │                               │
               ▼                               ▼
┌──────────────────────────────┐ ┌─────────────────────────────┐
│ Level 2: Core RSM Pipeline   │ │ Level 3: Visualization      │
│ (super_rsm.core: pipeline,   │ │ (super_rsm.visualization:   │
│  optimization, metrics)      │ │  multi-contour, config)     │
└──────────────┬───────────────┘ └─────────────┬───────────────┘
               │                               │
               ▼                               │
┌──────────────────────────────┐               │
│ Level 1: Regression Models   │               │
│ (super_rsm.models: protocols,│               │
│  registry, GP, Ridge, GPlearn│               │
└──────────────┬───────────────┘               │
               │                               │
               ▼                               ▼
┌─────────────────────────────────────────────────────────────┐
│ Level 0: Shared Utilities & Base Types                      │
│ (super_rsm.common: exceptions, formatting, constants)       │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 Key Architectural Decoupling Rules

1. **Core Does NOT Import Visualization**:
   - `rsm_result` in `core` ceases to call `plot_multi_contour`.
   - `visualization.GridSampler` queries the fitted model to generate 2D grid arrays.
   - Core RSM can be executed in headless environments (cloud containers, HPC batch scripts) without `matplotlib` or `seaborn`.
2. **Models Do NOT Import Core or GUI**:
   - Regression models implement a clean `BaseSurrogateModel` protocol (`fit`, `predict`, `predict_std`).
   - Models have zero knowledge of Tkinter, optimization constraints, or contour plotting.
3. **GUI Is Strictly a Consumer**:
   - GUI imports Core, Models, and Visualization. Nothing imports GUI.
   - Views communicate only through `RSMController`, avoiding cross-view circular references.
4. **Backward Compatibility via Facades**:
   - Existing root scripts (`rsm_gui.py` and `high_d_plotter.py`) remain in the repository as lightweight, backward-compatible facades pointing to `super_rsm.gui.app:main` and `super_rsm.visualization.multi_contour:plot_multi_contour`.

---

## 7. AI Context Efficiency & Human Navigation Evaluation

### 7.1 Quantitative Context Window Comparison

| Metric | Monolithic Structure (`rsm_gui.py`) | Modular Structure (`super_rsm/gui/`) | Improvement |
|---|---|---|---|
| **Max File Size** | 3,039 lines (~121 KB) | ~350 lines (`plot_config_dialog.py`) | **88.5% reduction** |
| **Typical Working File** | 3,039 lines | 80–150 lines | **95.0% reduction** |
| **AI Tokens per Inspection** | ~35,000 tokens | 1,000–3,500 tokens | **90% token savings** |
| **Risk of Unintended Edits** | High (accidental edits to unrelated tabs or handlers) | Low (isolated modules with explicit interfaces) | Substantial quality improvement |
| **Testability** | Cannot test UI units without loading whole app | Individual views, dialogs, and components unit-testable | High |

### 7.2 Human Developer Navigation Benefits
- **Logical Discoverability**: A developer tasked with updating the linear constraint solver navigates directly to `gui/dialogs/linear_constraint_dialog.py` and `core/optimizer.py`, without wading through 3,000 lines of unrelated Tkinter treeview packing.
- **Merge Conflict Elimination**: Team members can work concurrently on plot settings, KPI widgets, and surrogate regression models without touching the same monolithic file.
- **Consistent Code Patterns**: Reusable `ScrollablePanel` and `TreeviewHelper` components reduce boilerplate across all panels and enforce a uniform aesthetic.
