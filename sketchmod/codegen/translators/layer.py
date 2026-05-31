from .base import BaseTranslator


class LayerTranslator(BaseTranslator):
    node_type = "layer"

    def input_features(self):
        # Layer just needs the last dimension of whatever comes in
        return self._resolve_input_features()

    def init_code(self, writer, is_sequential, in_features):
        sid = self.node_id()
        neurons = self.node.get("numNeurons", 64)

        if isinstance(in_features, list):
            self._generate_multi_input_init(writer, sid, neurons)
        elif is_sequential:
            writer.line(f"nn.Linear({in_features}, {neurons}),")
        else:
            writer.line(f"self.{sid} = nn.Linear({in_features}, {neurons})")

    def forward_code(self, writer, input_vars, skip_vars):
        sid = self.node_id()
        out_var = f"data_{sid}"

        if len(input_vars) > 1:
            self._generate_multi_input_forward(writer, input_vars, sid, out_var)
        else:
            src_var = list(input_vars.values())[0]
            writer.line(f"{out_var} = self.{sid}({src_var})")

        act = self.node.get("activation", "relu")
        if act and act != "linear":
            fn = {"relu": "relu", "sigmoid": "sigmoid", "tanh": "tanh"}.get(act, act)
            writer.line(f"{out_var} = torch.{fn}({out_var})")

        return [out_var]
