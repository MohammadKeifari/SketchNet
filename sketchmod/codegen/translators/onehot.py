from .base import BaseTranslator


class OneHotEncodeTranslator(BaseTranslator):
    node_type = "onehot"

    def data_code(self, writer, input_vars):
        src_var = list(input_vars.values())[0]
        out_var = self.output_vars()[0]
        num_classes = self.node.get("numClasses", 10)
        writer.line(f"# One-hot encode ({num_classes} classes)")
        writer.line(
            f"{out_var} = torch.nn.functional.one_hot({src_var}.long(), num_classes={num_classes}).float()"
        )
        writer.line("")
        return [out_var]

    def validate(self):
        errors, warnings = [], []
        classes = self.node.get("numClasses", 10)

        if classes < 2:
            errors.append("OneHotEncode: number of classes must be at least 2")

        return {"errors": errors, "warnings": warnings}
