"""
Unit tests for the per-node emitters in ``codegen/nodes.py``.

Emitters are placement-agnostic: they turn already-resolved input expressions
into output expressions.  These tests exercise them directly, which is why the
same class can be checked once for both ``load_data`` and ``forward`` -- the
only difference is the ``in_model`` flag.
"""

import unittest

from sketchmod.codegen.analysis import Analysis
from sketchmod.codegen.graph import Graph, Node, Port, ShapeDim, ShapeInfo
from sketchmod.codegen.naming import Names
from sketchmod.codegen.nodes import NodeCtx, activation, emitter_for


def shape(*dims):
    return ShapeInfo(shape=[ShapeDim(d) for d in dims])


def port(port_id, *, node_id="src", kind="data", role=None, sub_type=None, dims=None):
    return Port(
        id=port_id,
        node_id=node_id,
        type="output",
        index=0,
        port_kind=kind,
        role=role,
        sub_type=sub_type,
        shape=shape(*dims) if dims else None,
    )


class EmitterTest(unittest.TestCase):
    """Builds a NodeCtx by hand and runs one emitter over it."""

    def emit(self, node, inputs=(), source_ports=(), params=None, in_model=False):
        graph = Graph()
        graph.nodes[node.id] = node
        analysis = Analysis(graph, {})
        sources = list(inputs)
        ports = list(source_ports) or [port(f"p{i}") for i in range(len(sources))]

        context = NodeCtx(
            node=node,
            analysis=analysis,
            phase="preprocessing",
            inputs=sources,
            sources=sources,
            source_ports=ports,
            resolve_param=(lambda index: (params or {}).get(index)),
            by_port=sources,
            in_model=in_model,
            names=Names(),
        )
        emitter = emitter_for(node)
        return {
            "submodules": emitter.submodules(context),
            "prelude": emitter.prelude(context),
            "values": emitter.expressions(context),
            "params": emitter.param_expressions(context),
            "statements": emitter.statements(context),
        }

    @staticmethod
    def node(node_id, node_type, properties=None, outputs=1, param_outputs=0):
        return Node(
            id=node_id,
            type=node_type,
            outputs=[
                Port(id=f"{node_id}_out{i}", node_id=node_id, type="output", index=i)
                for i in range(outputs)
            ],
            paramOutputs=[
                Port(
                    id=f"{node_id}_p{i}",
                    node_id=node_id,
                    type="output",
                    index=i,
                    port_kind="param",
                )
                for i in range(param_outputs)
            ],
            properties=properties or {},
        )


# ----------------------------------------------------------------------
#  Shared helpers
# ----------------------------------------------------------------------
class ActivationTest(unittest.TestCase):
    def test_linear_is_a_passthrough(self):
        self.assertEqual(activation("linear", "x"), "x")
        self.assertEqual(activation(None, "x"), "x")

    def test_torch_namespace(self):
        self.assertEqual(activation("relu", "x"), "torch.relu(x)")
        self.assertEqual(activation("tanh", "x"), "torch.tanh(x)")

    def test_functional_namespace(self):
        self.assertEqual(
            activation("leaky_relu", "x"), "torch.nn.functional.leaky_relu(x)"
        )

    def test_softmax_dimension_is_configurable(self):
        self.assertEqual(activation("softmax", "x"), "torch.softmax(x, dim=-1)")
        self.assertEqual(
            activation("softmax", "x", softmax_dim=1), "torch.softmax(x, dim=1)"
        )


# ----------------------------------------------------------------------
#  Data sources and transforms
# ----------------------------------------------------------------------
class InputDataTest(EmitterTest):
    def test_random_fallback(self):
        node = self.node("inp", "input-data")
        self.assertEqual(self.emit(node)["values"], ["torch.randn(200, 10)"])

    def test_manual_shape(self):
        node = self.node("inp", "input-data", {"dataShape": "(64, 3)"})
        self.assertEqual(self.emit(node)["values"], ["torch.randn(64, 3)"])

    def test_csv_dataset(self):
        node = self.node(
            "inp",
            "input-data",
            {"datasetId": 7, "datasetFile": "iris.csv", "datasetFormat": "csv"},
        )
        result = self.emit(node)
        self.assertEqual(result["prelude"], ["df = pd.read_csv('data/iris.csv')"])
        self.assertEqual(
            result["values"], ["torch.tensor(df.values, dtype=torch.float32)"]
        )


