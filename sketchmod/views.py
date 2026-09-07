import json
import io
import zipfile
import os
import re
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.urls import reverse
from data_manager.models import Dataset
from models_library.models import SketchModel
from .codegen.generator import CodeGenerator
from .codegen.validator import GraphValidator
from .codegen.phase_analyzer import highlight_path

logger = logging.getLogger(__name__)

MAX_GRAPH_BODY_BYTES = 2 * 1024 * 1024
_TEMPLATE_SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,62}$")


def _api_error(message="Request failed.", status=500):
    return JsonResponse({"success": False, "error": message}, status=status)


def _parse_graph_request(request):
    if len(request.body) > MAX_GRAPH_BODY_BYTES:
        return None, None, JsonResponse(
            {"success": False, "error": "Graph payload too large."}, status=413
        )
    data = json.loads(request.body)
    graph_json = data.get("graph", "{}")
    if isinstance(graph_json, str):
        graph = json.loads(graph_json)
    else:
        graph = graph_json
    return graph, data, None


def _zip_requirements(code: str) -> str:
    lines = [
        "torch>=2.0.0",
        "numpy>=1.24.0",
        "matplotlib>=3.7.0",
        "pandas>=2.0.0",
    ]
    if "sklearn" in code:
        lines.append("scikit-learn>=1.3.0")
    return "\n".join(lines) + "\n"


def _canvas_context(request, readonly=False, loaded_model=None):
    collapse_left = False
    collapse_right = False
    default_export_format = "pytorch-py"
    highlight_phase_on_open = "none"
    if request.user.is_authenticated:
        user_settings = request.user.settings
        collapse_left = user_settings.collapse_left_sidebar
        collapse_right = user_settings.collapse_right_sidebar
        default_export_format = user_settings.default_export_format
        highlight_phase_on_open = user_settings.highlight_phase_on_open
    context = {
        "readonly": readonly,
        "collapse_left_sidebar": collapse_left,
        "collapse_right_sidebar": collapse_right,
        "default_export_format": default_export_format,
        "highlight_phase_on_open": highlight_phase_on_open,
    }
    if loaded_model is not None:
        context["loaded_model"] = loaded_model
    return context


def canvas(request):
    load_id = request.GET.get("load")
    readonly = request.GET.get("readonly") == "1"

    if load_id and readonly:
        model = get_object_or_404(SketchModel, model_id=load_id)
        if not model.can_view(request.user):
            login_url = reverse("account_login")
            return redirect(f"{login_url}?next={request.get_full_path()}")
        return render(
            request,
            "sketchmod/canvas.html",
            _canvas_context(request, readonly=True, loaded_model=model),
        )

    if not request.user.is_authenticated:
        login_url = reverse("account_login")
        return redirect(f"{login_url}?next={request.get_full_path()}")

    return render(
        request,
        "sketchmod/canvas.html",
        _canvas_context(request, readonly=False),
    )


def api_dataset_columns(request, dataset_id):
    dataset = get_object_or_404(Dataset, dataset_id=dataset_id)
    if not dataset.is_visible_to(request.user):
        return JsonResponse({"error": "Not allowed"}, status=403)
    try:
        import pandas as pd

        file_path = dataset.file.path
        ext = dataset.format
        if ext == "csv":
            df = pd.read_csv(file_path, nrows=0)
        elif ext == "xlsx":
            df = pd.read_excel(file_path, nrows=0)
        elif ext == "json":
            df = pd.read_json(file_path)
            df = df.head(0)
        elif ext == "parquet":
            df = pd.read_parquet(file_path)
            df = df.head(0)
        else:
            return JsonResponse(
                {
                    "columns": [],
                    "count": 0,
                    "message": "Cannot read columns for this format",
                }
            )
        columns = df.columns.tolist()
        return JsonResponse({"columns": columns, "count": len(columns)})
    except Exception:
        logger.exception("Failed to read dataset columns")
        return JsonResponse(
            {"columns": [], "count": 0, "message": "Could not read columns."}
        )


def export_api(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST required"}, status=405)
    try:
        graph, data, error = _parse_graph_request(request)
        if error:
            return error

        export_format = data.get("format", "pytorch-py")

        validation = GraphValidator(graph).validate()
        if not validation["isValid"]:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Graph validation failed.",
                    "errors": validation["errors"],
                    "warnings": validation["warnings"],
                },
                status=400,
            )

        code = CodeGenerator(graph).generate()

        if export_format == "pytorch-zip":
            return _export_zip(graph, code, request)

        return JsonResponse({"success": True, "code": code, "filename": "model.py"})
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)
    except Exception:
        logger.exception("export_api failed")
        return _api_error("Export failed.")


