"""
Per-node code emitters.

Each node type is described once, as an expression over already-resolved input
expressions.  The emitter never knows whether it is running inside
``load_data`` or inside ``Model.forward`` -- :mod:`ir` resolves the inputs and
decides where the resulting statement goes.  That is what lets a single class
serve every phase, instead of the old ``placement="data"`` /
``placement="forward"`` pair of implementations.
"""

from .analysis import Analysis
from .naming import snake
from .sanitize import py_string_literal, safe_dim_slice, safe_filename, safe_slice_expr

# Activations that only exist under torch.nn.functional.
_FUNCTIONAL_ACTIVATIONS = frozenset(
    {"leaky_relu", "elu", "selu", "gelu", "mish", "silu", "softplus", "hardswish"}
)

_NO_ACTIVATION = frozenset({"", "linear", "none", "identity"})

_READERS = {
    "csv": "pd.read_csv",
    "xlsx": "pd.read_excel",
    "xls": "pd.read_excel",
    "json": "pd.read_json",
    "parquet": "pd.read_parquet",
}

_LOSSES = {
    "mse": "nn.MSELoss()",
    "cross_entropy": "nn.CrossEntropyLoss()",
    "bce": "nn.BCEWithLogitsLoss()",
    "l1": "nn.L1Loss()",
    "huber": "nn.HuberLoss()",
    "nll": "nn.NLLLoss()",
}


def activation(name, expr: str, softmax_dim: int = -1) -> str:
    """Wrap ``expr`` in an activation, or return it unchanged."""
    name = (name or "linear").lower()
    if name in _NO_ACTIVATION:
        return expr
    if name == "softmax":
        return f"torch.softmax({expr}, dim={softmax_dim})"
    if name == "argmax":
        return f"torch.argmax({expr}, dim={softmax_dim})"
    if name in _FUNCTIONAL_ACTIVATIONS:
        return f"torch.nn.functional.{name}({expr})"
    return f"torch.{name}({expr})"


def loss_expression(loss_type: str) -> str:
    return _LOSSES.get(loss_type, _LOSSES["mse"])


def _int_or_none(text):
    try:
        return int(str(text).strip())
    except (TypeError, ValueError):
        return None


def _contiguous(columns) -> bool:
    """True when a column list is an ascending run, so it can print as a slice."""
    return len(columns) > 4 and all(
        columns[i] + 1 == columns[i + 1] for i in range(len(columns) - 1)
    )


# ======================================================================
#  Emission context
# ======================================================================
class NodeCtx:
    """Everything an emitter needs, with inputs already resolved to expressions.

    ``inputs`` holds one expression per connected data input port (several
    sources arriving on the same port are already concatenated), ``sources``
    holds them individually, and ``by_port`` is aligned with the node's
    declared input ports so role-sensitive nodes can tell them apart.
    """

    def __init__(
        self,
        node,
        analysis: Analysis,
        phase,
        inputs,
        sources,
        source_ports,
        resolve_param=None,
        by_port=(),
        in_model=False,
        attr=None,
        names=None,
    ):
        self.node = node
        self.props = node.properties
        self.analysis = analysis
        self.graph = analysis.graph
        self.phase = phase
        self.inputs = list(inputs)
        self.sources = list(sources)
        self.source_ports = list(source_ports)
        self.by_port = list(by_port)
        self.in_model = in_model
        self.attr = attr or snake(node.id)
        self._names = names
        self._temps = {}
        self._resolve_param = resolve_param
        self._params = {}

    # -- inputs --------------------------------------------------------
    def input(self, index: int, default="None"):
        return self.inputs[index] if index < len(self.inputs) else default

    def source(self, index: int, default="None"):
        return self.sources[index] if index < len(self.sources) else default

    def source_port(self, index: int = 0):
        return self.source_ports[index] if index < len(self.source_ports) else None

    def param(self, index: int = 0):
        """Expressions published on the n-th param input, or None.

        Resolved on demand so a node that ignores a connected param port does
        not drag that value into the ``Data`` tuple.
        """
        if index not in self._params:
            self._params[index] = (
                self._resolve_param(index) if self._resolve_param else None
            )
        return self._params[index] or None

    # -- names ---------------------------------------------------------
    def temp(self, stem: str, prefixed: bool = True) -> str:
        """A stable helper variable name for this node, e.g. ``n6_mean``."""
        if stem not in self._temps:
            preferred = f"{snake(self.node.id)}_{stem}" if prefixed else stem
            self._temps[stem] = (
                self._names.fresh(preferred) if self._names else preferred
            )
        return self._temps[stem]

    # -- shapes --------------------------------------------------------
    def rank(self, index: int = 0):
        return Analysis.rank(self.source_port(index))

    def dim(self, index: int, axis: int):
        return Analysis.dim(self.source_port(index), axis)

    @property
    def in_features(self):
        """Total width of everything arriving at this node in the active phase."""
        total = 0
        for port in self.source_ports:
            width = Analysis.dim(port, -1)
            if width is None:
                rank = Analysis.rank(port)
                width = 1 if rank == 1 else None
            if width is None:
                return None
            total += width
        return total or None

    @property
    def in_channels(self):
        for port in self.source_ports:
            channels = Analysis.dim(port, 1)
            if channels is not None:
                return channels
        return 1