class ColumnSelectTest(EmitterTest):
    def test_index_list(self):
        node = self.node("c", "column-select", {"selectedColumns": [0, 2]})
        self.assertEqual(self.emit(node, ["raw"])["values"], ["raw[:, [0, 2]]"])

    def test_long_contiguous_run_becomes_a_slice(self):
        node = self.node("c", "column-select", {"selectedColumns": list(range(25))})
        self.assertEqual(self.emit(node, ["raw"])["values"], ["raw[:, 0:25]"])

    def test_range_text(self):
        node = self.node("c", "column-select", {"columnInput": "1:4"})
        self.assertEqual(self.emit(node, ["raw"])["values"], ["raw[:, 1:4]"])


class RowSelectTest(EmitterTest):
    def test_first_n(self):
        node = self.node("r", "row-select", {"method": "first-n", "value": "50"})
        result = self.emit(node, ["raw"])
        self.assertEqual(result["prelude"], [])
        self.assertEqual(result["values"], ["raw[:50]"])

    def test_random_uses_a_seeded_permutation(self):
        node = self.node(
            "r", "row-select", {"method": "random", "value": "10", "randomSeed": 7}
        )
        result = self.emit(node, ["raw"])
        self.assertEqual(
            result["prelude"],
            [
                "r_perm = torch.randperm(raw.size(0), "
                "generator=torch.Generator().manual_seed(7))"
            ],
        )
        self.assertEqual(result["values"], ["raw[r_perm[:10]]"])


class NormalizeTest(EmitterTest):
    def test_standard_computes_its_own_statistics(self):
        node = self.node("n", "normalize", {"method": "standard"}, param_outputs=1)
        result = self.emit(node, ["c2"])
        self.assertEqual(
            result["prelude"],
            [
                "n_mean = c2.mean(dim=0, keepdim=True)",
                "n_std = c2.std(dim=0, keepdim=True) + 1e-8",
            ],
        )
        self.assertEqual(result["values"], ["(c2 - n_mean) / n_std"])
        self.assertEqual(result["params"], [["n_mean", "n_std"]])

    def test_shared_statistics_are_reused_verbatim(self):
        """The epsilon lives in the shared std; adding it again would be a bug."""
        node = self.node("n7", "normalize", {"method": "standard"}, param_outputs=1)
        result = self.emit(node, ["c3"], params={0: ["n6_mean", "n6_std"]})
        self.assertEqual(result["prelude"], [])
        self.assertEqual(result["values"], ["(c3 - n6_mean) / n6_std"])
        self.assertEqual(result["params"], [["n6_mean", "n6_std"]])


class OneHotTest(EmitterTest):
    def test_column_vector_is_squeezed(self):
        node = self.node("o", "onehot", {"numClasses": 3}, param_outputs=1)
        result = self.emit(node, ["c4"], source_ports=[port("s", dims=(100, 1))])
        self.assertEqual(
            result["values"],
            [
                "torch.nn.functional.one_hot(c4.squeeze(-1).long(), "
                "num_classes=3).float()"
            ],
        )
        self.assertEqual(result["params"], [["torch.arange(3)"]])

    def test_flat_vector_is_left_alone(self):
        node = self.node("o", "onehot", {"numClasses": 3}, param_outputs=1)
        result = self.emit(node, ["c4"], source_ports=[port("s", dims=(100,))])
        self.assertEqual(
            result["values"],
            ["torch.nn.functional.one_hot(c4.long(), num_classes=3).float()"],
        )


