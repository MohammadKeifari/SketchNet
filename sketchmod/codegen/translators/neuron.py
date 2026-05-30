from .base import BaseTranslator


class NeuronTranslator(BaseTranslator):
    node_type = "neuron"

    def init_code(self, writer, is_sequential):
        sid = self.safe_id()
        if is_sequential:
            writer.line("nn.Linear(in_features, 1),")
        else:
            writer.line(f"self.{sid} = nn.Linear(in_features, 1)")

    def forward_code(self, writer, input_var, skip_vars):
        sid = self.safe_id()
        out = f"x_{sid}"
        writer.line(f"{out} = self.{sid}({input_var})")
        act = self.node.get("activation", "relu")
        if act and act != "linear":
            fn = {"relu": "relu", "sigmoid": "sigmoid", "tanh": "tanh"}.get(act, act)
            writer.line(f"{out} = torch.{fn}({out})")
        return out
