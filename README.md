# SketchNet

SketchNet is a visual machine learning editor. Draw neural network graphs on the **SketchMod** canvas, attach datasets from the Data library, save models to the Models library, and export clean PyTorch scripts.

## Quick start

```powershell
git clone <repository-url>
cd SketchNet
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py runserver
```

Open http://127.0.0.1:8000/ and sign up. Use the **SketchMod** tab to draw a graph, **Check** to validate, then **Export** to download Python code.

## Documentation

- [Architecture](docs/architecture.md)
- [Development](docs/development.md)
- [Codegen](docs/codegen.md)
- [Deployment](docs/deployment.md)
- [Contributing](CONTRIBUTING.md)

## Testing

```powershell
python manage.py test sketchmod
$env:PYTHONIOENCODING = "utf-8"
.venv\Scripts\python.exe sketchmod\tests\codegen\test_models.py --mode auto
```

## License

MIT — see [LICENSE](LICENSE).