# ======================================================================
#  Base emitter
# ======================================================================
class NodeEmitter:
    """Describes one node type. Every hook is optional."""

    #: Overrides the variable stem when the node id makes a poor name.
    value_name = None

    def submodules(self, n: NodeCtx) -> list:
        """``self.<attr> = ...`` lines for Model.__init__."""
        return []

    def prelude(self, n: NodeCtx) -> list:
        """Statements that must run before the node's values are bound."""
        return []

    def expressions(self, n: NodeCtx) -> list:
        """One expression per data output port."""
        return []

    def param_expressions(self, n: NodeCtx) -> list:
        """Expressions published on each param output port."""
        return []

    def statements(self, n: NodeCtx) -> list:
        """Side-effect-only code, for nodes that produce no tensor."""
        return []


# ======================================================================
#  Data sources and transforms
# ======================================================================
class InputDataEmitter(NodeEmitter):
    #: The dataset tensor reads better as `raw` than as the node's id.
    value_name = "raw"

    def _reader(self, n):
        filename = n.props.get("datasetFile")
        if not (n.props.get("datasetId") and filename):
            return None, None
        safe_name = safe_filename(filename)
        if safe_name is None:
            return None, None
        fmt = n.props.get("datasetFormat") or safe_name.rsplit(".", 1)[-1]
        return _READERS.get(str(fmt).lower()), safe_name

    def prelude(self, n):
        reader, filename = self._reader(n)
        if reader:
            return [f"{n.temp('df', prefixed=False)} = {reader}('data/{filename}')"]
        return []

    def expressions(self, n):
        reader, _ = self._reader(n)
        if reader:
            frame = n.temp("df", prefixed=False)
            return [f"torch.tensor({frame}.values, dtype=torch.float32)"]

        shape = n.props.get("dataShape")
        if shape:
            parts = [p.strip() for p in str(shape).strip("()").split(",") if p.strip()]
            dims = [_int_or_none(p) for p in parts]
            dims = [d if d is not None else 200 for d in dims]
            if dims:
                return [f"torch.randn({', '.join(str(d) for d in dims)})"]
        return ["torch.randn(200, 10)"]


class ColumnSelectEmitter(NodeEmitter):
    def expressions(self, n):
        source = n.input(0)
        columns = n.props.get("selectedColumns") or []
        if columns:
            if _contiguous(columns):
                return [f"{source}[:, {columns[0]}:{columns[-1] + 1}]"]
            return [f"{source}[:, {list(columns)}]"]

        text = str(n.props.get("columnInput") or "").strip()
        if not text:
            return [source]
        if ":" in text:
            slice_expr = safe_slice_expr(text)
            if slice_expr is None:
                return [source]
            start, _, end = slice_expr.partition(":")
            return [f"{source}[:, {start.strip() or '0'}:{end.strip()}]"]
        indices = [_int_or_none(p) for p in text.split(",")]
        indices = [i for i in indices if i is not None]
        return [f"{source}[:, {indices}]"] if indices else [source]


class RowSelectEmitter(NodeEmitter):
    def _count(self, n):
        return _int_or_none(n.props.get("value", "100")) or 100

    def prelude(self, n):
        if n.props.get("method", "first-n") != "random":
            return []
        seed = n.props.get("randomSeed", 42)
        source = n.input(0)
        return [
            f"{n.temp('perm')} = torch.randperm("
            f"{source}.size(0), generator=torch.Generator().manual_seed({seed}))"
        ]

    def expressions(self, n):
        source = n.input(0)
        method = n.props.get("method", "first-n")
        value = str(n.props.get("value", "100"))

        if method == "random":
            return [f"{source}[{n.temp('perm')}[:{self._count(n)}]]"]
        if method == "slice":
            slice_expr = safe_slice_expr(value)
            if slice_expr is None:
                return [source]
            start, _, end = slice_expr.partition(":")
            return [f"{source}[{start.strip() or '0'}:{end.strip()}]"]
        if method == "indices":
            indices = [_int_or_none(p) for p in value.split(",")]
            indices = [i for i in indices if i is not None]
            return [f"{source}[{indices}]"]
        return [f"{source}[:{self._count(n)}]"]


