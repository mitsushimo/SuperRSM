"""
super_rsm/visualization/normalization.py

Presentation-layer axis and output normalization for SuperRSM plots.
Transforms display coordinates, contour levels, uncertainty magnitudes, scatter overlays,
slice labels, and parity plot values strictly at render time without mutating any
upstream dataset, fitted model, or optimization results.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np

NORM_METHODS: Dict[str, str] = {
    "minmax_01": "Min-Max [0, 1]",
    "coded_11": "Coded [-1, 1]",
    "ratio": "Ratio (v / ref)",
}

RANGE_SOURCES: Dict[str, str] = {
    "dataset": "Dataset [Min, Max]",
    "plot_range": "Active Plot Range",
    "custom": "Custom [Min, Max]",
}

RATIO_SOURCES: Dict[str, str] = {
    "dataset_max": "Dataset Max",
    "dataset_mean": "Dataset Mean",
    "optimal": "Optimal Value",
    "plot_max": "Active Plot Max",
    "custom": "Custom Value",
}

ALL_AXIS_KEYS: Tuple[str, ...] = ("x_axis", "y_axis", "z_axis", "p_axis", "q_axis")

AXIS_DISPLAY_NAMES: Dict[str, str] = {
    "x_axis": "X-Axis",
    "y_axis": "Y-Axis",
    "z_axis": "Z-Axis (Output)",
    "p_axis": "Row-Axis (P) Titles",
    "q_axis": "Column-Axis (Q) Titles",
}


def _to_optional_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        v = float(value)
        return v if np.isfinite(v) else None
    except (TypeError, ValueError):
        return None


@dataclass
class AxisNormalizationSpec:
    """Configuration for normalizing a single plot axis or slice dimension."""

    enabled: bool = False
    method: str = "minmax_01"
    reference: str = "dataset"
    custom_min: Optional[float] = None
    custom_max: Optional[float] = None
    custom_ref: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": bool(self.enabled),
            "method": str(self.method),
            "reference": str(self.reference),
            "custom_min": _to_optional_float(self.custom_min),
            "custom_max": _to_optional_float(self.custom_max),
            "custom_ref": _to_optional_float(self.custom_ref),
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "AxisNormalizationSpec":
        if not isinstance(data, dict):
            return cls()
        method = str(data.get("method", "minmax_01"))
        if method not in NORM_METHODS:
            method = "minmax_01"
        default_ref = "dataset_max" if method == "ratio" else "dataset"
        ref = str(data.get("reference", default_ref))
        valid_refs = RATIO_SOURCES if method == "ratio" else RANGE_SOURCES
        if ref not in valid_refs:
            ref = default_ref
        return cls(
            enabled=bool(data.get("enabled", False)),
            method=method,
            reference=ref,
            custom_min=_to_optional_float(data.get("custom_min")),
            custom_max=_to_optional_float(data.get("custom_max")),
            custom_ref=_to_optional_float(data.get("custom_ref")),
        )


@dataclass
class PlotNormalizationConfig:
    """Unified plot-only normalization configuration across Contour, Uncertainty, and Parity plots."""

    apply_to_contour: bool = True
    apply_to_uncertainty: bool = True
    apply_to_parity: bool = False
    append_unit_suffix: bool = False
    x_axis: AxisNormalizationSpec = field(default_factory=AxisNormalizationSpec)
    y_axis: AxisNormalizationSpec = field(default_factory=AxisNormalizationSpec)
    z_axis: AxisNormalizationSpec = field(default_factory=AxisNormalizationSpec)
    p_axis: AxisNormalizationSpec = field(default_factory=AxisNormalizationSpec)
    q_axis: AxisNormalizationSpec = field(default_factory=AxisNormalizationSpec)

    def get_axis_spec(self, key: str) -> AxisNormalizationSpec:
        return getattr(self, key)

    def has_any_enabled(self) -> bool:
        """Return True if at least one plot target and at least one relevant axis are enabled."""
        contour_active = (self.apply_to_contour or self.apply_to_uncertainty) and any(
            getattr(self, k).enabled for k in ALL_AXIS_KEYS
        )
        parity_active = self.apply_to_parity and self.z_axis.enabled
        return bool(contour_active or parity_active)

    def is_parity_normalized(self) -> bool:
        """Return True if inline parity plot normalization is active."""
        return bool(self.apply_to_parity and self.z_axis.enabled)

    def describe_active_normalization(self) -> str:
        """Return a human-readable summary of active plot normalizations, or empty string if none."""
        if not self.has_any_enabled():
            return ""
        targets: List[str] = []
        if self.apply_to_contour and any(getattr(self, k).enabled for k in ALL_AXIS_KEYS):
            targets.append("Contour Plot")
        if self.apply_to_uncertainty and any(
            getattr(self, k).enabled for k in ("x_axis", "y_axis", "z_axis", "p_axis", "q_axis")
        ):
            targets.append("Uncertainty Plot")
        if self.is_parity_normalized():
            targets.append("Inline Parity Plot")

        axis_parts: List[str] = []
        for key in ALL_AXIS_KEYS:
            spec: AxisNormalizationSpec = getattr(self, key)
            if spec.enabled:
                m_lbl = NORM_METHODS.get(spec.method, spec.method)
                ref_map = RATIO_SOURCES if spec.method == "ratio" else RANGE_SOURCES
                r_lbl = ref_map.get(spec.reference, spec.reference)
                axis_parts.append(f"{AXIS_DISPLAY_NAMES[key]}: {m_lbl} ({r_lbl})")

        return (
            f"Plot-only normalization enabled for {', '.join(targets)} "
            f"[{'; '.join(axis_parts)}]. "
            "All upstream model fitting, evaluation, and optimization remain in raw units."
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "apply_to_contour": bool(self.apply_to_contour),
            "apply_to_uncertainty": bool(self.apply_to_uncertainty),
            "apply_to_parity": bool(self.apply_to_parity),
            "append_unit_suffix": bool(self.append_unit_suffix),
            "x_axis": self.x_axis.to_dict(),
            "y_axis": self.y_axis.to_dict(),
            "z_axis": self.z_axis.to_dict(),
            "p_axis": self.p_axis.to_dict(),
            "q_axis": self.q_axis.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Optional[Union["PlotNormalizationConfig", Dict[str, Any]]]) -> "PlotNormalizationConfig":
        if isinstance(data, cls):
            return cls.from_dict(data.to_dict())
        if not isinstance(data, dict):
            return cls()
        return cls(
            apply_to_contour=bool(data.get("apply_to_contour", True)),
            apply_to_uncertainty=bool(data.get("apply_to_uncertainty", True)),
            apply_to_parity=bool(data.get("apply_to_parity", False)),
            append_unit_suffix=bool(data.get("append_unit_suffix", False)),
            x_axis=AxisNormalizationSpec.from_dict(data.get("x_axis")),
            y_axis=AxisNormalizationSpec.from_dict(data.get("y_axis")),
            z_axis=AxisNormalizationSpec.from_dict(data.get("z_axis")),
            p_axis=AxisNormalizationSpec.from_dict(data.get("p_axis")),
            q_axis=AxisNormalizationSpec.from_dict(data.get("q_axis")),
        )


@dataclass(frozen=True)
class ResolvedAxisTransform:
    """Resolved affine transform v' = (v - offset) / scale for presentation-layer plotting."""

    offset: float
    scale: float
    method: str
    unit_suffix: str
    raw_min: Optional[float] = None
    raw_max: Optional[float] = None
    ref_value: Optional[float] = None

    def transform(self, values: Any) -> Any:
        """Transform raw values into normalized display units."""
        if np.ndim(values) == 0:
            return float((float(values) - self.offset) / self.scale)
        arr = np.asarray(values, dtype=float)
        return (arr - self.offset) / self.scale

    def transform_uncertainty(self, std_values: Any) -> Any:
        """Scale predictive standard deviations (sigma) without offset subtraction."""
        abs_scale = abs(self.scale)
        if np.ndim(std_values) == 0:
            return float(float(std_values) / abs_scale)
        arr = np.asarray(std_values, dtype=float)
        return arr / abs_scale


