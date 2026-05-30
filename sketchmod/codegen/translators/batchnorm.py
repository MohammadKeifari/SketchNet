from .base import BaseTranslator


class BatchNormTranslator(BaseTranslator):
    node_type = "batchnorm"

    def init_code(self, writer, is_sequential):
        sid = self.safe_id()
        if is_sequential:
            writer.line("nn.BatchNorm1d(num_features),")
        else:
            writer.line(f"self.bn_{sid} = nn.BatchNorm1d(num_features)")

    def forward_code(self, writer, input_var, skip_vars):
        sid = self.safe_id()
        out = f"x_{sid}"
        writer.line(f"{out} = self.bn_{sid}({input_var})")
        return out
