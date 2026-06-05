"""
Translators for converting SketchNet nodes into PyTorch code snippets.

This module defines translator classes that convert different node types from
the SketchNet graph into executable PyTorch code. Each translator is responsible
for generating code appropriate to its node type for different code generation
stages:
- data_code: Executed once in load_and_preprocess() for data loading/transforms
- init_code: Code for Model.__init__() to define layers and parameters
- forward_code: Code for Model.forward() to execute the model
- optimizer_code: Returns optimizer configuration parameters
- visualization_code: Code for generating visualizations after evaluation

The translator registry (get_translator) returns the appropriate translator
for each node type.
"""


class BaseTranslator:
    """
    Base translator class providing default (no-op) implementations.

    All translator subclasses inherit from this and override methods as needed.
    The base implementations do nothing, allowing translators to selectively
    implement only the code generation methods they need.

    Attributes:
        node_type (str): The type of node this translator handles (must be set by subclasses).
        node (Node): The graph node being translated.
        graph (Graph): The full computation graph (for lookups).
        var_map (Dict): Mapping of node/port IDs to variable names in generated code.
    """

    node_type = None

    def __init__(self, node, graph, var_map):
        """
        Initialize the translator.

        Args:
            node (Node): The node to translate.
            graph (Graph): The computation graph.
            var_map (Dict): Mapping of IDs to variable names (shared across all translators).
        """
        self.node = node
        self.graph = graph
        self.var_map = var_map

    def data_code(self, w, phase):
        """
        Generate data loading or preprocessing code.

        Args:
            w (CodeWriter): The code writer to append lines to.
            phase (str): The execution phase ("pre", "train", or "eval").
        """
        pass

    def init_code(self, w):
        """
        Generate model initialization code (Model.__init__).
        """
        pass

    def forward_code(self, w):
        """
        Generate model forward pass code (Model.forward).
        """
        pass

    def optimizer_code(self, w):
        """
        Return optimizer configuration as a Python dictionary literal.
        """
        return "{}"

    def visualization_code(self, w):
        """
        Generate visualization code (evaluate function).
        """
        pass

    def _get_input_var(self, node):
        """
        Return the variable name feeding a node's first input port.

        Performs a port‑ID‑first lookup:
        1. Exact source port ID in var_map.
        2. Fallback: source node ID in var_map.
        """
        for port in node.inputs + node.paramInputs:
            for link in self.graph.links:
                if link.id_to == port.id:
                    src_port_id = link.id_from
                    if src_port_id in self.var_map:
                        return self.var_map[src_port_id]
                    src_id = self.graph.ports[src_port_id].node_id
                    if src_id in self.var_map:
                        return self.var_map[src_id]
        return "raw_data"


# ---------------------------------------------------------------------------
# DATA NODES
# ---------------------------------------------------------------------------
class InputDataTranslator(BaseTranslator):
    """
    Loads a dataset from CSV, Excel, JSON, or Parquet, or generates synthetic
    random data when no dataset is provided.
    """

    node_type = "input-data"

    def data_code(self, w, phase):
        n = self.node
        ds = n.properties.get("dataShape")
        dataset_id = n.properties.get("datasetId")
        dataset_file = n.properties.get("datasetFile", "")
        dataset_format = n.properties.get("datasetFormat", "")

        if dataset_id and dataset_file:
            ext = dataset_format or dataset_file.rsplit(".", 1)[-1]
            if ext in ("csv", "xlsx", "json", "parquet"):
                if ext == "csv":
                    w.line("import pandas as pd")
                    w.line(f"df = pd.read_csv('data/{dataset_file}')")
                elif ext == "xlsx":
                    w.line("import pandas as pd")
                    w.line(f"df = pd.read_excel('data/{dataset_file}')")
                elif ext == "json":
                    w.line("import pandas as pd")
                    w.line(f"df = pd.read_json('data/{dataset_file}')")
                elif ext == "parquet":
                    w.line("import pandas as pd")
                    w.line(f"df = pd.read_parquet('data/{dataset_file}')")
                w.line("raw_data = torch.tensor(df.values, dtype=torch.float32)")
            else:
                w.line(f"# Unsupported format '{ext}' – loading random data instead")
                w.line("raw_data = torch.randn(200, 10)")
            self.var_map[n.id] = "raw_data"
        elif ds:
            parts = ds.strip("()").split(",")
            row_str = parts[0].strip()
            cols = [int(p.strip()) for p in parts[1:]]
            if row_str.isdigit():
                w.line(
                    f"raw_data = torch.randn({row_str}, {', '.join(str(c) for c in cols)})"
                )
            else:
                w.line(f"# Manual shape {ds}")
                w.line(f"num_rows = 200  # placeholder for '{row_str}'")
                w.line(
                    f"raw_data = torch.randn(num_rows, {', '.join(str(c) for c in cols)})"
                )
            self.var_map[n.id] = "raw_data"
        else:
            w.line("raw_data = torch.randn(200, 10)")
            self.var_map[n.id] = "raw_data"


