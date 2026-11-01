"""
Shared statistical diagnostics for SuperRSM regression models:
- Replicate group detection and Pure Error / Lack-of-Fit decomposition
- Unified ANOVA table construction (supporting exact and effective degrees of freedom)
- Regularized polynomial covariance, standard errors, t-statistics, and p-values
- First-order marginal factor sensitivity analysis for non-parametric/symbolic models
"""

from typing import Any, Callable, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
import scipy.stats as stats


def compute_input_groups(X: np.ndarray, decimals: int = 8) -> Tuple[np.ndarray, int]:
    """
    Assign each row of X to a unique input parameter combination group ID in [0, G-1],
    ordered by first appearance in X so group IDs preserve original dataset order.
    """
    X_arr = np.asarray(X, dtype=float)
    if X_arr.ndim == 1:
        X_arr = X_arr.reshape(-1, 1)
    if len(X_arr) == 0:
        return np.empty((0,), dtype=int), 0

    tol = 10.0 ** (-decimals)
    X_clean = np.where(np.abs(X_arr) < tol, 0.0, X_arr)
    X_round = np.round(X_clean, decimals=decimals)

    _, first_idx, inverse = np.unique(X_round, axis=0, return_index=True, return_inverse=True)
    order = np.argsort(first_idx)
    rank = np.empty_like(order)
    rank[order] = np.arange(len(first_idx))
    group_ids = rank[inverse]
    return group_ids.astype(int), int(len(first_idx))


def compute_pure_error(X: np.ndarray, y: np.ndarray, decimals: int = 8) -> Tuple[float, int, int]:
    """
    Compute model-independent Pure Error Sum of Squares (SS_PE), Pure Error degrees of freedom (df_PE),
    and number of unique input combinations (n_groups) from replicate observations.
    """
    y_arr = np.asarray(y, dtype=float).ravel()
    group_ids, n_groups = compute_input_groups(X, decimals=decimals)
    n_samples = len(y_arr)
    df_pe = n_samples - n_groups
    if df_pe <= 0 or n_groups <= 0:
        return 0.0, 0, n_groups

    ss_pe = 0.0
    for g in range(n_groups):
        mask = group_ids == g
        if np.sum(mask) > 1:
            y_g = y_arr[mask]
            ss_pe += float(np.sum((y_g - np.mean(y_g)) ** 2))
    return float(ss_pe), int(df_pe), int(n_groups)


