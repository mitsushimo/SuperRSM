"""
super_rsm/core/dataset.py

RSMDataset container: headless dataset encapsulation, array validation,
train/test splitting, summary statistics, and bounding box computation.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from super_rsm.common.exceptions import DataValidationError
from super_rsm.common.types import ArrayLike
from super_rsm.models.diagnostics import compute_input_groups


def _split_arrays(
    X: np.ndarray,
    y: np.ndarray,
    test_size: float,
    random_state: Optional[int],
    shuffle: bool,
    split_by_groups: bool,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Split (X, y) either row-wise or grouped by unique input parameter combinations."""
    if test_size < 0.0 or test_size >= 1.0:
        raise DataValidationError(f"test_size must be in [0.0, 1.0), got {test_size}")
    if test_size <= 0.0 or len(X) <= 1:
        n_feat = X.shape[1] if X.ndim == 2 else 0
        return X, np.empty((0, n_feat), dtype=float), y, np.empty((0,), dtype=float)

    if not split_by_groups:
        return train_test_split(X, y, test_size=test_size, random_state=random_state, shuffle=shuffle)

    group_ids, n_groups = compute_input_groups(X)
    if n_groups < 2:
        raise DataValidationError(
            "Cannot split by unique input combinations when fewer than 2 unique input combinations exist."
        )
    if n_groups == len(X):
        return train_test_split(X, y, test_size=test_size, random_state=random_state, shuffle=shuffle)

    unique_groups = np.arange(n_groups)
    train_groups, test_groups = train_test_split(
        unique_groups, test_size=test_size, random_state=random_state, shuffle=shuffle
    )
    train_idx = np.concatenate([np.flatnonzero(group_ids == g) for g in train_groups])
    test_idx = np.concatenate([np.flatnonzero(group_ids == g) for g in test_groups])
    return X[train_idx], X[test_idx], y[train_idx], y[test_idx]


