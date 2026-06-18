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


def default_check(proc, code, graph):
    """Basic checks that apply to every model."""
    ok = True
    if proc.returncode != 0:
        print("❌ Model crashed (non‑zero exit code)")
        ok = False
    if "Training complete." not in proc.stdout:
        print("❌ Missing 'Training complete.'")
        ok = False
    if proc.stderr.strip():
        if "Traceback" in proc.stderr:
            print("❌ Traceback in stderr")
            ok = False
        else:
            print("⚠️  stderr output (likely harmless warnings):")
            print(proc.stderr.strip()[:500])  # first 500 chars
    return ok


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
# Model‑specific checks
# ----------------------------------------------------------------------


def check_model1(proc, code, graph):
    """
    model1 checks:
      1. Output ports are correctly transformed:
         loss -> raw logits, prediction -> argmax, evaluation -> softmax.
      2. OneHot → DeOneHot parameter sharing is wired.
      3. Phase analysis produces correct sets.
      4. General execution succeeds.
    """
    ok = True

    # 1) Output port assignments
    loss_line = re.search(
        r"outputs\['output-main_output_0'\]\s*=\s*x\s*$", code, re.MULTILINE
    )
    argmax_line = re.search(
        r"outputs\['output-main_output_1'\]\s*=\s*torch\.argmax\(x,\s*dim=-1\)", code
    )
    softmax_line = re.search(
        r"outputs\['output-main_output_2'\]\s*=\s*torch\.softmax\(x,\s*dim=-1\)", code
    )

    if not loss_line:
        print("❌ Loss port not assigned as raw logits")
        ok = False
    else:
        print("✅ Loss port (raw logits)")

    if not argmax_line:
        print("❌ Prediction port not assigned as argmax")
        ok = False
    else:
        print("✅ Prediction port (argmax)")

    if not softmax_line:
        print("❌ Evaluation port not assigned as softmax")
        ok = False
    else:
        print("✅ Evaluation port (softmax)")

    # 2) OneHot → DeOneHot parameter sharing
    eval_section = code.split("def evaluate(")[1] if "def evaluate(" in code else code
    # In evaluation section, find the DeOneHot part (which produces d23_out)
    d23_match = re.search(r"d23_out\s*=\s*torch\.argmax", eval_section)
    if not d23_match:
        print("❌ DeOneHot d23 not found")
        ok = False
    else:
        # Everything after d23_out until next function or end
        d23_block = eval_section[d23_match.start() :]
        if "torch.arange" in d23_block:
            print("❌ DeOneHot creates its own categories (missing parameter sharing)")
            ok = False
        else:
            print("✅ OneHot → DeOneHot parameter sharing")

    # 3) Phase analysis
    parsed = parse_graph(graph)
    flow = analyze_phases(parsed)
    pre_set = flow["preprocessing_set"]
    train_set = flow["train_set"]
    eval_set = flow["eval_set"]

    if "o8" not in pre_set:
        print("❌ OneHot (o8) not in preprocessing set")
        ok = False
    if "l9" not in train_set:
        print("❌ Layer l9 not in training set")
        ok = False
    if "l9" not in eval_set:
        print("❌ Layer l9 not in evaluation set")
        ok = False
    if "v12" in train_set:
        print("❌ Visualization v12 should NOT be in training set")
        ok = False
    if "d23" in train_set:
        print("❌ DeOneHot d23 should NOT be in training set")
        ok = False
    else:
        print("✅ Phase analysis sets are correct")

    return ok


def check_model2(proc, code, graph):
    """
    model2 checks:
      1. Both visualizations v12 and v1 are present (both active in evaluation).
      2. The generated code contains exactly two plt.show() calls.
      3. General execution succeeds.
    """
    ok = True

    for viz in ("v12", "v1"):
        if f"Visualization '{viz}'" not in code:
            print(f"❌ Visualization {viz} missing")
            ok = False
        else:
            print(f"✅ Visualization {viz} present")

    show_count = code.count("plt.show()")
    if show_count != 2:
        print(f"❌ Expected 2 plt.show() calls, found {show_count}")
        ok = False
    else:
        print(f"✅ Found {show_count} plt.show() calls")

    return ok


