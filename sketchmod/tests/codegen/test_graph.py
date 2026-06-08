"""
Unit tests for graph parsing and symbolic shape propagation.
"""

import unittest
from sketchmod.codegen.graph import parse_graph, ShapeInfo, ShapeDim


class GraphParsingTest(unittest.TestCase):
    def setUp(self):
        self.basic_json = {
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
                    "datasetId": "ds1",
                    "datasetName": "Data",
                    "dataShape": "(100, 3)",
                    "datasetFile": "data.csv",
                    "datasetFormat": "csv",
                },
                {
                    "id": "layer1",
                    "type": "layer",
                    "x": 100,
                    "y": 100,
                    "inputPorts": [
                        {
                            "id": "layer1_in_0",
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
                            "id": "layer1_out_0",
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
                    "numNeurons": 32,
                    "bias": 0,
                    "hasBias": True,
                    "paramInputs": [],
                    "paramOutputs": [],
                    "numParamInputs": 0,
                    "numParamOutputs": 0,
                },
            ],
            "links": [
                {
                    "from": "inp_out_0",
                    "to": "layer1_in_0",
                    "weight": 1.0,
                    "weightShape": {"shape": [32, 3], "dtype": "float32"},
                    "hasWeight": True,
                }
            ],
            "ports": [],
            "nodeCounter": 2,
        }

    # ---------- basic parsing ----------
    def test_parse_basic_graph(self):
        graph = parse_graph(self.basic_json)
        self.assertIn("inp", graph.nodes)
        self.assertIn("layer1", graph.nodes)
        self.assertEqual(len(graph.links), 1)
        self.assertEqual(graph.ports["inp_out_0"].node_id, "inp")

    def test_activation_phases_preserved(self):
        graph = parse_graph(self.basic_json)
        self.assertEqual(
            graph.ports["layer1_in_0"].activation_phases, ["training", "evaluation"]
        )

    def test_link_weight_shape(self):
        graph = parse_graph(self.basic_json)
        link = graph.links[0]
        self.assertTrue(link.has_weight)
        self.assertEqual(link.weight_shape, {"shape": [32, 3], "dtype": "float32"})

    # ---------- shape propagation ----------
    def test_input_data_shape(self):
        graph = parse_graph(self.basic_json)
        inp_port = graph.ports["inp_out_0"]
        self.assertIsNotNone(inp_port.shape)
        self.assertEqual(len(inp_port.shape.shape), 2)
        self.assertEqual(int(inp_port.shape.shape[0]), 100)
        self.assertEqual(int(inp_port.shape.shape[1]), 3)

    def test_layer_shape_propagation(self):
        graph = parse_graph(self.basic_json)
        layer_out = graph.ports["layer1_out_0"]
        self.assertIsNotNone(layer_out.shape)
        self.assertEqual(len(layer_out.shape.shape), 2)
        self.assertEqual(int(layer_out.shape.shape[0]), 100)
        self.assertEqual(int(layer_out.shape.shape[1]), 32)

    def test_column_select_shape(self):
        json_data = {
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
                            "activationPhases": ["preprocessing"],
                            "portKind": "data",
                            "subType": None,
                            "shape": None,
                            "bias": 0,
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
                    "dataShape": "(50, 10)",
                },
                {
                    "id": "col",
                    "type": "column-select",
                    "x": 100,
                    "y": 100,
                    "inputPorts": [
                        {
                            "id": "col_in",
                            "type": "input",
                            "index": 0,
                            "activationPhases": ["preprocessing"],
                            "portKind": "data",
                            "subType": None,
                            "shape": None,
                            "bias": 0,
                        }
                    ],
                    "outputPorts": [
                        {
                            "id": "col_out",
                            "type": "output",
                            "index": 0,
                            "activationPhases": ["preprocessing"],
                            "portKind": "data",
                            "subType": None,
                            "shape": None,
                            "bias": 0,
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
                    "selectedColumns": [0, 1],
                    "columnInput": "0:1",
                },
            ],
            "links": [
                {
                    "from": "inp_out",
                    "to": "col_in",
                    "weight": 1,
                    "weightShape": None,
                    "hasWeight": False,
                }
            ],
            "ports": [],
            "nodeCounter": 2,
        }
        graph = parse_graph(json_data)
        col_out = graph.ports["col_out"]
        self.assertIsNotNone(col_out.shape)
        self.assertEqual(len(col_out.shape.shape), 2)
        self.assertEqual(int(col_out.shape.shape[0]), 50)
        self.assertEqual(int(col_out.shape.shape[1]), 2)

    def test_train_test_split_shapes(self):
        json_data = {
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
                            "activationPhases": ["preprocessing"],
                            "portKind": "data",
                        }
                    ],
                    "numInputs": 0,
                    "numOutputs": 1,
                    "bias": 0,
                    "hasBias": False,
                    "dataShape": "(200, 5)",
                },
                {
                    "id": "split",
                    "type": "train-test",
                    "x": 100,
                    "y": 100,
                    "inputPorts": [
                        {
                            "id": "split_in",
                            "type": "input",
                            "index": 0,
                            "activationPhases": ["preprocessing"],
                            "portKind": "data",
                        }
                    ],
                    "outputPorts": [
                        {
                            "id": "split_train",
                            "type": "output",
                            "index": 0,
                            "activationPhases": ["preprocessing"],
                            "portKind": "data",
                        },
                        {
                            "id": "split_test",
                            "type": "output",
                            "index": 1,
                            "activationPhases": ["preprocessing"],
                            "portKind": "data",
                        },
                    ],
                    "numInputs": 1,
                    "numOutputs": 2,
                    "trainRatio": 0.7,
                    "randomSeed": 42,
                },
            ],
            "links": [{"from": "inp_out", "to": "split_in", "weight": 1}],
            "ports": [],
            "nodeCounter": 2,
        }
        graph = parse_graph(json_data)
        train_port = graph.ports["split_train"]
        test_port = graph.ports["split_test"]
        self.assertIsNotNone(train_port.shape)
        self.assertIsNotNone(test_port.shape)
        self.assertEqual(int(train_port.shape.shape[0]), 140)  # floor(200 * 0.7)
        self.assertEqual(int(test_port.shape.shape[0]), 60)  # 200 - 140
        self.assertEqual(train_port.shape.shape[1], 5)

    def test_output_node_argmax_shape(self):
        json_data = {
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
                            "activationPhases": ["preprocessing"],
                            "portKind": "data",
                        }
                    ],
                    "dataShape": "(50, 10)",
                },
                {
                    "id": "out",
                    "type": "output",
                    "x": 100,
                    "y": 100,
                    "inputPorts": [
                        {
                            "id": "out_in",
                            "type": "input",
                            "index": 0,
                            "activationPhases": ["training"],
                            "portKind": "data",
                        }
                    ],
                    "outputPorts": [
                        {
                            "id": "loss",
                            "type": "output",
                            "index": 0,
                            "role": "loss",
                            "activationPhases": ["training"],
                            "portKind": "role",
                        },
                        {
                            "id": "pred",
                            "type": "output",
                            "index": 1,
                            "role": "prediction",
                            "activationPhases": ["evaluation"],
                            "portKind": "role",
                        },
                    ],
                    "numInputs": 1,
                    "numOutputs": 2,
                    "outputActivations": {"prediction": "argmax", "loss": "none"},
                },
            ],
            "links": [{"from": "inp_out", "to": "out_in", "weight": 1}],
            "ports": [],
            "nodeCounter": 2,
        }
        graph = parse_graph(json_data)
        loss_shape = graph.ports["loss"].shape
        pred_shape = graph.ports["pred"].shape
        self.assertEqual(len(loss_shape.shape), 2)
        self.assertEqual(int(loss_shape.shape[1]), 10)
        self.assertEqual(len(pred_shape.shape), 1)  # argmax → 1D
        self.assertEqual(int(pred_shape.shape[0]), 50)

    def test_onehot_shape(self):
        json_data = {
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
                            "activationPhases": ["preprocessing"],
                            "portKind": "data",
                        }
                    ],
                    "dataShape": "(100, 1)",
                },
                {
                    "id": "oh",
                    "type": "onehot",
                    "x": 100,
                    "y": 100,
                    "inputPorts": [
                        {
                            "id": "oh_in",
                            "type": "input",
                            "index": 0,
                            "activationPhases": ["preprocessing"],
                            "portKind": "data",
                        }
                    ],
                    "outputPorts": [
                        {
                            "id": "oh_out",
                            "type": "output",
                            "index": 0,
                            "activationPhases": ["preprocessing"],
                            "portKind": "data",
                        }
                    ],
                    "numInputs": 1,
                    "numOutputs": 1,
                    "numClasses": 5,
                },
            ],
            "links": [{"from": "inp_out", "to": "oh_in", "weight": 1}],
            "ports": [],
            "nodeCounter": 2,
        }
        graph = parse_graph(json_data)
        oh_shape = graph.ports["oh_out"].shape
        self.assertEqual(len(oh_shape.shape), 2)
        self.assertEqual(int(oh_shape.shape[0]), 100)
        self.assertEqual(int(oh_shape.shape[1]), 5)

    def test_unknown_shape_handled(self):
        json_data = {
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
                            "activationPhases": ["preprocessing"],
                            "portKind": "data",
                        }
                    ],
                    "dataShape": None,
                },
            ],
            "links": [],
            "ports": [],
            "nodeCounter": 1,
        }
        graph = parse_graph(json_data)
        self.assertEqual(graph.ports["inp_out"].shape.shape, [])

    def test_reshape_infer(self):
        json_data = {
            "nodes": [
                {
                    "id": "inp",
                    "type": "input-data",
                    "x": 0,
                    "y": 0,
                    "dataShape": "(64, 3, 32, 32)",
                    "outputPorts": [
                        {
                            "id": "inp_out",
                            "type": "output",
                            "index": 0,
                            "activationPhases": ["preprocessing"],
                            "portKind": "data",
                        }
                    ],
                },
                {
                    "id": "r",
                    "type": "reshape",
                    "x": 100,
                    "y": 0,
                    "targetShape": "(64, -1)",
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
                },
            ],
            "links": [{"from": "inp_out", "to": "r_in", "weight": 1}],
            "ports": [],
            "nodeCounter": 2,
        }
        graph = parse_graph(json_data)
        out_shape = graph.ports["r_out"].shape
        self.assertEqual(len(out_shape.shape), 2)
        self.assertEqual(int(out_shape.shape[0]), 64)
        self.assertEqual(int(out_shape.shape[1]), 3 * 32 * 32)


if __name__ == "__main__":
    unittest.main()
