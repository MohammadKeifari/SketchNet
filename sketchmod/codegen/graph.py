from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


@dataclass
class Port:
    id: str
    node_id: str
    type: str
    index: int
    sub_type: Optional[str] = None
    port_kind: str = "data"
    role: Optional[str] = None
    activation_phases: List[str] = field(default_factory=list)
    shape: Optional[Any] = None
    bias: float = 0.0
    connection_limit: int = 1


@dataclass
class Link:
    id_from: str
    id_to: str
    weight: float = 1.0
    weight_shape: Optional[Any] = None
    has_weight: bool = False


@dataclass
class Node:
    id: str
    type: str
    inputs: List[Port] = field(default_factory=list)
    outputs: List[Port] = field(default_factory=list)
    paramInputs: List[Port] = field(default_factory=list)
    paramOutputs: List[Port] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    x: float = 0.0
    y: float = 0.0


@dataclass
class Graph:
    nodes: Dict[str, Node] = field(default_factory=dict)
    links: List[Link] = field(default_factory=list)
    ports: Dict[str, Port] = field(default_factory=dict)

    def add_node(self, node: Node):
        self.nodes[node.id] = node

    def add_link(self, link: Link):
        self.links.append(link)

    def successors(self, node_id: str) -> List[str]:
        out_ids = {p.id for p in self.nodes[node_id].outputs}
        targets = set()
        for link in self.links:
            if link.id_from in out_ids:
                targets.add(self.ports[link.id_to].node_id)
        return list(targets)

    def predecessors(self, node_id: str) -> List[str]:
        in_ids = {p.id for p in self.nodes[node_id].inputs}
        sources = set()
        for link in self.links:
            if link.id_to in in_ids:
                sources.add(self.ports[link.id_from].node_id)
        return list(sources)


def parse_graph(json_data: dict) -> Graph:
    graph = Graph()
    # First pass: create nodes and ports
    for n in json_data.get("nodes", []):
        node = Node(
            id=n["id"], type=n["type"], properties=n, x=n.get("x", 0), y=n.get("y", 0)
        )
        # Input ports
        for p in n.get("inputPorts", []):
            phases = p.get("activationPhases", [])
            port = Port(
                id=p["id"],
                node_id=n["id"],
                type="input",
                index=p["index"],
                sub_type=p.get("subType"),
                port_kind=p.get("portKind", "data"),
                role=p.get("role"),
                activation_phases=phases,
                bias=p.get("bias", 0),
            )
            node.inputs.append(port)
            graph.ports[port.id] = port

        # Output ports
        for p in n.get("outputPorts", []):
            phases = p.get("activationPhases", [])
            port = Port(
                id=p["id"],
                node_id=n["id"],
                type="output",
                index=p["index"],
                sub_type=p.get("subType"),
                port_kind=p.get("portKind", "data"),
                role=p.get("role"),
                activation_phases=phases,
                bias=p.get("bias", 0),
            )
            node.outputs.append(port)
            graph.ports[port.id] = port

        # Param input ports
        for p in n.get("paramInputs", []):
            port = Port(
                id=p["id"],
                node_id=n["id"],
                type="input",
                index=p["index"],
                sub_type=None,
                port_kind="param",
                role=None,
                activation_phases=p.get("activationPhases", []),
                bias=p.get("bias", 0),
            )
            node.paramInputs.append(port)
            graph.ports[port.id] = port

        # Param output ports
        for p in n.get("paramOutputs", []):
            port = Port(
                id=p["id"],
                node_id=n["id"],
                type="output",
                index=p["index"],
                sub_type=None,
                port_kind="param",
                role=None,
                activation_phases=p.get("activationPhases", []),
                bias=p.get("bias", 0),
            )
            node.paramOutputs.append(port)
            graph.ports[port.id] = port

        graph.add_node(node)

    # Apply default phases for ports that have empty activation_phases
    _apply_default_phases(graph)

    # Parse links
    for l in json_data.get("links", []):
        link = Link(
            id_from=l["from"],
            id_to=l["to"],
            weight=l.get("weight", 1.0),
            weight_shape=l.get("weightShape"),
            has_weight=l.get("hasWeight", False),
        )
        graph.add_link(link)

    return graph


def _apply_default_phases(graph: Graph):
    """Set default activation phases for ports that were not explicitly set."""
    for node in graph.nodes.values():
        if node.type == "input-data":
            for p in node.outputs:
                if not p.activation_phases:
                    p.activation_phases = ["preprocessing"]
        elif node.type in (
            "column-select",
            "row-select",
            "dim-select",
            "normalize",
            "onehot",
        ):
            for p in node.inputs + node.outputs:
                if not p.activation_phases:
                    p.activation_phases = ["preprocessing", "training", "evaluation"]
        elif node.type == "train-test":
            for p in node.outputs:
                if not p.activation_phases:
                    if p.sub_type == "train":
                        p.activation_phases = ["training"]
                    elif p.sub_type == "test":
                        p.activation_phases = ["evaluation"]
        elif node.type in (
            "neuron",
            "layer",
            "conv2d",
            "flatten",
            "dropout",
            "batchnorm",
            "add",
            "concat",
        ):
            for p in node.inputs + node.outputs:
                if not p.activation_phases:
                    p.activation_phases = ["training", "evaluation"]
        elif node.type == "output":
            for p in node.inputs:
                if not p.activation_phases:
                    if p.sub_type == "train":
                        p.activation_phases = ["training"]
                    elif p.sub_type == "test":
                        p.activation_phases = ["evaluation"]
            for p in node.outputs:
                if not p.activation_phases:
                    if p.role == "loss":
                        p.activation_phases = ["training"]
                    elif p.role in ("prediction", "evaluation"):
                        p.activation_phases = ["evaluation"]
        elif node.type == "optimizer":
            for p in node.inputs:
                if not p.activation_phases:
                    if p.role == "loss" or p.role == "labels":
                        p.activation_phases = ["training"]
        elif node.type == "visualization":
            for p in node.inputs:
                if not p.activation_phases:
                    p.activation_phases = ["evaluation"]
        # ParamPorts are left empty