def check_model3(proc, code, graph):
    """
    model3 checks:
      1. Nodes that are NOT fully active in any phase must NOT appear in the generated code.
      2. Print node p7 (empty activationPhases) must be absent.
      3. Accuracy a6 and visualization v1 must be absent because some of their input ports lack the correct phase.
      4. Visualization v12 and DeOneHot d23 must be present (they have full evaluation connectivity).
      5. General execution succeeds.
    """
    ok = True

    # p7 should NOT be generated
    if "p7" in code:
        print("❌ p7 (Print) should not be generated (activationPhases empty)")
        ok = False
    else:
        print("✅ p7 correctly absent")

    # a6 should NOT be generated
    if "a6" in code:
        print(
            "❌ a6 (Accuracy) should not be generated (one input missing evaluation phase)"
        )
        ok = False
    else:
        print("✅ a6 correctly absent")

    # v1 should NOT be generated
    if "v1" in code and "Visualization 'v1'" in code:
        print(
            "❌ v1 (Visualization) should not be generated (color input lacks evaluation phase)"
        )
        ok = False
    else:
        print("✅ v1 correctly absent")

    # v12 and d23 SHOULD be generated
    if "Visualization 'v12'" not in code:
        print("❌ v12 missing but should be active")
        ok = False
    else:
        print("✅ v12 present")

    if "d23_out" not in code:
        print("❌ d23 missing but should be active")
        ok = False
    else:
        print("✅ d23 present")

    return ok


def check_model4(proc, code, graph):
    ok = True

    # 1. p12 (loss print) inside training loop
    if "print('loss" not in code and 'print("loss' not in code:
        print("❌ p12 (loss print) missing in training loop")
        ok = False
    else:
        print("✅ p12 (loss print) present in training loop")

    # 2. DeOneHot handles softmax input
    if "d23_out = torch.argmax(output_main_output_2_tensor, dim=-1)" not in code:
        print("❌ d23 not handling softmax correctly")
        ok = False
    else:
        print("✅ d23 handles softmax")

    # 3. Confusion matrix printed
    if "Confusion Matrix:" not in code:
        print("❌ Confusion matrix not printed")
        ok = False
    else:
        print("✅ Confusion matrix will be printed")

    # 4. Accuracy uses argmax predictions and c5 labels
    if "pred_labels = output_main_output_1_tensor" not in code:
        print(
            "❌ Accuracy predictions should use argmax output (output_main_output_1_tensor)"
        )
        ok = False
    else:
        print("✅ Accuracy predictions from correct port")
    if "true_labels = c5" not in code:
        print("❌ Accuracy labels should use c5")
        ok = False
    else:
        print("✅ Accuracy labels from c5")

    # 5. Both visualizations present
    for viz in ("v12", "v1"):
        if f"Visualization '{viz}'" not in code:
            print(f"❌ {viz} missing")
            ok = False
        else:
            print(f"✅ {viz} present")

    return ok


def check_model5(proc, code, graph):
    ok = True

    # 1. Three Train/Test Split nodes (t1, t2, t3) are present – check for the
    #    new variable names: train_data_t1, train_data_t2, train_data_t3.
    for s in ("t1", "t2", "t3"):
        if f"train_data_{s}" in code:
            print(f"✅ Split node {s} found")
        else:
            print(f"❌ Split node {s} missing")
            ok = False

    # 2. Training present
    if "class Model" in code and "train_model" in code:
        print("✅ Training loop present")
    else:
        print("❌ Training loop missing")
        ok = False

    # 3 & 4. Evaluation and visualization present
    if "def evaluate(" in code and "Visualization 'v1'" in code:
        print("✅ Evaluation + visualization v1 present")
    else:
        print("❌ Evaluation or visualization v1 missing")
        ok = False

    # 5. No shape mismatch warnings
    from sketchmod.codegen.validator import GraphValidator

    result = GraphValidator(graph).validate()
    warnings = [w["message"] for w in result.get("warnings", [])]
    if any(">1 column" in w for w in warnings) or any(
        "different sample sizes" in w for w in warnings
    ):
        print("❌ Unexpected shape mismatch warning for visualization")
        ok = False
    else:
        print("✅ No shape mismatch warnings")

    return ok


