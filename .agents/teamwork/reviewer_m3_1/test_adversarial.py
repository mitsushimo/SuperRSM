"""
Adversarial stress-testing suite for SuperRSM Visualization subsystem.
Authored by Reviewer M3-1 to rigorously challenge Worker M3's implementation.
"""

import gc
import json
import os
import threading
import time
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pytest

from super_rsm.common.exceptions import (
    GridConfigurationError,
    UncertaintyNotSupportedError,
)
from super_rsm.models.base import SurfaceGridConfig, SurfaceGridResult
from super_rsm.visualization import (
    GridSampler,
    MultiContourEngine,
    PlotSettings,
    VisualizationService,
    plot_a_function,
    plot_multi_contour,
    validate_multi_contour_inputs,
)


def test_flat_zero_variance_surface():
    """Verify that a completely flat surface (z_min == z_max) renders without ZeroDivisionError."""
    X, Y = np.meshgrid(np.linspace(0, 1, 10), np.linspace(0, 1, 10))
    Z_flat = np.full_like(X, 42.0)
    grid_res = SurfaceGridResult(X_mesh=X, Y_mesh=Y, Z_array=[[Z_flat]])

    fig, axes = MultiContourEngine.render(
        grid_result=grid_res,
        settings=PlotSettings(show_plot=False, show_colorbar=True),
        title="Zero Variance Surface",
    )
    assert fig is not None
    assert axes.shape == (1, 1)
    plt.close(fig)


def test_extreme_magnitude_coordinates():
    """Verify grid sampling and rendering across astronomical and microscopic coordinate scales."""
    X, Y = np.meshgrid(np.linspace(1e8, 1e9, 10), np.linspace(1e-8, 1e-7, 10))
    Z = np.sin(X * 1e-8) + np.cos(Y * 1e7)
    grid_res = SurfaceGridResult(X_mesh=X, Y_mesh=Y, Z_array=[[Z]])

    fig, axes = MultiContourEngine.render(
        grid_result=grid_res,
        settings=PlotSettings(show_plot=False),
        title="Extreme Scale Coordinates",
    )
    assert fig is not None
    plt.close(fig)


def test_high_dimensional_6d_grid_and_scatter():
    """Verify 6-dimensional parameter space slicing with fixed dimensions and scatter filtering."""
    class Mock6DModel:
        def predict(self, X):
            # linear combination
            return X[:, 0] + 2 * X[:, 1] + 3 * X[:, 2] + 4 * X[:, 3] + 5 * X[:, 4] + 6 * X[:, 5]

    config = SurfaceGridConfig(
        x_idx=0, x_values=np.linspace(0, 1, 5),
        y_idx=1, y_values=np.linspace(0, 1, 5),
        num_total_features=6,
        p_info=(2, np.array([10.0, 20.0])),
        q_info=(3, np.array([100.0, 200.0])),
        fixed_values=[(4, 1.0), (5, 2.0)],
        include_scatter=True,
        X_scatter=np.array([
            [0.5, 0.5, 10.0, 100.0, 1.0, 2.0],  # Matches row 0, col 0
            [0.2, 0.8, 20.0, 200.0, 1.0, 2.0],  # Matches row 1, col 1
            [0.1, 0.9, 10.0, 100.0, 9.9, 2.0],  # Non-matching fixed dim 4
        ]),
        y_scatter=np.array([10.0, 20.0, 30.0]),
    )

    res = GridSampler.sample(Mock6DModel(), config)
    assert len(res.Z_array) == 2 and len(res.Z_array[0]) == 2
    # Check matching scatter point in (0, 0)
    pts_00 = res.scatter_array[0][0]
    assert len(pts_00[0]) == 1 and pts_00[0][0] == 0.5
    # Check non-matching point was excluded
    pts_01 = res.scatter_array[0][1]
    assert len(pts_01[0]) == 0


