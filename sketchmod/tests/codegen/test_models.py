"""
SketchNet Model Test Runner
============================
Runs exported PyTorch models generated from JSON graph files.

Usage:
  # Interactive mode – windows appear for visual inspection
  python test_models.py --mode by_hand --models 1
  python test_models.py --mode by_hand              # run all interactively

  # Automatic headless testing (for CI)
  python test_models.py --mode auto
  python test_models.py --mode auto --models 1,2

  # Dump generated code to examples/ folder
  python test_models.py --mode auto --models 1 --dump-code

  # clear-cache

Place model JSON files in `examples/` and datasets in `examples/data/`.

The checks below are behavioural: they assert what the generated script does
(which port feeds the loss, whether the model converges, which diagnostics the
validator raises) rather than how the emitter happens to format it.  Accuracy,
loss and epoch thresholds are the contract and should not be relaxed.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# Find project root (the directory containing sketchmod/)
_current_file = Path(__file__).resolve()
_project_root = _current_file.parent
while not (_project_root / "sketchmod").is_dir():
    _project_root = _project_root.parent
sys.path.insert(0, str(_project_root))

from sketchmod.codegen.generator import CodeGenerator
from sketchmod.codegen.phase_analyzer import analyze_phases
from sketchmod.codegen.graph import parse_graph

EXAMPLES_DIR = Path(__file__).resolve().parent / "examples"
DATA_DIR = EXAMPLES_DIR / "data"


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def generate_code(model_json: dict) -> str:
    """Generate PyTorch code from the test graph fixture."""
    return CodeGenerator(model_json).generate()


def run_generated_code(
    code: str, timeout: int = 120, interactive: bool = False
) -> subprocess.CompletedProcess:
    # Force CPU before any torch import
    """Execute generated code in an isolated namespace."""
    code = "import os\n" "os.environ['CUDA_VISIBLE_DEVICES'] = ''\n" + code

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        tmp_path = f.name

    env = os.environ.copy()
    if not interactive:
        env["MPLBACKEND"] = "Agg"
    env["PYTHONUNBUFFERED"] = "1"

    try:
        proc = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=EXAMPLES_DIR,
            env=env,
        )
    finally:
        os.unlink(tmp_path)
    return proc


# Constructs the old dictionary-based generator emitted.  None of them should
# come back: every dataflow decision is now resolved at generation time.
LEGACY_PATTERNS = (
    "inputs_dict",
    "outputs.get(",
    "outputs[",
    "if tmp is not None",
    "in dir()",
    ".dim() ==",
)


def static_check(code: str) -> bool:
    """Checks every generated script must satisfy, whatever the graph."""
    found = [p for p in LEGACY_PATTERNS if p in code]
    if found:
        print(f"❌ Generated code fell back to runtime dataflow: {found}")
        return False
    return True


def default_check(proc, code, graph):
    """Basic checks that apply to every model."""
    ok = True
    if proc.returncode != 0:
        print("❌ Model crashed (non‑zero exit code)")
        ok = False

    # Only check for 'Training complete.' if the graph actually has an optimizer
    parsed = parse_graph(graph)
    flow = analyze_phases(parsed)
    has_optimizer = flow.get("optimizer") is not None

    if has_optimizer and "Training complete." not in proc.stdout:
        print("❌ Missing 'Training complete.'")
        ok = False

    if proc.stderr.strip():
        if "Traceback" in proc.stderr:
            print("❌ Traceback in stderr")
            ok = False
        else:
            print("⚠️  stderr output (likely harmless warnings):")
            print(proc.stderr.strip()[:500])

    return static_check(code) and ok


def clear_project_cache():
    """Delete all __pycache__ directories under the project root."""
    root = _project_root
    deleted = 0
    for dirpath, dirnames, _ in os.walk(root):
        if "__pycache__" in dirnames:
            pycache = Path(dirpath) / "__pycache__"
            try:
                for f in pycache.iterdir():
                    f.unlink()
                pycache.rmdir()
                deleted += 1
            except Exception:
                pass
    if deleted:
        print(f"🧹 Cleared {deleted} __pycache__ directories.")


# ----------------------------------------------------------------------
# Assertion helpers
# ----------------------------------------------------------------------


def check(label: str, condition, detail: str = "") -> bool:
    """Print one named check and return whether it held."""
    passed = bool(condition)
    suffix = f" - {detail}" if detail else ""
    print(f"{'✅' if passed else '❌'} {label}{suffix}")
    return passed


def section(code: str, header: str) -> str:
    """The body of one top-level ``def``/``class`` in the generated script."""
    lines = code.splitlines()
    start = next((i for i, l in enumerate(lines) if l.startswith(header)), None)
    if start is None:
        return ""
    body = []
    for line in lines[start + 1 :]:
        if line and not line.startswith(" "):
            break
        body.append(line)
    return "\n".join(body)


def output_roles(code: str) -> dict:
    """Maps each Output field to the expression ``forward`` returns for it."""
    match = re.search(r"return Output\(\n(.*?)\n\s*\)", code, re.S)
    if not match:
        return {}
    roles = {}
    for line in match.group(1).splitlines():
        name, _, expression = line.strip().rstrip(",").partition("=")
        if name.strip():
            roles[name.strip()] = expression.strip()
    return roles


def figure_titles(code: str) -> list:
    return re.findall(r"plt\.title\('([^']*)'\)", code)


def mentions(code: str, identifier: str) -> bool:
    return re.search(rf"\b{re.escape(identifier)}\b", code) is not None


def diagnostics(graph: dict) -> dict:
    from sketchmod.codegen.validator import GraphValidator

    return GraphValidator(graph).validate()


def error_codes(graph: dict) -> set:
    return {e.get("code") for e in diagnostics(graph)["errors"]}


def warning_codes(graph: dict) -> set:
    return {w.get("code") for w in diagnostics(graph)["warnings"]}


def train_losses(proc) -> list:
    return [float(v) for v in re.findall(r"Train Loss: ([0-9.eE+-]+)", proc.stdout)]


def final_accuracy(proc):
    match = re.search(r"Accuracy: ([0-9.]+)", proc.stdout)
    return float(match.group(1)) if match else None


def last_epoch(proc):
    epochs = re.findall(r"Epoch\s+(\d+)", proc.stdout)
    return int(epochs[-1]) if epochs else None


def loss_trend(proc) -> str:
    losses = train_losses(proc)
    return f"{losses[0]} → {losses[-1]}" if losses else "no loss output"


def converged(proc, threshold: float) -> bool:
    losses = train_losses(proc)
    return bool(losses) and losses[-1] < threshold


def loss_decreased(proc) -> bool:
    losses = train_losses(proc)
    return len(losses) >= 2 and losses[-1] < losses[0]


def accurate_to(proc, threshold: float) -> bool:
    accuracy = final_accuracy(proc)
    return accuracy is not None and accuracy > threshold


def linear_layers(code: str) -> list:
    """(in_features, out_features) of every nn.Linear the model builds."""
    return [
        (int(a), int(b)) for a, b in re.findall(r"nn\.Linear\((\d+),\s*(\d+)", code)
    ]


# ----------------------------------------------------------------------
# Model‑specific checks
# ----------------------------------------------------------------------


def check_model1(proc, code, graph):
    """Output port roles, OneHot→DeOneHot parameter sharing, phase partition."""
    roles = output_roles(code)
    flow = analyze_phases(parse_graph(graph))

    return all(
        [
            check("Loss port carries raw logits", roles.get("loss", "").isidentifier()),
            check(
                "Prediction port applies argmax",
                roles.get("prediction", "").startswith("torch.argmax("),
            ),
            check(
                "Evaluation port applies softmax",
                roles.get("evaluation", "").startswith("torch.softmax("),
            ),
            check(
                "DeOneHot reuses the OneHot categories",
                "torch.arange" not in code,
                "no category tensor is rebuilt",
            ),
            check("OneHot o8 is preprocessing", "o8" in flow["preprocessing_set"]),
            check("Layer l9 trains and evaluates", "l9" in flow["train_set"]
                  and "l9" in flow["eval_set"]),
            check("Visualization v12 stays out of training",
                  "v12" not in flow["train_set"]),
            check("DeOneHot d23 stays out of training", "d23" not in flow["train_set"]),
        ]
    )


def check_model2(proc, code, graph):
    """Both evaluation visualizations are drawn, exactly once each."""
    titles = figure_titles(code)
    return all(
        [
            check("Both visualizations emitted", {"v12", "v1"} <= set(titles), str(titles)),
            check("Two figures shown", code.count("plt.show()") == 2),
        ]
    )


def check_model3(proc, code, graph):
    """Partially-connected nodes are dropped; fully-connected ones survive."""
    titles = figure_titles(code)
    return all(
        [
            check("Print p7 absent (no activation phase)", not mentions(code, "p7")),
            check("Accuracy a6 absent (input lacks evaluation)", not mentions(code, "a6")),
            check("Visualization v1 absent (color lacks evaluation)", "v1" not in titles),
            check("Visualization v12 present", "v12" in titles),
            check("DeOneHot d23 present", mentions(code, "d23")),
        ]
    )


def check_model4(proc, code, graph):
    """Prints, DeOneHot on a softmax port, accuracy wiring, both plots."""
    titles = figure_titles(code)
    train_body = section(code, "def train(")
    deonehot = re.search(r"d23 = torch\.argmax\((out\.\w+), dim=-1\)", code)

    return all(
        [
            check("Loss print runs inside the training loop", "print(" in train_body),
            check(
                "DeOneHot reads the softmax evaluation port",
                deonehot and deonehot.group(1) == "out.evaluation",
                deonehot.group(1) if deonehot else "no DeOneHot",
            ),
            check("Confusion matrix requested", "confusion_matrix" in code),
            check(
                "Accuracy compares the prediction role port",
                "a6_predicted = out.prediction" in code,
            ),
            check("Accuracy labels come from c5", "a6_actual = data.c5" in code),
            check("Both visualizations emitted", {"v12", "v1"} <= set(titles)),
        ]
    )


def check_model5(proc, code, graph):
    """Three chained splits, a trained model, and a clean visualization."""
    load_body = section(code, "def load_data()")
    return all(
        [
            check(
                "All three Train/Test splits emitted",
                all(f"{s}_train" in load_body for s in ("t1", "t2", "t3")),
            ),
            check("Training loop present", "class Model" in code and "def train(" in code),
            check(
                "Evaluation draws v1",
                "def evaluate(" in code and "v1" in figure_titles(code),
            ),
            check(
                "No visualization shape warnings",
                "visualization-sample-mismatch" not in warning_codes(graph),
            ),
        ]
    )


def check_model6(proc, code, graph):
    """Dropout/Add/Concat topology, per-phase plots, convergence below 0.1."""
    return all(
        [
            check("Dropout present", "nn.Dropout" in code),
            check("Add merge present", re.search(r"= \w+ \+ \w+$", code, re.M)),
            check("Concat merge present", "torch.cat(" in code),
            check("viz_pre drawn during preprocessing",
                  "viz_pre" in figure_titles(section(code, "def load_data()"))),
            check("viz_eval drawn during evaluation",
                  "viz_eval" in figure_titles(section(code, "def evaluate("))),
            check(
                "Training visualization is reported and skipped",
                "visualization-in-training" in warning_codes(graph)
                and "viz_train" not in figure_titles(code),
            ),
            check("Converged below 0.1", converged(proc, 0.1), loss_trend(proc)),
        ]
    )


def check_model7(proc, code, graph):
    """RowSelect, BatchNorm, LeakyReLU, CrossEntropy, accuracy above 0.8."""
    roles = output_roles(code)
    return all(
        [
            check("RowSelect present", mentions(code, "row_sel")),
            check("BatchNorm present", "nn.BatchNorm" in code),
            check("LeakyReLU activation used", "leaky_relu" in code),
            check("CrossEntropyLoss configured", "nn.CrossEntropyLoss()" in code),
            check(
                "Prediction and evaluation ports apply argmax",
                all(
                    roles.get(r, "").startswith("torch.argmax(")
                    for r in ("prediction", "evaluation")
                ),
            ),
            check("Accuracy above 0.8", accurate_to(proc, 0.8), str(final_accuracy(proc))),
            check("Discrete colour mapping present", "ListedColormap" in code),
        ]
    )


def check_model8(proc, code, graph):
    """Conv2D → Reshape → Flatten pipeline reaching accuracy above 0.7."""
    return all(
        [
            check("Conv2D present", "nn.Conv2d" in code),
            check("Reshape present", ".reshape(" in code),
            check("Flatten present", "nn.Flatten" in code),
            check("Accuracy above 0.7", accurate_to(proc, 0.7), str(final_accuracy(proc))),
        ]
    )


def check_model9(proc, code, graph):
    """Extra optimizers are reported and ignored; training still runs."""
    return all(
        [
            check("Multiple optimizers reported", "multiple-optimizers" in warning_codes(graph)),
            check("Exactly one optimizer built", code.count("optimizer = optim.") == 1),
            check("Training completed", "Training complete." in proc.stdout),
        ]
    )


def check_model10(proc, code, graph):
    """Evaluation entering the model elsewhere is reported and skipped."""
    return all(
        [
            check(
                "Evaluation entry mismatch reported",
                "evaluation-entry-mismatch" in warning_codes(graph),
            ),
            check("No evaluation function generated", "def evaluate(" not in code),
            check(
                "Script exited cleanly",
                proc.returncode == 0 and "Training complete." in proc.stdout,
            ),
        ]
    )


def check_model11(proc, code, graph):
    """Straightforward regression that must converge below 0.05."""
    return all(
        [
            check("Training completed", "Training complete." in proc.stdout),
            check("Converged below 0.05", converged(proc, 0.05), loss_trend(proc)),
        ]
    )


def check_model12(proc, code, graph):
    """Branched network with an Add merge, prints in all three phases."""
    load_body = section(code, "def load_data()")
    train_body = section(code, "def train(")
    eval_body = section(code, "def evaluate(")

    return all(
        [
            check("Add merge present", re.search(r"= \w+ \+ \w+$", code, re.M)),
            check("viz_pre drawn during preprocessing", "viz_pre" in figure_titles(load_body)),
            check("viz_eval drawn during evaluation", "viz_eval" in figure_titles(eval_body)),
            check("Preprocessing print present", "pre_data_shape" in load_body),
            check("Training print present", "train_loss_tensor" in train_body),
            check("Evaluation print present", "predictions" in eval_body),
            check("Converged below 0.5", converged(proc, 0.5), loss_trend(proc)),
        ]
    )


def check_model13(proc, code, graph):
    """A cycle, an unconnected layer input and an impossible reshape."""
    errors, warnings = error_codes(graph), warning_codes(graph)
    return all(
        [
            check("Graph rejected", not diagnostics(graph)["isValid"]),
            check("Data-flow cycle reported", "data-flow-cycle" in errors),
            check("Unconnected layer input reported", "missing-input-connection" in errors),
            check("Impossible reshape reported", "reshape-infeasible" in warnings),
        ]
    )


def check_model14(proc, code, graph):
    """A symbolic reshape dimension resolves statically, without warnings."""
    reshape = re.search(r"\.reshape\((.+)\)\s*$", code, re.M)
    arguments = [a.strip() for a in reshape.group(1).split(",")] if reshape else []
    resolved = all(
        a == "-1" or a.lstrip("-").isdigit() or ".size(" in a for a in arguments
    )
    return all(
        [
            check("Reshape emitted", bool(reshape), reshape.group(0) if reshape else "none"),
            check("Symbolic dimension resolved statically", resolved, str(arguments)),
            check("One inferred dimension", arguments.count("-1") == 1),
            check("No reshape feasibility warning",
                  "reshape-infeasible" not in warning_codes(graph)),
        ]
    )


def check_model15(proc, code, graph):
    """Shared-parameter ports that depend on each other cannot be ordered."""
    return all(
        [
            check("Graph rejected", not diagnostics(graph)["isValid"]),
            check("Param-port cycle reported", "param-cycle" in error_codes(graph)),
        ]
    )


def check_model16(proc, code, graph):
    """A data-flow cycle makes the graph untranslatable."""
    return all(
        [
            check("Graph rejected", not diagnostics(graph)["isValid"]),
            check("Data-flow cycle reported", "data-flow-cycle" in error_codes(graph)),
        ]
    )


def check_model17(proc, code, graph):
    """A param-port cycle makes the graph untranslatable."""
    return all(
        [
            check("Graph rejected", not diagnostics(graph)["isValid"]),
            check("Param-port cycle reported", "param-cycle" in error_codes(graph)),
        ]
    )


def check_model18(proc, code, graph):
    """y = 2x must be learned essentially exactly."""
    return all(
        [
            check("MSELoss configured", "nn.MSELoss()" in code),
            check("Single 1→1 layer", linear_layers(code) == [(1, 1)], str(linear_layers(code))),
            check("Training completed", "Training complete." in proc.stdout),
            check("Converged below 1e-4", converged(proc, 1e-4), loss_trend(proc)),
        ]
    )


def check_model19(proc, code, graph):
    """Linearly separable classification: accuracy above 0.8."""
    roles = output_roles(code)
    return all(
        [
            check("CrossEntropyLoss configured", "nn.CrossEntropyLoss()" in code),
            check("Prediction port applies softmax",
                  roles.get("prediction", "").startswith("torch.softmax(")),
            check("Evaluation port applies argmax",
                  roles.get("evaluation", "").startswith("torch.argmax(")),
            check("Accuracy above 0.8", accurate_to(proc, 0.8), str(final_accuracy(proc))),
            check("Training completed", "Training complete." in proc.stdout),
        ]
    )


def check_model20(proc, code, graph):
    """Conv2D + Flatten classifier: accuracy above 0.8 and a falling loss."""
    return all(
        [
            check("Conv2D present", "nn.Conv2d" in code),
            check("Flatten present", "nn.Flatten" in code),
            check("Accuracy above 0.8", accurate_to(proc, 0.8), str(final_accuracy(proc))),
            check("Loss decreased", loss_decreased(proc), loss_trend(proc)),
        ]
    )


def check_model21(proc, code, graph):
    """Two branches added together must agree in width and converge."""
    layers = linear_layers(code)
    widths = {out for _, out in layers}
    return all(
        [
            check("Add merge present", re.search(r"= \w+ \+ \w+$", code, re.M)),
            check("At least two branches", len(layers) >= 2, str(layers)),
            check("Branch widths match", len(widths) == 1, str(widths)),
            check("Converged below 0.01", converged(proc, 0.01), loss_trend(proc)),
        ]
    )


def check_model22(proc, code, graph):
    """Classification run: accuracy above 0.9 with a falling loss."""
    return all(
        [
            check("Script exited cleanly", proc.returncode == 0),
            check("Training completed", "Training complete." in proc.stdout),
            check("Accuracy above 0.9", accurate_to(proc, 0.9), str(final_accuracy(proc))),
            check("Loss decreased", loss_decreased(proc), loss_trend(proc)),
        ]
    )


def check_model23(proc, code, graph):
    """A visualization-only graph still produces a runnable script."""
    scatter_colours = re.findall(r"plt\.scatter\([^\n]*c=([^,]+),", code)
    return all(
        [
            check("Discrete palette present", "ListedColormap" in code),
            check("Scatter is colour-mapped", bool(scatter_colours), str(scatter_colours)),
            check("Two figures shown", code.count("plt.show()") == 2),
            check("Script exited cleanly", proc.returncode == 0),
            check(
                "Missing model reported as a warning, not an error",
                diagnostics(graph)["isValid"]
                and "missing-output" in warning_codes(graph),
            ),
        ]
    )


def check_model24(proc, code, graph):
    """Continuous colour mapping keeps the configured endpoint colours."""
    return all(
        [
            check("Continuous colour map present", "LinearSegmentedColormap" in code),
            check("Configured colours preserved", "#ff0000" in code and "#ffff00" in code),
            check("Script exited cleanly", proc.returncode == 0),
        ]
    )


def check_model25(proc, code, graph):
    """Validation split plus early stopping cuts training short."""
    epoch = last_epoch(proc)
    return all(
        [
            check("Validation split emitted",
                  "val_size = int(features.size(0) * 0.2)" in code),
            check("Early stopping triggered", "Early stopping." in proc.stdout),
            check("Stopped before the epoch cap", epoch is not None and epoch < 200,
                  f"last epoch {epoch}"),
        ]
    )


def check_model26(proc, code, graph):
    """Two parallel features must both reach the layer, not just the first."""
    layers = linear_layers(code)
    call_sites = re.findall(r"torch\.cat\(\[data\.\w+, data\.\w+\], dim=1\)", code)
    return all(
        [
            check("Layer sized for both features", layers and layers[0][0] == 2, str(layers)),
            check("Both features concatenated at the call site", len(call_sites) >= 1),
            check("Training completed", "Training complete." in proc.stdout),
            check("Accuracy above 0.8", accurate_to(proc, 0.8), str(final_accuracy(proc))),
        ]
    )


def check_model27(proc, code, graph):
    """Inputs with incompatible batch sizes cannot meet inside one layer."""
    return all(
        [
            check("Graph rejected", not diagnostics(graph)["isValid"]),
            check("Batch size conflict reported", "batch-size-mismatch" in error_codes(graph)),
        ]
    )


def check_model28(proc, code, graph):
    """Full-featured run: SGD, clipping, validation accuracy, early stopping."""
    epoch = last_epoch(proc)
    return all(
        [
            check("SGD with momentum and weight decay",
                  "optim.SGD" in code and "momentum=0.9" in code
                  and "weight_decay=0.0001" in code),
            check("Gradient clipping applied", "clip_grad_norm_" in code),
            check("Validation split emitted",
                  "val_size = int(features.size(0) * 0.2)" in code),
            check("Validation uses accuracy",
                  "val_acc" in code and "Val Accuracy:" in proc.stdout),
            check("Early stopping triggered", "Early stopping." in proc.stdout),
            check("Confusion matrix printed", "Confusion Matrix:" in proc.stdout),
            check("Discrete colour visualisation present", "ListedColormap" in code),
            check("Stopped before the epoch cap", epoch is not None and epoch < 200,
                  f"last epoch {epoch}"),
        ]
    )


# Models that only test validator errors – their generated code must NOT be executed.
VALIDATION_ONLY_MODELS = {13, 14, 15, 16, 17, 27}

MODEL_CHECKS = {
    1: check_model1,
    2: check_model2,
    3: check_model3,
    4: check_model4,
    5: check_model5,
    6: check_model6,
    7: check_model7,
    8: check_model8,
    9: check_model9,
    10: check_model10,
    11: check_model11,
    12: check_model12,
    13: check_model13,
    14: check_model14,
    15: check_model15,
    16: check_model16,
    17: check_model17,
    18: check_model18,
    19: check_model19,
    20: check_model20,
    21: check_model21,
    22: check_model22,
    23: check_model23,
    24: check_model24,
    25: check_model25,
    26: check_model26,
    27: check_model27,
    28: check_model28,
}


# ----------------------------------------------------------------------
# Main test logic
# ----------------------------------------------------------------------


def test_model(model_file: Path, interactive: bool, dump_code: bool = False) -> bool:
    """Verify model."""
    print(f"\n=== Testing {model_file.name} ===")

    with open(model_file) as f:
        graph = json.load(f)

    code = generate_code(graph)

    # Force CPU device so tests are consistent and don't use GPU
    code = code.replace(
        "torch.device('cuda' if torch.cuda.is_available() else 'cpu')",
        "torch.device('cpu')",
    )

    print("Code generated successfully.")

    m = re.match(r"model(\d+)\.json", model_file.name, re.IGNORECASE)
    model_idx = int(m.group(1)) if m else None

    if dump_code:
        dump_path = EXAMPLES_DIR / f"{model_file.stem}_generated.py"
        with open(dump_path, "w", encoding="utf-8") as f:
            f.write(code)
        print(f"💾 Dumped generated code to {dump_path}")

    # Validation‑only models: skip execution, only check validator
    if model_idx in VALIDATION_ONLY_MODELS:
        print("⏭️  Validation‑only model – skipping execution.")
        ok = static_check(code)
        if model_idx is not None and model_idx in MODEL_CHECKS:
            print("\nRunning specific checks...")
            ok = MODEL_CHECKS[model_idx](None, code, graph) and ok
        if ok:
            print("✅ All checks passed.")
        return ok

    proc = run_generated_code(code, timeout=120, interactive=interactive)

    # Show errors even in interactive mode
    if proc.returncode != 0:
        print("❌ Model exited with error:")
        if proc.stderr:
            # If SyntaxError, try to extract line number and show the line
            stderr = proc.stderr
            print(stderr[-1000:])
            # Try to find line number in the error
            lineno_match = re.search(r"line (\d+)", stderr)
            if lineno_match:
                lineno = int(lineno_match.group(1))
                lines = code.splitlines()
                if lineno <= len(lines):
                    start = max(0, lineno - 3)
                    end = min(len(lines), lineno + 2)
                    print("\n--- Generated code near error ---")
                    for i in range(start, end):
                        marker = ">>>" if i == lineno - 1 else "   "
                        print(f"{marker} {i+1:4d}: {lines[i]}")
                    print("--- end of snippet ---")
        else:
            print("(no stderr output)")
        return False

    # Interactive mode – no further checks
    if interactive:
        print("✅ Model ran interactively without error.")
        return True

    # Run default checks
    ok = default_check(proc, code, graph)

    # Run model-specific checks if available
    if model_idx is not None and model_idx in MODEL_CHECKS:
        print("\nRunning specific checks...")
        specific_ok = MODEL_CHECKS[model_idx](proc, code, graph)
        ok = ok and specific_ok

    if ok:
        print("✅ All checks passed.")
    return ok


def main():
    """Run the module as a script."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--mode", choices=["auto", "by_hand"], default="by_hand")
    parser.add_argument("--models", type=str, default=None)
    parser.add_argument(
        "--dump-code",
        action="store_true",
        help="Save generated code to examples folder",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Delete all __pycache__ directories before running",
    )
    args = parser.parse_args()

    if args.clear_cache:
        clear_project_cache()

    interactive = args.mode == "by_hand"

    if args.models:
        indices = [int(x.strip()) for x in args.models.split(",")]
        json_files = []
        for i in indices:
            pattern = f"model{i}.json"
            match = (
                next(EXAMPLES_DIR.glob(pattern), None)
                or next(EXAMPLES_DIR.glob(pattern.upper()), None)
                or next(EXAMPLES_DIR.glob(pattern.lower()), None)
            )
            if match:
                json_files.append(match)
            else:
                print(f"Warning: model file for index {i} not found, skipping.")
    else:
        json_files = sorted(EXAMPLES_DIR.glob("model*.json"))

    if not json_files:
        print("No model JSON files found.")
        sys.exit(1)

    failed = []
    for f in json_files:
        if not test_model(f, interactive, args.dump_code):
            failed.append(f.name)

    if failed:
        print(f"\n❌ {len(failed)} test(s) FAILED: {failed}")
        sys.exit(1)
    else:
        print("\n✅ All tests passed.")


if __name__ == "__main__":
    main()
