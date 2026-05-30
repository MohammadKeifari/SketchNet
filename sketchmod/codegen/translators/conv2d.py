from .base import BaseTranslator


class Conv2DTranslator(BaseTranslator):
    node_type = "conv2d"

    def init_code(self, writer, is_sequential):
        sid = self.node_id()
        f = self.node.get("filters", 32)
        k = self.node.get("kernelSize", 3)
        s = self.node.get("stride", 1)
        p = self.node.get("padding", 0)
        line = f"nn.Conv2d(in_channels, {f}, kernel_size={k}, stride={s}, padding={p})"
        if is_sequential:
            writer.line(line + ",")
        else:
            writer.line(f"self.{sid} = {line}")

    def forward_code(self, writer, input_vars, skip_vars):
        src_var = list(input_vars.values())[0]
        sid = self.node_id()
        out_var = self.output_vars()[0]
        writer.line(f"{out_var} = self.{sid}({src_var})")
        act = self.node.get("activation", "relu")
        if act and act != "linear":
            fn = {"relu": "relu", "sigmoid": "sigmoid", "tanh": "tanh"}.get(act, act)
            writer.line(f"{out_var} = torch.{fn}({out_var})")
        return [out_var]
