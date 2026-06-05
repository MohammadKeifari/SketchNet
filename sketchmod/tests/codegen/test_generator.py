from django.test import SimpleTestCase
from sketchmod.codegen.generator import CodeGenerator

GRAPH_WITH_OPTIMIZER = {
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
            "dataShape": "(100, 2)",
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
                }
            ],
            "numInputs": 2,
            "numOutputs": 1,
            "bias": 0,
            "hasBias": False,
            "paramInputs": [],
            "paramOutputs": [],
            "numParamInputs": 0,
            "numParamOutputs": 0,
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
            "numNeurons": 32,
        },
        {
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
            "lossType": "mse",
            "optimizerType": "adam",
            "learningRate": 0.001,
            "adamBeta1": 0.9,
            "adamBeta2": 0.999,
            "adamEpsilon": 1e-8,
            "sgdMomentum": 0.9,
            "weightDecay": 0,
            "nesterov": False,
            "epochs": 5,
            "batchSize": 16,
            "shuffle": True,
            "gradientClip": None,
            "earlyStopping": False,
            "earlyStoppingPatience": 10,
        },
    ],
    "links": [
        {
            "from": "input-main_output_0",
            "to": "l1_input_0",
            "weight": 1.0,
            "weightShape": None,
            "hasWeight": True,
        },
        {
            "from": "l1_output_0",
            "to": "output-main_input_0",
            "weight": 0,
            "weightShape": None,
            "hasWeight": False,
        },
        {
            "from": "output-main_output_0",
            "to": "o1_input_0",
            "weight": 0,
            "weightShape": None,
            "hasWeight": False,
        },
        {
            "from": "input-main_output_0",
            "to": "o1_input_1",
            "weight": 0,
            "weightShape": None,
            "hasWeight": False,
        },
    ],
    "nodeCounter": 4,
}


class GeneratorTest(SimpleTestCase):
    def test_generate_returns_string(self):
        """Verify generate returns string."""
        gen = CodeGenerator(GRAPH_WITH_OPTIMIZER)
        code = gen.generate()
        self.assertIsInstance(code, str)
        self.assertTrue(len(code) > 0)

    def test_generated_code_has_imports(self):
        """Verify generated code has imports."""
        gen = CodeGenerator(GRAPH_WITH_OPTIMIZER)
        code = gen.generate()
        self.assertIn("import torch", code)
        self.assertIn("import torch.nn as nn", code)

    def test_generated_code_has_load_and_preprocess(self):
        """Verify generated code has load and preprocess."""
        gen = CodeGenerator(GRAPH_WITH_OPTIMIZER)
        code = gen.generate()
        self.assertIn("def load_and_preprocess():", code)

    def test_generated_code_has_model_class(self):
        """Verify generated code has model class."""
        gen = CodeGenerator(GRAPH_WITH_OPTIMIZER)
        code = gen.generate()
        self.assertIn("class Model(nn.Module):", code)

    def test_generated_code_has_train_model(self):
        """Verify generated code has train model."""
        gen = CodeGenerator(GRAPH_WITH_OPTIMIZER)
        code = gen.generate()
        self.assertIn("def train_model(", code)

    def test_generated_code_has_main_block(self):
        """Verify generated code has main block."""
        gen = CodeGenerator(GRAPH_WITH_OPTIMIZER)
        code = gen.generate()
        self.assertIn("if __name__ == '__main__':", code)
