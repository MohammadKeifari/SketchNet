"""
Comprehensive tests for every translator in translators.py.
Covers data, init, and forward placements.
"""

import unittest
from sketchmod.codegen.graph import Graph, Node, Port, Link
from sketchmod.codegen.writer import CodeWriter
from sketchmod.codegen.translators import get_translator


class BaseTranslatorTest(unittest.TestCase):
    """Common helpers for building test graphs and running translators."""

    @staticmethod
    def _make_port(
        port_id,
        node_id,
        port_type,
        index,
        activation_phases=None,
        port_kind="data",
        role=None,
        sub_type=None,
        shape=None,
    ):
        return Port(
            id=port_id,
            node_id=node_id,
            type=port_type,
            index=index,
            activation_phases=activation_phases or [],
            port_kind=port_kind,
            role=role,
            sub_type=sub_type,
            shape=shape,
        )

    def _graph_with_nodes(self, node_list, link_list):
        graph = Graph()
        for n in node_list:
            graph.nodes[n.id] = n
            for p in n.inputs + n.outputs + n.paramInputs + n.paramOutputs:
                graph.ports[p.id] = p
        graph.links = link_list
        return graph

    def _run_translator(
        self,
        node,
        graph,
        var_map=None,
        phase="preprocessing",
        placement="data",
        is_first=False,
    ):
        if var_map is None:
            var_map = {}
        w = CodeWriter()
        t = get_translator(node, graph, var_map)
        t.generate(w, phase, placement, is_first=is_first)
        return str(w), var_map


# ----------------------------------------------------------------
# InputData
# ----------------------------------------------------------------
class InputDataTranslatorTest(BaseTranslatorTest):
    def test_random_data_fallback(self):
        node = Node(id="inp", type="input-data")
        node.outputs = [
            self._make_port("inp_out", "inp", "output", 0, ["preprocessing"])
        ]
        graph = self._graph_with_nodes([node], [])
        code, vm = self._run_translator(node, graph)
        self.assertIn("raw_data = torch.randn(200, 10)", code)
        self.assertEqual(vm["inp"], "raw_data")

    def test_manual_shape(self):
        node = Node(id="inp", type="input-data", properties={"dataShape": "(64, 3)"})
        node.outputs = [
            self._make_port("inp_out", "inp", "output", 0, ["preprocessing"])
        ]
        graph = self._graph_with_nodes([node], [])
        code, vm = self._run_translator(node, graph)
        self.assertIn("raw_data = torch.randn(64, 3)", code)

    def test_csv_dataset(self):
        node = Node(
            id="inp",
            type="input-data",
            properties={
                "datasetId": "ds1",
                "datasetFile": "data.csv",
                "datasetFormat": "csv",
            },
        )
        node.outputs = [
            self._make_port("inp_out", "inp", "output", 0, ["preprocessing"])
        ]
        graph = self._graph_with_nodes([node], [])
        code, vm = self._run_translator(node, graph)
        self.assertIn("pd.read_csv('data/data.csv')", code)


# ----------------------------------------------------------------
# ColumnSelect
# ----------------------------------------------------------------
class ColumnSelectTranslatorTest(BaseTranslatorTest):
    def test_data_with_selected_columns(self):
        node = Node(
            id="col", type="column-select", properties={"selectedColumns": [0, 1]}
        )
        node.inputs = [self._make_port("col_in", "col", "input", 0, ["preprocessing"])]
        node.outputs = [
            self._make_port("col_out", "col", "output", 0, ["preprocessing"])
        ]
        src = Node(id="src", type="input-data")
        src.outputs = [
            self._make_port("src_out", "src", "output", 0, ["preprocessing"])
        ]
        links = [Link(id_from="src_out", id_to="col_in")]
        graph = self._graph_with_nodes([node, src], links)
        code, vm = self._run_translator(
            node, graph, var_map={"src": "raw_data", "src_out": "raw_data"}
        )
        self.assertIn("col_out = raw_data[:, [0, 1]]", code)
        self.assertEqual(vm["col"], "col_out")

    def test_forward_placement(self):
        node = Node(id="col", type="column-select", properties={"selectedColumns": [0]})
        node.inputs = [self._make_port("col_in", "col", "input", 0, ["training"])]
        node.outputs = [self._make_port("col_out", "col", "output", 0, ["training"])]
        src = Node(id="src", type="layer")
        src.outputs = [self._make_port("src_out", "src", "output", 0, ["training"])]
        links = [Link(id_from="src_out", id_to="col_in")]
        graph = self._graph_with_nodes([node, src], links)
        code, vm = self._run_translator(node, graph, placement="forward")
        self.assertIn("x = outputs.get('src', inputs_dict.get('src'))", code)
        self.assertIn("x = x[:, [0]]", code)
        self.assertIn("outputs['col'] = x", code)


