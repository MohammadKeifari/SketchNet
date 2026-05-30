from .base import BaseTranslator


class LayerTranslator(BaseTranslator):
    node_type = "layer"

    def init_code(self, writer, is_sequential):
        sid = self.node_id()
        neurons = self.node.get("numNeurons", 64)
        if is_sequential:
            writer.line(f"nn.Linear(in_features, {neurons}),")
        else:
            writer.line(f"self.{sid} = nn.Linear(in_features, {neurons})")

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