class DeOneHotTest(EmitterTest):
    """The rank is known statically, so no runtime ``.dim()`` branch is emitted."""

    def test_two_dimensional_input_uses_argmax(self):
        node = self.node("d", "deonehot")
        result = self.emit(node, ["probs"], source_ports=[port("s", dims=(100, 3))])
        self.assertEqual(result["values"], ["torch.argmax(probs, dim=-1)"])

    def test_one_dimensional_input_passes_through(self):
        node = self.node("d", "deonehot")
        result = self.emit(node, ["labels"], source_ports=[port("s", dims=(100,))])
        self.assertEqual(result["values"], ["labels"])


class TrainTestSplitTest(EmitterTest):
    def test_two_outputs_share_one_permutation(self):
        node = self.node(
            "t1", "train-test", {"trainRatio": 0.6, "randomSeed": 42}, outputs=2
        )
        result = self.emit(node, ["raw"])
        self.assertEqual(
            result["prelude"],
            [
                "t1_perm = torch.randperm(raw.size(0), "
                "generator=torch.Generator().manual_seed(42))",
                "t1_split = int(raw.size(0) * 0.6)",
            ],
        )
        self.assertEqual(
            result["values"], ["raw[t1_perm[:t1_split]]", "raw[t1_perm[t1_split:]]"]
        )


class ReshapeTest(EmitterTest):
    def test_literal_target(self):
        node = self.node("r", "reshape", {"targetShape": "(-1, 1, 5, 5)"})
        self.assertEqual(self.emit(node, ["feat"])["values"], ["feat.reshape(-1, 1, 5, 5)"])

    def test_symbolic_dimension_alone_becomes_inferred(self):
        node = self.node("r", "reshape", {"targetShape": "(batch, 10)"})
        self.assertEqual(self.emit(node, ["x"])["values"], ["x.reshape(-1, 10)"])

    def test_symbolic_dimension_beside_minus_one_reads_the_input(self):
        node = self.node("r", "reshape", {"targetShape": "(batch, -1)"})
        self.assertEqual(self.emit(node, ["x"])["values"], ["x.reshape(x.size(0), -1)"])


# ----------------------------------------------------------------------
#  Model layers
# ----------------------------------------------------------------------
class LayerTest(EmitterTest):
    def test_width_is_the_sum_of_everything_arriving(self):
        node = self.node("l", "layer", {"numNeurons": 16, "activation": "relu"})
        result = self.emit(
            node,
            ["x"],
            source_ports=[port("a", dims=(100, 3)), port("b", dims=(100, 5))],
            in_model=True,
        )
        self.assertEqual(result["submodules"], ["self.l = nn.Linear(8, 16)"])
        self.assertEqual(result["values"], ["torch.relu(self.l(x))"])

    def test_bias_is_only_mentioned_when_disabled(self):
        node = self.node("l", "layer", {"numNeurons": 4, "hasBias": False})
        result = self.emit(node, ["x"], [port("a", dims=(9, 2))], in_model=True)
        self.assertEqual(result["submodules"], ["self.l = nn.Linear(2, 4, bias=False)"])

    def test_outside_the_model_the_layer_is_built_inline_and_untrained(self):
        node = self.node("l3", "layer", {"numNeurons": 8})
        result = self.emit(node, ["c2"], [port("a", dims=(100, 3))], in_model=False)
        self.assertEqual(result["submodules"], [])
        self.assertIn("untrained", result["prelude"][0])
        self.assertEqual(result["values"], ["torch.relu(l3_module(c2))"])


class NeuronTest(EmitterTest):
    def test_always_a_single_output(self):
        node = self.node("n", "neuron", {"activation": "linear"})
        result = self.emit(node, ["x"], [port("a", dims=(100, 4))], in_model=True)
        self.assertEqual(result["submodules"], ["self.n = nn.Linear(4, 1)"])
        self.assertEqual(result["values"], ["self.n(x)"])


