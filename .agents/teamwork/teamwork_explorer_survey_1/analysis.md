# SuperRSM Architecture Survey & Repository Reorganization Analysis

**Author**: Explorer 1 (Codebase Architecture & Reorganization Explorer)  
**Date**: 2026-10-30  
**Status**: Completed Survey  
**Target Working Directory**: `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM`  

---

## 1. Executive Summary & Repository Inventory

SuperRSM is a specialized scientific Python application designed to fit Response Surface Models (RSM) to experimental or simulated datasets, optimize input parameters subject to rectangular bounds and linear constraints, evaluate surrogate predictions at arbitrary points with uncertainty metrics, and visualize multi-dimensional response surfaces using sliced contour subplot matrices.

The current repository consists of a flat structure containing **3 Python source files**, **1 configuration file**, **1 sample dataset**, **1 license**, **1 documentation file**, and a directory of documentation images.

### 1.1 Complete Repository Inventory Table

| File / Path | Size (Bytes) | Total Lines | Code Lines | Blank Lines | Comment Lines | Primary Responsibility |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `rsm_gui.py` | 121,563 | 3,038 | 2,560 | 369 | 109 | Monolithic Tkinter GUI: styles, dialogs, layout, data loading, constraint parsing, optimization orchestration, evaluation, plot configuration, and JSON profile management. |
| `rsm_backend.py` | 21,332 | 518 | 432 | 69 | 17 | Backend modeling: model builders (GP, RidgeCV, GP/gplearn), registry dictionary, `rsm_result` class, metrics, optimization wrapper, grid generation for plotting, and self-test suite. |
| `high_d_plotter.py` | 11,612 | 242 | 208 | 33 | 1 | Multi-panel contour visualization: input validation, default plot settings, $m \times n$ subplot generation, contour line labeling, and scatter data overlay. |
| `requirements.txt` | 312 | 19 | 8 | 5 | 6 | Project dependency specifications (`numpy`, `scipy`, `pandas`, `openpyxl`, `scikit-learn`, `gplearn`, `matplotlib`, `seaborn`). |
| `sample_data.csv` | 5,605 | 102 | 102 | 0 | 0 | Test dataset with 100 observations of 2 inputs (`x1`, `x2`) and 1 output (`y`), corresponding to quadratic function $y = (x_1 - 3)^2 + (x_2 - 4)^2 + 5$. |
| `README.md` | 17,338 | 295 | — | — | — | Comprehensive documentation: feature description, setup instructions, GUI walkthrough, model registry extension guide, and code examples. |
| `LICENSE` | 1,130 | 21 | — | — | — | MIT License (Mitsuki Shimomura & Michigan Technological University, 2026). |
| `.gitignore` | 4,884 | 134 | — | — | — | Standard Python, virtualenv, and IDE ignore patterns. |
| `readme_images/image.png`| 294,020 | — | — | — | — | Screenshot of the SuperRSM GUI displayed in `README.md`. |

---

## 2. Granular Structural Analysis of Existing Modules

### 2.1 `rsm_backend.py` (518 lines, 21.3 KB)

`rsm_backend.py` serves as the analytical foundation of the system. It contains 1 class, 11 top-level functions, 1 global registry dictionary, and a self-test suite.

#### Breakdown of Functions and Classes:
- **Model Builders** (Lines 30–95):
  - `build_gaussian_process_model(degree_fit=2, **kwargs)` (Lines 30–48): Constructs Ordinary Kriging (`degree_fit==0`, constant mean with `normalize_y=True`, `RBF + WhiteKernel`) or Universal Kriging (`degree_fit>0`, polynomial drift with `DotProduct + RBF + WhiteKernel`, `PolynomialFeatures`, `StandardScaler`).
  - `build_ridge_model(degree_fit=2, n_samples=None, **kwargs)` (Lines 51–64): Builds polynomial feature pipeline with `StandardScaler` and `RidgeCV` across 13 alpha values ($\log_{10}$ scale from $-6$ to $6$). Automatically selects 5-fold CV if $N \ge 5$.
  - `piecewise_function(condition, true_val, false_val)` (Lines 67–72): Helper function wrapped via `gplearn.functions.make_function` for genetic programming.
  - `build_genetic_programming_model(degree_fit=2, **kwargs)` (Lines 75–95): Instantiates `gplearn.genetic.SymbolicRegressor` with 5,000 population, 30 generations, parsimony coefficient 0.005, and custom function set (`add`, `sub`, `mul`, `div`, `sqrt`, `log`, `piecewise`).
  - `format_genetic_programming_expression(model)` (Lines 97–103): Inspects `model._program` to extract string equation.
- **Model Registry Dictionary & Functions** (Lines 106–144):
  - `MODEL_REGISTRY` (Line 106): Module-level global dictionary holding metadata dicts (`builder`, `supports_uncertainty`, `extract_coeffs`, `format_expression`).
  - `register_model(name, builder, supports_uncertainty=False, extract_coeffs=False, format_expression=None)` (Lines 128–137): Mutates `MODEL_REGISTRY`.
  - `get_supported_methods()` (Lines 140–144): Returns `list(MODEL_REGISTRY.keys())`.