class ColumnSelectTranslator(BaseTranslator):
    """
    Selects a subset of columns from the input tensor using PyTorch indexing.
    """

    node_type = "column-select"

    def data_code(self, w, phase):
        n = self.node
        cols = n.properties.get("selectedColumns", [])
        if not cols:
            col_str = n.properties.get("columnInput", "")
            if col_str:
                w.line(f"# ColumnSelect '{n.id}' with input '{col_str}'")
                w.line(f"indices = list(range({col_str}))")
                in_var = self._get_input_var(n)
                out_var = f"{n.id}_out"
                w.line(f"{out_var} = {in_var}[:, indices]")
                self.var_map[n.id] = out_var
            else:
                self.var_map[n.id] = self._get_input_var(n)
        else:
            col_list = ", ".join(str(c) for c in cols)
            in_var = self._get_input_var(n)
            out_var = f"{n.id}_out"
            w.line(f"{out_var} = {in_var}[:, [{col_list}]]")
            self.var_map[n.id] = out_var

    def _get_input_var(self, node):
        """Port‑ID first, then node‑ID."""
        for port in node.inputs:
            for link in self.graph.links:
                if link.id_to == port.id:
                    src_port_id = link.id_from
                    if src_port_id in self.var_map:
                        return self.var_map[src_port_id]
                    src_id = self.graph.ports[src_port_id].node_id
                    if src_id in self.var_map:
                        return self.var_map[src_id]
        return "raw_data"


class RowSelectTranslator(BaseTranslator):
    """Selects rows via first‑N, random, slice, or explicit indices."""

    node_type = "row-select"

    def data_code(self, w, phase):
        n = self.node
        method = n.properties.get("method", "first-n")
        value = n.properties.get("value", "100")
        seed = n.properties.get("randomSeed", 42)
        in_var = self._get_input_var(n)
        out_var = f"{n.id}_out"
        if method == "first-n":
            n_rows = int(value) if value.isdigit() else 100
            w.line(f"{out_var} = {in_var}[:{n_rows}]")
        elif method == "random":
            n_rows = int(value) if value.isdigit() else 100
            w.line(f"gen = torch.Generator().manual_seed({seed})")
            w.line(f"perm = torch.randperm({in_var}.size(0), generator=gen)")
            w.line(f"{out_var} = {in_var}[perm[:{n_rows}]]")
        elif method == "slice":
            parts = value.split(":")
            start = parts[0] if parts[0] else "0"
            end = parts[1] if parts[1] else f"{in_var}.size(0)"
            w.line(f"{out_var} = {in_var}[{start}:{end}]")
        elif method == "indices":
            w.line(f"indices = [{value}]")
            w.line(f"{out_var} = {in_var}[indices]")
        self.var_map[n.id] = out_var

    def _get_input_var(self, node):
        return ColumnSelectTranslator._get_input_var(self, node)


