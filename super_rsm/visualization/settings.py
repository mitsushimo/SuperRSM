"""
PlotSettings dataclass and profile serialization for SuperRSM visualization.
Provides strong typing, JSON serialization, dictionary compatibility, and presets.
"""

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


@dataclass
class PlotSettings:
    """Configuration settings governing contour plots, typography, and styling."""

    cmap: str = "viridis"
    fill_levels: int = 20
    line_levels: int = 10
    line_color: str = "white"
    line_width: float = 0.5
    inline_color: str = "white"
    inline_fontsize: int = 9
    inline_format: str = "%1.1f"
    alpha: float = 0.85
    uniform_cmap: bool = True
    vmin: Optional[float] = None
    vmax: Optional[float] = None

    show_colorbar: bool = False
    colorbar_label: str = ""

    show_grid: bool = True
    grid_color: str = "gray"
    grid_linestyle: str = "--"
    grid_alpha: float = 0.6

    title_fontsize: int = 14
    axis_label_fontsize: int = 11
    tick_label_fontsize: int = 9
    fig_width: float = 8.0
    fig_height: float = 6.0
    dpi: int = 100

    figure_facecolor: str = "white"
    axes_facecolor: str = "white"
    text_color: str = ".15"

    scatter_data: bool = False
    scatter_size: float = 30.0
    scatter_color_mode: str = "Fixed Color"
    scatter_color: str = "white"
    scatter_cmap: str = "viridis"
    scatter_edgecolor: str = "black"
    scatter_marker: str = "o"
    scatter_vmin: Optional[float] = None
    scatter_vmax: Optional[float] = None

    plot_uncertainty: bool = False
    show_plot: bool = False

    custom_options: Dict[str, Any] = field(default_factory=dict)

    def __getitem__(self, key: str) -> Any:
        if hasattr(self, key):
            return getattr(self, key)
        if key in self.custom_options:
            return self.custom_options[key]
        raise KeyError(f"PlotSettings has no setting '{key}'")

    def __setitem__(self, key: str, value: Any) -> None:
        if hasattr(self, key):
            setattr(self, key, value)
        else:
            self.custom_options[key] = value

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key) or (key in self.custom_options)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def to_dict(self) -> Dict[str, Any]:
        """Convert PlotSettings to a standard dictionary representation."""
        data = asdict(self)
        custom = data.pop("custom_options", {})
        data.update(custom)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlotSettings":
        """Instantiate PlotSettings from a dictionary, mapping unknown keys to custom_options."""
        known_fields = set(cls.__dataclass_fields__.keys()) - {"custom_options"}
        init_kwargs: Dict[str, Any] = {}
        custom: Dict[str, Any] = {}
        for k, v in data.items():
            if k in known_fields:
                init_kwargs[k] = v
            else:
                custom[k] = v
        return cls(**init_kwargs, custom_options=custom)

    def to_json(self, indent: int = 2) -> str:
        """Serialize settings to a JSON formatted string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> "PlotSettings":
        """Deserialize PlotSettings from a JSON string."""
        return cls.from_dict(json.loads(json_str))

    def save_json(self, filepath: Union[str, Path], indent: int = 2) -> None:
        """Save settings to a JSON file on disk."""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.to_json(indent=indent))

    @classmethod
    def load_json(cls, filepath: Union[str, Path]) -> "PlotSettings":
        """Load settings from a JSON file on disk."""
        with open(filepath, "r", encoding="utf-8") as f:
            return cls.from_json(f.read())

    def to_rc_params(self) -> Dict[str, Any]:
        """Convert visual settings into a scoped matplotlib rcParams dictionary."""
        rc: Dict[str, Any] = {
            "figure.figsize": (self.fig_width, self.fig_height),
            "figure.dpi": self.dpi,
            "axes.titlesize": self.title_fontsize,
            "axes.labelsize": self.axis_label_fontsize,
            "xtick.labelsize": self.tick_label_fontsize,
            "ytick.labelsize": self.tick_label_fontsize,
            "axes.grid": self.show_grid,
            "grid.color": self.grid_color,
            "grid.linestyle": self.grid_linestyle,
            "lines.linewidth": self.line_width,
            "figure.facecolor": self.figure_facecolor,
            "axes.facecolor": self.axes_facecolor,
            "text.color": self.text_color,
            "axes.labelcolor": self.text_color,
            "xtick.color": self.text_color,
            "ytick.color": self.text_color,
        }
        if self.grid_alpha is not None:
            rc["grid.alpha"] = self.grid_alpha
        return rc

    @classmethod
    def get_preset(cls, profile_name: str = "default") -> "PlotSettings":
        """Return a pre-configured PlotSettings instance for a standard aesthetic profile."""
        name = profile_name.lower().strip()
        if name == "publication":
            return cls(
                cmap="viridis", fill_levels=25, line_levels=12, line_width=0.4,
                title_fontsize=12, axis_label_fontsize=10, tick_label_fontsize=8,
                fig_width=6.5, fig_height=5.0, dpi=300, show_grid=True,
                grid_color="#cccccc", grid_linestyle="-", grid_alpha=0.5, scatter_size=20.0,
            )
        elif name == "presentation":
            return cls(
                cmap="plasma", fill_levels=20, line_levels=10, line_width=0.8,
                title_fontsize=18, axis_label_fontsize=14, tick_label_fontsize=12,
                fig_width=10.0, fig_height=7.0, dpi=150, show_grid=True,
                grid_color="#888888", grid_linestyle="--", grid_alpha=0.7, scatter_size=50.0,
            )
        elif name == "dark":
            return cls(
                cmap="magma", fill_levels=25, line_levels=12, line_color="cyan",
                line_width=0.6, inline_color="cyan", title_fontsize=14,
                axis_label_fontsize=11, tick_label_fontsize=9, fig_width=8.0, fig_height=6.0,
                dpi=120, show_grid=True, grid_color="#444444", grid_linestyle="--",
                grid_alpha=0.6, scatter_color="cyan", scatter_edgecolor="white", scatter_size=35.0,
                figure_facecolor="#1e1e1e", axes_facecolor="#1e1e1e", text_color="white",
            )
        return cls()

    @classmethod
    def preset(cls, profile_name: str = "default") -> "PlotSettings":
        """Alias for get_preset()."""
        return cls.get_preset(profile_name=profile_name)


default_plot_settings: Dict[str, Any] = PlotSettings().to_dict()
