from .base import BaseTranslator


class NeuronTranslator(BaseTranslator):
    node_type = "neuron"

    def init_code(self, writer, is_sequential):
        sid = self.node_id()
        if is_sequential:
            writer.line("nn.Linear(in_features, 1),")
        else:
            writer.line(f"self.{sid} = nn.Linear(in_features, 1)")

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
