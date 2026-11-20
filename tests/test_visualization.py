"""
Comprehensive automated test suite for SuperRSM Visualization subsystem:
1. Verification that importing and using visualization does NOT alter global matplotlib.rcParams
2. Vectorized GridSampler latency benchmark (< 50ms for 10,000 grid points)
3. Multi-dimensional grid slicing (P x Q subplots) and spatial scatter filtering
4. MultiContourEngine headless figure generation and layout
5. VisualizationService facade execution with SurfaceGridConfig and legacy dict config
6. RSMResult.visualize_rsm() integration and uncertainty error handling
7. PlotSettings profile presets and JSON serialization round-trip
8. Backward compatibility shims for high_d_plotter functions
"""

import os
from pathlib import Path
import time
import matplotlib
matplotlib.use("Agg")  # Enforce headless Agg backend for tests
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from super_rsm.common.exceptions import (
    GridConfigurationError,
    UncertaintyNotSupportedError,
)
from super_rsm.core import RSMDataset, fit_rsm
from super_rsm.models import PolynomialOLSModel, SurfaceGridConfig, SurfaceGridResult
from super_rsm.visualization import (
    PlotSettings,
    GridSampler,
    MultiContourEngine,
    VisualizationService,
    validate_multi_contour_inputs,
    plot_a_function,
    plot_multi_contour,
)


@pytest.fixture(scope="module")
def sample_dataset():
    path = Path(__file__).resolve().parent.parent / "sample_data.csv"
    assert path.exists(), f"sample_data.csv not found at {path}"
    df = pd.read_csv(path)
    return RSMDataset.from_dataframe(df, ["x1", "x2"], "y", test_size=0.20, random_state=42)


@pytest.fixture(scope="module")
def fitted_gp(sample_dataset):
    return fit_rsm(sample_dataset, method="Gaussian Process", degree_fit=0, noise_level=0.1)


@pytest.fixture(scope="module")
def fitted_ols(sample_dataset):
    return fit_rsm(sample_dataset, method="Polynomial OLS", degree_fit=2)


def test_zero_global_rcparams_mutation(fitted_ols):
    orig_rc = dict(matplotlib.rcParams)
    settings = PlotSettings.preset("dark")
    fig, axes = VisualizationService.visualize_result(
        result=fitted_ols,
        plot_settings=settings,
        title="Scoped Dark Theme Test",
    )
    plt.close(fig)

    for key in ["axes.facecolor", "figure.facecolor", "text.color", "axes.grid"]:
        assert matplotlib.rcParams[key] == orig_rc[key], f"Global rcParams['{key}'] was altered!"


def test_plot_settings_profiles_and_serialization():
    default_ps = PlotSettings()
    assert default_ps.cmap in ("plasma", "viridis") and default_ps.alpha > 0.0

    pub_ps = PlotSettings.preset("publication")
    assert pub_ps.dpi >= 300 and pub_ps.grid_linestyle == "-"

    d = pub_ps.to_dict()
    assert isinstance(d, dict) and d["dpi"] == pub_ps.dpi
    restored = PlotSettings.from_dict(d)
    assert restored.dpi == pub_ps.dpi and restored.cmap == pub_ps.cmap

    json_str = pub_ps.to_json()
    assert isinstance(json_str, str)
    from_json_ps = PlotSettings.from_json(json_str)
    assert from_json_ps.dpi == pub_ps.dpi

    rc = pub_ps.to_rc_params()
    assert isinstance(rc, dict) and "figure.dpi" in rc


def test_grid_sampler_10k_latency_benchmark(fitted_ols):
    config = SurfaceGridConfig(
        x_idx=0, x_values=np.linspace(0.0, 5.0, 100),
        y_idx=1, y_values=np.linspace(0.0, 5.0, 100),
        num_total_features=2,
    )
    _ = GridSampler.sample(fitted_ols.model, config)  # Warmup

    t0 = time.perf_counter()
    res = GridSampler.sample(fitted_ols.model, config)
    elapsed = time.perf_counter() - t0

    assert elapsed < 0.050, f"10k grid evaluation took {elapsed * 1000:.2f}ms (target < 50ms)"
    assert res.X_mesh.shape == (100, 100) and res.Z_array[0][0].shape == (100, 100)


