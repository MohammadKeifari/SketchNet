from django.test import SimpleTestCase
from sketchmod.codegen.graph import parse_graph
from sketchmod.codegen.writer import CodeWriter
from sketchmod.codegen.translators import get_translator


class BaseGraphMixin:
    """Helper to create a minimal graph with a single node of given type."""

    def _make_graph(self, node_dict, links=None):
        return {"nodes": [node_dict], "links": links or [], "nodeCounter": 1}

    def _get_translator(self, node_dict, links=None):
        graph = parse_graph(self._make_graph(node_dict, links))
        node = graph.nodes[node_dict["id"]]
        var_map = {}
        return get_translator(node, graph, var_map), var_map


class InputDataTranslatorTest(SimpleTestCase, BaseGraphMixin):
    def test_data_code_manual_shape(self):
        node = {
            "id": "input-main",
            "type": "input-data",
            "x": 0,
            "y": 0,
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
            "dataShape": "(200, 10)",
        }
        t, var_map = self._get_translator(node)
        w = CodeWriter()
        t.data_code(w, "pre")
        code = str(w)
        self.assertIn("raw_data = torch.randn(200, 10)", code)
        self.assertIn("raw_data", var_map.get("input-main", ""))

    def test_data_code_no_shape(self):
        node = {
            "id": "input-main",
            "type": "input-data",
            "x": 0,
            "y": 0,
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
        }
        t, var_map = self._get_translator(node)
        w = CodeWriter()
        t.data_code(w, "pre")
        code = str(w)
        self.assertIn("raw_data = torch.randn(200, 10)", code)