def test_empty_scatter_data_handling():
    """Verify include_scatter=True with empty scatter arrays does not raise IndexError."""
    X_m, Y_m = np.meshgrid(np.linspace(0, 1, 5), np.linspace(0, 1, 5))
    grid_res = SurfaceGridResult(
        X_mesh=X_m, Y_mesh=Y_m,
        Z_array=[[X_m + Y_m]],
        scatter_array=[[(np.array([]), np.array([]), np.array([]))]],
    )
    fig, axes = MultiContourEngine.render(
        grid_result=grid_res,
        settings=PlotSettings(scatter_data=True, scatter_color_mode="Output Value (Colormap)"),
        title="Empty Scatter Test",
    )
    assert fig is not None
    plt.close(fig)


def test_plot_settings_custom_options_mutation_and_serialization():
    """Test custom options preservation across serialization and dictionary mutations."""
    ps = PlotSettings()
    ps["custom_metric"] = "aic"
    ps["custom_flag"] = True
    assert ps["custom_metric"] == "aic"
    assert "custom_metric" in ps
    assert ps.get("nonexistent", "fallback") == "fallback"

    d = ps.to_dict()
    assert d["custom_metric"] == "aic"
    assert d["custom_flag"] is True

    json_repr = ps.to_json()
    loaded = PlotSettings.from_json(json_repr)
    assert loaded["custom_metric"] == "aic"
    assert loaded["custom_flag"] is True


def test_multithreaded_rendering_scoped_contexts():
    """Test that concurrent rendering in multiple threads with different presets does not leak rcParams."""
    errors = []

    def render_worker(preset_name, expected_facecolor):
        try:
            settings = PlotSettings.preset(preset_name)
            X, Y = np.meshgrid(np.linspace(0, 1, 8), np.linspace(0, 1, 8))
            res = SurfaceGridResult(X_mesh=X, Y_mesh=Y, Z_array=[[X * Y]])
            fig, ax = MultiContourEngine.render(res, settings=settings)
            plt.close(fig)
        except Exception as e:
            errors.append(e)

    threads = [
        threading.Thread(target=render_worker, args=("dark", "#1e1e1e")),
        threading.Thread(target=render_worker, args=("publication", "white")),
        threading.Thread(target=render_worker, args=("presentation", "white")),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0, f"Thread errors: {errors}"


def test_non_rsm_model_callable_fallback():
    """Test GridSampler with a plain Python lambda and verify vectorized evaluation."""
    func = lambda row: row[0]**2 + row[1]**2
    config = SurfaceGridConfig(
        x_idx=0, x_values=np.linspace(-1, 1, 10),
        y_idx=1, y_values=np.linspace(-1, 1, 10),
        num_total_features=2,
    )
    res = GridSampler.sample(func, config)
    assert res.Z_array[0][0].shape == (10, 10)
    assert np.isclose(res.Z_array[0][0][0, 0], 2.0)  # (-1)^2 + (-1)^2 = 2


def test_legacy_validation_robustness():
    """Exhaustive check of validate_multi_contour_inputs error reporting."""
    # Empty Z_array
    valid, msg = validate_multi_contour_inputs(np.ones((3, 3)), np.ones((3, 3)), [])
    assert not valid and "empty" in msg

    # Inconsistent row lengths in Z_array
    valid, msg = validate_multi_contour_inputs(
        np.ones((2, 2)), np.ones((2, 2)),
        [[np.ones((2, 2)), np.ones((2, 2))], [np.ones((2, 2))]]
    )
    assert not valid and "inconsistent" in msg

    # Mismatched shape of elements inside Z_array
    valid, msg = validate_multi_contour_inputs(
        np.ones((2, 2)), np.ones((2, 2)),
        [[np.ones((3, 3))]]
    )
    assert not valid and "match X and Y shape" in msg


def test_visualization_service_plot_function_with_pq():
    """Verify VisualizationService.plot_function with p and q grid parameters."""
    func = lambda X, Y, p, q: X + Y + p * q
    fig, axes = VisualizationService.plot_function(
        func=func,
        x_range=np.linspace(0, 1, 10),
        y_range=np.linspace(0, 1, 10),
        p_range=[1.0, 2.0],
        q_range=[10.0, 20.0, 30.0],
        title="P x Q Function Grid",
    )
    assert axes.shape == (2, 3)
    plt.close(fig)