class DimSelectTranslator(BaseTranslator):
    """Applies per‑dimension slicing (e.g., ``[0:3, 1:2]``)."""

    node_type = "dim-select"

    def data_code(self, w, phase):
        n = self.node
        dims = n.properties.get("dimSelections", [])
        in_var = self._get_input_var(n)
        out_var = f"{n.id}_out"
        if all(not s or s.strip() == ":" for s in dims):
            w.line(f"{out_var} = {in_var}  # no dimension selection")
        else:
            slices = []
            for sel in dims:
                if not sel or sel.strip() == ":":
                    slices.append(":")
                else:
                    slices.append(f"[{sel}]")
            if all(s == ":" for s in slices):
                w.line(f"{out_var} = {in_var}")
            else:
                slice_str = "[:, " + ", ".join(slices) + "]"
                w.line(f"{out_var} = {in_var}{slice_str}")
        self.var_map[n.id] = out_var

    def _get_input_var(self, node):
        return ColumnSelectTranslator._get_input_var(self, node)


class NormalizeTranslator(BaseTranslator):
    """Standard (Z‑score) or Min‑Max normalisation."""

    node_type = "normalize"

    def data_code(self, w, phase):
        n = self.node
        method = n.properties.get("method", "standard")
        in_var = self._get_input_var(n)
        out_var = f"{n.id}_out"
        if method == "standard":
            w.line(f"mean = {in_var}.mean(dim=0, keepdim=True)")
            w.line(f"std = {in_var}.std(dim=0, keepdim=True) + 1e-8")
            w.line(f"{out_var} = ({in_var} - mean) / std")
        elif method == "minmax":
            w.line(f"min_val = {in_var}.min(dim=0, keepdim=True)[0]")
            w.line(f"max_val = {in_var}.max(dim=0, keepdim=True)[0]")
            w.line(f"{out_var} = ({in_var} - min_val) / (max_val - min_val + 1e-8)")
        self.var_map[n.id] = out_var

    def _get_input_var(self, node):
        return ColumnSelectTranslator._get_input_var(self, node)


class OneHotTranslator(BaseTranslator):
    """One‑hot encodes integer labels. Supports param output for shared categories."""

    node_type = "onehot"

    def data_code(self, w, phase):
        n = self.node
        num_classes = n.properties.get("numClasses", 10)
        in_var = self._get_input_var(n)
        out_var = f"{n.id}_out"

        w.line("# OneHot encode – squeeze last dim if needed")
        w.line(f"{in_var}_squeezed = {in_var}.squeeze(-1).long()")
        w.line(
            f"{out_var} = torch.nn.functional.one_hot({in_var}_squeezed, num_classes={num_classes}).float()"
        )
        self.var_map[n.id] = out_var

        if n.paramOutputs:
            w.line(f"categories = torch.arange({num_classes})")
            self.var_map[n.paramOutputs[0].id] = "categories"


class DeOneHotTranslator(BaseTranslator):
    """Converts one‑hot vectors back to class indices. Handles both 1‑D and 2‑D inputs."""

    node_type = "deonehot"

    def data_code(self, w, phase):
        n = self.node
        in_var = self._get_input_var(n)
        out_var = f"{n.id}_out"

        param_input = None
        if n.paramInputs:
            for link in self.graph.links:
                if link.id_to == n.paramInputs[0].id:
                    param_input = self.var_map.get(link.id_from)
                    break

        if param_input:
            w.line(f"categories = {param_input}")

        w.line(f"if {in_var}.dim() == 2:")
        w.indent()
        w.line(f"{out_var} = torch.argmax({in_var}, dim=-1)")
        w.dedent()
        w.line("else:")
        w.indent()
        w.line(f"{out_var} = {in_var}  # already class indices")
        w.dedent()

        self.var_map[n.id] = out_var


class TrainTestSplitTranslator(BaseTranslator):
    """Splits data into train/test sets. Stores results under port IDs and node ID."""

    node_type = "train-test"

    def data_code(self, w, phase):
        n = self.node
        train_ratio = n.properties.get("trainRatio", 0.7)
        seed = n.properties.get("randomSeed", 42)
        in_var = self._get_input_var(n)

        train_var = f"train_data_{n.id}"
        test_var = f"test_data_{n.id}"

        w.line(f"train_size = int({in_var}.size(0) * {train_ratio})")
        w.line(f"gen = torch.Generator().manual_seed({seed})")
        w.line(f"perm = torch.randperm({in_var}.size(0), generator=gen)")
        w.line(f"{train_var} = {in_var}[perm[:train_size]]")
        w.line(f"{test_var} = {in_var}[perm[train_size:]]")

        train_port = next(p for p in n.outputs if p.sub_type == "train")
        test_port = next(p for p in n.outputs if p.sub_type == "test")
        self.var_map[train_port.id] = train_var
        self.var_map[test_port.id] = test_var
        self.var_map[n.id] = train_var  # for feed‑key compatibility