class ColumnSelectTranslatorTest(SimpleTestCase, BaseGraphMixin):
    def test_data_code_with_columns(self):
        node = {
            "id": "c1",
            "type": "column-select",
            "x": 0,
            "y": 0,
            "inputPorts": [
                {
                    "id": "c1_input_0",
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
                    "id": "c1_output_0",
                    "type": "output",
                    "index": 0,
                    "subType": None,
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["preprocessing"],
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
            "selectedColumns": [0, 2],
            "columnInput": "0,2",
            "availableColumns": [],
            "columnCount": 0,
            "datasetId": None,
        }
        # Need a source node to connect to input
        graph = {
            "nodes": [
                {
                    "id": "src",
                    "type": "input-data",
                    "x": 0,
                    "y": 0,
                    "inputPorts": [],
                    "outputPorts": [
                        {
                            "id": "src_output_0",
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
                node,
            ],
            "links": [
                {
                    "from": "src_output_0",
                    "to": "c1_input_0",
                    "weight": 1.0,
                    "weightShape": None,
                    "hasWeight": False,
                }
            ],
            "nodeCounter": 2,
        }
        g = parse_graph(graph)
        var_map = {"src": "raw_data"}
        t = get_translator(g.nodes["c1"], g, var_map)
        w = CodeWriter()
        t.data_code(w, "pre")
        code = str(w)
        self.assertIn("[:, [0, 2]]", code)


class NormalizeTranslatorTest(SimpleTestCase, BaseGraphMixin):
    def test_data_code_standard(self):
        node = {
            "id": "n1",
            "type": "normalize",
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
                    "portKind": "data",
                    "activationPhases": ["preprocessing"],
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
                    "activationPhases": ["preprocessing"],
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
        }
        graph = {
            "nodes": [
                {
                    "id": "src",
                    "type": "input-data",
                    "x": 0,
                    "y": 0,
                    "inputPorts": [],
                    "outputPorts": [
                        {
                            "id": "src_output_0",
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
                node,
            ],
            "links": [
                {
                    "from": "src_output_0",
                    "to": "n1_input_0",
                    "weight": 1.0,
                    "weightShape": None,
                    "hasWeight": False,
                }
            ],
            "nodeCounter": 2,
        }
        g = parse_graph(graph)
        var_map = {"src": "raw_data"}
        t = get_translator(g.nodes["n1"], g, var_map)
        w = CodeWriter()
        t.data_code(w, "pre")
        code = str(w)
        self.assertIn("mean =", code)
        self.assertIn("std =", code)


class OneHotTranslatorTest(SimpleTestCase, BaseGraphMixin):
    def test_data_code(self):
        node = {
            "id": "o1",
            "type": "onehot",
            "x": 0,
            "y": 0,
            "inputPorts": [
                {
                    "id": "o1_input_0",
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
                    "id": "o1_output_0",
                    "type": "output",
                    "index": 0,
                    "subType": None,
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["preprocessing"],
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
            "numClasses": 5,
        }
        graph = {
            "nodes": [
                {
                    "id": "src",
                    "type": "input-data",
                    "x": 0,
                    "y": 0,
                    "inputPorts": [],
                    "outputPorts": [
                        {
                            "id": "src_output_0",
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
                node,
            ],
            "links": [
                {
                    "from": "src_output_0",
                    "to": "o1_input_0",
                    "weight": 1.0,
                    "weightShape": None,
                    "hasWeight": False,
                }
            ],
            "nodeCounter": 2,
        }
        g = parse_graph(graph)
        var_map = {"src": "raw_data"}
        t = get_translator(g.nodes["o1"], g, var_map)
        w = CodeWriter()
        t.data_code(w, "pre")
        code = str(w)
        self.assertIn("one_hot", code)
        self.assertIn("num_classes=5", code)
        self.assertIn("squeeze", code)


class DeOneHotTranslatorTest(SimpleTestCase, BaseGraphMixin):
    def test_data_code(self):
        node = {
            "id": "d1",
            "type": "deonehot",
            "x": 0,
            "y": 0,
            "inputPorts": [
                {
                    "id": "d1_input_0",
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
                    "id": "d1_output_0",
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
            "bias": 0,
            "hasBias": False,
            "paramInputs": [],
            "paramOutputs": [],
            "numParamInputs": 0,
            "numParamOutputs": 0,
            "numClasses": 5,
        }
        graph = {
            "nodes": [
                {
                    "id": "src",
                    "type": "input-data",
                    "x": 0,
                    "y": 0,
                    "inputPorts": [],
                    "outputPorts": [
                        {
                            "id": "src_output_0",
                            "type": "output",
                            "index": 0,
                            "subType": None,
                            "shape": None,
                            "bias": 0,
                            "portKind": "data",
                            "activationPhases": ["evaluation"],
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
                node,
            ],
            "links": [
                {
                    "from": "src_output_0",
                    "to": "d1_input_0",
                    "weight": 1.0,
                    "weightShape": None,
                    "hasWeight": False,
                }
            ],
            "nodeCounter": 2,
        }
        g = parse_graph(graph)
        var_map = {"src": "predictions"}
        t = get_translator(g.nodes["d1"], g, var_map)
        w = CodeWriter()
        t.data_code(w, "eval")
        code = str(w)
        self.assertIn("argmax", code)


class TrainTestSplitTranslatorTest(SimpleTestCase, BaseGraphMixin):
    def test_data_code(self):
        node = {
            "id": "t1",
            "type": "train-test",
            "x": 0,
            "y": 0,
            "inputPorts": [
                {
                    "id": "t1_input_0",
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
                    "id": "t1_output_0",
                    "type": "output",
                    "index": 0,
                    "subType": "train",
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["preprocessing"],
                },
                {
                    "id": "t1_output_1",
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
        }
        graph = {
            "nodes": [
                {
                    "id": "src",
                    "type": "input-data",
                    "x": 0,
                    "y": 0,
                    "inputPorts": [],
                    "outputPorts": [
                        {
                            "id": "src_output_0",
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
                node,
            ],
            "links": [
                {
                    "from": "src_output_0",
                    "to": "t1_input_0",
                    "weight": 1.0,
                    "weightShape": None,
                    "hasWeight": False,
                }
            ],
            "nodeCounter": 2,
        }
        g = parse_graph(graph)
        var_map = {"src": "raw_data"}
        t = get_translator(g.nodes["t1"], g, var_map)
        w = CodeWriter()
        t.data_code(w, "pre")
        code = str(w)
        self.assertIn("train_size", code)
        self.assertIn("train_data", code)
        self.assertIn("test_data", code)


class LayerTranslatorTest(SimpleTestCase, BaseGraphMixin):
    def setUp(self):
        self.node = {
            "id": "l1",
            "type": "layer",
            "x": 0,
            "y": 0,
            "inputPorts": [
                {
                    "id": "l1_input_0",
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
                    "id": "l1_output_0",
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
            "hasBias": True,
            "paramInputs": [],
            "paramOutputs": [],
            "numParamInputs": 0,
            "numParamOutputs": 0,
            "activation": "relu",
            "numNeurons": 64,
        }
        graph_data = {
            "nodes": [
                {
                    "id": "src",
                    "type": "input-data",
                    "x": 0,
                    "y": 0,
                    "inputPorts": [],
                    "outputPorts": [
                        {
                            "id": "src_output_0",
                            "type": "output",
                            "index": 0,
                            "subType": None,
                            "shape": None,
                            "bias": 0,
                            "portKind": "data",
                            "activationPhases": ["training"],
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
                self.node,
            ],
            "links": [
                {
                    "from": "src_output_0",
                    "to": "l1_input_0",
                    "weight": 1.0,
                    "weightShape": None,
                    "hasWeight": True,
                }
            ],
            "nodeCounter": 2,
        }
        self.graph = parse_graph(graph_data)
        self.var_map = {"src": "data"}

    def test_init_code(self):
        node = self.graph.nodes["l1"]
        t = get_translator(node, self.graph, self.var_map)
        w = CodeWriter()
        t.init_code(w)
        code = str(w)
        self.assertIn("nn.Linear", code)
        self.assertIn("64", code)

    def test_forward_code(self):
        node = self.graph.nodes["l1"]
        t = get_translator(node, self.graph, self.var_map)
        w = CodeWriter()
        t.forward_code(w)
        code = str(w)
        self.assertIn("inputs_dict", code)
        self.assertIn("outputs", code)
        self.assertIn("relu", code)


class NeuronTranslatorTest(SimpleTestCase, BaseGraphMixin):
    def test_init_code(self):
        node = {
            "id": "n1",
            "type": "neuron",
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
                    "activationPhases": ["training"],
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
                    "activationPhases": ["training"],
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
            "activation": "sigmoid",
        }
        graph_data = {
            "nodes": [
                {
                    "id": "src",
                    "type": "input-data",
                    "x": 0,
                    "y": 0,
                    "inputPorts": [],
                    "outputPorts": [
                        {
                            "id": "src_output_0",
                            "type": "output",
                            "index": 0,
                            "subType": None,
                            "shape": None,
                            "bias": 0,
                            "portKind": "data",
                            "activationPhases": ["training"],
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
                node,
            ],
            "links": [
                {
                    "from": "src_output_0",
                    "to": "n1_input_0",
                    "weight": 1.0,
                    "weightShape": None,
                    "hasWeight": True,
                }
            ],
            "nodeCounter": 2,
        }
        g = parse_graph(graph_data)
        var_map = {"src": "data"}
        t = get_translator(g.nodes["n1"], g, var_map)
        w = CodeWriter()
        t.init_code(w)
        code = str(w)
        self.assertIn("nn.Linear", code)
        self.assertIn("1,", code)  # output size 1

    def test_forward_code(self):
        node = {
            "id": "n1",
            "type": "neuron",
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
                    "activationPhases": ["training"],
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
                    "activationPhases": ["training"],
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
            "activation": "tanh",
        }
        graph_data = {
            "nodes": [
                {
                    "id": "src",
                    "type": "input-data",
                    "x": 0,
                    "y": 0,
                    "inputPorts": [],
                    "outputPorts": [
                        {
                            "id": "src_output_0",
                            "type": "output",
                            "index": 0,
                            "subType": None,
                            "shape": None,
                            "bias": 0,
                            "portKind": "data",
                            "activationPhases": ["training"],
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
                node,
            ],
            "links": [
                {
                    "from": "src_output_0",
                    "to": "n1_input_0",
                    "weight": 1.0,
                    "weightShape": None,
                    "hasWeight": True,
                }
            ],
            "nodeCounter": 2,
        }
        g = parse_graph(graph_data)
        var_map = {"src": "data"}
        t = get_translator(g.nodes["n1"], g, var_map)
        w = CodeWriter()
        t.forward_code(w)
        code = str(w)
        self.assertIn("tanh", code)


class FlattenTranslatorTest(SimpleTestCase, BaseGraphMixin):
    def test_init_and_forward(self):
        node = {
            "id": "f1",
            "type": "flatten",
            "x": 0,
            "y": 0,
            "inputPorts": [
                {
                    "id": "f1_input_0",
                    "type": "input",
                    "index": 0,
                    "subType": None,
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["training"],
                }
            ],
            "outputPorts": [
                {
                    "id": "f1_output_0",
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
        graph_data = {
            "nodes": [
                {
                    "id": "src",
                    "type": "input-data",
                    "x": 0,
                    "y": 0,
                    "inputPorts": [],
                    "outputPorts": [
                        {
                            "id": "src_output_0",
                            "type": "output",
                            "index": 0,
                            "subType": None,
                            "shape": None,
                            "bias": 0,
                            "portKind": "data",
                            "activationPhases": ["training"],
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
                node,
            ],
            "links": [
                {
                    "from": "src_output_0",
                    "to": "f1_input_0",
                    "weight": 1.0,
                    "weightShape": None,
                    "hasWeight": False,
                }
            ],
            "nodeCounter": 2,
        }
        g = parse_graph(graph_data)
        var_map = {"src": "data"}
        t = get_translator(g.nodes["f1"], g, var_map)
        w = CodeWriter()
        t.init_code(w)
        self.assertIn("Flatten", str(w))
        w2 = CodeWriter()
        t.forward_code(w2)
        self.assertIn("flatten", str(w2))


class DropoutTranslatorTest(SimpleTestCase, BaseGraphMixin):
    def test_init_code(self):
        node = {
            "id": "d1",
            "type": "dropout",
            "x": 0,
            "y": 0,
            "inputPorts": [
                {
                    "id": "d1_input_0",
                    "type": "input",
                    "index": 0,
                    "subType": None,
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["training"],
                }
            ],
            "outputPorts": [
                {
                    "id": "d1_output_0",
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
            "rate": 0.3,
        }
        graph_data = {
            "nodes": [
                {
                    "id": "src",
                    "type": "input-data",
                    "x": 0,
                    "y": 0,
                    "inputPorts": [],
                    "outputPorts": [
                        {
                            "id": "src_output_0",
                            "type": "output",
                            "index": 0,
                            "subType": None,
                            "shape": None,
                            "bias": 0,
                            "portKind": "data",
                            "activationPhases": ["training"],
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
                node,
            ],
            "links": [
                {
                    "from": "src_output_0",
                    "to": "d1_input_0",
                    "weight": 1.0,
                    "weightShape": None,
                    "hasWeight": False,
                }
            ],
            "nodeCounter": 2,
        }
        g = parse_graph(graph_data)
        var_map = {"src": "data"}
        t = get_translator(g.nodes["d1"], g, var_map)
        w = CodeWriter()
        t.init_code(w)
        code = str(w)
        self.assertIn("Dropout", code)
        self.assertIn("0.3", code)


class BatchNormTranslatorTest(SimpleTestCase, BaseGraphMixin):
    def test_init_code(self):
        node = {
            "id": "b1",
            "type": "batchnorm",
            "x": 0,
            "y": 0,
            "inputPorts": [
                {
                    "id": "b1_input_0",
                    "type": "input",
                    "index": 0,
                    "subType": None,
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["training"],
                }
            ],
            "outputPorts": [
                {
                    "id": "b1_output_0",
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
            "eps": 0.001,
            "momentum": 0.1,
        }
        graph_data = {
            "nodes": [
                {
                    "id": "src",
                    "type": "input-data",
                    "x": 0,
                    "y": 0,
                    "inputPorts": [],
                    "outputPorts": [
                        {
                            "id": "src_output_0",
                            "type": "output",
                            "index": 0,
                            "subType": None,
                            "shape": None,
                            "bias": 0,
                            "portKind": "data",
                            "activationPhases": ["training"],
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
                node,
            ],
            "links": [
                {
                    "from": "src_output_0",
                    "to": "b1_input_0",
                    "weight": 1.0,
                    "weightShape": None,
                    "hasWeight": False,
                }
            ],
            "nodeCounter": 2,
        }
        g = parse_graph(graph_data)
        var_map = {"src": "data"}
        t = get_translator(g.nodes["b1"], g, var_map)
        w = CodeWriter()
        t.init_code(w)
        code = str(w)
        self.assertIn("BatchNorm1d", code)


class AddTranslatorTest(SimpleTestCase, BaseGraphMixin):
    def test_forward_code(self):
        node = {
            "id": "a1",
            "type": "add",
            "x": 0,
            "y": 0,
            "inputPorts": [
                {
                    "id": "a1_input_0",
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
                    "id": "a1_output_0",
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
        graph_data = {
            "nodes": [
                {
                    "id": "s1",
                    "type": "input-data",
                    "x": 0,
                    "y": 0,
                    "inputPorts": [],
                    "outputPorts": [
                        {
                            "id": "s1_output_0",
                            "type": "output",
                            "index": 0,
                            "subType": None,
                            "shape": None,
                            "bias": 0,
                            "portKind": "data",
                            "activationPhases": ["training"],
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
                    "id": "s2",
                    "type": "input-data",
                    "x": 0,
                    "y": 0,
                    "inputPorts": [],
                    "outputPorts": [
                        {
                            "id": "s2_output_0",
                            "type": "output",
                            "index": 0,
                            "subType": None,
                            "shape": None,
                            "bias": 0,
                            "portKind": "data",
                            "activationPhases": ["training"],
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
                node,
            ],
            "links": [
                {
                    "from": "s1_output_0",
                    "to": "a1_input_0",
                    "weight": 1.0,
                    "weightShape": None,
                    "hasWeight": False,
                },
                {
                    "from": "s2_output_0",
                    "to": "a1_input_0",
                    "weight": 1.0,
                    "weightShape": None,
                    "hasWeight": False,
                },
            ],
            "nodeCounter": 3,
        }
        g = parse_graph(graph_data)
        var_map = {"s1": "x", "s2": "y"}
        t = get_translator(g.nodes["a1"], g, var_map)
        w = CodeWriter()
        t.forward_code(w)
        code = str(w)
        self.assertIn("a + b", code)


class ConcatTranslatorTest(SimpleTestCase, BaseGraphMixin):
    def test_forward_code(self):
        node = {
            "id": "c1",
            "type": "concat",
            "x": 0,
            "y": 0,
            "inputPorts": [
                {
                    "id": "c1_input_0",
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
                    "id": "c1_output_0",
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
            "axis": 1,
        }
        graph_data = {
            "nodes": [
                {
                    "id": "s1",
                    "type": "input-data",
                    "x": 0,
                    "y": 0,
                    "inputPorts": [],
                    "outputPorts": [
                        {
                            "id": "s1_output_0",
                            "type": "output",
                            "index": 0,
                            "subType": None,
                            "shape": None,
                            "bias": 0,
                            "portKind": "data",
                            "activationPhases": ["training"],
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
                    "id": "s2",
                    "type": "input-data",
                    "x": 0,
                    "y": 0,
                    "inputPorts": [],
                    "outputPorts": [
                        {
                            "id": "s2_output_0",
                            "type": "output",
                            "index": 0,
                            "subType": None,
                            "shape": None,
                            "bias": 0,
                            "portKind": "data",
                            "activationPhases": ["training"],
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
                node,
            ],
            "links": [
                {
                    "from": "s1_output_0",
                    "to": "c1_input_0",
                    "weight": 1.0,
                    "weightShape": None,
                    "hasWeight": False,
                },
                {
                    "from": "s2_output_0",
                    "to": "c1_input_0",
                    "weight": 1.0,
                    "weightShape": None,
                    "hasWeight": False,
                },
            ],
            "nodeCounter": 3,
        }
        g = parse_graph(graph_data)
        var_map = {"s1": "x", "s2": "y"}
        t = get_translator(g.nodes["c1"], g, var_map)
        w = CodeWriter()
        t.forward_code(w)
        code = str(w)
        self.assertIn("torch.cat", code)


class OutputTranslatorTest(SimpleTestCase, BaseGraphMixin):
    def test_forward_code(self):
        node = {
            "id": "output-main",
            "type": "output",
            "x": 0,
            "y": 0,
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
                }
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
        graph_data = {
            "nodes": [
                {
                    "id": "src",
                    "type": "layer",
                    "x": 0,
                    "y": 0,
                    "inputPorts": [
                        {
                            "id": "src_input_0",
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
                            "id": "src_output_0",
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
                    "hasBias": True,
                    "paramInputs": [],
                    "paramOutputs": [],
                    "numParamInputs": 0,
                    "numParamOutputs": 0,
                    "activation": "relu",
                    "numNeurons": 10,
                },
                node,
            ],
            "links": [
                {
                    "from": "src_output_0",
                    "to": "output-main_input_0",
                    "weight": 1.0,
                    "weightShape": None,
                    "hasWeight": False,
                }
            ],
            "nodeCounter": 2,
        }
        g = parse_graph(graph_data)
        var_map = {"src": "x"}
        t = get_translator(g.nodes["output-main"], g, var_map)
        w = CodeWriter()
        t.forward_code(w)
        code = str(w)
        self.assertIn("outputs['output-main_output_0']", code)


class OptimizerTranslatorTest(SimpleTestCase, BaseGraphMixin):
    def test_optimizer_code(self):
        node = {
            "id": "o1",
            "type": "optimizer",
            "x": 0,
            "y": 0,
            "inputPorts": [
                {
                    "id": "o1_input_0",
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
                    "id": "o1_input_1",
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
            "lossType": "cross_entropy",
            "optimizerType": "sgd",
            "learningRate": 0.01,
            "adamBeta1": 0.9,
            "adamBeta2": 0.999,
            "adamEpsilon": 1e-8,
            "sgdMomentum": 0.9,
            "weightDecay": 0.0001,
            "nesterov": True,
            "epochs": 20,
            "batchSize": 64,
            "shuffle": False,
            "gradientClip": 1.0,
            "earlyStopping": True,
            "earlyStoppingPatience": 5,
        }
        t, _ = self._get_translator(node)
        w = CodeWriter()
        code = t.optimizer_code(w)
        self.assertIn("'loss_type': 'cross_entropy'", code)
        self.assertIn("'optimizer_type': 'sgd'", code)
        self.assertIn("'learning_rate': 0.01", code)
        self.assertIn("'epochs': 20", code)
        self.assertIn("'batch_size': 64", code)
        self.assertIn("'early_stopping': True", code)


class VisualizationTranslatorTest(SimpleTestCase, BaseGraphMixin):
    def test_visualization_code_discrete(self):
        node = {
            "id": "v1",
            "type": "visualization",
            "x": 0,
            "y": 0,
            "inputPorts": [
                {
                    "id": "v1_input_0",
                    "type": "input",
                    "index": 0,
                    "subType": "coord",
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["evaluation"],
                },
                {
                    "id": "v1_input_1",
                    "type": "input",
                    "index": 1,
                    "subType": "coord",
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["evaluation"],
                },
                {
                    "id": "v1_input_2",
                    "type": "input",
                    "index": 2,
                    "subType": None,
                    "shape": None,
                    "bias": 0,
                    "portKind": "role",
                    "activationPhases": ["evaluation"],
                    "role": "color",
                },
            ],
            "outputPorts": [],
            "numInputs": 3,
            "numOutputs": 0,
            "bias": 0,
            "hasBias": False,
            "paramInputs": [],
            "paramOutputs": [],
            "numParamInputs": 0,
            "numParamOutputs": 0,
            "colorMode": "discrete",
            "colorPalette": ["#ef4444", "#4ade80", "#60a5fa"],
            "continuousMinColor": "#3b82f6",
            "continuousMaxColor": "#ef4444",
        }
        t, _ = self._get_translator(node)
        w = CodeWriter()
        t.visualization_code(w)
        code = str(w)
        self.assertIn("ListedColormap", code)
        self.assertIn("#ef4444", code)
        self.assertIn("plt.scatter", code)


class Conv2DTranslatorTest(SimpleTestCase, BaseGraphMixin):
    def test_init_code(self):
        node = {
            "id": "c1",
            "type": "conv2d",
            "x": 0,
            "y": 0,
            "inputPorts": [
                {
                    "id": "c1_input_0",
                    "type": "input",
                    "index": 0,
                    "subType": None,
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["training"],
                }
            ],
            "outputPorts": [
                {
                    "id": "c1_output_0",
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
            "hasBias": True,
            "paramInputs": [],
            "paramOutputs": [],
            "numParamInputs": 0,
            "numParamOutputs": 0,
            "filters": 32,
            "kernelSize": 3,
            "stride": 2,
            "padding": 1,
            "activation": "relu",
        }
        t, _ = self._get_translator(node)
        w = CodeWriter()
        t.init_code(w)
        code = str(w)
        self.assertIn("Conv2d", code)
        self.assertIn("32", code)
        self.assertIn("kernel_size=3", code)
        self.assertIn("stride=2", code)
        self.assertIn("padding=1", code)
