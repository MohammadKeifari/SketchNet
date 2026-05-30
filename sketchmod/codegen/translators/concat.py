from .base import BaseTranslator


class ConcatTranslator(BaseTranslator):
    node_type = "concat"

    def init_code(self, writer, is_sequential):
        pass

    def forward_code(self, writer, input_vars, skip_vars):
        axis = self.node.get("axis", -1)
        vars_list = list(input_vars.values())
        if len(vars_list) < 2:
            incoming = self.g.get_links_to(self.node["id"])
            for link in incoming:
                src_node = self.g._port_node_id(link["from"])
                if src_node and src_node in skip_vars:
                    for v in skip_vars[src_node]:
                        if v not in vars_list:
                            vars_list.append(v)
        vars_str = ", ".join(vars_list) if vars_list else "x"
        out_var = self.output_vars()[0]
        writer.line(f"{out_var} = torch.cat([{vars_str}], dim={axis})")
        return [out_var]
