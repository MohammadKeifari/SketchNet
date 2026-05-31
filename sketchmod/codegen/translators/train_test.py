from .base import BaseTranslator


class TrainTestSplitTranslator(BaseTranslator):
    node_type = "train-test"

    def output_vars(self):
        nid = self.node_id()
        return [f"data_{nid}_train", f"data_{nid}_test"]

    def data_code(self, writer, input_vars):
        src_var = list(input_vars.values())[0]
        ratio = self.node.get("trainRatio", 0.7)
        seed = self.node.get("randomSeed", 42)
        train_var, test_var = self.output_vars()
        train_pct = int(ratio * 100)

        writer.line(f"# Train/test split: {train_pct}% / {100 - train_pct}%")
        writer.line(f"torch.manual_seed({seed})")
        writer.line(f"indices = torch.randperm(len({src_var}))")
        writer.line(f"split_idx = int(len({src_var}) * {ratio})")
        writer.line(f"{train_var} = {src_var}[indices[:split_idx]]")
        writer.line(f"{test_var} = {src_var}[indices[split_idx:]]")
        writer.line("")
        return [train_var, test_var]

    def validate(self):
        errors, warnings = [], []
        ratio = self.node.get("trainRatio", 0.7)

        if ratio <= 0 or ratio >= 1:
            errors.append("TrainTestSplit: train ratio must be between 0 and 1")

        return {"errors": errors, "warnings": warnings}
