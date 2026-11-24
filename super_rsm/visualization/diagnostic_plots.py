"""
super_rsm/visualization/diagnostic_plots.py

Headless diagnostic figure generators for SuperRSM model reports:
- Parameter Effect Magnitude Bar Plot (|t-Statistic|)
- Statistical Significance Bar Plot (-log10(p-Value))
- Relative Importance / Factor Sensitivity Bar Plot (%)
- Actual vs. Predicted Parity Plot (Train vs. Test sets)
Supports user overrides for titles, axis labels, parameter/term names, and legend labels.
Uses Figure and FigureCanvasAgg directly to avoid global pyplot state or memory leaks.
"""

import base64
import io
from typing import Any, Dict, List, Optional, Tuple, Union
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
import numpy as np

from super_rsm.visualization.normalization import (
    PlotNormalizationConfig,
    format_normalized_label,
    resolve_axis_transform,
)


def figure_to_png_bytes(fig: Figure, dpi: int = 110) -> bytes:
    """Render a Matplotlib Figure to raw PNG bytes in memory using Agg backend."""
    canvas = FigureCanvasAgg(fig)
    buf = io.BytesIO()
    canvas.print_figure(buf, format="png", dpi=dpi, bbox_inches="tight", facecolor=fig.get_facecolor())
    return buf.getvalue()


def figure_to_base64_png(fig: Figure, dpi: int = 110) -> str:
    """Render a Matplotlib Figure to a base64-encoded PNG string for HTML embedding."""
    raw = figure_to_png_bytes(fig, dpi=dpi)
    return base64.b64encode(raw).decode("ascii")


def save_figure(fig: Figure, filepath: str, dpi: int = 300) -> None:
    """Save a Matplotlib Figure to disk at publication resolution."""
    canvas = FigureCanvasAgg(fig)
    canvas.print_figure(filepath, dpi=dpi, bbox_inches="tight", facecolor=fig.get_facecolor())


def _style_axes(ax: Any, ylabel: str = "") -> None:
    """Apply clean spine and tick styling to a diagnostic plot Axes."""
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=8.5, fontweight="bold", color="#334155")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#CBD5E1")
    ax.spines["bottom"].set_color("#CBD5E1")
    ax.tick_params(colors="#334155", labelsize=8)


def _extract_sorted_sig_terms(result: Any) -> Optional[Tuple[List[str], np.ndarray, np.ndarray, List[str]]]:
    """Extract sorted terms, |t-stats|, raw p-values, and significance bar colors."""
    if result is None or getattr(result, "metrics", None) is None:
        return None
    p_values: Optional[Dict[str, float]] = getattr(result.metrics, "term_p_values", None)
    t_stats: Optional[Dict[str, float]] = getattr(result.metrics, "term_t_stats", None)
    if not p_values or not t_stats:
        return None
    terms = [t for t in p_values.keys() if t != "Intercept"] or list(p_values.keys())
    if not terms:
        return None
    terms_sorted = sorted(terms, key=lambda t: abs(t_stats.get(t, 0.0)))
    abs_t = np.array([abs(float(t_stats.get(t, 0.0))) for t in terms_sorted], dtype=float)
    raw_p = np.array([max(1e-16, min(1.0, float(p_values.get(t, 1.0)))) for t in terms_sorted], dtype=float)
    colors_p = ["#16A34A" if p < 0.01 else ("#2563EB" if p < 0.05 else "#94A3B8") for p in raw_p]
    return terms_sorted, abs_t, raw_p, colors_p


def get_default_plot_metadata(result: Any, plot_key: str) -> Dict[str, Any]:
    """Return default title, axis labels, and term/legend labels for a given inline plot key."""
    if result is None:
        return {"title": "", "xlabel": "", "ylabel": "", "term_labels": {}, "legend_labels": {}}

    if plot_key == "parity":
        target_lbl = getattr(result, "target_name", "Output") or "Output"
        ds = getattr(result, "dataset", None)
        n_tr = len(ds.X_train) if ds is not None else 0
        has_test = bool(ds is not None and ds.has_test_set and len(ds.X_test) > 0)
        legend = {"ideal": "1:1 Ideal Fit", "train": f"Train (n={n_tr})"}
        if has_test:
            legend["test"] = f"Test (n={len(ds.X_test)})"
        return {
            "title": f"Actual vs. Predicted Parity — {result.method} (R² = {result.R_sq:.4f})",
            "xlabel": f"Actual {target_lbl}",
            "ylabel": f"Predicted {target_lbl}",
            "term_labels": {},
            "legend_labels": legend,
        }

    if plot_key in ("t_value", "p_value"):
        sig_data = _extract_sorted_sig_terms(result)
        terms = list(reversed(sig_data[0])) if sig_data else []
        return {
            "title": "Effect Magnitude (|t-Value|)" if plot_key == "t_value" else "Statistical Significance (p-Values)",
            "xlabel": "|t-Statistic|" if plot_key == "t_value" else "-log10(p-Value)",
            "ylabel": "",
            "term_labels": {t: t for t in terms},
            "legend_labels": {},
        }

    if plot_key == "importance":
        importance = result.get_feature_importance() if hasattr(result, "get_feature_importance") else {}
        items = sorted(importance.items(), key=lambda kv: kv[1], reverse=True)
        has_coeffs = bool(result.get_coefficients()) if hasattr(result, "get_coefficients") else False
        title_str = (
            "Relative Term Importance (Standardized Weight Share)"
            if has_coeffs
            else "Input Factor Sensitivity (Main-Effect Variance Share)"
        )
        return {
            "title": title_str,
            "xlabel": "Relative Importance (%)",
            "ylabel": "",
            "term_labels": {k: k for k, _ in items},
            "legend_labels": {},
        }

    return {"title": "", "xlabel": "", "ylabel": "", "term_labels": {}, "legend_labels": {}}


