"""Parameterized SketchMod graphs for the SketchNet starter catalog."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from sketchmod.codegen.validator import GraphValidator

TEMPLATES_DIR = (
    Path(__file__).resolve().parents[2]
    / "sketchmod"
    / "static"
    / "sketchmod"
    / "templates"
)

_PREPROCESS = ["preprocessing"]
_ALL_PHASES = ["preprocessing", "training", "evaluation"]


def load_template(slug: str) -> dict:
    """Load a Learn-page graph template by slug."""
    path = TEMPLATES_DIR / f"{slug}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def node_by_id(graph: dict, node_id: str) -> dict:
    """Return the node dict with the given id."""
    for node in graph["nodes"]:
        if node["id"] == node_id:
            return node
    raise KeyError(f"Node '{node_id}' not found")


def attach_dataset(graph: dict, dataset) -> dict:
    """Set Input-node dataset identity from a saved Dataset row or test stand-in."""
    graph = copy.deepcopy(graph)
    filename = getattr(dataset, "dataset_file", None)
    fmt = getattr(dataset, "format", None)
    for node in graph["nodes"]:
        if node.get("type") == "input-data":
            node["datasetId"] = dataset.dataset_id
            node["datasetName"] = dataset.name
            node["dataShape"] = dataset.resolved_shape
            if filename:
                node["datasetFile"] = filename
            if fmt:
                node["datasetFormat"] = fmt
    return graph


def validate_graph(graph: dict) -> list:
    """Return validator error dicts (empty means the graph can generate)."""
    return GraphValidator(graph).validate()["errors"]


def _set_columns(graph: dict, n_features: int) -> None:
    node_by_id(graph, "feat")["selectedColumns"] = list(range(n_features))
    node_by_id(graph, "lab")["selectedColumns"] = [n_features]


def _rewrite_io_ports(node: dict, node_id: str) -> None:
    for port in node.get("inputPorts") or []:
        port["id"] = f"{node_id}_in"
    for port in node.get("outputPorts") or []:
        port["id"] = f"{node_id}_out"


def _replace_link(graph: dict, old_from: str, old_to: str, new_from: str, new_to: str) -> None:
    for link in graph["links"]:
        if link["from"] == old_from and link["to"] == old_to:
            link["from"] = new_from
            link["to"] = new_to
            return
    graph["links"].append({"from": new_from, "to": new_to})


def linear_regressor(n_features: int) -> dict:
    """Single linear unit, MSE — for tabular regression."""
    graph = load_template("linear-regression")
    _set_columns(graph, n_features)
    return graph


def linear_classifier(n_features: int, n_classes: int) -> dict:
    """Linear logits, softmax/argmax, cross-entropy, accuracy."""
    graph = load_template("binary-classification")
    _set_columns(graph, n_features)
    node_by_id(graph, "layer")["numNeurons"] = n_classes
    node_by_id(graph, "layer")["activation"] = "linear"
    return graph


def mlp_regressor(n_features: int, hidden: int = 32) -> dict:
    """Hidden ReLU layer then a single linear output, MSE."""
    graph = linear_regressor(n_features)
    head = node_by_id(graph, "layer")
    hidden_node = copy.deepcopy(head)
    hidden_node["id"] = "hidden"
    hidden_node["x"] = 460
    hidden_node["y"] = 200
    hidden_node["numNeurons"] = hidden
    hidden_node["activation"] = "relu"
    _rewrite_io_ports(hidden_node, "hidden")
    head["x"] = 620
    nodes = graph["nodes"]
    insert_at = next(i for i, n in enumerate(nodes) if n["id"] == "layer")
    nodes.insert(insert_at, hidden_node)
    _replace_link(graph, "feat_out", "layer_in", "feat_out", "hidden_in")
    graph["links"].append({"from": "hidden_out", "to": "layer_in"})
    graph["nodeCounter"] = graph.get("nodeCounter", 0) + 1
    return graph


def mlp_classifier(n_features: int, n_classes: int, hidden: int = 16) -> dict:
    """Hidden ReLU layer then class logits."""
    graph = linear_classifier(n_features, n_classes)
    head = node_by_id(graph, "layer")
    hidden_node = copy.deepcopy(head)
    hidden_node["id"] = "hidden"
    hidden_node["x"] = 460
    hidden_node["y"] = 200
    hidden_node["numNeurons"] = hidden
    hidden_node["activation"] = "relu"
    _rewrite_io_ports(hidden_node, "hidden")
    head["x"] = 620
    nodes = graph["nodes"]
    insert_at = next(i for i, n in enumerate(nodes) if n["id"] == "layer")
    nodes.insert(insert_at, hidden_node)
    _replace_link(graph, "feat_out", "layer_in", "feat_out", "hidden_in")
    graph["links"].append({"from": "hidden_out", "to": "layer_in"})
    graph["nodeCounter"] = graph.get("nodeCounter", 0) + 1
    return graph


def _accuracy_node() -> dict:
    return {
        "id": "acc",
        "type": "accuracy",
        "x": 640,
        "y": 420,
        "showConfusion": False,
        "inputPorts": [
            {
                "id": "acc_pred",
                "type": "input",
                "index": 0,
                "subType": "predictions",
                "activationPhases": ["evaluation"],
            },
            {
                "id": "acc_label",
                "type": "input",
                "index": 1,
                "subType": "labels",
                "activationPhases": ["evaluation"],
            },
        ],
        "outputPorts": [],
        "numInputs": 2,
        "numOutputs": 0,
    }


def _flatten_labels_node() -> dict:
    return {
        "id": "lab_flat",
        "type": "reshape",
        "x": 430,
        "y": 350,
        "targetShape": "(-1,)",
        "inputPorts": [
            {
                "id": "lab_flat_in",
                "type": "input",
                "index": 0,
                "activationPhases": _PREPROCESS,
            }
        ],
        "outputPorts": [
            {
                "id": "lab_flat_out",
                "type": "output",
                "index": 0,
                "activationPhases": _ALL_PHASES,
            }
        ],
        "numInputs": 1,
        "numOutputs": 1,
    }


def skip_classifier(n_features: int, n_classes: int) -> dict:
    """Residual add (hidden dim matches features) then class logits."""
    graph = load_template("skip-connection")
    _set_columns(graph, n_features)
    node_by_id(graph, "hidden")["numNeurons"] = n_features
    node_by_id(graph, "hidden")["activation"] = "relu"
    head = node_by_id(graph, "layer_out")
    head["numNeurons"] = n_classes
    head["activation"] = "linear"
    out = node_by_id(graph, "out")
    out["outputActivations"] = {
        "loss": "none",
        "prediction": "softmax",
        "evaluation": "argmax",
    }
    opt = node_by_id(graph, "opt")
    opt["lossType"] = "cross_entropy"
    graph["nodes"].append(_flatten_labels_node())
    graph["nodes"].append(_accuracy_node())
    graph["links"] = [
        link
        for link in graph["links"]
        if not (link["from"] == "lab_out" and link["to"] == "opt_labels")
    ]
    graph["links"].extend(
        [
            {"from": "lab_out", "to": "lab_flat_in"},
            {"from": "lab_flat_out", "to": "opt_labels"},
            {"from": "lab_flat_out", "to": "acc_label"},
            {"from": "pred_p", "to": "acc_pred"},
        ]
    )
    graph["nodeCounter"] = graph.get("nodeCounter", 0) + 2
    return graph


def digits_cnn() -> dict:
    """8x8 grayscale CNN for sklearn Digits (64 pixels + target)."""
    graph = load_template("cnn")
    _set_columns(graph, 64)
    node_by_id(graph, "reshape")["targetShape"] = "(-1, 1, 8, 8)"
    node_by_id(graph, "layer")["numNeurons"] = 10
    node_by_id(graph, "layer")["activation"] = "linear"
    out = node_by_id(graph, "out")
    out["outputActivations"] = {
        "loss": "none",
        "prediction": "softmax",
        "evaluation": "argmax",
    }
    acc = _accuracy_node()
    acc["x"] = 1060
    acc["y"] = 400
    graph["nodes"].append(acc)
    graph["links"].extend(
        [
            {"from": "lab_flat_out", "to": "acc_label"},
            {"from": "pred_p", "to": "acc_pred"},
        ]
    )
    graph["nodeCounter"] = graph.get("nodeCounter", 0) + 1
    return graph