def build_anova_table(
    y: np.ndarray,
    y_pred: np.ndarray,
    df_model: Optional[float] = None,
    X: Optional[np.ndarray] = None,
) -> pd.DataFrame:
    """
    Construct a unified ANOVA table for regression models.
    Includes Model (Regression), Residual (Error), Total, and—when replicate input
    combinations exist in X—Lack of Fit and Pure Error sub-rows.
    """
    y_arr = np.asarray(y, dtype=float).ravel()
    y_hat = np.asarray(y_pred, dtype=float).ravel()
    n_samples = len(y_arr)

    rss = float(np.sum((y_arr - y_hat) ** 2))
    tss = float(np.sum((y_arr - np.mean(y_arr)) ** 2))
    ss_reg = max(0.0, tss - rss)
    df_total = float(max(0, n_samples - 1))

    if df_model is not None and 0.0 < df_model < df_total:
        df_m = float(df_model)
        df_r = float(df_total - df_m)
        ms_reg = ss_reg / df_m if df_m > 0 else np.nan
        ms_res = rss / df_r if df_r > 0 else np.nan
        f_stat = (ms_reg / ms_res) if (ms_res > 1e-15 and df_m > 0) else np.nan
        f_pval = float(1.0 - stats.f.cdf(f_stat, df_m, df_r)) if np.isfinite(f_stat) else np.nan
    else:
        df_m = float(df_model) if (df_model is not None and df_model > 0) else np.nan
        df_r = float(df_total - df_m) if (np.isfinite(df_m) and df_total > df_m) else np.nan
        ms_reg, ms_res, f_stat, f_pval = np.nan, np.nan, np.nan, np.nan

    sources = ["Model (Regression)", "Residual (Error)", "Total"]
    ss_list = [ss_reg, rss, tss]
    df_list = [df_m, df_r, df_total]
    ms_list = [ms_reg, ms_res, np.nan]
    f_list = [f_stat, np.nan, np.nan]
    p_list = [f_pval, np.nan, np.nan]

    if X is not None and len(X) == n_samples:
        ss_pe, df_pe, _ = compute_pure_error(X, y_arr)
        if df_pe > 0:
            ss_lof = max(0.0, rss - ss_pe)
            ms_pe = ss_pe / df_pe
            if np.isfinite(df_r) and df_r > df_pe:
                df_lof = float(df_r - df_pe)
                ms_lof = ss_lof / df_lof if df_lof > 0 else np.nan
                f_lof = (ms_lof / ms_pe) if (ms_pe > 1e-15 and np.isfinite(ms_lof)) else np.nan
                p_lof = float(1.0 - stats.f.cdf(f_lof, df_lof, df_pe)) if np.isfinite(f_lof) else np.nan
            else:
                df_lof, ms_lof, f_lof, p_lof = np.nan, np.nan, np.nan, np.nan

            sources.extend(["  ↳ Lack of Fit", "  ↳ Pure Error"])
            ss_list.extend([ss_lof, ss_pe])
            df_list.extend([df_lof, float(df_pe)])
            ms_list.extend([ms_lof, ms_pe])
            f_list.extend([f_lof, np.nan])
            p_list.extend([p_lof, np.nan])

    return pd.DataFrame({
        "Source": sources,
        "SS": ss_list,
        "df": df_list,
        "MS": ms_list,
        "F-Value": f_list,
        "p-Value": p_list,
    })


