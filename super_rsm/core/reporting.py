"""
super_rsm/core/reporting.py

Unified diagnostic report and summary formatting for SuperRSM models and results.
Produces aligned statistical tables (coefficients, standard errors, t-scores, p-values,
ANOVA with Lack-of-Fit / Pure Error decomposition, factor sensitivity, and Train vs. Test metrics).
"""

from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd


def _sig_code(p_val: float) -> str:
    """Return standard statistical significance stars for a p-value."""
    if not np.isfinite(p_val):
        return ""
    if p_val < 0.001:
        return "***"
    if p_val < 0.01:
        return "**"
    if p_val < 0.05:
        return "*"
    if p_val < 0.10:
        return "."
    return ""


def format_anova_dataframe(anova_df: pd.DataFrame) -> str:
    """Format an ANOVA DataFrame into a clean aligned monospaced table without raw NaNs."""
    if anova_df is None or anova_df.empty:
        return ""

    rows: List[Dict[str, str]] = []
    for _, r in anova_df.iterrows():
        src = str(r.get("Source", ""))
        ss = r.get("SS", np.nan)
        df_v = r.get("df", np.nan)
        ms = r.get("MS", np.nan)
        fv = r.get("F-Value", np.nan)
        pv = r.get("p-Value", np.nan)

        ss_str = f"{float(ss):.5g}" if (ss is not None and np.isfinite(ss)) else "—"
        if df_v is not None and np.isfinite(df_v):
            df_f = float(df_v)
            df_str = f"{int(round(df_f))}" if abs(df_f - round(df_f)) < 1e-4 else f"{df_f:.2f}"
        else:
            df_str = "—"
        ms_str = f"{float(ms):.5g}" if (ms is not None and np.isfinite(ms)) else "—"
        f_str = f"{float(fv):.4f}" if (fv is not None and np.isfinite(fv)) else "—"
        if pv is not None and np.isfinite(pv):
            sig = _sig_code(float(pv))
            p_str = f"{float(pv):.4g} {sig}".rstrip()
        else:
            p_str = "—"

        rows.append({
            "Source": src,
            "SS": ss_str,
            "df": df_str,
            "MS": ms_str,
            "F-Value": f_str,
            "p-Value": p_str,
        })

    fmt_df = pd.DataFrame(rows)
    return fmt_df.to_string(index=False)


def format_coefficients_section(
    coeffs_dict: Dict[str, float],
    std_errors: Optional[Dict[str, float]],
    t_stats: Optional[Dict[str, float]],
    p_values: Optional[Dict[str, float]],
    importance: Optional[Dict[str, float]],
) -> List[str]:
    """Format model coefficients along with SE, t-statistics, p-values, and relative importance."""
    lines = ["Model Coefficients:"]
    std_errors = std_errors or {}
    t_stats = t_stats or {}
    p_values = p_values or {}
    importance = importance or {}

    has_stats = bool(t_stats and p_values)
    term_width = max(10, max((len(t) for t in coeffs_dict), default=10))

    if has_stats:
        hdr = (
            f"  {'Term':<{term_width}}  {'Estimate':>12}  {'Std. Error':>11}  "
            f"{'t-Value':>9}  {'p-Value':>10}  {'Rel.Imp':>8}  Sig"
        )
        lines.append(hdr)
        lines.append("  " + "-" * (len(hdr) - 2))

    for term, coeff in coeffs_dict.items():
        imp_str = f"{100.0 * importance[term]:6.1f}%" if term in importance else "      —"
        if has_stats and term in t_stats and term in p_values:
            se_v = std_errors.get(term, np.nan)
            t_v = t_stats[term]
            p_v = p_values[term]
            se_str = f"{se_v:11.5f}" if np.isfinite(se_v) else f"{'—':>11}"
            if term != "Intercept" and abs(coeff) < 1e-10 and abs(t_v) < 1e-10 and p_v >= 0.999:
                lines.append(
                    f"  - {term:<{term_width}}: {coeff:12.6f}  {se_str}  "
                    f"{'0.000':>9}  {'1.0000':>10}  {imp_str:>8}  [Pruned]"
                )
            else:
                sig = _sig_code(p_v)
                lines.append(
                    f"  - {term:<{term_width}}: {coeff:12.6f}  {se_str}  "
                    f"(t = {t_v:7.3f}, p = {p_v:9.4g})  {imp_str:>8}  {sig}".rstrip()
                )
        else:
            lines.append(f"  - {term:<{term_width}}: {coeff:12.6f}  (Rel.Imp = {imp_str.strip()})")

    if has_stats:
        lines.append("  Significance codes: '***' p<0.001, '**' p<0.01, '*' p<0.05, '.' p<0.10")
    lines.append("")
    return lines


