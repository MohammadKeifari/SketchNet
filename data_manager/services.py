import os
from django.core.exceptions import ValidationError

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