# ---------------------------------------------------------------------------
# MODEL NODES
# ---------------------------------------------------------------------------
class NeuronTranslator(BaseTranslator):
    """Single neuron: one nn.Linear layer, activation."""

    node_type = "neuron"

    def _guess_in_features(self, node):
        """
        Return the number of input features by looking at the last dimension
        of the shape of the first connected source port.
        """
        for port in node.inputs:
            for link in self.graph.links:
                if link.id_to == port.id:
                    src_port = self.graph.ports[link.id_from]
                    if (
                        src_port.shape
                        and src_port.shape.shape
                        and len(src_port.shape.shape) >= 2
                    ):
                        # shape is (batch, ..., in_features)
                        in_feat = src_port.shape.shape[-1]
                        try:
                            return int(str(in_feat))
                        except (ValueError, TypeError):
                            pass
        return "input_size  # TODO: set input feature dimension"

    def init_code(self, w):
        n = self.node
        in_features = self._guess_in_features(n)
        out_features = 1
        bias = n.properties.get("hasBias", True)
        bias_val = n.properties.get("bias", 0.0)
        w.line(
            f"self.fc_{n.id} = nn.Linear({in_features}, {out_features}, bias={bias})"
        )
        if bias:
            w.line(f"nn.init.constant_(self.fc_{n.id}.bias, {bias_val})")

    def forward_code(self, w):
        n = self.node
        w.line(f"# --- {n.type} {n.id} ---")
        src_id = None
        for port in n.inputs:
            for link in self.graph.links:
                if link.id_to == port.id:
                    src_id = self.graph.ports[link.id_from].node_id
                    break
            if src_id:
                break
        if src_id:
            w.line(f"if '{src_id}' in outputs or '{src_id}' in inputs_dict:")
            w.indent()
            w.line(f"x = outputs.get('{src_id}', inputs_dict.get('{src_id}'))")
            w.dedent()
            w.line(f"x = self.fc_{n.id}(x)")
            activation = n.properties.get("activation", "relu")
            if activation in ("linear", "none"):
                pass
            elif activation == "softmax":
                w.line("x = torch.softmax(x, dim=-1)")
            elif activation == "leaky_relu":
                w.line("x = torch.nn.functional.leaky_relu(x)")
            elif activation == "elu":
                w.line("x = torch.nn.functional.elu(x)")
            elif activation == "selu":
                w.line("x = torch.nn.functional.selu(x)")
            elif activation == "gelu":
                w.line("x = torch.nn.functional.gelu(x)")
            elif activation == "mish":
                w.line("x = torch.nn.functional.mish(x)")
            else:
                w.line(f"x = torch.{activation}(x)")
            w.line(f"outputs['{n.id}'] = x")
        else:
            w.line(f"outputs['{n.id}'] = None  # no input connected")


class LayerTranslator(NeuronTranslator):
    """Dense (linear) layer with configurable number of neurons and activation."""

    node_type = "layer"

    def init_code(self, w):
        n = self.node
        in_features = self._guess_in_features(n)  # inherited, uses port shape
        out_features = n.properties.get("numNeurons", 64)
        bias = n.properties.get("hasBias", True)
        bias_val = n.properties.get("bias", 0.0)
        w.line(
            f"self.fc_{n.id} = nn.Linear({in_features}, {out_features}, bias={bias})"
        )
        if bias:
            w.line(f"nn.init.constant_(self.fc_{n.id}.bias, {bias_val})")


