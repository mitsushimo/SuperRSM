# Milestone M1 Investigation Report: Standard Models, PolynomialOLSModel & Unit Test Specifications

**Working Directory**: `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\teamwork_explorer_m1_3`  
**Date**: October 30, 2026  
**Investigator**: Teamwork Explorer 3  
**Target Milestone**: M1 (Foundations, Baseline & Models Subsystem)  

---

## 1. Observation

Direct empirical observations, codebase inspections, and verification runs conducted on the workspace:

### 1.1 Existing Model Implementations in `rsm_backend.py`
- **Gaussian Process Regressor** (`rsm_backend.py:30-48`):
  ```python
  def build_gaussian_process_model(degree_fit=2, **kwargs):
      if degree_fit == 0:
          kernel = 1.0 * RBF(length_scale=1.0) + WhiteKernel(noise_level=0.1)
          return make_pipeline(StandardScaler(), GaussianProcessRegressor(kernel=kernel, normalize_y=True))
      else:
          kernel = DotProduct(sigma_0=1.0) + RBF(length_scale=1.0) + WhiteKernel(noise_level=0.1)
          return make_pipeline(PolynomialFeatures(degree=degree_fit, include_bias=False), StandardScaler(), GaussianProcessRegressor(kernel=kernel))
  ```
  - When `degree_fit == 0`, it executes Ordinary Kriging with a constant mean trend (`normalize_y=True`) and an RBF + WhiteKernel.
  - When `degree_fit > 0`, it executes Universal Kriging with polynomial features (`include_bias=False`), StandardScaler, and DotProduct + RBF + WhiteKernel.
  - **Empirical test**: `pipeline.predict(X, return_std=True)` successfully passes through scikit-learn's pipeline to return `(y_pred, sigma)`. On `sample_data.csv`, Ordinary Kriging (`degree_fit=0`) achieves $R^2 = 0.99892$, evaluating at $(3.0, 4.0)$ to $4.9144 \pm 0.6186$.

- **RidgeCV Regressor & Unscaled Coefficients** (`rsm_backend.py:51-64`, `178-186`):
  ```python
  def build_ridge_model(degree_fit=2, n_samples=None, **kwargs):
      alphas = np.logspace(-6, 6, 13)
      cv = 5 if (n_samples is None or n_samples >= 5) else None
      return make_pipeline(PolynomialFeatures(degree=degree_fit, include_bias=False), StandardScaler(), RidgeCV(alphas=alphas, cv=cv))
  ```
  - Unscaling logic in `rsm_backend.py:183-184`:
    $$\mathbf{\beta}_{\text{unscaled}} = \frac{\mathbf{\beta}_{\text{ridge}}}{\mathbf{\sigma}_{\text{scaler}}}, \quad \beta_{0, \text{unscaled}} = \beta_{0, \text{ridge}} - \mathbf{\beta}_{\text{unscaled}} \cdot \mathbf{\mu}_{\text{scaler}}$$
  - **Empirical test**: On `sample_data.csv`, RidgeCV (`degree_fit=2`) yields:
    - $R^2 = 0.99915$
    - Intercept: $29.6152$ (Theoretical: $30.0$)
    - Linear coefficients: $x_1 = -5.8192$ (Theoretical: $-6.0$), $x_2 = -7.9433$ (Theoretical: $-8.0$)
    - Quadratic coefficients: $x_1^2 = 0.9831$ (Theoretical: $1.0$), $x_1 x_2 = -0.0044$ (Theoretical: $0.0$), $x_2^2 = 0.9939$ (Theoretical: $1.0$)
    - Point evaluation at $(3.0, 4.0)$ yields $5.0813$ (Theoretical minimum: $5.0$).

- **Genetic Programming Symbolic Regressor** (`rsm_backend.py:67-103`):
  - Uses `gplearn.genetic.SymbolicRegressor` with custom primitive `piecewise_function(condition, true_val, false_val) = np.where(condition > 0, true_val, false_val)`.
  - Format expression extracts `model._program`.
  - **Empirical test**: `model._program` produces nested functional trees such as `add(sub(-0.818, sub(sub(X1, 0.802), X0)), add(X1, add(0.078, X1)))`.
  - With regex substitution `re.sub(r'\bX(\d+)\b', ...)`, generic `X0, X1` tokens map cleanly to physical input names (e.g. `x1, x2`).

### 1.2 Mathematical Behavior of Classical OLS & Singular Matrix Vulnerability
- Traditional matrix inversion `np.linalg.inv(Phi.T @ Phi)` on collinear data:
  ```
  Traceback (most recent call last):
    File "numpy/linalg/_linalg.py", line 608, in inv
    ...
  numpy.linalg.LinAlgError: Singular matrix
  ```
