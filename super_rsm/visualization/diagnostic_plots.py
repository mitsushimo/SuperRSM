"""
super_rsm/visualization/diagnostic_plots.py

Headless diagnostic figure generators for SuperRSM model reports:
- Parameter Significance & p-Value Bar Plot (|t-statistic| and -log10(p-value))
- Relative Importance / Factor Sensitivity Bar Plot (%)
- Actual vs. Predicted Parity Plot (Train vs. Test sets)
Uses Figure and FigureCanvasAgg directly to avoid global pyplot state or memory leaks.
"""

import base64
import io
from typing import Any, Dict, Optional
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
import numpy as np


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


def create_significance_plot(result: Any) -> Optional[Figure]:
    """
    Create a two-panel horizontal bar plot showing |t-Statistic| and -log10(p-Value)
    with alpha=0.05 and alpha=0.01 reference thresholds for parametric models.
    """
    if result is None or getattr(result, "metrics", None) is None:
        return None
    p_values: Optional[Dict[str, float]] = getattr(result.metrics, "term_p_values", None)
    t_stats: Optional[Dict[str, float]] = getattr(result.metrics, "term_t_stats", None)
    if not p_values or not t_stats:
        return None

    terms = [t for t in p_values.keys() if t != "Intercept"]
    if not terms:
        terms = list(p_values.keys())
    if not terms:
        return None

    # Sort terms so most significant (largest |t|) appears at the top
    terms_sorted = sorted(terms, key=lambda t: abs(t_stats.get(t, 0.0)))
    abs_t = np.array([abs(float(t_stats.get(t, 0.0))) for t in terms_sorted], dtype=float)
    raw_p = np.array([max(1e-16, min(1.0, float(p_values.get(t, 1.0)))) for t in terms_sorted], dtype=float)
    neg_log_p = -np.log10(raw_p)

    n_terms = len(terms_sorted)
    fig_h = max(2.6, min(6.5, 0.36 * n_terms + 1.1))
    fig = Figure(figsize=(7.2, fig_h), dpi=100, facecolor="#FFFFFF")
    ax_t, ax_p = fig.subplots(1, 2, sharey=True)

    y_pos = np.arange(n_terms)
    colors_p = [
        "#16A34A" if p < 0.01 else ("#2563EB" if p < 0.05 else "#94A3B8")
        for p in raw_p
    ]

    # Left panel: |t-Value|
    ax_t.barh(y_pos, abs_t, color=colors_p, height=0.62, edgecolor="#1E293B", linewidth=0.5, alpha=0.9)
    ax_t.set_yticks(y_pos)
    ax_t.set_yticklabels(terms_sorted, fontsize=8.5, color="#0F172A")
    ax_t.set_xlabel("|t-Statistic|", fontsize=8.5, fontweight="bold", color="#334155")
    ax_t.set_title("Effect Magnitude (|t-Value|)", fontsize=9.5, fontweight="bold", color="#0F172A", pad=8)
    ax_t.grid(axis="x", linestyle="--", alpha=0.4, color="#CBD5E1")
    ax_t.set_axisbelow(True)
    max_t = float(np.max(abs_t)) if len(abs_t) > 0 else 1.0
    ax_t.set_xlim(0, max(1.0, max_t * 1.22))
    for i, tv in enumerate(abs_t):
        ax_t.text(tv + max(0.02, max_t * 0.02), i, f"{tv:.2f}", va="center", fontsize=7.5, color="#334155")

    # Right panel: -log10(p-Value) & exact p-value labels
    ax_p.barh(y_pos, neg_log_p, color=colors_p, height=0.62, edgecolor="#1E293B", linewidth=0.5, alpha=0.9)
    thresh_05 = -np.log10(0.05)
    thresh_01 = -np.log10(0.01)
    ax_p.axvline(thresh_05, color="#2563EB", linestyle="--", linewidth=1.0, label="p = 0.05")
    ax_p.axvline(thresh_01, color="#16A34A", linestyle=":", linewidth=1.1, label="p = 0.01")
    ax_p.set_xlabel("-log10(p-Value)", fontsize=8.5, fontweight="bold", color="#334155")
    ax_p.set_title("Statistical Significance (p-Values)", fontsize=9.5, fontweight="bold", color="#0F172A", pad=8)
    ax_p.grid(axis="x", linestyle="--", alpha=0.4, color="#CBD5E1")
    ax_p.set_axisbelow(True)

    max_nlp = max(float(np.max(neg_log_p)) if len(neg_log_p) > 0 else 1.0, thresh_01 + 0.5)
    ax_p.set_xlim(0, max_nlp * 1.32)
    for i, (nlp, pv) in enumerate(zip(neg_log_p, raw_p)):
        p_lbl = f"p={pv:.2e}" if pv < 0.001 else f"p={pv:.4f}"
        ax_p.text(nlp + max_nlp * 0.02, i, p_lbl, va="center", fontsize=7.5, color="#0F172A")
    ax_p.legend(loc="lower right", fontsize=7.5, framealpha=0.9)

    for ax in (ax_t, ax_p):
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#CBD5E1")
        ax.spines["bottom"].set_color("#CBD5E1")
        ax.tick_params(colors="#334155", labelsize=8)

    fig.tight_layout()
    return fig


