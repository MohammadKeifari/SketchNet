"""
Indexed views over a parsed graph.

:class:`Analysis` answers the questions the generator and the validator both
ask -- who feeds this port, which nodes form the model, where does a phase
enter -- from indices built once, instead of re-scanning ``graph.links`` at
every call site.
"""

from .graph import Graph, Node, Port

#: Node types that own trainable parameters, i.e. that belong inside nn.Module.
PARAMETRIC_TYPES = frozenset({"neuron", "layer", "conv2d", "batchnorm"})

#: Node types that only make sense inside the model, parametric or not.
MODEL_TYPES = PARAMETRIC_TYPES | {"dropout"}

#: Node types that run for their side effects and produce no tensor.
SIDE_EFFECT_TYPES = frozenset({"visualization", "print", "accuracy"})

PHASES = ("preprocessing", "training", "evaluation")


def remove_extra_optimizers(graph: Graph) -> Graph:
    """Keep only the first optimizer; the rest are dropped along with their links."""
    optimizers = [n for n in graph.nodes.values() if n.type == "optimizer"]
    if len(optimizers) <= 1:
        return graph

    dropped_nodes = {n.id for n in optimizers[1:]}
    dropped_ports = {
        port.id
        for node in optimizers[1:]
        for port in node.inputs + node.outputs + node.paramInputs + node.paramOutputs
    }

    graph.nodes = {k: v for k, v in graph.nodes.items() if k not in dropped_nodes}
    graph.ports = {k: v for k, v in graph.ports.items() if k not in dropped_ports}
    graph.links = [
        link
        for link in graph.links
        if link.id_from not in dropped_ports and link.id_to not in dropped_ports
    ]
    return graph


class Analysis:
    """Cached structural queries over a graph plus its phase analysis."""

    def __init__(self, graph: Graph, flow: dict):
        self.graph = graph
        self.flow = flow

        self._incoming = {}
        self._outgoing = {}
        for link in graph.links:
            self._incoming.setdefault(link.id_to, []).append(link)
            self._outgoing.setdefault(link.id_from, []).append(link)

        self._model_nodes = None

    # ------------------------------------------------------------------
    #  Link / port queries
    # ------------------------------------------------------------------
    def links_into(self, port_id: str) -> list:
        return self._incoming.get(port_id, [])

    def links_from(self, port_id: str) -> list:
        return self._outgoing.get(port_id, [])

    def is_connected(self, port: Port) -> bool:
        return bool(self._incoming.get(port.id) or self._outgoing.get(port.id))

    def sources(self, port: Port) -> list:
        """Source ports feeding ``port``, in link declaration order."""
        return [self.graph.ports[link.id_from] for link in self.links_into(port.id)]

    def first_source(self, port: Port):
        sources = self.sources(port)
        return sources[0] if sources else None

    def active_sources(self, port: Port, phase) -> list:
        """Sources that carry ``phase`` on both ends of the link.

        This is the rule that separates two situations the old generator could
        not tell apart: sources sharing a phase are genuinely parallel inputs,
        while sources on different phases are the same logical input seen from
        different phases.
        """
        if phase is None:
            return self.sources(port)
        if phase not in port.activation_phases:
            return []
        return [src for src in self.sources(port) if phase in src.activation_phases]

    def connected_inputs(self, node: Node) -> list:
        """Data (non-param) input ports of ``node`` that have an incoming link."""
        return [
            port
            for port in node.inputs
            if port.port_kind != "param" and self.links_into(port.id)
        ]

    def param_source(self, node: Node, index: int = 0):
        """Source port feeding the node's n-th param input, if any."""
        if len(node.paramInputs) <= index:
            return None
        return self.first_source(node.paramInputs[index])

    # ------------------------------------------------------------------
    #  Distinguished nodes
    # ------------------------------------------------------------------
    @property
    def output_node(self):
        return next(
            (n for n in self.graph.nodes.values() if n.type == "output"),
            None,
        )

    @property
    def optimizer(self):
        return self.flow.get("optimizer")

    def loss_port(self):
        """The output port the optimizer computes its loss from."""
        node = self.output_node
        if node is None:
            return None
        for port in node.outputs:
            if port.role == "loss":
                return port
        return node.outputs[0] if node.outputs else None

    # ------------------------------------------------------------------
    #  Model subgraph
    # ------------------------------------------------------------------
    def model_nodes(self) -> list:
        """Training-phase nodes that make up nn.Module, in execution order.

        These are the nodes reachable backwards from the Output node through
        the training phase, excluding anything already computed during
        preprocessing.
        """
        if self._model_nodes is not None:
            return self._model_nodes

        train_set = self.flow.get("train_set", set())
        output_id = next(
            (nid for nid in train_set if self.graph.nodes[nid].type == "output"),
            None,
        )
        if output_id is None:
            self._model_nodes = []
            return self._model_nodes

        reachable = set()
        queue = [output_id]
        while queue:
            current = queue.pop(0)
            if current in reachable:
                continue
            reachable.add(current)
            for pred in self.graph.predecessors(current):
                if pred in train_set and pred not in reachable:
                    queue.append(pred)

        pre_set = self.flow.get("preprocessing_set", set())
        self._model_nodes = [
            nid
            for nid in self.flow.get("train_order", [])
            if nid in reachable and nid not in pre_set
        ]
        return self._model_nodes

    def model_entry(self, phase: str):
        """First model node reached in ``phase``, or None."""
        model = set(self.model_nodes())
        order_key = "train_order" if phase == "training" else "eval_order"
        for nid in self.flow.get(order_key, []):
            if nid in model:
                return nid
        return None

    def evaluation_reuses_model(self) -> bool:
        """True when evaluation enters the model where training does.

        When it does not, the trained weights cannot be reused and evaluation
        is skipped -- the validator reports this as a warning.
        """
        eval_entry = self.model_entry("evaluation")
        if eval_entry is None:
            return True
        return eval_entry == self.model_entry("training")

    # ------------------------------------------------------------------
    #  Shape helpers
    # ------------------------------------------------------------------
    @staticmethod
    def rank(port: Port):
        """Number of dimensions of a port's propagated shape, or None."""
        if port is None or port.shape is None or not port.shape.shape:
            return None
        return len(port.shape.shape)

    @staticmethod
    def dim(port: Port, index: int):
        """Concrete size of one dimension, or None when unknown or symbolic."""
        if port is None or port.shape is None or not port.shape.shape:
            return None
        dims = port.shape.shape
        if index >= len(dims) or index < -len(dims):
            return None
        try:
            return int(dims[index])
        except (ValueError, TypeError):
            return None
