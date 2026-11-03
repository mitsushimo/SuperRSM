"""
super_rsm/core/persistence.py

Self-contained .rsm project archive serialization and deserialization.
Bundles the full dataset (DataFrame), train/test partition, fitted surrogate model,
optimization bounds/constraints, and evaluation history into a portable .rsm ZIP container.
"""

import io
import json
import logging
from pathlib import Path
import pickle
from typing import Any, Dict, Optional
import zipfile
import numpy as np
import pandas as pd

from super_rsm.core.dataset import RSMDataset
from super_rsm.core.result import RSMResult
from super_rsm.models.registry import ModelRegistry

logger = logging.getLogger(__name__)

RSM_ARCHIVE_VERSION = "1.0"


def save_rsm_project(
    filepath: str,
    df: Optional[pd.DataFrame],
    state_dict: Dict[str, Any],
    result: Optional[RSMResult] = None,
) -> Path:
    """
    Save the complete SuperRSM session into a self-contained .rsm archive.

    Parameters
    ----------
    filepath : str
        Destination path (automatically given .rsm suffix if missing).
    df : Optional[pd.DataFrame]
        Active dataset to embed inside the archive so external CSV/Excel moves/deletions do not break it.
    state_dict : Dict[str, Any]
        JSON-serializable UI and workflow state (columns, method, hyperparameters, bounds, constraints, etc.).
    result : Optional[RSMResult]
        Fitted surrogate model result container, if a model has been fitted.
    """
    target_path = Path(filepath)
    if target_path.suffix.lower() != ".rsm":
        target_path = target_path.with_suffix(".rsm")

    manifest: Dict[str, Any] = {
        "format": "SuperRSM Project Archive",
        "version": RSM_ARCHIVE_VERSION,
        "has_dataset": df is not None,
        "has_result": result is not None,
        "state": state_dict,
    }

    with zipfile.ZipFile(target_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))

        if df is not None:
            csv_buf = io.StringIO()
            df.to_csv(csv_buf, index=False)
            zf.writestr("dataset.csv", csv_buf.getvalue().encode("utf-8"))

        if result is not None:
            ds = getattr(result, "dataset", None)
            if ds is not None:
                npz_buf = io.BytesIO()
                np.savez_compressed(
                    npz_buf,
                    X_train=ds.X_train,
                    y_train=ds.y_train,
                    X_test=ds.X_test,
                    y_test=ds.y_test,
                )
                zf.writestr("dataset_split.npz", npz_buf.getvalue())

            try:
                pkl_bytes = pickle.dumps(result, protocol=pickle.HIGHEST_PROTOCOL)
                zf.writestr("model_state.pkl", pkl_bytes)
            except Exception as exc:
                logger.warning("Could not pickle RSMResult directly (%s); relying on split + hyperparameters.", exc)

    return target_path


def load_rsm_project(filepath: str) -> Dict[str, Any]:
    """
    Load a self-contained .rsm project archive from disk.

    Returns a dictionary with keys:
      - 'version': str
      - 'df': Optional[pd.DataFrame]
      - 'result': Optional[RSMResult]
      - 'state': Dict[str, Any]
    """
    source_path = Path(filepath)
    if not source_path.exists():
        raise FileNotFoundError(f"Project file not found: {source_path}")
    if not zipfile.is_zipfile(source_path):
        raise ValueError(f"Invalid .rsm project file (not a valid archive): {source_path}")

    with zipfile.ZipFile(source_path, mode="r") as zf:
        names = set(zf.namelist())
        if "manifest.json" not in names:
            raise ValueError("Corrupted .rsm project file: missing 'manifest.json'.")

        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        state_dict: Dict[str, Any] = manifest.get("state", {})

        df: Optional[pd.DataFrame] = None
        if "dataset.csv" in names:
            csv_bytes = zf.read("dataset.csv")
            df = pd.read_csv(io.BytesIO(csv_bytes))

        result: Optional[RSMResult] = None
        if manifest.get("has_result", False):
            if "model_state.pkl" in names:
                try:
                    result = pickle.loads(zf.read("model_state.pkl"))
                except Exception as exc:
                    logger.warning("Pickle load failed (%s); reconstructing model from embedded split.", exc)
                    result = None

            if result is None and "dataset_split.npz" in names:
                result = _reconstruct_result_from_split(zf.read("dataset_split.npz"), state_dict)

    return {
        "version": manifest.get("version", RSM_ARCHIVE_VERSION),
        "df": df,
        "result": result,
        "state": state_dict,
    }


def _reconstruct_result_from_split(npz_bytes: bytes, state_dict: Dict[str, Any]) -> Optional[RSMResult]:
    """Fallback reconstruction of RSMResult from saved train/test arrays and hyperparameters."""
    try:
        with np.load(io.BytesIO(npz_bytes)) as data:
            X_train = data["X_train"]
            y_train = data["y_train"]
            X_test = data["X_test"]
            y_test = data["y_test"]

        input_cols = state_dict.get("input_cols", [])
        output_col = state_dict.get("output_col", "y")
        method = state_dict.get("method", "Gaussian Process")
        hparams = state_dict.get("hyperparameters", {})
        split_by_groups = bool(state_dict.get("split_by_groups", False))

        ds = RSMDataset(
            X_train=X_train,
            y_train=y_train,
            X_test=X_test,
            y_test=y_test,
            feature_names=input_cols,
            target_name=output_col,
            split_by_groups=split_by_groups,
        )
        model = ModelRegistry.create(method, **hparams)
        model.fit(ds.X_train, ds.y_train, feature_names=ds.feature_names)
        return RSMResult(model=model, dataset=ds, method=method)
    except Exception as exc:
        logger.error("Fallback model reconstruction failed: %s", exc)
        return None

