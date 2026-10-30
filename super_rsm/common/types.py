"""
Common types, enums, and protocols for SuperRSM.
"""

from enum import Enum
from typing import Dict, List, Sequence, Tuple, Union
import numpy as np


class ProblemType(str, Enum):
    """Supported problem types in SuperRSM."""
    REGRESSION = "regression"
    SURROGATE = "surrogate"
    RESPONSE_SURFACE = "response_surface"


class ModelCategory(str, Enum):
    """Categorical classification of regression and surrogate models."""
    POLYNOMIAL = "Parametric / Polynomial"
    KERNEL = "Non-Parametric / Kernel (Kriging)"
    ENSEMBLE = "Tree Ensemble"
    SYMBOLIC = "Symbolic / Evolutionary"
    NEURAL = "Neural / Deep Learning"


class OptimizationGoal(str, Enum):
    """Continuous optimization direction."""
    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"


class ConstraintOperator(str, Enum):
    """Relational operators for linear constraints."""
    LE = "<="
    GE = ">="
    EQ = "=="


# Type aliases for domain clarity
EvaluationPoint = Union[np.ndarray, Sequence[float], Dict[str, float]]
ArrayLike = Union[np.ndarray, Sequence[float], Sequence[Sequence[float]]]
BoundsDict = Dict[str, Tuple[float, float]]
BoundsList = List[Tuple[float, float]]
CoeffsDict = Dict[str, float]
FeatureNames = List[str]
MetricDict = Dict[str, Union[float, Dict[str, float], None]]
