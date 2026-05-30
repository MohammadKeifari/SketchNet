from .base import BaseTranslator


class TrainTestSplitTranslator(BaseTranslator):
    node_type = "train-test"

    def data_code(self, writer, input_var):
        ratio = self.node.get("trainRatio", 0.7)
        seed = self.node.get("randomSeed", 42)
        train_pct = int(ratio * 100)
        test_pct = 100 - train_pct

        writer.line(f"# Train/test split: {train_pct}% / {test_pct}%")
        writer.line(f"torch.manual_seed({seed})")
        writer.line("indices = torch.randperm(len(data))")
        writer.line(f"split_idx = int(len(data) * {ratio})")
        writer.line("data_train = data[indices[:split_idx]]")
        writer.line("data_test = data[indices[split_idx:]]")
        writer.line("")
        return None
