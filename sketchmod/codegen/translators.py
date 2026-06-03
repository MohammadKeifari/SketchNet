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

    def _get_input_var(self, node):
        for port in node.inputs + node.paramInputs:
            for link in self.graph.links:
                if link.id_to == port.id:
                    src_id = self.graph.ports[link.id_from].node_id
                    if src_id in self.var_map:
                        return self.var_map[src_id]
                    src_port = self.graph.ports[link.id_from]
                    if src_port.id in self.var_map:
                        return self.var_map[src_port.id]
        return "raw_data"


# ---------------------------------------------------------------------------
# DATA NODES
# ---------------------------------------------------------------------------
class InputDataTranslator(BaseTranslator):
    node_type = "input-data"

    def data_code(self, w, phase):
        n = self.node
        ds = n.properties.get("dataShape")
        dataset_id = n.properties.get("datasetId")
        dataset_file = n.properties.get("datasetFile", "")
        dataset_format = n.properties.get("datasetFormat", "")

        if dataset_id and dataset_file:
            # Real dataset – generate loading code
            ext = dataset_format or dataset_file.rsplit(".", 1)[-1]
            if ext in ("csv", "xlsx", "json", "parquet"):
                if ext == "csv":
                    w.line(f"import pandas as pd")
                    w.line(f"df = pd.read_csv('data/{dataset_file}')")
                elif ext == "xlsx":
                    w.line(f"import pandas as pd")
                    w.line(f"df = pd.read_excel('data/{dataset_file}')")
                elif ext == "json":
                    w.line(f"import pandas as pd")
                    w.line(f"df = pd.read_json('data/{dataset_file}')")
                elif ext == "parquet":
                    w.line(f"import pandas as pd")
                    w.line(f"df = pd.read_parquet('data/{dataset_file}')")
                w.line("raw_data = torch.tensor(df.values, dtype=torch.float32)")
            else:
                w.line(f"# Unsupported format '{ext}' – loading random data instead")
                w.line("raw_data = torch.randn(200, 10)")
            self.var_map[n.id] = "raw_data"
        elif ds:
            # Manual shape
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

        # Check if a param input is connected (for sharing encoding)
        param_input = None
        if n.paramOutputs:
            param_input = f"{n.id}_categories"

        w.line(f"# OneHot encode – squeeze last dim if needed")
        w.line(f"{in_var}_squeezed = {in_var}.squeeze(-1).long()")
        w.line(
            f"{out_var} = torch.nn.functional.one_hot({in_var}_squeezed, num_classes={num_classes}).float()"
        )
        self.var_map[n.id] = out_var

        # Store categories for sharing via param output
        if n.paramOutputs:
            w.line(f"categories = torch.arange({num_classes})")
            self.var_map[n.paramOutputs[0].id] = "categories"