# ----------------------------------------------------------------
# RowSelect
# ----------------------------------------------------------------
class RowSelectTranslatorTest(BaseTranslatorTest):
    def _row_node(self, method, value="100", seed=42):
        return Node(
            id="row",
            type="row-select",
            properties={"method": method, "value": value, "randomSeed": seed},
        )

    def _row_graph(self):
        node = self._row_node("first-n")
        node.inputs = [self._make_port("row_in", "row", "input", 0, ["preprocessing"])]
        node.outputs = [
            self._make_port("row_out", "row", "output", 0, ["preprocessing"])
        ]
        src = Node(id="src", type="input-data")
        src.outputs = [
            self._make_port("src_out", "src", "output", 0, ["preprocessing"])
        ]
        links = [Link(id_from="src_out", id_to="row_in")]
        graph = self._graph_with_nodes([node, src], links)
        return node, graph

    def test_first_n(self):
        node, graph = self._row_graph()
        code, vm = self._run_translator(
            node, graph, var_map={"src": "data", "src_out": "data"}
        )
        self.assertIn("row_out = data[:100]", code)

    def test_random(self):
        node = self._row_node("random")
        node.inputs = [self._make_port("row_in", "row", "input", 0, ["preprocessing"])]
        node.outputs = [
            self._make_port("row_out", "row", "output", 0, ["preprocessing"])
        ]
        src = Node(id="src", type="input-data")
        src.outputs = [
            self._make_port("src_out", "src", "output", 0, ["preprocessing"])
        ]
        links = [Link(id_from="src_out", id_to="row_in")]
        graph = self._graph_with_nodes([node, src], links)
        code, vm = self._run_translator(
            node, graph, var_map={"src": "data", "src_out": "data"}
        )
        self.assertIn("perm = torch.randperm(data.size(0)", code)
        self.assertIn("row_out = data[perm[:100]]", code)


# ----------------------------------------------------------------
# Normalize
# ----------------------------------------------------------------
class NormalizeTranslatorTest(BaseTranslatorTest):
    def test_standard_no_param(self):
        node = Node(id="norm", type="normalize", properties={"method": "standard"})
        node.inputs = [
            self._make_port("norm_in", "norm", "input", 0, ["preprocessing"])
        ]
        node.outputs = [
            self._make_port("norm_out", "norm", "output", 0, ["preprocessing"])
        ]
        src = Node(id="src", type="input-data")
        src.outputs = [
            self._make_port("src_out", "src", "output", 0, ["preprocessing"])
        ]
        links = [Link(id_from="src_out", id_to="norm_in")]
        graph = self._graph_with_nodes([node, src], links)
        code, vm = self._run_translator(
            node, graph, var_map={"src": "X", "src_out": "X"}
        )
        self.assertIn("mean = X.mean(dim=0, keepdim=True)", code)
        self.assertIn("(X - mean) / std", code)

    def test_param_sharing(self):
        node = Node(id="norm2", type="normalize", properties={"method": "standard"})
        node.inputs = [
            self._make_port("norm2_in", "norm2", "input", 0, ["preprocessing"])
        ]
        node.outputs = [
            self._make_port("norm2_out", "norm2", "output", 0, ["preprocessing"])
        ]
        node.paramInputs = [
            self._make_port(
                "norm2_pin", "norm2", "input", 0, ["preprocessing"], port_kind="param"
            )
        ]
        src = Node(id="src", type="input-data")
        src.outputs = [
            self._make_port("src_out", "src", "output", 0, ["preprocessing"])
        ]
        links = [Link(id_from="src_out", id_to="norm2_in")]
        # Simulate a param link from a previous normalizer
        param_src = Node(id="norm1", type="normalize")
        param_src.paramOutputs = [
            self._make_port(
                "norm1_pout", "norm1", "output", 0, ["preprocessing"], port_kind="param"
            )
        ]
        links.append(Link(id_from="norm1_pout", id_to="norm2_pin"))
        graph = self._graph_with_nodes([node, src, param_src], links)
        var_map = {
            "src": "X",
            "src_out": "X",
            "norm1_pout_mean": "m",
            "norm1_pout_std": "s",
        }
        code, vm = self._run_translator(node, graph, var_map=var_map)
        self.assertIn("(X - m) / (s + 1e-8)", code)


