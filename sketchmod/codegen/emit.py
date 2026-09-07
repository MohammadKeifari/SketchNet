"""
Renders an execution plan as a PyTorch script.

Every decision was already made in :mod:`ir`, so this module only lays
statements out and manages indentation.
"""

from .ir import Plan
from .writer import CodeWriter


def render(plan: Plan) -> str:
    w = CodeWriter()
    _imports(w, plan)
    _constants(w, plan)
    _types(w, plan)
    _load_data(w, plan)
    _model(w, plan)
    _train(w, plan)
    _evaluate(w, plan)
    _main(w, plan)
    return str(w).rstrip() + "\n"


# ----------------------------------------------------------------------
#  Preamble
# ----------------------------------------------------------------------
def _imports(w: CodeWriter, plan: Plan):
    w.line("import torch")
    w.line("import torch.nn as nn")
    if plan.train:
        w.line("import torch.optim as optim")
        w.line("from torch.utils.data import DataLoader, TensorDataset")
    if plan.needs_pandas:
        w.line("import pandas as pd")
    if plan.needs_pyplot:
        w.line("import matplotlib.pyplot as plt")
    w.line("from typing import NamedTuple")
    w.blank()


def _constants(w: CodeWriter, plan: Plan):
    w.line("DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')")
    for name, value in plan.constants:
        w.line(f"{name} = {value}")
    w.blank()


def _types(w: CodeWriter, plan: Plan):
    w.blank(2)
    with w.block("class Data(NamedTuple):"):
        if plan.data_fields:
            for name, _ in plan.data_fields:
                w.line(f"{name}: torch.Tensor")
        else:
            w.line("pass")

    if plan.output_fields:
        w.blank(2)
        with w.block("class Output(NamedTuple):"):
            for name, _ in plan.output_fields:
                w.line(f"{name}: torch.Tensor")


# ----------------------------------------------------------------------
#  Functions
# ----------------------------------------------------------------------
def _load_data(w: CodeWriter, plan: Plan):
    w.blank(2)
    with w.block("def load_data() -> Data:"):
        w.extend(plan.load_lines)
        if not plan.data_fields:
            w.line("return Data()")
        else:
            w.line("return Data(")
            w.indent()
            for name, value in plan.data_fields:
                w.line(f"{name}={value},")
            w.dedent()
            w.line(")")


def _model(w: CodeWriter, plan: Plan):
    if not plan.forward_lines and not plan.output_fields:
        return

    w.blank(2)
    with w.block("class Model(nn.Module):"):
        with w.block("def __init__(self):"):
            w.line("super().__init__()")
            w.extend(plan.submodules)
        w.blank()

        signature = ", ".join(f"{p}: torch.Tensor" for p in plan.forward_params)
        with w.block(f"def forward(self, {signature}) -> Output:"):
            w.extend(plan.forward_lines)
            w.line("return Output(")
            w.indent()
            for name, expression in plan.output_fields:
                w.line(f"{name}={expression},")
            w.dedent()
            w.line(")")


def _train(w: CodeWriter, plan: Plan):
    train = plan.train
    if train is None:
        w.blank(2)
        w.line(f"# Training skipped: {plan.skip_reason or 'nothing to train'}.")
        return

    w.blank(2)
    with w.block("def train(model: Model, data: Data) -> None:"):
        w.extend(train.setup)
        validation = train.validation
        if validation:
            _validation_split(w, train, validation)

        tensors = ", ".join(train.feature_tensors + [train.labels])
        w.line(
            f"loader = DataLoader(TensorDataset({tensors}), "
            "batch_size=BATCH_SIZE, shuffle=SHUFFLE)"
        )
        if validation and validation.early_stopping:
            w.line("best_metric = float('inf')")
            w.line("stale_epochs = 0")
        w.blank()

        with w.block("for epoch in range(1, EPOCHS + 1):"):
            w.line("model.train()")
            w.line("total_loss = 0.0")
            _batch_loop(w, train)
            w.line(
                "print(f'Epoch {epoch:3d}  "
                "Train Loss: {total_loss / len(loader.dataset):.6f}')"
            )
            if validation:
                _validation_pass(w, train, validation)


