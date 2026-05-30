from .base import BaseTranslator


class DropoutTranslator(BaseTranslator):
    node_type = "dropout"

    def init_code(self, writer, is_sequential):
        sid = self.safe_id()
        rate = self.node.get("rate", 0.5)
        if is_sequential:
            writer.line(f"nn.Dropout({rate}),")
        else:
            writer.line(f"self.dropout_{sid} = nn.Dropout({rate})")

    def forward_code(self, writer, input_var, skip_vars):
        sid = self.safe_id()
        out = f"x_{sid}"
        writer.line(f"{out} = self.dropout_{sid}({input_var})")
        return out
