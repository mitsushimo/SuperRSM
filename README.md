# Super RSM: Multi-Method Response Surface Methodology Analysis & Visualization Suite

**Super RSM** (`super_rsm`) is a modular, extensible Python library and desktop GUI application for fitting multi-dimensional Response Surface Models (RSM), evaluating surrogate predictions with uncertainty bounds, performing continuous constrained optimization, and rendering sliced multi-contour response surfaces.

![Super RSM GUI](readme_images/image.png)

---

## Key Features

- **Extensible Multi-Method Surrogate Modeling (`super_rsm.models`)**:
  - **Polynomial OLS (Classical RSM)**: Ordinary Least Squares polynomial surfaces with coded variable scaling, Moore-Penrose pseudo-inversion (`pinv`) for collinearity safety, two-tailed term $t$-statistics and $p$-values, Adjusted $R^2$, AIC/BIC, and a full Analysis of Variance (ANOVA) table.
  - **Gaussian Process Regressor (Kriging)**: Ordinary Kriging (`degree_fit=0`) and Universal Kriging (`degree_fit >= 1`) with predictive standard deviation ($\pm 1\sigma$ and 95% CI).
  - **Ridge Regression (`RidgeCV`)**: Cross-validated L2-regularized polynomial regression with analytical unscaling of physical coefficients.
  - **Genetic Programming (`SymbolicRegressor`)**: Evolutionary symbolic regression via `gplearn` that discovers closed-form algebraic equations.
- **Zero-Touch Model Plugin Architecture**:
  - Subclass `BaseRSMModel`, declare `metadata: ClassVar[ModelMetadata]` (including `HyperparameterSpec` schemas), and decorate with `@register_rsm_model`. The desktop GUI automatically adds the model to the dropdown and dynamically generates validated parameter controls without modifying any GUI code.
- **100% Headless Analytical Core (`super_rsm.core`)**:
  - Dataset splitting (`RSMDataset`), pipeline orchestration (`fit_rsm`, `rsm_fromDF`), and Scipy constrained continuous optimization (`OptimizationEngine`) operate completely headlessly with zero import-time dependencies on `tkinter`, `matplotlib`, or `seaborn`.
- **Vectorized Surface Grid & Scoped Visualization (`super_rsm.visualization`)**:
  - Evaluates $100 \times 100$ multi-panel ($P \times Q$) contour grids in single vectorized matrix batches ($<15\text{ ms}$) with experimental scatter overlays and scoped matplotlib styling contexts (`PlotSettings`).
- **Modular MVP Desktop GUI (`super_rsm.gui`)**:
  - Decomposed into cohesive views, dialogs, reusable components, reactive `AppState`, and a thread-safe `AppController` (`_run_async`) so long model fits and optimizations never freeze the UI.

---

## Package Architecture (`super_rsm/`)

Super RSM follows a strict 5-layer inward-dependent Directed Acyclic Graph (DAG), with every module kept concise (<350 lines) for human readability and AI maintainability:

```text
SuperRSM/
├── rsm_gui.py                        # Root GUI launcher entrypoint
├── rsm_backend.py                    # Root headless pipeline & registry facade
├── high_d_plotter.py                 # Root visualization facade
├── sample_data.csv                   # Benchmark quadratic dataset
├── tests/                            # Comprehensive pytest suite (baseline, models, core, visualization, gui)
└── super_rsm/
    ├── common/                       # Layer 0: Types, Enums, Exceptions, HyperparameterSpec, ModelMetadata
    ├── models/                       # Layer 1: BaseRSMModel ABC, ModelRegistry, GP, RidgeCV, Symbolic, PolynomialOLS
    ├── core/                         # Layer 2: Headless RSMDataset, RSMResult, OptimizationEngine, pipeline
    ├── visualization/                # Layer 3: PlotSettings, vectorized GridSampler, MultiContourEngine, VisualizationService
    └── gui/                          # Layer 4: MVP Desktop UI (RSMApp, AppController, AppState, views/, dialogs/, components/, styles/)
```

