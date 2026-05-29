class DataGenerator:
    """Generates the data loading function."""

    def __init__(self, generator):
        self.g = generator

    def generate(self):
        ordered = self.g.topological_order()
        preprocessing = [
            n
            for n in ordered
            if n["type"]
            not in (
                "layer",
                "neuron",
                "conv2d",
                "flatten",
                "dropout",
                "batchnorm",
                "add",
                "concat",
                "output",
            )
        ]

        optimizer = next((n for n in self.g.nodes if n["type"] == "optimizer"), None)
        batch_size = optimizer.get("batchSize", 32) if optimizer else 32
        shuffle = optimizer.get("shuffle", True) if optimizer else True

        input_node = next((n for n in preprocessing if n["type"] == "input-data"), None)
        split_node = next((n for n in preprocessing if n["type"] == "train-test"), None)
        norm_node = next((n for n in preprocessing if n["type"] == "normalize"), None)

        lines = []
        lines.append("def load_data():")
        lines.append('    """Load and preprocess data."""')

        if input_node and input_node.get("datasetName"):
            lines.append(f"    # Dataset: {input_node['datasetName']}")
            lines.append(f"    # Shape: {input_node.get('dataShape', 'unknown')}")

        lines.append("    # TODO: Replace with actual dataset loading")
        lines.append("    X = torch.randn(1000, 784)  # features")
        lines.append("    y = torch.randint(0, 10, (1000,))  # labels")
        lines.append("")

        if split_node:
            train_ratio = split_node.get("trainRatio", 0.7)
            seed = split_node.get("randomSeed", 42)
            lines.append(
                f"    # Train/test split: {int(train_ratio * 100)}/{int((1 - train_ratio) * 100)}"
            )
            lines.append(f"    torch.manual_seed({seed})")
            lines.append(f"    indices = torch.randperm(len(X))")
            lines.append(f"    split_idx = int(len(X) * {train_ratio})")
            lines.append(
                "    train_idx, test_idx = indices[:split_idx], indices[split_idx:]"
            )
            lines.append("    X_train, y_train = X[train_idx], y[train_idx]")
            lines.append("    X_test, y_test = X[test_idx], y[test_idx]")
        else:
            lines.append("    X_train, y_train = X, y")
            lines.append("    X_test, y_test = X[:100], y[:100]")

        lines.append("")

        if norm_node:
            method = norm_node.get("method", "standard")
            if method == "standard":
                lines.append("    # Standard normalization")
                lines.append("    mean = X_train.mean(dim=0, keepdim=True)")
                lines.append("    std = X_train.std(dim=0, keepdim=True) + 1e-8")
                lines.append("    X_train = (X_train - mean) / std")
                lines.append("    X_test = (X_test - mean) / std")
            else:
                lines.append("    # Min-Max normalization")
                lines.append("    x_min = X_train.min(dim=0, keepdim=True).values")
                lines.append("    x_max = X_train.max(dim=0, keepdim=True).values")
                lines.append("    X_train = (X_train - x_min) / (x_max - x_min + 1e-8)")
                lines.append("    X_test = (X_test - x_min) / (x_max - x_min + 1e-8)")
            lines.append("")

        lines.append(f"    train_dataset = TensorDataset(X_train, y_train)")
        lines.append(f"    test_dataset = TensorDataset(X_test, y_test)")
        lines.append(
            f"    train_loader = DataLoader(train_dataset, batch_size={batch_size}, shuffle={shuffle})"
        )
        lines.append(
            f"    test_loader = DataLoader(test_dataset, batch_size={batch_size}, shuffle=False)"
        )
        lines.append("    return train_loader, test_loader")

        return lines
