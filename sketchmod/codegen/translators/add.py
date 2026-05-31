from .base import BaseTranslator


class AddTranslator(BaseTranslator):
    node_type = "add"

    def init_code(self, writer, is_sequential):
        pass

    def forward_code(self, writer, input_vars):
        vars_list = list(input_vars.values())
        if len(vars_list) < 2:
            vars_list.append(vars_list[0] if vars_list else "x")
        out_var = f"data_{self.node_id()}"
        writer.line(f"{out_var} = {vars_list[0]} + {vars_list[1]}  # Skip connection")
        return [out_var]
