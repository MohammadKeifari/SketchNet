import json
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from data_manager.models import Dataset
from django.views.decorators.csrf import csrf_exempt

from .codegen.generator import CodeGenerator


@login_required
def canvas(request):
    context = {}
    if request.user.is_authenticated:
        user_settings = request.user.settings
        context["collapse_left_sidebar"] = user_settings.collapse_left_sidebar
        context["collapse_right_sidebar"] = user_settings.collapse_right_sidebar
    else:
        context["collapse_left_sidebar"] = False
        context["collapse_right_sidebar"] = False
    return render(request, "sketchmod/canvas.html", context)


def api_dataset_columns(request, dataset_id):
    """Return column names for a dataset"""
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
    except Exception as e:
        return JsonResponse({"columns": [], "count": 0, "message": str(e)})


@login_required
@csrf_exempt
def export_api(request):
    """API endpoint for code generation."""
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST required"}, status=405)

    try:
        data = json.loads(request.body)
        graph_json = data.get("graph", "{}")
        export_format = data.get("format", "pytorch-py")

        # Parse graph JSON
        if isinstance(graph_json, str):
            graph = json.loads(graph_json)
        else:
            graph = graph_json

        generator = CodeGenerator(graph)
        code = generator.generate()

        # Determine filename based on format
        filenames = {
            "pytorch-py": "model.py",
            "pytorch-zip": "model.py",  # zip handled separately
            "python-clipboard": "model.py",
        }
        filename = filenames.get(export_format, "model.py")

        return JsonResponse(
            {
                "success": True,
                "code": code,
                "filename": filename,
            }
        )

    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)
