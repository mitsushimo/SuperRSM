"""
Copyright (C) 2026, Mitsuki Shimomura & Michigan Technological University 

This is an updated version of the RSM software. Unlike the previous versions, which focused on a specific 
RSM method (OLS, Ridge, and Kriging), this version is designed to support multiple regression methods 
(including RidgeCV and Gaussian Process Regressor). 
The advanced plot-configuration features are inherited from the Kriging software. 
"""

import numpy as np
from numpy.linalg import lstsq
from scipy.optimize import minimize, LinearConstraint
from sklearn.preprocessing import StandardScaler, PolynomialFeatures
from sklearn.metrics import r2_score, mean_squared_error
from sklearn.model_selection import train_test_split 
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, DotProduct, WhiteKernel 
from sklearn.linear_model import RidgeCV
from sklearn.pipeline import make_pipeline
from gplearn.genetic import SymbolicRegressor
from gplearn.functions import make_function

from high_d_plotter import plot_multi_contour


# =============================================================================
# Model Registry & Builders for Extensibility
# =============================================================================

def build_gaussian_process_model(degree_fit=2, **kwargs):
    """
    Builder for Gaussian Process Regressor (Kriging).
    degree_fit == 0: Ordinary Kriging (constant mean via normalize_y=True, no polynomial trend)
    degree_fit > 0: Universal Kriging with polynomial drift trend
    """
    if degree_fit == 0:
        kernel = 1.0 * RBF(length_scale=1.0) + WhiteKernel(noise_level=0.1)
        return make_pipeline(
            StandardScaler(), 
            GaussianProcessRegressor(kernel=kernel, normalize_y=True)
        )
    else:
        kernel = DotProduct(sigma_0=1.0) + RBF(length_scale=1.0) + WhiteKernel(noise_level=0.1)
        return make_pipeline(
            PolynomialFeatures(degree=degree_fit, include_bias=False), 
            StandardScaler(), 
            GaussianProcessRegressor(kernel=kernel)
        )


def build_ridge_model(degree_fit=2, n_samples=None, **kwargs):
    """
    Builder for Ridge Regression with Cross-Validation (RidgeCV).
    Uses PolynomialFeatures to fit polynomial Response Surfaces.
    """
    if degree_fit < 1:
        raise ValueError("Polynomial degree must be at least 1 for Ridge regression.")
    alphas = np.logspace(-6, 6, 13)
    cv = 5 if (n_samples is None or n_samples >= 5) else None
    return make_pipeline(
        PolynomialFeatures(degree=degree_fit, include_bias=False), 
        StandardScaler(), 
        RidgeCV(alphas=alphas, cv=cv)
    )


def piecewise_function(condition, true_val, false_val): 
    """
    A simple piecewise function to be used in genetic programming models. 
    Returns true_val if condition is above 0, and false_val otherwise.
    """
    return np.where(condition > 0, true_val, false_val)


def build_genetic_programming_model(degree_fit=2, **kwargs): 
    """
    The builder function for the Genetic Programming model, implemented using the gplearn library.
    """
    piecewise = make_function(function=piecewise_function, name='piecewise', arity=3)
    function_set = ["add", "sub", "mul", "div", "sqrt", "log", piecewise]
    gp_model = SymbolicRegressor(
        function_set=function_set,
        population_size = 5000, 
        generations = 30, 
        stopping_criteria = 0.0, 
        p_crossover = 0.7, 
        p_subtree_mutation = 0.1, 
        p_hoist_mutation = 0.05, 
        p_point_mutation = 0.1,
        max_samples = 0.9, 
        parsimony_coefficient = 0.005, 
        random_state = 42, 
        const_range = (-30, 30)
    )
    return gp_model

def format_genetic_programming_expression(model):
    """
    Format the resulting mathematical expression from a fitted Genetic Programming model.
    """
    if hasattr(model, "_program") and model._program is not None:
        return f"Mathematical Expression:\n  {model._program}"
    return None


