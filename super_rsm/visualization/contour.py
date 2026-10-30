"""
MultiContourEngine and Matplotlib figure generator for SuperRSM.
Renders publication-quality multi-slice contour plots with zero global side-effects
via scoped styling contexts (plt.rc_context), headless execution, and backward compatibility.
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import numpy as np

from super_rsm.models.base import SurfaceGridResult
from super_rsm.visualization.settings import PlotSettings


def validate_multi_contour_inputs(
    X: Any, Y: Any, Z_array: Any,
    label_array: Optional[Any] = None, scatter_array: Optional[Any] = None,
) -> Tuple[bool, Optional[str]]:
    """Validate multi-contour inputs, preserving 100% backward compatibility."""
    try:
        X_np, Y_np = np.asarray(X), np.asarray(Y)
    except Exception as e:
        return False, f"X and Y must be array-like: {e}"

    if X_np.ndim != 2 or Y_np.ndim != 2:
        return False, f"X and Y must be 2D arrays. Got X ndim: {X_np.ndim}, Y ndim: {Y_np.ndim}."
    if X_np.shape != Y_np.shape:
        return False, f"X and Y must have the exact same shape. Got X: {X_np.shape}, Y: {Y_np.shape}."

    ny, nx = X_np.shape
    try:
        m = len(Z_array)
        if m == 0:
            return False, "Z_array cannot be empty."
        n = len(Z_array[0])
    except Exception:
        return False, "Z_array must be a 2D grid (nested list or array) of 2D data arrays."

    for i in range(m):
        if not hasattr(Z_array[i], "__len__") or len(Z_array[i]) != n:
            return False, f"Z_array rows have inconsistent lengths. Row 0 has {n}, row {i} has {len(Z_array[i]) if hasattr(Z_array[i], '__len__') else 'non-sequence'}."
        for j in range(n):
            try:
                Z_ij = np.asarray(Z_array[i][j])
            except Exception:
                return False, f"Element at Z_array[{i}][{j}] cannot be converted to a NumPy array."
            if Z_ij.shape != (ny, nx):
                return False, f"Z_array[{i}][{j}] shape {Z_ij.shape} does not match X and Y shape {(ny, nx)}."

    for name, arr in [("label_array", label_array), ("scatter_array", scatter_array)]:
        if arr is not None:
            try:
                if len(arr) != m or any(len(row) != n for row in arr):
                    return False, f"{name} dimensions must match Z_array outer grid ({m}x{n})."
            except Exception:
                return False, f"{name} must be a 2D nested list or array matching Z_array outer dimensions."

    return True, None


class MultiContourEngine:
    """Pure Matplotlib multi-subplot contour generator with scoped styling contexts."""

    @classmethod
    def render(
        cls,
        grid_result: SurfaceGridResult,
        settings: Optional[Union[PlotSettings, Dict[str, Any]]] = None,
        title: str = "Multi-Contour Visualization",
        xlabel: str = "X",
        ylabel: str = "Y",
        label_array: Optional[List[List[str]]] = None,
        show: bool = False,
        save_path: Optional[str] = None,
        render_uncertainty: bool = False,
        uncertainty_overlay: bool = True,
    ) -> Tuple[Figure, np.ndarray]:
        """Generate multi-slice contour figure within scoped plt.rc_context."""
        ps = settings if isinstance(settings, PlotSettings) else (
            PlotSettings.from_dict(settings) if isinstance(settings, dict) else PlotSettings()
        )
        Z_data = grid_result.U_array if (render_uncertainty and grid_result.U_array) else grid_result.Z_array
        m, n = len(Z_data), len(Z_data[0])
        X, Y = grid_result.X_mesh, grid_result.Y_mesh
        x_min, x_max = float(np.min(X)), float(np.max(X))
        y_min, y_max = float(np.min(Y)), float(np.max(Y))

        fill_levels, line_levels, z_min, z_max = cls._calc_levels(Z_data, ps)
        rc_params = cls.build_rc_params(ps)

        with plt.rc_context(rc_params):
            fig, axes = plt.subplots(m, n, sharex=True, sharey=True, squeeze=False)
            last_cf = None

            for i in range(m):
                for j in range(n):
                    ax = axes[i, j]
                    Z_ij = Z_data[i][j]
                    levels_arg = fill_levels if (ps.uniform_cmap or ps.show_colorbar) else ps.fill_levels
                    kwargs_cf: Dict[str, Any] = {"cmap": ps.cmap, "alpha": ps.alpha, "levels": levels_arg}
                    if ps.uniform_cmap or ps.show_colorbar:
                        kwargs_cf["vmin"], kwargs_cf["vmax"] = z_min, z_max
                    last_cf = ax.contourf(X, Y, Z_ij, **kwargs_cf)

                    lines = ax.contour(X, Y, Z_ij, levels=line_levels, colors=ps.line_color, linewidths=ps.line_width)
                    ax.clabel(lines, inline=True, fontsize=ps.inline_fontsize, fmt=ps.inline_format, colors=ps.inline_color)

                    if uncertainty_overlay and not render_uncertainty and grid_result.U_array is not None:
                        u_lines = ax.contour(X, Y, grid_result.U_array[i][j], levels=max(ps.line_levels // 2, 5),
                                             colors="#e74c3c", linestyles="--", linewidths=0.7)
                        ax.clabel(u_lines, inline=True, fontsize=max(ps.inline_fontsize - 1, 6), fmt="u=%1.2f", colors="#e74c3c")

                    if ps.scatter_data and grid_result.scatter_array is not None:
                        cls._render_scatter(ax, grid_result.scatter_array[i][j], ps, z_min, z_max, Z_ij, x_min, x_max, y_min, y_max)
                    else:
                        ax.set_xlim(x_min, x_max)
                        ax.set_ylim(y_min, y_max)

                    if label_array is not None and i < len(label_array) and j < len(label_array[i]):
                        ax.set_title(str(label_array[i][j]))
                    ax.set_xlabel(xlabel)
                    ax.set_ylabel(ylabel)
                    if ps.show_grid:
                        ax.grid(True, color=ps.grid_color, linestyle=ps.grid_linestyle, alpha=getattr(ps, "grid_alpha", 0.6))

            if ps.show_colorbar and last_cf is not None:
                cbar = fig.colorbar(last_cf, ax=axes.ravel().tolist())
                if ps.colorbar_label:
                    cbar.set_label(ps.colorbar_label)

            if title:
                fig.suptitle(title)
            if save_path:
                fig.savefig(save_path, dpi=ps.dpi, bbox_inches="tight")
            if show or ps.show_plot:
                plt.show()

        return fig, axes

    @classmethod
    def build_rc_params(cls, settings: PlotSettings) -> Dict[str, Any]:
        """Extract scoped rcParams dictionary from PlotSettings."""
        if hasattr(settings, "to_rc_params") and callable(settings.to_rc_params):
            return settings.to_rc_params()
        rc: Dict[str, Any] = {
            "figure.figsize": (settings.fig_width, settings.fig_height), "figure.dpi": settings.dpi,
            "axes.titlesize": settings.title_fontsize, "axes.labelsize": settings.axis_label_fontsize,
            "xtick.labelsize": settings.tick_label_fontsize, "ytick.labelsize": settings.tick_label_fontsize,
            "axes.grid": settings.show_grid, "grid.color": settings.grid_color,
            "grid.linestyle": settings.grid_linestyle, "lines.linewidth": settings.line_width,
            "figure.facecolor": "white", "axes.facecolor": "white", "text.color": ".15",
            "axes.labelcolor": ".15", "xtick.color": ".15", "ytick.color": ".15",
        }
        if getattr(settings, "grid_alpha", None) is not None:
            rc["grid.alpha"] = settings.grid_alpha
        return rc

    @classmethod
    def _calc_levels(cls, Z_data: List[List[np.ndarray]], ps: PlotSettings) -> Tuple[np.ndarray, np.ndarray, float, float]:
        z_min = ps.vmin if ps.vmin is not None else min(float(np.min(arr)) for row in Z_data for arr in row)
        z_max = ps.vmax if ps.vmax is not None else max(float(np.max(arr)) for row in Z_data for arr in row)
        if np.isclose(z_min, z_max):
            z_min -= 1e-6
            z_max += 1e-6
        use_unif = ps.uniform_cmap or ps.show_colorbar
        fill_levels = np.linspace(z_min, z_max, ps.fill_levels) if use_unif else np.asarray(ps.fill_levels)
        line_levels = np.linspace(z_min, z_max, ps.line_levels) if use_unif else np.asarray(ps.line_levels)
        return fill_levels, line_levels, z_min, z_max

    @classmethod
    def _render_scatter(
        cls, ax: Any, pts: Any, ps: PlotSettings, z_min: float, z_max: float, Z_ij: np.ndarray,
        x_min: float, x_max: float, y_min: float, y_max: float,
    ) -> None:
        if pts is None or len(pts) < 2 or len(pts[0]) == 0:
            ax.set_xlim(x_min, x_max)
            ax.set_ylim(y_min, y_max)
            return
        x_pts, y_pts = pts[0], pts[1]
        color_mode = getattr(ps, "scatter_color_mode", "Fixed Color")
        if color_mode == "Output Value (Colormap)" and len(pts) >= 3 and pts[2] is not None and len(pts[2]) > 0:
            s_cmap = ps.scatter_cmap or ps.cmap
            if ps.scatter_vmin is not None and ps.scatter_vmax is not None:
                s_vmin, s_vmax = ps.scatter_vmin, ps.scatter_vmax
            elif ps.uniform_cmap:
                s_vmin, s_vmax = z_min, z_max
            else:
                s_vmin, s_vmax = float(np.min(Z_ij)), float(np.max(Z_ij))
                if np.isclose(s_vmin, s_vmax):
                    s_vmin, s_vmax = s_vmin - 1e-6, s_vmax + 1e-6
            ax.scatter(x_pts, y_pts, s=ps.scatter_size, c=pts[2], cmap=s_cmap, vmin=s_vmin, vmax=s_vmax,
                       edgecolors=ps.scatter_edgecolor, marker=ps.scatter_marker, zorder=5)
        else:
            ax.scatter(x_pts, y_pts, s=ps.scatter_size, c=ps.scatter_color,
                       edgecolors=ps.scatter_edgecolor, marker=ps.scatter_marker, zorder=5)
        ax.set_xlim(x_min, x_max)
        ax.set_ylim(y_min, y_max)


def plot_multi_contour(
    X: Any, Y: Any, Z_array: Any,
    label_array: Optional[Any] = None, title: str = "Multi-Contour Visualization",
    xlabel: str = "X", ylabel: str = "Y", plot_settings: Optional[Dict[str, Any]] = None,
    scatter_array: Optional[Any] = None,
) -> Tuple[Figure, np.ndarray]:
    """Legacy forwarder for multi-slice contour plots, returning (fig, axes)."""
    is_valid, msg = validate_multi_contour_inputs(X, Y, Z_array, label_array, scatter_array)
    if not is_valid:
        raise ValueError(msg)
    settings = PlotSettings.from_dict(plot_settings) if plot_settings else PlotSettings()
    grid_res = SurfaceGridResult(
        X_mesh=np.asarray(X), Y_mesh=np.asarray(Y),
        Z_array=[[np.asarray(col) for col in row] for row in Z_array], scatter_array=scatter_array,
    )
    return MultiContourEngine.render(
        grid_result=grid_res, settings=settings, title=title, xlabel=xlabel, ylabel=ylabel, label_array=label_array,
    )


def plot_a_function(
    func: Any, x_range: Any, y_range: Any, p_range: Any, q_range: Any,
    title: str = "Function Visualization", xlabel: str = "X", ylabel: str = "Y",
    label_array: Optional[Any] = None, plot_settings: Optional[Dict[str, Any]] = None,
) -> Tuple[Figure, np.ndarray]:
    """Legacy forwarder evaluating f(X, Y, p, q) over coordinate ranges."""
    x, y, p, q = np.asarray(x_range), np.asarray(y_range), np.asarray(p_range), np.asarray(q_range)
    X, Y = np.meshgrid(x, y)
    Z_array = []
    for p_i in p:
        row = []
        for q_j in q:
            try:
                row.append(func(X, Y, p_i, q_j))
            except TypeError:
                row.append(func(X, Y))
        Z_array.append(row)
    if label_array is None:
        label_array = [[f"p={p_i}, q={q_j}" for q_j in q] for p_i in p]
    return plot_multi_contour(X, Y, Z_array, label_array=label_array, title=title,
                              xlabel=xlabel, ylabel=ylabel, plot_settings=plot_settings)