class DimSelectEmitter(NodeEmitter):
    def expressions(self, n):
        source = n.input(0)
        selections = n.props.get("dimSelections") or []
        parts = []
        for selection in selections:
            token = safe_dim_slice(selection)
            if token is None:
                return [source]
            parts.append(token)
        if not parts or all(p == ":" for p in parts):
            return [source]
        return [f"{source}[:, {', '.join(parts)}]"]


class NormalizeEmitter(NodeEmitter):
    """Standard or min-max scaling, optionally reusing another node's statistics."""

    def _stats(self, n):
        """(low, high) expressions: mean/std, or min/max for the minmax method."""
        shared = n.param(0)
        if shared and len(shared) >= 2:
            return shared[0], shared[1]
        return n.temp("mean"), n.temp("std")

    def prelude(self, n):
        if n.param(0):
            return []
        source = n.input(0)
        low, high = self._stats(n)
        if n.props.get("method", "standard") == "standard":
            return [
                f"{low} = {source}.mean(dim=0, keepdim=True)",
                f"{high} = {source}.std(dim=0, keepdim=True) + 1e-8",
            ]
        return [
            f"{low} = {source}.min(dim=0, keepdim=True)[0]",
            f"{high} = {source}.max(dim=0, keepdim=True)[0]",
        ]

    def expressions(self, n):
        source = n.input(0)
        low, high = self._stats(n)
        if n.props.get("method", "standard") == "standard":
            return [f"({source} - {low}) / {high}"]
        return [f"({source} - {low}) / ({high} - {low} + 1e-8)"]

    def param_expressions(self, n):
        low, high = self._stats(n)
        return [[low, high]]


class OneHotEmitter(NodeEmitter):
    def expressions(self, n):
        source = n.input(0)
        classes = n.props.get("numClasses", 10)
        if n.rank(0) != 1:
            source = f"{source}.squeeze(-1)"
        return [
            f"torch.nn.functional.one_hot({source}.long(), "
            f"num_classes={classes}).float()"
        ]

    def param_expressions(self, n):
        return [[f"torch.arange({n.props.get('numClasses', 10)})"]]


class DeOneHotEmitter(NodeEmitter):
    """Class indices from a one-hot or probability tensor.

    The rank is known from shape propagation, so the old runtime
    ``if x.dim() == 2`` branch collapses to one of its two arms here.
    """

    def expressions(self, n):
        source = n.input(0)
        if n.rank(0) == 1:
            return [source]
        return [f"torch.argmax({source}, dim=-1)"]


class TrainTestSplitEmitter(NodeEmitter):
    def prelude(self, n):
        source = n.input(0)
        seed = n.props.get("randomSeed", 42)
        ratio = n.props.get("trainRatio", 0.7)
        return [
            f"{n.temp('perm')} = torch.randperm("
            f"{source}.size(0), generator=torch.Generator().manual_seed({seed}))",
            f"{n.temp('split')} = int({source}.size(0) * {ratio})",
        ]

    def expressions(self, n):
        source = n.input(0)
        perm, split = n.temp("perm"), n.temp("split")
        return [
            f"{source}[{perm}[:{split}]]",
            f"{source}[{perm}[{split}:]]",
        ]


class ReshapeEmitter(NodeEmitter):
    def expressions(self, n):
        source = n.input(0)
        target = str(n.props.get("targetShape", "(-1)"))
        parts = [p.strip() for p in target.strip("()").split(",") if p.strip()]
        if not parts:
            return [source]

        inferred_taken = "-1" in parts
        args = []
        for axis, part in enumerate(parts):
            if _int_or_none(part) is not None:
                args.append(part)
            elif not inferred_taken:
                # A symbolic name with no explicit -1: let PyTorch infer it.
                args.append("-1")
                inferred_taken = True
            else:
                # Symbolic and -1 is spoken for: read the size off the input.
                args.append(f"{source}.size({axis})")
        return [f"{source}.reshape({', '.join(args)})"]