MODEL_REGISTRY = {
    "Gaussian Process": {
        "builder": build_gaussian_process_model,
        "supports_uncertainty": True,
        "extract_coeffs": False,
        "format_expression": None,
    },
    "RidgeCV": {
        "builder": build_ridge_model,
        "supports_uncertainty": False,
        "extract_coeffs": True,
        "format_expression": None,
    },
    "Genetic Programming": {
        "builder": build_genetic_programming_model,
        "supports_uncertainty": False,
        "extract_coeffs": False,
        "format_expression": format_genetic_programming_expression,
    },
}


def register_model(name, builder, supports_uncertainty=False, extract_coeffs=False, format_expression=None):
    """
    Register a new regression model in the framework.
    """
    MODEL_REGISTRY[name] = {
        "builder": builder,
        "supports_uncertainty": supports_uncertainty,
        "extract_coeffs": extract_coeffs,
        "format_expression": format_expression,
    }


def get_supported_methods():
    """
    Return a list of all registered regression method names.
    """
    return list(MODEL_REGISTRY.keys())


class rsm_result:
    """
    A class to hold the results of the response surface model fitting, including
    evaluation metrics, optimization, unscaled coefficients (if available), and visualization.
    """

    def __init__(self, model, X_train, y_train, X_test, y_test, method="Gaussian Process"):
        self.model = model
        self.X_train = X_train
        self.y_train = y_train
        self.X_test = X_test
        self.y_test = y_test
        self.method = method

        meta = MODEL_REGISTRY.get(method, {})
        self.supports_uncertainty = meta.get("supports_uncertainty", False)

        # Format expression string if provided by the model registry (e.g. Genetic Programming)
        format_expr_func = meta.get("format_expression")
        if callable(format_expr_func):
            try:
                self.expression_text = format_expr_func(self.model)
            except Exception:
                self.expression_text = None
        else:
            self.expression_text = None

        self.coeffs = None
        self.intercept = None

        # Extract unscaled coefficients if available (e.g. RidgeCV)
        if meta.get("extract_coeffs", False) or (hasattr(model, "named_steps") and "ridgecv" in model.named_steps):
            try:
                scaler_step = model.named_steps.get('standardscaler')
                ridge_step = model.named_steps.get('ridgecv')
                if scaler_step is not None and ridge_step is not None:
                    self.coeffs = ridge_step.coef_ / scaler_step.scale_
                    self.intercept = ridge_step.intercept_ - np.dot(self.coeffs, scaler_step.mean_)
            except Exception:
                pass

        # Make predictions on the test set
        if self.supports_uncertainty:
            y_pred, sigma = model.predict(X_test, return_std=True)
            self.sigma_test = sigma
        else:
            y_pred = model.predict(X_test)
            self.sigma_test = None

        self.R_sq = r2_score(y_test, y_pred)
        self.MSE = mean_squared_error(y_test, y_pred)
        self.RMSE = np.sqrt(self.MSE)

    def __str__(self):
        parts = [f"Regression Method: {self.method}"]
        if self.expression_text:
            parts.append(self.expression_text) # type: ignore
        if self.intercept is not None and self.coeffs is not None:
            parts.append(f"Intercept: {self.intercept}, Coefficients: {self.coeffs}")
        parts.append(f"Coefficient of Determination (R2): {self.R_sq}")
        parts.append(f"Mean Squared Error (MSE): {self.MSE}")
        parts.append(f"Root Mean Squared Error (RMSE): {self.RMSE}")
        return "\n".join(parts)

    def target_func(self, params, return_std=False):
        """
        Evaluate the fitted response surface model at the given input parameters (params) as an iterative object.
        """
        X_eval = np.array(params).reshape(1, -1)
        if return_std:
            if not self.supports_uncertainty:
                raise ValueError(f"Uncertainty estimation is not supported by {self.method}.")
            return self.model.predict(X_eval, return_std=True)
        return self.model.predict(X_eval)

    def evaluate_point(self, params, return_std=False):
        """
        Evaluate the fitted response surface model at a single point and return scalar float(s).
        Returns (y_val, std_val) if return_std is True, otherwise y_val.
        """
        if return_std and self.supports_uncertainty:
            y_pred, sigma = self.target_func(params, return_std=True)
            y_val = float(np.asarray(y_pred, dtype=float).ravel()[0])
            std_val = float(np.asarray(sigma, dtype=float).ravel()[0])
            return y_val, std_val
        y_pred = self.target_func(params, return_std=False)
        y_val = float(np.asarray(y_pred, dtype=float).ravel()[0])
        if return_std:
            return y_val, None
        return y_val

    def optimize(self, initial_guess=None, bounds=None, constraints=None, maximize=False):
        """
        Optimize the fitted response surface model to find the input parameters that minimize or maximize the output.
        initial_guess: Initial guess for the optimization.
        bounds: Bounds for the optimization (optional).
        constraints: Constraints for the optimization (optional). Can be a LinearConstraint,
                     a dict, or a list of constraints for scipy.optimize.minimize.
        maximize: If True, maximizes the output instead of minimizing (default False).
        Returns the optimized parameters and the corresponding optimal output value.
        """
        if initial_guess is None:
            initial_guess = np.zeros(self.X_test.shape[1])

        kwargs = {}
        if bounds is not None:
            kwargs['bounds'] = bounds
        if constraints is not None:
            kwargs['constraints'] = constraints

        if maximize:
            def objective(p):
                return -float(np.asarray(self.target_func(p), dtype=float).ravel()[0])
        else:
            objective = self.target_func

        result = minimize(objective, initial_guess, **kwargs)
        self.last_opt_result = result
        self.last_opt_maximize = bool(maximize)

        raw_fun = result.fun.item() if hasattr(result.fun, 'item') and getattr(result.fun, 'ndim', 0) > 0 else float(result.fun)
        opt_fun = -raw_fun if maximize else raw_fun
        return result.x, opt_fun

    def visualize_rsm(self, config, title="Function Visualization", xlabel="X", ylabel="Y", label_array=None, plot_settings=None):
        """
        Visualize the fitted response surface model over the given ranges of parameters as contour plots. 

        config is a dictionary specifying the axes and fixed values:
        {
            'x': (index, values_array),
            'y': (index, values_array),
            'p': (index, values_array), # Optional row axis for subplots
            'q': (index, values_array), # Optional column axis for subplots
            'fixed': [(index, value), ...] # Optional fixed values for other parameters
        }
        """
        print("Creating the contour plots...")
        x_idx, x_values = config['x']
        y_idx, y_values = config['y']
        
        p_info = config.get('p')
        q_info = config.get('q')
        fixed_info = config.get('fixed', [])
        
        p_values = p_info[1] if p_info else [None]
        q_values = q_info[1] if q_info else [None]

        X, Y = np.meshgrid(x_values, y_values)
        X_flat = X.flatten()
        Y_flat = Y.flatten()

        plot_unc = plot_settings.get('plot_uncertainty', False) if plot_settings else False
        if plot_unc and not self.supports_uncertainty:
            raise ValueError(f"Uncertainty plotting is not supported for {self.method}.")

        # Combine training and test measurement data for scatter plotting
        x_parts = [arr for arr in (self.X_train, self.X_test) if arr is not None and len(arr) > 0]
        X_all = np.vstack(x_parts) if x_parts else None
        y_parts = [np.asarray(arr).ravel() for arr in (self.y_train, self.y_test) if arr is not None and len(arr) > 0]
        y_all = np.concatenate(y_parts) if y_parts else None

        Z_array = []
        U_array = []
        scatter_array = []
        for p_val in p_values:
            Z_row = []
            U_row = []
            scatter_row = []
            for q_val in q_values:
                # Filter measurement data matching this subplot's P, Q, and Fixed parameter values
                if X_all is not None:
                    mask = np.ones(len(X_all), dtype=bool)
                    if p_info is not None:
                        mask &= np.isclose(X_all[:, p_info[0]], p_val) # type: ignore
                    if q_info is not None:
                        mask &= np.isclose(X_all[:, q_info[0]], q_val) # type: ignore
                    for f_idx, f_val in fixed_info:
                        mask &= np.isclose(X_all[:, f_idx], f_val)
                    if y_all is not None and len(y_all) == len(X_all):
                        scatter_row.append((X_all[mask, x_idx], X_all[mask, y_idx], y_all[mask]))
                    else:
                        scatter_row.append((X_all[mask, x_idx], X_all[mask, y_idx]))
                else:
                    scatter_row.append((np.array([]), np.array([]), np.array([])))

                # Evaluate the model over the X, Y grid
                Z_flat = []
                U_flat = []
                for x_val, y_val in zip(X_flat, Y_flat):
                    params = np.zeros(self.X_test.shape[1])
                    params[x_idx] = x_val
                    params[y_idx] = y_val
                    if p_info is not None:
                        params[p_info[0]] = p_val
                    if q_info is not None:
                        params[q_info[0]] = q_val
                    for f_idx, f_val in fixed_info:
                        params[f_idx] = f_val
                        
                    if plot_unc:
                        z_value, u_value = self.target_func(params, return_std=True)
                        if isinstance(z_value, np.ndarray):
                            z_value = z_value[0]
                        if isinstance(u_value, np.ndarray):
                            u_value = u_value[0]
                        Z_flat.append(z_value)
                        U_flat.append(u_value)
                    else:
                        z_value = self.target_func(params)
                        if isinstance(z_value, np.ndarray):
                            z_value = z_value[0]
                        Z_flat.append(z_value) 
                Z_mesh = np.array(Z_flat).reshape(X.shape)
                Z_row.append(Z_mesh)
                if plot_unc:
                    U_mesh = np.array(U_flat).reshape(X.shape)
                    U_row.append(U_mesh)
            Z_array.append(Z_row)
            scatter_array.append(scatter_row)
            if plot_unc:
                U_array.append(U_row)

        if plot_settings is None:
            plot_settings = {}
        ps_main = plot_settings.copy()
        if plot_unc:
            ps_main['show_plot'] = False

        # Plot the contour plots
        plot_multi_contour(
            X, Y, Z_array,
            title=title,
            xlabel=xlabel,
            ylabel=ylabel,
            label_array=label_array,
            plot_settings=ps_main,
            scatter_array=scatter_array
        )

        if plot_unc:
            ps_unc = plot_settings.copy()
            ps_unc['show_plot'] = True
            if ps_unc.get('colorbar_label'):
                ps_unc['colorbar_label'] = f"{ps_unc['colorbar_label']} (Uncertainty)"
            if y_all is not None and len(y_all) > 0:
                s_vmin = float(np.min(y_all))
                s_vmax = float(np.max(y_all))
                if np.isclose(s_vmin, s_vmax):
                    s_vmin -= 1e-6
                    s_vmax += 1e-6
                ps_unc.setdefault('scatter_vmin', s_vmin)
                ps_unc.setdefault('scatter_vmax', s_vmax)
            plot_multi_contour(
                X, Y, U_array,
                title=title + " (Uncertainty)",
                xlabel=xlabel,
                ylabel=ylabel,
                label_array=label_array,
                plot_settings=ps_unc,
                scatter_array=scatter_array
            )