class Conv2DTranslator(BaseTranslator):
    """2D convolutional layer with optional activation."""

    node_type = "conv2d"

    def _guess_in_channels(self, node):
        """Return the number of input channels from the first connected input shape."""
        for port in node.inputs:
            for link in self.graph.links:
                if link.id_to == port.id:
                    src_port = self.graph.ports[link.id_from]
                    if (
                        src_port.shape
                        and src_port.shape.shape
                        and len(src_port.shape.shape) >= 2
                    ):
                        # assume shape is (batch, channels, …)
                        ch_expr = src_port.shape.shape[1]
                        try:
                            return int(str(ch_expr))
                        except (ValueError, TypeError):
                            pass
        return 1  # fallback

    def init_code(self, w):
        n = self.node
        in_channels = self._guess_in_channels(n)  # inferred from input shape
        out_channels = n.properties.get("filters", 32)
        kernel = n.properties.get("kernelSize", 3)
        stride = n.properties.get("stride", 1)
        padding = n.properties.get("padding", 0)
        bias = n.properties.get("hasBias", True)
        w.line(
            f"self.conv_{n.id} = nn.Conv2d({in_channels}, {out_channels}, "
            f"kernel_size={kernel}, stride={stride}, padding={padding}, bias={bias})"
        )

    def forward_code(self, w):
        n = self.node
        in_src = (
            list(self.graph.predecessors(n.id))[0]
            if self.graph.predecessors(n.id)
            else None
        )
        if in_src:
            w.line(f"if '{in_src}' in outputs or '{in_src}' in inputs_dict:")
            w.indent()
            w.line(f"x = outputs.get('{in_src}', inputs_dict.get('{in_src}'))")
            w.dedent()
        else:
            w.line("x = inputs_dict[list(inputs_dict.keys())[0]]  # fallback")
        w.line(f"x = self.conv_{n.id}(x)")
        activation = n.properties.get("activation", "relu")
        if activation in ("linear", "none"):
            pass
        elif activation == "softmax":
            w.line("x = torch.softmax(x, dim=1)")
        elif activation == "leaky_relu":
            w.line("x = torch.nn.functional.leaky_relu(x)")
        elif activation == "elu":
            w.line("x = torch.nn.functional.elu(x)")
        elif activation == "selu":
            w.line("x = torch.nn.functional.selu(x)")
        elif activation == "gelu":
            w.line("x = torch.nn.functional.gelu(x)")
        elif activation == "mish":
            w.line("x = torch.nn.functional.mish(x)")
        else:
            w.line(f"x = torch.{activation}(x)")
        w.line(f"outputs['{n.id}'] = x")


class FlattenTranslator(BaseTranslator):
    """Flattens all non‑batch dimensions into a single vector."""

    node_type = "flatten"

    def init_code(self, w):
        n = self.node
        w.line(f"self.flatten_{n.id} = nn.Flatten()")

    def forward_code(self, w):
        n = self.node
        in_src = list(self.graph.predecessors(n.id))[0]
        w.line(f"if '{in_src}' in outputs or '{in_src}' in inputs_dict:")
        w.indent()
        w.line(f"x = outputs.get('{in_src}', inputs_dict.get('{in_src}'))")
        w.dedent()
        w.line(f"x = self.flatten_{n.id}(x)")
        w.line(f"outputs['{n.id}'] = x")


class DropoutTranslator(BaseTranslator):
    """Dropout layer – applied during training, ignored during evaluation."""

    node_type = "dropout"

    def init_code(self, w):
        n = self.node
        rate = n.properties.get("rate", 0.5)
        w.line(f"self.dropout_{n.id} = nn.Dropout(p={rate})")

    def forward_code(self, w):
        n = self.node
        in_src = list(self.graph.predecessors(n.id))[0]
        w.line(f"if '{in_src}' in outputs or '{in_src}' in inputs_dict:")
        w.indent()
        w.line(f"x = outputs.get('{in_src}', inputs_dict.get('{in_src}'))")
        w.dedent()
        w.line(f"x = self.dropout_{n.id}(x)")
        w.line(f"outputs['{n.id}'] = x")