- Moore-Penrose pseudo-inversion `np.linalg.pinv(Phi.T @ Phi)` and `np.linalg.lstsq(Phi, y, rcond=None)`:
  - Executes cleanly on collinear matrices with rank $r < P$.
  - Successfully computes minimum-norm parameter vectors and pseudo-inverse covariance matrices without raising `LinAlgError`.

### 1.3 ANOVA & Statistical Hypothesis Testing on `sample_data.csv`
- Testing `PolynomialOLSModel` formulation on `sample_data.csv`:
  - $N = 100$, $P = 6$ terms ($1, x_1, x_2, x_1^2, x_1 x_2, x_2^2$), $df_{\text{resid}} = 94$.
  - $R^2 = 0.99875$, $R^2_{\text{adj}} = 0.99869$, $RSS = 29.9771$, $MSE = 0.2998$, $RMSE = 0.5475$.
  - Term statistics computed via pseudo-inverse covariance:
    * `Intercept`: $\beta = 29.8318$, $SE = 0.2675$, $t = 111.52$, $p = 0.0000$ (Significant)
    * `x1`: $\beta = -5.9131$, $SE = 0.0840$, $t = -70.44$, $p = 0.0000$ (Significant)
    * `x2`: $\beta = -7.9950$, $SE = 0.0872$, $t = -91.69$, $p = 0.0000$ (Significant)
    * `x1^2`: $\beta = 0.9917$, $SE = 0.0078$, $t = 126.79$, $p = 0.0000$ (Significant)
    * `x1 x2`: $\beta = -0.0048$, $SE = 0.0068$, $t = -0.71$, $p = 0.4806$ (NOT significant, $p > 0.05$)
    * `x2^2`: $\beta = 1.0008$, $SE = 0.0078$, $t = 127.61$, $p = 0.0000$ (Significant)
  - ANOVA decomposition:
    * $SS_{\text{model}} = 24046.85$, $df = 5$, $MS = 4809.37$, $F = 15080.59$, $p = 0.0000$
    * $SS_{\text{resid}} = 29.98$, $df = 94$, $MS = 0.3189$
    * $SS_{\text{total}} = 24076.83$, $df = 99$
  - Perfectly reflects the known truth: the true function $y = (x_1-3)^2 + (x_2-4)^2 + 5$ contains no interaction term $x_1 x_2$, which `PolynomialOLSModel` statistically confirms ($p = 0.4806$).

---

## 2. Logic Chain

From the observations, we deduce the concrete specifications for the four regression models in `super_rsm/models/` and their unit tests in `tests/test_models.py`:

```
+----------------------------------------------------------------------------------------------------+
|                                    super_rsm.models.base.BaseRSMModel                               |
|   - ClassVar metadata: ModelMetadata                                                                |
|   - Abstract methods: fit(X, y, feature_names=None, **kwargs), predict(X)                          |
|   - Virtual methods: predict_with_uncertainty, evaluate_point, get_formula, get_coefficients, etc.   |
+----------------------------------------------------------------------------------------------------+
                   ▲                             ▲                          ▲                        ▲
                   │                             │                          │                        │
+-------------------------+ +-------------------------+ +------------------------+ +------------------------+
| GaussianProcessRSMModel | |     RidgeCVRSMModel     | | SymbolicRegressorModel | |   PolynomialOLSModel   |
| (Ordinary & Universal   | | (Polynomial Features,   | | (Genetic Programming,  | | (Classical RSM, pinv,  |
|  Kriging + Uncertainty) | |  Analytical Unscaling)  | |  gplearn Expression)   | |  ANOVA, term p-values) |
+-------------------------+ +-------------------------+ +------------------------+ +------------------------+
```

### 2.1 Specification for `super_rsm/models/gaussian_process.py` (`GaussianProcessRSMModel`)

1. **Class Header & Registration**:
   - Class name: `GaussianProcessRSMModel(BaseRSMModel)`
   - Decorator: `@register_rsm_model`
   - Static metadata (`ClassVar[ModelMetadata]`):
     - `name`: `"Gaussian Process"`
     - `display_name`: `"Gaussian Process (Kriging)"`
     - `category`: `ModelCategory.KERNEL`
     - `description`: `"Gaussian Process Regressor (Kriging) supporting Ordinary (degree=0) and Universal Kriging (degree>0) with predictive uncertainty estimation."`
     - `supports_uncertainty`: `True`
     - `supports_coefficients`: `False`
     - `supports_feature_importance`: `False`
     - `supports_formula`: `False`
     - `has_anova`: `False`
     - `hyperparameters`:
       * `degree_fit`: `int`, default `2`, min `0`, max `4`, step `1`, tooltip `"Polynomial trend degree (0=Ordinary Kriging, >0=Universal Kriging with drift)"`
       * `length_scale`: `float`, default `1.0`, min `0.01`, max `100.0`, step `0.5`, tooltip `"Initial RBF length scale parameter"`
       * `noise_level`: `float`, default `0.1`, min `1e-5`, max `10.0`, step `0.05`, tooltip `"WhiteKernel observation noise variance level"`
       * `n_restarts_optimizer`: `int`, default `0`, min `0`, max `10`, step `1`, tooltip `"Number of kernel hyperparameter optimizer restarts"`
       * `random_state`: `int`, default `42`, min `0`, max `99999`, step `1`, tooltip `"Random seed for reproducibility"`

