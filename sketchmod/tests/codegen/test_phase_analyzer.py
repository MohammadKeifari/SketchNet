from django.test import SimpleTestCase
from sketchmod.codegen.graph import parse_graph
from sketchmod.codegen.phase_analyzer import analyze_phases, highlight_path

SIMPLE_GRAPH = {
    "nodes": [
        {
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
        },
        {
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


class PhaseAnalyzerTest(SimpleTestCase):
    def test_analyze_phases_returns_expected_keys(self):
        graph = parse_graph(SIMPLE_GRAPH)
        flow = analyze_phases(graph)
        self.assertIn("preprocessing_order", flow)
        self.assertIn("train_order", flow)
        self.assertIn("eval_order", flow)
        self.assertIn("optimizer", flow)
        self.assertIn("visualizations", flow)

    def test_input_data_in_preprocessing(self):
        graph = parse_graph(SIMPLE_GRAPH)
        flow = analyze_phases(graph)
        self.assertIn("input-main", flow["preprocessing_order"])

    def test_optimizer_is_none_when_missing(self):
        graph = parse_graph(SIMPLE_GRAPH)
        flow = analyze_phases(graph)
        self.assertIsNone(flow["optimizer"])

    def test_highlight_path_returns_dict(self):
        graph = parse_graph(SIMPLE_GRAPH)
        result = highlight_path(SIMPLE_GRAPH, "preprocessing")
        self.assertIn("nodes", result)
        self.assertIn("links", result)
        self.assertIsInstance(result["nodes"], list)