- **`class rsm_result`** (Lines 147–408, 262 lines):
  - `__init__(self, model, X_train, y_train, X_test, y_test, method="Gaussian Process")` (Lines 153–198):
    - Stores dataset splits and method name.
    - Inspects `MODEL_REGISTRY` for uncertainty and expression extraction callback.
    - **Hardcoded coefficient unscaling logic** (Lines 178–186): Specifically inspects `model.named_steps` for `standardscaler` and `ridgecv`, computing unscaled physical coefficients $w = w_{\text{scaled}} / s$ and intercept $b = b_{\text{scaled}} - w \cdot \mu$.
    - Evaluates test set predictions and computes metrics: $R^2$, MSE, RMSE.
  - `__str__(self)` (Lines 200–209): Returns formatted multi-line summary string.
  - `target_func(self, params, return_std=False)` (Lines 211–220): Evaluates single point via `model.predict(X_eval, return_std=...)`.
  - `evaluate_point(self, params, return_std=False)` (Lines 222–236): Scalar wrapper returning `(y_val, std_val)` or `y_val`.
  - `optimize(self, initial_guess=None, bounds=None, constraints=None, maximize=False)` (Lines 238–269): Solves continuous optimization problem using `scipy.optimize.minimize`. Supports rectangular bounds and linear constraints. Negates objective function when `maximize=True`. Caches `last_opt_result` and `last_opt_maximize`.
  - `visualize_rsm(self, config, title=..., xlabel=..., ylabel=..., label_array=..., plot_settings=...)` (Lines 271–408, 138 lines):
    - Constructs 2D meshgrids for $X$ and $Y$, iterating over outer subplot dimensions $P$ and $Q$.
    - Iterates point-by-point through $X_{\text{flat}}, Y_{\text{flat}}$ (unvectorized scalar loop).
    - Filters experimental measurement data matching each subplot's $P$, $Q$, and fixed parameters for scatter overlays.
    - Calls `plot_multi_contour()` from `high_d_plotter.py`.
    - Generates secondary uncertainty contour plot if `plot_uncertainty=True`.
- **Pipeline and Data Preparation Functions** (Lines 411–468):
  - `generate_term_strings(input_columns, model)` (Lines 411–419): Extracts polynomial feature names from `PolynomialFeatures` pipeline step or falls back to column names.
  - `fit_rsm2(X, y, degree_fit=2, test_size=0.20, method="Gaussian Process", **kwargs)` (Lines 422–439): Splits data via `train_test_split`, calls registry builder, fits model, returns `rsm_result`.
  - `build_data(df, input_columns, output_column)` (Lines 442–452): Extracts NumPy arrays $X$ and $y$ from DataFrame.
  - `rsm_fromDF(df, input_columns, output_column, degree_fit=2, test_size=0.20, method="Gaussian Process", **kwargs)` (Lines 455–468): Convenience pipeline wrapper connecting DataFrame to `fit_rsm2`.
- **Built-in Self-Test Block** (Lines 471–518):
  - Generates 100 synthetic quadratic samples with known minimum at $(3.0, 4.0)$ with value $5.0$.
  - Iterates over all registered methods (`Gaussian Process`, `RidgeCV`, `Genetic Programming`), verifying fitting, point evaluation, minimization, maximization, and coefficient extraction.

---

### 2.2 `high_d_plotter.py` (242 lines, 11.6 KB)

`high_d_plotter.py` provides high-dimensional visualization routines by plotting a 2D grid of 2D contour subplots ($m \times n$) representing slices of higher-dimensional response surfaces.

#### Breakdown of Functions and Elements:
- **Module-Level Side Effect** (Line 15):
  - `sns.set_theme(style="whitegrid")` executes immediately on import, modifying global matplotlib/seaborn rcParams.
- **`validate_multi_contour_inputs`** (Lines 17–83, 67 lines):
  - Validates that $X$ and $Y$ are 2D arrays of identical shape $(n_y, n_x)$.
  - Validates that $Z_{\text{array}}$ is an $m \times n$ grid of 2D arrays matching $(n_y, n_x)$.
  - Validates matching dimensions for `label_array` and `scatter_array`.
- **`default_plot_settings`** (Lines 86–108):
  - Global dictionary containing 18 default styling options (`cmap`, `alpha`, `fill_levels`, `line_levels`, `line_color`, `inline_color`, `inline_fontsize`, `grid_color`, `grid_linestyle`, `inline_format`, `uniform_cmap`, `show_colorbar`, `colorbar_label`, `scatter_data`, `scatter_size`, `scatter_color_mode`, `scatter_color`, `scatter_cmap`, `scatter_edgecolor`, `scatter_marker`, `show_plot`).
- **`plot_multi_contour`** (Lines 110–221, 112 lines):
  - Computes global $Z_{\text{min}}$ and $Z_{\text{max}}$ across all subplots for shared colormap normalization.
  - Generates figure and axes via `plt.subplots(m, n, sharex=True, sharey=True, squeeze=False)`.
  - Plots filled contours (`ax.contourf`) and contour lines (`ax.contour`) with inline clabels (`ax.clabel`).
  - Overlays measurement scatter points with either "Fixed Color" mode or "Output Value (Colormap)" mode.
  - Adds optional colorbar to the right of the subplot matrix.
  - Invokes `plt.show()` if `show_plot=True`.
