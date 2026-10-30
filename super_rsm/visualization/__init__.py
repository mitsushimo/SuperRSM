"""
Visualization package for SuperRSM providing multi-dimensional response surface
rendering, scoped styling contexts, fast vectorized grid sampling, and legacy shims.
Zero global side-effects: importing this package does not mutate matplotlib.rcParams.
"""

from super_rsm.visualization.settings import PlotSettings, default_plot_settings
from super_rsm.visualization.grid import GridSampler
from super_rsm.visualization.contour import (
    MultiContourEngine,
    plot_multi_contour,
    validate_multi_contour_inputs,
    plot_a_function,
)
from super_rsm.visualization.service import VisualizationService

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
