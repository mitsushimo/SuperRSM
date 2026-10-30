"""
high_d_plotter.py

Clean root facade re-exporting the modularized SuperRSM visualization engine.
"""

from super_rsm.visualization import (
    VisualizationService,
    MultiContourEngine,
    GridSampler,
    PlotSettings,
    plot_multi_contour,
    validate_multi_contour_inputs,
    plot_a_function,
    default_plot_settings,
)

__all__ = [
    "VisualizationService",
    "MultiContourEngine",
    "GridSampler",
    "PlotSettings",
    "plot_multi_contour",
    "validate_multi_contour_inputs",
    "plot_a_function",
    "default_plot_settings",
]