# ----------------------------------------------------------------
# Neuron / Layer
# ----------------------------------------------------------------
class NeuronTranslatorTest(BaseTranslatorTest):
    def test_init_code(self):
        node = Node(id="n", type="neuron", properties={"activation": "relu"})
        node.inputs = [self._make_port("n_in", "n", "input", 0, ["training"])]
        # Need weight_shape on link for _guess_in_features
        src = Node(id="src", type="input-data")
        src.outputs = [self._make_port("src_out", "src", "output", 0, ["training"])]
        links = [
            Link(
                id_from="src_out",
                id_to="n_in",
                weight_shape={"shape": [1, 3], "dtype": "float32"},
                has_weight=True,
            )
        ]
        graph = self._graph_with_nodes([node, src], links)
        code, vm = self._run_translator(node, graph, placement="init")
        self.assertIn("self.fc_n = nn.Linear(3, 1)", code)

    def test_forward_first_with_multi_source(self):
        node = Node(id="n", type="neuron", properties={"activation": "relu"})
        node.inputs = [
            self._make_port("n_in", "n", "input", 0, ["training", "evaluation"])
        ]
        src1 = Node(id="src1", type="normalize")
        src2 = Node(id="src2", type="normalize")
        src1.outputs = [self._make_port("s1_out", "src1", "output", 0, ["training"])]
        src2.outputs = [self._make_port("s2_out", "src2", "output", 0, ["evaluation"])]
        links = [
            Link(id_from="s1_out", id_to="n_in"),
            Link(id_from="s2_out", id_to="n_in"),
        ]
        graph = self._graph_with_nodes([node, src1, src2], links)
        code, vm = self._run_translator(node, graph, placement="forward", is_first=True)
        self.assertIn("inputs_dict.get('src1', inputs_dict.get('src2'))", code)
        self.assertIn("x = torch.relu(x)", code)

    def test_forward_not_first(self):
        node = Node(id="n", type="neuron", properties={"activation": "sigmoid"})
        node.inputs = [self._make_port("n_in", "n", "input", 0, ["training"])]
        prev = Node(id="prev", type="layer")
        prev.outputs = [self._make_port("prev_out", "prev", "output", 0, ["training"])]
        links = [Link(id_from="prev_out", id_to="n_in")]
        graph = self._graph_with_nodes([node, prev], links)
        code, vm = self._run_translator(
            node, graph, placement="forward", is_first=False
        )
        self.assertIn("outputs.get('prev'", code)
        self.assertIn("torch.sigmoid(x)", code)


class LayerTranslatorTest(BaseTranslatorTest):
    def test_init_with_num_neurons(self):
        node = Node(id="l", type="layer", properties={"numNeurons": 64})
        node.inputs = [self._make_port("l_in", "l", "input", 0, ["training"])]
        src = Node(id="src", type="input-data")
        src.outputs = [self._make_port("src_out", "src", "output", 0, ["training"])]
        links = [
            Link(
                id_from="src_out",
                id_to="l_in",
                weight_shape={"shape": [64, 8], "dtype": "float32"},
                has_weight=True,
            )
        ]
        graph = self._graph_with_nodes([node, src], links)
        code, vm = self._run_translator(node, graph, placement="init")
        self.assertIn("self.fc_l = nn.Linear(8, 64)", code)


# ----------------------------------------------------------------
# Conv2D
# ----------------------------------------------------------------
class Conv2DTranslatorTest(BaseTranslatorTest):
    def test_init(self):
        node = Node(
            id="conv",
            type="conv2d",
            properties={"filters": 32, "kernelSize": 3, "stride": 1, "padding": 0},
        )
        node.inputs = [self._make_port("conv_in", "conv", "input", 0, ["training"])]
        # Provide a source with shape so guess_in_channels works
        src = Node(id="src", type="input-data")
        src.outputs = [
            self._make_port(
                "src_out",
                "src",
                "output",
                0,
                ["training"],
                shape=type(
                    "Shape", (), {"shape": [None, 3, 32, 32], "dtype": "float32"}
                )(),
            )
        ]
        links = [Link(id_from="src_out", id_to="conv_in")]
        graph = self._graph_with_nodes([node, src], links)
        code, vm = self._run_translator(node, graph, placement="init")
        self.assertIn(
            "self.conv_conv = nn.Conv2d(3, 32, kernel_size=3, stride=1, padding=0, bias=True)",
            code,
        )


