from django.test import SimpleTestCase
from sketchmod.codegen.writer import CodeWriter
from sketchmod.codegen.translators import (
    LayerTranslator,
    NeuronTranslator,
    FlattenTranslator,
    DropoutTranslator,
    BatchNormTranslator,
    Conv2DTranslator,
    AddTranslator,
    ConcatTranslator,
    NormalizeTranslator,
    TrainTestSplitTranslator,
    OutputTranslator,
    OptimizerTranslator,
)
from unittest.mock import Mock


class TranslatorTests(SimpleTestCase):

    def _make_node(self, id, type, **kwargs):
        node = {"id": id, "type": type}
        node.update(kwargs)
        return node

    def _make_gen(self):
        gen = Mock()
        gen.get_links_to.return_value = []
        gen._port_node_id.return_value = None
        return gen

    # ========== LAYER ==========

    def test_layer_init_sequential(self):
        w = CodeWriter()
        node = self._make_node("l1", "layer", numNeurons=128, activation="relu")
        t = LayerTranslator(node, None)
        t.init_code(w, is_sequential=True)
        self.assertIn("nn.Linear(in_features, 128)", str(w))

    def test_layer_init_custom(self):
        w = CodeWriter()
        node = self._make_node("l1", "layer", numNeurons=64, activation="sigmoid")
        t = LayerTranslator(node, None)
        t.init_code(w, is_sequential=False)
        self.assertIn("self.l1 = nn.Linear(in_features, 64)", str(w))

    def test_layer_forward(self):
        w = CodeWriter()
        node = self._make_node("l1", "layer", numNeurons=64, activation="relu")
        t = LayerTranslator(node, None)
        out = t.forward_code(w, "x", {})
        self.assertEqual(out, "x_l1")
        self.assertIn("x_l1 = self.l1(x)", str(w))
        self.assertIn("torch.relu", str(w))

    def test_layer_forward_no_activation(self):
        w = CodeWriter()
        node = self._make_node("l1", "layer", numNeurons=64, activation="linear")
        t = LayerTranslator(node, None)
        t.forward_code(w, "x", {})
        self.assertNotIn("torch.relu", str(w))

    # ========== NEURON ==========

    def test_neuron_init(self):
        w = CodeWriter()
        node = self._make_node("n1", "neuron", activation="tanh")
        t = NeuronTranslator(node, None)
        t.init_code(w, is_sequential=False)
        self.assertIn("self.n1 = nn.Linear(in_features, 1)", str(w))

    # ========== FLATTEN ==========

    def test_flatten_init(self):
        w = CodeWriter()
        node = self._make_node("f1", "flatten")
        t = FlattenTranslator(node, None)
        t.init_code(w, is_sequential=True)
        self.assertIn("nn.Flatten()", str(w))

    # ========== DROPOUT ==========

    def test_dropout_init(self):
        w = CodeWriter()
        node = self._make_node("d1", "dropout", rate=0.3)
        t = DropoutTranslator(node, None)
        t.init_code(w, is_sequential=False)
        self.assertIn("nn.Dropout(0.3)", str(w))

    # ========== BATCHNORM ==========

    def test_batchnorm_init(self):
        w = CodeWriter()
        node = self._make_node("b1", "batchnorm")
        t = BatchNormTranslator(node, None)
        t.init_code(w, is_sequential=True)
        self.assertIn("nn.BatchNorm1d", str(w))

    # ========== CONV2D ==========

    def test_conv2d_init(self):
        w = CodeWriter()
        node = self._make_node(
            "c1", "conv2d", filters=32, kernelSize=3, stride=1, padding=0
        )
        t = Conv2DTranslator(node, None)
        t.init_code(w, is_sequential=False)
        self.assertIn("nn.Conv2d", str(w))
        self.assertIn("kernel_size=3", str(w))

    # ========== ADD ==========

    def test_add_forward(self):
        w = CodeWriter()
        node = self._make_node("a1", "add")
        gen = self._make_gen()
        gen.get_links_to.return_value = [
            {"from": "l1_output_0"},
            {"from": "l2_output_0"},
        ]
        t = AddTranslator(node, gen)
        out = t.forward_code(w, "x", {"l1": "x_l1", "l2": "x_l2"})
        self.assertIn("+", str(w))
        self.assertIn("Skip connection", str(w))

    # ========== CONCAT ==========

    def test_concat_forward(self):
        w = CodeWriter()
        node = self._make_node("c1", "concat", axis=-1)
        gen = self._make_gen()
        gen.get_links_to.return_value = [
            {"from": "l1_output_0"},
            {"from": "l2_output_0"},
        ]
        t = ConcatTranslator(node, gen)
        t.forward_code(w, "x", {"l1": "x_l1", "l2": "x_l2"})
        self.assertIn("torch.cat", str(w))

    # ========== NORMALIZE ==========

    def test_normalize_standard(self):
        w = CodeWriter()
        node = self._make_node("n1", "normalize", method="standard")
        t = NormalizeTranslator(node, None)
        t.data_code(w, None)
        code = str(w)
        self.assertIn("mean =", code)
        self.assertIn("std =", code)

    def test_normalize_minmax(self):
        w = CodeWriter()
        node = self._make_node("n1", "normalize", method="minmax")
        t = NormalizeTranslator(node, None)
        t.data_code(w, None)
        code = str(w)
        self.assertIn("x_min =", code)
        self.assertIn("x_max =", code)

    # ========== TRAIN/TEST SPLIT ==========

    def test_train_test_split(self):
        w = CodeWriter()
        node = self._make_node("t1", "train-test", trainRatio=0.75, randomSeed=99)
        t = TrainTestSplitTranslator(node, None)
        t.data_code(w, None)
        code = str(w)
        self.assertIn("0.75", code)
        self.assertIn("torch.manual_seed(99)", code)

    # ========== OUTPUT ==========

    def test_output_forward(self):
        w = CodeWriter()
        node = self._make_node("o1", "output")
        t = OutputTranslator(node, None)
        out = t.forward_code(w, "x_l2", {})
        self.assertIn("return x_l2", str(w))

    # ========== OPTIMIZER ==========

    def test_optimizer_adam(self):
        w = CodeWriter()
        node = self._make_node(
            "opt1",
            "optimizer",
            optimizerType="adam",
            learningRate=0.001,
            lossType="cross_entropy",
        )
        t = OptimizerTranslator(node, None)
        t.optimizer_code(w)
        code = str(w)
        self.assertIn("optim.Adam", code)
        self.assertIn("lr=0.001", code)
        self.assertIn("nn.CrossEntropyLoss()", code)

    def test_optimizer_sgd(self):
        w = CodeWriter()
        node = self._make_node(
            "opt1",
            "optimizer",
            optimizerType="sgd",
            learningRate=0.01,
            lossType="mse",
            sgdMomentum=0.8,
            weightDecay=0.001,
            nesterov=True,
        )
        t = OptimizerTranslator(node, None)
        t.optimizer_code(w)
        code = str(w)
        self.assertIn("optim.SGD", code)
        self.assertIn("momentum=0.8", code)
        self.assertIn("nesterov=True", code)
        self.assertIn("nn.MSELoss()", code)
