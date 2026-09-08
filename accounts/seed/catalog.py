"""Starter catalog: sklearn datasets and the model that consumes each of them."""

from __future__ import annotations

import numpy as np
import pandas as pd

STARTER_USERNAME = "SketchNet"
STARTER_EMAIL = "sketchnet@example.com"
STARTER_BIO = (
    "Official starter models and classic datasets for learning on SketchNet."
)

EXPECTED_DATASET_COUNT = 10
EXPECTED_MODEL_COUNT = 7

# Rows × columns including the trailing `target` column.
EXPECTED_DATASET_SHAPES = {
    "Iris": (150, 5),
    "Wine": (178, 14),
    "Breast Cancer": (569, 31),
    "Diabetes": (442, 11),
    "Digits": (1797, 65),
    "Moons": (400, 3),
    "Circles": (400, 3),
    "Blobs": (400, 3),
    "Two-class": (400, 9),
    "Friedman 1": (400, 11),
}

# Occupies model54.JSON … in sketchmod/tests/codegen/test_models.py.
STARTER_MODEL_BASE = 54


def dataset_slug(name: str) -> str:
    return name.lower().replace(" ", "_").replace("-", "_")


def write_starter_datasets(directory) -> dict:
    """Write each catalog table as `{slug}.csv` under directory."""
    from pathlib import Path

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    written = {}
    for spec in DATASETS:
        path = directory / f"{dataset_slug(spec['name'])}.csv"
        spec["loader"]().to_csv(path, index=False)
        written[spec["name"]] = path
    return written


def build_catalog_graph(model_name: str, dataset_name: str, frame) -> dict:
    """Wire a catalog model to a table so codegen can load `data/{slug}.csv`."""
    from types import SimpleNamespace

    from accounts.seed.graphs import attach_dataset

    n_features = max(int(frame.shape[1]) - 1, 0)
    n_classes = 1
    if "target" in frame.columns:
        unique = frame["target"].nunique()
        n_classes = int(unique) if unique else 1
    graph = build_model_graph(model_name, n_features, n_classes)
    slug = dataset_slug(dataset_name)
    return attach_dataset(
        graph,
        SimpleNamespace(
            dataset_id=slug,
            name=dataset_name,
            resolved_shape=f"({len(frame)}, {frame.shape[1]})",
            dataset_file=f"{slug}.csv",
            format="csv",
        ),
    )


def _table(X, y, feature_names) -> pd.DataFrame:
    names = [str(name).replace(" ", "_") for name in feature_names]
    frame = pd.DataFrame(np.asarray(X), columns=names)
    frame["target"] = np.asarray(y)
    return frame


def load_iris_df() -> pd.DataFrame:
    from sklearn.datasets import load_iris

    bunch = load_iris()
    return _table(bunch.data, bunch.target, bunch.feature_names)


def load_wine_df() -> pd.DataFrame:
    from sklearn.datasets import load_wine

    bunch = load_wine()
    return _table(bunch.data, bunch.target, bunch.feature_names)


def load_breast_cancer_df() -> pd.DataFrame:
    from sklearn.datasets import load_breast_cancer

    bunch = load_breast_cancer()
    return _table(bunch.data, bunch.target, bunch.feature_names)


def load_diabetes_df() -> pd.DataFrame:
    from sklearn.datasets import load_diabetes

    bunch = load_diabetes()
    return _table(bunch.data, bunch.target, bunch.feature_names)


def load_digits_df() -> pd.DataFrame:
    from sklearn.datasets import load_digits

    bunch = load_digits()
    names = [f"pixel_{i}" for i in range(bunch.data.shape[1])]
    return _table(bunch.data, bunch.target, names)


def load_moons_df() -> pd.DataFrame:
    from sklearn.datasets import make_moons

    X, y = make_moons(n_samples=400, noise=0.15, random_state=42)
    return _table(X, y, ["x", "y"])


def load_circles_df() -> pd.DataFrame:
    from sklearn.datasets import make_circles

    X, y = make_circles(n_samples=400, noise=0.08, factor=0.5, random_state=42)
    return _table(X, y, ["x", "y"])


def load_blobs_df() -> pd.DataFrame:
    from sklearn.datasets import make_blobs

    X, y = make_blobs(n_samples=400, centers=3, n_features=2, random_state=42)
    return _table(X, y, ["x", "y"])


def load_two_class_df() -> pd.DataFrame:
    from sklearn.datasets import make_classification

    X, y = make_classification(
        n_samples=400,
        n_features=8,
        n_informative=4,
        n_redundant=2,
        n_classes=2,
        random_state=42,
    )
    return _table(X, y, [f"feature_{i}" for i in range(X.shape[1])])