- **`plot_a_function`** (Lines 225–242, 18 lines):
  - Helper function evaluating an arbitrary 4-parameter mathematical function $f(x, y, p, q)$ over 1D iterables and forwarding to `plot_multi_contour`.

---

### 2.3 `rsm_gui.py` (3,038 lines, 121.6 KB)

`rsm_gui.py` is a massive monolithic file containing styling, dialogs, application shell, and event handlers. It is by far the largest file in the repository (25× larger than `high_d_plotter.py` and 6× larger than `rsm_backend.py`).

#### Major Functional Sections:
1. **Theme, Colors, & TTK Styles** (Lines 18–305):
   - `PALETTE` dictionary: 17 hex color tokens for background, cards, text, accents, borders, and status indicators.
   - Presets: `COMMON_CMAPS` (10 items), `COMMON_LINESTYLES` (4 items), `COMMON_MARKERS` (10 items).
   - `get_ui_fonts()`: Detects platform (Windows/macOS/Linux) and creates Tkinter font instances.
   - `configure_ttk_styles(root)` (224 lines): Configures styles for `TFrame`, `Card.TFrame`, `Header.TFrame`, `TLabel`, `TButton`, `Primary.TButton`, `Success.TButton`, `Accent.TButton`, `Danger.TButton`, `TNotebook`, `Treeview`, and `TCombobox`.
2. **Constraint Formatting & Dialog** (Lines 308–572):
   - `format_linear_expression(coeffs_dict, operator, bound)` (Lines 308–345): Formats algebraic strings like `1.5 * x1 + 2.0 * x2 <= 10.0`.
   - `class LinearConstraintDialog(tk.Toplevel)` (Lines 348–572, 225 lines): Modal dialog with dynamic coefficient entry fields for every active input variable, operator combobox (`<=`, `>=`, `==`), bound entry field, live equation preview, and save callback.
3. **`class RSMGui(tk.Tk)`** (Lines 575–3033, 2,459 lines):
   - **`__init__`** (Lines 576–598): Initializes application window, state variables (`self.df`, `self.result`, `self.linear_constraints`, `self.bound_entries`, `self.eval_entries`, `self.eval_history`).
   - **`create_widgets`** (Lines 600–1318, 719 lines):
     - Header banner with icon, title, dataset summary, and "Load Demo Dataset" button.
     - Horizontal split pane (`ttk.PanedWindow`).
     - Left Sidebar:
       - File Selection Bar (`browse_file`, `load_data`).
       - Column Selection (`input_listbox`, `output_combo`, Select All, Clear).
       - Model & Fit Settings (Method combobox, degree spinbox, test ratio spinbox, "Fit Surrogate Model" button, model status indicator).
       - Optimization Goal & Parameter Bounds (Goal combobox: `Minimize` / `Maximize`, dynamic bounds entries inside scrollable canvas, Fill Bounds from Data, Clear Bounds).
       - Linear Constraints Management (Treeview listing defined constraints, Add, Edit, Delete, Clear buttons).
       - Action buttons bar ("Run Optimization", "Configure Plot").
     - Right Notebook & KPI Strip:
       - KPI strip: 4 summary cards (Target Response, Model Fit Status, Optimal Solution, Solver Status).
       - Tab 1: Optimal Solution & Constraints (Optimal parameter values treeview, constraint verification treeview, Copy to Clipboard button).
       - Tab 2: Model Equation & Full Report (Scrollable `tk.Text` widget).
       - Tab 3: Evaluate Model (Point evaluation parameter inputs, shortcuts: "Fill from Optimal", "Fill with Data Mean", "Evaluate Point" button, predicted response + uncertainty display, evaluation history comparison treeview, clipboard export).
     - Bottom status bar.
   - **Methods Breakdown Table**:

