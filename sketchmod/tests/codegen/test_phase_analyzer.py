"""
Comprehensive tests for phase_analyzer.py.

Covers preprocessing, training/evaluation traversal, conjunctive/disjunctive
activation, carry‑over, output node relaxation, param‑port handling, topological
ordering, and highlight_path.
"""

import unittest
from sketchmod.codegen.graph import (
    Graph,
    Node,
    Port,
    Link,
    parse_graph,
)
from sketchmod.codegen.phase_analyzer import analyze_phases, highlight_path


class PhaseAnalyzerTest(unittest.TestCase):
    # ----------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------
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
        )

    def _make_output_node(self, name, input_phases, output_phases):
        """Create a minimal output node that consumes a single input."""
        out = Node(id=name, type="output")
        out.inputs = [self._make_port(f"{name}_in", name, "input", 0, input_phases)]
        out.outputs = [
            self._make_port(
                f"{name}_out", name, "output", 0, output_phases, role="loss"
            )
        ]
        return out

    def _build_graph(self, nodes, links):
        graph = Graph()
        for n in nodes:
            graph.nodes[n.id] = n
            for p in n.inputs + n.outputs + n.paramInputs + n.paramOutputs:
                graph.ports[p.id] = p
        graph.links = links
        return graph

    # ----------------------------------------------------------------
    # Preprocessing
    # ----------------------------------------------------------------
    def test_preprocessing_simple_chain(self):
        inp = Node(id="inp", type="input-data")
        col = Node(id="col", type="column-select")
        # output node to consume col's output
        sink = Node(id="sink", type="output")
        inp.outputs = [
            self._make_port("inp_out", "inp", "output", 0, ["preprocessing"])
        ]
        col.inputs = [self._make_port("col_in", "col", "input", 0, ["preprocessing"])]
        col.outputs = [
            self._make_port("col_out", "col", "output", 0, ["preprocessing"])
        ]
        sink.inputs = [
            self._make_port("sink_in", "sink", "input", 0, ["preprocessing"])
        ]
        links = [
            Link(id_from="inp_out", id_to="col_in"),
            Link(id_from="col_out", id_to="sink_in"),
        ]
        graph = self._build_graph([inp, col, sink], links)
        flow = analyze_phases(graph)
        self.assertIn("inp", flow["preprocessing_set"])
        self.assertIn("col", flow["preprocessing_set"])
        self.assertIn("sink", flow["preprocessing_set"])
        # order: inp -> col -> sink
        self.assertLess(
            flow["preprocessing_order"].index("inp"),
            flow["preprocessing_order"].index("col"),
        )
        self.assertLess(
            flow["preprocessing_order"].index("col"),
            flow["preprocessing_order"].index("sink"),
        )

    def test_preprocessing_stops_at_missing_phase(self):
        inp = Node(id="inp", type="input-data")
        col = Node(id="col", type="column-select")
        inp.outputs = [
            self._make_port("inp_out", "inp", "output", 0, ["preprocessing"])
        ]
        col.inputs = [self._make_port("col_in", "col", "input", 0, [])]  # no phases
        col.outputs = [
            self._make_port("col_out", "col", "output", 0, ["preprocessing"])
        ]
        links = [Link(id_from="inp_out", id_to="col_in")]
        graph = self._build_graph([inp, col], links)
        flow = analyze_phases(graph)
        self.assertIn("inp", flow["preprocessing_set"])
        self.assertNotIn("col", flow["preprocessing_set"])

    def test_preprocessing_output_must_have_phase(self):
        inp = Node(id="inp", type="input-data")
        col = Node(id="col", type="column-select")
        inp.outputs = [
            self._make_port("inp_out", "inp", "output", 0, ["preprocessing"])
        ]
        col.inputs = [self._make_port("col_in", "col", "input", 0, ["preprocessing"])]
        col.outputs = [self._make_port("col_out", "col", "output", 0, [])]  # no phase
        links = [Link(id_from="inp_out", id_to="col_in")]
        graph = self._build_graph([inp, col], links)
        flow = analyze_phases(graph)
        self.assertNotIn("col", flow["preprocessing_set"])

    # ----------------------------------------------------------------
    # Training / Evaluation carry‑over
    # ----------------------------------------------------------------
    def test_training_seed_from_preprocessing(self):
        inp = Node(id="inp", type="input-data")
        norm = Node(id="norm", type="normalize")
        layer = Node(id="layer", type="layer")
        sink = Node(id="sink", type="output")  # consume layer output
        inp.outputs = [
            self._make_port("inp_out", "inp", "output", 0, ["preprocessing"])
        ]
        norm.inputs = [
            self._make_port("norm_in", "norm", "input", 0, ["preprocessing"])
        ]
        norm.outputs = [
            self._make_port(
                "norm_out", "norm", "output", 0, ["preprocessing", "training"]
            )
        ]
        layer.inputs = [self._make_port("layer_in", "layer", "input", 0, ["training"])]
        layer.outputs = [
            self._make_port("layer_out", "layer", "output", 0, ["training"])
        ]
        sink.inputs = [self._make_port("sink_in", "sink", "input", 0, ["training"])]
        links = [
            Link(id_from="inp_out", id_to="norm_in"),
            Link(id_from="norm_out", id_to="layer_in"),
            Link(id_from="layer_out", id_to="sink_in"),
        ]
        graph = self._build_graph([inp, norm, layer, sink], links)
        flow = analyze_phases(graph)
        self.assertIn("norm", flow["preprocessing_set"])
        self.assertIn("layer", flow["train_set"])
        self.assertIn("sink", flow["train_set"])

    def test_training_without_seed_phase_fails(self):
        inp = Node(id="inp", type="input-data")
        norm = Node(id="norm", type="normalize")
        layer = Node(id="layer", type="layer")
        inp.outputs = [
            self._make_port("inp_out", "inp", "output", 0, ["preprocessing"])
        ]
        norm.inputs = [
            self._make_port("norm_in", "norm", "input", 0, ["preprocessing"])
        ]
        norm.outputs = [
            self._make_port("norm_out", "norm", "output", 0, ["preprocessing"])
        ]  # no training
        layer.inputs = [self._make_port("layer_in", "layer", "input", 0, ["training"])]
        layer.outputs = [
            self._make_port("layer_out", "layer", "output", 0, ["training"])
        ]
        links = [
            Link(id_from="inp_out", id_to="norm_in"),
            Link(id_from="norm_out", id_to="layer_in"),
        ]
        graph = self._build_graph([inp, norm, layer], links)
        flow = analyze_phases(graph)
        self.assertNotIn("layer", flow["train_set"])

    def test_evaluation_seed_from_preprocessing(self):
        inp = Node(id="inp", type="input-data")
        norm = Node(id="norm", type="normalize")
        layer = Node(id="layer", type="layer")
        sink = Node(id="sink", type="output")  # consume layer output
        inp.outputs = [
            self._make_port("inp_out", "inp", "output", 0, ["preprocessing"])
        ]
        norm.inputs = [
            self._make_port("norm_in", "norm", "input", 0, ["preprocessing"])
        ]
        norm.outputs = [
            self._make_port(
                "norm_out", "norm", "output", 0, ["preprocessing", "evaluation"]
            )
        ]
        layer.inputs = [
            self._make_port("layer_in", "layer", "input", 0, ["evaluation"])
        ]
        layer.outputs = [
            self._make_port("layer_out", "layer", "output", 0, ["evaluation"])
        ]
        sink.inputs = [self._make_port("sink_in", "sink", "input", 0, ["evaluation"])]
        links = [
            Link(id_from="inp_out", id_to="norm_in"),
            Link(id_from="norm_out", id_to="layer_in"),
            Link(id_from="layer_out", id_to="sink_in"),
        ]
        graph = self._build_graph([inp, norm, layer, sink], links)
        flow = analyze_phases(graph)
        self.assertIn("layer", flow["eval_set"])
        self.assertIn("sink", flow["eval_set"])

    # ----------------------------------------------------------------
    # Conjunctive nodes
    # ----------------------------------------------------------------
    def test_add_requires_both_inputs(self):
        inp = Node(id="inp", type="input-data")
        src1 = Node(id="src1", type="normalize")
        src2 = Node(id="src2", type="normalize")
        add = Node(id="add", type="add")
        sink = Node(id="sink", type="output")
        inp.outputs = [
            self._make_port("inp_out", "inp", "output", 0, ["preprocessing"])
        ]
        src1.inputs = [self._make_port("s1_in", "src1", "input", 0, ["preprocessing"])]
        src1.outputs = [
            self._make_port(
                "s1_out", "src1", "output", 0, ["preprocessing", "training"]
            )
        ]
        src2.inputs = [self._make_port("s2_in", "src2", "input", 0, ["preprocessing"])]
        src2.outputs = [
            self._make_port("s2_out", "src2", "output", 0, ["preprocessing"])
        ]  # no training
        add.inputs = [
            self._make_port("add_in1", "add", "input", 0, ["training"]),
            self._make_port("add_in2", "add", "input", 1, ["training"]),
        ]
        add.outputs = [self._make_port("add_out", "add", "output", 0, ["training"])]
        sink.inputs = [self._make_port("sink_in", "sink", "input", 0, ["training"])]
        links = [
            Link(id_from="inp_out", id_to="s1_in"),
            Link(id_from="inp_out", id_to="s2_in"),
            Link(id_from="s1_out", id_to="add_in1"),
            Link(id_from="s2_out", id_to="add_in2"),
            Link(id_from="add_out", id_to="sink_in"),
        ]
        graph = self._build_graph([inp, src1, src2, add, sink], links)
        flow = analyze_phases(graph)
        # add requires both inputs; s2_out has no training → add not active
        self.assertNotIn("add", flow["train_set"])
        # sink requires add, so also not active
        self.assertNotIn("sink", flow["train_set"])

    def test_optimizer_conjunctive(self):
        inp = Node(id="inp", type="input-data")
        norm = Node(id="norm", type="normalize")
        out = Node(id="out", type="output")
        opt = Node(id="opt", type="optimizer")
        inp.outputs = [
            self._make_port("inp_out", "inp", "output", 0, ["preprocessing"])
        ]
        norm.inputs = [
            self._make_port("norm_in", "norm", "input", 0, ["preprocessing"])
        ]
        norm.outputs = [
            self._make_port(
                "norm_out", "norm", "output", 0, ["preprocessing", "training"]
            )
        ]
        out.inputs = [self._make_port("out_in", "out", "input", 0, ["training"])]
        out.outputs = [
            self._make_port("loss_p", "out", "output", 0, ["training"], role="loss")
        ]
        opt.inputs = [
            self._make_port("opt_loss", "opt", "input", 0, ["training"], role="loss"),
            self._make_port(
                "opt_labels", "opt", "input", 1, ["training"], role="labels"
            ),
        ]
        links = [
            Link(id_from="inp_out", id_to="norm_in"),
            Link(id_from="norm_out", id_to="out_in"),
            Link(id_from="loss_p", id_to="opt_loss"),
        ]
        graph = self._build_graph([inp, norm, out, opt], links)
        flow = analyze_phases(graph)
        self.assertIn("out", flow["train_set"])  # out activates via norm seed
        # opt activates because the disconnected label port is ignored
        self.assertIn("opt", flow["train_set"])

    def test_visualization_conjunctive(self):
        inp = Node(id="inp", type="input-data")
        viz = Node(id="viz", type="visualization")
        inp.outputs = [
            self._make_port("s_x", "inp", "output", 0, ["preprocessing", "evaluation"]),
            self._make_port("s_y", "inp", "output", 1, ["preprocessing", "evaluation"]),
        ]
        viz.inputs = [
            self._make_port("v_x", "viz", "input", 0, ["evaluation"], sub_type="coord"),
            self._make_port("v_y", "viz", "input", 1, ["evaluation"], sub_type="coord"),
            self._make_port("v_c", "viz", "input", 2, ["evaluation"], role="color"),
        ]
        links = [
            Link(id_from="s_x", id_to="v_x"),
            Link(id_from="s_y", id_to="v_y"),
        ]
        graph = self._build_graph([inp, viz], links)
        flow = analyze_phases(graph)
        # viz requires ALL connected inputs. Only x and y are connected; both satisfied → viz active.
        self.assertIn("viz", flow["eval_set"])

    # ----------------------------------------------------------------
    # Disjunctive nodes
    # ----------------------------------------------------------------
    def test_layer_with_multi_input_disjunctive(self):
        inp = Node(id="inp", type="input-data")
        n_train = Node(id="nt", type="normalize")
        n_eval = Node(id="ne", type="normalize")
        layer = Node(id="l", type="layer")
        sink = Node(id="sink", type="output")
        inp.outputs = [
            self._make_port("inp_out", "inp", "output", 0, ["preprocessing"])
        ]
        n_train.inputs = [self._make_port("nt_in", "nt", "input", 0, ["preprocessing"])]
        n_train.outputs = [
            self._make_port("nt_out", "nt", "output", 0, ["preprocessing", "training"])
        ]
        n_eval.inputs = [self._make_port("ne_in", "ne", "input", 0, ["preprocessing"])]
        n_eval.outputs = [
            self._make_port(
                "ne_out", "ne", "output", 0, ["preprocessing", "evaluation"]
            )
        ]
        layer.inputs = [
            self._make_port("l_in", "l", "input", 0, ["training", "evaluation"])
        ]
        layer.outputs = [
            self._make_port("l_out", "l", "output", 0, ["training", "evaluation"])
        ]
        sink.inputs = [
            self._make_port("sink_in", "sink", "input", 0, ["training", "evaluation"])
        ]
        links = [
            Link(id_from="inp_out", id_to="nt_in"),
            Link(id_from="inp_out", id_to="ne_in"),
            Link(id_from="nt_out", id_to="l_in"),
            Link(id_from="ne_out", id_to="l_in"),
            Link(id_from="l_out", id_to="sink_in"),
        ]
        graph = self._build_graph([inp, n_train, n_eval, layer, sink], links)
        flow = analyze_phases(graph)
        self.assertIn("l", flow["train_set"])
        self.assertIn("l", flow["eval_set"])
        self.assertIn("sink", flow["train_set"])
        self.assertIn("sink", flow["eval_set"])

    # ----------------------------------------------------------------
    # Output node relaxation
    # ----------------------------------------------------------------
    def test_output_node_at_least_one_input_and_output(self):
        inp = Node(id="inp", type="input-data")
        src = Node(id="src", type="layer")
        out = Node(id="out", type="output")
        inp.outputs = [
            self._make_port("inp_out", "inp", "output", 0, ["preprocessing"])
        ]
        src.inputs = [self._make_port("src_in", "src", "input", 0, ["preprocessing"])]
        src.outputs = [
            self._make_port(
                "src_out", "src", "output", 0, ["preprocessing", "training"]
            )
        ]
        out.inputs = [
            self._make_port("out_in_train", "out", "input", 0, ["training"]),
            self._make_port("out_in_test", "out", "input", 1, ["evaluation"]),
        ]
        out.outputs = [
            self._make_port("loss", "out", "output", 0, ["training"], role="loss"),
            self._make_port(
                "pred", "out", "output", 1, ["evaluation"], role="prediction"
            ),
            self._make_port(
                "eval", "out", "output", 2, ["evaluation"], role="evaluation"
            ),
        ]
        links = [
            Link(id_from="inp_out", id_to="src_in"),
            Link(id_from="src_out", id_to="out_in_train"),
        ]
        graph = self._build_graph([inp, src, out], links)
        flow = analyze_phases(graph)
        # output node requires an outgoing link on at least one output port → not active
        self.assertNotIn("out", flow["train_set"])
        self.assertNotIn("out", flow["eval_set"])

    # ----------------------------------------------------------------
    # Param ports are ignored for activation
    # ----------------------------------------------------------------
    def test_param_port_does_not_block_activation(self):
        inp = Node(id="inp", type="input-data")
        norm1 = Node(id="n1", type="normalize")
        norm2 = Node(id="n2", type="normalize")
        sink = Node(id="sink", type="output")
        inp.outputs = [
            self._make_port("inp_out", "inp", "output", 0, ["preprocessing"])
        ]
        norm1.inputs = [self._make_port("n1_in", "n1", "input", 0, ["preprocessing"])]
        norm1.outputs = [
            self._make_port("n1_out", "n1", "output", 0, ["preprocessing"])
        ]
        norm1.paramOutputs = [
            self._make_port(
                "n1_param", "n1", "output", 0, ["preprocessing"], port_kind="param"
            )
        ]
        norm2.inputs = [self._make_port("n2_in", "n2", "input", 0, ["preprocessing"])]
        norm2.paramInputs = [
            self._make_port("n2_param", "n2", "input", 0, [], port_kind="param")
        ]
        norm2.outputs = [
            self._make_port("n2_out", "n2", "output", 0, ["preprocessing"])
        ]
        sink.inputs = [
            self._make_port("sink_in", "sink", "input", 0, ["preprocessing"])
        ]
        links = [
            Link(id_from="inp_out", id_to="n1_in"),
            Link(id_from="n1_out", id_to="n2_in"),
            Link(id_from="n1_param", id_to="n2_param"),
            Link(id_from="n2_out", id_to="sink_in"),
        ]
        graph = self._build_graph([inp, norm1, norm2, sink], links)
        flow = analyze_phases(graph)
        # norm2 should activate even though its param input has no phases
        self.assertIn("n2", flow["preprocessing_set"])
        self.assertIn("sink", flow["preprocessing_set"])

    # ----------------------------------------------------------------
    # Topological ordering respects dependencies
    # ----------------------------------------------------------------
    def test_topological_order(self):
        inp = Node(id="a", type="input-data")
        b = Node(id="b", type="column-select")
        c = Node(id="c", type="normalize")
        sink = Node(id="sink", type="output")
        inp.outputs = [self._make_port("a_out", "a", "output", 0, ["preprocessing"])]
        b.inputs = [self._make_port("b_in", "b", "input", 0, ["preprocessing"])]
        b.outputs = [self._make_port("b_out", "b", "output", 0, ["preprocessing"])]
        c.inputs = [self._make_port("c_in", "c", "input", 0, ["preprocessing"])]
        c.outputs = [self._make_port("c_out", "c", "output", 0, ["preprocessing"])]
        sink.inputs = [
            self._make_port("sink_in", "sink", "input", 0, ["preprocessing"])
        ]
        links = [
            Link(id_from="a_out", id_to="b_in"),
            Link(id_from="b_out", id_to="c_in"),
            Link(id_from="c_out", id_to="sink_in"),
        ]
        graph = self._build_graph([inp, b, c, sink], links)
        flow = analyze_phases(graph)
        order = flow["preprocessing_order"]
        self.assertLess(order.index("a"), order.index("b"))
        self.assertLess(order.index("b"), order.index("c"))
        self.assertLess(order.index("c"), order.index("sink"))

    def test_param_dependency_ordering(self):
        inp = Node(id="inp", type="input-data")
        n1 = Node(id="n1", type="normalize")
        n2 = Node(id="n2", type="normalize")
        sink = Node(id="sink", type="output")
        inp.outputs = [
            self._make_port("inp_out", "inp", "output", 0, ["preprocessing"])
        ]
        n1.inputs = [self._make_port("n1_in", "n1", "input", 0, ["preprocessing"])]
        n1.outputs = [self._make_port("n1_out", "n1", "output", 0, ["preprocessing"])]
        n1.paramOutputs = [
            self._make_port(
                "n1_param", "n1", "output", 0, ["preprocessing"], port_kind="param"
            )
        ]
        n2.inputs = [self._make_port("n2_in", "n2", "input", 0, ["preprocessing"])]
        n2.paramInputs = [
            self._make_port("n2_param", "n2", "input", 0, [], port_kind="param")
        ]
        n2.outputs = [self._make_port("n2_out", "n2", "output", 0, ["preprocessing"])]
        sink.inputs = [
            self._make_port("sink_in", "sink", "input", 0, ["preprocessing"])
        ]
        links = [
            Link(id_from="inp_out", id_to="n1_in"),
            Link(id_from="n1_out", id_to="n2_in"),
            Link(id_from="n1_param", id_to="n2_param"),
            Link(id_from="n2_out", id_to="sink_in"),
        ]
        graph = self._build_graph([inp, n1, n2, sink], links)
        flow = analyze_phases(graph)
        self.assertIn("n2", flow["preprocessing_set"])
        self.assertLess(
            flow["preprocessing_order"].index("n1"),
            flow["preprocessing_order"].index("n2"),
        )

    # ----------------------------------------------------------------
    # highlight_path
    # ----------------------------------------------------------------
    def test_highlight_preprocessing(self):
        json_data = {
            "nodes": [
                {
                    "id": "inp",
                    "type": "input-data",
                    "x": 0,
                    "y": 0,
                    "inputPorts": [],
                    "outputPorts": [
                        {
                            "id": "inp_out",
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
                    "dataShape": None,
                },
            ],
            "links": [],
            "ports": [],
            "nodeCounter": 1,
        }
        result = highlight_path(json_data, "preprocessing")
        self.assertIn("inp", result["nodes"])
        self.assertEqual(result["links"], [])

    def test_highlight_with_links(self):
        json_data = {
            "nodes": [
                {
                    "id": "inp",
                    "type": "input-data",
                    "x": 0,
                    "y": 0,
                    "inputPorts": [],
                    "outputPorts": [
                        {
                            "id": "inp_out",
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
                },
                {
                    "id": "col",
                    "type": "column-select",
                    "x": 100,
                    "y": 0,
                    "inputPorts": [
                        {
                            "id": "col_in",
                            "type": "input",
                            "index": 0,
                            "subType": None,
                            "shape": None,
                            "bias": 0,
                            "portKind": "data",
                            "activationPhases": ["preprocessing"],
                        }
                    ],
                    "outputPorts": [
                        {
                            "id": "col_out",
                            "type": "output",
                            "index": 0,
                            "subType": None,
                            "shape": None,
                            "bias": 0,
                            "portKind": "data",
                            "activationPhases": ["preprocessing"],
                        }
                    ],
                    "numInputs": 1,
                    "numOutputs": 1,
                    "bias": 0,
                    "hasBias": False,
                    "paramInputs": [],
                    "paramOutputs": [],
                    "numParamInputs": 0,
                    "numParamOutputs": 0,
                    "selectedColumns": [0],
                },
                # add a sink so col's output is connected
                {
                    "id": "sink",
                    "type": "output",
                    "x": 200,
                    "y": 0,
                    "inputPorts": [
                        {
                            "id": "sink_in",
                            "type": "input",
                            "index": 0,
                            "subType": None,
                            "shape": None,
                            "bias": 0,
                            "portKind": "data",
                            "activationPhases": ["preprocessing"],
                        }
                    ],
                    "outputPorts": [],
                    "numInputs": 1,
                    "numOutputs": 0,
                    "bias": 0,
                    "hasBias": False,
                    "paramInputs": [],
                    "paramOutputs": [],
                    "numParamInputs": 0,
                    "numParamOutputs": 0,
                },
            ],
            "links": [
                {"from": "inp_out", "to": "col_in", "weight": 1},
                {"from": "col_out", "to": "sink_in", "weight": 1},
            ],
            "ports": [],
            "nodeCounter": 3,
        }
        result = highlight_path(json_data, "preprocessing")
        self.assertCountEqual(result["nodes"], ["inp", "col", "sink"])
        self.assertIn("inp_out→col_in", result["links"])
        self.assertIn("col_out→sink_in", result["links"])


if __name__ == "__main__":
    unittest.main()
