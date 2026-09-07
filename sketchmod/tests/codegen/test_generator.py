"""
Unit tests for the main code generator.
Checks that the generated code contains expected patterns.
"""

import json
import re
import unittest

from sketchmod.codegen.generator import CodeGenerator


class GeneratorTest(unittest.TestCase):
    def setUp(self):
        # Minimal classification graph with evaluation path
        self.minimal_graph = {
            "nodes": [
                {
                    "id": "inp",
                    "type": "input-data",
                    "x": 0,
                    "y": 0,
                    "inputPorts": [],
                    "outputPorts": [
                        {
                            "id": "inp_out_0",
                            "type": "output",
                            "index": 0,
                            "subType": None,
                            "shape": None,
                            "bias": 0,
                            "portKind": "data",
                            "activationPhases": ["preprocessing"],
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
                    "datasetId": None,
                    "datasetName": None,
                    "dataShape": "(100, 5)",
                },
                {
                    "id": "split",
                    "type": "train-test",
                    "x": 50,
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
                            "activationPhases": ["preprocessing"],
                        },
                        {
                            "id": "split_test",
                            "type": "output",
                            "index": 1,
                            "subType": "test",
                            "shape": None,
                            "bias": 0,
                            "portKind": "data",
                            "activationPhases": ["preprocessing"],
                        },
                    ],
                    "numInputs": 1,
                    "numOutputs": 2,
                    "bias": 0,
                    "hasBias": False,
                    "paramInputs": [],
                    "paramOutputs": [],
                    "numParamInputs": 0,
                    "numParamOutputs": 0,
                    "trainRatio": 0.7,
                    "testRatio": 0.3,
                    "randomSeed": 42,
                },
                {
                    "id": "feat_col",
                    "type": "column-select",
                    "x": 100,
                    "y": 30,
                    "inputPorts": [
                        {
                            "id": "feat_col_in",
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
                            "id": "feat_col_out",
                            "type": "output",
                            "index": 0,
                            "subType": "features",
                            "shape": None,
                            "bias": 0,
                            "portKind": "data",
                            "activationPhases": ["preprocessing", "training"],
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
                    "selectedColumns": [0, 1, 2],
                    "columnInput": "0:2",
                },
                {
                    "id": "label_col",
                    "type": "column-select",
                    "x": 100,
                    "y": 150,
                    "inputPorts": [
                        {
                            "id": "label_col_in",
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
                            "id": "label_col_out",
                            "type": "output",
                            "index": 0,
                            "subType": "labels",
                            "shape": None,
                            "bias": 0,
                            "portKind": "data",
                            "activationPhases": ["preprocessing", "training"],
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
                    "selectedColumns": [4],
                    "columnInput": "4",
                },
                # ---- Evaluation path: normalize test features ----
                {
                    "id": "norm_test",
                    "type": "normalize",
                    "x": 100,
                    "y": 250,
                    "inputPorts": [
                        {
                            "id": "norm_test_in",
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
                            "id": "norm_test_out",
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
                    "bias": 0,
                    "hasBias": False,
                    "paramInputs": [],
                    "paramOutputs": [],
                    "numParamInputs": 0,
                    "numParamOutputs": 0,
                    "method": "standard",
                },
                {
                    "id": "layer1",
                    "type": "layer",
                    "x": 200,
                    "y": 50,
                    "inputPorts": [
                        {
                            "id": "layer1_in",
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
                            "id": "layer1_out",
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
                    "id": "output",
                    "type": "output",
                    "x": 300,
                    "y": 50,
                    "inputPorts": [
                        {
                            "id": "output_in_train",
                            "type": "input",
                            "index": 0,
                            "subType": "train",
                            "shape": None,
                            "bias": 0,
                            "portKind": "data",
                            "activationPhases": ["training"],
                        },
                        {
                            "id": "output_in_test",
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
                            "id": "loss_port",
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
                            "id": "pred_port",
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
                            "id": "eval_port",
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
                    "outputActivations": {
                        "loss": "none",
                        "prediction": "none",
                        "evaluation": "none",
                    },
                },
                {
                    "id": "opt",
                    "type": "optimizer",
                    "x": 400,
                    "y": 50,
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
                {"from": "inp_out_0", "to": "split_in", "weight": 1},
                # training branch
                {"from": "split_train", "to": "feat_col_in", "weight": 1},
                {"from": "split_train", "to": "label_col_in", "weight": 1},
                {
                    "from": "feat_col_out",
                    "to": "layer1_in",
                    "weight": 1,
                    "weightShape": {"shape": [16, 3], "dtype": "float32"},
                    "hasWeight": True,
                },
                {"from": "layer1_out", "to": "output_in_train", "weight": 1},
                {"from": "loss_port", "to": "opt_loss", "weight": 1},
                {"from": "label_col_out", "to": "opt_labels", "weight": 1},
                # evaluation branch
                {"from": "split_test", "to": "norm_test_in", "weight": 1},
                {
                    "from": "norm_test_out",
                    "to": "layer1_in",
                    "weight": 1,
                    "weightShape": {"shape": [16, 3], "dtype": "float32"},
                    "hasWeight": True,
                },
                {"from": "layer1_out", "to": "output_in_test", "weight": 1},
            ],
            "ports": [],
            "nodeCounter": 0,
        }

    # ---------- helpers ----------
    @staticmethod
    def data_fields(code):
        """Field names of the generated Data NamedTuple."""
        block = code.split("class Data(NamedTuple):")[1].split("\n\n")[0]
        return re.findall(r"^\s+(\w+): torch\.Tensor$", block, re.M)

    @staticmethod
    def forward_body(code):
        return code.split("def forward(")[1].split("\n\n")[0]

    # ---------- basic generation ----------
    def test_generate_minimal_training_script(self):
        code = CodeGenerator(self.minimal_graph).generate()
        self.assertIn("class Model(nn.Module):", code)
        self.assertIn("def train(model: Model, data: Data) -> None:", code)
        self.assertIn("def evaluate(", code)
        self.assertIn("criterion = nn.MSELoss()", code)
        self.assertIn("optimizer = optim.Adam(model.parameters(), lr=0.01)", code)
        self.assertIn("EPOCHS = 5", code)
        self.assertIn("for epoch in range(1, EPOCHS + 1):", code)

    def test_forward_is_static_single_assignment(self):
        """No dictionary plumbing, no runtime guards - one binding per node."""
        body = self.forward_body(CodeGenerator(self.minimal_graph).generate())
        self.assertIn("layer1 = torch.relu(self.layer1(x))", body)
        for pattern in ("outputs[", "inputs_dict", "if ", ".dim()"):
            self.assertNotIn(pattern, body)

    def test_no_optimizer_skips_training(self):
        graph = json.loads(json.dumps(self.minimal_graph))
        # remove optimizer node AND its links
        opt_node_ids = {"opt_loss", "opt_labels"}
        graph["links"] = [
            l
            for l in graph["links"]
            if l["from"] not in opt_node_ids and l["to"] not in opt_node_ids
        ]
        graph["nodes"] = [n for n in graph["nodes"] if n["type"] != "optimizer"]
        code = CodeGenerator(graph).generate()
        self.assertIn("# Training skipped: no optimizer node", code)
        self.assertNotIn("class Model", code)

    def test_evaluation_present(self):
        code = CodeGenerator(self.minimal_graph).generate()
        self.assertIn("def evaluate(model: Model, data: Data) -> None:", code)
        self.assertIn("model.eval()", code)
        self.assertIn("out = model(data.norm_test.to(DEVICE))", code)

    def test_data_carries_only_live_values(self):
        """Exported fields are the ones train/evaluate read, nothing else."""
        code = CodeGenerator(self.minimal_graph).generate()
        self.assertEqual(
            sorted(self.data_fields(code)), ["feat_col", "label_col", "norm_test"]
        )
        # The raw split feeds later preprocessing only, so it stays local.
        self.assertIn("split_train = raw[", code)
        self.assertNotIn("split_train: torch.Tensor", code)

    def test_output_activation_softmax(self):
        graph = json.loads(json.dumps(self.minimal_graph))
        graph["nodes"][6]["outputActivations"] = {
            "prediction": "softmax",
            "loss": "none",
            "evaluation": "none",
        }
        code = CodeGenerator(graph).generate()
        self.assertIn("prediction=torch.softmax(layer1, dim=-1),", code)

    def test_crossentropy_cast_long(self):
        graph = json.loads(json.dumps(self.minimal_graph))
        graph["nodes"][-1]["lossType"] = "cross_entropy"
        code = CodeGenerator(graph).generate()
        self.assertIn("labels = data.label_col.squeeze(-1).long()", code)
        self.assertIn("nn.CrossEntropyLoss()", code)

    def test_visualization_skipped_in_training(self):
        graph = json.loads(json.dumps(self.minimal_graph))
        viz = {
            "id": "viz_train",
            "type": "visualization",
            "x": 500,
            "y": 500,
            "inputPorts": [
                {
                    "id": "viz_in",
                    "type": "input",
                    "index": 0,
                    "subType": "coord",
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["training"],
                }
            ],
            "outputPorts": [],
            "numInputs": 1,
            "numOutputs": 0,
            "bias": 0,
            "hasBias": False,
            "paramInputs": [],
            "paramOutputs": [],
            "numParamInputs": 0,
            "numParamOutputs": 0,
            "colorMode": "none",
        }
        graph["nodes"].append(viz)
        graph["links"].append({"from": "layer1_out", "to": "viz_in", "weight": 1})
        gen = CodeGenerator(graph)
        code = gen.generate()
        self.assertNotIn("plt.figure()", code)


if __name__ == "__main__":
    unittest.main()
