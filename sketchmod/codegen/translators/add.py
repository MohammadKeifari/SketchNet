from .base import BaseTranslator


class AddTranslator(BaseTranslator):
    node_type = "add"

    def init_code(self, writer, is_sequential):
        pass

    def forward_code(self, writer, input_var, skip_vars):
        incoming = self.g.get_links_to(self.node["id"])
        sources = []
        for link in incoming:
            src_node = self.g._port_node_id(link["from"])
            if src_node and src_node in skip_vars:
                sources.append(skip_vars[src_node])
            else:
                sources.append(input_var)
        if len(sources) < 2:
            sources.append(input_var)
        out = f"x_{self.safe_id()}"
        writer.line(f"{out} = {sources[0]} + {sources[1]}  # Skip connection")
        return out
