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

    def forward_code(self, writer, input_vars, skip_vars):
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