2. **Constructor (`__init__`)**:
   ```python
   def __init__(
       self,
       degree_fit: int = 2,
       length_scale: float = 1.0,
       noise_level: float = 0.1,
       n_restarts_optimizer: int = 0,
       random_state: int = 42,
       **kwargs: Any
   ):
       super().__init__(
           degree_fit=degree_fit,
           length_scale=length_scale,
           noise_level=noise_level,
           n_restarts_optimizer=n_restarts_optimizer,
           random_state=random_state,
           **kwargs
       )
       self.degree_fit = degree_fit
       self.length_scale = length_scale
       self.noise_level = noise_level
       self.n_restarts_optimizer = n_restarts_optimizer
       self.random_state = random_state
       self.pipeline: Optional[Any] = None
   ```

3. **Fitting (`fit`)**:
   - Updates any overridden hyperparameters from `kwargs`.
   - Assembles scikit-learn pipeline:
     * If `self.degree_fit == 0`:
       `kernel = 1.0 * RBF(length_scale=self.length_scale) + WhiteKernel(noise_level=self.noise_level)`
       `self.pipeline = make_pipeline(StandardScaler(), GaussianProcessRegressor(kernel=kernel, normalize_y=True, n_restarts_optimizer=self.n_restarts_optimizer, random_state=self.random_state))`
     * If `self.degree_fit > 0`:
       `kernel = DotProduct(sigma_0=1.0) + RBF(length_scale=self.length_scale) + WhiteKernel(noise_level=self.noise_level)`
       `self.pipeline = make_pipeline(PolynomialFeatures(degree=self.degree_fit, include_bias=False), StandardScaler(), GaussianProcessRegressor(kernel=kernel, normalize_y=False, n_restarts_optimizer=self.n_restarts_optimizer, random_state=self.random_state))`
   - Fits pipeline on `X` and `y`.
   - Computes $R^2$, RMSE, MSE on training data and populates `self.metrics = ModelMetrics(r2=float(r2), rmse=float(rmse), mse=float(mse))`.
   - Sets `self.is_fitted = True` and returns `self`.

4. **Prediction (`predict` & `predict_with_uncertainty`)**:
   - `predict(self, X: np.ndarray) -> np.ndarray`:
     Ensures fitted. Converts 1D inputs to 2D `(1, -1)`. Calls `self.pipeline.predict(X_arr)` and returns 1D float array `(N,)`.
   - `predict_with_uncertainty(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]`:
     Ensures fitted. Calls `self.pipeline.predict(X_arr, return_std=True)`. Returns `(np.asarray(y_pred, dtype=float).ravel(), np.asarray(sigma, dtype=float).ravel())`.

---

### 2.2 Specification for `super_rsm/models/ridge.py` (`RidgeCVRSMModel`)

1. **Class Header & Registration**:
   - Class name: `RidgeCVRSMModel(BaseRSMModel)`
   - Decorator: `@register_rsm_model`
   - Static metadata (`ClassVar[ModelMetadata]`):
     - `name`: `"RidgeCV"`
     - `display_name`: `"RidgeCV (L2 Regularized Polynomial)"`
     - `category`: `ModelCategory.POLYNOMIAL`
     - `description`: `"Ridge regression with cross-validation on polynomial features. Extracts unscaled physical coefficients and prevents overfitting."`
     - `supports_uncertainty`: `False`
     - `supports_coefficients`: `True`
     - `supports_feature_importance`: `True`
     - `supports_formula`: `True`
     - `has_anova`: `False`
     - `hyperparameters`:
       * `degree_fit`: `int`, default `2`, min `1`, max `4`, step `1`, tooltip `"Degree of polynomial features"`
       * `alphas_count`: `int`, default `13`, min `5`, max `50`, step `1`, tooltip `"Number of log-spaced alpha penalties in [1e-6, 1e6]"`
       * `cv`: `Optional[int]`, default `5`, min `2`, max `10`, step `1`, tooltip `"Cross-validation folds (None for Leave-One-Out generalized CV)"`

