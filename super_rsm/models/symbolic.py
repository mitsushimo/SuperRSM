"""
Symbolic Regression using Genetic Programming (gplearn).
Discovers analytical closed-form mathematical equations with variable mapping.
"""

import re
from typing import Any, ClassVar, List, Optional
from gplearn.functions import make_function
from gplearn.genetic import SymbolicRegressor
import numpy as np
from sklearn.metrics import mean_squared_error, r2_score

from super_rsm.common.config import HyperparameterSpec, ModelMetadata
from super_rsm.common.types import ModelCategory
from super_rsm.models.base import BaseRSMModel, ModelMetrics
from super_rsm.models.registry import register_model


def piecewise_function(condition: np.ndarray, true_val: np.ndarray, false_val: np.ndarray) -> np.ndarray:
    """Piecewise step function primitive for symbolic genetic programming."""
    return np.where(condition > 0, true_val, false_val)


@register_model
class SymbolicRegressorRSMModel(BaseRSMModel):
    """
    Symbolic regression using genetic programming (gplearn).
    Discovers analytical mathematical equations directly from data.
    """

    metadata: ClassVar[ModelMetadata] = ModelMetadata(
        name="Genetic Programming",
        display_name="Genetic Programming (Symbolic Regressor)",
        category=ModelCategory.SYMBOLIC,
        description="Symbolic regression using genetic programming (gplearn).",
        supports_uncertainty=False,
        supports_coefficients=False,
        supports_feature_importance=False,
        supports_formula=True,
        has_anova=False,
        hyperparameters=[
            HyperparameterSpec("population_size", "Population Size", int, default=2000, min_val=50, max_val=20000, step=50,
                               tooltip="Number of candidate formula programs per generation"),
            HyperparameterSpec("generations", "Generations", int, default=20, min_val=2, max_val=100, step=1,
                               tooltip="Number of evolutionary generations"),
            HyperparameterSpec("parsimony_coefficient", "Parsimony Coefficient", float, default=0.005, min_val=0.0001, max_val=0.1, step=0.001,
                               tooltip="Penalty weight on formula tree complexity"),
            HyperparameterSpec("random_state", "Random State", int, default=42, min_val=0, max_val=99999, step=1,
                               tooltip="Random seed for search reproducibility"),
        ],
    )

    def __init__(
        self,
        population_size: int = 2000,
        generations: int = 20,
        parsimony_coefficient: float = 0.005,
        random_state: int = 42,
        **kwargs: Any,
    ):
        super().__init__(
            population_size=population_size,
            generations=generations,
            parsimony_coefficient=parsimony_coefficient,
            random_state=random_state,
            **kwargs,
        )
        self.population_size = population_size
        self.generations = generations
        self.parsimony_coefficient = parsimony_coefficient
        self.random_state = random_state
        self.model: Optional[SymbolicRegressor] = None

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> "SymbolicRegressorRSMModel":
        """Fit genetic programming symbolic regression model."""
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)
                self.hyperparameters[k] = v

        X_arr = np.asarray(X, dtype=float)
        y_arr = np.asarray(y, dtype=float).ravel()
        if X_arr.ndim == 1:
            X_arr = X_arr.reshape(-1, 1)

        self.feature_names = (
            list(feature_names) if feature_names is not None else [f"x{i+1}" for i in range(X_arr.shape[1])]
        )

        piecewise = make_function(function=piecewise_function, name="piecewise", arity=3)
        function_set = ["add", "sub", "mul", "div", "sqrt", "log", piecewise]

        self.model = SymbolicRegressor(
            function_set=function_set,
            population_size=self.population_size,
            generations=self.generations,
            stopping_criteria=0.0,
            p_crossover=0.7,
            p_subtree_mutation=0.1,
            p_hoist_mutation=0.05,
            p_point_mutation=0.1,
            max_samples=0.9,
            parsimony_coefficient=self.parsimony_coefficient,
            random_state=self.random_state,
            const_range=(-30, 30),
        )
        self.model.fit(X_arr, y_arr)
        self.X_train = X_arr
        self.y_train = y_arr
        self.is_fitted = True

        y_pred = self.model.predict(X_arr)
        mse = mean_squared_error(y_arr, y_pred)
        rmse = float(np.sqrt(mse))
        r2 = r2_score(y_arr, y_pred)
        self.metrics = ModelMetrics(r2=float(r2), rmse=rmse, mse=float(mse))
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Compute predicted output using the evolved symbolic program tree."""
        self._ensure_fitted()
        X_arr = np.asarray(X, dtype=float)
        if X_arr.ndim == 1:
            X_arr = X_arr.reshape(1, -1) if len(X_arr) == len(self.feature_names) else X_arr.reshape(-1, 1)
        y_pred = self.model.predict(X_arr)
        return np.asarray(y_pred, dtype=float).ravel()

    def get_formula(self) -> Optional[str]:
        """Extract analytical equation with physical variable token substitution."""
        self._ensure_fitted()
        if not hasattr(self.model, "_program") or self.model._program is None:
            return None
        expr_str = str(self.model._program)

        def repl(match: re.Match) -> str:
            idx = int(match.group(1))
            if idx < len(self.feature_names):
                return self.feature_names[idx]
            return match.group(0)

        formatted = re.sub(r"\bX(\d+)\b", repl, expr_str)
        return f"y = {formatted}"
