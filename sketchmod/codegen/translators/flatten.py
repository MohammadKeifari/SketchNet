from .base import BaseTranslator


class FlattenTranslator(BaseTranslator):
    node_type = "flatten"

    def init_code(self, writer, is_sequential):
        if is_sequential:
            writer.line("nn.Flatten(),")
        else:
            writer.line("self.flatten = nn.Flatten()")

    def forward_code(self, writer, input_var, skip_vars):
        out = f"x_{self.safe_id()}"
        writer.line(f"{out} = self.flatten({input_var})")
        return out