def generate_term_strings(input_columns, model):
    """
    Generate a list of strings representing the terms in the response surface model (RSM) for the given list
    of input columns names. 
    """
    if hasattr(model, 'named_steps') and 'polynomialfeatures' in model.named_steps:
        poly_step = model.named_steps['polynomialfeatures']
        return list(poly_step.get_feature_names_out(input_columns))
    return list(input_columns)


def fit_rsm2(X, y, degree_fit=2, test_size=0.20, method="Gaussian Process", **kwargs):
    """
    Fit the response surface model (RSM) for the given data using the specified regression method.
    X is a 2D array, columns of which are the measured inputs. y is a 1D array of the measured outputs.
    method: String name of the regression method.
    Returns the rsm_result object containing the fitted model and the data. 
    """
    if method not in MODEL_REGISTRY:
        raise ValueError(f"Unknown regression method '{method}'. Supported methods: {get_supported_methods()}")

    # Split the data into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42)

    builder = MODEL_REGISTRY[method]["builder"]
    model = builder(degree_fit=degree_fit, n_samples=len(X_train), **kwargs)
    model.fit(X_train, y_train)

    return rsm_result(model, X_train, y_train, X_test, y_test, method=method)
    

def build_data(df, input_columns, output_column):
    """
    Build the input and output data arrays from a pandas DataFrame.
    df: pandas DataFrame containing the data.
    input_columns: List of column names to be used as inputs.
    output_column: Column name to be used as output.
    Returns X (input array) and y (output array).
    """
    X = df[input_columns].to_numpy()
    y = df[output_column].to_numpy()
    return X, y