# ----------------------------------------------------------------
# Flatten / Dropout / BatchNorm
# ----------------------------------------------------------------
class FlattenTranslatorTest(BaseTranslatorTest):
    def test_data_squeeze(self):
        node = Node(id="flat", type="flatten")
        node.inputs = [
            self._make_port("flat_in", "flat", "input", 0, ["preprocessing"])
        ]
        node.outputs = [
            self._make_port("flat_out", "flat", "output", 0, ["preprocessing"])
        ]
        src = Node(id="src", type="input-data")
        src.outputs = [
            self._make_port("src_out", "src", "output", 0, ["preprocessing"])
        ]
        links = [Link(id_from="src_out", id_to="flat_in")]
        graph = self._graph_with_nodes([node, src], links)
        code, vm = self._run_translator(
            node, graph, var_map={"src": "t", "src_out": "t"}
        )
        self.assertIn("if t.dim() == 2 and t.size(-1) == 1:", code)


class DropoutTranslatorTest(BaseTranslatorTest):
    def test_init_and_forward(self):
        node = Node(id="drop", type="dropout", properties={"rate": 0.5})
        node.inputs = [self._make_port("drop_in", "drop", "input", 0, ["training"])]
        node.outputs = [self._make_port("drop_out", "drop", "output", 0, ["training"])]
        prev = Node(id="prev", type="layer")
        prev.outputs = [self._make_port("prev_out", "prev", "output", 0, ["training"])]
        links = [Link(id_from="prev_out", id_to="drop_in")]
        graph = self._graph_with_nodes([node, prev], links)
        code_init, _ = self._run_translator(node, graph, placement="init")
        self.assertIn("self.dropout_drop = nn.Dropout(p=0.5)", code_init)
        code_fwd, _ = self._run_translator(node, graph, placement="forward")
        self.assertIn("self.dropout_drop(x)", code_fwd)


class BatchNormTranslatorTest(BaseTranslatorTest):
    def test_init_guess_features(self):
        node = Node(id="bn", type="batchnorm")
        node.inputs = [self._make_port("bn_in", "bn", "input", 0, ["training"])]
        # Provide a predecessor layer to guess num features
        prev = Node(id="prev", type="layer", properties={"numNeurons": 128})
        prev.outputs = [self._make_port("prev_out", "prev", "output", 0, ["training"])]
        links = [Link(id_from="prev_out", id_to="bn_in")]
        graph = self._graph_with_nodes([node, prev], links)
        code, vm = self._run_translator(node, graph, placement="init")
        self.assertIn("self.bn_bn = nn.BatchNorm1d(num_features=128)", code)


# ----------------------------------------------------------------
# Add / Concat
# ----------------------------------------------------------------
class AddTranslatorTest(BaseTranslatorTest):
    def test_two_inputs(self):
        node = Node(id="add", type="add")
        node.inputs = [self._make_port("add_in", "add", "input", 0, ["training"])]
        node.outputs = [self._make_port("add_out", "add", "output", 0, ["training"])]
        a = Node(id="a", type="layer")
        a.outputs = [self._make_port("a_out", "a", "output", 0, ["training"])]
        b = Node(id="b", type="layer")
        b.outputs = [self._make_port("b_out", "b", "output", 0, ["training"])]
        links = [
            Link(id_from="a_out", id_to="add_in"),
            Link(id_from="b_out", id_to="add_in"),
        ]
        graph = self._graph_with_nodes([node, a, b], links)
        code, vm = self._run_translator(node, graph, placement="forward")
        self.assertIn("outputs.get('a'", code)
        self.assertIn("outputs.get('b'", code)
        self.assertIn("x = a + b", code)