2. **Constructor (`__init__`)**:
   ```python
   def __init__(
       self,
       degree_fit: int = 2,
       alphas_count: int = 13,
       cv: Optional[int] = 5,
       **kwargs: Any
   ):
       super().__init__(degree_fit=degree_fit, alphas_count=alphas_count, cv=cv, **kwargs)
       self.degree_fit = degree_fit
       self.alphas_count = alphas_count
       self.cv = cv
       self.pipeline: Optional[Any] = None
       self.unscaled_coeffs: Optional[np.ndarray] = None
       self.unscaled_intercept: Optional[float] = None
       self.term_names: List[str] = []
   ```

3. **Fitting & Analytical Unscaling (`fit`)**:
   - Validates `degree_fit >= 1`.
   - Folds selection: if $N_{\text{samples}} < 5$, automatically falls back to `cv = None` to avoid fold-size errors.
   - Pipeline assembly:
     1. `poly_step`: `PolynomialFeatures(degree=self.degree_fit, include_bias=False)`
     2. `scaler_step`: `StandardScaler()`
     3. `ridge_step`: `RidgeCV(alphas=np.logspace(-6, 6, self.alphas_count), cv=cv_actual)`
   - Fits pipeline on `X` and `y`.
   - Unscaling computation:
     ```python
     scaler = self.pipeline.named_steps["standardscaler"]
     ridge = self.pipeline.named_steps["ridgecv"]
     poly = self.pipeline.named_steps["polynomialfeatures"]

     self.term_names = list(poly.get_feature_names_out(self.feature_names))
     safe_scale = np.where(scaler.scale_ > 1e-12, scaler.scale_, 1.0)
     self.unscaled_coeffs = ridge.coef_ / safe_scale
     self.unscaled_intercept = float(ridge.intercept_ - np.dot(self.unscaled_coeffs, scaler.mean_))
     ```
   - Populates `self.metrics = ModelMetrics(r2=float(r2), rmse=float(rmse), mse=float(mse))`.
   - Sets `self.is_fitted = True` and returns `self`.

4. **Coefficient, Formula & Importance Accessors**:
   - `get_coefficients(self) -> Dict[str, float]`:
     Returns `{"Intercept": self.unscaled_intercept, **{t: float(c) for t, c in zip(self.term_names, self.unscaled_coeffs)}}`.
   - `get_formula(self) -> str`:
     Returns formatted string:
     `"y = 29.6152 - 5.8192*x1 - 7.9433*x2 + 0.9831*x1^2 - 0.0044*x1 x2 + 0.9939*x2^2"`.
   - `get_feature_importance(self) -> Dict[str, float]`:
     Computes normalized standardized coefficient magnitude:
     `abs_c = np.abs(self.pipeline.named_steps["ridgecv"].coef_)`
     `norm = np.sum(abs_c)`
     Returns `{t: float(c / norm) for t, c in zip(self.term_names, abs_c)}`.

---

### 2.3 Specification for `super_rsm/models/symbolic.py` (`SymbolicRegressorRSMModel`)

1. **Class Header & Registration**:
   - Class name: `SymbolicRegressorRSMModel(BaseRSMModel)`
   - Decorator: `@register_rsm_model`
   - Static metadata (`ClassVar[ModelMetadata]`):
     - `name`: `"Genetic Programming"`
     - `display_name`: `"Genetic Programming (Symbolic Regressor)"`
     - `category`: `ModelCategory.SYMBOLIC`
     - `description`: `"Symbolic regression using genetic programming (gplearn). Discovers analytical closed-form mathematical equations directly from data."`
     - `supports_uncertainty`: `False`
     - `supports_coefficients`: `False`
     - `supports_feature_importance`: `False`
     - `supports_formula`: `True`
     - `has_anova`: `False`
     - `hyperparameters`:
       * `population_size`: `int`, default `2000`, min `50`, max `20000`, step `50`, tooltip `"Number of candidate formula programs per generation"`
       * `generations`: `int`, default `20`, min `2`, max `100`, step `1`, tooltip `"Number of genetic evolutionary generations"`
       * `parsimony_coefficient`: `float`, default `0.005`, min `0.0001`, max `0.1`, step `0.001`, tooltip `"Penalty weight on equation tree complexity"`
       * `random_state`: `int`, default `42`, min `0`, max `99999`, step `1`, tooltip `"Random seed for search reproducibility"`

2. **Primitive Definition**:
   ```python
   def piecewise_function(condition: np.ndarray, true_val: np.ndarray, false_val: np.ndarray) -> np.ndarray:
       """Piecewise step function primitive for genetic programming."""
       return np.where(condition > 0, true_val, false_val)
   ```

