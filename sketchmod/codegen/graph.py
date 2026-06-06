"""
Graph data structures for SketchNet code generation.

Defines Port, Link, Node, and Graph.  Parses front‑end JSON into Python objects.
No default phase assignment – phases come exclusively from the user’s canvas.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


@dataclass
class Port:
    """
    A connection point on a node.

    Attributes:
        id: unique identifier (from canvas)
        node_id: id of the owning node
        type: "input" or "output"
        index: position among the node’s ports of the same type
        sub_type: visual hint only (e.g. "train", "coord") – never used for logic
        port_kind: "data" or "param"
        role: visual role (e.g. "loss", "prediction") – never used for logic
        activation_phases: list of phases where this port is checked (set by user)
        shape: tensor shape information (may be used by validators)
        bias: bias value if applicable
    """

    id: str
    node_id: str
    type: str  # "input" or "output"
    index: int
    sub_type: Optional[str] = None
    port_kind: str = "data"
    role: Optional[str] = None
    activation_phases: List[str] = field(default_factory=list)
    shape: Optional[Any] = None
    bias: float = 0.0


@dataclass
class Link:
    """Connection between two ports."""

    id_from: str  # source port id
    id_to: str  # target port id
    weight: float = 1.0
    weight_shape: Optional[Any] = None
    has_weight: bool = False


@dataclass
class Node:
    """
    A computational unit in the graph.

    Attributes:
        id: unique identifier
        type: node type string (e.g. "layer", "input-data", "output")
        inputs, outputs: data ports
        paramInputs, paramOutputs: parameter ports
        properties: all original JSON properties (activation, numNeurons, etc.)
        x, y: canvas coordinates
    """

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
    """
    The complete computation graph.

    Provides dictionary lookups for nodes and ports, and
    graph traversal helpers (successors, predecessors) that consider
    both data and param links.
    """

    nodes: Dict[str, Node] = field(default_factory=dict)
    links: List[Link] = field(default_factory=list)
    ports: Dict[str, Port] = field(default_factory=dict)

    def successors(self, node_id: str) -> List[str]:
        """All nodes that receive output from the given node (data + param)."""
        out_ids = set()
        node = self.nodes[node_id]
        for p in node.outputs + node.paramOutputs:
            out_ids.add(p.id)
        targets = set()
        for link in self.links:
            if link.id_from in out_ids:
                targets.add(self.ports[link.id_to].node_id)
        return list(targets)

    def predecessors(self, node_id: str) -> List[str]:
        """All nodes that feed input into the given node (data + param)."""
        in_ids = set()
        node = self.nodes[node_id]
        for p in node.inputs + node.paramInputs:
            in_ids.add(p.id)
        sources = set()
        for link in self.links:
            if link.id_to in in_ids:
                sources.add(self.ports[link.id_from].node_id)
        return list(sources)


def parse_graph(json_data: dict) -> Graph:
    """
    Convert front‑end JSON into a Graph object.

    Expects:
        "nodes": list of node dicts with id, type, inputPorts, outputPorts,
                 paramInputs, paramOutputs
        "links": list of link dicts with from, to, weight, weightShape, hasWeight
    """
    graph = Graph()

    # --- Nodes & ports ---
    for n in json_data.get("nodes", []):
        node = Node(
            id=n["id"],
            type=n["type"],
            properties=n,
            x=n.get("x", 0),
            y=n.get("y", 0),
        )

        # Helper to create a Port from a port dict
        def make_port(p: dict, port_type: str, kind: str, idx: int) -> Port:
            port = Port(
                id=p["id"],
                node_id=n["id"],
                type=port_type,
                index=idx,
                sub_type=p.get("subType"),
                port_kind=kind,
                role=p.get("role"),
                activation_phases=p.get("activationPhases", []),
                bias=p.get("bias", 0.0),
            )
            return port

        # Data inputs
        for i, p in enumerate(n.get("inputPorts", [])):
            port = make_port(p, "input", p.get("portKind", "data"), i)
            node.inputs.append(port)
            graph.ports[port.id] = port

        # Data outputs
        for i, p in enumerate(n.get("outputPorts", [])):
            port = make_port(p, "output", p.get("portKind", "data"), i)
            node.outputs.append(port)
            graph.ports[port.id] = port

        # Param inputs
        for i, p in enumerate(n.get("paramInputs", [])):
            port = make_port(p, "input", "param", i)
            node.paramInputs.append(port)
            graph.ports[port.id] = port

        # Param outputs
        for i, p in enumerate(n.get("paramOutputs", [])):
            port = make_port(p, "output", "param", i)
            node.paramOutputs.append(port)
            graph.ports[port.id] = port

        graph.nodes[node.id] = node

    # --- Links ---
    for l in json_data.get("links", []):
        link = Link(
            id_from=l["from"],
            id_to=l["to"],
            weight=l.get("weight", 1.0),
            weight_shape=l.get("weightShape"),
            has_weight=l.get("hasWeight", False),
        )
        graph.links.append(link)

    return graph