def _finite_1d(values: Any) -> np.ndarray:
    if values is None:
        return np.array([], dtype=float)
    arr = np.asarray(values, dtype=float).ravel()
    return arr[np.isfinite(arr)]


def resolve_axis_transform(
    spec: Optional[AxisNormalizationSpec],
    data_values: Optional[Any] = None,
    plot_values: Optional[Any] = None,
    opt_value: Optional[float] = None,
    axis_name: str = "Axis",
) -> Optional[ResolvedAxisTransform]:
    """
    Resolve an AxisNormalizationSpec into a concrete affine ResolvedAxisTransform.
    Returns None if spec is None or disabled. Raises ValueError on degenerate ranges/references.
    """
    if spec is None or not spec.enabled:
        return None

    data_arr = _finite_1d(data_values)
    plot_arr = _finite_1d(plot_values)
    fallback_arr = data_arr if len(data_arr) > 0 else plot_arr

    if spec.method in ("minmax_01", "coded_11"):
        if spec.reference == "custom":
            if spec.custom_min is None or spec.custom_max is None:
                raise ValueError(f"{axis_name}: Custom [Min, Max] normalization requires both Min and Max values.")
            vmin, vmax = float(spec.custom_min), float(spec.custom_max)
        elif spec.reference == "plot_range":
            src = plot_arr if len(plot_arr) > 0 else data_arr
            if len(src) == 0:
                raise ValueError(f"{axis_name}: No finite values available to determine plot range.")
            vmin, vmax = float(np.min(src)), float(np.max(src))
        else:  # "dataset"
            src = data_arr if len(data_arr) > 0 else plot_arr
            if len(src) == 0:
                raise ValueError(f"{axis_name}: No finite dataset values available for normalization.")
            vmin, vmax = float(np.min(src)), float(np.max(src))

        span = vmax - vmin
        if abs(span) < 1e-12:
            raise ValueError(
                f"{axis_name}: Cannot normalize constant range [{vmin:.4g}, {vmax:.4g}] (min == max)."
            )

        if spec.method == "minmax_01":
            return ResolvedAxisTransform(
                offset=vmin,
                scale=span,
                method="minmax_01",
                unit_suffix="[Norm. 0–1]",
                raw_min=vmin,
                raw_max=vmax,
            )
        # coded_11: 2*(v - vmin)/(vmax - vmin) - 1 = (v - mid) / half_span
        mid = 0.5 * (vmin + vmax)
        half_span = 0.5 * span
        return ResolvedAxisTransform(
            offset=mid,
            scale=half_span,
            method="coded_11",
            unit_suffix="[Coded -1 to 1]",
            raw_min=vmin,
            raw_max=vmax,
        )

    if spec.method == "ratio":
        ref_val: Optional[float] = None
        if spec.reference == "custom":
            if spec.custom_ref is None:
                raise ValueError(f"{axis_name}: Custom Ratio normalization requires a non-zero reference value.")
            ref_val = float(spec.custom_ref)
        elif spec.reference == "optimal":
            if opt_value is not None and np.isfinite(opt_value):
                ref_val = float(opt_value)
            elif len(fallback_arr) > 0:
                ref_val = float(np.max(np.abs(fallback_arr)))
        elif spec.reference == "dataset_mean":
            src = data_arr if len(data_arr) > 0 else plot_arr
            if len(src) > 0:
                ref_val = float(np.mean(src))
        elif spec.reference == "plot_max":
            src = plot_arr if len(plot_arr) > 0 else data_arr
            if len(src) > 0:
                ref_val = float(np.max(src))
        else:  # "dataset_max"
            src = data_arr if len(data_arr) > 0 else plot_arr
            if len(src) > 0:
                ref_val = float(np.max(src))

        if ref_val is None or not np.isfinite(ref_val) or abs(ref_val) < 1e-12:
            raise ValueError(
                f"{axis_name}: Ratio normalization reference value is zero or unavailable ({ref_val})."
            )
        return ResolvedAxisTransform(
            offset=0.0,
            scale=ref_val,
            method="ratio",
            unit_suffix="[Normalized]",
            ref_value=ref_val,
        )

    raise ValueError(f"{axis_name}: Unsupported normalization method '{spec.method}'.")


def format_normalized_label(
    base_label: str,
    transform: Optional[ResolvedAxisTransform],
    append_suffix: bool = False,
) -> str:
    """Optionally append a normalized unit hint to a default label."""
    if not append_suffix or transform is None or not base_label:
        return base_label
    if transform.unit_suffix in base_label:
        return base_label
    return f"{base_label} {transform.unit_suffix}"
