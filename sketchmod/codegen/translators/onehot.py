from .base import BaseTranslator


class OneHotEncodeTranslator(BaseTranslator):
    node_type = "onehot"

    def data_code(self, writer, input_var):
        num_classes = self.node.get("numClasses", 10)
        writer.line(f"# One-hot encode labels ({num_classes} classes)")
        writer.line(
            f"y_train = torch.nn.functional.one_hot(y_train, num_classes={num_classes}).float()"
        )
        writer.line(
            f"y_test = torch.nn.functional.one_hot(y_test, num_classes={num_classes}).float()"
        )
        writer.line("")
        return None
