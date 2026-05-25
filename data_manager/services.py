import os
from django.core.exceptions import ValidationError
import pandas as pd

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB


def validate_file_size(file):
    """Validate file is within size limit"""
    if file.size > MAX_UPLOAD_SIZE:
        size_mb = MAX_UPLOAD_SIZE / (1024 * 1024)
        raise ValidationError(f"File size must be under {size_mb:.0f}MB.")


def validate_file_extension(file, allowed_formats):
    """Validate file extension matches allowed formats"""
    ext = os.path.splitext(file.name)[1].lower().lstrip(".")
    if ext not in allowed_formats:
        raise ValidationError(
            f"File type .{ext} is not supported. Allowed: {', '.join(allowed_formats)}"
        )


# Map format choices to allowed extensions
FORMAT_EXTENSIONS = {
    "csv": ["csv"],
    "json": ["json"],
    "xlsx": ["xlsx"],
    "parquet": ["parquet"],
    "rar": ["rar"],
    "zip": ["zip"],
    "other": [
        "csv",
        "json",
        "xlsx",
        "parquet",
        "rar",
        "zip",
        "txt",
        "jpg",
        "png",
        "pdf",
    ],
}


def infer_dataset_shape(dataset):
    """
    Try to infer the shape of a dataset from its file.
    Returns (shape_string, known) or (None, False) if can't determine.
    """
    if dataset.format == "other":
        return None, False

    file_path = dataset.file.path

    try:
        if dataset.format == "csv":
            # Read just the header to get column count, then count rows
            df_header = pd.read_csv(file_path, nrows=0)
            col_count = len(df_header.columns)
            # Count total rows (skip header)
            with open(file_path, "r") as f:
                row_count = sum(1 for _ in f) - 1  # Subtract header
            return f"({row_count}, {col_count})", True

        elif dataset.format == "xlsx":
            df = pd.read_excel(file_path)
            return f"({df.shape[0]}, {df.shape[1]})", True

        elif dataset.format == "json":
            df = pd.read_json(file_path)
            if isinstance(df, pd.DataFrame):
                return f"({df.shape[0]}, {df.shape[1]})", True
            return None, False

        elif dataset.format == "parquet":
            df = pd.read_parquet(file_path)
            return f"({df.shape[0]}, {df.shape[1]})", True

        elif dataset.format in ("zip", "rar"):
            return None, False

    except Exception:
        return None, False
