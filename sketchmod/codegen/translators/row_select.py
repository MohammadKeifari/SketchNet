from .base import BaseTranslator


class RowSelectTranslator(BaseTranslator):
    node_type = "row-select"

    def data_code(self, writer, input_vars):
        src_var = list(input_vars.values())[0]
        out_var = self.output_vars()[0]
        method = self.node.get("method", "first-n")
        value = self.node.get("value", "100")
        seed = self.node.get("randomSeed", 42)

        if method == "first-n":
            n = int(value) if str(value).isdigit() else 100
            writer.line(f"# Select first {n} rows")
            writer.line(f"{out_var} = {src_var}[:{n}]")
        elif method == "random":
            n = int(value) if str(value).isdigit() else 100
            writer.line(f"# Random sample of {n} rows")
            writer.line(f"torch.manual_seed({seed})")
            writer.line(f"idx_{self.node_id()} = torch.randperm(len({src_var}))[:{n}]")
            writer.line(f"{out_var} = {src_var}[idx_{self.node_id()}]")
        elif method == "slice":
            writer.line(f"# Slice rows: {value}")
            writer.line(f"parts = [{value}]")
            writer.line(f"{out_var} = {src_var}[{value}]")
        elif method == "indices":
            writer.line(f"# Select indices: {value}")
            writer.line(f"idx_{self.node_id()} = torch.tensor([{value}])")
            writer.line(f"{out_var} = {src_var}[idx_{self.node_id()}]")
        writer.line("")
        return [out_var]