def load_friedman1_df() -> pd.DataFrame:
    from sklearn.datasets import make_friedman1

    X, y = make_friedman1(n_samples=400, n_features=10, noise=1.0, random_state=42)
    return _table(X, y, [f"feature_{i}" for i in range(X.shape[1])])


DATASETS = [
    {
        "name": "Iris",
        "description": (
            "UCI Iris: 150 flowers, four measurements, three species. "
            "Classic multiclass classification."
        ),
        "loader": load_iris_df,
    },
    {
        "name": "Wine",
        "description": (
            "UCI Wine: 13 chemical features, three cultivars. "
            "Multiclass classification."
        ),
        "loader": load_wine_df,
    },
    {
        "name": "Breast Cancer",
        "description": (
            "Wisconsin diagnostic breast cancer: 30 cell-nucleus features, "
            "benign vs malignant."
        ),
        "loader": load_breast_cancer_df,
    },
    {
        "name": "Diabetes",
        "description": (
            "sklearn diabetes: 442 patients, 10 baseline features, "
            "quantitative disease progression."
        ),
        "loader": load_diabetes_df,
    },
    {
        "name": "Digits",
        "description": (
            "8×8 handwritten digits (1,797 samples, 10 classes). "
            "Small image-classification stand-in for MNIST."
        ),
        "loader": load_digits_df,
    },
    {
        "name": "Moons",
        "description": (
            "Two interlocking half-circles. Nonlinear binary classification toy."
        ),
        "loader": load_moons_df,
    },
    {
        "name": "Circles",
        "description": (
            "Concentric circles. Nonlinear binary classification toy."
        ),
        "loader": load_circles_df,
    },
    {
        "name": "Blobs",
        "description": (
            "Three isotropic Gaussian blobs with cluster labels. "
            "Simple clustering / multiclass toy."
        ),
        "loader": load_blobs_df,
    },
    {
        "name": "Two-class",
        "description": (
            "sklearn make_classification: 400 samples, eight mixed features, "
            "two linearly separable-ish classes."
        ),
        "loader": load_two_class_df,
    },
    {
        "name": "Friedman 1",
        "description": (
            "Friedman #1 benchmark: nonlinear regression of ten features "
            "with additive noise."
        ),
        "loader": load_friedman1_df,
    },
]


def build_model_graph(name: str, n_features: int, n_classes: int) -> dict:
    """Return the catalog graph for a named starter model."""
    from accounts.seed.graphs import (
        digits_cnn,
        layout_graph,
        linear_classifier,
        linear_regressor,
        mlp_classifier,
        mlp_regressor,
        skip_classifier,
    )

    builders = {
        "Linear Regression": lambda: linear_regressor(n_features),
        "Binary Classifier": lambda: linear_classifier(n_features, n_classes),
        "Iris MLP": lambda: mlp_classifier(n_features, n_classes, hidden=16),
        "Digits CNN": digits_cnn,
        "Skip Connection": lambda: skip_classifier(n_features, n_classes),
        "Two-class Linear": lambda: linear_classifier(n_features, n_classes),
        "Friedman MLP": lambda: mlp_regressor(n_features, hidden=32),
    }
    try:
        graph = builders[name]()
    except KeyError as exc:
        raise ValueError(f"Unknown starter model '{name}'") from exc
    return layout_graph(graph)


MODELS = [
    {
        "name": "Linear Regression",
        "dataset": "Diabetes",
        "description": (
            "Single linear layer trained with MSE on the Diabetes features."
        ),
    },
    {
        "name": "Binary Classifier",
        "dataset": "Breast Cancer",
        "description": (
            "Linear two-class head with softmax, cross-entropy, and accuracy "
            "on Wisconsin breast cancer."
        ),
    },
    {
        "name": "Iris MLP",
        "dataset": "Iris",
        "description": (
            "Small ReLU MLP for three-class Iris species prediction."
        ),
    },
    {
        "name": "Digits CNN",
        "dataset": "Digits",
        "description": (
            "Conv2D on 8×8 digit images (reshape 64 pixels to 1×8×8), "
            "ten-class output."
        ),
    },
    {
        "name": "Skip Connection",
        "dataset": "Wine",
        "description": (
            "Residual add around a hidden layer, then a three-class Wine head."
        ),
    },
    {
        "name": "Two-class Linear",
        "dataset": "Two-class",
        "description": (
            "Linear two-class head with softmax, cross-entropy, and accuracy "
            "on the synthetic two-class table."
        ),
    },
    {
        "name": "Friedman MLP",
        "dataset": "Friedman 1",
        "description": (
            "Hidden ReLU MLP trained with MSE on the Friedman #1 regression "
            "benchmark."
        ),
    },
]
