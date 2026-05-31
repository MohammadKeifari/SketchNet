from .base import BaseTranslator


class OutputTranslator(BaseTranslator):
    node_type = "output"

    def output_vars(self):
        nid = self.node_id()
        return [
            f"data_{nid}_loss",
            f"data_{nid}_prediction",
            f"data_{nid}_evaluation",
        ]

    def init_code(self, writer, is_sequential):
        pass

    def forward_code(self, writer, input_vars):
        train_var = input_vars.get(
            0, list(input_vars.values())[0] if input_vars else "x"
        )
        test_var = input_vars.get(1, train_var)
        loss_var, pred_var, eval_var = self.output_vars()

        writer.line(f"# Output routing")
        writer.line(f"if phase == 'training':")
        writer.indent()
        writer.line(f"{loss_var} = {train_var}")
        writer.dedent()
        writer.line(f"else:  # evaluation")
        writer.indent()
        writer.line(f"{pred_var} = {test_var}")
        writer.line(f"{eval_var} = {test_var}")
        writer.dedent()

        return self.output_vars()

    def validate(self):
        errors, warnings = [], []

        train_connected = False
        test_connected = False

        for port_data in self.node.get("inputPorts", []):
            port_id = port_data["id"]
            subtype = port_data.get("subType", "")
            connected = any(l["to"] == port_id for l in self.g.links)

            if subtype == "train":
                train_connected = connected
            elif subtype == "test":
                test_connected = connected

        if not train_connected and not test_connected:
            warnings.append("Output: no input ports connected")
        elif train_connected and not test_connected:
            warnings.append("Output: only train port connected — no evaluation data")
        elif test_connected and not train_connected:
            warnings.append("Output: only test port connected — no training data")

        return {"errors": errors, "warnings": warnings}