def test_multidim_slices_and_scatter_filtering():
    X_obs = np.array([
        [1.0, 2.0, 10.0, 100.0],
        [1.5, 2.5, 20.0, 100.0],
        [0.0, 0.0, 30.0, 200.0],
    ])
    y_obs = np.array([5.0, 6.0, 7.0])

    rng = np.random.RandomState(42)
    m4 = PolynomialOLSModel(degree_fit=1)
    m4.fit(rng.randn(30, 4), rng.randn(30))

    config = SurfaceGridConfig(
        x_idx=0, x_values=np.linspace(0, 3, 10),
        y_idx=1, y_values=np.linspace(0, 3, 10),
        num_total_features=4,
        p_info=(2, np.array([10.0, 20.0])),  # 2 row slices
        q_info=(3, np.array([100.0, 200.0])),  # 2 col slices
        include_scatter=True,
        X_scatter=X_obs,
        y_scatter=y_obs,
    )
    res = GridSampler.sample(m4, config)

    assert len(res.Z_array) == 2 and len(res.Z_array[0]) == 2
    pts_00 = res.scatter_array[0][0]
    assert len(pts_00[0]) == 1 and pts_00[0][0] == 1.0


def test_grid_config_validation_errors():
    with pytest.raises(GridConfigurationError, match="distinct"):
        SurfaceGridConfig(x_idx=0, x_values=np.linspace(0, 1, 5), y_idx=0, y_values=np.linspace(0, 1, 5), num_total_features=2).validate()
    with pytest.raises(GridConfigurationError, match="unassigned"):
        SurfaceGridConfig(x_idx=0, x_values=np.linspace(0, 1, 5), y_idx=1, y_values=np.linspace(0, 1, 5), num_total_features=3).validate()


def test_multi_contour_engine_headless_generation():
    X_m, Y_m = np.meshgrid(np.linspace(0, 1, 10), np.linspace(0, 1, 10))
    grid_res = SurfaceGridResult(
        X_mesh=X_m, Y_mesh=Y_m,
        Z_array=[[X_m + Y_m, X_m * 2], [Y_m * 2, X_m * Y_m]],
    )
    fig, axes = MultiContourEngine.render(
        grid_result=grid_res,
        settings=PlotSettings(show_plot=False),
        title="Headless Engine Test",
    )
    assert isinstance(fig, matplotlib.figure.Figure)
    assert axes.shape == (2, 2)
    plt.close(fig)


def test_visualization_service_visualize_result(fitted_ols, tmp_path):
    legacy_cfg = {
        "x": (0, np.linspace(0.0, 5.0, 20)),
        "y": (1, np.linspace(0.0, 5.0, 20)),
    }
    save_file = str(tmp_path / "test_surface.png")
    fig, axes = VisualizationService.visualize_result(
        result=fitted_ols,
        config=legacy_cfg,
        plot_settings={"scatter_data": True, "show_plot": False},
        save_path=save_file,
    )
    assert isinstance(fig, matplotlib.figure.Figure)
    assert os.path.exists(save_file) and os.path.getsize(save_file) > 0
    plt.close(fig)

    fig_def, _ = VisualizationService.visualize_result(result=fitted_ols, config=None)
    assert isinstance(fig_def, matplotlib.figure.Figure)
    plt.close(fig_def)


def test_result_visualize_rsm_and_uncertainty(fitted_gp, fitted_ols, tmp_path):
    save_file = str(tmp_path / "gp_main.png")
    fig_gp, axes_gp = fitted_gp.visualize_rsm(
        config={"x": (0, np.linspace(0, 5, 10)), "y": (1, np.linspace(0, 5, 10))},
        title="GP Response",
        plot_settings={
            "plot_uncertainty": True,
            "show_colorbar": True,
            "colorbar_label": "y",
            "scatter_data": True,
            "scatter_color_mode": "Output Value (Colormap)",
            "show_plot": False,
        },
        save_path=save_file,
    )
    assert isinstance(fig_gp, matplotlib.figure.Figure)
    assert hasattr(fig_gp, "uncertainty_figure")
    fig_unc = fig_gp.uncertainty_figure
    assert isinstance(fig_unc, matplotlib.figure.Figure)
    assert fig_unc is not fig_gp
    assert fig_unc._suptitle.get_text() == "GP Response (Uncertainty)"
    assert os.path.exists(save_file)
    assert os.path.exists(str(tmp_path / "gp_main_uncertainty.png"))
    plt.close(fig_gp)
    plt.close(fig_unc)

    with pytest.raises(UncertaintyNotSupportedError):
        fitted_ols.visualize_rsm(
            config={"x": (0, np.linspace(0, 5, 10)), "y": (1, np.linspace(0, 5, 10))},
            plot_settings={"plot_uncertainty": True},
        )