def compute_regularized_term_stats(
    Z_std: np.ndarray,
    y: np.ndarray,
    y_pred: np.ndarray,
    unscaled_intercept: float,
    unscaled_coeffs: np.ndarray,
    scaler_mean: np.ndarray,
    scaler_scale: np.ndarray,
    term_names: List[str],
    l2_penalty: float = 0.0,
    cov_std_override: Optional[np.ndarray] = None,
    active_mask: Optional[np.ndarray] = None,
) -> Dict[str, Any]:
    """
    Compute effective degrees of freedom, Adjusted R², AIC, BIC, and unscaled physical
    term standard errors, t-statistics, and p-values for regularized polynomial models.
    """
    n_samples, p_terms = Z_std.shape
    rss = float(np.sum((y - y_pred) ** 2))
    tss = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - (rss / tss) if tss > 1e-15 else 0.0
    mse = rss / n_samples if n_samples > 0 else 0.0

    if active_mask is None:
        active_mask = np.ones(p_terms, dtype=bool)
    active_idx = np.flatnonzero(active_mask)

    # Effective degrees of freedom via SVD of active standardized design matrix
    if len(active_idx) > 0:
        Z_act = Z_std[:, active_idx]
        _, s_vals, vt = np.linalg.svd(Z_act, full_matrices=False)
        s_sq = s_vals ** 2
        alpha_eff = max(0.0, float(l2_penalty))
        df_model = float(np.sum(s_sq / np.maximum(1e-15, s_sq + alpha_eff)))
    else:
        s_sq, vt, alpha_eff = np.array([]), np.empty((0, 0)), 0.0
        df_model = 0.0

    df_resid = max(1.0, float(n_samples - 1) - df_model)
    s2 = rss / df_resid if df_resid > 0 else 0.0

    if cov_std_override is not None:
        cov_std = np.asarray(cov_std_override, dtype=float)
    else:
        cov_std = np.zeros((p_terms, p_terms), dtype=float)
        if len(active_idx) > 0:
            shrink_diag = s_sq / (np.maximum(1e-15, s_sq + alpha_eff) ** 2)
            cov_act = (vt.T * shrink_diag) @ vt * s2
            cov_std[np.ix_(active_idx, active_idx)] = cov_act

    safe_scale = np.where(scaler_scale > 1e-12, scaler_scale, 1.0)
    cov_phys = cov_std / np.outer(safe_scale, safe_scale)
    se_terms = np.sqrt(np.maximum(0.0, np.diag(cov_phys)))

    # Propagate variance to physical intercept: beta_0 = y_bar - mu^T beta_phys
    var_intercept = (s2 / max(1, n_samples)) + float(scaler_mean @ cov_phys @ scaler_mean)
    se_intercept = float(np.sqrt(max(0.0, var_intercept)))

    all_names = ["Intercept", *term_names]
    all_coeffs = np.concatenate([[unscaled_intercept], unscaled_coeffs])
    all_se = np.concatenate([[se_intercept], se_terms])
    all_active = np.concatenate([[True], active_mask])

    t_stats: Dict[str, float] = {}
    p_values: Dict[str, float] = {}
    std_errors: Dict[str, float] = {}

    for name, coeff, se_val, is_act in zip(all_names, all_coeffs, all_se, all_active):
        std_errors[name] = float(se_val)
        if not is_act or se_val <= 1e-12:
            t_stats[name] = 0.0
            p_values[name] = 1.0
        else:
            t_val = float(coeff / se_val)
            p_val = float(2.0 * (1.0 - stats.t.cdf(abs(t_val), df=df_resid)))
            t_stats[name] = t_val
            p_values[name] = p_val

    k_params = df_model + 1.0
    adj_r2 = 1.0 - (1.0 - r2) * ((n_samples - 1) / df_resid) if (df_resid > 0 and tss > 0) else r2
    aic = float(n_samples * np.log(max(1e-12, mse)) + 2.0 * k_params)
    bic = float(n_samples * np.log(max(1e-12, mse)) + k_params * np.log(max(1, n_samples)))

    return {
        "df_model": df_model,
        "df_resid": df_resid,
        "adj_r2": float(adj_r2),
        "aic": aic,
        "bic": bic,
        "term_std_errors": std_errors,
        "term_t_stats": t_stats,
        "term_p_values": p_values,
    }


def compute_factor_sensitivity(
    predict_fn: Callable[[np.ndarray], np.ndarray],
    X: np.ndarray,
    feature_names: List[str],
    grid_points: int = 25,
) -> Dict[str, float]:
    """
    Compute normalized first-order main-effect variance sensitivity for each input factor
    by sweeping each factor across its empirical [min, max] range while holding other
    factors at their sample mean.
    """
    X_arr = np.asarray(X, dtype=float)
    if X_arr.ndim == 1:
        X_arr = X_arr.reshape(-1, 1)
    n_features = X_arr.shape[1]
    means = np.mean(X_arr, axis=0)
    mins = np.min(X_arr, axis=0)
    maxs = np.max(X_arr, axis=0)

    variances = np.zeros(n_features, dtype=float)
    for j in range(n_features):
        if np.isclose(mins[j], maxs[j]):
            variances[j] = 0.0
            continue
        sweep = np.tile(means, (grid_points, 1))
        sweep[:, j] = np.linspace(mins[j], maxs[j], grid_points)
        try:
            preds = np.asarray(predict_fn(sweep), dtype=float).ravel()
            variances[j] = float(np.var(preds)) if not np.any(np.isnan(preds)) else 0.0
        except Exception:
            variances[j] = 0.0

    total_var = float(np.sum(variances))
    if total_var <= 1e-15:
        return {name: 1.0 / max(1, n_features) for name in feature_names}
    return {name: float(v / total_var) for name, v in zip(feature_names, variances)}

