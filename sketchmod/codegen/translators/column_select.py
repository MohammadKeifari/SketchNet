from .base import BaseTranslator


class ColumnSelectTranslator(BaseTranslator):
    node_type = "column-select"

    def data_code(self, writer, input_vars):
        src_var = list(input_vars.values())[0]
        out_var = self.output_vars()[0]
        columns = self.node.get("selectedColumns", [])
        column_input = self.node.get("columnInput", "")

        if columns:
            cols_str = ", ".join(str(c) for c in columns)
            writer.line(f"# Select columns [{cols_str}]")
            writer.line(f"{out_var} = {src_var}[:, [{cols_str}]]")
        elif column_input:
            writer.line(f"# Column selection: {column_input}")
            writer.line(f"{out_var} = {src_var}[:, [{column_input}]]")
        else:
            writer.line(f"# No column selection")
            writer.line(f"{out_var} = {src_var}")
        writer.line("")
        return [out_var]