def create_t_value_plot(result: Any, overrides: Optional[Dict[str, Any]] = None) -> Optional[Figure]:
    """Create a horizontal bar plot showing |t-Statistic| effect magnitude for parametric models."""
    sig_data = _extract_sorted_sig_terms(result)
    if sig_data is None:
        return None
    terms_sorted, abs_t, _, colors_p = sig_data
    ovr = overrides or {}
    term_map: Dict[str, str] = ovr.get("term_labels") or {}
    display_terms = [term_map.get(t, t) or t for t in terms_sorted]

    n_terms = len(terms_sorted)
    fig_h = max(2.4, min(6.2, 0.35 * n_terms + 1.0))
    fig = Figure(figsize=(6.6, fig_h), dpi=100, facecolor="#FFFFFF")
    ax = fig.subplots(1, 1)

    y_pos = np.arange(n_terms)
    ax.barh(y_pos, abs_t, color=colors_p, height=0.6, edgecolor="#1E293B", linewidth=0.5, alpha=0.9)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(display_terms, fontsize=8.5, color="#0F172A")
    ax.set_xlabel(ovr.get("xlabel") or "|t-Statistic|", fontsize=8.5, fontweight="bold", color="#334155")
    ax.set_title(ovr.get("title") or "Effect Magnitude (|t-Value|)", fontsize=9.5, fontweight="bold", color="#0F172A", pad=8)
    ax.grid(axis="x", linestyle="--", alpha=0.4, color="#CBD5E1")
    ax.set_axisbelow(True)

    max_t = float(np.max(abs_t)) if len(abs_t) > 0 else 1.0
    ax.set_xlim(0, max(1.0, max_t * 1.22))
    for i, tv in enumerate(abs_t):
        ax.text(tv + max(0.02, max_t * 0.018), i, f"{tv:.2f}", va="center", fontsize=8, color="#0F172A", fontweight="bold")

    _style_axes(ax, ylabel=ovr.get("ylabel", ""))
    fig.tight_layout()
    return fig


def create_p_value_plot(result: Any, overrides: Optional[Dict[str, Any]] = None) -> Optional[Figure]:
    """Create a horizontal bar plot showing -log10(p-Value) and significance thresholds."""
    sig_data = _extract_sorted_sig_terms(result)
    if sig_data is None:
        return None
    terms_sorted, _, raw_p, colors_p = sig_data
    neg_log_p = -np.log10(raw_p)
    ovr = overrides or {}
    term_map: Dict[str, str] = ovr.get("term_labels") or {}
    display_terms = [term_map.get(t, t) or t for t in terms_sorted]

    n_terms = len(terms_sorted)
    fig_h = max(2.4, min(6.2, 0.35 * n_terms + 1.0))
    fig = Figure(figsize=(6.6, fig_h), dpi=100, facecolor="#FFFFFF")
    ax = fig.subplots(1, 1)

    y_pos = np.arange(n_terms)
    ax.barh(y_pos, neg_log_p, color=colors_p, height=0.6, edgecolor="#1E293B", linewidth=0.5, alpha=0.9)
    thresh_05 = -np.log10(0.05)
    thresh_01 = -np.log10(0.01)
    ax.axvline(thresh_05, color="#2563EB", linestyle="--", linewidth=1.0, label="p = 0.05")
    ax.axvline(thresh_01, color="#16A34A", linestyle=":", linewidth=1.1, label="p = 0.01")
    ax.set_yticks(y_pos)
    ax.set_yticklabels(display_terms, fontsize=8.5, color="#0F172A")
    ax.set_xlabel(ovr.get("xlabel") or "-log10(p-Value)", fontsize=8.5, fontweight="bold", color="#334155")
    ax.set_title(ovr.get("title") or "Statistical Significance (p-Values)", fontsize=9.5, fontweight="bold", color="#0F172A", pad=8)
    ax.grid(axis="x", linestyle="--", alpha=0.4, color="#CBD5E1")
    ax.set_axisbelow(True)

    max_nlp = max(float(np.max(neg_log_p)) if len(neg_log_p) > 0 else 1.0, thresh_01 + 0.5)
    ax.set_xlim(0, max_nlp * 1.32)
    for i, (nlp, pv) in enumerate(zip(neg_log_p, raw_p)):
        p_lbl = f"p={pv:.2e}" if pv < 0.001 else f"p={pv:.4f}"
        ax.text(nlp + max_nlp * 0.018, i, p_lbl, va="center", fontsize=8, color="#0F172A")
    ax.legend(loc="lower right", fontsize=7.5, framealpha=0.9)

    _style_axes(ax, ylabel=ovr.get("ylabel", ""))
    fig.tight_layout()
    return fig