class BatchNormTranslator(BaseTranslator):
    """Batch normalisation layer (1D)."""

    node_type = "batchnorm"

    def _guess_num_features(self, node):
        """Return the number of features from the first connected input shape."""
        for port in node.inputs:
            for link in self.graph.links:
                if link.id_to == port.id:
                    src_port = self.graph.ports[link.id_from]
                    if (
                        src_port.shape
                        and src_port.shape.shape
                        and len(src_port.shape.shape) >= 2
                    ):
                        # shape is (batch, features) or (batch, channels, ...)
                        # assume features are the last dimension
                        num = src_port.shape.shape[-1]
                        try:
                            return int(str(num))
                        except (ValueError, TypeError):
                            pass
        return 1  # fallback

    def init_code(self, w):
        n = self.node
        num_features = self._guess_num_features(n)
        w.line(f"self.bn_{n.id} = nn.BatchNorm1d(num_features={num_features})")

    def forward_code(self, w):
        n = self.node
        in_src = list(self.graph.predecessors(n.id))[0]
        w.line(f"if '{in_src}' in outputs or '{in_src}' in inputs_dict:")
        w.indent()
        w.line(f"x = outputs.get('{in_src}', inputs_dict.get('{in_src}'))")
        w.dedent()
        w.line(f"x = self.bn_{n.id}(x)")
        w.line(f"outputs['{n.id}'] = x")


class AddTranslator(BaseTranslator):
    """Element‑wise addition of two tensors (skip / residual connection)."""

    node_type = "add"

    def init_code(self, w):
        pass

    def forward_code(self, w):
        n = self.node
        preds = list(self.graph.predecessors(n.id))
        if len(preds) >= 2:
            w.line(f"a = outputs.get('{preds[0]}', inputs_dict.get('{preds[0]}'))")
            w.line(f"b = outputs.get('{preds[1]}', inputs_dict.get('{preds[1]}'))")
            w.line("if a is not None and b is not None:")
            w.indent()
            w.line("x = a + b")
            w.line(f"outputs['{n.id}'] = x")
            w.dedent()
        else:
            w.line(f"outputs['{n.id}'] = None  # Add requires 2 inputs")


class ConcatTranslator(BaseTranslator):
    """Concatenates two or more tensors along a specified dimension."""

    node_type = "concat"

    def init_code(self, w):
        pass

    def forward_code(self, w):
        n = self.node
        preds = list(self.graph.predecessors(n.id))
        axis = n.properties.get("axis", -1)
        if len(preds) >= 2:
            w.line("tensors = []")
            for p in preds:
                w.line(f"tmp = outputs.get('{p}', inputs_dict.get('{p}'))")
                w.line("if tmp is not None: tensors.append(tmp)")
            w.line("if len(tensors) > 1:")
            w.indent()
            w.line(f"x = torch.cat(tensors, dim={axis})")
            w.line(f"outputs['{n.id}'] = x")
            w.dedent()
            w.line("else:")
            w.indent()
            w.line(f"outputs['{n.id}'] = None")
            w.dedent()
        else:
            w.line(f"outputs['{n.id}'] = None  # Concat requires at least 2 inputs")


class OutputTranslator(BaseTranslator):
    """
    Passes the output of the last model layer to the loss, prediction,
    and evaluation ports. Supports per‑port activations (softmax, argmax).
    """

    node_type = "output"

    def init_code(self, w):
        pass

    def forward_code(self, w):
        n = self.node
        src_id = None
        for port in n.inputs:
            for link in self.graph.links:
                if link.id_to == port.id:
                    src_id = self.graph.ports[link.id_from].node_id
                    break
            if src_id:
                break
        if src_id:
            w.line(f"if '{src_id}' in outputs:")
            w.indent()
            w.line(f"x = outputs['{src_id}']")
            for out_port in n.outputs:
                role = out_port.role
                act = n.properties.get("outputActivations", {}).get(role, "none")
                if role == "loss" or act == "none":
                    w.line(f"outputs['{out_port.id}'] = x")
                elif act == "softmax":
                    w.line(f"outputs['{out_port.id}'] = torch.softmax(x, dim=-1)")
                elif act == "argmax":
                    w.line(f"outputs['{out_port.id}'] = torch.argmax(x, dim=-1)")
            w.line(f"outputs['{n.id}'] = x")  # raw for backward compatibility
            w.dedent()
        else:
            w.line(f"outputs['{n.id}'] = None  # no input connected")


