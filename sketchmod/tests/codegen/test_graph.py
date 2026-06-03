from django.test import SimpleTestCase
from sketchmod.codegen.graph import parse_graph

VALID_GRAPH = {
    "nodes": [
        {
            "id": "input-main",
            "type": "input-data",
            "x": 100,
            "y": 100,
            "inputPorts": [],
            "outputPorts": [
                {
                    "id": "input-main_output_0",
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
            "dataShape": None,
        },
        {
            "id": "output-main",
            "type": "output",
            "x": 300,
            "y": 100,
            "inputPorts": [
                {
                    "id": "output-main_input_0",
                    "type": "input",
                    "index": 0,
                    "subType": "train",
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["training"],
                },
                {
                    "id": "output-main_input_1",
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
                    "id": "output-main_output_0",
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
                    "id": "output-main_output_1",
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
                    "id": "output-main_output_2",
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
    ],
    "links": [],
    "nodeCounter": 2,
}


class GraphTest(SimpleTestCase):
    def test_parse_valid_graph(self):
        graph = parse_graph(VALID_GRAPH)
        self.assertEqual(len(graph.nodes), 2)
        self.assertIn("input-main", graph.nodes)
        self.assertIn("output-main", graph.nodes)

    def test_input_data_node_parsed(self):
        graph = parse_graph(VALID_GRAPH)
        node = graph.nodes["input-main"]
        self.assertEqual(node.type, "input-data")
        self.assertEqual(len(node.outputs), 1)
        port = node.outputs[0]
        self.assertEqual(port.activation_phases, ["preprocessing"])

    def test_output_node_parsed(self):
        graph = parse_graph(VALID_GRAPH)
        node = graph.nodes["output-main"]
        self.assertEqual(node.type, "output")
        self.assertEqual(len(node.inputs), 2)
        self.assertEqual(node.inputs[0].sub_type, "train")
        self.assertEqual(node.inputs[1].sub_type, "test")
        self.assertEqual(len(node.outputs), 3)

    def test_default_phases_applied(self):
        """Even if activationPhases is empty, defaults should be applied."""
        g = {
            "nodes": [
                {
                    "id": "n1",
                    "type": "layer",
                    "x": 0,
                    "y": 0,
                    "inputPorts": [
                        {
                            "id": "n1_input_0",
                            "type": "input",
                            "index": 0,
                            "subType": None,
                            "shape": None,
                            "bias": 0,
                            "portKind": "multi",
                            "activationPhases": [],
                        }
                    ],
                    "outputPorts": [
                        {
                            "id": "n1_output_0",
                            "type": "output",
                            "index": 0,
                            "subType": None,
                            "shape": None,
                            "bias": 0,
                            "portKind": "data",
                            "activationPhases": [],
                        }
                    ],
                    "numInputs": 1,
                    "numOutputs": 1,
                    "bias": 0,
                    "hasBias": True,
                    "paramInputs": [],
                    "paramOutputs": [],
                    "numParamInputs": 0,
                    "numParamOutputs": 0,
                    "activation": "relu",
                    "numNeurons": 64,
                }
            ],
            "links": [],
            "nodeCounter": 1,
        }
        graph = parse_graph(g)
        node = graph.nodes["n1"]
        # Both ports should have been set to ["training", "evaluation"] by default
        self.assertEqual(node.inputs[0].activation_phases, ["training", "evaluation"])
        self.assertEqual(node.outputs[0].activation_phases, ["training", "evaluation"])
