from .base import BaseTranslator


class ColumnSelectTranslator(BaseTranslator):
    node_type = "column-select"

    def data_code(self, writer, input_var):
        columns = self.node.get("selectedColumns", [])
        column_input = self.node.get("columnInput", "")

        if columns:
            cols_str = ", ".join(str(c) for c in columns)
            writer.line(f"# Select columns: [{cols_str}]")
            writer.line(f"X_train = X_train[:, [{cols_str}]]")
            writer.line(f"X_test = X_test[:, [{cols_str}]]")
        elif column_input:
            writer.line(f"# Column selection: {column_input}")
            writer.line(f"# TODO: Apply column selection based on: {column_input}")

        writer.line("")
        return None
