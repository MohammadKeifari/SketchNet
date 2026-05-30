from .base import BaseTranslator


class FlattenTranslator(BaseTranslator):
    node_type = "flatten"

    def init_code(self, writer, is_sequential):
        if is_sequential:
            writer.line("nn.Flatten(),")
        else:
            writer.line("self.flatten = nn.Flatten()")

    def forward_code(self, writer, input_vars, skip_vars):
        src_var = list(input_vars.values())[0]
        out_var = self.output_vars()[0]
        writer.line(f"{out_var} = self.flatten({src_var})")
        return [out_var]
