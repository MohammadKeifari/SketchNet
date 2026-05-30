import json
import io
import zipfile
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404
from data_manager.models import Dataset
from django.views.decorators.csrf import csrf_exempt

from .generator import CodeGenerator


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

        if isinstance(graph_json, str):
            graph = json.loads(graph_json)
        else:
            graph = graph_json

        generator = CodeGenerator(graph)
        code = generator.generate()

        # ZIP export — bundle .py file with dataset
        if export_format == "pytorch-zip":
            return _export_zip(graph, code, request)

        # Other formats — return JSON with code
        return JsonResponse(
            {
                "success": True,
                "code": code,
                "filename": "model.py",
            }
        )

    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


def _export_zip(graph, code, request):
    """Create a zip file containing model.py and dataset files."""
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add the generated model.py
        zf.writestr("model.py", code)

        # Find InputDataNode and add dataset if available
        input_node = next(
            (n for n in graph.get("nodes", []) if n["type"] == "input-data"),
            None,
        )

        if input_node and input_node.get("datasetId"):
            dataset_id = input_node["datasetId"]
            try:
                from data_manager.models import Dataset
                from django.conf import settings
                import os

                # Query by the custom dataset_id field
                dataset = Dataset.objects.get(dataset_id=dataset_id)

                if dataset.file and dataset.file.name:
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
                            f"Dataset file not found at: {file_path}\n"
                            f"Please download the dataset separately from SketchNet.\n",
                        )
                else:
                    zf.writestr("data/README.txt", "Dataset has no file attached.\n")

            except ImportError:
                zf.writestr("data/README.txt", "Cannot import Dataset model.\n")
            except Dataset.DoesNotExist:
                zf.writestr(
                    "data/README.txt", f"Dataset with ID '{dataset_id}' not found.\n"
                )
            except Exception as e:
                zf.writestr("data/README.txt", f"Error accessing dataset: {str(e)}\n")
        else:
            # No dataset selected — add a placeholder
            zf.writestr(
                "data/README.txt",
                "No dataset selected in the model.\n"
                "Add your dataset to the 'data/' folder and update load_data() in model.py\n",
            )

        # Add requirements.txt
        zf.writestr(
            "requirements.txt",
            "torch>=2.0.0\nnumpy>=1.24.0\nmatplotlib>=3.7.0\npandas>=2.0.0\n",
        )

    zip_buffer.seek(0)
    response = HttpResponse(zip_buffer.getvalue(), content_type="application/zip")
    response["Content-Disposition"] = 'attachment; filename="model.zip"'
    return response


@login_required
@csrf_exempt
def validate_api(request):
    """API endpoint for graph validation."""
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST required"}, status=405)

    try:
        data = json.loads(request.body)
        graph_json = data.get("graph", "{}")

        if isinstance(graph_json, str):
            graph = json.loads(graph_json)
        else:
            graph = graph_json

        from .codegen.validator import GraphValidator
        validator = GraphValidator(graph)
        result = validator.validate()

        return JsonResponse({
            "success": True,
            "errors": result["errors"],
            "warnings": result["warnings"],
            "isValid": len(result["errors"]) == 0,
        })

    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)