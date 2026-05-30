from .base import BaseTranslator


class InputDataTranslator(BaseTranslator):
    node_type = "input-data"

    def data_code(self, writer, input_var):
        dataset_name = self.node.get("datasetName")
        data_shape = self.node.get("dataShape")
        dataset_id = self.node.get("datasetId")

        if dataset_id and dataset_name:
            writer.line(f"# Dataset: {dataset_name} (ID: {dataset_id})")
            writer.line(f"# Shape: {data_shape or 'auto-detect'}")
            writer.line(f"# TODO: Update file path to your dataset location")
            writer.line(f"import pandas as pd")
            writer.line(f"df = pd.read_csv('{dataset_name}.csv')  # Update path")
            writer.line("X = torch.tensor(df.iloc[:, :-1].values, dtype=torch.float32)")
            writer.line("y = torch.tensor(df.iloc[:, -1].values, dtype=torch.long)")
        elif data_shape:
            writer.line(f"# Expected input shape: {data_shape}")
            writer.line("X = torch.randn(1000, 784)  # TODO: Replace with real data")
            writer.line(
                "y = torch.randint(0, 10, (1000,))  # TODO: Replace with real labels"
            )
        else:
            writer.line("# No dataset configured — using placeholder data")
            writer.line("X = torch.randn(1000, 784)  # TODO: Replace with real data")
            writer.line(
                "y = torch.randint(0, 10, (1000,))  # TODO: Replace with real labels"
            )

        writer.line("")
        return "X, y"
