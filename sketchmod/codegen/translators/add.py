from .base import BaseTranslator


class AddTranslator(BaseTranslator):
    node_type = "add"

    def init_code(self, writer, is_sequential):
        pass

    def forward_code(self, writer, input_vars, skip_vars):
        vars_list = list(input_vars.values())
        if len(vars_list) < 2:
            # Try skip_vars
            incoming = self.g.get_links_to(self.node["id"])
            for link in incoming:
                src_node = self.g._port_node_id(link["from"])
                if src_node and src_node in skip_vars:
                    for v in skip_vars[src_node]:
                        if v not in vars_list:
                            vars_list.append(v)
        if len(vars_list) < 2:
            vars_list.append(vars_list[0] if vars_list else "x")
        out_var = self.output_vars()[0]
        writer.line(f"{out_var} = {vars_list[0]} + {vars_list[1]}  # Skip connection")
        return [out_var]