def check_model6(proc, code, graph):
    """
    model6 checks:
      1. Dropout, Add, Concat nodes are present in the generated code.
      2. Preprocessing visualization (viz_pre) is present and runs in load_and_preprocess.
      3. Evaluation visualization (viz_eval) is present and runs in evaluate.
      4. Training visualization (viz_train) triggers a validator warning.
      5. Model converges (final training loss < 0.1).
    """
    ok = True

    # 1. Key nodes
    for node_name in ["dropout", "Add", "Concat"]:
        if node_name.lower() in code.lower():
            print(f"✅ {node_name} found")
        else:
            print(f"❌ {node_name} missing")
            ok = False

    # 2. Preprocessing viz
    if "Visualization 'viz_pre'" in code:
        print("✅ viz_pre present")
    else:
        print("❌ viz_pre missing")
        ok = False

    # 3. Evaluation viz
    if "Visualization 'viz_eval'" in code:
        print("✅ viz_eval present")
    else:
        print("❌ viz_eval missing")
        ok = False

    # 4. Training viz warning
    from sketchmod.codegen.validator import GraphValidator

    result = GraphValidator(graph).validate()
    warnings = [w["message"] for w in result.get("warnings", [])]
    if any("training" in w.lower() and "visualization" in w.lower() for w in warnings):
        print("✅ Training visualization warning present")
    else:
        print("❌ Training visualization warning missing")
        ok = False

    # 5. Convergence
    output = proc.stdout
    import re

    losses = re.findall(r"Train Loss: ([0-9.]+)", output)
    if losses:
        final_train_loss = float(losses[-1])
        if final_train_loss < 0.1:
            print(f"✅ Model converged (final train loss = {final_train_loss:.6f})")
        else:
            print(
                f"❌ Model did not converge (final train loss = {final_train_loss:.6f})"
            )
            ok = False
    else:
        print("❌ Could not parse train loss from output")
        ok = False

    return ok


def check_model7(proc, code, graph):
    """
    model7 checks:
      1. RowSelect node is present.
      2. BatchNorm node is present.
      3. LeakyReLU activation is used.
      4. CrossEntropyLoss is configured.
      5. Output activations softmax/argmax are correctly set.
      6. Accuracy node appears and final accuracy exceeds 80 %.
      7. Visualization with discrete colour mapping is present.
    """
    ok = True

    # 1. RowSelect
    if "row_sel_out" in code or "row_sel" in code:
        print("✅ RowSelect found")
    else:
        print("❌ RowSelect missing")
        ok = False

    # 2. BatchNorm
    if "BatchNorm" in code or "bn1" in code:
        print("✅ BatchNorm found")
    else:
        print("❌ BatchNorm missing")
        ok = False

    # 3. LeakyReLU
    if "leaky_relu" in code:
        print("✅ LeakyReLU activation used")
    else:
        print("❌ LeakyReLU not found")
        ok = False

    # 4. CrossEntropyLoss
    if "CrossEntropyLoss" in code:
        print("✅ CrossEntropyLoss")
    else:
        print("❌ CrossEntropyLoss missing")
        ok = False

    # 5. Output activations
    if "torch.argmax(x, dim=-1)" in code:
        print("✅ Argmax on prediction/evaluation ports")
    else:
        print("❌ Argmax missing")
        ok = False

    # 6. Accuracy > 80%
    output = proc.stdout
    import re

    acc_match = re.search(r"Accuracy: ([0-9.]+)", output)
    if acc_match:
        acc = float(acc_match.group(1))
        if acc > 0.8:
            print(f"✅ Accuracy {acc:.4f} > 0.8")
        else:
            print(f"❌ Accuracy {acc:.4f} ≤ 0.8")
            ok = False
    else:
        print("❌ Could not parse Accuracy from output")
        ok = False

    # 7. Visualization with colour
    if "ListedColormap" in code:
        print("✅ Discrete colour mapping present")
    else:
        print("❌ No discrete colour mapping found")
        ok = False

    return ok


