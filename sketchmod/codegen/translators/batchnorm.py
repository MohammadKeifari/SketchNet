from .base import BaseTranslator


class BatchNormTranslator(BaseTranslator):
    node_type = "batchnorm"

    def init_code(self, writer, is_sequential):
        sid = self.node_id()
        if is_sequential:
            writer.line("nn.BatchNorm1d(num_features),")
        else:
            writer.line(f"self.bn_{sid} = nn.BatchNorm1d(num_features)")

    def forward_code(self, writer, input_vars):
        src_var = list(input_vars.values())[0]
        sid = self.node_id()
        out_var = self.output_vars()[0]
        writer.line(f"{out_var} = self.bn_{sid}({src_var})")
        return [out_var]
