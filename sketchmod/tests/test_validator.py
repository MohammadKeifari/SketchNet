from django.test import SimpleTestCase
from sketchmod.codegen.validator import GraphValidator


class ValidatorBasicTests(SimpleTestCase):
    """Basic validation checks."""

    def _make_graph(self, nodes, links, ports):
        return {"nodes": nodes, "links": links, "ports": ports}

    def _validate(self, nodes, links, ports=None):
        if ports is None:
            ports = []
            for n in nodes:
                for p in n.get("inputPorts", []):
                    ports.append(p)
                for p in n.get("outputPorts", []):
                    ports.append(p)
        graph = self._make_graph(nodes, links, ports)
        validator = GraphValidator(graph)
        return validator.validate()

    # ========== EMPTY GRAPH ==========

    def test_empty_graph_no_output(self):
        result = self._validate([], [], [])
        # Empty graph should warn about no output
        self.assertTrue(len(result["errors"]) > 0 or len(result["warnings"]) > 0)

    # ========== INPUT DATA CONNECTIVITY ==========

    def test_inputdata_no_outgoing_warns(self):
        nodes = [
            {
                "id": "i1",
                "type": "input-data",
                "inputPorts": [],
                "outputPorts": [
                    {
                        "id": "i1_output_0",
                        "type": "output",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "portKind": "data",
                    }
                ],
            },
            {
                "id": "o1",
                "type": "output",
                "inputPorts": [
                    {
                        "id": "o1_input_0",
                        "type": "input",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "portKind": "data",
                    }
                ],
                "outputPorts": [],
            },
        ]
        links = []
        result = self._validate(nodes, links)
        warnings = [w["message"] for w in result["warnings"]]
        self.assertIn("InputData: no outgoing connections", warnings)

    # ========== OUTPUT CONNECTIVITY ==========

    def test_output_no_input_errors(self):
        nodes = [
            {
                "id": "i1",
                "type": "input-data",
                "inputPorts": [],
                "outputPorts": [
                    {
                        "id": "i1_output_0",
                        "type": "output",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "portKind": "data",
                    }
                ],
            },
            {
                "id": "o1",
                "type": "output",
                "inputPorts": [
                    {
                        "id": "o1_input_0",
                        "type": "input",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "portKind": "data",
                    }
                ],
                "outputPorts": [],
            },
        ]
        links = [
            {
                "from": "i1_output_0",
                "to": "o1_input_0",
                "weight": 0,
                "weightShape": None,
                "hasWeight": False,
            },
        ]
        result = self._validate(nodes, links)
        self.assertFalse(result["errors"])  # Connected properly

    def test_output_disconnected_errors(self):
        nodes = [
            {
                "id": "i1",
                "type": "input-data",
                "inputPorts": [],
                "outputPorts": [
                    {
                        "id": "i1_output_0",
                        "type": "output",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "portKind": "data",
                    }
                ],
            },
            {
                "id": "o1",
                "type": "output",
                "inputPorts": [
                    {
                        "id": "o1_input_0",
                        "type": "input",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "portKind": "data",
                    }
                ],
                "outputPorts": [],
            },
        ]
        links = []  # Nothing connected
        result = self._validate(nodes, links)
        errors = [e["message"] for e in result["errors"]]
        self.assertTrue(any("not connected" in e for e in errors))

    # ========== CONNECTION COUNT CHECKS ==========

    def test_layer_requires_input(self):
        nodes = [
            {
                "id": "l1",
                "type": "layer",
                "inputPorts": [
                    {
                        "id": "l1_input_0",
                        "type": "input",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "portKind": "multi",
                    }
                ],
                "outputPorts": [
                    {
                        "id": "l1_output_0",
                        "type": "output",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "portKind": "data",
                    }
                ],
                "numNeurons": 64,
                "activation": "relu",
            },
        ]
        links = []
        result = self._validate(nodes, links)
        errors = [e["message"] for e in result["errors"]]
        self.assertTrue(any("requires at least 1" in e for e in errors))

    def test_add_requires_two_inputs(self):
        nodes = [
            {
                "id": "a1",
                "type": "add",
                "inputPorts": [
                    {
                        "id": "a1_input_0",
                        "type": "input",
                        "index": 0,
                        "subType": "main",
                        "shape": None,
                        "portKind": "multi",
                    }
                ],
                "outputPorts": [
                    {
                        "id": "a1_output_0",
                        "type": "output",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "portKind": "data",
                    }
                ],
            },
        ]
        links = []
        result = self._validate(nodes, links)
        errors = [e["message"] for e in result["errors"]]
        self.assertTrue(any("requires at least 2" in e for e in errors))

    def test_concat_requires_two_inputs(self):
        nodes = [
            {
                "id": "c1",
                "type": "concat",
                "inputPorts": [
                    {
                        "id": "c1_input_0",
                        "type": "input",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "portKind": "multi",
                    }
                ],
                "outputPorts": [
                    {
                        "id": "c1_output_0",
                        "type": "output",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "portKind": "data",
                    }
                ],
                "axis": -1,
            },
        ]
        links = []
        result = self._validate(nodes, links)
        errors = [e["message"] for e in result["errors"]]
        self.assertTrue(any("requires at least 2" in e for e in errors))

    def test_optimizer_requires_two_inputs(self):
        nodes = [
            {
                "id": "opt1",
                "type": "optimizer",
                "inputPorts": [
                    {
                        "id": "opt1_input_0",
                        "type": "input",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "portKind": "role",
                        "role": "loss",
                    },
                    {
                        "id": "opt1_input_1",
                        "type": "input",
                        "index": 1,
                        "subType": None,
                        "shape": None,
                        "portKind": "role",
                        "role": "labels",
                    },
                ],
                "outputPorts": [],
                "lossType": "cross_entropy",
                "optimizerType": "adam",
                "learningRate": 0.001,
                "epochs": 10,
                "batchSize": 32,
            },
        ]
        links = []
        result = self._validate(nodes, links)
        errors = [e["message"] for e in result["errors"]]
        self.assertTrue(any("requires 2 input" in e for e in errors))

    # ========== OPTIMIZER CONFIG CHECKS ==========

    def test_optimizer_negative_lr(self):
        nodes = [
            {
                "id": "opt1",
                "type": "optimizer",
                "inputPorts": [
                    {
                        "id": "opt1_input_0",
                        "type": "input",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "portKind": "role",
                        "role": "loss",
                    },
                    {
                        "id": "opt1_input_1",
                        "type": "input",
                        "index": 1,
                        "subType": None,
                        "shape": None,
                        "portKind": "role",
                        "role": "labels",
                    },
                ],
                "outputPorts": [],
                "lossType": "cross_entropy",
                "optimizerType": "adam",
                "learningRate": -0.1,
                "epochs": 10,
                "batchSize": 32,
            },
        ]
        result = self._validate(nodes, [])
        errors = [e["message"] for e in result["errors"]]
        self.assertTrue(any("learning rate" in e.lower() for e in errors))

    def test_optimizer_zero_epochs(self):
        nodes = [
            {
                "id": "opt1",
                "type": "optimizer",
                "inputPorts": [
                    {
                        "id": "opt1_input_0",
                        "type": "input",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "portKind": "role",
                        "role": "loss",
                    },
                    {
                        "id": "opt1_input_1",
                        "type": "input",
                        "index": 1,
                        "subType": None,
                        "shape": None,
                        "portKind": "role",
                        "role": "labels",
                    },
                ],
                "outputPorts": [],
                "lossType": "cross_entropy",
                "optimizerType": "adam",
                "learningRate": 0.001,
                "epochs": 0,
                "batchSize": 32,
            },
        ]
        result = self._validate(nodes, [])
        errors = [e["message"] for e in result["errors"]]
        self.assertTrue(any("epochs" in e.lower() for e in errors))

    def test_optimizer_early_stopping_bad_patience(self):
        nodes = [
            {
                "id": "opt1",
                "type": "optimizer",
                "inputPorts": [
                    {
                        "id": "opt1_input_0",
                        "type": "input",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "portKind": "role",
                        "role": "loss",
                    },
                    {
                        "id": "opt1_input_1",
                        "type": "input",
                        "index": 1,
                        "subType": None,
                        "shape": None,
                        "portKind": "role",
                        "role": "labels",
                    },
                ],
                "outputPorts": [],
                "lossType": "cross_entropy",
                "optimizerType": "adam",
                "learningRate": 0.001,
                "epochs": 10,
                "batchSize": 32,
                "earlyStopping": True,
                "earlyStoppingPatience": 0,
            },
        ]
        result = self._validate(nodes, [])
        errors = [e["message"] for e in result["errors"]]
        self.assertTrue(any("patience" in e.lower() for e in errors))

    # ========== CYCLE DETECTION ==========

    def test_simple_cycle_detected(self):
        nodes = [
            {
                "id": "l1",
                "type": "layer",
                "inputPorts": [
                    {
                        "id": "l1_input_0",
                        "type": "input",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "portKind": "multi",
                    }
                ],
                "outputPorts": [
                    {
                        "id": "l1_output_0",
                        "type": "output",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "portKind": "data",
                    }
                ],
                "numNeurons": 64,
                "activation": "relu",
            },
            {
                "id": "l2",
                "type": "layer",
                "inputPorts": [
                    {
                        "id": "l2_input_0",
                        "type": "input",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "portKind": "multi",
                    }
                ],
                "outputPorts": [
                    {
                        "id": "l2_output_0",
                        "type": "output",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "portKind": "data",
                    }
                ],
                "numNeurons": 32,
                "activation": "relu",
            },
        ]
        links = [
            {
                "from": "l1_output_0",
                "to": "l2_input_0",
                "weight": 0,
                "weightShape": None,
                "hasWeight": True,
            },
            {
                "from": "l2_output_0",
                "to": "l1_input_0",
                "weight": 0,
                "weightShape": None,
                "hasWeight": True,
            },
        ]
        result = self._validate(nodes, links)
        errors = [e["message"] for e in result["errors"]]
        self.assertTrue(any("cycle" in e.lower() for e in errors))

    def test_no_cycle_in_chain(self):
        nodes = [
            {
                "id": "i1",
                "type": "input-data",
                "inputPorts": [],
                "outputPorts": [
                    {
                        "id": "i1_output_0",
                        "type": "output",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "portKind": "data",
                    }
                ],
            },
            {
                "id": "l1",
                "type": "layer",
                "inputPorts": [
                    {
                        "id": "l1_input_0",
                        "type": "input",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "portKind": "multi",
                    }
                ],
                "outputPorts": [
                    {
                        "id": "l1_output_0",
                        "type": "output",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "portKind": "data",
                    }
                ],
                "numNeurons": 64,
                "activation": "relu",
            },
            {
                "id": "o1",
                "type": "output",
                "inputPorts": [
                    {
                        "id": "o1_input_0",
                        "type": "input",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "portKind": "data",
                    }
                ],
                "outputPorts": [],
            },
        ]
        links = [
            {
                "from": "i1_output_0",
                "to": "l1_input_0",
                "weight": 0,
                "weightShape": None,
                "hasWeight": True,
            },
            {
                "from": "l1_output_0",
                "to": "o1_input_0",
                "weight": 0,
                "weightShape": None,
                "hasWeight": False,
            },
        ]
        result = self._validate(nodes, links)
        errors = [e["message"] for e in result["errors"]]
        self.assertFalse(any("cycle" in e.lower() for e in errors))

    # ========== GRAPH CONNECTIVITY ==========

    def test_no_path_to_output_errors(self):
        nodes = [
            {
                "id": "i1",
                "type": "input-data",
                "inputPorts": [],
                "outputPorts": [
                    {
                        "id": "i1_output_0",
                        "type": "output",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "portKind": "data",
                    }
                ],
            },
            {
                "id": "l1",
                "type": "layer",
                "inputPorts": [
                    {
                        "id": "l1_input_0",
                        "type": "input",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "portKind": "multi",
                    }
                ],
                "outputPorts": [
                    {
                        "id": "l1_output_0",
                        "type": "output",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "portKind": "data",
                    }
                ],
                "numNeurons": 64,
                "activation": "relu",
            },
            {
                "id": "o1",
                "type": "output",
                "inputPorts": [
                    {
                        "id": "o1_input_0",
                        "type": "input",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "portKind": "data",
                    }
                ],
                "outputPorts": [],
            },
        ]
        links = [
            {
                "from": "i1_output_0",
                "to": "l1_input_0",
                "weight": 0,
                "weightShape": None,
                "hasWeight": True,
            },
            # Missing: l1 → o1
        ]
        result = self._validate(nodes, links)
        errors = [e["message"] for e in result["errors"]]
        self.assertTrue(
            any("no path" in e.lower() or "path" in e.lower() for e in errors)
        )

    # ========== ORPHAN NODES ==========

    def test_orphan_node_warns(self):
        nodes = [
            {
                "id": "i1",
                "type": "input-data",
                "inputPorts": [],
                "outputPorts": [
                    {
                        "id": "i1_output_0",
                        "type": "output",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "portKind": "data",
                    }
                ],
            },
            {
                "id": "l1",
                "type": "layer",
                "inputPorts": [
                    {
                        "id": "l1_input_0",
                        "type": "input",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "portKind": "multi",
                    }
                ],
                "outputPorts": [
                    {
                        "id": "l1_output_0",
                        "type": "output",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "portKind": "data",
                    }
                ],
                "numNeurons": 64,
                "activation": "relu",
            },
            {
                "id": "l2",
                "type": "layer",  # Orphan — not connected to anything
                "inputPorts": [
                    {
                        "id": "l2_input_0",
                        "type": "input",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "portKind": "multi",
                    }
                ],
                "outputPorts": [
                    {
                        "id": "l2_output_0",
                        "type": "output",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "portKind": "data",
                    }
                ],
                "numNeurons": 32,
                "activation": "relu",
            },
            {
                "id": "o1",
                "type": "output",
                "inputPorts": [
                    {
                        "id": "o1_input_0",
                        "type": "input",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "portKind": "data",
                    }
                ],
                "outputPorts": [],
            },
        ]
        links = [
            {
                "from": "i1_output_0",
                "to": "l1_input_0",
                "weight": 0,
                "weightShape": None,
                "hasWeight": True,
            },
            {
                "from": "l1_output_0",
                "to": "o1_input_0",
                "weight": 0,
                "weightShape": None,
                "hasWeight": False,
            },
        ]
        result = self._validate(nodes, links)
        warnings = [w["message"] for w in result["warnings"]]
        self.assertTrue(any("not connected to anything" in w for w in warnings))

    # ========== NODE CONFIG CHECKS ==========

    def test_dropout_high_rate_warns(self):
        nodes = [
            {
                "id": "d1",
                "type": "dropout",
                "inputPorts": [
                    {
                        "id": "d1_input_0",
                        "type": "input",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "portKind": "data",
                    }
                ],
                "outputPorts": [
                    {
                        "id": "d1_output_0",
                        "type": "output",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "portKind": "data",
                    }
                ],
                "rate": 0.95,
            },
        ]
        result = self._validate(nodes, [])
        warnings = [w["message"] for w in result["warnings"]]
        self.assertTrue(any("rate is very high" in w for w in warnings))

    def test_traintest_bad_ratio_errors(self):
        nodes = [
            {
                "id": "t1",
                "type": "train-test",
                "inputPorts": [
                    {
                        "id": "t1_input_0",
                        "type": "input",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "portKind": "data",
                    }
                ],
                "outputPorts": [
                    {
                        "id": "t1_output_0",
                        "type": "output",
                        "index": 0,
                        "subType": "train",
                        "shape": None,
                        "portKind": "data",
                    },
                    {
                        "id": "t1_output_1",
                        "type": "output",
                        "index": 1,
                        "subType": "test",
                        "shape": None,
                        "portKind": "data",
                    },
                ],
                "trainRatio": 1.5,
                "testRatio": -0.5,
                "randomSeed": 42,
            },
        ]
        result = self._validate(nodes, [])
        errors = [e["message"] for e in result["errors"]]
        self.assertTrue(any("ratio" in e.lower() for e in errors))

    def test_onehot_few_classes_errors(self):
        nodes = [
            {
                "id": "oh1",
                "type": "onehot",
                "inputPorts": [
                    {
                        "id": "oh1_input_0",
                        "type": "input",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "portKind": "data",
                    }
                ],
                "outputPorts": [
                    {
                        "id": "oh1_output_0",
                        "type": "output",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "portKind": "data",
                    }
                ],
                "numClasses": 1,
            },
        ]
        result = self._validate(nodes, [])
        errors = [e["message"] for e in result["errors"]]
        self.assertTrue(any("classes" in e.lower() for e in errors))

    # ========== NO OPTIMIZER WARNING ==========

    def test_no_optimizer_warns(self):
        nodes = [
            {
                "id": "i1",
                "type": "input-data",
                "inputPorts": [],
                "outputPorts": [
                    {
                        "id": "i1_output_0",
                        "type": "output",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "portKind": "data",
                    }
                ],
            },
            {
                "id": "o1",
                "type": "output",
                "inputPorts": [
                    {
                        "id": "o1_input_0",
                        "type": "input",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "portKind": "data",
                    }
                ],
                "outputPorts": [],
            },
        ]
        links = [
            {
                "from": "i1_output_0",
                "to": "o1_input_0",
                "weight": 0,
                "weightShape": None,
                "hasWeight": False,
            },
        ]
        result = self._validate(nodes, links)
        warnings = [w["message"] for w in result["warnings"]]
        self.assertTrue(
            any(
                "no optimizer" in w.lower() or "cannot be trained" in w.lower()
                for w in warnings
            )
        )
