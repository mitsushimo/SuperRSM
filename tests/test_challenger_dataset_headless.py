"""
tests/test_challenger_dataset_headless.py

Adversarial Challenger Test Suite for SuperRSM Milestone M2:
- Adversarial Dataset Validation (NaNs, Infs, shape/count mismatches, empty/1-row inputs)
- Headless execution isolation in clean subprocesses (zero tkinter, matplotlib, seaborn)
- Dynamic visualization dependency check in RSMResult.visualize_rsm()
- Multithreaded concurrent pipeline fitting across models and pipelines
- String / non-numeric input exception characterization
"""

import concurrent.futures
import subprocess
import sys
import numpy as np
import pandas as pd
import pytest

from super_rsm.common.exceptions import (
    DataValidationError,
    ModelFitError,
)
from super_rsm.core import (
    RSMDataset,
    RSMResult,
    fit_rsm,
    fit_rsm2,
    rsm_fromDF,
)


# -----------------------------------------------------------------------------
# 1. Adversarial Dataset Validation: NaNs, Infs, Shapes, and Counts
# -----------------------------------------------------------------------------

def test_adversarial_nan_and_inf_handling():
    """Verify all NaN and Inf configurations raise DataValidationError cleanly."""
    valid_x = np.array([[1.0, 2.0], [3.0, 4.0]])
    valid_y = np.array([10.0, 20.0])

    # 1. NaN in X_train (all-NaN column, single NaN, NaN in y)
    with pytest.raises(DataValidationError, match="contains NaN values"):
        RSMDataset(X_train=np.array([[np.nan, 2.0], [np.nan, 4.0]]), y_train=valid_y)
    with pytest.raises(DataValidationError, match="contains NaN values"):
        RSMDataset(X_train=np.array([[1.0, np.nan], [3.0, 4.0]]), y_train=valid_y)
    with pytest.raises(DataValidationError, match="contains NaN values"):
        RSMDataset(X_train=valid_x, y_train=np.array([np.nan, 20.0]))

    # 2. Inf / -Inf in X_train and y_train
    with pytest.raises(DataValidationError, match="contains Inf values"):
        RSMDataset(X_train=np.array([[np.inf, 2.0], [3.0, 4.0]]), y_train=valid_y)
    with pytest.raises(DataValidationError, match="contains Inf values"):
        RSMDataset(X_train=np.array([[-np.inf, 2.0], [3.0, 4.0]]), y_train=valid_y)
    with pytest.raises(DataValidationError, match="contains Inf values"):
        RSMDataset(X_train=valid_x, y_train=np.array([10.0, -np.inf]))

    # 3. NaN and Inf in X_test and y_test
    with pytest.raises(DataValidationError, match="contains NaN values"):
        RSMDataset(X_train=valid_x, y_train=valid_y, X_test=np.array([[np.nan, 1.0]]), y_test=np.array([1.0]))
    with pytest.raises(DataValidationError, match="contains Inf values"):
        RSMDataset(X_train=valid_x, y_train=valid_y, X_test=np.array([[1.0, 1.0]]), y_test=np.array([np.inf]))


def test_adversarial_shapes_counts_and_duplicates():
    """Verify dimensionality violations, count mismatches, and duplicate names."""
    valid_x = np.array([[1.0, 2.0], [3.0, 4.0]])
    valid_y = np.array([10.0, 20.0])

    # 1. 1D and 3D X_train
    with pytest.raises(DataValidationError, match="must be a 2D array"):
        RSMDataset(X_train=np.array([1.0, 2.0]), y_train=valid_y)
    with pytest.raises(DataValidationError, match="must be a 2D array"):
        RSMDataset(X_train=np.ones((2, 2, 2)), y_train=valid_y)

    # 2. Sample count mismatch between X and y
    with pytest.raises(DataValidationError, match="Sample count mismatch"):
        RSMDataset(X_train=np.ones((5, 2)), y_train=np.ones(4))
    with pytest.raises(DataValidationError, match="Sample count mismatch"):
        RSMDataset(X_train=valid_x, y_train=valid_y, X_test=np.ones((3, 2)), y_test=np.ones(2))

    # 3. Feature dimension mismatch between train and test
    with pytest.raises(DataValidationError, match="Feature dimension mismatch"):
        RSMDataset(X_train=valid_x, y_train=valid_y, X_test=np.ones((2, 3)), y_test=valid_y)

    # 4. Duplicate feature names
    with pytest.raises(DataValidationError, match="Duplicate feature names"):
        RSMDataset(X_train=valid_x, y_train=valid_y, feature_names=["x1", "x1"])


def test_adversarial_empty_inputs_and_edge_cases():
    """Verify behavior on zero-row inputs, non-existent columns, and target collisions."""
    # 1. Completely empty DataFrame and zero-row DataFrame
    with pytest.raises(DataValidationError, match="Input DataFrame cannot be empty"):
        RSMDataset.from_dataframe(pd.DataFrame(), ["x1"], "y")
    with pytest.raises(DataValidationError, match="Input DataFrame cannot be empty"):
        RSMDataset.from_dataframe(pd.DataFrame(columns=["x1", "y"]), ["x1"], "y")

    # 2. Empty input_columns
    df = pd.DataFrame({"x1": [1.0, 2.0], "y": [3.0, 4.0]})
    with pytest.raises(DataValidationError, match="input_columns cannot be empty"):
        RSMDataset.from_dataframe(df, [], "y")

    # 3. Target column collision with input columns
    with pytest.raises(DataValidationError, match="cannot be in input_columns"):
        RSMDataset.from_dataframe(df, ["x1", "y"], "y")

    # 4. Empty X_train in array constructor
    with pytest.raises(DataValidationError, match="cannot be empty"):
        RSMDataset(X_train=np.empty((0, 2)), y_train=np.empty(0))


