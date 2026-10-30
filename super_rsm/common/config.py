"""
Configuration schemas, hyperparameter specifications, model metadata, and constraint DTOs.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from super_rsm.common.types import ModelCategory, ConstraintOperator
from super_rsm.common.exceptions import (
    HyperparameterValidationError,
    ConstraintValidationError,
)


@dataclass(frozen=True)
class HyperparameterSpec:
    """
    Specification of a user-tunable model hyperparameter for dynamic UI and CLI configuration.
    """
    name: str
    display_name: str
    param_type: type  # int, float, str, bool
    default: Any
    min_val: Optional[Union[int, float]] = None
    max_val: Optional[Union[int, float]] = None
    step: Optional[Union[int, float]] = None
    choices: Optional[List[Any]] = None
    tooltip: str = ""

    def validate(self, value: Any) -> Any:
        """Validate and cast a value against this specification."""
        try:
            cast_value = self.param_type(value)
        except (ValueError, TypeError) as exc:
            raise HyperparameterValidationError(
                f"Hyperparameter '{self.name}' must be of type {self.param_type.__name__}, got {value!r}"
            ) from exc

        if self.choices is not None and cast_value not in self.choices:
            raise HyperparameterValidationError(
                f"Hyperparameter '{self.name}' must be one of {self.choices}, got {cast_value!r}"
            )

        if self.min_val is not None and cast_value < self.min_val:
            raise HyperparameterValidationError(
                f"Hyperparameter '{self.name}' value {cast_value} < minimum allowed {self.min_val}"
            )

        if self.max_val is not None and cast_value > self.max_val:
            raise HyperparameterValidationError(
                f"Hyperparameter '{self.name}' value {cast_value} > maximum allowed {self.max_val}"
            )

        return cast_value


@dataclass(frozen=True)
class ModelMetadata:
    """
    Static metadata describing model capabilities, parameter schema, and diagnostic properties.
    """
    name: str
    display_name: str
    category: ModelCategory
    description: str
    supports_uncertainty: bool = False
    supports_coefficients: bool = False
    supports_feature_importance: bool = False
    supports_formula: bool = False
    has_anova: bool = False
    hyperparameters: List[HyperparameterSpec] = field(default_factory=list)

    def get_hyperparameter(self, name: str) -> Optional[HyperparameterSpec]:
        """Retrieve hyperparameter specification by parameter name."""
        for hp in self.hyperparameters:
            if hp.name == name:
                return hp
        return None

    def get_default_hyperparameters(self) -> Dict[str, Any]:
        """Return dictionary of default parameter values."""
        return {hp.name: hp.default for hp in self.hyperparameters}


@dataclass
class ConstraintSpec:
    """
    Specification of a linear inequality or equality constraint:
    sum(c_i * x_i) [operator] bound.
    """
    coeffs: Dict[str, float]
    operator: ConstraintOperator
    bound: float

    def __post_init__(self) -> None:
        if not self.coeffs:
            raise ConstraintValidationError("Constraint must contain at least one variable coefficient.")
        if not isinstance(self.operator, ConstraintOperator):
            try:
                self.operator = ConstraintOperator(self.operator)
            except ValueError as exc:
                raise ConstraintValidationError(f"Invalid constraint operator: {self.operator}") from exc

    def to_expression(self) -> str:
        """
        Format as human-readable string expression, e.g., '2*x1 - 1.5*x2 <= 10.0'.
        Preserves formatting without requiring GUI presentation code.
        """
        terms = []
        for col, coeff in self.coeffs.items():
            if abs(coeff) < 1e-12:
                continue
            terms.append((col, coeff, f"{coeff:g}"))

        if not terms:
            return f"(No non-zero terms) {self.operator.value} {self.bound:g}"

        expr_parts = []
        for i, (col, coeff, coeff_str) in enumerate(terms):
            if i == 0:
                if coeff == 1.0:
                    expr_parts.append(f"{col}")
                elif coeff == -1.0:
                    expr_parts.append(f"-{col}")
                else:
                    expr_parts.append(f"{coeff_str}*{col}")
            else:
                if coeff > 0:
                    if coeff == 1.0:
                        expr_parts.append(f"+ {col}")
                    else:
                        expr_parts.append(f"+ {coeff_str}*{col}")
                else:
                    if coeff == -1.0:
                        expr_parts.append(f"- {col}")
                    else:
                        expr_parts.append(f"- {abs(coeff):g}*{col}")

        return f"{' '.join(expr_parts)} {self.operator.value} {self.bound:g}"

    def evaluate(self, point: Dict[str, float]) -> bool:
        """Evaluate if the provided point dictionary satisfies the constraint."""
        val = sum(coeff * point.get(var, 0.0) for var, coeff in self.coeffs.items())
        if self.operator == ConstraintOperator.LE:
            return val <= self.bound + 1e-9
        elif self.operator == ConstraintOperator.GE:
            return val >= self.bound - 1e-9
        elif self.operator == ConstraintOperator.EQ:
            return abs(val - self.bound) <= 1e-9
        return False
