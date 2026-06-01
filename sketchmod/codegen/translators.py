"""
Translators convert SketchNet nodes into PyTorch code snippets.
Each translator has methods for:
    data_code   – code executed once in load_and_preprocess()
    init_code   – code for Model.__init__()
    forward_code – code for Model.forward()
    extra_code  – additional code (e.g., optimizer config, visualization)
"""


class BaseTranslator:
    """Default translator – does nothing."""

    node_type = None

    def __init__(self, node, graph, var_map):
        self.node = node
        self.graph = graph
        self.var_map = var_map  # maps node/port id -> variable name

    def data_code(self, w, phase):
        """Generate preprocessing / data‑transform code."""
        pass

    def init_code(self, w):
        """Generate model __init__ code."""
        pass

    def forward_code(self, w):
        """Generate model forward code."""
        pass

    def optimizer_code(self, w):
        """Return optimizer config dict as a Python dict literal."""
        return "{}"

    def visualization_code(self, w):
        """Generate visualization code."""
        pass


# ---------------------------------------------------------------------------
# DATA NODES
# ---------------------------------------------------------------------------
class InputDataTranslator(BaseTranslator):
    node_type = "input-data"

    def data_code(self, w, phase):
        n = self.node
        ds = n.properties.get("dataShape")
        if ds:
            parts = ds.strip("()").split(",")
            row_sym = parts[0].strip()
            cols = [int(p.strip()) for p in parts[1:]]
            w.line(f"# InputData '{n.id}': manual shape {ds}")
            w.line(f"num_rows = 200  # placeholder for '{row_sym}'")
            w.line(
                f"raw_data = torch.randn(num_rows, {', '.join(str(c) for c in cols)})"
            )
            self.var_map[n.id] = "raw_data"
        else:
            w.line("# No shape or dataset provided – creating random data")
            w.line("raw_data = torch.randn(200, 10)")
            self.var_map[n.id] = "raw_data"


class ColumnSelectTranslator(BaseTranslator):
    node_type = "column-select"

    def data_code(self, w, phase):
        n = self.node
        cols = n.properties.get("selectedColumns", [])
        if not cols:
            col_str = n.properties.get("columnInput", "")
            if col_str:
                w.line(f"# ColumnSelect '{n.id}' with input '{col_str}'")
                # generate dynamic selection using Python slice syntax
                w.line(f"indices = list(range({col_str}))")
                in_var = self._get_input_var(n)
                out_var = f"{n.id}_out"
                w.line(f"{out_var} = {in_var}[:, indices]")
                self.var_map[n.id] = out_var
            else:
                # pass-through
                self.var_map[n.id] = self._get_input_var(n)
        else:
            col_list = ", ".join(str(c) for c in cols)
            in_var = self._get_input_var(n)
            out_var = f"{n.id}_out"
            w.line(f"{out_var} = {in_var}[:, [{col_list}]]")
            self.var_map[n.id] = out_var

    def _get_input_var(self, node):
        for port in node.inputs:
            for link in self.graph.links:
                if link.id_to == port.id:
                    src_id = self.graph.ports[link.id_from].node_id
                    # Check var_map for node id or port id
                    if src_id in self.var_map:
                        return self.var_map[src_id]
                    src_port = self.graph.ports[link.id_from]
                    if src_port.id in self.var_map:
                        return self.var_map[src_port.id]
        return "raw_data"


class RowSelectTranslator(BaseTranslator):
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
    node_type = "dim-select"

    def data_code(self, w, phase):
        n = self.node
        dims = n.properties.get("dimSelections", [])
        in_var = self._get_input_var(n)
        out_var = f"{n.id}_out"
        # For now, we'll generate a simple pass-through if all dims are ":"
        if all(not s or s.strip() == ":" for s in dims):
            w.line(f"{out_var} = {in_var}  # no dimension selection")
        else:
            # Build a list of indices for each dimension
            slices = []
            for sel in dims:
                if not sel or sel.strip() == ":":
                    slices.append(":")
                else:
                    # parse like "0,1,2" or "0:3"
                    slices.append(f"[{sel}]")
            if all(s == ":" for s in slices):
                w.line(f"{out_var} = {in_var}")
            else:
                # concatenate slices after the batch dim
                slice_str = "[:, " + ", ".join(slices) + "]"
                w.line(f"{out_var} = {in_var}{slice_str}")
        self.var_map[n.id] = out_var

    def _get_input_var(self, node):
        return ColumnSelectTranslator._get_input_var(self, node)