class DeOneHotTranslator(BaseTranslator):
    node_type = "deonehot"

    def data_code(self, w, phase):
        n = self.node
        in_var = self._get_input_var(n)
        out_var = f"{n.id}_out"

        # Check if a param input is connected (for shared encoding)
        param_input = None
        if n.paramInputs:
            for link in self.graph.links:
                if link.id_to == n.paramInputs[0].id:
                    param_input = self.var_map.get(link.id_from)
                    break

        if param_input:
            w.line(f"categories = {param_input}")
            w.line(f"{out_var} = torch.argmax({in_var}, dim=-1)")
        else:
            w.line(f"{out_var} = torch.argmax({in_var}, dim=-1)")

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
        w.line(f"# --- {n.type} {n.id} ---")
        # Collect source node IDs and weights
        terms = []
        for port in n.inputs:
            for link in self.graph.links:
                if link.id_to == port.id:
                    src_id = self.graph.ports[link.id_from].node_id
                    weight_name = f"self.weight_{link.id_from}_{link.id_to}"
                    terms.append((src_id, weight_name))
        if not terms:
            w.line(f"outputs['{n.id}'] = None  # no input connected")
            return

        # Build weighted sum using values from `outputs` (internal nodes) or `inputs_dict` (first layer)
        w.line(f"x = None")
        for src_id, wgt in terms:
            w.line(f"if '{src_id}' in outputs or '{src_id}' in inputs_dict:")
            w.indent()
            w.line(f"val = outputs.get('{src_id}', inputs_dict.get('{src_id}'))")
            w.line(f"if x is None: x = {wgt} * val")
            w.line(f"else: x = x + {wgt} * val")
            w.dedent()
        w.line("if x is None:")
        w.indent()
        w.line(f'raise ValueError("No input for {n.type} {n.id}")')
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
            ids = ", ".join(f"'{p}'" for p in preds)
            w.line(
                f"tensors = [inputs_dict.get(p) for p in [{ids}] if inputs_dict.get(p) is not None]"
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
        # The output node receives its input from the last model layer.
        # We read from the internal 'outputs' dict, not from 'inputs_dict'.
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
                w.line(f"outputs['{out_port.id}'] = x")
            w.line(f"outputs['{n.id}'] = x")
            w.dedent()
        else:
            w.line(f"outputs['{n.id}'] = None  # no input connected")


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

        var_names = []
        for i, port in enumerate(coord_ports):
            var = f"data_{i}"
            w.line(f"{var} = viz_data.get('{port.id}')")
            var_names.append(var)

        # Determine if we have a colour source
        if color_port:
            w.line(f"colors = viz_data.get('{color_port.id}')")
        else:
            w.line("colors = None")

        # Build a custom colormap from the user's palette only for discrete mode
        color_mode = n.properties.get("colorMode", "none")
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
            # use a default continuous map, or the user's min/max colours
            w.line(f"from matplotlib.colors import LinearSegmentedColormap")
            min_c = n.properties.get("continuousMinColor", "#3b82f6")
            max_c = n.properties.get("continuousMaxColor", "#ef4444")
            w.line(
                f"custom_cmap = LinearSegmentedColormap.from_list('cust', ['{min_c}', '{max_c}'])"
            )
            cmap_name = "custom_cmap"
        else:
            cmap_name = "None"

        # Draw the scatter plot
        if len(coord_ports) == 1:
            w.line(f"plt.hist({var_names[0]}.flatten(), bins=20)")
        elif len(coord_ports) == 2:
            if color_port and cmap_name != "None":
                w.line(
                    f"plt.scatter({var_names[0]}.flatten(), {var_names[1]}.flatten(), "
                    f"c=colors.flatten(), alpha=0.5, cmap={cmap_name})"
                )
                # Only add color bar for continuous mode
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
    node_type = "print"

    def data_code(self, w, phase):
        n = self.node
        label = n.properties.get("label", "") or n.id
        # Print each connected input
        for i, port in enumerate(n.inputs):
            for link in self.graph.links:
                if link.id_to == port.id:
                    src_id = self.graph.ports[link.id_from].node_id
                    var = self.var_map.get(src_id, "None")
                    w.line(f'print("{label}[{i}]:", {var}.shape, {var}[:3])')
                    break


class AccuracyTranslator(BaseTranslator):
    node_type = "accuracy"

    def data_code(self, w, phase):
        n = self.node
        show_confusion = n.properties.get("showConfusion", False)
        # Get the two input variables
        pred_var = None
        label_var = None
        for port in n.inputs:
            for link in self.graph.links:
                if link.id_to == port.id:
                    src_id = self.graph.ports[link.id_from].node_id
                    var = self.var_map.get(src_id, "None")
                    if port.index == 0:
                        pred_var = var
                    else:
                        label_var = var
                    break
        if not pred_var or not label_var:
            w.line("# Accuracy node missing inputs")
            return

        w.line(f"# Accuracy calculation")
        w.line(
            f"pred_labels = {pred_var}.argmax(dim=1) if {pred_var}.dim() == 2 else {pred_var}"
        )
        w.line(
            f"true_labels = {label_var}.argmax(dim=1) if {label_var}.dim() == 2 else {label_var}"
        )
        w.line(f"acc = (pred_labels == true_labels).float().mean()")
        w.line(f'print(f"Accuracy: {{acc.item():.4f}}")')

        if show_confusion:
            w.line(
                "from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay"
            )
            w.line(f"cm = confusion_matrix(true_labels.cpu(), pred_labels.cpu())")
            w.line("disp = ConfusionMatrixDisplay(confusion_matrix=cm)")
            w.line("disp.plot()")
            w.line("plt.title('Confusion Matrix')")
            w.line("plt.show()")


# Registry mapping node type -> translator class
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
    cls = TRANSLATOR_REGISTRY.get(node.type, BaseTranslator)
    return cls(node, graph, var_map)