def create_significance_plot(result: Any, overrides: Optional[Dict[str, Any]] = None) -> Optional[Figure]:
    """Backward-compatible alias returning the p-value significance plot."""
    return create_p_value_plot(result, overrides=overrides)


def create_importance_plot(result: Any, overrides: Optional[Dict[str, Any]] = None) -> Optional[Figure]:
    """Create a horizontal bar chart of normalized parameter / factor relative importance (%)."""
    if result is None or not hasattr(result, "get_feature_importance"):
        return None
    importance = result.get_feature_importance()
    if not importance:
        return None

    ovr = overrides or {}
    term_map: Dict[str, str] = ovr.get("term_labels") or {}
    items = sorted(importance.items(), key=lambda kv: kv[1])
    labels = [term_map.get(k, k) or k for k, _ in items]
    pcts = np.array([100.0 * float(v) for _, v in items], dtype=float)

    n_items = len(labels)
    fig_h = max(2.4, min(6.0, 0.34 * n_items + 1.0))
    fig = Figure(figsize=(6.6, fig_h), dpi=100, facecolor="#FFFFFF")
    ax = fig.subplots(1, 1)

    y_pos = np.arange(n_items)
    ax.barh(y_pos, pcts, color="#2563EB", height=0.6, edgecolor="#1E3A8A", linewidth=0.5, alpha=0.88)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=8.5, color="#0F172A")
    ax.set_xlabel(ovr.get("xlabel") or "Relative Importance (%)", fontsize=8.5, fontweight="bold", color="#334155")

    has_coeffs = bool(result.get_coefficients()) if hasattr(result, "get_coefficients") else False
    default_title = (
        "Relative Term Importance (Standardized Weight Share)"
        if has_coeffs
        else "Input Factor Sensitivity (Main-Effect Variance Share)"
    )
    ax.set_title(ovr.get("title") or default_title, fontsize=9.5, fontweight="bold", color="#0F172A", pad=8)
    ax.grid(axis="x", linestyle="--", alpha=0.4, color="#CBD5E1")
    ax.set_axisbelow(True)

    max_pct = max(10.0, float(np.max(pcts)) if len(pcts) > 0 else 100.0)
    ax.set_xlim(0, min(118.0, max_pct * 1.22))
    for i, val in enumerate(pcts):
        ax.text(val + max_pct * 0.015, i, f"{val:.1f}%", va="center", fontsize=8, color="#0F172A", fontweight="bold")

    _style_axes(ax, ylabel=ovr.get("ylabel", ""))
    fig.tight_layout()
    return fig