| Method Name | Lines | Line Count | Functional Category | Responsibility |
| :--- | :--- | :--- | :--- | :--- |
| `__init__` | 576–598 | 23 | Lifecycle | Initialize main window and state attributes |
| `create_widgets` | 600–1318 | 719 | UI Layout | Build complete Tkinter widget hierarchy |
| `_create_kpi_card` | 1324–1379 | 56 | Widget Helper | Construct individual styled KPI metric cards |
| `_get_current_fit_signature` | 1381–1396 | 16 | Caching/State | Hash current inputs, degree, method, and test size |
| `_check_fit_settings_staleness` | 1398–1411 | 14 | Validation | Compare active model signature with UI entries, toggle amber warning |
| `_invalidate_fitted_model` | 1413–1445 | 33 | State Management | Clear cached model, reset KPI cards and results tables |
| `_on_method_change` | 1447–1469 | 23 | Event Handler | Update UI controls based on selected regression algorithm |
| `_on_opt_goal_change` | 1471–1479 | 9 | Event Handler | Update KPI labels between "Optimal Min" and "Optimal Max" |
| `_on_output_selected` | 1481–1494 | 14 | Event Handler | Invalidate model if target variable changes |
| `_update_column_selection_hint` | 1496–1508 | 13 | UI Helper | Update column count caption below listbox |
| `select_all_inputs` | 1510–1518 | 9 | UI Action | Select all available input variables |
| `clear_input_selection` | 1520–1522 | 3 | UI Action | Deselect all input variables |
| `fill_bounds_from_data` | 1524–1533 | 10 | Data Helper | Auto-fill parameter bounds with dataset min/max values |
| `clear_bounds_entries` | 1535–1539 | 5 | UI Action | Clear min/max bound text entries |
| `copy_results_to_clipboard` | 1541–1547 | 7 | Export | Copy full report text to system clipboard |
| `_get_col_mean_str` | 1553–1559 | 7 | Data Helper | Compute column mean as formatted string |
| `fill_eval_from_optimal` | 1561–1573 | 13 | UI Action | Populate evaluation inputs with optimal parameter solution |
| `fill_eval_from_mean` | 1575–1580 | 6 | UI Action | Populate evaluation inputs with dataset mean values |
| `clear_eval_entries` | 1582–1585 | 4 | UI Action | Clear point evaluation entries |
| `clear_eval_history` | 1587–1591 | 5 | UI Action | Clear point evaluation history table |
| `copy_eval_history` | 1593–1603 | 11 | Export | Export evaluation history table to clipboard |
| `_on_eval_history_double_click` | 1605–1616 | 12 | Event Handler | Restore double-clicked historical point into entry fields |
| `evaluate_custom_point` | 1618–1685 | 68 | Analytical Action | Evaluate point on `self.result`, calculate $95\%$ CI, update UI |
| `add_linear_constraint` | 1691–1702 | 12 | Dialog Launcher | Open `LinearConstraintDialog` to add a new constraint |
| `edit_linear_constraint` | 1704–1725 | 22 | Dialog Launcher | Open dialog to edit existing selected constraint |
| `delete_linear_constraint` | 1727–1737 | 11 | UI Action | Remove selected constraint from list |
| `clear_linear_constraints` | 1739–1744 | 6 | UI Action | Clear all defined linear constraints |
| `refresh_constraints_tree` | 1746–1755 | 10 | UI Helper | Refresh Treeview items with formatted constraint equations |
| `browse_file` | 1761–1772 | 12 | Dialog Launcher | Open file picker for `.csv`, `.xlsx`, `.xls` |
| `load_data` | 1774–1818 | 45 | Data Ingestion | Read spreadsheet/CSV into pandas DataFrame, populate lists |
| `_get_col_range_str` | 1820–1826 | 7 | Data Helper | Calculate formatted column range `[min, max]` |
| `on_input_select` | 1828–1952 | 125 | UI Rebuilder | Dynamically rebuild parameter bounds and point eval entries |
| `_render_full_report` | 1958–2004 | 47 | Reporting | Assemble and render formatted text report in Tab 2 |
| `fit_model` | 2006–2121 | 116 | Orchestration | Fit surrogate model via `rsm_backend.rsm_fromDF`, update KPIs |
| `run_optimization` | 2123–2357 | 235 | Optimization | Parse bounds/constraints, construct Scipy constraints, optimize, verify |
| `_get_col_plot_defaults` | 2363–2385 | 23 | Plot Helper | Calculate default plotting ranges and steps for variables |
| `open_plot_config` | 2387–2718 | 332 | Dialog Launcher | Multi-tab dialog for plot roles, labels, and advanced settings |
| `_reset_plot_axes_to_data` | 2720–2728 | 9 | Plot Helper | Reset plot min/max ranges to dataset bounds |
| `_set_plot_fixed_to_optimal` | 2730–2734 | 5 | Plot Helper | Set fixed parameter values to optimal coordinates |
| `_set_plot_fixed_to_mean` | 2736–2744 | 9 | Plot Helper | Set fixed parameter values to dataset means |
| `_update_scatter_color_state` | 2746–2759 | 14 | UI Helper | Toggle scatter color entries between fixed and colormap |
| `_update_plot_role_inputs` | 2761–2817 | 57 | UI Helper | Enable/disable entries based on role (`X`, `Y`, `P`, `Q`, `Fixed`) |
| `generate_plot` | 2819–2927 | 109 | Plot Action | Assemble plot configuration dictionary and call `visualize_rsm` |
| `save_plot_settings` | 2929–2970 | 42 | Profile I/O | Serialize plot configuration profile to JSON file |
| `load_plot_settings` | 2972–3033 | 62 | Profile I/O | Deserialize plot configuration profile from JSON file |

---

## 3. Coupling, Dependency Flow, and Architectural Smells

### 3.1 Current Import Dependencies & Architecture Flow

The existing dependency structure is strictly linear:

```
+-------------------------------------------------------------+
|                         rsm_gui.py                          |
|  - Tkinter GUI, ttk styles, LinearConstraintDialog          |
|  - Data loading, dynamic entry generation                   |
|  - Bounds parsing & Scipy LinearConstraint instantiation   |
|  - Optimization reporting & KPI management                  |
|  - Plot config dialog & JSON profile serialization          |
+-------------------------------------------------------------+
                              │
                              │ imports rsm_backend
                              ▼
+-------------------------------------------------------------+
|                       rsm_backend.py                        |
|  - Model builders: GP, RidgeCV, Genetic Programming         |
|  - Global MODEL_REGISTRY dictionary                         |
|  - rsm_result (metrics, evaluate_point, optimize)           |
|  - visualize_rsm (mesh generation & scatter data filtering) |
+-------------------------------------------------------------+
                              │
                              │ imports plot_multi_contour
                              ▼
+-------------------------------------------------------------+
|                     high_d_plotter.py                       |
|  - Matplotlib / Seaborn multi-contour subplots              |
|  - default_plot_settings dictionary                         |
|  - Scatter overlay logic                                    |
+-------------------------------------------------------------+
```

