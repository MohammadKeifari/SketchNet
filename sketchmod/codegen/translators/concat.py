from .base import BaseTranslator


class ConcatTranslator(BaseTranslator):
    node_type = "concat"

    def init_code(self, writer, is_sequential):
        pass

    def forward_code(self, writer, input_var, skip_vars):
        axis = self.node.get("axis", -1)
        incoming = self.g.get_links_to(self.node["id"])
        sources = []
        for link in incoming:
            src_node = self.g._port_node_id(link["from"])
            if src_node and src_node in skip_vars:
                sources.append(skip_vars[src_node])
            else:
                sources.append(input_var)
        vars_list = ", ".join(sources) if sources else input_var
        out = f"x_{self.safe_id()}"
        writer.line(f"{out} = torch.cat([{vars_list}], dim={axis})")
        return out