# ======================================================================
#  Model layers
# ======================================================================
class _ParametricEmitter(NodeEmitter):
    """Shared plumbing for layers that own weights.

    Inside the model the layer is an ``nn.Module`` attribute.  Outside it --
    which the validator flags as a warning -- the module is built inline so the
    script still runs, visibly untrained.
    """

    def construction(self, n) -> str:
        raise NotImplementedError

    def call(self, n, module: str) -> str:
        return activation(n.props.get("activation", "relu"), f"{module}({n.input(0)})")

    def submodules(self, n):
        return [f"self.{n.attr} = {self.construction(n)}"] if n.in_model else []

    def prelude(self, n):
        if n.in_model:
            return []
        return [
            f"{n.temp('module')} = {self.construction(n)}"
            "  # untrained: outside the optimizer's reach"
        ]

    def expressions(self, n):
        module = f"self.{n.attr}" if n.in_model else n.temp("module")
        return [self.call(n, module)]


class LinearEmitter(_ParametricEmitter):
    out_features = None  # None means "read numNeurons from the node"

    def construction(self, n):
        out = self.out_features or n.props.get("numNeurons", 64)
        arguments = [str(n.in_features or 1), str(out)]
        if not n.props.get("hasBias", True):
            arguments.append("bias=False")
        return f"nn.Linear({', '.join(arguments)})"


class NeuronEmitter(LinearEmitter):
    out_features = 1


class Conv2DEmitter(_ParametricEmitter):
    def construction(self, n):
        arguments = [
            str(n.in_channels),
            str(n.props.get("filters", 32)),
            f"kernel_size={n.props.get('kernelSize', 3)}",
        ]
        if n.props.get("stride", 1) != 1:
            arguments.append(f"stride={n.props.get('stride')}")
        if n.props.get("padding", 0) != 0:
            arguments.append(f"padding={n.props.get('padding')}")
        if not n.props.get("hasBias", True):
            arguments.append("bias=False")
        return f"nn.Conv2d({', '.join(arguments)})"

    def call(self, n, module):
        return activation(
            n.props.get("activation", "relu"), f"{module}({n.input(0)})", softmax_dim=1
        )


class BatchNormEmitter(_ParametricEmitter):
    def _num_features(self, n):
        rank = n.rank(0)
        axis = 1 if rank and rank >= 3 else -1
        return n.dim(0, axis) or 1

    def construction(self, n):
        rank = n.rank(0)
        kind = "BatchNorm2d" if rank == 4 else "BatchNorm1d"
        return f"nn.{kind}(num_features={self._num_features(n)})"

    def call(self, n, module):
        return f"{module}({n.input(0)})"


class DropoutEmitter(NodeEmitter):
    def submodules(self, n):
        if not n.in_model:
            return []
        return [f"self.{n.attr} = nn.Dropout(p={n.props.get('rate', 0.5)})"]

    def expressions(self, n):
        if n.in_model:
            return [f"self.{n.attr}({n.input(0)})"]
        # Dropout is a no-op outside training; say so explicitly.
        return [
            f"torch.nn.functional.dropout({n.input(0)}, "
            f"p={n.props.get('rate', 0.5)}, training=False)"
        ]


class FlattenEmitter(NodeEmitter):
    def submodules(self, n):
        return [f"self.{n.attr} = nn.Flatten()"] if n.in_model else []

    def expressions(self, n):
        if n.in_model:
            return [f"self.{n.attr}({n.input(0)})"]
        source = n.input(0)
        if n.rank(0) == 1:
            return [source]
        if n.rank(0) == 2 and n.dim(0, -1) == 1:
            return [f"{source}.squeeze(-1)"]
        return [f"torch.flatten({source}, start_dim=1)"]


class AddEmitter(NodeEmitter):
    def expressions(self, n):
        if len(n.sources) < 2:
            return [n.source(0)]
        return [" + ".join(n.sources)]


class ConcatEmitter(NodeEmitter):
    def expressions(self, n):
        if len(n.sources) < 2:
            return [n.source(0)]
        axis = n.props.get("axis", -1)
        return [f"torch.cat([{', '.join(n.sources)}], dim={axis})"]


class OutputEmitter(NodeEmitter):
    """Applies the per-role activation configured on the Output node."""

    def expressions(self, n):
        source = n.input(0)
        activations = n.props.get("outputActivations", {}) or {}
        return [
            activation(activations.get(port.role, "none"), source)
            for port in n.node.outputs
        ]


# ======================================================================
#  Side-effect nodes
# ======================================================================
class PrintEmitter(NodeEmitter):
    def statements(self, n):
        label = py_string_literal(n.props.get("label") or n.node.id)
        return [
            f"print({label} + f'[{i}]:', {expr}.shape, {expr})"
            for i, expr in enumerate(n.sources)
        ]


