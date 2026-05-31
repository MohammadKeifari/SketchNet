from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


@dataclass
class Port:
    id: str
    node_id: str
    type: str  # "input" / "output"
    index: int
    sub_type: Optional[str] = None
    port_kind: str = "data"  # "data", "multi", "role", "param"
    role: Optional[str] = None
    activation_mode: str = "every_batch"  # will be overridden
    shape: Optional[Any] = None  # ignore
    bias: float = 0.0
    connection_limit: int = 1


@dataclass
class Link:
    id_from: str
    id_to: str
    weight: float = 1.0  # default 1 (will be set from JSON)
    weight_shape: Optional[Any] = None
    has_weight: bool = False


@dataclass
class Node:
    id: str
    type: str
    inputs: List[Port] = field(default_factory=list)
    outputs: List[Port] = field(default_factory=list)
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

    def get_node(self, node_id: str) -> Node:
        return self.nodes[node_id]

    def get_port(self, port_id: str) -> Port:
        return self.ports[port_id]

    # Build adjacency
    def successors(self, node_id: str) -> List[str]:
        """Nodes that receive output from this node"""
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
            port = Port(
                id=p["id"],
                node_id=n["id"],
                type="input",
                index=p["index"],
                sub_type=p.get("subType"),
                port_kind=p.get("portKind", "data"),
                role=p.get("role"),
                activation_mode=p.get("activationMode", "every_batch"),
                bias=p.get("bias", 0),
            )
            # data/multi ports on non-model nodes default to "both" if not set explicitly
            if port.port_kind in ("data", "multi") and not p.get("activationMode"):
                if node.type not in (
                    "neuron",
                    "layer",
                    "conv2d",
                    "flatten",
                    "dropout",
                    "batchnorm",
                    "add",
                    "concat",
                    "output",
                ):
                    port.activation_mode = "both"
            node.inputs.append(port)
            graph.ports[port.id] = port

        # Output ports
        for p in n.get("outputPorts", []):
            port = Port(
                id=p["id"],
                node_id=n["id"],
                type="output",
                index=p["index"],
                sub_type=p.get("subType"),
                port_kind=p.get("portKind", "data"),
                role=p.get("role"),
                activation_mode=p.get("activationMode", "every_batch"),
                bias=p.get("bias", 0),
            )
            # Role ports: apply default based on role if no explicit activation
            if port.port_kind == "role" and not p.get("activationMode"):
                role_defaults = {
                    "loss": "every_batch",
                    "prediction": "last_batch",
                    "evaluation": "last_batch",
                    "labels": "every_batch",
                    "color": "last_batch",
                }
                port.activation_mode = role_defaults.get(port.role, "every_batch")
            # Data/multi ports on non-model nodes default to "both"
            if port.port_kind in ("data", "multi") and not p.get("activationMode"):
                if node.type not in (
                    "neuron",
                    "layer",
                    "conv2d",
                    "flatten",
                    "dropout",
                    "batchnorm",
                    "add",
                    "concat",
                    "output",
                ):
                    port.activation_mode = "both"
            node.outputs.append(port)
            graph.ports[port.id] = port

        # Special default for TrainTestSplit outputs if not explicitly set
        if node.type == "train-test":
            for port in node.outputs:
                # Find the original port dict to check if activationMode was provided
                orig_ports = n.get("outputPorts", [])
                for orig_port in orig_ports:
                    if orig_port["id"] == port.id:
                        if "activationMode" not in orig_port:
                            if port.sub_type == "train":
                                port.activation_mode = "every_batch"
                            elif port.sub_type == "test":
                                port.activation_mode = "last_batch"
                        break

        graph.add_node(node)

    # Parse links
    for l in json_data.get("links", []):
        link = Link(
            id_from=l["from"],
            id_to=l["to"],
            weight=l.get("weight", 1.0) if l.get("weight") != 0 else 1.0,
            weight_shape=l.get("weightShape"),
            has_weight=l.get("hasWeight", False),
        )
        graph.add_link(link)

    return graph
