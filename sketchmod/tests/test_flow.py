from django.test import SimpleTestCase
from sketchmod.codegen.flow import FlowAnalyzer


class FlowAnalyzerTests(SimpleTestCase):

    def _make_graph(self, nodes, links, ports=None):
        if ports is None:
            ports = []
            for n in nodes:
                for p in n.get("inputPorts", []):
                    ports.append(p)
                for p in n.get("outputPorts", []):
                    ports.append(p)
        return {"nodes": nodes, "links": links, "ports": ports}

    def _analyze(self, nodes, links):
        graph = self._make_graph(nodes, links)
        analyzer = FlowAnalyzer(graph)
        return analyzer.analyze()

    # ========== EMPTY GRAPH ==========

    def test_empty_graph(self):
        result = self._analyze([], [])
        self.assertEqual(result["preprocessing"]["nodes"], [])
        self.assertEqual(result["model_nodes"], [])
        self.assertIsNone(result["output_node"])

    # ========== SIMPLE CHAIN ==========

    def test_simple_chain(self):
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
                "id": "o1",
                "type": "output",
                "inputPorts": [
                    self._port("o1_input_0", "input", 0, "data", subType="train"),
                    self._port("o1_input_1", "input", 1, "data", subType="test"),
                ],
                "outputPorts": [
                    self._role_port("o1_output_0", "output", 0, "loss"),
                    self._role_port("o1_output_1", "output", 1, "prediction"),
                    self._role_port("o1_output_2", "output", 2, "evaluation"),
                ],
            },
        ]
        links = [
            self._link("i1_output_0", "l1_input_0"),
            self._link("l1_output_0", "o1_input_0"),
            self._link("l1_output_0", "o1_input_1"),
        ]
        result = self._analyze(nodes, links)

        # Preprocessing: InputData
        self.assertEqual(len(result["preprocessing"]["nodes"]), 1)
        self.assertEqual(result["preprocessing"]["nodes"][0]["id"], "i1")

        # Model: Layer + Output
        self.assertEqual(len(result["model_nodes"]), 1)
        self.assertEqual(result["model_nodes"][0]["id"], "l1")

        # Sequential
        self.assertTrue(result["is_sequential"])

        # Output node
        self.assertIsNotNone(result["output_node"])
        self.assertEqual(result["output_node"]["id"], "o1")

    # ========== WITH PREPROCESSING ==========

    def test_with_preprocessing(self):
        nodes = [
            {
                "id": "i1",
                "type": "input-data",
                "inputPorts": [],
                "outputPorts": [self._port("i1_output_0", "output", 0, "data")],
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
                "numNeurons": 10,
                "activation": "relu",
                "inputPorts": [self._port("l1_input_0", "input", 0, "multi")],
                "outputPorts": [self._port("l1_output_0", "output", 0, "data")],
            },
            {
                "id": "o1",
                "type": "output",
                "inputPorts": [
                    self._port("o1_input_0", "input", 0, "data", subType="train"),
                    self._port("o1_input_1", "input", 1, "data", subType="test"),
                ],
                "outputPorts": [
                    self._role_port("o1_output_0", "output", 0, "loss"),
                    self._role_port("o1_output_1", "output", 1, "prediction"),
                    self._role_port("o1_output_2", "output", 2, "evaluation"),
                ],
            },
        ]
        links = [
            self._link("i1_output_0", "n1_input_0"),
            self._link("n1_output_0", "t1_input_0"),
            self._link("t1_output_0", "l1_input_0"),
            self._link("l1_output_0", "o1_input_0"),
            self._link("l1_output_0", "o1_input_1"),
        ]
        result = self._analyze(nodes, links)

        # Preprocessing: InputData + Normalize + TrainTest
        self.assertEqual(len(result["preprocessing"]["nodes"]), 3)
        pre_ids = [n["id"] for n in result["preprocessing"]["nodes"]]
        self.assertEqual(pre_ids, ["i1", "n1", "t1"])

        # Model nodes
        self.assertEqual(len(result["model_nodes"]), 1)

    # ========== NON-SEQUENTIAL ==========

    def test_add_breaks_sequential(self):
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
                "inputPorts": [self._port("a1_input_0", "input", 0, "multi")],
                "outputPorts": [self._port("a1_output_0", "output", 0, "data")],
            },
            {
                "id": "o1",
                "type": "output",
                "inputPorts": [
                    self._port("o1_input_0", "input", 0, "data", subType="train"),
                    self._port("o1_input_1", "input", 1, "data", subType="test"),
                ],
                "outputPorts": [self._role_port("o1_output_0", "output", 0, "loss")],
            },
        ]
        links = [
            self._link("i1_output_0", "l1_input_0"),
            self._link("l1_output_0", "a1_input_0"),
            self._link("i1_output_0", "a1_input_0"),  # Skip
            self._link("a1_output_0", "o1_input_0"),
            self._link("a1_output_0", "o1_input_1"),
        ]
        result = self._analyze(nodes, links)
        self.assertFalse(result["is_sequential"])

    # ========== HELPERS ==========

    def _port(self, id, type, index, kind, subType=None):
        return {
            "id": id,
            "type": type,
            "index": index,
            "subType": subType,
            "portKind": kind,
        }

    def _role_port(self, id, type, index, role):
        return {
            "id": id,
            "type": type,
            "index": index,
            "subType": None,
            "portKind": "role",
            "role": role,
        }

    def _link(self, from_id, to_id):
        return {
            "from": from_id,
            "to": to_id,
            "weight": 0,
            "weightShape": None,
            "hasWeight": False,
        }
