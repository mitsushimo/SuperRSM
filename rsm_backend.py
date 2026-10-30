"""
rsm_backend.py

Clean root facade re-exporting the modularized SuperRSM core pipeline and model registry.
"""

from super_rsm.core import (
    RSMDataset,
    RSMResult,
    rsm_result,
    OptimizationEngine,
    OptimizationResult,
    fit_rsm,
    fit_rsm2,
    rsm_fromDF,
    build_data,
)
from super_rsm.models import (
    BaseRSMModel,
    ModelRegistry,
    register_model,
    register_rsm_model,
    get_supported_methods,
    get_metadata,
    GaussianProcessRSMModel,
    RidgeCVRSMModel,
    SymbolicRegressorRSMModel,
    PolynomialOLSModel,
)
from super_rsm.models.ridge import _generate_polynomial_term_names


def generate_term_strings(column_names, model):
    """Return polynomial term strings for a fitted polynomial model."""
    if hasattr(model, "term_names") and model.term_names:
        return [t for t in model.term_names if t != "Intercept"]
    if hasattr(model, "named_steps") and "polynomialfeatures" in model.named_steps:
        return _generate_polynomial_term_names(column_names, model.named_steps["polynomialfeatures"])
    if hasattr(model, "pipeline") and hasattr(model.pipeline, "named_steps"):
        return _generate_polynomial_term_names(column_names, model.pipeline.named_steps["polynomialfeatures"])
    return list(column_names)


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
    "BaseRSMModel",
    "ModelRegistry",
    "register_model",
    "register_rsm_model",
    "get_supported_methods",
    "get_metadata",
    "generate_term_strings",
    "GaussianProcessRSMModel",
    "RidgeCVRSMModel",
    "SymbolicRegressorRSMModel",
    "PolynomialOLSModel",
]