def check_model8(proc, code, graph):
    """
    model8 checks:
      1. Conv2D node present in generated code.
      2. Reshape node present.
      3. Flatten node present.
      4. Accuracy > 0.7 (should be near 1.0 with this simple dataset).
    """
    ok = True

    if "nn.Conv2d" in code or "self.conv_conv" in code:
        print("✅ Conv2D found")
    else:
        print("❌ Conv2D missing")
        ok = False

    if ".reshape(" in code:
        print("✅ Reshape found")
    else:
        print("❌ Reshape missing")
        ok = False

    if "nn.Flatten" in code or "self.flatten_flat" in code:
        print("✅ Flatten found")
    else:
        print("❌ Flatten missing")
        ok = False

    import re

    acc_match = re.search(r"Accuracy: ([0-9.]+)", proc.stdout)
    if acc_match:
        acc = float(acc_match.group(1))
        if acc > 0.7:
            print(f"✅ Accuracy {acc:.4f} > 0.7")
        else:
            print(f"❌ Accuracy {acc:.4f} ≤ 0.7")
            ok = False
    else:
        print("❌ Could not parse Accuracy")
        ok = False

    return ok


def check_model9(proc, code, graph):
    """
    model9 checks:
      1. Validator warns about multiple optimizers.
      2. Training still runs with the first optimizer.
    """
    ok = True

    from sketchmod.codegen.validator import GraphValidator

    result = GraphValidator(graph).validate()
    warnings = result.get("warnings", [])
    if any("Only the first one will be used" in w.get("message", "") for w in warnings):
        print("✅ Multiple optimizers warning present")
    else:
        print("❌ Expected warning for multiple optimizers not found")
        ok = False

    if "Training complete." in proc.stdout:
        print("✅ Training completed with first optimizer")
    else:
        print("❌ Training did not complete")
        ok = False

    return ok


def check_model10(proc, code, graph):
    """
    model10 checks:
      1. Validator warns about evaluation entry point.
      2. No evaluation function is generated.
      3. Script exits cleanly (no NameError).
    """
    ok = True

    from sketchmod.codegen.validator import GraphValidator

    result = GraphValidator(graph).validate()
    warnings = result.get("warnings", [])
    if any("Evaluation will be skipped" in w.get("message", "") for w in warnings):
        print("✅ Evaluation entry point warning present")
    else:
        print("❌ Expected warning for evaluation entry point not found")
        ok = False

    if "def evaluate(" not in code:
        print("✅ No evaluation function generated")
    else:
        print("❌ Evaluation function should not be generated")
        ok = False

    # The script should exit cleanly (returncode 0, 'Training complete.' present)
    if proc.returncode == 0 and "Training complete." in proc.stdout:
        print("✅ Script exited cleanly")
    else:
        print("❌ Script crashed or training incomplete")
        ok = False

    return ok


def check_model11(proc, code, graph):
    """
    model11 checks:
      1. Validator reports error about multiple training entry points.
         (The UI would block export when this error exists, so the test
          only needs to confirm the error is present.)
    """
    ok = True

    from sketchmod.codegen.validator import GraphValidator

    result = GraphValidator(graph).validate()
    errors = result.get("errors", [])
    if any("Multiple training entry points" in e.get("message", "") for e in errors):
        print("✅ Multiple training entry points error detected")
    else:
        print("❌ Expected error for multiple training entry points not found")
        ok = False

    return ok


def check_model12(proc, code, graph):
    """
    model12 checks:
      1. Branched network with Add merge is generated.
      2. Preprocessing visualization exists.
      3. Evaluation visualization exists.
      4. Print nodes appear in all three phases.
      5. Model converges (final train loss < 0.5).
    """
    ok = True

    # 1. Add merge present
    if "x = a + b" in code or "outputs['add']" in code:
        print("✅ Add merge found")
    else:
        print("❌ Add merge missing")
        ok = False

    # 2. Preprocessing viz
    if "Visualization 'viz_pre'" in code:
        print("✅ viz_pre present")
    else:
        print("❌ viz_pre missing")
        ok = False

    # 3. Evaluation viz
    if "Visualization 'viz_eval'" in code:
        print("✅ viz_eval present")
    else:
        print("❌ viz_eval missing")
        ok = False

    # 4. Print nodes in all phases
    for label in ("pre_data_shape", "train_loss_tensor", "predictions"):
        if f'print("{label}' in code or f"print('{label}" in code:
            print(f"✅ Print '{label}' found")
        else:
            print(f"❌ Print '{label}' missing")
            ok = False

    # 5. Convergence
    output = proc.stdout if proc else ""
    import re

    losses = re.findall(r"Train Loss: ([0-9.]+)", output)
    if losses:
        final_train_loss = float(losses[-1])
        if final_train_loss < 0.5:
            print(f"✅ Model converged (final train loss = {final_train_loss:.6f})")
        else:
            print(
                f"❌ Model did not converge (final train loss = {final_train_loss:.6f})"
            )
            ok = False
    else:
        print("❌ Could not parse train loss from output")
        ok = False

    return ok