3. **Fitting & Model Construction (`fit`)**:
   - Assembles gplearn `SymbolicRegressor`:
     ```python
     piecewise = make_function(function=piecewise_function, name="piecewise", arity=3)
     function_set = ["add", "sub", "mul", "div", "sqrt", "log", piecewise]
     self.model = SymbolicRegressor(
         function_set=function_set,
         population_size=self.population_size,
         generations=self.generations,
         stopping_criteria=0.0,
         p_crossover=0.7,
         p_subtree_mutation=0.1,
         p_hoist_mutation=0.05,
         p_point_mutation=0.1,
         max_samples=0.9,
         parsimony_coefficient=self.parsimony_coefficient,
         random_state=self.random_state,
         const_range=(-30, 30),
     )
     self.model.fit(X, y)
     ```
   - Sets `self.is_fitted = True` and computes standard `ModelMetrics`.

4. **Formula Extraction with Variable Mapping**:
   - `get_formula(self) -> Optional[str]`:
     ```python
     if not hasattr(self.model, "_program") or self.model._program is None:
         return None
     expr_str = str(self.model._program)
     # Substitute X0, X1 with feature_names using regex word boundaries
     def repl(match: re.Match) -> str:
         idx = int(match.group(1))
         if idx < len(self.feature_names):
             return self.feature_names[idx]
         return match.group(0)
     formatted = re.sub(r"\bX(\d+)\b", repl, expr_str)
     return f"y = {formatted}"
     ```
   - Also provides legacy formatting function: `format_genetic_programming_expression(model)`.

---

### 2.4 Specification for `super_rsm/models/polynomial_ols.py` (`PolynomialOLSModel`)

1. **Class Header & Registration**:
   - Class name: `PolynomialOLSModel(BaseRSMModel)`
   - Decorator: `@register_rsm_model`
   - Static metadata (`ClassVar[ModelMetadata]`):
     - `name`: `"Polynomial OLS"`
     - `display_name`: `"Polynomial OLS (with p-values & ANOVA)"`
     - `category`: `ModelCategory.POLYNOMIAL`
     - `description`: `"Classical RSM: Ordinary Least Squares polynomial surface with coded units [-1, +1], Moore-Penrose pseudo-inversion for collinear data robustness, full ANOVA table, term t-stats, p-values, and AIC/BIC."`
     - `supports_uncertainty`: `False`
     - `supports_coefficients`: `True`
     - `supports_feature_importance`: `True`
     - `supports_formula`: `True`
     - `has_anova`: `True`
     - `hyperparameters`:
       * `degree_fit`: `int`, default `2`, min `1`, max `4`, step `1`, tooltip `"Degree of polynomial surface (1=Linear, 2=Quadratic with interactions, 3=Cubic)"`
       * `coded_units`: `bool`, default `False`, tooltip `"Transform features to [-1, +1] coded scale for numerical conditioning"`

2. **Constructor (`__init__`)**:
   ```python
   def __init__(self, degree_fit: int = 2, coded_units: bool = False, **kwargs: Any):
       super().__init__(degree_fit=degree_fit, coded_units=coded_units, **kwargs)
       self.degree_fit = degree_fit
       self.coded_units = coded_units
       self.poly: Optional[PolynomialFeatures] = None
       self.term_names: List[str] = []
       self.beta: Optional[np.ndarray] = None
       self.residuals: Optional[np.ndarray] = None
       self.df_resid: int = 0
       self._x_mins: Optional[np.ndarray] = None
       self._x_maxs: Optional[np.ndarray] = None
   ```

3. **Coded Units Transformation**:
   - When `self.coded_units == True`:
     $$\mathbf{z}_j = \frac{2\mathbf{x}_j - (b_j + a_j)}{b_j - a_j} \in [-1, +1]$$
     If $b_j == a_j$, $\mathbf{z}_j = 0.0$.
   - Training stores `self._x_mins` and `self._x_maxs`.
   - `predict(X)` applies the identical transformation before polynomial expansion.

4. **SVD Least Squares & Moore-Penrose Pseudo-Inversion**:
   - Check sample size: if $N \le P$, raise `ValueError(f"Sample size (N={n_samples}) must exceed number of polynomial terms (P={p_terms}). Reduce polynomial degree or collect more experimental runs.")`.
   - SVD Solve: `beta, residuals_sum, rank, s = np.linalg.lstsq(Phi, y, rcond=None)`.
   - Pseudo-inverse Covariance: `phi_cov = np.linalg.pinv(Phi.T @ Phi)`.
   - Guarantees zero crash on collinear data ($rank < P$).

