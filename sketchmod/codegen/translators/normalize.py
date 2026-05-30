from .base import BaseTranslator


class NormalizeTranslator(BaseTranslator):
    node_type = "normalize"

    def data_code(self, writer, input_vars):
        src_var = list(input_vars.values())[0]
        out_var = self.output_vars()[0]
        method = self.node.get("method", "standard")

        if method == "standard":
            writer.line(f"# Standard normalization")
            writer.line(f"mean_{self.node_id()} = {src_var}.mean(dim=0, keepdim=True)")
            writer.line(
                f"std_{self.node_id()} = {src_var}.std(dim=0, keepdim=True) + 1e-8"
            )
            writer.line(
                f"{out_var} = ({src_var} - mean_{self.node_id()}) / std_{self.node_id()}"
            )
        else:
            writer.line(f"# Min-Max normalization")
            writer.line(
                f"min_{self.node_id()} = {src_var}.min(dim=0, keepdim=True).values"
            )
            writer.line(
                f"max_{self.node_id()} = {src_var}.max(dim=0, keepdim=True).values"
            )
            writer.line(
                f"{out_var} = ({src_var} - min_{self.node_id()}) / (max_{self.node_id()} - min_{self.node_id()} + 1e-8)"
            )
        writer.line("")
        return [out_var]