### 3.2 Detailed Codebase Smells & Tight Coupling Points

#### Smell 1: Inverted Dependency / Core-to-Plotter Coupling
- **Observation**: `rsm_backend.py:23` executes `from high_d_plotter import plot_multi_contour`. Furthermore, `rsm_result.visualize_rsm` (lines 271–408, 138 lines) is directly embedded into the core mathematical result class.
- **Problem**: Core surrogate modeling logic is tightly coupled to visualization. If a developer uses `rsm_backend` in a headless environment, CLI, or microservice, `high_d_plotter` is still imported, triggering `matplotlib.pyplot` and `seaborn` imports and theme overrides.
- **Architectural Violation**: Violates the Dependency Inversion Principle and Single Responsibility Principle.

#### Smell 2: Open-Closed Principle Violation in Model Unscaling & Expression Formatting
- **Observation**: In `rsm_backend.py:178–186`, `rsm_result.__init__` contains hardcoded model-type inspections:
  ```python
  if meta.get("extract_coeffs", False) or (hasattr(model, "named_steps") and "ridgecv" in model.named_steps):
      try:
          scaler_step = model.named_steps.get('standardscaler')
          ridge_step = model.named_steps.get('ridgecv')
          if scaler_step is not None and ridge_step is not None:
              self.coeffs = ridge_step.coef_ / scaler_step.scale_
              self.intercept = ridge_step.intercept_ - np.dot(self.coeffs, scaler_step.mean_)
      except Exception:
          pass
  ```
  Similarly, expression formatting relies on an optional `format_expression` callable registered in a dictionary.
- **Problem**: Any new regression model (e.g., Lasso, ElasticNet, DecisionTree, XGBoost, or custom neural net surrogate) cannot define how its coefficients or expressions are extracted without either hacking `rsm_result` or adhering to ad-hoc dictionary conventions.
- **Architectural Violation**: Violates the Open-Closed Principle. Model-specific behavior should be encapsulated polymorphically within model adapters implementing a common interface.

#### Smell 3: Global Mutable State in Model Registration
- **Observation**: `rsm_backend.py:106` defines `MODEL_REGISTRY` as a top-level mutable dictionary. Functions `register_model` (line 128) and `get_supported_methods` (line 140) read and write directly to this global dictionary.
- **Problem**: Global mutable state hinders parallel test execution, prevents scoped registries (e.g., plugin isolation), and lacks type safety or validation.
- **Architectural Violation**: Lack of encapsulation and formal Model Provider/Registry interface.

#### Smell 4: Mathematical Optimization & Constraint Logic Embedded in the GUI
- **Observation**: In `rsm_gui.py:2184–2205`, the GUI directly parses its UI dictionaries and constructs `scipy.optimize.LinearConstraint` with coefficient matrix $A$, lower bounds $lb$, and upper bounds $ub$:
  ```python
  for c in self.linear_constraints:
      row = [c["coeffs"].get(col, 0.0) for col in input_cols]
      A_matrix.append(row)
      # ...
  scipy_constraints = LinearConstraint(np.array(A_matrix), np.array(lb_vec), np.array(ub_vec))
  ```
  In lines 308–345, the GUI implements mathematical string formatting for linear inequalities. In lines 2280–2320, the GUI performs constraint satisfaction and tolerance verification.
- **Problem**: Domain logic (numerical optimization setup, constraint verification, mathematical formatting) is entangled with Tkinter event handlers. This code cannot be unit-tested without instantiating the entire Tkinter GUI!
- **Architectural Violation**: Violates Separation of Concerns between Presentation Layer and Domain Layer.

#### Smell 5: Monolithic Plot Configuration Dialog
- **Observation**: `rsm_gui.py:2387–2718` contains `open_plot_config`, a 332-line inline method creating a complex multi-tab Toplevel dialog, wiring up role selection, colormap choices, scatter options, and JSON profile serialization.
- **Problem**: Highly repetitive UI creation code that inflates `rsm_gui.py` to >3,000 lines and is impossible to maintain or test independently.
- **Architectural Violation**: Lack of dedicated dialog/component encapsulation.

#### Smell 6: Inefficient Unvectorized Mesh Evaluation
- **Observation**: In `rsm_backend.py:336–360`, `visualize_rsm` loops over every $(x_i, y_i)$ coordinate individually in Python:
  ```python
  for x_val, y_val in zip(X_flat, Y_flat):
      params = np.zeros(self.X_test.shape[1])
      params[x_idx] = x_val
      params[y_idx] = y_val
      # ...
      z_value = self.target_func(params)
      Z_flat.append(z_value)
  ```
- **Problem**: For a standard $100 \times 100$ grid, this executes 10,000 separate calls to `model.predict()`. For Gaussian Process models with matrix operations or symbolic expression trees, this adds massive overhead compared to a single vectorized batch evaluation `model.predict(X_grid)`.

