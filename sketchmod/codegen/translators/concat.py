from .base import BaseTranslator


class ConcatTranslator(BaseTranslator):
    node_type = "concat"

    def init_code(self, writer, is_sequential):
        pass

    def forward_code(self, writer, input_vars):
        axis = self.node.get("axis", -1)
        vars_list = list(input_vars.values())
        vars_str = ", ".join(vars_list) if vars_list else "x"
        out_var = f"data_{self.node_id()}"
        writer.line(f"{out_var} = torch.cat([{vars_str}], dim={axis})")
        return [out_var]
