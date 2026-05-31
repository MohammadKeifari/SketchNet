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
        """Trace back through preprocessing to find input feature count."""
        incoming = self.g._links_to(self.node["id"])
        if not incoming:
            return None

        src_port_id = incoming[0]["from"]
        src_node_id = self.g._port_node_id(src_port_id)

        return self._trace_features_back(src_node_id, src_port_id)

    def _trace_features_back(self, node_id, port_id):
        """Recursively trace back through graph to find feature dimension."""
        node = self.g._node_map.get(node_id, {})
        if not node:
            return None

        t = node.get("type")

        # ColumnSelect: count selected columns
        if t == "column-select":
            cols = node.get("selectedColumns", [])
            if cols:
                return len(cols)
            col_input = node.get("columnInput", "")
            if col_input:
                return self._parse_column_count(col_input)
            return None

        # TrainTestSplit: trace back through its input
        if t == "train-test":
            incoming = self.g._links_to(node_id)
            if incoming:
                next_src = self.g._port_node_id(incoming[0]["from"])
                return self._trace_features_back(next_src, incoming[0]["from"])

        # Pass-through nodes: trace back
        if t in ("normalize", "row-select", "dim-select", "onehot"):
            incoming = self.g._links_to(node_id)
            if incoming:
                next_src = self.g._port_node_id(incoming[0]["from"])
                return self._trace_features_back(next_src, incoming[0]["from"])

        # InputData: parse dataShape
        if t == "input-data":
            shape = node.get("dataShape", "")
            if shape:
                import re

                parts = re.findall(r"\d+", shape)
                if parts:
                    return int(parts[-1])
            return None

        # Port shape as fallback
        port = self.g._port_map.get(port_id, {})
        shape_data = port.get("shape", {})
        if shape_data and shape_data.get("shape"):
            shape = shape_data["shape"]
            if len(shape) >= 2:
                last_dim = shape[-1]
                if isinstance(last_dim, (int, float)):
                    return int(last_dim)
                if isinstance(last_dim, str):
                    try:
                        return int(last_dim)
                    except ValueError:
                        return None

        return None

    def _parse_column_count(self, col_input):
        """Parse '0:2' → 3, '0,1,2' → 3"""
        import re

        total = 0
        for part in col_input.split(","):
            part = part.strip()
            if ":" in part:
                match = re.match(r"(\d*):(\d*)", part)
                if match:
                    start = int(match.group(1)) if match.group(1) else 0
                    end = int(match.group(2)) if match.group(2) else 0
                    total += max(0, end - start + 1)
            elif part.isdigit():
                total += 1
        return total if total > 0 else None

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
