"""
Unit tests for topological ordering of nodes.
"""

import unittest
from sketchmod.codegen.graph import Graph, Node, Port, Link
from sketchmod.codegen.orderer import topological_sort


class TopologicalSortTest(unittest.TestCase):
    def _make_graph(self, nodes, links):
        graph = Graph()
        for n in nodes:
            graph.nodes[n.id] = n
            for p in n.inputs + n.outputs + n.paramInputs + n.paramOutputs:
                graph.ports[p.id] = p
        graph.links = links
        return graph

    def test_simple_chain(self):
        a = Node(id="a", type="input-data")
        b = Node(id="b", type="normalize")
        c = Node(id="c", type="layer")
        a.outputs = [Port(id="a_out", node_id="a", type="output", index=0)]
        b.inputs = [Port(id="b_in", node_id="b", type="input", index=0)]
        b.outputs = [Port(id="b_out", node_id="b", type="output", index=0)]
        c.inputs = [Port(id="c_in", node_id="c", type="input", index=0)]
        links = [
            Link(id_from="a_out", id_to="b_in"),
            Link(id_from="b_out", id_to="c_in"),
        ]
        graph = self._make_graph([a, b, c], links)
        order = topological_sort(graph, {"a", "b", "c"})
        self.assertEqual(order, ["a", "b", "c"])

    def test_param_dependency(self):
        n1 = Node(id="norm1", type="normalize")
        n2 = Node(id="norm2", type="normalize")
        pout = Port(
            id="n1_param", node_id="norm1", type="output", index=0, port_kind="param"
        )
        pin = Port(
            id="n2_param", node_id="norm2", type="input", index=0, port_kind="param"
        )
        n1.paramOutputs = [pout]
        n2.paramInputs = [pin]
        links = [Link(id_from="n1_param", id_to="n2_param")]
        graph = self._make_graph([n1, n2], links)
        order = topological_sort(graph, {"norm1", "norm2"})
        self.assertEqual(order, ["norm1", "norm2"])

    def test_two_parallel_branches(self):
        a = Node(id="a", type="input-data")
        b = Node(id="b", type="column-select")
        c = Node(id="c", type="column-select")
        d = Node(id="d", type="concat")
        a.outputs = [Port(id="a_out", node_id="a", type="output", index=0)]
        b.inputs = [Port(id="b_in", node_id="b", type="input", index=0)]
        b.outputs = [Port(id="b_out", node_id="b", type="output", index=0)]
        c.inputs = [Port(id="c_in", node_id="c", type="input", index=0)]
        c.outputs = [Port(id="c_out", node_id="c", type="output", index=0)]
        d.inputs = [Port(id="d_in", node_id="d", type="input", index=0)]
        links = [
            Link(id_from="a_out", id_to="b_in"),
            Link(id_from="a_out", id_to="c_in"),
            Link(id_from="b_out", id_to="d_in"),
            Link(id_from="c_out", id_to="d_in"),
        ]
        graph = self._make_graph([a, b, c, d], links)
        order = topological_sort(graph, {"a", "b", "c", "d"})
        self.assertEqual(order.index("a"), 0)
        self.assertLess(order.index("b"), order.index("d"))
        self.assertLess(order.index("c"), order.index("d"))
        self.assertEqual(len(order), 4)

    def test_multiple_inputs_single_source(self):
        # Two nodes that both depend on the same source
        a = Node(id="a", type="input-data")
        b = Node(id="b", type="layer")
        c = Node(id="c", type="layer")
        a.outputs = [Port(id="a_out", node_id="a", type="output", index=0)]
        b.inputs = [Port(id="b_in", node_id="b", type="input", index=0)]
        c.inputs = [Port(id="c_in", node_id="c", type="input", index=0)]
        links = [
            Link(id_from="a_out", id_to="b_in"),
            Link(id_from="a_out", id_to="c_in"),
        ]
        graph = self._make_graph([a, b, c], links)
        order = topological_sort(graph, {"a", "b", "c"})
        self.assertEqual(order[0], "a")
        self.assertIn("b", order)
        self.assertIn("c", order)

    def test_subset_sort(self):
        a = Node(id="a", type="input-data")
        b = Node(id="b", type="normalize")
        c = Node(id="c", type="layer")
        a.outputs = [Port(id="a_out", node_id="a", type="output", index=0)]
        b.inputs = [Port(id="b_in", node_id="b", type="input", index=0)]
        b.outputs = [Port(id="b_out", node_id="b", type="output", index=0)]
        c.inputs = [Port(id="c_in", node_id="c", type="input", index=0)]
        links = [
            Link(id_from="a_out", id_to="b_in"),
            Link(id_from="b_out", id_to="c_in"),
        ]
        graph = self._make_graph([a, b, c], links)
        # sort only {a, c} – b is missing, so c has no incoming edge from a
        order = topological_sort(graph, {"a", "c"})
        self.assertCountEqual(order, ["a", "c"])  # both present, any order valid


if __name__ == "__main__":
    unittest.main()