# ---------------------------------------------------------------------------
# SPECIAL NODES
# ---------------------------------------------------------------------------
class OptimizerTranslator(BaseTranslator):
    """Produces a configuration dictionary for the training loop."""

    node_type = "optimizer"

    def optimizer_code(self, w):
        n = self.node
        props = n.properties

        def pybool(val):
            return "True" if val else "False"

        config_lines = [
            f"'loss_type': '{props.get('lossType', 'mse')}'",
            f"'optimizer_type': '{props.get('optimizerType', 'adam')}'",
            f"'learning_rate': {props.get('learningRate', 0.001)}",
            f"'adam_beta1': {props.get('adamBeta1', 0.9)}",
            f"'adam_beta2': {props.get('adamBeta2', 0.999)}",
            f"'adam_epsilon': {props.get('adamEpsilon', 1e-8)}",
            f"'sgd_momentum': {props.get('sgdMomentum', 0.9)}",
            f"'weight_decay': {props.get('weightDecay', 0)}",
            f"'nesterov': {pybool(props.get('nesterov', False))}",
            f"'epochs': {props.get('epochs', 10)}",
            f"'batch_size': {props.get('batchSize', 32)}",
            f"'shuffle': {pybool(props.get('shuffle', True))}",
            f"'gradient_clip': {props.get('gradientClip') if props.get('gradientClip') is not None else 'None'}",
            f"'early_stopping': {pybool(props.get('earlyStopping', False))}",
            f"'early_stopping_patience': {props.get('earlyStoppingPatience', 10)}",
        ]
        return (
            "{\n" + ",\n".join(f"        {line}" for line in config_lines) + "\n    }"
        )


class VisualizationTranslator(BaseTranslator):
    """Generates matplotlib plotting code for scatter plots (1‑3 coords, optional colour)."""

    node_type = "visualization"

    def visualization_code(self, w):
        n = self.node
        coord_ports = [p for p in n.inputs if p.sub_type == "coord"]
        color_port = next((p for p in n.inputs if p.role == "color"), None)

        w.line(f"# Visualization '{n.id}'")
        w.line("plt.figure()")

        var_names = []
        for i, port in enumerate(coord_ports):
            var = f"data_{i}"
            w.line(f"{var} = viz_data.get('{port.id}')")
            var_names.append(var)

        if color_port:
            w.line(f"colors = viz_data.get('{color_port.id}')")
        else:
            w.line("colors = None")

        color_mode = n.properties.get("colorMode", "none")
        cmap_name = "None"
        if color_mode == "discrete" and color_port:
            palette = n.properties.get("colorPalette", [])
            if palette:
                w.line("from matplotlib.colors import ListedColormap")
                hex_list = ", ".join(f"'{c}'" for c in palette)
                w.line(f"custom_cmap = ListedColormap([{hex_list}])")
                cmap_name = "custom_cmap"
            else:
                cmap_name = "'tab10'"
        elif color_mode == "continuous" and color_port:
            w.line("from matplotlib.colors import LinearSegmentedColormap")
            min_c = n.properties.get("continuousMinColor", "#3b82f6")
            max_c = n.properties.get("continuousMaxColor", "#ef4444")
            w.line(
                f"custom_cmap = LinearSegmentedColormap.from_list('cust', ['{min_c}', '{max_c}'])"
            )
            cmap_name = "custom_cmap"

        if len(coord_ports) == 1:
            w.line(f"plt.hist({var_names[0]}.flatten(), bins=20)")
        elif len(coord_ports) == 2:
            if color_port and cmap_name != "None":
                w.line(
                    f"plt.scatter({var_names[0]}.flatten(), {var_names[1]}.flatten(), "
                    f"c=colors.flatten(), alpha=0.5, cmap={cmap_name})"
                )
                if color_mode == "continuous":
                    w.line("cbar = plt.colorbar()")
                    w.line("cbar.set_label('Value')")
            else:
                w.line(
                    f"plt.scatter({var_names[0]}.flatten(), {var_names[1]}.flatten(), alpha=0.5)"
                )
        elif len(coord_ports) == 3:
            w.line("fig = plt.figure()")
            w.line("ax = fig.add_subplot(111, projection='3d')")
            if color_port and cmap_name != "None":
                w.line(
                    f"ax.scatter({var_names[0]}, {var_names[1]}, {var_names[2]}, "
                    f"c=colors.flatten(), alpha=0.5, cmap={cmap_name})"
                )
            else:
                w.line(f"ax.scatter({var_names[0]}, {var_names[1]}, {var_names[2]})")

        w.line(f"plt.title('Visualization {n.id}')")
        w.line("plt.grid(True)")
        w.line("plt.show()")