#### Smell 7: Module Import Side-Effects
- **Observation**: `high_d_plotter.py:15` executes `sns.set_theme(style="whitegrid")` at module import time.
- **Problem**: Any consumer importing `rsm_backend` indirectly mutates matplotlib's global theme and default figure parameters without consent.

#### Smell 8: AI Context Window and Human Developer Overhead
- **Observation**: `rsm_gui.py` is 3,038 lines (121.6 KB). An AI model reading this file consumes approximately 30,000–35,000 tokens of context. Making targeted changes or reasoning about a specific tab requires parsing thousands of lines of unrelated layout code.
- **Goal**: Decompose all files to under 400–500 lines per module, with clear, self-contained responsibilities.

---

## 4. Proposed Modular Target Architecture

To satisfy **R1** (Architectural Reorganization) and **R2** (User-Expandable Regression Models), the codebase should be reorganized into a cohesive Python package named `super_rsm` (or modular package tree), accompanied by thin backward-compatibility shims at the repository root.

### 4.1 Target Directory Hierarchy

```
c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\
│
├── rsm_gui.py                       # [Shim] 100% backward-compatible CLI/GUI launcher (~20 lines)
├── rsm_backend.py                   # [Shim] 100% backward-compatible API re-export (~40 lines)
├── high_d_plotter.py                # [Shim] 100% backward-compatible plotter re-export (~25 lines)
├── requirements.txt                 # Unchanged dependencies
├── sample_data.csv                  # Test dataset
├── README.md                        # Documentation
├── LICENSE                          # MIT License
├── readme_images/                   # Documentation screenshots
│
└── super_rsm/                       # Core modular package
    ├── __init__.py                  # Package exports & version
    │
    ├── models/                      # REGRESSION MODEL SUBSYSTEM (R2)
    │   ├── __init__.py              # Re-exports registry & standard models
    │   ├── base.py                  # Abstract Base Class / Protocol for Surrogate Models (~100 lines)
    │   ├── registry.py              # Model Registry class with decorator support (~90 lines)
    │   ├── gaussian_process.py      # GP / Kriging model adapter (~110 lines)
    │   ├── ridge.py                 # RidgeCV polynomial model adapter (~95 lines)
    │   └── symbolic.py              # GP Symbolic Regressor adapter (~120 lines)
    │
    ├── core/                        # CORE RSM MATH & DOMAIN LOGIC (R1)
    │   ├── __init__.py              # Re-exports dataset, result, optimizer, pipeline
    │   ├── dataset.py               # RSMDataset container, data loader, train/test splitting (~90 lines)
    │   ├── result.py                # RSMResult class (metrics, point eval, summary, target_func) (~130 lines)
    │   ├── optimization.py          # OptimizationEngine, ConstraintDefinition, Scipy builder (~160 lines)
    │   └── pipeline.py              # fit_rsm and rsm_from_dataframe orchestration (~80 lines)
    │
    ├── visualization/               # VISUALIZATION & PLOTTING SUBSYSTEM
    │   ├── __init__.py              # Re-exports plotter & visualization service
    │   ├── contour.py               # Multi-contour subplot matrix generator (from high_d_plotter) (~170 lines)
    │   ├── grid_builder.py          # Vectorized (X, Y, P, Q, Fixed) mesh generation & batch eval (~110 lines)
    │   ├── service.py               # RSMVisualizationService coordinating mesh & plot (~100 lines)
    │   └── settings.py              # PlotSettings dataclass & JSON profile save/load (~90 lines)
    │
    └── gui/                         # MODULAR TKINTER USER INTERFACE
        ├── __init__.py              # GUI module exports
        ├── app.py                   # RSMApp main window & state coordinator (~280 lines)
        ├── styles.py                # Palette constants, fonts, and configure_ttk_styles (~180 lines)
        ├── widgets/                 # Reusable GUI components
        │   ├── __init__.py
        │   ├── kpi_card.py          # KPICard widget (~80 lines)
        │   └── scrollable_frame.py  # Canvas-based ScrollableFrame widget (~65 lines)
        ├── dialogs/                 # Modal dialog windows
        │   ├── __init__.py
        │   ├── constraint_dialog.py # LinearConstraintDialog (~200 lines)
        │   └── plot_config_dialog.py# PlotConfigDialog (Roles, Labels, Advanced tabs) (~320 lines)
        └── panels/                  # Main window tab panels & sidebars
            ├── __init__.py
            ├── data_panel.py        # File loader & column selector panel (~150 lines)
            ├── model_fit_panel.py   # Model method, degree, test ratio, fit button (~130 lines)
            ├── bounds_panel.py      # Parameter bounds & linear constraints management (~170 lines)
            └── results_notebook.py  # 3-tab notebook (Solution tables, Report text, Evaluate) (~260 lines)
```

---

### 4.2 Module Sizing & Cohesion Analysis

Every target module has been scoped to stay well under the **400-line threshold** (most are 80–250 lines), optimizing for human cognition and AI context windows:

