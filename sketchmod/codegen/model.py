class ModelGenerator:
    """Generates the PyTorch model class."""

    def __init__(self, generator):
        self.g = generator
        self.nodes = generator.nodes
        self.links = generator.links

    def generate(self, model_nodes=None):
        if model_nodes is None:
            ordered = self.g.topological_order()
            model_nodes = [n for n in ordered if n["type"] in self._model_types()]
        if not model_nodes:
            return []  # No model nodes, return empty

        is_seq = self._is_sequential(model_nodes)

        lines = []
        lines.append("class SketchNetModel(nn.Module):")
        lines.append("    def __init__(self):")
        lines.append("        super().__init__()")

        if is_seq:
            lines.append("        self.model = nn.Sequential(")
            for node in model_nodes:
                layer = self._layer_init(node)  # No assignment
                if layer:
                    lines.append(f"            {layer},")
            lines.append("        )")
        else:
            for node in model_nodes:
                layer = self._layer_def(node)  # With assignment
                if layer:
                    lines.append(f"        {layer}")

        lines.append("")
        lines.append("    def forward(self, x):")
        if is_seq:
            lines.append("        return self.model(x)")
        else:
            lines.extend(self._custom_forward(model_nodes))

        return lines

    def _model_types(self):
        return {
            "layer",
            "neuron",
            "conv2d",
            "flatten",
            "dropout",
            "batchnorm",
            "add",
            "concat",
        }

    def _is_sequential(self, model_nodes):
        """Check if model graph is a simple chain."""
        for node in model_nodes:
            if node["type"] in ("add", "concat"):
                return False
            incoming = [
                l
                for l in self.links
                if self.g._port_target_node(l["to"]) == node["id"]
                and self.g._node_map.get(self.g._port_source_node(l["from"]), {}).get(
                    "type"
                )
                in self._model_types()
            ]
            if len(incoming) > 1:
                return False
        return True

    def _safe_id(self, node_id):
        return node_id.replace("-", "_")

    def _layer_def(self, node):
        sid = self._safe_id(node["id"])
        t = node["type"]

        if t == "layer":
            neurons = node.get("numNeurons", 64)
            return f"self.{sid} = nn.Linear(in_features, {neurons})"
        elif t == "conv2d":
            filters = node.get("filters", 32)
            kernel = node.get("kernelSize", 3)
            stride = node.get("stride", 1)
            padding = node.get("padding", 0)
            return f"self.{sid} = nn.Conv2d(in_channels, {filters}, kernel_size={kernel}, stride={stride}, padding={padding})"
        elif t == "flatten":
            return "self.flatten = nn.Flatten()"
        elif t == "dropout":
            rate = node.get("rate", 0.5)
            return f"self.dropout_{sid} = nn.Dropout({rate})"
        elif t == "batchnorm":
            return f"self.bn_{sid} = nn.BatchNorm1d(num_features)"
        return None

    def _layer_init(self, node):
        """Return just the layer constructor for Sequential."""
        sid = self._safe_id(node["id"])
        t = node["type"]

        if t == "layer":
            neurons = node.get("numNeurons", 64)
            return f"nn.Linear(in_features, {neurons})"
        elif t == "conv2d":
            filters = node.get("filters", 32)
            kernel = node.get("kernelSize", 3)
            stride = node.get("stride", 1)
            padding = node.get("padding", 0)
            return f"nn.Conv2d(in_channels, {filters}, kernel_size={kernel}, stride={stride}, padding={padding})"
        elif t == "flatten":
            return "nn.Flatten()"
        elif t == "dropout":
            rate = node.get("rate", 0.5)
            return f"nn.Dropout({rate})"
        elif t == "batchnorm":
            return "nn.BatchNorm1d(num_features)"
        return None

    def _custom_forward(self, model_nodes):
        lines = []
        var = "x"
        skip_outputs = {}

        for node in model_nodes:
            sid = self._safe_id(node["id"])
            t = node["type"]

            if t == "add":
                # Find the two sources
                incoming = self.g.get_links_to(node["id"])
                sources = [self.g._port_source_node(l["from"]) for l in incoming]
                source_vars = [skip_outputs.get(s, "x") for s in sources]
                lines.append(
                    f"        {var} = {source_vars[0]} + {source_vars[1]}  # Skip connection"
                )
                skip_outputs[node["id"]] = var
            elif t == "concat":
                axis = node.get("axis", -1)
                incoming = self.g.get_links_to(node["id"])
                sources = [
                    skip_outputs.get(self.g._port_source_node(l["from"]), "x")
                    for l in incoming
                ]
                vars_list = ", ".join(sources)
                lines.append(f"        {var} = torch.cat([{vars_list}], dim={axis})")
                skip_outputs[node["id"]] = var
            elif t == "flatten":
                lines.append(f"        {var} = self.flatten({var})")
                skip_outputs[node["id"]] = var
            elif t == "dropout":
                lines.append(f"        {var} = self.dropout_{sid}({var})")
                skip_outputs[node["id"]] = var
            elif t == "batchnorm":
                lines.append(f"        {var} = self.bn_{sid}({var})")
                skip_outputs[node["id"]] = var
            elif t in ("layer", "conv2d"):
                lines.append(f"        {var} = self.{sid}({var})")
                activation = node.get("activation", "relu")
                if activation and activation != "linear":
                    act_fn = {"relu": "relu", "sigmoid": "sigmoid", "tanh": "tanh"}.get(
                        activation, activation
                    )
                    lines.append(f"        {var} = torch.{act_fn}({var})")
                skip_outputs[node["id"]] = var

        lines.append(f"        return {var}")
        return lines
