from .base import BaseTranslator


class NormalizeTranslator(BaseTranslator):
    node_type = "normalize"

    def data_code(self, writer, input_var):
        method = self.node.get("method", "standard")

        if method == "standard":
            writer.line("# Z-score normalization (fit on train, apply to test)")
            writer.line("mean = X_train.mean(dim=0, keepdim=True)")
            writer.line("std = X_train.std(dim=0, keepdim=True) + 1e-8")
            writer.line("X_train = (X_train - mean) / std")
            writer.line("X_test = (X_test - mean) / std")
        else:
            writer.line("# Min-Max normalization (fit on train, apply to test)")
            writer.line("x_min = X_train.min(dim=0, keepdim=True).values")
            writer.line("x_max = X_train.max(dim=0, keepdim=True).values")
            writer.line("X_train = (X_train - x_min) / (x_max - x_min + 1e-8)")
            writer.line("X_test = (X_test - x_min) / (x_max - x_min + 1e-8)")

        writer.line("")
        return None
