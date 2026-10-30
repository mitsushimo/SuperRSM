"""
SuperRSM: Modular Response Surface Methodology and Extensible Surrogate Modeling.
"""

__version__ = "2.0.0"

from super_rsm.common import (
    ProblemType,
    ModelCategory,
    OptimizationGoal,
    ConstraintOperator,
    HyperparameterSpec,
    ModelMetadata,
    ConstraintSpec,
    SuperRSMError,
    ModelError,
    ModelFitError,
    ModelNotFittedError,
    PredictionError,
    UncertaintyNotSupportedError,
    OptimizationError,
    ConfigurationError,
    GridConfigurationError,
    ConstraintValidationError,
    HyperparameterValidationError,
    DataValidationError,
    RegistryError,
)

from super_rsm.models import (
    BaseRSMModel,
    ModelMetrics,
    SurfaceGridConfig,
    SurfaceGridResult,
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

__all__ = [
    "__version__",
    # Common Types & Config
    "ProblemType",
    "ModelCategory",
    "OptimizationGoal",
    "ConstraintOperator",
    "HyperparameterSpec",
    "ModelMetadata",
    "ConstraintSpec",
    # Exceptions
    "SuperRSMError",
    "ModelError",
    "ModelFitError",
    "ModelNotFittedError",
    "PredictionError",
    "UncertaintyNotSupportedError",
    "OptimizationError",
    "ConfigurationError",
    "GridConfigurationError",
    "ConstraintValidationError",
    "HyperparameterValidationError",
    "DataValidationError",
    "RegistryError",
    # Models & Registry
    "BaseRSMModel",
    "ModelMetrics",
    "SurfaceGridConfig",
    "SurfaceGridResult",
    "ModelRegistry",
    "register_model",
    "register_rsm_model",
    "get_supported_methods",
    "get_metadata",
    "GaussianProcessRSMModel",
    "RidgeCVRSMModel",
    "SymbolicRegressorRSMModel",
    "PolynomialOLSModel",
    # Core Domain & Pipeline
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