| Proposed Module | Est. Lines | Cohesion & Responsibilities | Key Dependencies |
| :--- | :--- | :--- | :--- |
| `super_rsm/models/base.py` | ~100 | Defines `SurrogateModel` ABC / Protocol (`fit`, `predict`, `get_coefficients`, `get_expression`, `get_feature_names`). | `abc`, `numpy`, `typing` |
| `super_rsm/models/registry.py` | ~90 | Encapsulated `ModelRegistry` class, `@register_model` decorator, method enumeration. | `super_rsm.models.base` |
| `super_rsm/models/gaussian_process.py` | ~110 | Ordinary & Universal Kriging surrogate model implementation. | `sklearn.gaussian_process`, `base` |
| `super_rsm/models/ridge.py` | ~95 | Cross-validated polynomial Ridge regression with unscaled coefficients. | `sklearn.linear_model`, `base` |
| `super_rsm/models/symbolic.py` | ~120 | Genetic Programming symbolic regressor with piecewise function and formula extraction. | `gplearn`, `base` |
| `super_rsm/core/dataset.py` | ~90 | `RSMDataset` container, train/test splitting, pandas extraction. | `numpy`, `pandas`, `sklearn.model_selection` |
| `super_rsm/core/result.py` | ~130 | `RSMResult` container, metrics computation ($R^2$, MSE, RMSE), point evaluation. Decoupled from plotting! | `numpy`, `models.base`, `dataset` |
| `super_rsm/core/optimization.py` | ~160 | `OptimizationEngine`, `ConstraintDefinition`, Scipy `LinearConstraint` builder, constraint verification. | `scipy.optimize`, `numpy` |
| `super_rsm/core/pipeline.py` | ~80 | High-level `fit_rsm` and `rsm_from_dataframe` orchestration functions. | `models`, `dataset`, `result` |
| `super_rsm/visualization/contour.py` | ~170 | Cleaned `plot_multi_contour` without import-time side effects. | `matplotlib`, `seaborn`, `numpy` |
| `super_rsm/visualization/grid_builder.py`| ~110 | Vectorized multi-dimensional slice grid construction and batch prediction. | `numpy`, `models.base` |
| `super_rsm/visualization/service.py` | ~100 | Coordinates mesh generation, scatter data filtering, and contour plotting. | `grid_builder`, `contour` |
| `super_rsm/visualization/settings.py` | ~90 | `PlotSettings` dataclass, default styling dictionary, JSON profile serialization. | `json`, `dataclasses` |
| `super_rsm/gui/styles.py` | ~180 | Color palette tokens, UI fonts, ttk styles setup. | `tkinter`, `tkinter.ttk` |
| `super_rsm/gui/widgets/kpi_card.py` | ~80 | Styled KPI card widget with value, subtitle, and accent bar. | `tkinter`, `tkinter.ttk`, `styles` |
| `super_rsm/gui/widgets/scrollable_frame.py`| ~65 | Canvas-based scrollable container for dynamic bounds. | `tkinter`, `tkinter.ttk` |
| `super_rsm/gui/dialogs/constraint_dialog.py`| ~200 | Modal dialog for defining and editing linear constraints. | `tkinter`, `core.optimization` |
| `super_rsm/gui/dialogs/plot_config_dialog.py`| ~320 | Multi-tab dialog for plot roles, labels, and advanced settings. | `tkinter`, `visualization.settings` |
| `super_rsm/gui/panels/data_panel.py` | ~150 | File selection bar, column selection listbox and combobox. | `tkinter`, `pandas` |
| `super_rsm/gui/panels/model_fit_panel.py` | ~130 | Method combobox, degree, test ratio, fit button, status pill. | `tkinter`, `models.registry` |
| `super_rsm/gui/panels/bounds_panel.py` | ~170 | Dynamic bounds entries and linear constraints treeview. | `tkinter`, `widgets.scrollable_frame` |
| `super_rsm/gui/panels/results_notebook.py`| ~260 | Tab 1 (Tables), Tab 2 (Report text), Tab 3 (Evaluate Model). | `tkinter`, `core.result` |
| `super_rsm/gui/app.py` | ~280 | Main application coordinator, event binding, and controller. | `super_rsm.core`, `super_rsm.gui` |

---

### 4.3 Clean Unidirectional Dependency Flow

The proposed architecture establishes a strict **one-way dependency flow**, eliminating circular dependency risks and decoupling presentation from math:

```
[Presentation Layer]
   super_rsm.gui
      │
      ├──> super_rsm.core (dataset, result, optimization, pipeline)
      ├──> super_rsm.visualization (service, settings)
      └──> super_rsm.models (registry, base)
               │
               ▼
[Service / Orchestration Layer]
   super_rsm.visualization
      │
      ├──> super_rsm.core (result, dataset)
      └──> super_rsm.models (base)
               │
               ▼
[Domain Math Layer]
   super_rsm.core
      │
      └──> super_rsm.models (base, registry)
               │
               ▼
[Model Abstraction Layer]
   super_rsm.models
      └──> (No internal dependencies; only standard library & scikit-learn / scipy)
```

**Verification against Dependency Smells**:
1. `models` has ZERO dependencies on `core`, `visualization`, or `gui`.
2. `core` has ZERO dependencies on `visualization` or `gui`. Core optimization and surrogate evaluation can run headlessly.
3. `visualization` has ZERO dependencies on `gui`.
4. `gui` depends on `core`, `models`, and `visualization` solely via well-defined public interfaces.

---

### 4.4 Backward Compatibility Shims

To ensure existing scripts, workflows, and tests continue to work without modification:

