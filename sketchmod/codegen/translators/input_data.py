from .base import BaseTranslator


class InputDataTranslator(BaseTranslator):
    node_type = "input-data"

    def output_vars(self):
        return [f"data_{self.node_id()}"]

    def data_code(self, writer, input_vars):
        var = self.output_vars()[0]
        dataset_name = self.node.get("datasetName")
        data_shape = self.node.get("dataShape")
        dataset_id = self.node.get("datasetId")

        if dataset_id and dataset_name:
            writer.line(f"# Dataset: {dataset_name} (ID: {dataset_id})")
            if data_shape:
                writer.line(f"# Expected shape: {data_shape}")
            writer.line("import pandas as pd")
            writer.line(f"df = pd.read_csv('{dataset_name}.csv')  # Update path")
            writer.line(f"{var} = torch.tensor(df.values, dtype=torch.float32)")
        elif data_shape:
            writer.line(f"# Expected shape: {data_shape}")
            writer.line(
                f"{var} = torch.randn(1000, 784)  # TODO: Replace with real data"
            )
        else:
            writer.line(
                f"{var} = torch.randn(1000, 784)  # TODO: Replace with real data"
            )

        writer.line("")
        return [var]
