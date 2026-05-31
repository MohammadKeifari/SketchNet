from .base import BaseTranslator


class DropoutTranslator(BaseTranslator):
    node_type = "dropout"

    def init_code(self, writer, is_sequential):
        sid = self.node_id()
        rate = self.node.get("rate", 0.5)
        if is_sequential:
            writer.line(f"nn.Dropout({rate}),")
        else:
            writer.line(f"self.dropout_{sid} = nn.Dropout({rate})")

    def forward_code(self, writer, input_vars):
        src_var = list(input_vars.values())[0]
        sid = self.node_id()
        out_var = self.output_vars()[0]
        writer.line(f"{out_var} = self.dropout_{sid}({src_var})")
        return [out_var]

    def validate(self):
        errors, warnings = [], []
        rate = self.node.get("rate", 0.5)

        if rate > 0.8:
            warnings.append(f"Dropout: rate is very high ({int(rate * 100)}%)")

        return {"errors": errors, "warnings": warnings}