class ConcatTranslatorTest(BaseTranslatorTest):
    def test_multi_input_concat(self):
        node = Node(id="cat", type="concat", properties={"axis": -1})
        node.inputs = [self._make_port("cat_in", "cat", "input", 0, ["training"])]
        node.outputs = [self._make_port("cat_out", "cat", "output", 0, ["training"])]
        a = Node(id="a", type="layer")
        a.outputs = [self._make_port("a_out", "a", "output", 0, ["training"])]
        b = Node(id="b", type="layer")
        b.outputs = [self._make_port("b_out", "b", "output", 0, ["training"])]
        links = [
            Link(id_from="a_out", id_to="cat_in"),
            Link(id_from="b_out", id_to="cat_in"),
        ]
        graph = self._graph_with_nodes([node, a, b], links)
        code, vm = self._run_translator(node, graph, placement="forward")
        self.assertIn("torch.cat(tensors, dim=-1)", code)


# ----------------------------------------------------------------
# Output
# ----------------------------------------------------------------
class OutputTranslatorTest(BaseTranslatorTest):
    def test_per_port_activations(self):
        node = Node(
            id="out",
            type="output",
            properties={
                "outputActivations": {
                    "loss": "none",
                    "prediction": "softmax",
                    "evaluation": "argmax",
                }
            },
        )
        node.inputs = [self._make_port("out_in", "out", "input", 0, ["training"])]
        node.outputs = [
            self._make_port("loss_p", "out", "output", 0, ["training"], role="loss"),
            self._make_port(
                "pred_p", "out", "output", 1, ["evaluation"], role="prediction"
            ),
            self._make_port(
                "eval_p", "out", "output", 2, ["evaluation"], role="evaluation"
            ),
        ]
        src = Node(id="src", type="layer")
        src.outputs = [self._make_port("src_out", "src", "output", 0, ["training"])]
        links = [Link(id_from="src_out", id_to="out_in")]
        graph = self._graph_with_nodes([node, src], links)
        code, vm = self._run_translator(node, graph, placement="forward")
        self.assertIn("outputs['loss_p'] = x", code)
        self.assertIn("torch.softmax(x, dim=-1)", code)
        self.assertIn("torch.argmax(x, dim=-1)", code)


# ----------------------------------------------------------------
# Optimizer
# ----------------------------------------------------------------
class OptimizerTranslatorTest(BaseTranslatorTest):
    def test_emit_training_setup_adam_mse(self):
        node = Node(
            id="opt",
            type="optimizer",
            properties={
                "lossType": "mse",
                "optimizerType": "adam",
                "learningRate": 0.01,
            },
        )
        w = CodeWriter()
        t = get_translator(node, Graph(), {})
        t.emit_training_setup(w)
        code = str(w)
        self.assertIn("criterion = nn.MSELoss()", code)
        self.assertIn("optimizer = optim.Adam(model.parameters(), lr=0.01", code)

    def test_crossentropy_cast_long(self):
        node = Node(
            id="opt",
            type="optimizer",
            properties={
                "lossType": "cross_entropy",
                "optimizerType": "sgd",
                "learningRate": 0.1,
            },
        )
        w = CodeWriter()
        t = get_translator(node, Graph(), {})
        t.emit_training_setup(w)
        code = str(w)
        self.assertIn("criterion = nn.CrossEntropyLoss()", code)
        self.assertIn("labels = labels.long()", code)


# ----------------------------------------------------------------
# Visualization
# ----------------------------------------------------------------
class VisualizationTranslatorTest(BaseTranslatorTest):
    def test_scatter_with_discrete_color(self):
        node = Node(
            id="viz",
            type="visualization",
            properties={
                "colorMode": "discrete",
                "colorPalette": ["#ff0000", "#00ff00"],
            },
        )
        node.inputs = [
            self._make_port("v_x", "viz", "input", 0, ["evaluation"], sub_type="coord"),
            self._make_port("v_y", "viz", "input", 1, ["evaluation"], sub_type="coord"),
            self._make_port("v_c", "viz", "input", 2, ["evaluation"], role="color"),
        ]
        src = Node(id="src", type="input-data")
        src.outputs = [
            self._make_port("sx", "src", "output", 0, ["evaluation"]),
            self._make_port("sy", "src", "output", 1, ["evaluation"]),
            self._make_port("sc", "src", "output", 2, ["evaluation"]),
        ]
        links = [
            Link(id_from="sx", id_to="v_x"),
            Link(id_from="sy", id_to="v_y"),
            Link(id_from="sc", id_to="v_c"),
        ]
        graph = self._graph_with_nodes([node, src], links)
        code, vm = self._run_translator(
            node, graph, var_map={"sx": "a", "sy": "b", "sc": "c"}, phase="evaluation"
        )
        self.assertIn("ListedColormap", code)
        self.assertIn("plt.scatter(data_v_x.flatten()", code)
        self.assertIn("c=colors.flatten()", code)


