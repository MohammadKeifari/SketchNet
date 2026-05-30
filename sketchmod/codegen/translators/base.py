class BaseTranslator:
    node_type = None

    def __init__(self, node, generator):
        self.node = node
        self.g = generator

    def safe_id(self):
        return self.node["id"].replace("-", "_")

    def init_code(self, writer, is_sequential):
        pass

    def forward_code(self, writer, input_var, skip_vars):
        return input_var

    def data_code(self, writer, input_var):
        return input_var

    def optimizer_code(self, writer):
        pass

    def training_code(self, writer):
        pass