class Conv2DTest(EmitterTest):
    def test_channels_come_from_the_input_shape(self):
        node = self.node(
            "conv",
            "conv2d",
            {"filters": 4, "kernelSize": 3, "stride": 1, "padding": 0},
        )
        result = self.emit(node, ["x"], [port("a", dims=(100, 1, 5, 5))], in_model=True)
        self.assertEqual(
            result["submodules"], ["self.conv = nn.Conv2d(1, 4, kernel_size=3)"]
        )
        self.assertEqual(result["values"], ["torch.relu(self.conv(x))"])


class MaxPool2DTest(EmitterTest):
    def test_maxpool2d_reduces_spatial_dims(self):
        node = self.node(
            "pool",
            "maxpool2d",
            {"kernelSize": 2, "stride": 2, "padding": 0},
        )
        result = self.emit(node, ["x"], [port("a", dims=(100, 8, 6, 6))], in_model=True)
        self.assertEqual(result["submodules"], ["self.pool = nn.MaxPool2d(2)"])
        self.assertEqual(result["values"], ["self.pool(x)"])


class BatchNormTest(EmitterTest):
    def test_one_dimensional(self):
        node = self.node("bn", "batchnorm")
        result = self.emit(node, ["x"], [port("a", dims=(100, 32))], in_model=True)
        self.assertEqual(
            result["submodules"], ["self.bn = nn.BatchNorm1d(num_features=32)"]
        )

    def test_two_dimensional(self):
        node = self.node("bn", "batchnorm")
        result = self.emit(node, ["x"], [port("a", dims=(100, 8, 5, 5))], in_model=True)
        self.assertEqual(
            result["submodules"], ["self.bn = nn.BatchNorm2d(num_features=8)"]
        )


class DropoutTest(EmitterTest):
    def test_inside_the_model(self):
        node = self.node("drop", "dropout", {"rate": 0.2})
        result = self.emit(node, ["x"], in_model=True)
        self.assertEqual(result["submodules"], ["self.drop = nn.Dropout(p=0.2)"])
        self.assertEqual(result["values"], ["self.drop(x)"])

    def test_outside_the_model_it_is_explicitly_inactive(self):
        node = self.node("drop", "dropout", {"rate": 0.2})
        result = self.emit(node, ["x"], in_model=False)
        self.assertEqual(
            result["values"],
            ["torch.nn.functional.dropout(x, p=0.2, training=False)"],
        )


class FlattenTest(EmitterTest):
    def test_inside_the_model_uses_a_submodule(self):
        node = self.node("flat", "flatten")
        result = self.emit(
            node, ["conv"], [port("a", dims=(100, 4, 3, 3))], in_model=True
        )
        self.assertEqual(result["submodules"], ["self.flat = nn.Flatten()"])
        self.assertEqual(result["values"], ["self.flat(conv)"])

    def test_single_column_is_squeezed(self):
        node = self.node("flat", "flatten")
        result = self.emit(node, ["labels"], [port("a", dims=(100, 1))])
        self.assertEqual(result["values"], ["labels.squeeze(-1)"])

    def test_higher_rank_is_flattened_functionally(self):
        node = self.node("flat", "flatten")
        result = self.emit(node, ["img"], [port("a", dims=(100, 4, 3, 3))])
        self.assertEqual(result["values"], ["torch.flatten(img, start_dim=1)"])


class MergeTest(EmitterTest):
    def test_add(self):
        node = self.node("add", "add")
        self.assertEqual(self.emit(node, ["a", "b"])["values"], ["a + b"])

    def test_concat(self):
        node = self.node("cat", "concat", {"axis": -1})
        self.assertEqual(
            self.emit(node, ["a", "b"])["values"], ["torch.cat([a, b], dim=-1)"]
        )

    def test_concat_of_one_source_is_a_passthrough(self):
        node = self.node("cat", "concat")
        self.assertEqual(self.emit(node, ["a"])["values"], ["a"])


