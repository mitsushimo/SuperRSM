"""
super_rsm/core/__init__.py

Core domain logic, headless pipeline orchestration, and numerical optimization for SuperRSM.
"""

from super_rsm.core.dataset import RSMDataset, build_data
from super_rsm.core.result import RSMResult, rsm_result
from super_rsm.core.optimization import OptimizationEngine, OptimizationResult
from super_rsm.core.pipeline import fit_rsm, fit_rsm2, rsm_fromDF

__all__ = [
    "RSMDataset",
    "RSMResult",
    "rsm_result",
    "OptimizationEngine",
    "OptimizationResult",
    "fit_rsm",
    "fit_rsm2",
    "rsm_fromDF",
    "build_data",
]
