"""
Indented code buffer used by the emitter.

``block`` is the preferred way to open a suite: it re-indents for the duration
of the ``with`` statement, so an indent can never be left dangling.
"""

from contextlib import contextmanager


class CodeWriter:
    """Accumulates lines of Python source with automatic indentation."""

    def __init__(self):
        self.lines = []
        self._indent = 0

    def indent(self):
        self._indent += 1

    def dedent(self):
        self._indent = max(0, self._indent - 1)

    @contextmanager
    def block(self, header: str):
        """Write ``header`` and indent everything emitted inside the ``with``."""
        self.line(header)
        self.indent()
        try:
            yield self
        finally:
            self.dedent()

    def line(self, text: str = ""):
        self.lines.append(("    " * self._indent + text) if text else "")

    def extend(self, texts):
        for text in texts:
            self.line(text)

    def blank(self, count: int = 1):
        """Ensure the buffer ends with exactly ``count`` blank lines."""
        if not self.lines:
            return
        while self.lines and self.lines[-1] == "":
            self.lines.pop()
        self.lines.extend([""] * count)

    def __str__(self):
        return "\n".join(self.lines)
