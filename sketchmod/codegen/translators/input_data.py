from .base import BaseTranslator


class InputDataTranslator(BaseTranslator):
    node_type = "input-data"

    def data_code(self, writer, input_vars):
        var = self.output_vars()[0]
        dataset_name = self.node.get("datasetName")
        data_shape = self.node.get("dataShape")
        dataset_id = self.node.get("datasetId")

        if dataset_id and dataset_name:
            writer.line(f"# Dataset: {dataset_name} (ID: {dataset_id})")
            writer.line("import pandas as pd")
            writer.line(f"df = pd.read_csv('{dataset_name}.csv')  # Update path")
            writer.line(f"{var} = torch.tensor(df.values, dtype=torch.float32)")
        elif data_shape:
            # Generate random data matching the shape if possible
            shape_str = data_shape.strip("()")
            parts = shape_str.split(",")
            dims = []
            for p in parts:
                p = p.strip()
                try:
                    dims.append(int(p))
                except ValueError:
                    dims.append(100)  # fallback for symbolic dimensions
            dims_str = ", ".join(str(d) for d in dims)
            writer.line(f"# Expected shape: {data_shape}")
            writer.line(
                f"{var} = torch.randn({dims_str})  # TODO: Replace with real data"
            )
        else:
            writer.line(
                f"{var} = torch.randn(1000, 784)  # TODO: Replace with real data"
            )

        writer.line("")
        return [var]
