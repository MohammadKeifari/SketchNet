from .base import BaseTranslator


class NeuronTranslator(BaseTranslator):
    node_type = "neuron"

    def input_features(self):
        # Layer just needs the last dimension of whatever comes in
        return self._resolve_input_features()

    def init_code(self, writer, is_sequential, in_features="in_features"):
        sid = self.node_id()
        in_f = in_features if isinstance(in_features, int) else str(in_features)
        if is_sequential:
            writer.line(f"nn.Linear({in_f}, 1),")
        else:
            writer.line(f"self.{sid} = nn.Linear({in_f}, 1)")

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