def create_parity_plot(
    result: Any, overrides: Optional[Dict[str, Any]] = None,
    normalization: Optional[Union[PlotNormalizationConfig, Dict[str, Any]]] = None,
    opt_output_val: Optional[float] = None,
) -> Optional[Figure]:
    """Create an Actual vs. Predicted parity scatter plot for Training and Test partitions."""
    if result is None or getattr(result, "dataset", None) is None or len(result.dataset.X_train) == 0:
        return None
    ds = result.dataset
    y_tr_actual = np.asarray(ds.y_train, dtype=float).ravel()
    y_tr_pred = np.asarray(result.evaluate_batch(ds.X_train), dtype=float).ravel()

    has_test = ds.has_test_set and len(ds.X_test) > 0
    if has_test:
        y_te_actual = np.asarray(ds.y_test, dtype=float).ravel()
        y_te_pred = np.asarray(result.evaluate_batch(ds.X_test), dtype=float).ravel()
        all_vals = np.concatenate([y_tr_actual, y_tr_pred, y_te_actual, y_te_pred])
        raw_y_data = np.concatenate([y_tr_actual, y_te_actual])
    else:
        y_te_actual, y_te_pred = np.array([]), np.array([])
        all_vals, raw_y_data = np.concatenate([y_tr_actual, y_tr_pred]), y_tr_actual

    norm_cfg = PlotNormalizationConfig.from_dict(normalization) if normalization is not None else None
    z_tf = None
    if norm_cfg is not None and norm_cfg.is_parity_normalized():
        z_tf = resolve_axis_transform(norm_cfg.z_axis, raw_y_data, all_vals, opt_output_val, "Parity Output")
        if z_tf is not None:
            y_tr_actual, y_tr_pred = z_tf.transform(y_tr_actual), z_tf.transform(y_tr_pred)
            if has_test:
                y_te_actual, y_te_pred = z_tf.transform(y_te_actual), z_tf.transform(y_te_pred)
                all_vals = np.concatenate([y_tr_actual, y_tr_pred, y_te_actual, y_te_pred])
            else:
                all_vals = np.concatenate([y_tr_actual, y_tr_pred])

    finite_vals = all_vals[np.isfinite(all_vals)]
    if len(finite_vals) == 0:
        return None

    v_min, v_max = float(np.min(finite_vals)), float(np.max(finite_vals))
    pad = (v_max - v_min) * 0.06 if v_max > v_min else 1.0
    lo, hi = v_min - pad, v_max + pad

    ovr = overrides or {}
    leg_map: Dict[str, str] = ovr.get("legend_labels") or {}
    fig = Figure(figsize=(5.4, 3.6), dpi=100, facecolor="#FFFFFF")
    ax = fig.subplots(1, 1)
    ax.plot([lo, hi], [lo, hi], linestyle="--", color="#64748B", linewidth=1.2, label=leg_map.get("ideal") or "1:1 Ideal Fit", zorder=1)
    ax.scatter(y_tr_actual, y_tr_pred, c="#2563EB", edgecolors="#FFFFFF", linewidth=0.5, s=36, alpha=0.82, label=leg_map.get("train") or f"Train (n={len(y_tr_actual)})", zorder=2)
    if has_test:
        ax.scatter(y_te_actual, y_te_pred, c="#16A34A", edgecolors="#FFFFFF", linewidth=0.6, marker="^", s=44, alpha=0.9, label=leg_map.get("test") or f"Test (n={len(y_te_actual)})", zorder=3)

    target_lbl = getattr(result, "target_name", "Output") or "Output"
    append_suffix = bool(norm_cfg and norm_cfg.append_unit_suffix)
    ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
    ax.set_xlabel(ovr.get("xlabel") or format_normalized_label(f"Actual {target_lbl}", z_tf, append_suffix), fontsize=8.5, fontweight="bold", color="#334155")
    ax.set_ylabel(ovr.get("ylabel") or format_normalized_label(f"Predicted {target_lbl}", z_tf, append_suffix), fontsize=8.5, fontweight="bold", color="#334155")
    ax.set_title(ovr.get("title") or f"Actual vs. Predicted Parity — {result.method} (R² = {result.R_sq:.4f})", fontsize=9.5, fontweight="bold", color="#0F172A", pad=8)
    ax.grid(True, linestyle="--", alpha=0.4, color="#CBD5E1")
    ax.legend(loc="upper left", fontsize=8, framealpha=0.92)
    _style_axes(ax); fig.tight_layout()
    return fig


def build_report_figures(
    result: Any, plot_overrides: Optional[Dict[str, Dict[str, Any]]] = None,
    normalization: Optional[Union[PlotNormalizationConfig, Dict[str, Any]]] = None,
    opt_output_val: Optional[float] = None,
) -> Dict[str, Figure]:
    """Generate all applicable diagnostic figures for a fitted RSMResult, applying optional user overrides."""
    figures: Dict[str, Figure] = {}
    if result is None:
        return figures
    ovr = plot_overrides or {}
    parity_fig = create_parity_plot(result, overrides=ovr.get("parity"), normalization=normalization, opt_output_val=opt_output_val)
    if parity_fig is not None:
        figures["parity"] = parity_fig

    t_fig = create_t_value_plot(result, overrides=ovr.get("t_value"))
    if t_fig is not None:
        figures["t_value"] = t_fig

    p_fig = create_p_value_plot(result, overrides=ovr.get("p_value"))
    if p_fig is not None:
        figures["p_value"] = p_fig

    imp_fig = create_importance_plot(result, overrides=ovr.get("importance"))
    if imp_fig is not None:
        figures["importance"] = imp_fig

    return figures