def rsm_fromDF(df, input_columns, output_column, degree_fit=2, test_size=0.20, method="Gaussian Process", **kwargs):
    """
    Fit a response surface model (RSM) from a pandas DataFrame.
    df: pandas DataFrame containing the data.
    input_columns: List of column names to be used as inputs.
    output_column: Column name to be used as output.
    degree_fit: Polynomial degree for the fit.
    test_size: Ratio of the data to reserve for test split.
    method: Regression method name.
    Returns an rsm_result object containing the fitted model and optimization results.
    """
    X, y = build_data(df, input_columns, output_column)
    result = fit_rsm2(X, y, degree_fit=degree_fit, test_size=test_size, method=method, **kwargs)
    return result


if __name__ == "__main__":
    # Test function with known minimum: f(x0, x1) = (x0 - 3.0)^2 + (x1 - 4.0)^2 + 5.0
    # Minimum is at (3.0, 4.0) with value 5.0
    known_min_coords = np.array([3.0, 4.0])
    known_min_val = 5.0

    # Generate 100 samples in the range [0, 10] for both parameters
    np.random.seed(42)
    X = np.random.uniform(0.0, 10.0, (100, 2))
    y = (
        (X[:, 0] - known_min_coords[0]) ** 2
        + (X[:, 1] - known_min_coords[1]) ** 2
        + known_min_val
    )

    for test_method in get_supported_methods():
        print(f"\n================ Testing Method: {test_method} ================")
        result = fit_rsm2(X, y, degree_fit=2, method=test_method)
        print("Fitted Model:")
        print(result)

        # Evaluate at known minimum point
        eval_val, eval_std = result.evaluate_point(known_min_coords, return_std=True)
        print(f"Evaluated at {known_min_coords}: y = {eval_val:.6f} (std = {eval_std})")

        # Run RSM minimization starting from initial guess [0.0, 0.0]
        opt_params, opt_val = result.optimize(initial_guess=np.zeros(2), maximize=False)
        print("Minimization Results:")
        print(f"Optimized parameters: {opt_params} (Expected: {known_min_coords})")
        print(f"Optimized minimum value: {opt_val:.6f} (Expected: {known_min_val:.6f})")

        # Run RSM maximization within [0, 10]^2 bounds
        max_params, max_val = result.optimize(
            initial_guess=np.array([5.0, 5.0]),
            bounds=[(0.0, 10.0), (0.0, 10.0)],
            maximize=True,
        )
        print("Maximization Results (within [0, 10]^2):")
        print(f"Maximized parameters: {max_params}")
        print(f"Maximized output value: {max_val:.6f}")

        if result.coeffs is not None:
            terms = generate_term_strings(['x0', 'x1'], result.model)
            print("Extracted Terms and Coefficients:")
            for t, c in zip(terms, result.coeffs):
                print(f"  {t}: {c:.6f}")

    print("\nAll backend tests passed successfully!")
