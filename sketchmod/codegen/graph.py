"""
Graph data structures for SketchNet code generation.

This module defines the core data structures representing a neural network graph:
- Port: Input/output connection point on a node with activation phases
- Link: Connection between two ports, potentially with learnable weights
- Node: A computational unit in the graph (layer, data transform, etc.)
- Graph: The complete computational graph containing all nodes and connections

The module also provides parsing functionality to convert JSON graph data from the
frontend into these Python objects, and phase assignment logic to determine when
each port is active during different execution phases (preprocessing, training, evaluation).
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


@dataclass
class Port:
    """
    Represents an input or output port on a node in the computation graph.

    A port is a connection point where data or parameters can flow between nodes.
    Each port has activation phases that determine during which execution phases
    (preprocessing, training, evaluation) it is active.

    Attributes:
        id (str): Unique identifier for this port.
        node_id (str): ID of the node that owns this port.
        type (str): Either "input" or "output".
        index (int): Position of this port in the node's port list.
        sub_type (Optional[str]): Additional classification (e.g., "train" vs "test" for
            train-test split nodes).
        port_kind (str): Either "data" for data flow or "param" for parameter flow.
            Defaults to "data".
        role (Optional[str]): Semantic role (e.g., "loss" for optimizer input, "prediction"
            for output).
        activation_phases (List[str]): Phases when this port is active:
            ["preprocessing"], ["training"], ["evaluation"], or combinations thereof.
        shape (Optional[Any]): Tensor shape specification (used in some contexts).
        bias (float): Bias value if applicable. Defaults to 0.0.
        connection_limit (int): Maximum number of connections to this port. Defaults to 1.
    """

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
    """
    Represents a connection between two ports in the computation graph.

    A link carries data or parameters from an output port to an input port.
    Links can optionally have learnable weights (for layers that combine inputs).

    Attributes:
        id_from (str): ID of the source port.
        id_to (str): ID of the destination port.
        weight (float): Edge weight multiplier. Defaults to 1.0.
        weight_shape (Optional[Any]): Shape of the weight tensor if has_weight is True.
        has_weight (bool): Whether this link has learnable weights (e.g., for add/concat
            layers that combine multiple inputs). Defaults to False.
    """

    id_from: str
    id_to: str
    weight: float = 1.0
    weight_shape: Optional[Any] = None
    has_weight: bool = False


@dataclass
class Node:
    """
    Represents a computational unit (node) in the computation graph.

    A node can represent various types of operations: data input, preprocessing transforms,
    neural network layers, output operations, optimizers, etc.

    Attributes:
        id (str): Unique identifier for this node.
        type (str): Node type (e.g., "input-data", "conv2d", "layer", "optimizer",
            "output", "column-select", etc.).
        inputs (List[Port]): Input data ports for this node.
        outputs (List[Port]): Output data ports for this node.
        paramInputs (List[Port]): Parameter/configuration input ports.
        paramOutputs (List[Port]): Parameter/configuration output ports.
        properties (Dict[str, Any]): Additional configuration properties specific to
            this node type (e.g., kernel size for conv2d, dataset file name for input-data).
        x (float): X coordinate in the visual editor. Defaults to 0.0.
        y (float): Y coordinate in the visual editor. Defaults to 0.0.
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
    Represents a complete computation graph for neural network definition.

    The graph is a directed acyclic graph (DAG) where nodes are computational units
    and links are data/parameter flows between them. It includes utility methods for
    traversing the graph structure.

    Attributes:
        nodes (Dict[str, Node]): Mapping of node IDs to Node objects.
        links (List[Link]): List of all connections in the graph.
        ports (Dict[str, Port]): Mapping of port IDs to Port objects for quick lookup.
    """

    nodes: Dict[str, Node] = field(default_factory=dict)
    links: List[Link] = field(default_factory=list)
    ports: Dict[str, Port] = field(default_factory=dict)

    def add_node(self, node: Node):
        """
        Add a node to the graph.

        Args:
            node (Node): The node to add.
        """
        self.nodes[node.id] = node

    def add_link(self, link: Link):
        """
        Add a link (connection) to the graph.

        Args:
            link (Link): The link to add.
        """
        self.links.append(link)

    def successors(self, node_id: str) -> List[str]:
        """
        Get all nodes that receive output from the given node.

        Args:
            node_id (str): The ID of the source node.

        Returns:
            List[str]: List of node IDs that are downstream from the given node.
        """
        out_ids = {p.id for p in self.nodes[node_id].outputs}
        targets = set()
        for link in self.links:
            if link.id_from in out_ids:
                targets.add(self.ports[link.id_to].node_id)
        return list(targets)

    def predecessors(self, node_id: str) -> List[str]:
        """
        Get all nodes that feed input to the given node.

        Args:
            node_id (str): The ID of the target node.

        Returns:
            List[str]: List of node IDs that are upstream from the given node.
        """
        in_ids = {p.id for p in self.nodes[node_id].inputs}
        sources = set()
        for link in self.links:
            if link.id_to in in_ids:
                sources.add(self.ports[link.id_from].node_id)
        return list(sources)


def parse_graph(json_data: dict) -> Graph:
    """
    Parse JSON graph data into a Graph object.

    Converts JSON representation of a computation graph (from the SketchNet frontend)
    into Python objects. Performs two main steps:
    1. Creates nodes and ports from the JSON data
    2. Applies default activation phases to ports that don't have explicit phases

    Args:
        json_data (dict): JSON data with keys:
            - "nodes": List of node definitions
            - "links": List of connection definitions
            Each node should have "id", "type", "inputPorts", "outputPorts",
            "paramInputs", "paramOutputs", and optional "x", "y" coordinates.

    Returns:
        Graph: The parsed computation graph with all nodes, ports, and links.
    """
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
    # _apply_default_phases(graph)

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
    """
    Set default activation phases for ports that were not explicitly specified.

    Different node types have different default activation phase patterns:
    - input-data: outputs are active in preprocessing
    - preprocessing nodes (column-select, normalize, etc.): all ports active in
      preprocessing, training, and evaluation
    - train-test split: train output active only in training, test output only in evaluation
    - model layers (conv2d, layer, etc.): all ports active in training and evaluation
    - output node: inputs vary by sub_type; outputs vary by role (loss, prediction, etc.)
    - optimizer: loss and label inputs active in training
    - visualization: inputs active in evaluation

    Args:
        graph (Graph): The graph whose port phases should be populated.
    """
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
