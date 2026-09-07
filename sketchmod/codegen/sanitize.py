"""
Escape user-controlled graph properties before they are written into Python source.
"""

import re

_SLICE_RE = re.compile(
    r"^(\d+|\s*:\s*|\d+\s*:\s*|\s*:\s*\d+|\d+\s*:\s*\d+|\d+\s*,\s*\d+)*$"
    r"|^(\d+|\d+\s*,\s*\d+)*$"
)

_FILENAME_RE = re.compile(r"^[\w.\-]+$")


def py_string_literal(value: str) -> str:
    """Return a safe double-quoted Python string literal."""
    text = str(value or "")
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def safe_slice_expr(text: str) -> str | None:
    """Return slice text if it matches a strict allow-list, else None."""
    cleaned = str(text or "").strip()
    if not cleaned:
        return None
    if not _SLICE_RE.match(cleaned):
        return None
    return cleaned


def safe_dim_slice(text: str) -> str | None:
    """Allow : or a non-negative integer per dimension slice token."""
    cleaned = str(text or "").strip()
    if not cleaned or cleaned == ":":
        return ":"
    if cleaned.isdigit():
        return cleaned
    if _SLICE_RE.match(cleaned):
        return cleaned
    return None


def safe_filename(name: str) -> str | None:
    """Basename-only filename without path traversal or quotes."""
    cleaned = str(name or "").strip()
    if not cleaned or ".." in cleaned or "/" in cleaned or "\\" in cleaned:
        return None
    basename = cleaned.replace("\\", "/").split("/")[-1]
    if not basename or basename in (".", ".."):
        return None
    if not _FILENAME_RE.match(basename):
        return None
    return basename