class OutputTest(EmitterTest):
    def test_each_role_gets_its_own_activation(self):
        node = Node(
            id="out",
            type="output",
            outputs=[
                Port(id="loss_p", node_id="out", type="output", index=0, role="loss"),
                Port(
                    id="pred_p", node_id="out", type="output", index=1, role="prediction"
                ),
                Port(
                    id="eval_p", node_id="out", type="output", index=2, role="evaluation"
                ),
            ],
            properties={
                "outputActivations": {
                    "loss": "none",
                    "prediction": "softmax",
                    "evaluation": "argmax",
                }
            },
        )
        self.assertEqual(
            self.emit(node, ["layer"])["values"],
            ["layer", "torch.softmax(layer, dim=-1)", "torch.argmax(layer, dim=-1)"],
        )


# ----------------------------------------------------------------------
#  Side-effect nodes
# ----------------------------------------------------------------------
class PrintTest(EmitterTest):
    def test_prints_shape_and_value(self):
        node = self.node("p", "print", {"label": "loss"}, outputs=0)
        self.assertEqual(
            self.emit(node, ["out.loss"])["statements"],
            ['print("loss" + f\'[0]:\', out.loss.shape, out.loss)'],
        )


class AccuracyTest(EmitterTest):
    def test_one_hot_labels_are_reduced_to_indices(self):
        node = self.node("acc", "accuracy", outputs=0)
        statements = self.emit(
            node,
            ["out.prediction", "data.labels"],
            source_ports=[port("p", dims=(100, 3)), port("l", dims=(100, 3))],
        )["statements"]
        self.assertEqual(statements[0], "acc_predicted = out.prediction.argmax(dim=1)")
        self.assertEqual(statements[1], "acc_actual = data.labels.argmax(dim=1)")

    def test_column_labels_are_squeezed(self):
        node = self.node("acc", "accuracy", outputs=0)
        statements = self.emit(
            node,
            ["out.prediction", "data.labels"],
            source_ports=[port("p", dims=(100,)), port("l", dims=(100, 1))],
        )["statements"]
        self.assertEqual(statements[0], "acc_predicted = out.prediction.long()")
        self.assertEqual(statements[1], "acc_actual = data.labels.squeeze(-1).long()")

    def test_confusion_matrix_is_opt_in(self):
        node = self.node("acc", "accuracy", {"showConfusion": True}, outputs=0)
        statements = self.emit(node, ["p", "l"])["statements"]
        self.assertIn("from sklearn.metrics import confusion_matrix", statements)


class VisualizationTest(EmitterTest):
    def test_scatter_with_a_discrete_palette(self):
        node = Node(
            id="viz",
            type="visualization",
            inputs=[
                Port(id="x", node_id="viz", type="input", index=0, sub_type="coord"),
                Port(id="y", node_id="viz", type="input", index=1, sub_type="coord"),
                Port(id="c", node_id="viz", type="input", index=2, role="color"),
            ],
            properties={
                "label": "clusters",
                "colorMode": "discrete",
                "colorPalette": ["#ef4444", "#4ade80"],
            },
        )
        statements = self.emit(node, ["a", "b", "labels"])["statements"]
        joined = "\n".join(statements)
        self.assertIn("from matplotlib.colors import ListedColormap", joined)
        self.assertIn("ListedColormap(['#ef4444', '#4ade80'])", joined)
        self.assertIn(
            "plt.scatter(a.flatten(), b.flatten(), c=labels.flatten(), "
            "cmap=viz_cmap, alpha=0.5)",
            joined,
        )
        self.assertIn('plt.title("clusters")', joined)

    def test_single_coordinate_draws_a_histogram(self):
        node = Node(
            id="viz",
            type="visualization",
            inputs=[
                Port(id="x", node_id="viz", type="input", index=0, sub_type="coord")
            ],
            properties={"label": "spread"},
        )
        statements = self.emit(node, ["a"])["statements"]
        self.assertIn("plt.hist(a.flatten(), bins=20)", statements)


if __name__ == "__main__":
    unittest.main()
