from django.test import SimpleTestCase
from sketchmod.generator import CodeGenerator


class GeneratorIntegrationTests(SimpleTestCase):

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
        return gen.generate()

    def test_full_pipeline_generates(self):
        """A complete graph with input, layer, output, and optimizer should generate valid code."""
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
                "id": "l1",
                "type": "layer",
                "numNeurons": 128,
                "activation": "relu",
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
            },
            {
                "id": "l2",
                "type": "layer",
                "numNeurons": 10,
                "activation": "sigmoid",
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
                "outputPorts": [
                    {
                        "id": "o1_output_0",
                        "type": "output",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "portKind": "role",
                        "role": "loss",
                    },
                    {
                        "id": "o1_output_1",
                        "type": "output",
                        "index": 1,
                        "subType": None,
                        "shape": None,
                        "portKind": "role",
                        "role": "prediction",
                    },
                    {
                        "id": "o1_output_2",
                        "type": "output",
                        "index": 2,
                        "subType": None,
                        "shape": None,
                        "portKind": "role",
                        "role": "evaluation",
                    },
                ],
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
                "epochs": 5,
                "batchSize": 64,
                "shuffle": True,
                "gradientClip": None,
                "earlyStopping": False,
                "earlyStoppingPatience": 10,
            },
            {
                "id": "viz1",
                "type": "visualization",
                "colorMode": "none",
                "inputPorts": [],
                "outputPorts": [],
                "colorPalette": ["#ef4444"],
                "continuousMinColor": "#3b82f6",
                "continuousMaxColor": "#ef4444",
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
                "to": "l2_input_0",
                "weight": 0,
                "weightShape": None,
                "hasWeight": True,
            },
            {
                "from": "l2_output_0",
                "to": "o1_input_0",
                "weight": 0,
                "weightShape": None,
                "hasWeight": False,
            },
            {
                "from": "o1_output_0",
                "to": "opt1_input_0",
                "weight": 0,
                "weightShape": None,
                "hasWeight": False,
            },
        ]
        code = self._generate(nodes, links)

        # Should contain all major sections
        self.assertIn("# Generated by SketchNet", code)
        self.assertIn("import torch", code)
        self.assertIn("class SketchNetModel", code)
        self.assertIn("def load_data():", code)
        self.assertIn("def train_model(", code)
        self.assertIn('if __name__ == "__main__":', code)

        # Should NOT error on valid code
        try:
            compile(code, "<generated>", "exec")
        except SyntaxError as e:
            self.fail(f"Generated code has syntax error: {e}")

    def test_code_is_valid_python(self):
        """Minimal valid graph should produce compilable Python code."""
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
                "numNeurons": 5,
                "activation": "relu",
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
        code = self._generate(nodes, links)
        try:
            compile(code, "<generated>", "exec")
        except SyntaxError as e:
            self.fail(f"Generated code has syntax error: {e}")
