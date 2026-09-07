# Development

## Setup

See [README.md](../README.md). Use the project virtualenv — system Python may lack `sympy`.

## Running tests

```powershell
python manage.py test sketchmod
python manage.py test data_manager models_library accounts
```

### Codegen model suite

After changing `sketchmod/codegen/**`:

```powershell
$env:PYTHONIOENCODING = "utf-8"
.venv\Scripts\python.exe sketchmod\tests\codegen\test_models.py --mode auto --dump-code
```

Set `PYTHONIOENCODING=utf-8` on Windows so emoji test output does not crash the console.

## Adding a node type

1. Add shape rules in `sketchmod/codegen/graph.py` if needed.
2. Add a `NodeEmitter` in `sketchmod/codegen/nodes.py` and register it in `EMITTERS`.
3. Add validator checks in `sketchmod/codegen/validator.py`.
4. Add canvas node class in `sketchmod/static/sketchmod/js/canvas.js`.
5. Add tests in `sketchmod/tests/codegen/test_nodes.py` and an example graph if applicable.
