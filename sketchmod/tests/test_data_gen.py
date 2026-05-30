from django.test import SimpleTestCase
from sketchmod.generator import CodeGenerator
from sketchmod.codegen.data import DataGenerator


class DataGeneratorTests(SimpleTestCase):

    def _make_graph(self, nodes, links, ports=None):
        if ports is None:
            ports = []
            for n in nodes:
                for p in n.get("inputPorts", []):
                    ports.append(p)
                for p in n.get("outputPorts", []):
                    ports.append(p)
        return {"nodes": nodes, "links": links, "ports": ports}

    def _generate(self, nodes, links):
        graph = self._make_graph(nodes, links)
        gen = CodeGenerator(graph)
        data_gen = DataGenerator(gen)
        return "\n".join(data_gen.generate())

    def test_basic_data_loading(self):
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
                "dataShape": "(1000, 784)",
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
            }
        ]
        code = self._generate(nodes, links)
        self.assertIn("def load_data():", code)
        self.assertIn("TensorDataset", code)
        self.assertIn("DataLoader", code)

    def test_train_test_split(self):
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
                "dataShape": "(1000, 10)",
            },
            {
                "id": "t1",
                "type": "train-test",
                "trainRatio": 0.8,
                "randomSeed": 42,
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
                "to": "t1_input_0",
                "weight": 0,
                "weightShape": None,
                "hasWeight": False,
            },
            {
                "from": "t1_output_0",
                "to": "o1_input_0",
                "weight": 0,
                "weightShape": None,
                "hasWeight": False,
            },
        ]
        code = self._generate(nodes, links)
        self.assertIn("split_idx", code)
        self.assertIn("0.8", code)
        self.assertIn("torch.manual_seed(42)", code)

    def test_normalization_standard(self):
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
                "id": "n1",
                "type": "normalize",
                "method": "standard",
                "inputPorts": [
                    {
                        "id": "n1_input_0",
                        "type": "input",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "portKind": "data",
                    }
                ],
                "outputPorts": [
                    {
                        "id": "n1_output_0",
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
                "to": "n1_input_0",
                "weight": 0,
                "weightShape": None,
                "hasWeight": False,
            },
            {
                "from": "n1_output_0",
                "to": "o1_input_0",
                "weight": 0,
                "weightShape": None,
                "hasWeight": False,
            },
        ]
        code = self._generate(nodes, links)
        self.assertIn("Standard", code)
        self.assertIn("mean =", code)
        self.assertIn("std =", code)

    def test_normalization_minmax(self):
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
                "id": "n1",
                "type": "normalize",
                "method": "minmax",
                "inputPorts": [
                    {
                        "id": "n1_input_0",
                        "type": "input",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "portKind": "data",
                    }
                ],
                "outputPorts": [
                    {
                        "id": "n1_output_0",
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
                "to": "n1_input_0",
                "weight": 0,
                "weightShape": None,
                "hasWeight": False,
            },
            {
                "from": "n1_output_0",
                "to": "o1_input_0",
                "weight": 0,
                "weightShape": None,
                "hasWeight": False,
            },
        ]
        code = self._generate(nodes, links)
        self.assertIn("Min-Max", code)
        self.assertIn("x_min =", code)
        self.assertIn("x_max =", code)

    def test_batch_size_from_optimizer(self):
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
                "batchSize": 128,
                "shuffle": False,
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
        code = self._generate(nodes, links)
        self.assertIn("batch_size=128", code)
        self.assertIn("shuffle=False", code)
