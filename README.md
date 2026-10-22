# Super RSM: Multi-Method Response Surface Methodology Analysis & Visualization Tool

This project provides an extensible Python-based tool with a Graphical User Interface (GUI) designed to fit Response Surface Models (RSM) to experimental or simulated datasets and find the optimal input parameters to minimize a target output variable.

Unlike single-method tools, **Super RSM** supports multiple regression methods—including **Gaussian Process Regressor (Kriging)**, **Ridge Regression (RidgeCV)**, and **Genetic Programming (Symbolic Regression)**—within an extensible architecture that makes adding future regression models straightforward, while inheriting advanced multi-dimensional contour plot configurability.

---

## Features
- **Multiple Regression Methods**:
  - **Gaussian Process Regressor (Kriging)**: Supports Ordinary Kriging (constant mean) and Universal Kriging with polynomial drift trends, complete with predictive uncertainty estimation.
  - **Ridge Regression (RidgeCV)**: Fast cross-validated L2-regularized polynomial fitting with automatic unscaling and extraction of polynomial term coefficients.
  - **Genetic Programming (Symbolic Regression)**: Evolutionary symbolic regression powered by `gplearn` (`SymbolicRegressor`) that discovers closed-form mathematical equations and relationships directly from data, complete with support for standard arithmetic functions and custom functions (e.g., piecewise).
- **Extensible Architecture**: Built with a modular registry pattern (`MODEL_REGISTRY` & `register_model`), allowing new regression models to be integrated into the backend and GUI seamlessly.
- **Graphical User Interface (GUI)**:
  - Intuitive interface for loading data (`.csv` and `.xlsx`).
  - Column selection, dynamic optimization bounds specification, polynomial degree adjustment, and test-ratio configuration.
  - Automatic adaptation of results (displaying coefficients for polynomial models like RidgeCV, or mathematical expressions for Genetic Programming).
- **Advanced Plot Configuration & Visualization**:
  - High-dimensional contour and multi-panel ($P \times Q$) subplot visualization powered by `high_d_plotter.py`.
  - **Measurement Data Scatter Overlay**: Option to scatter-plot experimental/simulated data points (both training and test sets) directly on top of contour plots and uncertainty plots, automatically filtering points that match each subplot's Row-Axis ($P$), Column-Axis ($Q$), and Fixed parameter values.
  - **Granular Styling Controls**: Full customization of axes, colormaps (`cmap`), uniform color scaling across subplots, colorbars and labels, transparency (`alpha`), contour fill/line levels, inline contour labels, grids, and scatter marker appearance (size, face color, edge color, and marker style).
  - **Predictive Uncertainty Mapping**: Dedicated secondary uncertainty contour plot generation for uncertainty-capable models (e.g., Gaussian Process), with automatic GUI state handling when switching models or loading settings profiles.
  - **Profile Management**: Save and load complete plot configuration profiles (parameter roles, labels, and advanced styling/scatter settings) as `.json` files.
- **Continuous & Constrained Optimization**: Scipy-powered numerical optimization to identify optimal input parameters that minimize target responses. Supports:
  - **Rectangular Bounds**: Parameter-specific lower and upper limits.
  - **Nonrectangular Linear Constraints**: Arbitrary linear combinations of variables ($\sum c_i x_i \le b$, $\ge b$, or $= b$) configured through an interactive GUI constraint builder or passed directly via `scipy.optimize.LinearConstraint` in the backend.

---

## Getting Started

### Prerequisites
Make sure you have Python 3 installed along with the following packages:
- `numpy`
- `scipy`
- `pandas`
- `scikit-learn`
- `matplotlib`
- `seaborn`
- `openpyxl` (if reading `.xlsx` files)
- `gplearn` (for Genetic Programming / symbolic regression)

You can install the required packages using pip:
```bash
pip install numpy scipy pandas scikit-learn matplotlib seaborn openpyxl gplearn
```

*(Note: `tkinter` is used for the GUI and is included by default with standard Python installations.)*

### Running the Application
To launch the GUI, navigate to the `Code` directory and run:
```bash
python rsm_gui.py
```

---

## GUI Instructions

