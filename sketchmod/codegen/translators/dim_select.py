from .base import BaseTranslator


class DimSelectTranslator(BaseTranslator):
    node_type = "dim-select"

    def data_code(self, writer, input_var):
        dims = self.node.get("dimSelections", [])
        if not dims:
            return None

        # Build slicing for each dimension
        slices = []
        for d in dims:
            if not d or d.strip() == "" or d.strip() == ":":
                slices.append(":")
            else:
                slices.append(d.strip())

        # If first dim is sliced, it applies to the batch dimension
        if slices and slices[0] != ":":
            batch_slice = slices[0]
            other_slices = ", ".join(slices[1:]) if len(slices) > 1 else ""
            writer.line(
                f"# Dimension selection: batch[{batch_slice}], dims[{other_slices}]"
                if other_slices
                else f"# Batch slicing: [{batch_slice}]"
            )
            writer.line(f"X_train = X_train[{batch_slice}]")
            writer.line(f"X_test = X_test[{batch_slice}]")
            if other_slices:
                writer.line(f"X_train = X_train[:, {other_slices}]")
                writer.line(f"X_test = X_test[:, {other_slices}]")
        else:
            slice_str = ", ".join(slices)
            writer.line(f"# Dimension selection: [{slice_str}]")
            writer.line(f"X_train = X_train[:, {slice_str}]")
            writer.line(f"X_test = X_test[:, {slice_str}]")

        writer.line("")
        return None
