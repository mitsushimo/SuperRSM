"""
Regression models and model registry subsystem for SuperRSM.
"""

from super_rsm.models.base import (
    BaseRSMModel,
    ModelMetrics,
    SurfaceGridConfig,
    SurfaceGridResult,
)

from super_rsm.models.registry import (
    ModelRegistry,
    register_model,
    register_rsm_model,
    get_supported_methods,
    get_metadata,
)

# Import model implementations to trigger automatic registration
from super_rsm.models.gaussian_process import GaussianProcessRSMModel
from super_rsm.models.ridge import RidgeCVRSMModel
from super_rsm.models.symbolic import SymbolicRegressorRSMModel
from super_rsm.models.polynomial_ols import PolynomialOLSModel

__all__ = [
    # Base and grid evaluation
    "BaseRSMModel",
    "ModelMetrics",
    "SurfaceGridConfig",
    "SurfaceGridResult",
    # Registry
    "ModelRegistry",
    "register_model",
    "register_rsm_model",
    "get_supported_methods",
    "get_metadata",
    # Concrete Model Classes
    "GaussianProcessRSMModel",
    "RidgeCVRSMModel",
    "SymbolicRegressorRSMModel",
    "PolynomialOLSModel",
]
