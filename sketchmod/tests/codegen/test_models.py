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

    # 2) OneHot → DeOneHot param link
    param_link = re.search(r"categories\s*=\s*o8_param_out_0", code)
    if not param_link:
        print("❌ OneHot → DeOneHot parameter sharing missing")
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
      1. Only visualization v12 is present; v1 is not active because its
         color input (c5) has only preprocessing phase.
      2. The generated code contains exactly one plt.show() call (for v12).
      3. General execution succeeds.
    """
    ok = True

    if "Visualization 'v12'" not in code:
        print("❌ Visualization v12 missing from code")
        ok = False
    else:
        print("✅ Visualization v12 found")

    # v1 should NOT be present
    if "Visualization 'v1'" in code:
        print("❌ Visualization v1 should NOT be active (color input lacks evaluation)")
        ok = False
    else:
        print("✅ Visualization v1 correctly absent")

    show_count = code.count("plt.show()")
    if show_count != 1:
        print(f"❌ Expected exactly 1 plt.show() call, found {show_count}")
        ok = False
    else:
        print(f"✅ Found {show_count} plt.show() call")

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
    """
    model4 checks:
      1. Training‑phase Print node p12 (label 'loss') is generated
         and runs inside the training loop every batch.
      2. DeOneHot (d23) correctly receives the softmax output
         and applies argmax.
      3. Confusion matrix is printed because
         showConfusion=True on the Accuracy node.
      4. Accuracy uses the argmax prediction port (output-main_output_1)
         and labels from c5.
      5. Both visualizations v12 and v1 are present.
         - v12 color comes from d23 (active via param-port carry-over).
         - v1 color comes from c5 (evaluation-active).
    """
    ok = True

    # 1. p12 (loss print) inside training loop
    if 'print("loss[0]:' not in code:  # note the colon
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
    """
    model5 checks:
      1. Three Train/Test Split nodes (t1, t2, t3) are present.
      2. Training loop is generated (layers have training phases).
      3. Evaluation function is generated (visualization v1 is active).
      4. Visualization v1 is present in the code.
      5. No shape-mismatch warning is emitted (graph uses proper 1D columns).
      6. The generated code runs without crash.
    """
    ok = True

    # 1. Three splits
    for s in ("t1", "t2", "t3"):
        if f"{s}_output_0" in code:
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
      5. Output activation softmax/argmax are correctly set.
      6. Accuracy node appears and final accuracy exceeds 80 %.
      7. Visualization with discrete colour mapping is present.
    """
    ok = True

    # 1. RowSelect
    if "row_sel" in code:
        print("✅ RowSelect found")
    else:
        print("❌ RowSelect missing")
        ok = False

    # 2. BatchNorm
    if "BatchNorm" in code:
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
    if "torch.softmax(x, dim=-1)" in code:
        print("✅ Softmax on prediction port")
    else:
        print("❌ Softmax missing")
        ok = False
    if "torch.argmax(x, dim=-1)" in code:
        print("✅ Argmax on evaluation port")
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


MODEL_CHECKS = {
    1: check_model1,
    2: check_model2,
    3: check_model3,
    4: check_model4,
    5: check_model5,
    6: check_model6,
    6: check_model7,
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

    if dump_code:
        dump_path = EXAMPLES_DIR / f"{model_file.stem}_generated.py"
        with open(dump_path, "w", encoding="utf-8") as f:
            f.write(code)
        print(f"💾 Dumped generated code to {dump_path}")

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
    args = parser.parse_args()

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