1. **`rsm_gui.py` (Shim)**:
   ```python
   """Backward compatibility shim for SuperRSM GUI."""
   from super_rsm.gui.app import RSMApp

   if __name__ == "__main__":
       app = RSMApp()
       app.mainloop()
   ```

2. **`rsm_backend.py` (Shim)**:
   ```python
   """Backward compatibility shim for SuperRSM backend API."""
   from super_rsm.models.registry import MODEL_REGISTRY, register_model, get_supported_methods
   from super_rsm.models.gaussian_process import build_gaussian_process_model
   from super_rsm.models.ridge import build_ridge_model
   from super_rsm.models.symbolic import (
       build_genetic_programming_model,
       piecewise_function,
       format_genetic_programming_expression,
   )
   from super_rsm.core.result import RSMResult as rsm_result
   from super_rsm.core.dataset import build_data
   from super_rsm.core.pipeline import fit_rsm2, rsm_fromDF
   from super_rsm.models.ridge import generate_term_strings

   __all__ = [
       "MODEL_REGISTRY", "register_model", "get_supported_methods",
       "build_gaussian_process_model", "build_ridge_model",
       "build_genetic_programming_model", "piecewise_function",
       "format_genetic_programming_expression", "rsm_result",
       "generate_term_strings", "fit_rsm2", "build_data", "rsm_fromDF",
   ]
   ```

3. **`high_d_plotter.py` (Shim)**:
   ```python
   """Backward compatibility shim for high-dimensional contour plotter."""
   from super_rsm.visualization.contour import plot_multi_contour, validate_multi_contour_inputs, plot_a_function
   from super_rsm.visualization.settings import default_plot_settings

   __all__ = ["plot_multi_contour", "validate_multi_contour_inputs", "plot_a_function", "default_plot_settings"]
   ```

---

## 5. Comparative Evaluation: Current vs. Proposed Architecture

| Dimension | Current Architecture | Proposed Modular Architecture | Architectural Impact |
| :--- | :--- | :--- | :--- |
| **File Count & Organization** | 3 monolithic files in root folder | 4 domain packages (`models`, `core`, `visualization`, `gui`) + 3 shims | Clear namespace and domain boundaries |
| **Maximum File Size** | `rsm_gui.py`: **3,038 lines** | Largest file: `plot_config_dialog.py` (~320 lines) | **89% reduction** in maximum file length |
| **Average File Size** | ~1,266 lines | ~135 lines | Comfortable human navigation and sub-second comprehension |
| **AI Context Consumption** | 30,000+ tokens for GUI inspection | 1,500–3,500 tokens per module | Eliminates hallucination and truncation risks in LLM editing |
| **Model Extensibility (R2)** | Module-level dictionary; hardcoded unscaling in `rsm_result` | Polymorphic `SurrogateModel` ABC + `@register_model` | Zero modification to core/GUI needed when adding new models |
| **Separation of Concerns** | GUI builds Scipy constraints; backend runs Matplotlib | Strict layered separation: GUI ──> Core ──> Models | Core math runs headlessly without GUI or Matplotlib |
| **Grid Evaluation Speed** | Unvectorized 10,000-iteration scalar Python loop | Batch vectorized matrix prediction `model.predict(X_mesh)` | **10× to 50× faster** contour rendering for expensive models |
| **Testability** | Cannot test GUI dialogs or math separately; self-test in `__main__` | Unit tests per module (`test_models`, `test_optimization`, etc.) | Comprehensive, fast automated unit and integration tests |
| **Backward Compatibility** | N/A | 100% backward compatible via root shims | Zero disruption to existing user scripts or workflows |

---

## 6. Recommendations for the Implementation Plan

Based on the survey findings, the implementation plan artifact should structure the migration into **4 incremental phases**:

1. **Phase 1: Model Abstraction & Registry Layer (`super_rsm.models`)**
   - Implement `SurrogateModel` ABC / Protocol and `ModelRegistry`.
   - Wrap existing models (`GaussianProcess`, `RidgeCV`, `GeneticProgramming`) as compliant adapters.
   - Verify self-test parity with existing `rsm_backend.py:471–518`.
2. **Phase 2: Core Domain Logic Decoupling (`super_rsm.core`)**
   - Extract `RSMDataset`, `RSMResult` (decoupled from plotting), and `OptimizationEngine`.
   - Move Scipy `LinearConstraint` generation and constraint satisfaction checks from GUI to `optimization.py`.
   - Verify optimization results against known quadratic minimum $(3.0, 4.0)$ with value $5.0$.
3. **Phase 3: Visualization Refactoring & Vectorization (`super_rsm.visualization`)**
   - Extract `plot_multi_contour`, `PlotSettings`, and create `RSMVisualizationService`.
   - Implement vectorized mesh prediction in `grid_builder.py`.
   - Remove top-level `sns.set_theme` side effect on import.
4. **Phase 4: Modular GUI Decomposition & Backward-Compatibility Shims (`super_rsm.gui`)**
   - Decompose `rsm_gui.py` into `styles.py`, `dialogs/`, `panels/`, `widgets/`, and `app.py`.
   - Provide root shims (`rsm_gui.py`, `rsm_backend.py`, `high_d_plotter.py`).
   - Run end-to-end GUI smoke tests and verify backward compatibility.