class AccuracyEmitter(NodeEmitter):
    """Compares predictions against labels, adapting each side by its shape."""

    @staticmethod
    def _as_class_indices(expr, port):
        width = Analysis.dim(port, -1)
        rank = Analysis.rank(port)
        if rank is None or rank == 1:
            return f"{expr}.long()"
        if width == 1:
            return f"{expr}.squeeze(-1).long()"
        return f"{expr}.argmax(dim=1)"

    def statements(self, n):
        if len(n.sources) < 2:
            return []
        predicted, actual = n.temp("predicted"), n.temp("actual")
        lines = [
            f"{predicted} = {self._as_class_indices(n.source(0), n.source_port(0))}",
            f"{actual} = {self._as_class_indices(n.source(1), n.source_port(1))}",
            f'print(f"Accuracy: {{({predicted} == {actual}).float().mean().item():.4f}}")',
        ]
        if n.props.get("showConfusion", False):
            lines += [
                "from sklearn.metrics import confusion_matrix",
                'print("Confusion Matrix:")',
                f"print(confusion_matrix({actual}.cpu(), {predicted}.cpu()))",
            ]
        return lines


class VisualizationEmitter(NodeEmitter):
    """A matplotlib figure: histogram, 2-D scatter or 3-D scatter."""

    def _colormap(self, n, lines):
        mode = n.props.get("colorMode", "none")
        if mode == "discrete":
            palette = n.props.get("colorPalette") or []
            if not palette:
                return "'tab10'"
            colors = ", ".join(f"'{c}'" for c in palette)
            lines.append("from matplotlib.colors import ListedColormap")
            lines.append(f"{n.temp('cmap')} = ListedColormap([{colors}])")
            return n.temp("cmap")
        if mode == "continuous":
            low = n.props.get("continuousMinColor", "#3b82f6")
            high = n.props.get("continuousMaxColor", "#ef4444")
            lines.append("from matplotlib.colors import LinearSegmentedColormap")
            lines.append(
                f"{n.temp('cmap')} = LinearSegmentedColormap.from_list("
                f"'{snake(n.node.id)}', ['{low}', '{high}'])"
            )
            return n.temp("cmap")
        return None

    def statements(self, n):
        coords, color = [], None
        for port, expr in zip(n.node.inputs, n.by_port):
            if expr is None:
                continue
            if port.role == "color":
                color = expr
            else:
                coords.append(expr)
        if not coords:
            return []

        lines = [f"# {n.props.get('label') or n.node.id}", "plt.figure()"]
        cmap = self._colormap(n, lines) if color else None
        style = "alpha=0.5"
        if color and cmap:
            style = f"c={color}.flatten(), cmap={cmap}, alpha=0.5"

        if len(coords) == 1:
            lines.append(f"plt.hist({coords[0]}.flatten(), bins=20)")
        elif len(coords) == 2:
            lines.append(
                f"plt.scatter({coords[0]}.flatten(), {coords[1]}.flatten(), {style})"
            )
            if n.props.get("colorMode") == "continuous":
                lines.append("plt.colorbar()")
        else:
            lines.append("ax = plt.figure().add_subplot(projection='3d')")
            flat = ", ".join(f"{c}.flatten()" for c in coords[:3])
            lines.append(f"ax.scatter({flat}, {style})")

        lines += [
            f"plt.title({py_string_literal(n.props.get('label') or n.node.id)})",
            "plt.grid(True)",
            "plt.show()",
        ]
        return lines


# ======================================================================
#  Registry
# ======================================================================
EMITTERS = {
    "input-data": InputDataEmitter(),
    "column-select": ColumnSelectEmitter(),
    "row-select": RowSelectEmitter(),
    "dim-select": DimSelectEmitter(),
    "normalize": NormalizeEmitter(),
    "onehot": OneHotEmitter(),
    "deonehot": DeOneHotEmitter(),
    "train-test": TrainTestSplitEmitter(),
    "reshape": ReshapeEmitter(),
    "neuron": NeuronEmitter(),
    "layer": LinearEmitter(),
    "conv2d": Conv2DEmitter(),
    "batchnorm": BatchNormEmitter(),
    "dropout": DropoutEmitter(),
    "flatten": FlattenEmitter(),
    "add": AddEmitter(),
    "concat": ConcatEmitter(),
    "output": OutputEmitter(),
    "print": PrintEmitter(),
    "accuracy": AccuracyEmitter(),
    "visualization": VisualizationEmitter(),
    "optimizer": NodeEmitter(),
}

#: Node types this package knows how to translate.
SUPPORTED_TYPES = frozenset(EMITTERS)


def emitter_for(node) -> NodeEmitter:
    return EMITTERS.get(node.type, NodeEmitter())
