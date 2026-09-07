# Architecture

## Django apps

| App | URL prefix | Role |
|-----|------------|------|
| `accounts` | `/accounts/` | Custom user model, django-allauth |
| `data_manager` | `/data/` | Dataset upload, sharing, synthetic data |
| `models_library` | `/models/` | Saved graph JSON, forks, likes |
| `sketchmod` | `/sketchmod/` | SketchMod canvas + codegen APIs |
| `setting` | `/settings/` | Theme and sidebar preferences |
| `bug_reports` | `/bug-reports/` | In-app bug submission |

## Codegen pipeline

```
JSON graph → parse_graph (graph.py)
          → analyze_phases (phase_analyzer.py)
          → GraphValidator (validator.py)
          → build_plan (ir.py)
          → render (emit.py)
          → model.py
```

The intermediate **ExecutionPlan** resolves all dataflow at generation time (static SSA). Generated scripts use `Data` and `Output` NamedTuples — no runtime `inputs_dict`.

## Naming

- **SketchNet** — the product and project name.
- **SketchMod** — the canvas editor tab where graphs are drawn.
