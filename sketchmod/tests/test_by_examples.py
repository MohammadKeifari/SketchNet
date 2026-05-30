from django.test import SimpleTestCase
from sketchmod.codegen.generator import CodeGenerator
from sketchmod.codegen.validator import GraphValidator


class ExampleGraphTests(SimpleTestCase):
    """Test real-world example graphs for both validation and code generation."""

    def _validate_and_generate(self, graph):
        validator = GraphValidator(graph)
        result = validator.validate()
        gen = CodeGenerator(graph)
        code = gen.generate()
        return result, code

    # ========== EXAMPLE 1: Simple Classifier ==========

    def test_simple_classifier(self):
        """Input(784) → Layer(128, relu) → Layer(10, sigmoid) → Output"""
        nodes = [
            {
                "id": "i1",
                "type": "input-data",
                "inputPorts": [],
                "outputPorts": [self._port("i1_output_0", "output", 0, "data")],
                "dataShape": "(1000, 784)",
            },
            {
                "id": "l1",
                "type": "layer",
                "numNeurons": 128,
                "activation": "relu",
                "inputPorts": [self._port("l1_input_0", "input", 0, "multi")],
                "outputPorts": [self._port("l1_output_0", "output", 0, "data")],
            },
            {
                "id": "l2",
                "type": "layer",
                "numNeurons": 10,
                "activation": "sigmoid",
                "inputPorts": [self._port("l2_input_0", "input", 0, "multi")],
                "outputPorts": [self._port("l2_output_0", "output", 0, "data")],
            },
            {
                "id": "o1",
                "type": "output",
                "inputPorts": [self._port("o1_input_0", "input", 0, "data")],
                "outputPorts": [
                    self._role_port("o1_output_0", "output", 0, "loss"),
                    self._role_port("o1_output_1", "output", 1, "prediction"),
                    self._role_port("o1_output_2", "output", 2, "evaluation"),
                ],
            },
        ]
        links = [
            self._link("i1_output_0", "l1_input_0", True),
            self._link("l1_output_0", "l2_input_0", True),
            self._link("l2_output_0", "o1_input_0", False),
        ]
        graph = {"nodes": nodes, "links": links, "ports": self._collect_ports(nodes)}
        result, code = self._validate_and_generate(graph)

        self.assertTrue(
            result["errors"] == [], f"Unexpected errors: {result['errors']}"
        )
        self.assertIn("nn.Sequential", code)
        self.assertIn("128", code)
        self.assertIn("10", code)
        compile(code, "<test>", "exec")  # Must be valid Python

    # ========== EXAMPLE 2: With Train/Test Split ==========

    def test_with_train_test_split(self):
        """Input → TrainTestSplit → Layer → Output"""
        nodes = [
            {
                "id": "i1",
                "type": "input-data",
                "inputPorts": [],
                "outputPorts": [self._port("i1_output_0", "output", 0, "data")],
                "dataShape": "(1000, 784)",
            },
            {
                "id": "t1",
                "type": "train-test",
                "trainRatio": 0.7,
                "randomSeed": 42,
                "inputPorts": [self._port("t1_input_0", "input", 0, "data")],
                "outputPorts": [
                    self._port("t1_output_0", "output", 0, "data", subType="train"),
                    self._port("t1_output_1", "output", 1, "data", subType="test"),
                ],
            },
            {
                "id": "l1",
                "type": "layer",
                "numNeurons": 64,
                "activation": "relu",
                "inputPorts": [self._port("l1_input_0", "input", 0, "multi")],
                "outputPorts": [self._port("l1_output_0", "output", 0, "data")],
            },
            {
                "id": "o1",
                "type": "output",
                "inputPorts": [self._port("o1_input_0", "input", 0, "data")],
                "outputPorts": [self._role_port("o1_output_0", "output", 0, "loss")],
            },
        ]
        links = [
            self._link("i1_output_0", "t1_input_0", False),
            self._link("t1_output_0", "l1_input_0", True),
            self._link("l1_output_0", "o1_input_0", False),
        ]
        graph = {"nodes": nodes, "links": links, "ports": self._collect_ports(nodes)}
        result, code = self._validate_and_generate(graph)

        self.assertTrue(
            result["errors"] == [], f"Unexpected errors: {result['errors']}"
        )
        self.assertIn("split_idx", code)
        self.assertIn("0.7", code)
        compile(code, "<test>", "exec")

    # ========== EXAMPLE 3: Skip Connection (Add Node) ==========

    def test_skip_connection(self):
        """Input → Layer1 → Add ← Input (skip) → Layer2 → Output"""
        nodes = [
            {
                "id": "i1",
                "type": "input-data",
                "inputPorts": [],
                "outputPorts": [self._port("i1_output_0", "output", 0, "data")],
            },
            {
                "id": "l1",
                "type": "layer",
                "numNeurons": 64,
                "activation": "relu",
                "inputPorts": [self._port("l1_input_0", "input", 0, "multi")],
                "outputPorts": [self._port("l1_output_0", "output", 0, "data")],
            },
            {
                "id": "a1",
                "type": "add",
                "inputPorts": [
                    self._port("a1_input_0", "input", 0, "multi", subType="main")
                ],
                "outputPorts": [self._port("a1_output_0", "output", 0, "data")],
            },
            {
                "id": "l2",
                "type": "layer",
                "numNeurons": 64,
                "activation": "relu",
                "inputPorts": [self._port("l2_input_0", "input", 0, "multi")],
                "outputPorts": [self._port("l2_output_0", "output", 0, "data")],
            },
            {
                "id": "o1",
                "type": "output",
                "inputPorts": [self._port("o1_input_0", "input", 0, "data")],
                "outputPorts": [self._role_port("o1_output_0", "output", 0, "loss")],
            },
        ]
        links = [
            self._link("i1_output_0", "l1_input_0", True),
            self._link("l1_output_0", "a1_input_0", False),
            self._link("i1_output_0", "a1_input_0", False),  # Skip connection
            self._link("a1_output_0", "l2_input_0", True),
            self._link("l2_output_0", "o1_input_0", False),
        ]
        graph = {"nodes": nodes, "links": links, "ports": self._collect_ports(nodes)}
        result, code = self._validate_and_generate(graph)

        self.assertTrue(
            result["errors"] == [], f"Unexpected errors: {result['errors']}"
        )
        self.assertNotIn("nn.Sequential", code)  # Add breaks sequential
        self.assertIn("Skip connection", code)
        compile(code, "<test>", "exec")

    # ========== EXAMPLE 4: Concat ==========

    def test_concat_two_branches(self):
        """Input → Branch1(Layer) ↘ Concat → Layer → Output
        → Branch2(Layer) ↗"""
        nodes = [
            {
                "id": "i1",
                "type": "input-data",
                "inputPorts": [],
                "outputPorts": [self._port("i1_output_0", "output", 0, "data")],
            },
            {
                "id": "l1",
                "type": "layer",
                "numNeurons": 32,
                "activation": "relu",
                "inputPorts": [self._port("l1_input_0", "input", 0, "multi")],
                "outputPorts": [self._port("l1_output_0", "output", 0, "data")],
            },
            {
                "id": "l2",
                "type": "layer",
                "numNeurons": 32,
                "activation": "relu",
                "inputPorts": [self._port("l2_input_0", "input", 0, "multi")],
                "outputPorts": [self._port("l2_output_0", "output", 0, "data")],
            },
            {
                "id": "c1",
                "type": "concat",
                "axis": -1,
                "inputPorts": [self._port("c1_input_0", "input", 0, "multi")],
                "outputPorts": [self._port("c1_output_0", "output", 0, "data")],
            },
            {
                "id": "l3",
                "type": "layer",
                "numNeurons": 10,
                "activation": "sigmoid",
                "inputPorts": [self._port("l3_input_0", "input", 0, "multi")],
                "outputPorts": [self._port("l3_output_0", "output", 0, "data")],
            },
            {
                "id": "o1",
                "type": "output",
                "inputPorts": [self._port("o1_input_0", "input", 0, "data")],
                "outputPorts": [self._role_port("o1_output_0", "output", 0, "loss")],
            },
        ]
        links = [
            self._link("i1_output_0", "l1_input_0", True),
            self._link("i1_output_0", "l2_input_0", True),
            self._link("l1_output_0", "c1_input_0", False),
            self._link("l2_output_0", "c1_input_0", False),
            self._link("c1_output_0", "l3_input_0", True),
            self._link("l3_output_0", "o1_input_0", False),
        ]
        graph = {"nodes": nodes, "links": links, "ports": self._collect_ports(nodes)}
        result, code = self._validate_and_generate(graph)

        self.assertTrue(
            result["errors"] == [], f"Unexpected errors: {result['errors']}"
        )
        self.assertIn("torch.cat", code)
        compile(code, "<test>", "exec")

    # ========== EXAMPLE 5: Full Training Pipeline ==========

    def test_full_training_pipeline(self):
        """Complete pipeline with preprocessing, model, optimizer, and visualization."""
        nodes = [
            {
                "id": "i1",
                "type": "input-data",
                "inputPorts": [],
                "outputPorts": [self._port("i1_output_0", "output", 0, "data")],
                "dataShape": "(1000, 784)",
            },
            {
                "id": "n1",
                "type": "normalize",
                "method": "standard",
                "inputPorts": [self._port("n1_input_0", "input", 0, "data")],
                "outputPorts": [self._port("n1_output_0", "output", 0, "data")],
            },
            {
                "id": "t1",
                "type": "train-test",
                "trainRatio": 0.8,
                "randomSeed": 42,
                "inputPorts": [self._port("t1_input_0", "input", 0, "data")],
                "outputPorts": [
                    self._port("t1_output_0", "output", 0, "data", subType="train"),
                    self._port("t1_output_1", "output", 1, "data", subType="test"),
                ],
            },
            {
                "id": "l1",
                "type": "layer",
                "numNeurons": 256,
                "activation": "relu",
                "inputPorts": [self._port("l1_input_0", "input", 0, "multi")],
                "outputPorts": [self._port("l1_output_0", "output", 0, "data")],
            },
            {
                "id": "d1",
                "type": "dropout",
                "rate": 0.3,
                "inputPorts": [self._port("d1_input_0", "input", 0, "data")],
                "outputPorts": [self._port("d1_output_0", "output", 0, "data")],
            },
            {
                "id": "l2",
                "type": "layer",
                "numNeurons": 10,
                "activation": "sigmoid",
                "inputPorts": [self._port("l2_input_0", "input", 0, "multi")],
                "outputPorts": [self._port("l2_output_0", "output", 0, "data")],
            },
            {
                "id": "o1",
                "type": "output",
                "inputPorts": [self._port("o1_input_0", "input", 0, "data")],
                "outputPorts": [
                    self._role_port("o1_output_0", "output", 0, "loss"),
                    self._role_port("o1_output_1", "output", 1, "prediction"),
                    self._role_port("o1_output_2", "output", 2, "evaluation"),
                ],
            },
            {
                "id": "opt1",
                "type": "optimizer",
                "inputPorts": [
                    self._role_port("opt1_input_0", "input", 0, "loss"),
                    self._role_port("opt1_input_1", "input", 1, "labels"),
                ],
                "outputPorts": [],
                "lossType": "cross_entropy",
                "optimizerType": "adam",
                "learningRate": 0.001,
                "epochs": 20,
                "batchSize": 64,
                "shuffle": True,
                "gradientClip": 1.0,
                "earlyStopping": True,
                "earlyStoppingPatience": 5,
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
            self._link("i1_output_0", "n1_input_0", False),
            self._link("n1_output_0", "t1_input_0", False),
            self._link("t1_output_0", "l1_input_0", True),
            self._link("l1_output_0", "d1_input_0", False),
            self._link("d1_output_0", "l2_input_0", True),
            self._link("l2_output_0", "o1_input_0", False),
            self._link("o1_output_0", "opt1_input_0", False),  # Loss port
            self._link("t1_output_0", "opt1_input_1", False),  # Labels port
        ]
        graph = {"nodes": nodes, "links": links, "ports": self._collect_ports(nodes)}
        result, code = self._validate_and_generate(graph)

        self.assertTrue(
            result["errors"] == [], f"Unexpected errors: {result['errors']}"
        )
        self.assertIn("class SketchNetModel", code)
        self.assertIn("def load_data():", code)
        self.assertIn("def train_model(", code)
        self.assertIn("def visualize(", code)
        self.assertIn("Standard", code)
        self.assertIn("Early stopping", code)
        self.assertIn("torch.nn.utils.clip_grad_norm_", code)
        compile(code, "<test>", "exec")

    # ========== HELPERS ==========

    def _port(self, id, type, index, kind, subType=None, shape=None):
        return {
            "id": id,
            "type": type,
            "index": index,
            "subType": subType,
            "shape": shape,
            "portKind": kind,
        }

    def _role_port(self, id, type, index, role):
        return {
            "id": id,
            "type": type,
            "index": index,
            "subType": None,
            "shape": None,
            "portKind": "role",
            "role": role,
        }

    def _link(self, from_id, to_id, has_weight, weight=0):
        return {
            "from": from_id,
            "to": to_id,
            "weight": weight,
            "weightShape": None,
            "hasWeight": has_weight,
        }

    def _collect_ports(self, nodes):
        ports = []
        for n in nodes:
            for p in n.get("inputPorts", []):
                ports.append(p)
            for p in n.get("outputPorts", []):
                ports.append(p)
        return ports