1. **Load Data**: Browse and load your dataset (`.csv`, `.xlsx`, or `.xls`).
2. **Select Columns**: Choose one or more input independent variables and one target output response variable.
3. **Optimization Bounds (Optional)**: Specify minimum and maximum parameter ranges for individual variables.
4. **Linear Constraints (Optional)**: Click `"Add a constraint"` to define coupled linear constraints across variables (e.g., $1.0 \times \text{Var}_1 + 2.0 \times \text{Var}_2 \le 50.0$) with live algebraic expression preview. Manage multiple constraints via the interactive list (Add, Edit, Delete, Clear).
5. **Model Settings**: Choose the regression method (`Gaussian Process`, `RidgeCV`, or `Genetic Programming`), polynomial degree, and test data ratio.
6. **Run RSM Optimization**: Click to fit the model, display $R^2$, MSE, RMSE, model coefficients (for `RidgeCV`) or discovered mathematical expressions (for `Genetic Programming`), optimized parameter values, and a constraint verification report evaluating all defined linear constraints at the optimal solution.
7. **Configure Plot**: Open the plot configuration window to customize multi-dimensional contour visualizations across three tabs:
   - **Roles Tab**: Assign each input parameter a role:
     - `X-Axis` / `Y-Axis`: Primary 2D contour axes (specify `Min`, `Max`, and grid `Steps`).
     - `Row-Axis (P)` / `Column-Axis (Q)`: Optional subplot grid dimensions for visualizing 3D/4D+ slices (specify comma-separated values).
     - `Fixed`: Hold remaining parameters constant at a specified value.
   - **Labels Tab**: Customize the plot title, X/Y axis labels, colorbar label, and custom prefixes/suffixes for Row-Axis ($P$) and Column-Axis ($Q$) subplot titles.
   - **Advanced Settings Tab**:
     - **Contour & Grid Styling**: Adjust colormap (`cmap`), transparency (`alpha`), fill/line levels, contour line color, inline label color/fontsize/format, and grid color/linestyle.
     - **Colorbar & Scaling**: Toggle `Uniform Colormap` (shared color scale across all subplots) and `Show Colorbar`.
     - **Uncertainty Plotting**: Toggle `Plot Uncertainty (Secondary Window)` to generate an accompanying predictive standard deviation contour plot (automatically enabled only for models supporting uncertainty).
     - **Measurement Data Scatter Overlay**: Toggle `Scatter-Plot Data` to overlay actual dataset points matching each subplot's $P$, $Q$, and fixed parameter values, and configure `Scatter Marker Size`, `Scatter Marker Color`, `Scatter Edge Color`, and `Scatter Marker Style`.
   - **Save / Load Settings**: Export your current plot configuration to a `.json` file or reload a saved configuration profile.

---

## Architecture & Extensibility

The backend (`rsm_backend.py`) uses a modular registry pattern (`MODEL_REGISTRY`) to register and construct regression models dynamically. This design decouples model definition from model fitting and GUI execution, allowing new regression algorithms to be added seamlessly.

The GUI automatically pulls available methods directly from the backend via `get_supported_methods()`, ensuring that any registered model immediately appears in the GUI dropdown without modifying GUI code.

---

### How to Implement a New Regression Method

Adding a new regression method involves two steps:
1. Define a **builder function** that returns an unfitted scikit-learn-compatible estimator or pipeline.
2. Register the builder using `register_model()`.

```python
from rsm_backend import register_model

register_model(
    name="YourMethodName",
    builder=build_your_custom_model,
    supports_uncertainty=False,
    extract_coeffs=False
)
```

---

### Builder Function Specification

A **builder function** is a factory function responsible for instantiating and configuring a regression model before it is fitted. When `fit_rsm2()` is executed, the backend calls the builder function and then fits the returned estimator via `model.fit(X_train, y_train)`.

#### 1. Function Signature

A builder function must accept `degree_fit` and `**kwargs`, and typically accepts `n_samples`:

```python
def build_custom_model(degree_fit=2, n_samples=None, **kwargs):
    """
    Builder function for Custom Regression.

    Parameters:
    -----------
    degree_fit : int, default=2
        The polynomial degree selected in the GUI or passed to fit_rsm2().
        Used when constructing polynomial feature expansions.
    n_samples : int or None, optional
        The number of training samples (len(X_train)).
        Useful for setting adaptive parameters like cross-validation folds (cv).
    **kwargs : dict
        Additional keyword arguments forwarded from fit_rsm2() or rsm_fromDF().

    Returns:
    --------
    model : sklearn.base.BaseEstimator or sklearn.pipeline.Pipeline
        An unfitted scikit-learn estimator or pipeline.
    """
```

#### 2. Estimator Requirements (Return Value)

