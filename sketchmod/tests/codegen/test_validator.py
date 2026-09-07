"""
Comprehensive tests for GraphValidator.
Covers every error and warning condition.
"""

import unittest
from copy import deepcopy
from sketchmod.codegen.validator import GraphValidator


class ValidatorTest(unittest.TestCase):
    # ----------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------
    @staticmethod
    def _base():
        """
        Well‑formed graph with NO errors.
        inp_out carries all three phases, so it can seed training & evaluation.
        """
        return {
            "nodes": [
                {
                    "id": "inp",
                    "type": "input-data",
                    "x": 0,
                    "y": 0,
                    "inputPorts": [],
                    "outputPorts": [
                        {
                            "id": "inp_out",
                            "type": "output",
                            "index": 0,
                            "subType": None,
                            "shape": None,
                            "bias": 0,
                            "portKind": "data",
                            "activationPhases": [
                                "preprocessing",
                                "training",
                                "evaluation",
                            ],
                        }
                    ],
                    "numInputs": 0,
                    "numOutputs": 1,
                    "bias": 0,
                    "hasBias": False,
                    "paramInputs": [],
                    "paramOutputs": [],
                    "numParamInputs": 0,
                    "numParamOutputs": 0,
                    "dataShape": "(100, 5)",
                },
                {
                    "id": "out",
                    "type": "output",
                    "x": 300,
                    "y": 0,
                    "inputPorts": [
                        {
                            "id": "out_in_train",
                            "type": "input",
                            "index": 0,
                            "subType": "train",
                            "shape": None,
                            "bias": 0,
                            "portKind": "data",
                            "activationPhases": ["training"],
                        },
                        {
                            "id": "out_in_test",
                            "type": "input",
                            "index": 1,
                            "subType": "test",
                            "shape": None,
                            "bias": 0,
                            "portKind": "data",
                            "activationPhases": ["evaluation"],
                        },
                    ],
                    "outputPorts": [
                        {
                            "id": "loss_p",
                            "type": "output",
                            "index": 0,
                            "subType": None,
                            "shape": None,
                            "bias": 0,
                            "portKind": "role",
                            "activationPhases": ["training"],
                            "role": "loss",
                        },
                        {
                            "id": "pred_p",
                            "type": "output",
                            "index": 1,
                            "subType": None,
                            "shape": None,
                            "bias": 0,
                            "portKind": "role",
                            "activationPhases": ["evaluation"],
                            "role": "prediction",
                        },
                        {
                            "id": "eval_p",
                            "type": "output",
                            "index": 2,
                            "subType": None,
                            "shape": None,
                            "bias": 0,
                            "portKind": "role",
                            "activationPhases": ["evaluation"],
                            "role": "evaluation",
                        },
                    ],
                    "numInputs": 2,
                    "numOutputs": 3,
                    "bias": 0,
                    "hasBias": False,
                    "paramInputs": [],
                    "paramOutputs": [],
                    "numParamInputs": 0,
                    "numParamOutputs": 0,
                },
                {
                    "id": "layer",
                    "type": "layer",
                    "x": 200,
                    "y": 0,
                    "inputPorts": [
                        {
                            "id": "layer_in",
                            "type": "input",
                            "index": 0,
                            "subType": None,
                            "shape": None,
                            "bias": 0,
                            "portKind": "multi",
                            "activationPhases": ["training", "evaluation"],
                        }
                    ],
                    "outputPorts": [
                        {
                            "id": "layer_out",
                            "type": "output",
                            "index": 0,
                            "subType": None,
                            "shape": None,
                            "bias": 0,
                            "portKind": "data",
                            "activationPhases": ["training", "evaluation"],
                        }
                    ],
                    "numInputs": 1,
                    "numOutputs": 1,
                    "activation": "relu",
                    "numNeurons": 16,
                    "bias": 0,
                    "hasBias": True,
                    "paramInputs": [],
                    "paramOutputs": [],
                    "numParamInputs": 0,
                    "numParamOutputs": 0,
                },
                {
                    "id": "opt",
                    "type": "optimizer",
                    "x": 400,
                    "y": 0,
                    "inputPorts": [
                        {
                            "id": "opt_loss",
                            "type": "input",
                            "index": 0,
                            "subType": None,
                            "shape": None,
                            "bias": 0,
                            "portKind": "role",
                            "activationPhases": ["training"],
                            "role": "loss",
                        },
                        {
                            "id": "opt_labels",
                            "type": "input",
                            "index": 1,
                            "subType": None,
                            "shape": None,
                            "bias": 0,
                            "portKind": "role",
                            "activationPhases": ["training"],
                            "role": "labels",
                        },
                    ],
                    "outputPorts": [],
                    "numInputs": 2,
                    "numOutputs": 0,
                    "bias": 0,
                    "hasBias": False,
                    "paramInputs": [],
                    "paramOutputs": [],
                    "numParamInputs": 0,
                    "numParamOutputs": 0,
                    "lossType": "mse",
                    "optimizerType": "adam",
                    "learningRate": 0.01,
                    "epochs": 5,
                    "batchSize": 16,
                    "shuffle": False,
                },
            ],
            "links": [
                {
                    "from": "inp_out",
                    "to": "layer_in",
                    "weight": 1,
                    "weightShape": {"shape": [16, "?"], "dtype": "float32"},
                    "hasWeight": True,
                },
                {"from": "inp_out", "to": "opt_labels", "weight": 1},
                {"from": "layer_out", "to": "out_in_train", "weight": 1},
                {"from": "layer_out", "to": "out_in_test", "weight": 1},
                {"from": "loss_p", "to": "opt_loss", "weight": 1},
            ],
            "ports": [],
            "nodeCounter": 0,
        }

    def _assert_has_message(self, collection, substring, msg=None):
        for item in collection:
            if substring in item.get("message", ""):
                return
        self.fail(msg or f"No message containing '{substring}' found in {collection}")

    def _assert_has_code(self, collection, code, msg=None):
        """Prefer this over message matching: codes are the stable contract."""
        found = {item.get("code") for item in collection}
        if code not in found:
            self.fail(msg or f"No diagnostic with code '{code}' in {sorted(found)}")

    # ----------------------------------------------------------------
    # ERRORS
    # ----------------------------------------------------------------
    def test_missing_input_data_error(self):
        g = self._base()
        g["nodes"] = [n for n in g["nodes"] if n["id"] != "inp"]
        g["links"] = [l for l in g["links"] if "inp_out" not in (l["from"], l["to"])]
        r = GraphValidator(g).validate()
        self._assert_has_message(r["errors"], "Missing Input Data node")
        self.assertFalse(r["isValid"])

    def test_missing_output_error(self):
        g = self._base()
        g["nodes"] = [n for n in g["nodes"] if n["id"] != "out"]
        out_ports = {"out_in_train", "out_in_test", "loss_p", "pred_p", "eval_p"}
        g["links"] = [
            l
            for l in g["links"]
            if l["from"] not in out_ports and l["to"] not in out_ports
        ]
        r = GraphValidator(g).validate()
        self._assert_has_message(r["errors"], "Missing Output node")
        self.assertFalse(r["isValid"])

    def test_optimizer_wrong_phase_error(self):
        g = deepcopy(self._base())
        opt = next(n for n in g["nodes"] if n["type"] == "optimizer")
        opt["inputPorts"][0]["activationPhases"] = ["preprocessing"]
        opt["inputPorts"][1]["activationPhases"] = ["preprocessing"]
        r = GraphValidator(g).validate()
        self._assert_has_code(r["errors"], "optimizer-not-training")
        self.assertFalse(r["isValid"])

    def test_param_port_cycle_error(self):
        g = deepcopy(self._base())
        n1 = {
            "id": "n1",
            "type": "normalize",
            "x": 100,
            "y": 100,
            "inputPorts": [
                {
                    "id": "n1_in",
                    "type": "input",
                    "index": 0,
                    "subType": None,
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["preprocessing"],
                }
            ],
            "outputPorts": [
                {
                    "id": "n1_out",
                    "type": "output",
                    "index": 0,
                    "subType": None,
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["preprocessing"],
                }
            ],
            "paramInputs": [
                {
                    "id": "n1_pin",
                    "type": "input",
                    "index": 0,
                    "portKind": "param",
                    "activationPhases": ["preprocessing"],
                }
            ],
            "paramOutputs": [
                {
                    "id": "n1_pout",
                    "type": "output",
                    "index": 0,
                    "portKind": "param",
                    "activationPhases": ["preprocessing"],
                }
            ],
            "numInputs": 1,
            "numOutputs": 1,
            "numParamInputs": 1,
            "numParamOutputs": 1,
            "bias": 0,
            "hasBias": False,
            "method": "standard",
        }
        n2 = {
            "id": "n2",
            "type": "normalize",
            "x": 200,
            "y": 100,
            "inputPorts": [
                {
                    "id": "n2_in",
                    "type": "input",
                    "index": 0,
                    "subType": None,
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["preprocessing"],
                }
            ],
            "outputPorts": [
                {
                    "id": "n2_out",
                    "type": "output",
                    "index": 0,
                    "subType": None,
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["preprocessing"],
                }
            ],
            "paramInputs": [
                {
                    "id": "n2_pin",
                    "type": "input",
                    "index": 0,
                    "portKind": "param",
                    "activationPhases": ["preprocessing"],
                }
            ],
            "paramOutputs": [
                {
                    "id": "n2_pout",
                    "type": "output",
                    "index": 0,
                    "portKind": "param",
                    "activationPhases": ["preprocessing"],
                }
            ],
            "numInputs": 1,
            "numOutputs": 1,
            "numParamInputs": 1,
            "numParamOutputs": 1,
            "bias": 0,
            "hasBias": False,
            "method": "standard",
        }
        g["nodes"].extend([n1, n2])
        g["links"].extend(
            [
                {"from": "inp_out", "to": "n1_in", "weight": 1},
                {"from": "n1_out", "to": "n2_in", "weight": 1},
                {"from": "n1_pout", "to": "n2_pin", "weight": 1},
                {"from": "n2_pout", "to": "n1_pin", "weight": 1},
            ]
        )
        r = GraphValidator(g).validate()
        self._assert_has_code(r["errors"], "param-cycle")
        self.assertFalse(r["isValid"])

    def test_layer_no_input_error(self):
        g = deepcopy(self._base())
        g["links"] = [l for l in g["links"] if l["to"] != "layer_in"]
        r = GraphValidator(g).validate()
        self._assert_has_message(r["errors"], "requires at least 1 input connection")
        self.assertFalse(r["isValid"])

    def test_add_wrong_input_count_error(self):
        g = deepcopy(self._base())
        add = {
            "id": "add",
            "type": "add",
            "x": 200,
            "y": 200,
            "inputPorts": [
                {
                    "id": "add_in",
                    "type": "input",
                    "index": 0,
                    "subType": "main",
                    "shape": None,
                    "bias": 0,
                    "portKind": "multi",
                    "activationPhases": ["training"],
                }
            ],
            "outputPorts": [
                {
                    "id": "add_out",
                    "type": "output",
                    "index": 0,
                    "subType": None,
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["training"],
                }
            ],
            "numInputs": 1,
            "numOutputs": 1,
            "bias": 0,
            "hasBias": False,
            "paramInputs": [],
            "paramOutputs": [],
            "numParamInputs": 0,
            "numParamOutputs": 0,
        }
        g["nodes"].append(add)
        g["links"].append({"from": "layer_out", "to": "add_in", "weight": 1})
        r = GraphValidator(g).validate()
        self._assert_has_message(
            r["errors"], "Add node 'add' requires exactly 2 inputs"
        )
        self.assertFalse(r["isValid"])

    def test_concat_insufficient_inputs_error(self):
        g = deepcopy(self._base())
        concat = {
            "id": "concat",
            "type": "concat",
            "x": 200,
            "y": 200,
            "inputPorts": [
                {
                    "id": "concat_in",
                    "type": "input",
                    "index": 0,
                    "subType": None,
                    "shape": None,
                    "bias": 0,
                    "portKind": "multi",
                    "activationPhases": ["training"],
                }
            ],
            "outputPorts": [
                {
                    "id": "concat_out",
                    "type": "output",
                    "index": 0,
                    "subType": None,
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["training"],
                }
            ],
            "numInputs": 1,
            "numOutputs": 1,
            "axis": -1,
            "bias": 0,
            "hasBias": False,
            "paramInputs": [],
            "paramOutputs": [],
            "numParamInputs": 0,
            "numParamOutputs": 0,
        }
        g["nodes"].append(concat)
        g["links"].append({"from": "layer_out", "to": "concat_in", "weight": 1})
        r = GraphValidator(g).validate()
        self._assert_has_message(
            r["errors"], "Concat node 'concat' requires at least 2 inputs"
        )
        self.assertFalse(r["isValid"])

    # ----------------------------------------------------------------
    # WARNINGS
    # ----------------------------------------------------------------
    def test_optimizer_missing_warning(self):
        g = deepcopy(self._base())
        g["nodes"] = [n for n in g["nodes"] if n["type"] != "optimizer"]
        g["links"] = [
            l
            for l in g["links"]
            if "opt_loss" not in (l["from"], l["to"])
            and "opt_labels" not in (l["from"], l["to"])
        ]
        r = GraphValidator(g).validate()
        self._assert_has_message(r["warnings"], "No optimizer node")
        self.assertTrue(r["isValid"])

    def test_model_in_preprocessing_warning(self):
        g = deepcopy(self._base())
        layer = next(n for n in g["nodes"] if n["type"] == "layer")
        layer["inputPorts"][0]["activationPhases"] = ["preprocessing"]
        layer["outputPorts"][0]["activationPhases"] = ["preprocessing"]
        r = GraphValidator(g).validate()
        self._assert_has_code(r["warnings"], "untrained-layer")
        self._assert_has_message(r["warnings"], "runs in preprocessing")

    def test_model_eval_without_train_warning(self):
        g = deepcopy(self._base())
        layer = next(n for n in g["nodes"] if n["type"] == "layer")
        # Put the layer only in evaluation – training will still be present for
        # the optimizer (inp_out has all phases, so opt_labels gets a training seed).
        layer["inputPorts"][0]["activationPhases"] = ["evaluation"]
        layer["outputPorts"][0]["activationPhases"] = ["evaluation"]
        r = GraphValidator(g).validate()
        self._assert_has_code(r["warnings"], "untrained-layer")
        self._assert_has_message(r["warnings"], "runs in evaluation")

    def test_visualization_in_training_warning(self):
        g = deepcopy(self._base())
        viz = {
            "id": "viz",
            "type": "visualization",
            "x": 500,
            "y": 500,
            "inputPorts": [
                {
                    "id": "viz_x",
                    "type": "input",
                    "index": 0,
                    "subType": "coord",
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["training"],
                },
                {
                    "id": "viz_y",
                    "type": "input",
                    "index": 1,
                    "subType": "coord",
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["training"],
                },
            ],
            "outputPorts": [],
            "numInputs": 2,
            "numOutputs": 0,
            "bias": 0,
            "hasBias": False,
            "paramInputs": [],
            "paramOutputs": [],
            "numParamInputs": 0,
            "numParamOutputs": 0,
            "colorMode": "none",
        }
        g["nodes"].append(viz)
        g["links"].append({"from": "layer_out", "to": "viz_x", "weight": 1})
        g["links"].append({"from": "layer_out", "to": "viz_y", "weight": 1})
        r = GraphValidator(g).validate()
        self._assert_has_message(
            r["warnings"],
            "Visualization 'viz' is in the training phase and will be skipped",
        )

    def test_preprocessing_only_warning(self):
        g = deepcopy(self._base())
        # Remove optimizer entirely, then remove training/eval from all ports
        # so that only preprocessing remains.
        g["nodes"] = [n for n in g["nodes"] if n["type"] != "optimizer"]
        g["links"] = [
            l
            for l in g["links"]
            if "opt_loss" not in (l["from"], l["to"])
            and "opt_labels" not in (l["from"], l["to"])
        ]
        layer = next(n for n in g["nodes"] if n["type"] == "layer")
        layer["inputPorts"][0]["activationPhases"] = ["preprocessing"]
        layer["outputPorts"][0]["activationPhases"] = ["preprocessing"]
        inp_out = g["nodes"][0]["outputPorts"][0]
        inp_out["activationPhases"] = ["preprocessing"]
        r = GraphValidator(g).validate()
        self._assert_has_message(
            r["warnings"], "Preprocessing does not reach training or evaluation"
        )

    def test_onehot_crossentropy_warning(self):
        g = deepcopy(self._base())
        opt = next(n for n in g["nodes"] if n["type"] == "optimizer")
        opt["lossType"] = "cross_entropy"
        oh = {
            "id": "oh",
            "type": "onehot",
            "x": 100,
            "y": 200,
            "inputPorts": [
                {
                    "id": "oh_in",
                    "type": "input",
                    "index": 0,
                    "subType": None,
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["preprocessing"],
                }
            ],
            "outputPorts": [
                {
                    "id": "oh_out",
                    "type": "output",
                    "index": 0,
                    "subType": None,
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["preprocessing", "training"],
                }
            ],
            "numInputs": 1,
            "numOutputs": 1,
            "numClasses": 5,
            "bias": 0,
            "hasBias": False,
            "paramInputs": [],
            "paramOutputs": [],
            "numParamInputs": 0,
            "numParamOutputs": 0,
        }
        g["nodes"].append(oh)
        g["links"].append({"from": "inp_out", "to": "oh_in", "weight": 1})
        g["links"] = [l for l in g["links"] if l["to"] != "opt_labels"]
        g["links"].append({"from": "oh_out", "to": "opt_labels", "weight": 1})
        r = GraphValidator(g).validate()
        self._assert_has_message(
            r["warnings"],
            "CrossEntropyLoss expects class indices, but labels come from a OneHot node",
        )

    def test_bce_without_onehot_warning(self):
        g = deepcopy(self._base())
        opt = next(n for n in g["nodes"] if n["type"] == "optimizer")
        opt["lossType"] = "bce"
        r = GraphValidator(g).validate()
        self._assert_has_code(r["warnings"], "label-loss-mismatch")
        self._assert_has_message(r["warnings"], "BCEWithLogitsLoss expects one-hot")

    def test_accuracy_missing_inputs_warning(self):
        g = deepcopy(self._base())
        acc = {
            "id": "acc",
            "type": "accuracy",
            "x": 500,
            "y": 500,
            "inputPorts": [
                {
                    "id": "acc_pred",
                    "type": "input",
                    "index": 0,
                    "subType": "predictions",
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["evaluation"],
                },
                {
                    "id": "acc_label",
                    "type": "input",
                    "index": 1,
                    "subType": "labels",
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["evaluation"],
                },
            ],
            "outputPorts": [],
            "numInputs": 2,
            "numOutputs": 0,
            "bias": 0,
            "hasBias": False,
            "paramInputs": [],
            "paramOutputs": [],
            "numParamInputs": 0,
            "numParamOutputs": 0,
            "showConfusion": False,
        }
        g["nodes"].append(acc)
        g["links"].append({"from": "pred_p", "to": "acc_pred", "weight": 1})
        r = GraphValidator(g).validate()
        self._assert_has_message(r["warnings"], "Accuracy node 'acc' expects 2 inputs")

    def test_visualization_shape_mismatch_warning(self):
        g = self._base()
        # Create two branches with different sample sizes:
        # inp -> layer (100,) -> output -> prediction port
        # inp -> column-select (80,) -> output -> evaluation port
        # Change inp data shape to produce 100 rows, then add a train-test split?
        # Simpler: manually adjust the layer output shape? No, we need a natural mismatch.
        # We'll add a train-test split that gives different sizes.
        split = {
            "id": "split",
            "type": "train-test",
            "x": 100,
            "y": 50,
            "inputPorts": [
                {
                    "id": "split_in",
                    "type": "input",
                    "index": 0,
                    "subType": None,
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["preprocessing"],
                }
            ],
            "outputPorts": [
                {
                    "id": "split_train",
                    "type": "output",
                    "index": 0,
                    "subType": "train",
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["preprocessing", "evaluation"],
                },
                {
                    "id": "split_test",
                    "type": "output",
                    "index": 1,
                    "subType": "test",
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["preprocessing", "evaluation"],
                },
            ],
            "numInputs": 1,
            "numOutputs": 2,
            "bias": 0,
            "hasBias": False,
            "trainRatio": 0.7,
            "randomSeed": 42,
        }
        # Use column-selects to extract a single column for each coord
        col1 = {
            "id": "col1",
            "type": "column-select",
            "x": 200,
            "y": 80,
            "inputPorts": [
                {
                    "id": "col1_in",
                    "type": "input",
                    "index": 0,
                    "subType": None,
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["evaluation"],
                }
            ],
            "outputPorts": [
                {
                    "id": "col1_out",
                    "type": "output",
                    "index": 0,
                    "subType": None,
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["evaluation"],
                }
            ],
            "numInputs": 1,
            "numOutputs": 1,
            "selectedColumns": [0],
        }
        col2 = {
            "id": "col2",
            "type": "column-select",
            "x": 200,
            "y": 120,
            "inputPorts": [
                {
                    "id": "col2_in",
                    "type": "input",
                    "index": 0,
                    "subType": None,
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["evaluation"],
                }
            ],
            "outputPorts": [
                {
                    "id": "col2_out",
                    "type": "output",
                    "index": 0,
                    "subType": None,
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["evaluation"],
                }
            ],
            "numInputs": 1,
            "numOutputs": 1,
            "selectedColumns": [0],
        }
        viz = {
            "id": "viz",
            "type": "visualization",
            "x": 500,
            "y": 500,
            "inputPorts": [
                {
                    "id": "viz_x",
                    "type": "input",
                    "index": 0,
                    "subType": "coord",
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["evaluation"],
                },
                {
                    "id": "viz_y",
                    "type": "input",
                    "index": 1,
                    "subType": "coord",
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["evaluation"],
                },
            ],
            "outputPorts": [],
            "numInputs": 2,
            "numOutputs": 0,
            "bias": 0,
            "hasBias": False,
            "colorMode": "none",
        }
        g["nodes"].extend([split, col1, col2, viz])
        # Remove old connections to layer; plug split between inp and layer
        g["links"] = [
            l for l in g["links"] if l["from"] != "inp_out" and l["to"] != "layer_in"
        ]
        g["links"].extend(
            [
                {"from": "inp_out", "to": "split_in", "weight": 1},
                {"from": "split_train", "to": "col1_in", "weight": 1},
                {"from": "split_test", "to": "col2_in", "weight": 1},
                {"from": "col1_out", "to": "viz_x", "weight": 1},
                {"from": "col2_out", "to": "viz_y", "weight": 1},
            ]
        )
        r = GraphValidator(g).validate()
        self._assert_has_message(r["warnings"], "different sample sizes")

    def test_accuracy_label_onehot_warning(self):
        g = deepcopy(self._base())
        # Add a column-select to extract a single column for the onehot input
        col = {
            "id": "col_labels",
            "type": "column-select",
            "x": 100,
            "y": 200,
            "inputPorts": [
                {
                    "id": "col_labels_in",
                    "type": "input",
                    "index": 0,
                    "subType": None,
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["preprocessing"],
                }
            ],
            "outputPorts": [
                {
                    "id": "col_labels_out",
                    "type": "output",
                    "index": 0,
                    "subType": None,
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["preprocessing", "evaluation"],
                }
            ],
            "numInputs": 1,
            "numOutputs": 1,
            "selectedColumns": [0],
        }
        oh = {
            "id": "oh",
            "type": "onehot",
            "x": 150,
            "y": 250,
            "inputPorts": [
                {
                    "id": "oh_in",
                    "type": "input",
                    "index": 0,
                    "subType": None,
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["preprocessing"],
                }
            ],
            "outputPorts": [
                {
                    "id": "oh_out",
                    "type": "output",
                    "index": 0,
                    "subType": None,
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["preprocessing", "evaluation"],
                }
            ],
            "numInputs": 1,
            "numOutputs": 1,
            "numClasses": 5,
            "bias": 0,
            "hasBias": False,
            "paramInputs": [],
            "paramOutputs": [],
        }
        acc = {
            "id": "acc",
            "type": "accuracy",
            "x": 500,
            "y": 500,
            "inputPorts": [
                {
                    "id": "acc_pred",
                    "type": "input",
                    "index": 0,
                    "subType": "predictions",
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["evaluation"],
                },
                {
                    "id": "acc_label",
                    "type": "input",
                    "index": 1,
                    "subType": "labels",
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["evaluation"],
                },
            ],
            "outputPorts": [],
            "numInputs": 2,
            "numOutputs": 0,
            "bias": 0,
            "hasBias": False,
            "showConfusion": False,
        }
        g["nodes"].extend([col, oh, acc])
        g["links"].append({"from": "inp_out", "to": "col_labels_in", "weight": 1})
        g["links"].append({"from": "col_labels_out", "to": "oh_in", "weight": 1})
        g["links"].append({"from": "oh_out", "to": "acc_label", "weight": 1})
        g["links"].append({"from": "pred_p", "to": "acc_pred", "weight": 1})
        r = GraphValidator(g).validate()
        self._assert_has_code(r["warnings"], "accuracy-label-reshape")
        self._assert_has_message(r["warnings"], "appears to be one-hot encoded")

    def test_accuracy_label_squeeze_warning(self):
        g = deepcopy(self._base())
        # Add a column-select that extracts a single column (shape N,1)
        col = {
            "id": "col",
            "type": "column-select",
            "x": 100,
            "y": 200,
            "inputPorts": [
                {
                    "id": "col_in",
                    "type": "input",
                    "index": 0,
                    "subType": None,
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["preprocessing"],
                }
            ],
            "outputPorts": [
                {
                    "id": "col_out",
                    "type": "output",
                    "index": 0,
                    "subType": None,
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["preprocessing", "evaluation"],
                }
            ],
            "numInputs": 1,
            "numOutputs": 1,
            "selectedColumns": [0],
        }
        acc = {
            "id": "acc",
            "type": "accuracy",
            "x": 500,
            "y": 500,
            "inputPorts": [
                {
                    "id": "acc_pred",
                    "type": "input",
                    "index": 0,
                    "subType": "predictions",
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["evaluation"],
                },
                {
                    "id": "acc_label",
                    "type": "input",
                    "index": 1,
                    "subType": "labels",
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["evaluation"],
                },
            ],
            "outputPorts": [],
            "numInputs": 2,
            "numOutputs": 0,
            "bias": 0,
            "hasBias": False,
            "showConfusion": False,
        }
        g["nodes"].extend([col, acc])
        g["links"].append({"from": "inp_out", "to": "col_in", "weight": 1})
        g["links"].append({"from": "col_out", "to": "acc_label", "weight": 1})
        g["links"].append({"from": "pred_p", "to": "acc_pred", "weight": 1})
        r = GraphValidator(g).validate()
        self._assert_has_message(r["warnings"], "automatically squeezed to (N)")

    def test_no_errors_valid_graph(self):
        g = self._base()
        r = GraphValidator(g).validate()
        self.assertEqual(len(r["errors"]), 0, msg=f"Unexpected errors: {r['errors']}")
        self.assertTrue(r["isValid"])

    def test_cross_entropy_without_input_shape_does_not_warn_label_unknown(self):
        """Missing Input Data shape already warns; do not duplicate on Optimizer."""
        g = deepcopy(self._base())
        for node in g["nodes"]:
            if node["type"] == "input-data":
                node["dataShape"] = None
                node["datasetId"] = None
            if node["type"] == "optimizer":
                node["lossType"] = "cross_entropy"
        r = GraphValidator(g).validate()
        self._assert_has_code(r["warnings"], "missing-dataset")
        codes = {w.get("code") for w in r["warnings"]}
        self.assertNotIn("label-shape-unknown", codes)

    def test_reshape_infeasible_warning(self):
        g = deepcopy(self._base())
        reshape = {
            "id": "r",
            "type": "reshape",
            "x": 200,
            "y": 200,
            "targetShape": "(10, 10)",
            "inputPorts": [
                {
                    "id": "r_in",
                    "type": "input",
                    "index": 0,
                    "activationPhases": ["preprocessing"],
                    "portKind": "data",
                }
            ],
            "outputPorts": [
                {
                    "id": "r_out",
                    "type": "output",
                    "index": 0,
                    "activationPhases": ["preprocessing"],
                    "portKind": "data",
                }
            ],
        }
        g["nodes"].append(reshape)
        g["links"].append({"from": "inp_out", "to": "r_in", "weight": 1})
        r = GraphValidator(g).validate()
        self._assert_has_message(r["warnings"], "total elements mismatch")


if __name__ == "__main__":
    unittest.main()
