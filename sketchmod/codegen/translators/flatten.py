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

    def output_features(self):
        """Compute what the flattened dimension will be."""
        incoming = self.g._links_to(self.node["id"])
        if not incoming:
            return None

        src_port_id = incoming[0]["from"]
        src_port = self.g._port_map.get(src_port_id, {})
        shape_data = src_port.get("shape", {})

        if shape_data and shape_data.get("shape"):
            shape = shape_data["shape"]
            # Multiply all dims except batch (first)
            dims = shape[1:]
            if all(isinstance(d, (int, float)) for d in dims):
                product = 1
                for d in dims:
                    product *= int(d)
                return product
            # Symbolic
            return " * ".join(str(d) for d in dims)

        return None