The returned object must conform to the standard `scikit-learn` estimator interface:
- **`model.fit(X, y)`**: Fits the model on training data ($X \in \mathbb{R}^{N \times D}$, $y \in \mathbb{R}^{N}$).
- **`model.predict(X)`**: Evaluates predictions on input points.
- **`model.predict(X, return_std=True)`** *(Optional)*: If registered with `supports_uncertainty=True`, calling `.predict(X, return_std=True)` must return a 2-element tuple `(y_pred, sigma)`, where `sigma` is the 1D predictive standard deviation for each input point.
- **Pipeline Best Practices**:
  - Wrapping feature transformations and estimators in `sklearn.pipeline.make_pipeline(...)` or `Pipeline([...])` is strongly recommended.
  - Including `PolynomialFeatures(degree=degree_fit, include_bias=False)` allows `generate_term_strings()` to automatically extract and label polynomial terms (e.g., $x_0$, $x_1^2$, $x_0 x_1$).
  - Including `StandardScaler()` helps stabilize numerical regression methods with widely varying input scales.

#### 3. Registration Parameters (`register_model`)

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `name` | `str` | Display name of the method shown in the GUI dropdown and summary printouts. |
| `builder` | `callable` | The builder function adhering to the specification above. |
| `supports_uncertainty` | `bool` | Set to `True` if `model.predict(X, return_std=True)` is implemented. Enables the uncertainty contour plotting option in the GUI and backend. |
| `extract_coeffs` | `bool` | Set to `True` if the model has extractable linear polynomial coefficients (e.g., scaled pipeline with `coef_` and `intercept_`) for displaying unscaled physical equations. |
| `format_expression` | `callable` *(Optional)* | A callable taking `(model)` and returning a string representation of the model's fitted equation/program (e.g., for Genetic Programming). Displayed in summary printouts and the GUI. |

---

### Builder Function Examples

#### Example 1: Standard Polynomial Linear / Regularized Model (e.g., LassoCV)

```python
from sklearn.linear_model import LassoCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from rsm_backend import register_model

def build_lasso_model(degree_fit=2, n_samples=None, **kwargs):
    """
    Builder for Polynomial Lasso regression with cross-validation.
    """
    if degree_fit < 1:
        raise ValueError("degree_fit must be at least 1.")
    
    cv = 5 if (n_samples is None or n_samples >= 5) else None
    
    return make_pipeline(
        PolynomialFeatures(degree=degree_fit, include_bias=False),
        StandardScaler(),
        LassoCV(cv=cv, **kwargs)
    )

# Register the model
register_model(
    name="LassoCV",
    builder=build_lasso_model,
    supports_uncertainty=False,
    extract_coeffs=False
)
```

#### Example 2: Uncertainty-Capable Model (e.g., Custom Gaussian Process)

```python
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern, WhiteKernel
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from rsm_backend import register_model

def build_custom_gp_model(degree_fit=2, **kwargs):
    """
    Builder for Gaussian Process with a Matern kernel and predictive uncertainty.
    """
    kernel = Matern(length_scale=1.0, nu=2.5) + WhiteKernel(noise_level=0.1)
    
    return make_pipeline(
        StandardScaler(),
        GaussianProcessRegressor(kernel=kernel, normalize_y=True, **kwargs)
    )

# Register with supports_uncertainty=True
register_model(
    name="Gaussian Process (Matern)",
    builder=build_custom_gp_model,
    supports_uncertainty=True,
    extract_coeffs=False
)
```

#### Example 3: Symbolic Regression / Genetic Programming (with Expression Formatting)

```python
import numpy as np
from gplearn.genetic import SymbolicRegressor
from gplearn.functions import make_function
from rsm_backend import register_model

def piecewise_function(condition, true_val, false_val):
    return np.where(condition > 0, true_val, false_val)

def build_genetic_programming_model(degree_fit=2, **kwargs):
    """
    Builder for Genetic Programming Symbolic Regression using gplearn.
    """
    piecewise = make_function(function=piecewise_function, name='piecewise', arity=3)
    function_set = ["add", "sub", "mul", "div", "sqrt", "log", piecewise]
    return SymbolicRegressor(
        function_set=function_set,
        population_size=5000,
        generations=30,
        stopping_criteria=0.0,
        p_crossover=0.7,
        p_subtree_mutation=0.1,
        p_hoist_mutation=0.05,
        p_point_mutation=0.1,
        max_samples=0.9,
        parsimony_coefficient=0.005,
        random_state=42,
        const_range=(-30, 30),
        **kwargs
    )

def format_genetic_programming_expression(model):
    """
    Extract and format the discovered mathematical equation.
    """
    if hasattr(model, "_program") and model._program is not None:
        return f"Mathematical Expression:\n  {model._program}"
    return None

# Register with format_expression callback
register_model(
    name="Genetic Programming",
    builder=build_genetic_programming_model,
    supports_uncertainty=False,
    extract_coeffs=False,
    format_expression=format_genetic_programming_expression
)
```