---

## Installation & Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Launch the Desktop GUI
```bash
python -m super_rsm
# or:
python rsm_gui.py
```

### 3. Run the Automated Test Suite
```bash
pytest -v
```

---

## Headless Python API Usage

```python
import pandas as pd
from super_rsm import rsm_fromDF, ConstraintSpec, ConstraintOperator

df = pd.read_csv("sample_data.csv")

# Fit Classical Polynomial OLS (with ANOVA & p-values)
result = rsm_fromDF(
    df=df,
    input_columns=["x1", "x2"],
    output_column="y",
    method="Polynomial OLS",
    degree_fit=2,
)
print(result.summary())

# Constrained continuous optimization (e.g., x1 + x2 <= 6.0)
constraint = ConstraintSpec(coeffs={"x1": 1.0, "x2": 1.0}, operator=ConstraintOperator.LE, bound=6.0)
opt = result.optimize(bounds={"x1": (0.0, 10.0), "x2": (0.0, 10.0)}, constraints=[constraint], maximize=False)
print(f"Optimal parameters: {opt.to_dict(['x1', 'x2'])}, Minimum y = {opt.fun:.4f}")
```

---

## How to Add a Custom Regression Model (Zero GUI Edits)

To add a new regression model that automatically integrates into both the headless pipeline and the desktop GUI:

1. Create a new module in `super_rsm/models/` (or in your user script) subclassing `BaseRSMModel`.
2. Declare `metadata: ClassVar[ModelMetadata]` with `HyperparameterSpec` items.
3. Decorate the class with `@register_rsm_model`.

```python
from typing import Any, ClassVar, List, Optional
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score

from super_rsm import (
    BaseRSMModel,
    HyperparameterSpec,
    ModelCategory,
    ModelMetadata,
    ModelMetrics,
    register_rsm_model,
)


@register_rsm_model
class RandomForestRSMModel(BaseRSMModel):
    metadata: ClassVar[ModelMetadata] = ModelMetadata(
        name="Random Forest",
        display_name="Random Forest Regressor",
        category=ModelCategory.ENSEMBLE,
        description="Non-parametric tree ensemble regressor with feature importances.",
        supports_uncertainty=False,
        supports_feature_importance=True,
        hyperparameters=[
            HyperparameterSpec("n_estimators", "Trees", int, default=100, min_val=10, max_val=1000, step=10),
            HyperparameterSpec("max_depth", "Max Depth", int, default=6, min_val=1, max_val=30, step=1),
        ],
    )

    def __init__(self, n_estimators: int = 100, max_depth: int = 6, **kwargs: Any):
        super().__init__(n_estimators=n_estimators, max_depth=max_depth, **kwargs)
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.estimator: Optional[RandomForestRegressor] = None

    def fit(self, X: np.ndarray, y: np.ndarray, feature_names: Optional[List[str]] = None, **kwargs: Any) -> "RandomForestRSMModel":
        X_arr = np.asarray(X, dtype=float)
        y_arr = np.asarray(y, dtype=float).ravel()
        self.feature_names = list(feature_names) if feature_names else [f"x{i+1}" for i in range(X_arr.shape[1])]

        self.estimator = RandomForestRegressor(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            random_state=42,
        )
        self.estimator.fit(X_arr, y_arr)
        self.X_train, self.y_train = X_arr, y_arr
        self.is_fitted = True

        y_pred = self.estimator.predict(X_arr)
        mse = float(mean_squared_error(y_arr, y_pred))
        self.metrics = ModelMetrics(r2=float(r2_score(y_arr, y_pred)), rmse=float(np.sqrt(mse)), mse=mse)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        self._ensure_fitted()
        X_arr = np.asarray(X, dtype=float)
        if X_arr.ndim == 1:
            X_arr = X_arr.reshape(1, -1)
        return np.asarray(self.estimator.predict(X_arr), dtype=float).ravel()
```