class PrintTranslator(BaseTranslator):
    """Prints the shape and content of a tensor (for debugging)."""

    node_type = "print"

    def data_code(self, w, phase):
        n = self.node
        label = n.properties.get("label", "") or n.id
        for i, port in enumerate(n.inputs):
            for link in self.graph.links:
                if link.id_to == port.id:
                    src_port_id = link.id_from
                    if src_port_id in self.var_map:
                        var = self.var_map[src_port_id]
                    else:
                        src_id = self.graph.ports[src_port_id].node_id
                        var = self.var_map.get(src_id, "None")
                    w.line(f'print("{label}[{i}]:", {var}.shape, {var})')
                    break


class AccuracyTranslator(BaseTranslator):
    """Computes classification accuracy and optionally prints a confusion matrix."""

    node_type = "accuracy"

    def data_code(self, w, phase):
        n = self.node
        show_confusion = n.properties.get("showConfusion", False)
        pred_var = None
        label_var = None
        for port in n.inputs:
            for link in self.graph.links:
                if link.id_to == port.id:
                    src_port_id = link.id_from
                    if src_port_id in self.var_map:
                        var = self.var_map[src_port_id]
                    else:
                        src_id = self.graph.ports[src_port_id].node_id
                        var = self.var_map.get(src_id, "None")
                    if port.index == 0:
                        pred_var = var
                    else:
                        label_var = var
                    break
        if not pred_var or not label_var:
            w.line("# Accuracy node missing inputs")
            return

        w.line("# Accuracy calculation")
        w.line(
            f"pred_labels = {pred_var}.argmax(dim=1) if {pred_var}.dim() == 2 else {pred_var}"
        )
        w.line(
            f"true_labels = {label_var}.argmax(dim=1) if {label_var}.dim() == 2 else {label_var}"
        )
        w.line("acc = (pred_labels == true_labels).float().mean()")
        w.line('print(f"Accuracy: {acc.item():.4f}")')

        if show_confusion:
            w.line("from sklearn.metrics import confusion_matrix")
            w.line("cm = confusion_matrix(true_labels.cpu(), pred_labels.cpu())")
            w.line('print("Confusion Matrix:")')
            w.line("print(cm)")


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
TRANSLATOR_REGISTRY = {
    "input-data": InputDataTranslator,
    "column-select": ColumnSelectTranslator,
    "row-select": RowSelectTranslator,
    "dim-select": DimSelectTranslator,
    "normalize": NormalizeTranslator,
    "onehot": OneHotTranslator,
    "deonehot": DeOneHotTranslator,
    "train-test": TrainTestSplitTranslator,
    "neuron": NeuronTranslator,
    "layer": LayerTranslator,
    "conv2d": Conv2DTranslator,
    "flatten": FlattenTranslator,
    "dropout": DropoutTranslator,
    "batchnorm": BatchNormTranslator,
    "add": AddTranslator,
    "concat": ConcatTranslator,
    "output": OutputTranslator,
    "optimizer": OptimizerTranslator,
    "visualization": VisualizationTranslator,
    "print": PrintTranslator,
    "accuracy": AccuracyTranslator,
}


def get_translator(node, graph, var_map):
    """Return the translator instance for a given node."""
    cls = TRANSLATOR_REGISTRY.get(node.type, BaseTranslator)
    return cls(node, graph, var_map)