def _export_zip(graph, code, request):
    """Create a zip file containing model.py and dataset files."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("model.py", code)

        input_node = next(
            (n for n in graph.get("nodes", []) if n["type"] == "input-data"),
            None,
        )
        if input_node and input_node.get("datasetId"):
            dataset_id = input_node["datasetId"]
            try:
                dataset = Dataset.objects.get(dataset_id=dataset_id)
                if not dataset.is_visible_to(request.user):
                    zf.writestr(
                        "data/README.txt",
                        "You do not have access to the selected dataset.\n"
                        "Add your own data to the data/ folder and update load_data().\n",
                    )
                elif dataset.file and dataset.file.name:
                    file_path = os.path.join(settings.MEDIA_ROOT, dataset.file.name)
                    if os.path.exists(file_path):
                        filename = os.path.basename(dataset.file.name)
                        zf.write(file_path, f"data/{filename}")
                        ext = (
                            dataset.format
                            if dataset.format
                            else filename.rsplit(".", 1)[-1]
                        )
                        load_instructions = ""
                        if ext == "csv":
                            load_instructions = f"df = pd.read_csv('data/{filename}')"
                        elif ext in ("xlsx", "xls"):
                            load_instructions = f"df = pd.read_excel('data/{filename}')"
                        elif ext == "json":
                            load_instructions = f"df = pd.read_json('data/{filename}')"
                        elif ext == "parquet":
                            load_instructions = (
                                f"df = pd.read_parquet('data/{filename}')"
                            )
                        else:
                            load_instructions = f"# Load 'data/{filename}' appropriately for {ext} format"
                        zf.writestr(
                            "data/README.txt",
                            f"Dataset: {dataset.name}\n"
                            f"Format: {ext}\n"
                            f"Uploaded: {dataset.created_at}\n"
                            f"\nLoad with:\n"
                            f"  import pandas as pd\n"
                            f"  {load_instructions}\n",
                        )
                    else:
                        zf.writestr(
                            "data/README.txt",
                            "Dataset file not found.\n"
                            "Please download the dataset separately from SketchNet.\n",
                        )
                else:
                    zf.writestr("data/README.txt", "Dataset has no file attached.\n")
            except Dataset.DoesNotExist:
                zf.writestr(
                    "data/README.txt", f"Dataset with ID '{dataset_id}' not found.\n"
                )
            except Exception:
                logger.exception("Failed to attach dataset to export zip")
                zf.writestr("data/README.txt", "Error accessing dataset.\n")
        else:
            zf.writestr(
                "data/README.txt",
                "No dataset selected in the model.\n"
                "Add your dataset to the 'data/' folder and update load_data() in model.py\n",
            )

        zf.writestr("requirements.txt", _zip_requirements(code))

    zip_buffer.seek(0)
    response = HttpResponse(zip_buffer.getvalue(), content_type="application/zip")
    response["Content-Disposition"] = 'attachment; filename="model.zip"'
    return response


def validate_api(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST required"}, status=405)
    try:
        graph, _, error = _parse_graph_request(request)
        if error:
            return error
        result = GraphValidator(graph).validate()
        return JsonResponse({"success": True, **result})
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)
    except Exception:
        logger.exception("validate_api failed")
        return _api_error("Validation failed.")


def highlight_path_api(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST required"}, status=405)
    try:
        graph, data, error = _parse_graph_request(request)
        if error:
            return error
        phase = data.get("phase", "")
        result = highlight_path(graph, phase)
        return JsonResponse({"success": True, **result})
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)
    except Exception:
        logger.exception("highlight_path_api failed")
        return _api_error("Highlight failed.")


def template_view(request, template_name):
    """Load a template and redirect to canvas with session storage set."""
    if not _TEMPLATE_SLUG_RE.fullmatch(template_name):
        request.session["template_error"] = f"Template '{template_name}' not found."
        return redirect("sketchmod:canvas")

    template_dir = os.path.abspath(
        os.path.join(
            settings.BASE_DIR,
            "sketchmod",
            "static",
            "sketchmod",
            "templates",
        )
    )
    template_path = os.path.abspath(
        os.path.join(template_dir, f"{template_name}.json")
    )
    try:
        if os.path.commonpath([template_dir, template_path]) != template_dir:
            request.session["template_error"] = (
                f"Template '{template_name}' not found."
            )
            return redirect("sketchmod:canvas")
    except ValueError:
        request.session["template_error"] = f"Template '{template_name}' not found."
        return redirect("sketchmod:canvas")

    if os.path.exists(template_path):
        with open(template_path) as f:
            graph = json.load(f)
        request.session["template_graph"] = graph
    else:
        request.session["template_error"] = f"Template '{template_name}' not found."

    return redirect("sketchmod:canvas")


@login_required
def consume_template_api(request):
    """Return and clear the template stored in session."""
    graph = request.session.pop("template_graph", None)
    error = request.session.pop("template_error", None)
    return JsonResponse({"graph": graph, "error": error})
