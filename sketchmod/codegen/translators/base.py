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

    # === MODEL ===
    def init_code(self, writer, is_sequential):
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
