from .base import BaseTranslator


class Conv2DTranslator(BaseTranslator):
    node_type = "conv2d"

    def init_code(self, writer, is_sequential, in_features="in_channels"):
        sid = self.node_id()
        f = self.node.get("filters", 32)
        k = self.node.get("kernelSize", 3)
        s = self.node.get("stride", 1)
        p = self.node.get("padding", 0)
        in_f = in_features if isinstance(in_features, int) else str(in_features)
        line = f"nn.Conv2d({in_f}, {f}, kernel_size={k}, stride={s}, padding={p})"
        if is_sequential:
            writer.line(line + ",")
        else:
            writer.line(f"self.{sid} = {line}")

    def input_features(self):
        # Conv2D expects (B, H, W, C) or (B, C, H, W)
        # The input channels depend on the data format
        incoming = self.g._links_to(self.node["id"])
        if not incoming:
            return None

        src_port_id = incoming[0]["from"]
        src_port = self.g._port_map.get(src_port_id, {})
        shape_data = src_port.get("shape", {})

        if shape_data and shape_data.get("shape"):
            shape = shape_data["shape"]
            if len(shape) == 4:
                # Assume channels-last: (B, H, W, C)
                last_dim = shape[-1]
                if isinstance(last_dim, (int, float)):
                    return int(last_dim)
                return str(last_dim)

        return None

    def forward_code(self, writer, input_vars):
        src_var = list(input_vars.values())[0]
        sid = self.node_id()
        out_var = self.output_vars()[0]
        writer.line(f"{out_var} = self.{sid}({src_var})")
        act = self.node.get("activation", "relu")
        if act and act != "linear":
            fn = {"relu": "relu", "sigmoid": "sigmoid", "tanh": "tanh"}.get(act, act)
            writer.line(f"{out_var} = torch.{fn}({out_var})")
        return [out_var]
