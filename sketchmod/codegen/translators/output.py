from .base import BaseTranslator


class OutputTranslator(BaseTranslator):
    node_type = "output"

    def init_code(self, writer, is_sequential):
        pass

    def forward_code(self, writer, input_var, skip_vars):
        writer.line(f"return {input_var}")
        return input_var