5. **Statistical Metrics & ANOVA Table**:
   - $df_{\text{resid}} = n_{\text{samples}} - p_{\text{terms}}$
   - $RSS = \sum (y_i - \hat{y}_i)^2$, $s^2 = RSS / df_{\text{resid}}$
   - $TSS = \sum (y_i - \bar{y})^2$, $SS_{\text{reg}} = TSS - RSS$
   - Standard Errors: $SE(\beta) = \sqrt{\text{clip}(\text{diag}(\text{cov}), 0) \cdot s^2}$
   - $t$-stats & $p$-values:
     $$t_k = \frac{\beta_k}{SE(\beta_k)}, \quad p_k = 2 \left(1 - F_t(|t_k|, df=df_{\text{resid}})\right)$$
   - ANOVA DataFrame:
     ```python
     ms_reg = ss_reg / (p_terms - 1) if p_terms > 1 else 0.0
     f_stat = ms_reg / s_sq if s_sq > 0 else np.nan
     f_p_val = 1.0 - stats.f.cdf(f_stat, p_terms - 1, df_resid) if s_sq > 0 else np.nan

     anova_df = pd.DataFrame({
         "Source": ["Model (Regression)", "Residual (Error)", "Total"],
         "SS": [ss_reg, rss, tss],
         "df": [p_terms - 1, df_resid, n_samples - 1],
         "MS": [ms_reg, s_sq, np.nan],
         "F-Value": [f_stat, np.nan, np.nan],
         "p-Value": [f_p_val, np.nan, np.nan]
     })
     ```
   - Fit Diagnostics:
     $$R^2 = 1 - \frac{RSS}{TSS}, \quad R^2_{\text{adj}} = 1 - (1 - R^2)\frac{n - 1}{df_{\text{resid}}}$$
     $$AIC = n \ln\left(\frac{RSS}{n}\right) + 2 P, \quad BIC = n \ln\left(\frac{RSS}{n}\right) + P \ln(n)$$

---

### 2.5 Detailed Unit Test Specifications for `tests/test_models.py`

The test suite must cover 6 primary test suites with 16 distinct test cases:

```
tests/test_models.py
├── TestModelRegistry (3 tests)
│   ├── test_registry_contains_all_four_models
│   ├── test_registry_metadata_introspection_without_instantiation
│   └── test_registry_unknown_model_raises_keyerror
├── TestGaussianProcessRSMModel (4 tests)
│   ├── test_gp_universal_kriging_sample_data
│   ├── test_gp_ordinary_kriging_degree_0_accuracy
│   ├── test_gp_predict_with_uncertainty
│   └── test_gp_unfitted_raises_runtime_error
├── TestRidgeCVRSMModel (4 tests)
│   ├── test_ridge_fit_predict_sample_data
│   ├── test_ridge_unscaled_coefficients_accuracy
│   ├── test_ridge_formula_and_importance
│   └── test_ridge_small_sample_generalized_cv_fallback
├── TestSymbolicRegressorRSMModel (3 tests)
│   ├── test_symbolic_fit_predict_fast
│   ├── test_symbolic_formula_variable_substitution
│   └── test_symbolic_piecewise_primitive
├── TestPolynomialOLSModel (5 tests)
│   ├── test_ols_fit_predict_sample_data_accuracy
│   ├── test_ols_anova_table_decomposition
│   ├── test_ols_term_p_values_identifies_insignificant_interaction
│   ├── test_ols_collinear_data_robustness_with_pseudo_inverse
│   ├── test_ols_coded_units_transformation
│   └── test_ols_underdetermined_samples_raises_value_error
└── TestPolymorphicModelInterface (2 tests)
    ├── test_all_models_evaluate_point_scalar_contract
    └── test_all_models_vectorized_batch_predict_shape
```

#### Detailed Test Logic & Expected Assertions:

1. **`test_registry_contains_all_four_models`**:
   - Asserts `"Gaussian Process" in ModelRegistry.list_names()`
   - Asserts `"RidgeCV" in ModelRegistry.list_names()`
   - Asserts `"Genetic Programming" in ModelRegistry.list_names()`
   - Asserts `"Polynomial OLS" in ModelRegistry.list_names()`

2. **`test_registry_metadata_introspection_without_instantiation`**:
   - For all 4 names, calls `meta = ModelRegistry.get_metadata(name)`.
   - Asserts `isinstance(meta, ModelMetadata)`.
   - Asserts `meta.name` matches registry key.
   - Asserts `len(meta.hyperparameters) > 0`.
   - Confirms zero instances of models are created (pure static metadata).

3. **`test_gp_ordinary_kriging_degree_0_accuracy`**:
   - Loads `sample_data.csv` ($X \in [0, 10]^2, y = (x_1-3)^2 + (x_2-4)^2 + 5$).
   - Fits `GaussianProcessRSMModel(degree_fit=0, noise_level=0.1)`.
   - Asserts $R^2 > 0.95$.
   - Evaluates at $(3.0, 4.0)$ via `model.evaluate_point([3.0, 4.0], return_std=True)`.
   - Asserts `abs(mean - 5.0) < 0.5`.
   - Asserts `sigma > 0.0` and `sigma < 2.0`.

4. **`test_gp_predict_with_uncertainty`**:
   - Calls `y_pred, sigma = model.predict_with_uncertainty(X)`.
   - Asserts `y_pred.shape == (len(X),)`.
   - Asserts `sigma.shape == (len(X),)`.
   - Asserts `np.all(sigma >= 0.0)`.

