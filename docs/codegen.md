# Codegen

SketchNet generates readable PyTorch from canvas graphs using a two-stage pipeline:

1. **IR** (`ir.py`) — builds an `ExecutionPlan`: preprocessing, `Data` fields, model inputs (phase-based binding), `forward` SSA lines, train/eval loops.
2. **Emit** (`emit.py`) — renders the plan into a single `.py` file.

Node types are implemented once in `nodes.py` as placement-agnostic emitters.

## Validator tiers

- **Errors** — graph cannot be translated (cycles, missing connections, optimizer not in training phase).
- **Warnings** — translatable but questionable (layer in preprocessing, multiple optimizers).

Every diagnostic includes a stable `code` field for tests and UI matching.

## Key design rules

- Same-phase model inputs concatenate; cross-phase sources collapse to one `forward` parameter.
- `Data` NamedTuple fields are chosen by liveness (what train/eval actually reads).
- User-controlled strings are sanitized in `sanitize.py` before emission.

## Contract test

`sketchmod/tests/codegen/test_generation_contract.py` asserts: invalid graph **or** generated source compiles.