# ----------------------------------------------------------------
# Print
# ----------------------------------------------------------------
class PrintTranslatorTest(BaseTranslatorTest):
    def test_data_placement(self):
        node = Node(id="p", type="print", properties={"label": "debug"})
        node.inputs = [self._make_port("p_in", "p", "input", 0, ["preprocessing"])]
        src = Node(id="src", type="input-data")
        src.outputs = [
            self._make_port("src_out", "src", "output", 0, ["preprocessing"])
        ]
        links = [Link(id_from="src_out", id_to="p_in")]
        graph = self._graph_with_nodes([node, src], links)
        code, vm = self._run_translator(node, graph, var_map={"src_out": "tensor"})
        self.assertIn('print("debug[0]:", tensor.shape, tensor)', code)


# ----------------------------------------------------------------
# Accuracy
# ----------------------------------------------------------------
class AccuracyTranslatorTest(BaseTranslatorTest):
    def test_single_column_label_squeezed(self):
        from sketchmod.codegen.graph import ShapeInfo, ShapeDim

        node = Node(id="acc", type="accuracy", properties={"showConfusion": False})
        node.inputs = [
            self._make_port(
                "acc_pred", "acc", "input", 0, ["evaluation"], sub_type="predictions"
            ),
            self._make_port(
                "acc_label", "acc", "input", 1, ["evaluation"], sub_type="labels"
            ),
        ]
        # Source for prediction: shape (N,)
        pred_src = Node(id="pred_src", type="output")
        pred_src.outputs = [
            self._make_port(
                "ps",
                "pred_src",
                "output",
                0,
                ["evaluation"],
                shape=ShapeInfo(shape=[ShapeDim(100)]),
            )
        ]
        # Source for label: shape (N, 1) → should be squeezed
        label_src = Node(id="label_src", type="column-select")
        label_src.outputs = [
            self._make_port(
                "ls",
                "label_src",
                "output",
                0,
                ["evaluation"],
                shape=ShapeInfo(shape=[ShapeDim(100), ShapeDim(1)]),
            )
        ]
        links = [
            Link(id_from="ps", id_to="acc_pred"),
            Link(id_from="ls", id_to="acc_label"),
        ]
        graph = self._graph_with_nodes([node, pred_src, label_src], links)
        code, vm = self._run_translator(
            node, graph, var_map={"ps": "p", "ls": "l"}, phase="evaluation"
        )
        self.assertIn("pred_labels = p.long()", code)
        self.assertIn("true_labels = l.squeeze(-1).long()", code)
        self.assertIn("acc = (pred_labels == true_labels).float().mean()", code)


class ReshapeTranslatorTest(BaseTranslatorTest):
    def test_data_reshape_infer(self):
        node = Node(id="r", type="reshape", properties={"targetShape": "(64, -1)"})
        node.inputs = [self._make_port("r_in", "r", "input", 0, ["preprocessing"])]
        node.outputs = [self._make_port("r_out", "r", "output", 0, ["preprocessing"])]
        src = Node(id="src", type="input-data")
        src.outputs = [
            self._make_port("src_out", "src", "output", 0, ["preprocessing"])
        ]
        links = [Link(id_from="src_out", id_to="r_in")]
        graph = self._graph_with_nodes([node, src], links)
        code, vm = self._run_translator(
            node, graph, var_map={"src": "tensor", "src_out": "tensor"}
        )
        self.assertIn("tensor.reshape((64, -1))", code)

    def test_forward_reshape(self):
        node = Node(id="r", type="reshape", properties={"targetShape": "(28, 28)"})
        node.inputs = [self._make_port("r_in", "r", "input", 0, ["training"])]
        node.outputs = [self._make_port("r_out", "r", "output", 0, ["training"])]
        prev = Node(id="prev", type="layer")
        prev.outputs = [self._make_port("prev_out", "prev", "output", 0, ["training"])]
        links = [Link(id_from="prev_out", id_to="r_in")]
        graph = self._graph_with_nodes([node, prev], links)
        code, vm = self._run_translator(node, graph, placement="forward")
        self.assertIn("x.reshape((28, 28))", code)
        self.assertIn("outputs['r'] = x", code)


if __name__ == "__main__":
    unittest.main()
