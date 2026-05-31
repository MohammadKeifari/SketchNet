class BaseTranslator:
    node_type = None

    def __init__(self, node, generator):
        self.node = node
        self.g = generator

    def node_id(self):
        return self.node["id"].replace("-", "_")

    def output_vars(self):
        """Return list of output variable names this node produces."""
        return [f"data_{self.node_id()}"]

    def input_features(self):
        """Return the expected input feature dimension, or None if unknown."""
        return self._resolve_input_features()

    def _resolve_input_features(self):
        """Default: look at the first incoming link's source port shape."""
        incoming = self.g._links_to(self.node["id"])
        if not incoming:
            return None

        src_port_id = incoming[0]["from"]
        src_port = self.g._port_map.get(src_port_id, {})
        shape_data = src_port.get("shape", {})

        if shape_data and shape_data.get("shape"):
            shape = shape_data["shape"]
            if len(shape) >= 2:
                last_dim = shape[-1]
                if isinstance(last_dim, (int, float)):
                    return int(last_dim)
                return str(last_dim)  # Symbolic like "F" or "C"
            if len(shape) == 1:
                return (
                    int(shape[0])
                    if isinstance(shape[0], (int, float))
                    else str(shape[0])
                )

        return None

    # === MODEL ===
    def init_code(self, writer, is_sequential, in_features="in_features"):
        pass

    def forward_code(self, writer, input_vars, skip_vars):
        """input_vars: dict port_index -> variable_name. Returns list of output var names."""
        return self.output_vars()

    # === DATA ===
    def data_code(self, writer, input_vars):
        """input_vars: dict port_index -> variable_name. Returns list of output var names."""
        return self.output_vars()

    # === TRAINING ===
    def optimizer_code(self, writer):
        pass

    def training_code(self, writer):
        pass
