"""
Graph data structures for SketchNet code generation.

Parses front‑end JSON into Python objects, then runs a deterministic,
symbolic shape propagation so every port carries a reliable ShapeInfo.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Union
import math
import sympy


# ---------------------------------------------------------------------------
#  Symbolic dimension helper
# ---------------------------------------------------------------------------
class ShapeDim:
    """
    A single dimension that can be a concrete int or a symbolic expression.
    Arithmetic operations produce new ShapeDim with simplified sympy expressions.
    """

    def __init__(self, value: Union[int, str, sympy.Expr]):
        if isinstance(value, int):
            self._value = sympy.Integer(value)
        elif isinstance(value, str):
            s = value.strip()
            # if the string is a plain integer (possibly negative), use it directly
            if s.isdigit() or (s.startswith("-") and s[1:].isdigit()):
                self._value = sympy.Integer(int(s))
            else:
                self._value = sympy.symbols(s)
        elif isinstance(value, sympy.Expr):
            self._value = value
        else:
            raise TypeError(
                f"ShapeDim expects int, str, or sympy.Expr, got {type(value)}"
            )
        self._value = sympy.simplify(self._value)

    @property
    def is_concrete(self) -> bool:
        return self._value.is_Integer

    @property
    def is_symbolic(self) -> bool:
        return not self.is_concrete

    def __int__(self) -> int:
        if self.is_concrete:
            return int(self._value)
        raise ValueError(f"Cannot convert symbolic dimension {self._value} to int")

    def __repr__(self):
        return str(self._value)

    def __str__(self):
        return str(self._value)

    # Arithmetic
    def __add__(self, other):
        if isinstance(other, ShapeDim):
            return ShapeDim(self._value + other._value)
        if isinstance(other, int):
            return ShapeDim(self._value + other)
        return NotImplemented

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        if isinstance(other, ShapeDim):
            return ShapeDim(self._value - other._value)
        if isinstance(other, int):
            return ShapeDim(self._value - other)
        return NotImplemented

    def __mul__(self, other):
        if isinstance(other, ShapeDim):
            return ShapeDim(self._value * other._value)
        if isinstance(other, (int, float)):
            return ShapeDim(self._value * other)
        return NotImplemented

    def __rmul__(self, other):
        return self.__mul__(other)

    def __floordiv__(self, other):
        if isinstance(other, ShapeDim):
            return ShapeDim(sympy.floor(self._value / other._value))
        if isinstance(other, int):
            return ShapeDim(sympy.floor(self._value / other))
        return NotImplemented

    def __truediv__(self, other):
        # Use floating division? We'll stick to floor division for integer shapes.
        return self.__floordiv__(other)

    def __eq__(self, other):
        if isinstance(other, ShapeDim):
            return self._value == other._value
        if isinstance(other, int):
            return self._value == other
        return False

    def __hash__(self):
        return hash(self._value)


# ---------------------------------------------------------------------------
#  Shape information
# ---------------------------------------------------------------------------
@dataclass
class ShapeInfo:
    """Holds tensor shape information."""

    shape: List[ShapeDim] = field(default_factory=list)
    dtype: str = "float32"

    @property
    def known(self) -> bool:
        """True if every dimension is a concrete integer."""
        return all(d.is_concrete for d in self.shape) if self.shape else False

    @property
    def symbolic(self) -> bool:
        """True if any dimension is symbolic."""
        return any(d.is_symbolic for d in self.shape)

    @staticmethod
    def unknown():
        return ShapeInfo(shape=[])


# ---------------------------------------------------------------------------
#  Core graph objects (unchanged except shape annotation)
# ---------------------------------------------------------------------------
@dataclass
class Port:
    id: str
    node_id: str
    type: str  # "input" | "output"
    index: int
    sub_type: Optional[str] = None
    port_kind: str = "data"
    role: Optional[str] = None
    activation_phases: List[str] = field(default_factory=list)
    shape: Optional[ShapeInfo] = None
    bias: float = 0.0


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

    def successors(self, node_id: str) -> List[str]:
        out_ids = {p.id for p in self.nodes[node_id].outputs}
        out_ids.update(p.id for p in self.nodes[node_id].paramOutputs)
        targets = set()
        for link in self.links:
            if link.id_from in out_ids:
                targets.add(self.ports[link.id_to].node_id)
        return list(targets)

    def predecessors(self, node_id: str) -> List[str]:
        in_ids = {p.id for p in self.nodes[node_id].inputs}
        in_ids.update(p.id for p in self.nodes[node_id].paramInputs)
        sources = set()
        for link in self.links:
            if link.id_to in in_ids:
                sources.add(self.ports[link.id_from].node_id)
        return list(sources)


# ---------------------------------------------------------------------------
#  JSON → Graph
# ---------------------------------------------------------------------------
def parse_graph(json_data: dict) -> Graph:
    graph = Graph()

    for n in json_data.get("nodes", []):
        node = Node(
            id=n["id"],
            type=n["type"],
            properties=n,
            x=n.get("x", 0),
            y=n.get("y", 0),
        )

        def make_port(p: dict, port_type: str, kind: str, idx: int) -> Port:
            return Port(
                id=p["id"],
                node_id=n["id"],
                type=port_type,
                index=idx,
                sub_type=p.get("subType"),
                port_kind=kind,
                role=p.get("role"),
                activation_phases=p.get("activationPhases", []),
                bias=p.get("bias", 0.0),
                shape=None,  # will be filled by propagation
            )

        # data inputs
        for i, p in enumerate(n.get("inputPorts", [])):
            port = make_port(p, "input", p.get("portKind", "data"), i)
            node.inputs.append(port)
            graph.ports[port.id] = port

        # data outputs
        for i, p in enumerate(n.get("outputPorts", [])):
            port = make_port(p, "output", p.get("portKind", "data"), i)
            node.outputs.append(port)
            graph.ports[port.id] = port

        # param inputs
        for i, p in enumerate(n.get("paramInputs", [])):
            port = make_port(p, "input", "param", i)
            node.paramInputs.append(port)
            graph.ports[port.id] = port

        # param outputs
        for i, p in enumerate(n.get("paramOutputs", [])):
            port = make_port(p, "output", "param", i)
            node.paramOutputs.append(port)
            graph.ports[port.id] = port

        graph.nodes[node.id] = node

    for l in json_data.get("links", []):
        link = Link(
            id_from=l["from"],
            id_to=l["to"],
            weight=l.get("weight", 1.0),
            weight_shape=l.get("weightShape"),
            has_weight=l.get("hasWeight", False),
        )
        graph.links.append(link)

    # ----- Run symbolic shape propagation -----
    _propagate_shapes(graph)

    return graph


# ---------------------------------------------------------------------------
#  Shape propagation engine
# ---------------------------------------------------------------------------
def _parse_data_shape(data_shape: str) -> List[ShapeDim]:
    """Convert a shape string like '(100, 3)' or '(None, 3)' into a list of ShapeDim."""
    if not data_shape:
        return []
    cleaned = data_shape.strip("()")
    parts = cleaned.split(",")
    result = []
    for p in parts:
        p = p.strip()
        if p.isdigit() or (p.startswith("-") and p[1:].isdigit()):
            result.append(ShapeDim(int(p)))
        else:
            result.append(ShapeDim(p))  # symbolic name
    return result


def _first_input_shape(node, graph):
    """Return the first available input shape, or None."""
    for port in node.inputs:
        for link in graph.links:
            if link.id_to == port.id:
                src = graph.ports[link.id_from]
                if src.shape is not None:
                    return src.shape
    return None


def _set_output_shape(node, shape: ShapeInfo):
    """Assign the same shape to all output ports of the node."""
    for port in node.outputs:
        port.shape = shape


def _propagate_shapes(graph: Graph):
    """
    Topologically sort all nodes and propagate shapes from InputData
    through the graph, assigning a ShapeInfo to every data port.
    """
    # ---- Kahn's algorithm ----
    in_degree = {nid: 0 for nid in graph.nodes}
    adj = {nid: [] for nid in graph.nodes}
    for nid in graph.nodes:
        for succ in graph.successors(nid):
            adj[nid].append(succ)
            in_degree[succ] += 1

    queue = [nid for nid, deg in in_degree.items() if deg == 0]
    topo_order = []
    while queue:
        nid = queue.pop(0)
        topo_order.append(nid)
        for succ in adj[nid]:
            in_degree[succ] -= 1
            if in_degree[succ] == 0:
                queue.append(succ)

    # ---- Process nodes ----
    for nid in topo_order:
        node = graph.nodes[nid]
        if node.type == "input-data":
            _shape_input_data(node)
        elif node.type == "column-select":
            _shape_column_select(node, graph)
        elif node.type == "row-select":
            _shape_row_select(node, graph)
        elif node.type == "dim-select":
            _shape_dim_select(node, graph)
        elif node.type == "train-test":
            _shape_train_test(node, graph)
        elif node.type == "normalize":
            _shape_passthrough(node, graph)
        elif node.type == "neuron":
            _shape_layer(node, graph, out_features=1)
        elif node.type == "layer":
            _shape_layer(node, graph, out_features=None)
        elif node.type == "conv2d":
            _shape_conv2d(node, graph)
        elif node.type == "flatten":
            _shape_flatten(node, graph)
        elif node.type in ("dropout", "batchnorm"):
            _shape_passthrough(node, graph)
        elif node.type == "add":
            _shape_add(node, graph)
        elif node.type == "concat":
            _shape_concat(node, graph)
        elif node.type == "onehot":
            _shape_onehot(node, graph)
        elif node.type == "deonehot":
            _shape_deonehot(node, graph)
        elif node.type == "output":
            _shape_output(node, graph)
        elif node.type == "reshape":
            _shape_reshape(node, graph)


# ---------------------------------------------------------------------------
#  Per‑node shape helpers (symbolic)
# ---------------------------------------------------------------------------
def _shape_passthrough(node, graph):
    shape = _first_input_shape(node, graph)
    if shape:
        _set_output_shape(node, shape)


def _shape_input_data(node):
    ds = node.properties.get("dataShape")
    dims = _parse_data_shape(ds) if ds else []
    for port in node.outputs:
        port.shape = ShapeInfo(shape=dims)


def _shape_column_select(node, graph):
    cols = node.properties.get("selectedColumns", [])
    col_str = node.properties.get("columnInput", "")
    inp = _first_input_shape(node, graph)
    if not inp or not inp.shape:
        return
    n_rows = inp.shape[0] if inp.shape else None
    if cols:
        out_cols = ShapeDim(len(cols))
    elif col_str:
        # Try to evaluate simple ranges symbolically
        out_cols = None
        try:
            if ":" in col_str:
                parts = col_str.split(":")
                start = int(parts[0]) if parts[0] else 0
                end = int(parts[1]) if parts[1] else None
                if end is not None:
                    out_cols = ShapeDim(end - start)
        except:
            pass
        if out_cols is None:
            out_cols = ShapeDim(col_str)  # keep as symbolic name
    else:
        out_cols = inp.shape[1] if len(inp.shape) > 1 else ShapeDim("?")
    _set_output_shape(node, ShapeInfo(shape=[n_rows, out_cols]))


def _shape_row_select(node, graph):
    method = node.properties.get("method", "first-n")
    value = node.properties.get("value", "100")
    inp = _first_input_shape(node, graph)
    if not inp or not inp.shape:
        return
    n_rows = None
    try:
        if method in ("first-n", "random"):
            n_rows = ShapeDim(int(value))
        elif method == "slice":
            parts = value.split(":")
            start = int(parts[0]) if parts[0] else 0
            end = int(parts[1]) if parts[1] else None
            if end is not None:
                n_rows = ShapeDim(end - start)
        elif method == "indices":
            n_rows = ShapeDim(
                len([int(x.strip()) for x in value.split(",") if x.strip()])
            )
    except:
        n_rows = ShapeDim(value)  # fallback symbolic
    if n_rows is None:
        n_rows = inp.shape[0] if inp.shape else ShapeDim("?")
    _set_output_shape(node, ShapeInfo(shape=[n_rows] + list(inp.shape[1:])))


def _shape_dim_select(node, graph):
    inp = _first_input_shape(node, graph)
    if not inp or not inp.shape:
        return
    dims = node.properties.get("dimSelections", [])
    out_shape = []
    for i, sel in enumerate(dims):
        if not sel or sel.strip() == ":":
            out_shape.append(inp.shape[i] if i < len(inp.shape) else ShapeDim("?"))
        else:
            out_shape.append(ShapeDim(sel))  # keep symbolic
    _set_output_shape(node, ShapeInfo(shape=out_shape))


def _shape_train_test(node, graph):
    inp = _first_input_shape(node, graph)
    if not inp or not inp.shape:
        return
    ratio = node.properties.get("trainRatio", 0.7)
    n = inp.shape[0]
    # train = floor(n * ratio)
    train_n = ShapeDim(sympy.floor(n._value * ratio))
    test_n = ShapeDim(n._value - train_n._value)
    for port in node.outputs:
        if port.index == 0:
            shape = [train_n] + list(inp.shape[1:])
        else:
            shape = [test_n] + list(inp.shape[1:])
        port.shape = ShapeInfo(shape=shape)


def _shape_layer(node, graph, out_features=None):
    if out_features is None:
        out_features = node.properties.get("numNeurons", 64)
    inp = _first_input_shape(node, graph)
    if not inp or not inp.shape or len(inp.shape) < 2:
        return
    n = inp.shape[0]
    _set_output_shape(node, ShapeInfo(shape=[n, ShapeDim(out_features)]))


def _shape_conv2d(node, graph):
    inp = _first_input_shape(node, graph)
    if not inp or not inp.shape or len(inp.shape) < 4:
        return
    n, c, h, w = inp.shape[:4]
    filters = node.properties.get("filters", 32)
    k = node.properties.get("kernelSize", 3)
    stride = node.properties.get("stride", 1)
    padding = node.properties.get("padding", 0)
    # H_out = floor((H + 2*P - K) / S) + 1
    h_out = ShapeDim(sympy.floor((h._value + 2 * padding - k) / stride) + 1)
    w_out = ShapeDim(sympy.floor((w._value + 2 * padding - k) / stride) + 1)
    _set_output_shape(node, ShapeInfo(shape=[n, ShapeDim(filters), h_out, w_out]))


def _shape_flatten(node, graph):
    inp = _first_input_shape(node, graph)
    if not inp or not inp.shape:
        return
    n = inp.shape[0]
    prod = sympy.Integer(1)
    for d in inp.shape[1:]:
        prod = prod * d._value
    _set_output_shape(node, ShapeInfo(shape=[n, ShapeDim(sympy.simplify(prod))]))


def _shape_add(node, graph):
    for port in node.inputs:
        for link in graph.links:
            if link.id_to == port.id:
                src = graph.ports[link.id_from]
                if src.shape is not None:
                    _set_output_shape(node, src.shape)
                    return
    _set_output_shape(node, ShapeInfo.unknown())


def _shape_concat(node, graph):
    axis = node.properties.get("axis", -1)
    shapes = []
    for port in node.inputs:
        for link in graph.links:
            if link.id_to == port.id:
                src = graph.ports[link.id_from]
                if src.shape is not None:
                    shapes.append(src.shape)
    if not shapes:
        return
    rank = max(len(s.shape) for s in shapes)
    axis = axis if axis >= 0 else rank + axis
    out = [ShapeDim("0") for _ in range(rank)]
    for d in range(rank):
        if d == axis:
            total = sympy.Integer(0)
            for s in shapes:
                if d < len(s.shape):
                    total = total + s.shape[d]._value
            out[d] = ShapeDim(sympy.simplify(total))
        else:
            # take first non‑zero dim
            for s in shapes:
                if d < len(s.shape):
                    out[d] = s.shape[d]
                    break
    _set_output_shape(node, ShapeInfo(shape=out))


def _shape_onehot(node, graph):
    inp = _first_input_shape(node, graph)
    if not inp or not inp.shape:
        return
    num_classes = node.properties.get("numClasses", 10)
    shape = list(inp.shape)
    if shape and shape[-1].is_concrete and int(shape[-1]) == 1:
        shape[-1] = ShapeDim(num_classes)
    else:
        shape.append(ShapeDim(num_classes))
    _set_output_shape(node, ShapeInfo(shape=shape))


def _shape_deonehot(node, graph):
    inp = _first_input_shape(node, graph)
    if not inp or not inp.shape or len(inp.shape) < 2:
        return
    shape = inp.shape[:-1]
    _set_output_shape(node, ShapeInfo(shape=shape))


def _shape_output(node, graph):
    inp = _first_input_shape(node, graph)
    if not inp or not inp.shape:
        return
    activations = node.properties.get("outputActivations", {})
    for port in node.outputs:
        role = port.role
        act = activations.get(role, "none")
        if act == "argmax":
            # 1-D tensor: (batch,)
            new_shape = [inp.shape[0]]
        else:
            # same as input: (batch, features)
            new_shape = list(inp.shape)
        port.shape = ShapeInfo(shape=new_shape)


def _shape_reshape(node, graph):
    inp = _first_input_shape(node, graph)
    if not inp or not inp.shape:
        return
    target_str = node.properties.get("targetShape", "(batch, -1)")
    parts = _parse_target_shape(target_str)
    if not parts:
        return
    # total input elements
    total_inp = sympy.Integer(1)
    for d in inp.shape:
        total_inp = total_inp * d._value
    infer_idx = -1
    concrete_product = sympy.Integer(1)
    for i, p in enumerate(parts):
        if p == "-1":
            if infer_idx != -1:
                return  # only one -1 allowed
            infer_idx = i
        else:
            try:
                concrete_product = concrete_product * int(p)
            except ValueError:
                pass  # symbolic dim, keep as is
    if infer_idx >= 0:
        inferred = sympy.floor(total_inp / concrete_product)
        parts[infer_idx] = str(inferred) if inferred.is_Integer else str(inferred)
    out_shape = [ShapeDim(p) for p in parts]
    _set_output_shape(node, ShapeInfo(shape=out_shape))


def _parse_target_shape(target_str: str) -> List[str]:
    """Parse a shape string like '(batch, -1)' into a list of dimension strings."""
    cleaned = target_str.strip("()")
    if not cleaned:
        return []
    return [x.strip() for x in cleaned.split(",")]
