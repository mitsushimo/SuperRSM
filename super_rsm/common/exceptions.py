"""
Hierarchical exception classes for SuperRSM.
"""


class SuperRSMError(Exception):
    """Root base exception for all SuperRSM errors."""
    pass


class ModelError(SuperRSMError):
    """Base class for model training, prediction, and evaluation errors."""
    pass


class ModelFitError(ModelError):
    """Raised when model training or fitting fails (e.g., non-convergence, singular matrix)."""
    pass


class ModelNotFittedError(ModelError):
    """Raised when attempting to predict or inspect metrics on an unfitted model."""
    pass


class PredictionError(ModelError):
    """Raised when model prediction fails due to dimension mismatch or invalid input."""
    pass


class UncertaintyNotSupportedError(ModelError):
    """Raised when predictive uncertainty is requested from a model that does not support it."""
    pass


class OptimizationError(SuperRSMError):
    """Raised when continuous optimization encounters an infeasible or numerical error."""
    pass


class ConfigurationError(SuperRSMError):
    """Base class for invalid configuration or parameter specifications."""
    pass


class GridConfigurationError(ConfigurationError):
    """Raised when response surface grid dimensions collide, are unassigned, or invalid."""
    pass


class ConstraintValidationError(ConfigurationError):
    """Raised when a linear constraint is malformed or mathematically inconsistent."""
    pass


class HyperparameterValidationError(ConfigurationError):
    """Raised when a hyperparameter value violates type, bound, or choice constraints."""
    pass


class DataValidationError(SuperRSMError):
    """Raised when input datasets contain NaNs, Infs, dimension mismatches, or missing columns."""
    pass


class RegistryError(SuperRSMError):
    """Raised when model registration or retrieval fails in ModelRegistry."""
    pass
