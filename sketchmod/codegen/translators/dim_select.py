from .base import BaseTranslator


class DimSelectTranslator(BaseTranslator):
    node_type = "dim-select"

    def data_code(self, writer, input_vars):
        src_var = list(input_vars.values())[0]
        out_var = self.output_vars()[0]
        dims = self.node.get("dimSelections", [])

        if not dims:
            writer.line(f"{out_var} = {src_var}")
            writer.line("")
            return [out_var]

        slices = []
        for d in dims:
            if not d or d.strip() in ("", ":"):
                slices.append(":")
            else:
                slices.append(d.strip())

        if slices and slices[0] != ":":
            batch_slice = slices[0]
            other = ", ".join(slices[1:]) if len(slices) > 1 else ""
            writer.line(
                f"# Dim selection: batch[{batch_slice}]"
                + (f", dims[{other}]" if other else "")
            )
            writer.line(f"{out_var} = {src_var}[{batch_slice}]")
            if other:
                writer.line(f"{out_var} = {out_var}[:, {other}]")
        else:
            slice_str = ", ".join(slices)
            writer.line(f"# Dim selection: [{slice_str}]")
            writer.line(f"{out_var} = {src_var}[:, {slice_str}]")
        writer.line("")
        return [out_var]