class NormalizeTranslator(BaseTranslator):
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
    node_type = "onehot"

    def data_code(self, w, phase):
        n = self.node
        num_classes = n.properties.get("numClasses", 10)
        in_var = self._get_input_var(n)
        out_var = f"{n.id}_out"

        # Check if a ParamInput is connected – we can reuse fitted categories
        param_input = None
        if n.paramInputs:
            for link in self.graph.links:
                if link.id_to == n.paramInputs[0].id:
                    param_input = self.var_map.get(link.id_from)  # source variable name
                    break

        if param_input:
            # Use the pre‑fitted categories (e.g., from a training branch node)
            w.line(f"categories = {param_input}")
            w.line(f"# Ensure categories is a tensor of shape ({num_classes},)")
            w.line(
                f"{out_var} = torch.nn.functional.one_hot({in_var}.long(), num_classes=len(categories)).float()"
            )
            # If categories length might differ from num_classes, we'll just use the tensor directly
            # Simplified: assume categories is a tensor of class indices
            w.line(
                f"# Assuming categories is a 1D tensor of class indices, map labels to these categories"
            )
            w.line(f"# This is a placeholder – adjust as needed")
        else:
            # Compute categories from data (unique values or fixed range)
            w.line(
                f"categories = torch.arange({num_classes})  # assume consecutive 0..{num_classes-1}"
            )
            w.line(
                f"{out_var} = torch.nn.functional.one_hot({in_var}.long(), num_classes={num_classes}).float()"
            )
            # If this node has a param output, we can store the categories for later use
            if n.paramOutputs:
                # Store the categories variable in var_map under the param output port id
                # so that another onehot node can reuse it.
                self.var_map[n.paramOutputs[0].id] = "categories"

        self.var_map[n.id] = out_var


class TrainTestSplitTranslator(BaseTranslator):
    node_type = "train-test"

    def data_code(self, w, phase):
        n = self.node
        train_ratio = n.properties.get("trainRatio", 0.7)
        seed = n.properties.get("randomSeed", 42)
        in_var = self._get_input_var(n)
        w.line(f"train_size = int({in_var}.size(0) * {train_ratio})")
        w.line(f"gen = torch.Generator().manual_seed({seed})")
        w.line(f"perm = torch.randperm({in_var}.size(0), generator=gen)")
        w.line(f"train_data = {in_var}[perm[:train_size]]")
        w.line(f"test_data = {in_var}[perm[train_size:]]")
        train_port = next(p for p in n.outputs if p.sub_type == "train")
        test_port = next(p for p in n.outputs if p.sub_type == "test")
        self.var_map[train_port.id] = "train_data"
        self.var_map[test_port.id] = "test_data"
        self.var_map[n.id] = "train_data"  # default fallback

    def _get_input_var(self, node):
        return ColumnSelectTranslator._get_input_var(self, node)


# ---------------------------------------------------------------------------
# MODEL NODES
# ---------------------------------------------------------------------------
class NeuronTranslator(BaseTranslator):
    node_type = "neuron"

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
        for port in n.inputs:
            for link in self.graph.links:
                if link.id_to == port.id:
                    weight_name = f"weight_{link.id_from}_{link.id_to}"
                    init_val = link.weight if link.weight != 0.0 else 1.0
                    w.line(
                        f"self.{weight_name} = nn.Parameter(torch.tensor({init_val}))"
                    )

    def forward_code(self, w):
        n = self.node
        w.line(f"# --- Neuron {n.id} ---")
        # Collect all incoming tensor names and corresponding weight parameters
        terms = []
        for port in n.inputs:
            for link in self.graph.links:
                if link.id_to == port.id:
                    src_id = self.graph.ports[link.id_from].node_id
                    weight_name = f"self.weight_{link.id_from}_{link.id_to}"
                    terms.append((src_id, weight_name))
                    break
        if not terms:
            w.line(f"outputs['{n.id}'] = None  # no input connected")
            return
        # Build weighted sum
        w.line(f"x = None")
        for src_id, wgt in terms:
            w.line(f"if '{src_id}' in inputs_dict:")
            w.indent()
            w.line(f"if x is None: x = {wgt} * inputs_dict['{src_id}']")
            w.line(f"else: x = x + {wgt} * inputs_dict['{src_id}']")
            w.dedent()
        w.line("if x is None:")
        w.indent()
        w.line(f'raise ValueError("No input for neuron {n.id}")')
        w.dedent()
        activation = n.properties.get("activation", "relu")
        w.line(f"x = self.fc_{n.id}(x)")
        w.line(f"x = torch.{activation}(x)")
        w.line(f"outputs['{n.id}'] = x")

    def _guess_in_features(self, node):
        for port in node.inputs:
            for link in self.graph.links:
                if link.id_to == port.id and link.weight_shape:
                    shape = link.weight_shape.get("shape", [])
                    if len(shape) >= 2:
                        return shape[1]
        return "input_size  # TODO: set input feature dimension"


