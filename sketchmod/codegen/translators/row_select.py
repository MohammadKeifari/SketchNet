from .base import BaseTranslator


class RowSelectTranslator(BaseTranslator):
    node_type = "row-select"

    def data_code(self, writer, input_var):
        method = self.node.get("method", "first-n")
        value = self.node.get("value", "100")
        seed = self.node.get("randomSeed", 42)

        if method == "first-n":
            n = int(value) if value.isdigit() else 100
            writer.line(f"# Select first {n} rows")
            writer.line(f"X_train = X_train[:{n}]")
            writer.line(f"y_train = y_train[:{n}]")
        elif method == "random":
            n = int(value) if value.isdigit() else 100
            writer.line(f"# Random sample of {n} rows")
            writer.line(f"torch.manual_seed({seed})")
            writer.line(f"idx = torch.randperm(len(X_train))[:{n}]")
            writer.line("X_train = X_train[idx]")
            writer.line("y_train = y_train[idx]")
        elif method == "slice":
            writer.line(f"# Slice rows: {value}")
            writer.line(f"# TODO: Apply slice: {value}")
        elif method == "indices":
            writer.line(f"# Select specific indices: {value}")
            writer.line(f"# TODO: Apply index selection: {value}")

        writer.line("")
        return None
