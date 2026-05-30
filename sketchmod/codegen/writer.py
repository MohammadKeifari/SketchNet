class CodeWriter:
    """Helper for generating indented Python code."""

    def __init__(self):
        self.lines = []
        self._indent = 0

    def indent(self):
        self._indent += 1

    def dedent(self):
        self._indent = max(0, self._indent - 1)

    def line(self, text=""):
        if text:
            self.lines.append("    " * self._indent + text)
        else:
            self.lines.append("")

    def __str__(self):
        return "\n".join(self.lines)