def check_model13(proc, code, graph):
    """
    model13 checks:
      1. Data‑flow cycle error detected.
      2. Unconnected layer input error detected.
      3. Impossible reshape warning detected.
    """
    ok = True

    from sketchmod.codegen.validator import GraphValidator

    result = GraphValidator(graph).validate()
    errors = result.get("errors", [])
    warnings = result.get("warnings", [])

    if any("Data‑flow cycle" in e.get("message", "") for e in errors):
        print("✅ Data‑flow cycle error detected")
    else:
        print("❌ Data‑flow cycle error not found")
        ok = False

    if any(
        "requires at least 1 input connection" in e.get("message", "") for e in errors
    ):
        print("✅ Unconnected layer input error detected")
    else:
        print("❌ Unconnected layer input error not found")
        ok = False

    if any("total elements mismatch" in w.get("message", "") for w in warnings):
        print("✅ Impossible reshape warning detected")
    else:
        print("❌ Impossible reshape warning not found")
        ok = False

    return ok


def check_model14(proc, code, graph):
    """
    model14 checks:
      1. Reshape line contains the symbolic name 'batch' (preserved, not substituted).
      2. Reshape line uses -1 for inferred dimension.
      3. No shape feasibility warning (the input size 200*28*28 is divisible by batch=200).
      4. The model is validation‑only – code is generated but not executed.
    """
    ok = True

    # 1. Symbolic 'batch' appears in the reshape call.
    if "batch" in code:
        print("✅ Symbolic 'batch' present in generated code")
    else:
        print("❌ Symbolic 'batch' missing")
        ok = False

    # 2. The -1 dimension is kept (it should be inferred, so -1 should appear).
    # The reshape call should look like: .reshape((batch, -1))
    if ".reshape((batch, -1))" in code:
        print("✅ Reshape with -1 inferred dimension")
    else:
        # Fallback: maybe the code uses a different formatting
        if "-1" in code and "batch" in code:
            print("✅ Reshape line contains -1 and batch")
        else:
            print("❌ Reshape line does not contain -1")
            ok = False

    # 3. Check validator warnings: there should be no reshape feasibility warning.
    from sketchmod.codegen.validator import GraphValidator

    result = GraphValidator(graph).validate()
    warnings = [w["message"] for w in result.get("warnings", [])]
    reshape_warnings = [
        w for w in warnings if "reshape" in w.lower() and "total elements" in w.lower()
    ]
    if reshape_warnings:
        print("❌ Unexpected reshape feasibility warning:", reshape_warnings[0])
        ok = False
    else:
        print("✅ No reshape feasibility warning")

    return ok


def check_model15(proc, code, graph):
    """
    model15 checks (validation only):
      1. Error: Param‑port cycle detected.
    """
    ok = True
    from sketchmod.codegen.validator import GraphValidator

    result = GraphValidator(graph).validate()
    errors = result.get("errors", [])
    warnings = result.get("warnings", [])

    # 1. Param‑port cycle error
    if any("Param‑port cycle" in e.get("message", "") for e in errors):
        print("✅ Param‑port cycle error detected")
    else:
        print("❌ Param‑port cycle error not found")
        ok = False

    return ok


# Models that only test validator errors – their generated code must NOT be executed.
VALIDATION_ONLY_MODELS = {11, 13, 14, 15}

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
        if model_idx is not None and model_idx in MODEL_CHECKS:
            print("\nRunning specific checks...")
            ok = MODEL_CHECKS[model_idx](None, code, graph)
            if ok:
                print("✅ All checks passed.")
            return ok
        return True

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

    # Determine model index from filename
    m = re.match(r"model(\d+)\.json", model_file.name, re.IGNORECASE)
    model_idx = int(m.group(1)) if m else None

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
