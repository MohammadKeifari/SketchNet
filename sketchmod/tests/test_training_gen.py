from django.test import SimpleTestCase
from sketchmod.codegen.generator import CodeGenerator
from sketchmod.codegen.training import TrainingGenerator


class TrainingGeneratorTests(SimpleTestCase):

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
        train_gen = TrainingGenerator(gen)
        return "\n".join(train_gen.generate())

    def _make_optimizer(self, **kwargs):
        defaults = {
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
            "batchSize": 32,
            "shuffle": True,
            "gradientClip": None,
            "earlyStopping": False,
            "earlyStoppingPatience": 10,
            "adamBeta1": 0.9,
            "adamBeta2": 0.999,
            "adamEpsilon": 1e-8,
            "sgdMomentum": 0.9,
            "weightDecay": 0,
            "nesterov": False,
        }
        defaults.update(kwargs)
        return defaults

    def _make_basic_graph(self, optimizer=None):
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
                "numNeurons": 10,
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
        if optimizer:
            nodes.append(optimizer)
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
        return nodes, links

    # ========== OPTIMIZER CONFIG ==========

    def test_adam_optimizer(self):
        opt = self._make_optimizer(optimizerType="adam", learningRate=0.001)
        nodes, links = self._make_basic_graph(opt)
        code = self._generate(nodes, links)
        self.assertIn("optim.Adam", code)
        self.assertIn("lr=0.001", code)
        self.assertIn("betas=(0.9, 0.999)", code)

    def test_adamw_optimizer(self):
        opt = self._make_optimizer(
            optimizerType="adamw", learningRate=0.0001, weightDecay=0.01
        )
        nodes, links = self._make_basic_graph(opt)
        code = self._generate(nodes, links)
        self.assertIn("optim.AdamW", code)
        self.assertIn("weight_decay=0.01", code)

    def test_sgd_optimizer(self):
        opt = self._make_optimizer(
            optimizerType="sgd",
            learningRate=0.01,
            sgdMomentum=0.9,
            weightDecay=0.0001,
            nesterov=True,
        )
        nodes, links = self._make_basic_graph(opt)
        code = self._generate(nodes, links)
        self.assertIn("optim.SGD", code)
        self.assertIn("momentum=0.9", code)
        self.assertIn("nesterov=True", code)

    # ========== LOSS FUNCTIONS ==========

    def test_cross_entropy_loss(self):
        opt = self._make_optimizer(lossType="cross_entropy")
        nodes, links = self._make_basic_graph(opt)
        code = self._generate(nodes, links)
        self.assertIn("nn.CrossEntropyLoss()", code)

    def test_mse_loss(self):
        opt = self._make_optimizer(lossType="mse")
        nodes, links = self._make_basic_graph(opt)
        code = self._generate(nodes, links)
        self.assertIn("nn.MSELoss()", code)

    # ========== TRAINING LOOP ==========

    def test_basic_training_loop(self):
        opt = self._make_optimizer(epochs=25)
        nodes, links = self._make_basic_graph(opt)
        code = self._generate(nodes, links)
        self.assertIn("for epoch in range(25):", code)
        self.assertIn("model.train()", code)
        self.assertIn("optimizer.zero_grad()", code)
        self.assertIn("loss.backward()", code)
        self.assertIn("optimizer.step()", code)

    def test_gradient_clipping(self):
        opt = self._make_optimizer(gradientClip=1.0)
        nodes, links = self._make_basic_graph(opt)
        code = self._generate(nodes, links)
        self.assertIn("clip_grad_norm_", code)
        self.assertIn("1.0", code)

    def test_early_stopping(self):
        opt = self._make_optimizer(earlyStopping=True, earlyStoppingPatience=5)
        nodes, links = self._make_basic_graph(opt)
        code = self._generate(nodes, links)
        self.assertIn("best_val_loss", code)
        self.assertIn("patience_counter", code)
        self.assertIn("Early stopping", code)

    def test_no_early_stopping_by_default(self):
        opt = self._make_optimizer(earlyStopping=False)
        nodes, links = self._make_basic_graph(opt)
        code = self._generate(nodes, links)
        self.assertNotIn("best_val_loss", code)

    # ========== MAIN BLOCK ==========

    def test_main_block(self):
        opt = self._make_optimizer()
        nodes, links = self._make_basic_graph(opt)
        code = self._generate(nodes, links)
        self.assertIn('if __name__ == "__main__":', code)
        self.assertIn("model = SketchNetModel()", code)
        self.assertIn("load_data()", code)

    def test_evaluation_code(self):
        opt = self._make_optimizer()
        nodes, links = self._make_basic_graph(opt)
        code = self._generate(nodes, links)
        self.assertIn("Accuracy", code)
        self.assertIn("torch.max", code)

    # ========== NO OPTIMIZER ==========

    def test_no_optimizer_inference_only(self):
        nodes, links = self._make_basic_graph(optimizer=None)
        code = self._generate(nodes, links)
        self.assertIn("inference only", code)
        self.assertNotIn("train_model", code)