@dataclass
class RSMDataset:
    """Immutable domain container for Response Surface Methodology datasets."""
    X_train: np.ndarray
    y_train: np.ndarray
    X_test: np.ndarray = field(default_factory=lambda: np.empty((0, 0), dtype=float))
    y_test: np.ndarray = field(default_factory=lambda: np.empty((0,), dtype=float))
    feature_names: List[str] = field(default_factory=list)
    target_name: str = "y"
    split_by_groups: bool = False

    def __post_init__(self) -> None:
        self.X_train = np.asarray(self.X_train, dtype=float)
        self.y_train = np.asarray(self.y_train, dtype=float).ravel()
        if self.X_test is not None and len(self.X_test) > 0:
            self.X_test = np.asarray(self.X_test, dtype=float)
            self.y_test = np.asarray(self.y_test, dtype=float).ravel()
        else:
            n_feat = self.X_train.shape[1] if self.X_train.ndim == 2 else 0
            self.X_test = np.empty((0, n_feat), dtype=float)
            self.y_test = np.empty((0,), dtype=float)

        if not self.feature_names:
            n_feat = self.X_train.shape[1] if self.X_train.ndim == 2 else 0
            self.feature_names = [f"x{i + 1}" for i in range(n_feat)]
        else:
            self.feature_names = list(self.feature_names)
        self.validate()

    def validate(self) -> None:
        """Validate dimensions, row counts, feature names, and check for NaNs/Infs."""
        if self.X_train.ndim != 2:
            raise DataValidationError(f"X_train must be a 2D array, got shape {self.X_train.shape}")
        if self.y_train.ndim != 1:
            raise DataValidationError(f"y_train must be a 1D array, got shape {self.y_train.shape}")
        if len(self.X_train) == 0:
            raise DataValidationError("X_train cannot be empty.")
        if len(self.X_train) != len(self.y_train):
            raise DataValidationError(f"Sample count mismatch: X_train has {len(self.X_train)} samples but y_train has {len(self.y_train)} samples.")
        if self.X_train.shape[1] != len(self.feature_names):
            raise DataValidationError(f"Feature count mismatch: X_train has {self.X_train.shape[1]} columns, but feature_names has {len(self.feature_names)} items.")
        if len(set(self.feature_names)) != len(self.feature_names):
            raise DataValidationError(f"Duplicate feature names detected: {self.feature_names}")
        if np.isnan(self.X_train).any() or np.isnan(self.y_train).any():
            raise DataValidationError("X_train or y_train contains NaN values.")
        if np.isinf(self.X_train).any() or np.isinf(self.y_train).any():
            raise DataValidationError("X_train or y_train contains Inf values.")

        if len(self.X_test) > 0:
            if self.X_test.ndim != 2 or self.y_test.ndim != 1:
                raise DataValidationError("X_test must be 2D and y_test must be 1D.")
            if len(self.X_test) != len(self.y_test):
                raise DataValidationError(f"Sample count mismatch: X_test has {len(self.X_test)} samples but y_test has {len(self.y_test)} samples.")
            if self.X_test.shape[1] != self.X_train.shape[1]:
                raise DataValidationError(f"Feature dimension mismatch: X_test has {self.X_test.shape[1]} columns, expected {self.X_train.shape[1]}.")
            if np.isnan(self.X_test).any() or np.isnan(self.y_test).any():
                raise DataValidationError("X_test or y_test contains NaN values.")
            if np.isinf(self.X_test).any() or np.isinf(self.y_test).any():
                raise DataValidationError("X_test or y_test contains Inf values.")

    @classmethod
    def from_dataframe(
        cls,
        df: pd.DataFrame,
        input_columns: Sequence[str],
        output_column: str,
        test_size: float = 0.2,
        random_state: Optional[int] = 42,
        shuffle: bool = True,
        split_by_groups: bool = False,
    ) -> "RSMDataset":
        """Construct RSMDataset directly from a pandas DataFrame."""
        if not isinstance(df, pd.DataFrame):
            raise DataValidationError(f"Expected pandas DataFrame, got {type(df).__name__}")
        if df.empty:
            raise DataValidationError("Input DataFrame cannot be empty.")
        if not input_columns:
            raise DataValidationError("input_columns cannot be empty.")

        missing_inputs = [c for c in input_columns if c not in df.columns]
        if missing_inputs:
            raise DataValidationError(f"Missing input columns in DataFrame: {missing_inputs}")
        if output_column not in df.columns:
            raise DataValidationError(f"Missing output column in DataFrame: '{output_column}'")
        if output_column in input_columns:
            raise DataValidationError(f"Output column '{output_column}' cannot be in input_columns.")

        X = df[list(input_columns)].to_numpy(dtype=float)
        y = df[output_column].to_numpy(dtype=float).ravel()
        X_tr, X_te, y_tr, y_te = _split_arrays(X, y, test_size, random_state, shuffle, split_by_groups)

        return cls(
            X_train=X_tr,
            y_train=y_tr,
            X_test=X_te,
            y_test=y_te,
            feature_names=list(input_columns),
            target_name=str(output_column),
            split_by_groups=bool(split_by_groups),
        )

    @classmethod
    def from_arrays(
        cls,
        X_train: ArrayLike,
        y_train: ArrayLike,
        X_test: Optional[ArrayLike] = None,
        y_test: Optional[ArrayLike] = None,
        feature_names: Optional[Sequence[str]] = None,
        target_name: str = "y",
    ) -> "RSMDataset":
        """Construct RSMDataset from pre-split arrays."""
        X_tr = np.asarray(X_train, dtype=float)
        y_tr = np.asarray(y_train, dtype=float).ravel()
        n_feat = X_tr.shape[1] if X_tr.ndim == 2 else 0
        X_te = np.asarray(X_test, dtype=float) if (X_test is not None and len(X_test) > 0) else np.empty((0, n_feat), dtype=float)
        y_te = np.asarray(y_test, dtype=float).ravel() if (y_test is not None and len(y_test) > 0) else np.empty((0,), dtype=float)
        names = list(feature_names) if feature_names is not None else [f"x{i + 1}" for i in range(n_feat)]
        return cls(X_train=X_tr, y_train=y_tr, X_test=X_te, y_test=y_te, feature_names=names, target_name=target_name)

    @classmethod
    def from_unsplit_arrays(
        cls,
        X: ArrayLike,
        y: ArrayLike,
        test_size: float = 0.2,
        random_state: Optional[int] = 42,
        shuffle: bool = True,
        feature_names: Optional[Sequence[str]] = None,
        target_name: str = "y",
        split_by_groups: bool = False,
    ) -> "RSMDataset":
        """Construct RSMDataset from unsplit arrays with automated splitting."""
        X_arr = np.asarray(X, dtype=float)
        y_arr = np.asarray(y, dtype=float).ravel()
        X_tr, X_te, y_tr, y_te = _split_arrays(X_arr, y_arr, test_size, random_state, shuffle, split_by_groups)
        names = list(feature_names) if feature_names is not None else [f"x{i + 1}" for i in range(X_arr.shape[1])]
        return cls(
            X_train=X_tr,
            y_train=y_tr,
            X_test=X_te,
            y_test=y_te,
            feature_names=names,
            target_name=target_name,
            split_by_groups=bool(split_by_groups),
        )

    @property
    def num_train(self) -> int: return len(self.X_train)
    @property
    def n_train(self) -> int: return len(self.X_train)
    @property
    def num_test(self) -> int: return len(self.X_test)
    @property
    def n_test(self) -> int: return len(self.X_test)
    @property
    def num_total(self) -> int: return len(self.X_train) + len(self.X_test)
    @property
    def n_total(self) -> int: return len(self.X_train) + len(self.X_test)
    @property
    def num_features(self) -> int: return self.X_train.shape[1]
    @property
    def n_features(self) -> int: return self.X_train.shape[1]
    @property
    def has_test_set(self) -> bool: return len(self.X_test) > 0
    @property
    def n_unique_train(self) -> int: return compute_input_groups(self.X_train)[1]
    @property
    def n_unique_test(self) -> int: return compute_input_groups(self.X_test)[1] if self.has_test_set else 0
    @property
    def n_unique_total(self) -> int: return compute_input_groups(self.X_all)[1]
    @property
    def has_train_replicates(self) -> bool: return self.n_train > self.n_unique_train
    @property
    def X_all(self) -> np.ndarray: return np.vstack([self.X_train, self.X_test]) if self.has_test_set else self.X_train
    @property
    def y_all(self) -> np.ndarray: return np.concatenate([self.y_train, self.y_test]) if self.has_test_set else self.y_train

    @property
    def bounds(self) -> Dict[str, Tuple[float, float]]:
        comb = self.X_all
        return {name: (float(np.min(comb[:, i])), float(np.max(comb[:, i]))) for i, name in enumerate(self.feature_names)}

    def summary_stats(self) -> Dict[str, Any]:
        """Compute descriptive summary statistics across all data."""
        comb_X = self.X_all
        stats: Dict[str, Any] = {
            "num_features": self.num_features,
            "num_train_samples": self.num_train,
            "num_test_samples": self.num_test,
            "feature_ranges": self.bounds,
        }
        for i, name in enumerate(self.feature_names):
            col = comb_X[:, i]
            stats[name] = {
                "min": float(np.min(col)), "max": float(np.max(col)), "mean": float(np.mean(col)),
                "std": float(np.std(col, ddof=1)) if len(col) > 1 else 0.0, "median": float(np.median(col)),
                "q25": float(np.percentile(col, 25)), "q75": float(np.percentile(col, 75)),
            }
        comb_y = self.y_all
        stats[self.target_name] = {
            "min": float(np.min(comb_y)), "max": float(np.max(comb_y)), "mean": float(np.mean(comb_y)),
            "std": float(np.std(comb_y, ddof=1)) if len(comb_y) > 1 else 0.0, "median": float(np.median(comb_y)),
            "q25": float(np.percentile(comb_y, 25)), "q75": float(np.percentile(comb_y, 75)),
        }
        return stats


def build_data(df: pd.DataFrame, input_columns: Sequence[str], output_column: str) -> Tuple[np.ndarray, np.ndarray]:
    """Legacy helper extracting input (X) and target (y) numpy arrays from a DataFrame."""
    if not isinstance(df, pd.DataFrame):
        raise DataValidationError(f"Expected pandas DataFrame, got {type(df).__name__}")
    missing_inputs = [c for c in input_columns if c not in df.columns]
    if missing_inputs:
        raise DataValidationError(f"Missing input columns in DataFrame: {missing_inputs}")
    if output_column not in df.columns:
        raise DataValidationError(f"Missing output column in DataFrame: '{output_column}'")
    X = df[list(input_columns)].to_numpy(dtype=float)
    y = df[output_column].to_numpy(dtype=float).ravel()
    return X, y