def create_importance_plot(result: Any) -> Optional[Figure]:
    """
    Create a horizontal bar chart of normalized parameter / factor relative importance (%).
    """
    if result is None or not hasattr(result, "get_feature_importance"):
        return None
    importance = result.get_feature_importance()
    if not importance:
        return None

    items = sorted(importance.items(), key=lambda kv: kv[1])
    labels = [k for k, _ in items]
    pcts = np.array([100.0 * float(v) for _, v in items], dtype=float)

    n_items = len(labels)
    fig_h = max(2.4, min(6.0, 0.34 * n_items + 1.0))
    fig = Figure(figsize=(6.6, fig_h), dpi=100, facecolor="#FFFFFF")
    ax = fig.subplots(1, 1)

    y_pos = np.arange(n_items)
    ax.barh(y_pos, pcts, color="#2563EB", height=0.6, edgecolor="#1E3A8A", linewidth=0.5, alpha=0.88)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=8.5, color="#0F172A")
    ax.set_xlabel("Relative Importance (%)", fontsize=8.5, fontweight="bold", color="#334155")

    has_coeffs = bool(result.get_coefficients()) if hasattr(result, "get_coefficients") else False
    title_str = (
        "Relative Term Importance (Standardized Weight Share)"
        if has_coeffs
        else "Input Factor Sensitivity (Main-Effect Variance Share)"
    )
    ax.set_title(title_str, fontsize=9.5, fontweight="bold", color="#0F172A", pad=8)
    ax.grid(axis="x", linestyle="--", alpha=0.4, color="#CBD5E1")
    ax.set_axisbelow(True)

    max_pct = max(10.0, float(np.max(pcts)) if len(pcts) > 0 else 100.0)
    ax.set_xlim(0, min(118.0, max_pct * 1.22))
    for i, val in enumerate(pcts):
        ax.text(val + max_pct * 0.015, i, f"{val:.1f}%", va="center", fontsize=8, color="#0F172A", fontweight="bold")

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#CBD5E1")
    ax.spines["bottom"].set_color("#CBD5E1")
    ax.tick_params(colors="#334155", labelsize=8)

    fig.tight_layout()
    return fig


def create_parity_plot(result: Any) -> Optional[Figure]:
    """
    Create an Actual vs. Predicted parity scatter plot for Training and Test partitions.
    """
    if result is None or getattr(result, "dataset", None) is None:
        return None
    ds = result.dataset
    if len(ds.X_train) == 0:
        return None

    y_tr_actual = np.asarray(ds.y_train, dtype=float).ravel()
    y_tr_pred = np.asarray(result.evaluate_batch(ds.X_train), dtype=float).ravel()

    has_test = ds.has_test_set and len(ds.X_test) > 0
    if has_test:
        y_te_actual = np.asarray(ds.y_test, dtype=float).ravel()
        y_te_pred = np.asarray(result.evaluate_batch(ds.X_test), dtype=float).ravel()
        all_vals = np.concatenate([y_tr_actual, y_tr_pred, y_te_actual, y_te_pred])
    else:
        y_te_actual, y_te_pred = np.array([]), np.array([])
        all_vals = np.concatenate([y_tr_actual, y_tr_pred])

    finite_vals = all_vals[np.isfinite(all_vals)]
    if len(finite_vals) == 0:
        return None

    v_min, v_max = float(np.min(finite_vals)), float(np.max(finite_vals))
    pad = (v_max - v_min) * 0.06 if v_max > v_min else 1.0
    lo, hi = v_min - pad, v_max + pad

    fig = Figure(figsize=(5.4, 3.6), dpi=100, facecolor="#FFFFFF")
    ax = fig.subplots(1, 1)

    ax.plot([lo, hi], [lo, hi], linestyle="--", color="#64748B", linewidth=1.2, label="1:1 Ideal Fit", zorder=1)
    ax.scatter(
        y_tr_actual, y_tr_pred, c="#2563EB", edgecolors="#FFFFFF", linewidth=0.5,
        s=36, alpha=0.82, label=f"Train (n={len(y_tr_actual)})", zorder=2,
    )
    if has_test:
        ax.scatter(
            y_te_actual, y_te_pred, c="#16A34A", edgecolors="#FFFFFF", linewidth=0.6,
            marker="^", s=44, alpha=0.9, label=f"Test (n={len(y_te_actual)})", zorder=3,
        )

    target_lbl = getattr(result, "target_name", "Output") or "Output"
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_xlabel(f"Actual {target_lbl}", fontsize=8.5, fontweight="bold", color="#334155")
    ax.set_ylabel(f"Predicted {target_lbl}", fontsize=8.5, fontweight="bold", color="#334155")
    ax.set_title(
        f"Actual vs. Predicted Parity — {result.method} (R² = {result.R_sq:.4f})",
        fontsize=9.5, fontweight="bold", color="#0F172A", pad=8,
    )
    ax.grid(True, linestyle="--", alpha=0.4, color="#CBD5E1")
    ax.legend(loc="upper left", fontsize=8, framealpha=0.92)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#CBD5E1")
    ax.spines["bottom"].set_color("#CBD5E1")
    ax.tick_params(colors="#334155", labelsize=8)

    fig.tight_layout()
    return fig


def build_report_figures(result: Any) -> Dict[str, Figure]:
    """Generate all applicable diagnostic figures for a fitted RSMResult."""
    figures: Dict[str, Figure] = {}
    if result is None:
        return figures

    parity_fig = create_parity_plot(result)
    if parity_fig is not None:
        figures["parity"] = parity_fig

    sig_fig = create_significance_plot(result)
    if sig_fig is not None:
        figures["significance"] = sig_fig

    imp_fig = create_importance_plot(result)
    if imp_fig is not None:
        figures["importance"] = imp_fig

    return figures

