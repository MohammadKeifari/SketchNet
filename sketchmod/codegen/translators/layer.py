from .base import BaseTranslator


class LayerTranslator(BaseTranslator):
    node_type = "layer"

    def init_code(self, writer, is_sequential):
        sid = self.safe_id()
        neurons = self.node.get("numNeurons", 64)
        if is_sequential:
            writer.line(f"nn.Linear(in_features, {neurons}),")
        else:
            writer.line(f"self.{sid} = nn.Linear(in_features, {neurons})")

    def forward_code(self, writer, input_var, skip_vars):
        sid = self.safe_id()
        out = f"x_{sid}"
        writer.line(f"{out} = self.{sid}({input_var})")
        act = self.node.get("activation", "relu")
        if act and act != "linear":
            fn = {"relu": "relu", "sigmoid": "sigmoid", "tanh": "tanh"}.get(act, act)
            writer.line(f"{out} = torch.{fn}({out})")
        return out