def format_factor_sensitivity_section(importance: Dict[str, float]) -> List[str]:
    """Format first-order marginal variance sensitivity ranking for non-parametric/symbolic models."""
    if not importance:
        return []
    lines = ["Input Factor Sensitivity (Main-Effect Variance Share):"]
    ranked = sorted(importance.items(), key=lambda kv: kv[1], reverse=True)
    for rank, (factor, share) in enumerate(ranked, 1):
        lines.append(f"  [{rank}] {factor:<14}: {100.0 * share:6.2f}%")
    lines.append("")
    return lines


def format_full_report_text(
    result: Any,
    input_cols: List[str],
    output_col: str,
    last_opt_report_text: str = "",
) -> str:
    """Format complete diagnostic report for GUI and headless inspection."""
    if result is None or not input_cols:
        return ""

    ds = getattr(result, "dataset", None)
    metrics = result.metrics
    train_metrics = getattr(result, "train_metrics", None)

    lines = [
        "=== Surrogate Model Fit Summary ===\n",
        f"Target Output Variable: {output_col}",
        f"Input Factors ({len(input_cols)}): {', '.join(input_cols)}",
        f"Regression Method: {result.method}",
    ]

    if ds is not None:
        split_mode = (
            "Grouped by Unique Input Combinations"
            if getattr(ds, "split_by_groups", False)
            else "Random Row Split"
        )
        n_tr, n_te = ds.n_train, ds.n_test
        u_tr = getattr(ds, "n_unique_train", n_tr)
        u_te = getattr(ds, "n_unique_test", n_te)
        lines.append(
            f"Dataset Partition: {n_tr} Train ({u_tr} unique conditions) | "
            f"{n_te} Test ({u_te} unique conditions) [{split_mode}]"
        )

    eval_scope = "Test Set" if (ds is not None and ds.has_test_set) else "Training Set"
    lines.append(f"Coefficient of Determination (R²) [{eval_scope}]: {result.R_sq:.4f}")
    if metrics.adj_r2 is not None:
        lines.append(f"Adjusted R²: {metrics.adj_r2:.4f}")
    lines.append(f"Mean Squared Error (MSE): {result.MSE:.6f}")
    lines.append(f"Root Mean Squared Error (RMSE): {result.RMSE:.6f}")
    if metrics.mae is not None:
        lines.append(f"Mean Absolute Error (MAE): {metrics.mae:.6f}")

    if ds is not None and ds.has_test_set and train_metrics is not None:
        lines.append(
            f"Training Set Fit: Train R² = {train_metrics.r2:.4f}, "
            f"Train RMSE = {train_metrics.rmse:.6f}, Train MSE = {train_metrics.mse:.6f}"
        )

    if metrics.aic is not None and metrics.bic is not None:
        lines.append(f"AIC: {metrics.aic:.2f}  |  BIC: {metrics.bic:.2f}")
    lines.append("")

    custom = getattr(metrics, "custom_metrics", None)
    if custom:
        lines.append("Model Diagnostics & Hyperparameters:")
        for k, v in custom.items():
            lines.append(f"  - {k}: {v}")
        lines.append("")

    coeffs_dict = result.get_coefficients()
    importance = result.get_feature_importance()
    if coeffs_dict:
        lines.extend(
            format_coefficients_section(
                coeffs_dict=coeffs_dict,
                std_errors=metrics.term_std_errors,
                t_stats=metrics.term_t_stats,
                p_values=metrics.term_p_values,
                importance=importance,
            )
        )
    elif importance:
        lines.extend(format_factor_sensitivity_section(importance))

    if getattr(result, "expression_text", None):
        lines.append(f"Model Equation:\n  {result.expression_text}\n")

    if metrics.anova_table is not None:
        lines.append("ANOVA Table:")
        lines.append(format_anova_dataframe(metrics.anova_table))
        lines.append("")

    if last_opt_report_text:
        lines.append(last_opt_report_text.rstrip())

    return "\n".join(lines) + "\n"


def format_result_summary(result: Any) -> str:
    """Format concise headless summary string for RSMResult.summary()."""
    header = f"SuperRSM Model Summary: {result.method}\n" + ("=" * 50) + "\n"
    body = format_full_report_text(
        result=result,
        input_cols=result.feature_names,
        output_col=result.target_name,
    )
    return header + body