class LayerTranslator(NeuronTranslator):
    node_type = "layer"

    def init_code(self, w):
        n = self.node
        in_features = self._guess_in_features(n)
        out_features = n.properties.get("numNeurons", 64)
        bias = n.properties.get("hasBias", True)
        bias_val = n.properties.get("bias", 0.0)
        w.line(
            f"self.fc_{n.id} = nn.Linear({in_features}, {out_features}, bias={bias})"
        )
        if bias:
            w.line(f"nn.init.constant_(self.fc_{n.id}.bias, {bias_val})")
        for port in n.inputs:
            for link in self.graph.links:
                if link.id_to == port.id:
                    weight_name = f"weight_{link.id_from}_{link.id_to}"
                    init_val = link.weight if link.weight != 0.0 else 1.0
                    w.line(
                        f"self.{weight_name} = nn.Parameter(torch.tensor({init_val}))"
                    )

    # forward_code inherited from NeuronTranslator


class Conv2DTranslator(BaseTranslator):
    node_type = "conv2d"

    def init_code(self, w):
        n = self.node
        in_channels = 1  # placeholder, should be derived from input shape
        out_channels = n.properties.get("filters", 32)
        kernel = n.properties.get("kernelSize", 3)
        stride = n.properties.get("stride", 1)
        padding = n.properties.get("padding", 0)
        bias = n.properties.get("hasBias", True)
        w.line(
            f"self.conv_{n.id} = nn.Conv2d({in_channels}, {out_channels}, kernel_size={kernel}, stride={stride}, padding={padding}, bias={bias})"
        )
        # scalar weights for input links (if multi-input)
        for port in n.inputs:
            for link in self.graph.links:
                if link.id_to == port.id:
                    weight_name = f"weight_{link.id_from}_{link.id_to}"
                    init_val = link.weight if link.weight != 0.0 else 1.0
                    w.line(
                        f"self.{weight_name} = nn.Parameter(torch.tensor({init_val}))"
                    )

    def forward_code(self, w):
        n = self.node
        # find input source (usually one)
        in_src = (
            list(self.graph.predecessors(n.id))[0]
            if self.graph.predecessors(n.id)
            else None
        )
        if in_src:
            w.line(f"x = inputs_dict.get('{in_src}')")
        else:
            w.line("x = inputs_dict[list(inputs_dict.keys())[0]]  # fallback")
        w.line(f"x = self.conv_{n.id}(x)")
        activation = n.properties.get("activation", "relu")
        w.line(f"x = torch.{activation}(x)")
        w.line(f"outputs['{n.id}'] = x")


class FlattenTranslator(BaseTranslator):
    node_type = "flatten"

    def init_code(self, w):
        n = self.node
        w.line(f"self.flatten_{n.id} = nn.Flatten()")

    def forward_code(self, w):
        n = self.node
        in_src = list(self.graph.predecessors(n.id))[0]
        w.line(f"x = inputs_dict['{in_src}']")
        w.line(f"x = self.flatten_{n.id}(x)")
        w.line(f"outputs['{n.id}'] = x")


class DropoutTranslator(BaseTranslator):
    node_type = "dropout"

    def init_code(self, w):
        n = self.node
        rate = n.properties.get("rate", 0.5)
        w.line(f"self.dropout_{n.id} = nn.Dropout(p={rate})")

    def forward_code(self, w):
        n = self.node
        in_src = list(self.graph.predecessors(n.id))[0]
        w.line(f"x = inputs_dict['{in_src}']")
        w.line(f"x = self.dropout_{n.id}(x)")
        w.line(f"outputs['{n.id}'] = x")