def _batch_loop(w: CodeWriter, train):
    loop_vars = ", ".join(train.loop_vars)
    with w.block(f"for {loop_vars}, y in loader:"):
        moved = ", ".join(f"{v}.to(DEVICE)" for v in train.loop_vars)
        w.line(f"{loop_vars}, y = {moved}, y.to(DEVICE)")
        w.line(f"out = model({loop_vars})")
        w.line(f"loss = criterion(out.{train.loss_field}, y)")
        w.line("optimizer.zero_grad()")
        w.line("loss.backward()")
        if train.gradient_clip is not None:
            w.line(
                "torch.nn.utils.clip_grad_norm_"
                f"(model.parameters(), {train.gradient_clip})"
            )
        w.line("optimizer.step()")
        w.line(f"total_loss += loss.item() * {train.loop_vars[0]}.size(0)")
        w.extend(train.body)


def _validation_split(w: CodeWriter, train, validation):
    first = train.feature_tensors[0]
    w.blank()
    w.line(f"val_size = int({first}.size(0) * {validation.split})")
    w.line(f"val_order = torch.randperm({first}.size(0))")
    for name in train.feature_tensors:
        w.line(f"val_{name} = {name}[val_order[:val_size]]")
    w.line(f"val_y = {train.labels}[val_order[:val_size]]")
    for name in train.feature_tensors:
        w.line(f"{name} = {name}[val_order[val_size:]]")
    w.line(f"{train.labels} = {train.labels}[val_order[val_size:]]")
    w.blank()


def _validation_pass(w: CodeWriter, train, validation):
    arguments = ", ".join(
        f"val_{name}.to(DEVICE)" for name in train.feature_tensors
    )
    w.line("model.eval()")
    with w.block("with torch.inference_mode():"):
        w.line(f"val_out = model({arguments})")
        if validation.metric == "accuracy":
            w.line(
                f"val_acc = ({validation.prediction} == "
                "val_y.to(DEVICE)).float().mean().item()"
            )
            w.line("print(f'           Val Accuracy: {val_acc:.4f}')")
            w.line("metric = 1.0 - val_acc")
        else:
            w.line(
                f"val_loss = criterion(val_out.{train.loss_field}, "
                "val_y.to(DEVICE)).item()"
            )
            w.line("print(f'           Val Loss: {val_loss:.6f}')")
            w.line("metric = val_loss")

    if validation.early_stopping:
        with w.block("if metric < best_metric:"):
            w.line("best_metric = metric")
            w.line("stale_epochs = 0")
        with w.block("else:"):
            w.line("stale_epochs += 1")
            with w.block("if stale_epochs >= PATIENCE:"):
                w.line("print('Early stopping.')")
                w.line("break")


def _evaluate(w: CodeWriter, plan: Plan):
    evaluation = plan.evaluation
    if evaluation is None:
        return

    w.blank(2)
    signature = (
        "model: Model, data: Data" if evaluation.uses_model else "data: Data"
    )
    with w.block(f"def evaluate({signature}) -> None:"):
        if evaluation.uses_model:
            w.line("model.eval()")
            with w.block("with torch.inference_mode():"):
                w.line(f"out = model({', '.join(evaluation.call_args)})")
        elif not evaluation.body:
            w.line("pass")
        w.extend(evaluation.body)


def _main(w: CodeWriter, plan: Plan):
    w.blank(2)
    with w.block("if __name__ == '__main__':"):
        w.line("data = load_data()")
        if plan.train:
            w.line("model = Model().to(DEVICE)")
            w.line("train(model, data)")
            w.line("print('Training complete.')")
        if plan.evaluation:
            arguments = "model, data" if plan.evaluation.uses_model else "data"
            w.line(f"evaluate({arguments})")
