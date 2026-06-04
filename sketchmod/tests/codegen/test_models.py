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
    return CodeGenerator(model_json).generate()


def run_generated_code(
    code: str, timeout: int = 120, interactive: bool = False
) -> subprocess.CompletedProcess:
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        tmp_path = f.name

    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = ""  # force CPU for tests
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
            print("⚠️  stderr output (warnings?)")
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


MODEL_CHECKS = {
    1: check_model1,
}


# ----------------------------------------------------------------------
# Main test logic
# ----------------------------------------------------------------------


def test_model(model_file: Path, interactive: bool, dump_code: bool = False) -> bool:
    print(f"\n=== Testing {model_file.name} ===")

    with open(model_file) as f:
        graph = json.load(f)

    code = generate_code(graph)
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
    m = re.match(r"model(\d+)\.json", model_file.name)
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
        json_files = [EXAMPLES_DIR / f"model{i}.json" for i in indices]
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