class BatchNormTranslator(BaseTranslator):
    node_type = "batchnorm"

    def init_code(self, w):
        n = self.node
        # Need num_features, guess from input
        w.line(
            f"self.bn_{n.id} = nn.BatchNorm1d(num_features=1)  # TODO: set num_features"
        )

    def forward_code(self, w):
        n = self.node
        in_src = list(self.graph.predecessors(n.id))[0]
        w.line(f"x = inputs_dict['{in_src}']")
        w.line(f"x = self.bn_{n.id}(x)")
        w.line(f"outputs['{n.id}'] = x")


class AddTranslator(BaseTranslator):
    node_type = "add"

    def init_code(self, w):
        pass  # no parameters

    def forward_code(self, w):
        n = self.node
        preds = list(self.graph.predecessors(n.id))
        if len(preds) >= 2:
            w.line(f"a = inputs_dict.get('{preds[0]}')")
            w.line(f"b = inputs_dict.get('{preds[1]}')")
            w.line(f"if a is not None and b is not None:")
            w.indent()
            w.line(f"x = a + b")
            w.line(f"outputs['{n.id}'] = x")
            w.dedent()
        else:
            w.line(f"outputs['{n.id}'] = None  # Add requires 2 inputs")


class ConcatTranslator(BaseTranslator):
    node_type = "concat"

    def init_code(self, w):
        pass

    def forward_code(self, w):
        n = self.node
        preds = list(self.graph.predecessors(n.id))
        axis = n.properties.get("axis", -1)
        if len(preds) >= 2:
            preds_str = ", ".join(f"'{p}'" for p in preds)
            w.line(
                f"tensors = [inputs_dict.get(p) for p in [{preds_str}] if inputs_dict.get(p) is not None]"
            )
            w.line(f"if len(tensors) > 1:")
            w.indent()
            w.line(f"x = torch.cat(tensors, dim={axis})")
            w.line(f"outputs['{n.id}'] = x")
            w.dedent()
        else:
            w.line(f"outputs['{n.id}'] = None  # Concat requires at least 2 inputs")


class OutputTranslator(BaseTranslator):
    node_type = "output"

    def init_code(self, w):
        pass

    def forward_code(self, w):
        n = self.node
        seen_sources = set()
        for port in n.inputs:
            src_id = None
            for link in self.graph.links:
                if link.id_to == port.id:
                    src_id = self.graph.ports[link.id_from].node_id
                    break
            if src_id and src_id not in seen_sources:
                seen_sources.add(src_id)
                w.line(f"if '{src_id}' in inputs_dict:")
                w.indent()
                w.line(f"x = inputs_dict['{src_id}']")
                for out_port in n.outputs:
                    w.line(f"outputs['{out_port.id}'] = x")
                w.dedent()
        w.line(f"if seen_sources: outputs['{n.id}'] = x")


# ---------------------------------------------------------------------------
# SPECIAL NODES (optimizer, visualization)
# ---------------------------------------------------------------------------
class OptimizerTranslator(BaseTranslator):
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
    node_type = "visualization"

    def visualization_code(self, w):
        n = self.node
        coord_ports = [p for p in n.inputs if p.sub_type == "coord"]
        color_port = next((p for p in n.inputs if p.role == "color"), None)
        w.line(f"# Visualization '{n.id}'")
        w.line("plt.figure()")
        if len(coord_ports) == 1:
            w.line("plt.hist(predictions.flatten(), bins=20)")
        elif len(coord_ports) == 2:
            w.line(
                "plt.scatter(y_test.numpy().flatten(), predictions.flatten(), alpha=0.5)"
            )
            w.line("plt.xlabel('True labels')")
            w.line("plt.ylabel('Predictions')")
        elif len(coord_ports) == 3:
            w.line("fig = plt.figure()")
            w.line("ax = fig.add_subplot(111, projection='3d')")
            w.line("ax.scatter(y_test, predictions, eval_values)")
        if color_port and n.properties.get("colorMode") in ("discrete", "continuous"):
            w.line("# Color mapping would go here (omitted for brevity)")
        w.line("plt.title(f'Visualization {n.id}')")
        w.line("plt.grid(True)")
        w.line("plt.show()")


# Registry mapping node type -> translator class
TRANSLATOR_REGISTRY = {
    "input-data": InputDataTranslator,
    "column-select": ColumnSelectTranslator,
    "row-select": RowSelectTranslator,
    "dim-select": DimSelectTranslator,
    "normalize": NormalizeTranslator,
    "onehot": OneHotTranslator,
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
}


def get_translator(node, graph, var_map):
    cls = TRANSLATOR_REGISTRY.get(node.type, BaseTranslator)
    return cls(node, graph, var_map)