5. **`test_ridge_unscaled_coefficients_accuracy`**:
   - Fits `RidgeCVRSMModel(degree_fit=2)` on `sample_data.csv`.
   - Asserts $R^2 > 0.99$.
   - Obtains `coeffs = model.get_coefficients()`.
   - Asserts `abs(coeffs["Intercept"] - 30.0) < 2.0`.
   - Asserts `abs(coeffs["x1"] - (-6.0)) < 1.0`.
   - Asserts `abs(coeffs["x2"] - (-8.0)) < 1.0`.
   - Asserts `abs(coeffs["x1^2"] - 1.0) < 0.2`.
   - Asserts `abs(coeffs["x1 x2"] - 0.0) < 0.2`.
   - Asserts `abs(coeffs["x2^2"] - 1.0) < 0.2`.

6. **`test_ridge_small_sample_generalized_cv_fallback`**:
   - Calls `RidgeCVRSMModel(degree_fit=1).fit(X[:4], y[:4])` ($N=4 < 5$).
   - Asserts no exception is raised and model fits successfully.

7. **`test_symbolic_fit_predict_fast`**:
   - Fits `SymbolicRegressorRSMModel(population_size=100, generations=3, random_state=42)` on first 20 samples of `sample_data.csv`.
   - Asserts `model.is_fitted is True`.
   - Asserts `model.predict(X[:5]).shape == (5,)`.
   - Asserts formula is extracted via `model.get_formula()`.
   - Checks that variable tokens `X0` and `X1` are replaced with `x1` and `x2`.

8. **`test_ols_fit_predict_sample_data_accuracy`**:
   - Fits `PolynomialOLSModel(degree_fit=2)` on `sample_data.csv`.
   - Metrics assertions:
     * `metrics.r2 > 0.995`
     * `metrics.adj_r2 > 0.995`
     * `metrics.rmse < 0.7`
   - Coefficient assertions:
     * `abs(model.get_coefficients()["Intercept"] - 29.83) < 0.5`
     * `abs(model.get_coefficients()["x1"] - (-5.91)) < 0.2`
     * `abs(model.get_coefficients()["x2"] - (-7.99)) < 0.2`
     * `abs(model.get_coefficients()["x1^2"] - 0.99) < 0.1`
     * `abs(model.get_coefficients()["x1 x2"] - 0.00) < 0.1`
     * `abs(model.get_coefficients()["x2^2"] - 1.00) < 0.1`

9. **`test_ols_anova_table_decomposition`**:
   - Inspects `metrics.anova_table`.
   - Asserts table has 3 rows: `"Model (Regression)"`, `"Residual (Error)"`, `"Total"`.
   - Asserts $SS_{\text{model}} + SS_{\text{resid}} \approx SS_{\text{total}}$ within $1e-4$.
   - Asserts $df_{\text{model}} + df_{\text{resid}} == df_{\text{total}}$ ($5 + 94 == 99$).
   - Asserts model $p$-value $< 1e-5$.

10. **`test_ols_term_p_values_identifies_insignificant_interaction`**:
    - Inspects `metrics.term_p_values`:
      * `term_p_values["Intercept"] < 0.001`
      * `term_p_values["x1"] < 0.001`
      * `term_p_values["x2"] < 0.001`
      * `term_p_values["x1^2"] < 0.001`
      * `term_p_values["x2^2"] < 0.001`
      * `term_p_values["x1 x2"] > 0.05` ($p \approx 0.48$) -> Accurately verifies that $x_1 x_2$ is statistically insignificant.

11. **`test_ols_collinear_data_robustness_with_pseudo_inverse`**:
    - Synthesizes collinear dataset where $x_2 = 2.0 \cdot x_1 + 0.0$.
    - Verifies `np.linalg.inv(Phi.T @ Phi)` raises `numpy.linalg.LinAlgError`.
    - Verifies `PolynomialOLSModel(degree_fit=2).fit(X_collinear, y)` succeeds WITHOUT raising `LinAlgError`.
    - Verifies `predict()` returns valid numeric predictions.
    - Verifies $t$-statistics and $p$-values are computed safely without crashing.

12. **`test_ols_underdetermined_samples_raises_value_error`**:
    - Attempts to fit quadratic model (6 terms) with only 5 samples.
    - Asserts `pytest.raises(ValueError)` with error text mentioning sample size $N$ must exceed polynomial terms $P$.

13. **`test_all_models_evaluate_point_scalar_contract`**:
    - For each model class in `[GaussianProcessRSMModel, RidgeCVRSMModel, SymbolicRegressorRSMModel, PolynomialOLSModel]`:
    - Evaluates `val, std = model.evaluate_point([3.0, 4.0])`.
    - Asserts `isinstance(val, float)`.
    - If model supports uncertainty, asserts `isinstance(std, float)`; otherwise `std is None`.

