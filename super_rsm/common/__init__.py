"""
Common types, configurations, specifications, and exceptions for SuperRSM.
"""

from super_rsm.common.types import (
    ProblemType,
    ModelCategory,
    OptimizationGoal,
    ConstraintOperator,
    EvaluationPoint,
    ArrayLike,
    BoundsDict,
    BoundsList,
    CoeffsDict,
    FeatureNames,
    MetricDict,
)

from super_rsm.common.exceptions import (
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

from super_rsm.common.config import (
    HyperparameterSpec,
    ModelMetadata,
    ConstraintSpec,
)

__all__ = [
    # Types & Enums
    "ProblemType",
    "ModelCategory",
    "OptimizationGoal",
    "ConstraintOperator",
    "EvaluationPoint",
    "ArrayLike",
    "BoundsDict",
    "BoundsList",
    "CoeffsDict",
    "FeatureNames",
    "MetricDict",
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
    # Config & DTOs
    "HyperparameterSpec",
    "ModelMetadata",
    "ConstraintSpec",
]