def test_backward_compatible_shims():
    valid, msg = validate_multi_contour_inputs(np.zeros((2, 2)), np.zeros((2, 2)), [[np.zeros((2, 2))]])
    assert valid and msg is None
    invalid, err = validate_multi_contour_inputs(np.zeros((2, 2)), np.zeros((3, 3)), [[np.zeros((2, 2))]])
    assert not invalid and err is not None

    fig, _ = plot_a_function(lambda X, Y, p, q: X + Y, [0, 1], [0, 1], [0], [0], plot_settings={"show_plot": False})
    assert isinstance(fig, matplotlib.figure.Figure)
    plt.close(fig)


def test_compute_figsize_scales_for_large_grids():
    ps = PlotSettings(fig_width=8.0, fig_height=6.0, subplot_width=3.2, subplot_height=2.8)
    assert MultiContourEngine.compute_figsize(1, 1, ps) == (8.0, 6.0)

    w4, h4 = MultiContourEngine.compute_figsize(4, 4, ps, has_title=True, has_colorbar=False)
    assert w4 > 8.0 and h4 > 6.0

    w4_cb, h4_cb = MultiContourEngine.compute_figsize(4, 4, ps, has_title=True, has_colorbar=True)
    assert w4_cb > w4 and h4_cb == h4

    ps_fixed = PlotSettings(fig_width=8.0, fig_height=6.0, auto_figsize=False)
    assert MultiContourEngine.compute_figsize(5, 5, ps_fixed, has_title=True, has_colorbar=True) == (8.0, 6.0)


@pytest.mark.parametrize("m,n", [(4, 4), (5, 4), (4, 1), (1, 4)])
@pytest.mark.parametrize("outer_only", [True, False])
@pytest.mark.parametrize("show_colorbar", [False, True])
def test_large_multi_contour_grid_no_label_title_overlap(m, n, outer_only, show_colorbar):
    X_m, Y_m = np.meshgrid(np.linspace(0, 10, 12), np.linspace(0, 10, 12))
    Z_array = [[np.sin(X_m + i) + np.cos(Y_m + j) for j in range(n)] for i in range(m)]
    labels = [[f"p={i}, q={j}" for j in range(n)] for i in range(m)]
    grid_res = SurfaceGridResult(X_mesh=X_m, Y_mesh=Y_m, Z_array=Z_array)

    ps = PlotSettings(
        show_plot=False,
        show_colorbar=show_colorbar,
        colorbar_label="Response" if show_colorbar else "",
        auto_layout=True,
        auto_figsize=True,
        outer_labels_only=outer_only,
    )
    fig, axes = MultiContourEngine.render(
        grid_result=grid_res,
        settings=ps,
        title="Multi-Contour Overlap Check",
        xlabel="Temperature (C)",
        ylabel="Pressure (kPa)",
        label_array=labels,
    )
    try:
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()

        # Verify label placement respects outer_labels_only
        for i in range(m):
            for j in range(n):
                expected_x = "Temperature (C)" if (not outer_only or i == m - 1) else ""
                expected_y = "Pressure (kPa)" if (not outer_only or j == 0) else ""
                assert axes[i, j].get_xlabel() == expected_x
                assert axes[i, j].get_ylabel() == expected_y

        # Verify zero overlap between row i xlabel/axes and row i+1 title
        for i in range(m - 1):
            for j in range(n):
                ax_top, ax_bot = axes[i, j], axes[i + 1, j]
                title_bbox = ax_bot.title.get_window_extent(renderer=renderer)
                assert not ax_top.get_window_extent(renderer=renderer).overlaps(title_bbox)
                if ax_top.xaxis.label.get_text():
                    xlabel_bbox = ax_top.xaxis.label.get_window_extent(renderer=renderer)
                    assert not xlabel_bbox.overlaps(title_bbox)

        # Verify zero overlap between suptitle and top-row titles
        if fig._suptitle is not None and fig._suptitle.get_text():
            sup_bbox = fig._suptitle.get_window_extent(renderer=renderer)
            for j in range(n):
                assert not sup_bbox.overlaps(axes[0, j].title.get_window_extent(renderer=renderer))
    finally:
        plt.close(fig)
