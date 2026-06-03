from django.test import SimpleTestCase
from sketchmod.codegen.validator import GraphValidator

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


class ValidatorTest(SimpleTestCase):
    def test_validate_returns_errors_and_warnings(self):
        validator = GraphValidator(SIMPLE_GRAPH)
        result = validator.validate()
        self.assertIn("errors", result)
        self.assertIn("warnings", result)
        self.assertIn("isValid", result)

    def test_missing_optimizer_error(self):
        validator = GraphValidator(SIMPLE_GRAPH)
        result = validator.validate()
        errors = result["errors"]
        self.assertTrue(
            any("Optimizer node is required" in e["message"] for e in errors)
        )

    def test_missing_input_data_error(self):
        graph = {
            "nodes": [
                {
                    "id": "output-main",
                    "type": "output",
                    "x": 0,
                    "y": 0,
                    "inputPorts": [],
                    "outputPorts": [],
                    "numInputs": 0,
                    "numOutputs": 0,
                    "bias": 0,
                    "hasBias": False,
                    "paramInputs": [],
                    "paramOutputs": [],
                    "numParamInputs": 0,
                    "numParamOutputs": 0,
                }
            ],
            "links": [],
            "nodeCounter": 1,
        }
        validator = GraphValidator(graph)
        result = validator.validate()
        self.assertTrue(
            any("Missing Input Data node" in e["message"] for e in result["errors"])
        )

    def test_link_weight_zero_warning(self):
        graph = {
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
                },
            ],
            "links": [
                {
                    "from": "input-main_output_0",
                    "to": "l1_input_0",
                    "weight": 0,
                    "weightShape": None,
                    "hasWeight": True,
                }
            ],
            "nodeCounter": 2,
        }
        validator = GraphValidator(graph)
        result = validator.validate()
        self.assertTrue(
            any("Link weight is 0" in w["message"] for w in result["warnings"])
        )