14. **`test_all_models_vectorized_batch_predict_shape`**:
    - For each model class:
    - Pass $X_{\text{batch}}$ of shape $(25, 2)$.
    - Asserts output shape is strictly 1D `(25,)` with `dtype=float`.

---

## 3. Caveats

1. **Read-Only Investigation Constraint**:
   - In accordance with explorer rules, zero production code or test files were written directly to `super_rsm/` or `tests/`. This document serves as the implementation contract for the implementation Worker.
2. **Execution Time for Genetic Programming in Test Suite**:
   - In production, `SymbolicRegressor` can take 20–60 seconds if configured with `population_size=5000` and `generations=30`. In unit tests, `population_size=100` and `generations=2` or `3` must be used so that the entire test suite completes within $<3$ seconds.
3. **Collinear Factor Inferences**:
   - While Moore-Penrose pseudo-inversion guarantees that collinear data will never crash the system, collinear columns inherently share variance. The standard errors in collinear models reflect the minimum-norm solution; users should be advised to examine ANOVA and $p$-values when designing screening experiments.

---

## 4. Conclusion

1. **Architecture Ready**: All 4 models cleanly inherit from `BaseRSMModel` with zero coupling to GUI or plotting modules, ensuring 100% headless batch execution.
2. **Mathematical Integrity**:
   - `GaussianProcessRSMModel` handles both Ordinary (degree=0, RBF, normalized) and Universal Kriging (degree>0, polynomial trend) with native predictive uncertainty.
   - `RidgeCVRSMModel` accurately extracts physical unscaled coefficients ($w_j = w_j^* / \sigma_j, w_0 = w_0^* - \mathbf{w} \cdot \mathbf{\mu}$).
   - `SymbolicRegressorRSMModel` exposes `piecewise` and formats readable formulas with variable token replacement.
   - `PolynomialOLSModel` successfully introduces classical Response Surface Methodology to SuperRSM, providing coded units $[-1, +1]$, SVD least-squares, Moore-Penrose pseudo-inversion for collinear data robustness, full ANOVA decomposition, two-tailed $t$-tests and $p$-values, Adjusted $R^2$, and $AIC/BIC$.
3. **Test Suite Specified**: `tests/test_models.py` is comprehensively planned with 16 distinct assertions verifying statistical accuracy, boundary stress conditions, and polymorphic API compliance across all four regression models.

---

## 5. Verification Method

To verify these findings and implementations:

1. **Inspect this handoff specification**:
   - `c:\Users\mitsu\OneDrive\Personal Projects\SuperRSM\.agents\teamwork\teamwork_explorer_m1_3\handoff.md`
2. **Execute Python verification command for Moore-Penrose pseudo-inverse vs singular inversion**:
   ```powershell
   python -c "import numpy as np; Phi = np.array([[1.0, 1.0, 2.0], [1.0, 2.0, 4.0], [1.0, 3.0, 6.0], [1.0, 4.0, 8.0]]); print('lstsq rank:', np.linalg.lstsq(Phi, [1, 2, 3, 4], rcond=None)[2]); print('pinv shape:', np.linalg.pinv(Phi.T @ Phi).shape)"
   ```
3. **Execute Python verification command for OLS ANOVA & term p-values on `sample_data.csv`**:
   ```powershell
   python -c "import pandas as pd, numpy as np, scipy.stats as stats; from sklearn.preprocessing import PolynomialFeatures; df = pd.read_csv('sample_data.csv'); X = df[['x1', 'x2']].to_numpy(); y = df['y'].to_numpy(); poly = PolynomialFeatures(degree=2, include_bias=True); Phi = poly.fit_transform(X); beta, _, _, _ = np.linalg.lstsq(Phi, y, rcond=None); y_pred = Phi @ beta; n, p = Phi.shape; df_resid = n - p; s_sq = np.sum((y - y_pred)**2) / df_resid; se = np.sqrt(np.diag(np.linalg.pinv(Phi.T @ Phi)) * s_sq); t_stats = beta / se; p_vals = 2 * (1 - stats.t.cdf(np.abs(t_stats), df=df_resid)); print(dict(zip(['Intercept', 'x1', 'x2', 'x1^2', 'x1 x2', 'x2^2'], np.round(p_vals, 4))))"
   ```
   *Expected output*: `{'Intercept': 0.0, 'x1': 0.0, 'x2': 0.0, 'x1^2': 0.0, 'x1 x2': 0.4806, 'x2^2': 0.0}`
4. **Post-Implementation Test Command**:
   ```powershell
   pytest tests/test_models.py -v
   ```
   *Expected output*: All 16 unit tests pass with zero warnings or errors.