def test_single_sample_and_unbalanced_datasets():
    """Verify 1-row datasets split gracefully and raise ModelFitError cleanly when fit."""
    df_single = pd.DataFrame({"x1": [1.0], "x2": [2.0], "y": [5.0]})
    ds = RSMDataset.from_dataframe(df_single, ["x1", "x2"], "y", test_size=0.2)
    assert ds.num_train == 1 and ds.num_test == 0

    stats = ds.summary_stats()
    assert stats["num_train_samples"] == 1
    assert stats["x1"]["std"] == 0.0

    # Fitting with 1 sample on Polynomial OLS (degree 2 -> P=6) should raise ModelFitError
    with pytest.raises(ModelFitError, match="must exceed number of polynomial terms"):
        fit_rsm(ds, method="Polynomial OLS", degree_fit=2)


def test_string_inputs_in_numeric_columns():
    """Characterize exception type when non-numeric strings are supplied."""
    df_str = pd.DataFrame({"x1": ["non_numeric", "data"], "y": [1.0, 2.0]})
    # Currently numpy to_numpy(dtype=float) raises ValueError; ensure an exception is raised
    with pytest.raises((DataValidationError, ValueError)):
        RSMDataset.from_dataframe(df_str, ["x1"], "y")


# -----------------------------------------------------------------------------
# 2. Headless Isolation Verification in Independent Subprocesses
# -----------------------------------------------------------------------------

def test_headless_subprocess_clean_import():
    """Verify that importing super_rsm.core in a clean process loads ZERO GUI modules."""
    script = (
        "import sys\n"
        "import super_rsm.core\n"
        "forbidden = ['tkinter', 'matplotlib', 'seaborn', 'matplotlib.pyplot', 'high_d_plotter']\n"
        "leaked = [m for m in forbidden if m in sys.modules]\n"
        "if leaked:\n"
        "    print(f'LEAK:{leaked}')\n"
        "    sys.exit(1)\n"
        "print('CLEAN')\n"
    )
    proc = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    assert proc.returncode == 0, f"Subprocess failed: {proc.stderr}"
    assert "CLEAN" in proc.stdout


def test_headless_subprocess_pipeline_and_opt_execution():
    """Verify fitting, evaluating, and optimizing in a subprocess never imports GUI modules."""
    script = (
        "import sys\n"
        "import numpy as np\n"
        "import super_rsm.core as core\n"
        "np.random.seed(42)\n"
        "X = np.random.uniform(-1, 1, size=(25, 2))\n"
        "y = 2.0 + 1.5 * X[:, 0] - 0.5 * X[:, 1]\n"
        "res = core.fit_rsm2(X, y, method='Polynomial OLS', degree=1)\n"
        "p, v = res.optimize()\n"
        "forbidden = ['tkinter', 'matplotlib', 'seaborn', 'high_d_plotter']\n"
        "leaked = [m for m in forbidden if m in sys.modules]\n"
        "if leaked:\n"
        "    print(f'LEAK:{leaked}')\n"
        "    sys.exit(1)\n"
        "print('HEADLESS_PIPELINE_OK')\n"
    )
    proc = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    assert proc.returncode == 0, f"Subprocess failed: {proc.stderr}"
    assert "HEADLESS_PIPELINE_OK" in proc.stdout


def test_visualize_rsm_graceful_import_error(monkeypatch):
    """Verify visualize_rsm raises informative ImportError when visualization service is missing."""
    import sys
    monkeypatch.setitem(sys.modules, "super_rsm.visualization.service", None)
    X = np.random.uniform(-1, 1, size=(20, 2))
    y = 2.0 + X[:, 0]
    res = fit_rsm2(X, y, method="Polynomial OLS", degree=1)
    with pytest.raises(ImportError, match="Visualization subsystem not available"):
        res.visualize_rsm(config=None)


# -----------------------------------------------------------------------------
# 3. Multithreaded Concurrent Pipeline Fitting
# -----------------------------------------------------------------------------

def _fit_task(task_id: int):
    """Worker task executing pipeline training and optimization concurrently."""
    np.random.seed(200 + task_id)
    X = np.random.uniform(-2, 2, size=(30, 2))
    y = 1.5 + 2.0 * X[:, 0] - 1.0 * X[:, 1] + 0.5 * (X[:, 0] ** 2)
    df = pd.DataFrame(X, columns=["x1", "x2"])
    df["resp"] = y

    if task_id % 3 == 0:
        res = fit_rsm2(X, y, method="Polynomial OLS", degree=2, test_size=0.2)
    elif task_id % 3 == 1:
        res = fit_rsm2(X, y, method="RidgeCV", degree_fit=2, feature_names=["x1", "x2"], test_size=0.2)
    else:
        res = rsm_fromDF(df, ["x1", "x2"], "resp", method="Gaussian Process", degree_fit=0, test_size=0.2)

    val = res.evaluate_point([0.2, 0.4])
    opt = res.optimize(bounds={"x1": (-1.0, 1.0), "x2": (-1.0, 1.0)})
    return task_id, res.r2, opt.fun


def test_concurrent_multithreaded_pipeline_fits():
    """Verify simultaneous fitting across 12 concurrent worker threads without race conditions."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(_fit_task, i) for i in range(12)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert len(results) == 12
    for task_id, r2, opt_fun in results:
        assert isinstance(r2, float) and not np.isnan(r2)
        assert isinstance(opt_fun, float) and not np.isnan(opt_fun)
