class CodeWriter:
    def __init__(self):
        self.lines = []
        self._indent = 0

    def indent(self):
        self._indent += 1

    def dedent(self):
        if self._indent > 0:
            self._indent -= 1

    def line(self, text=""):
        self.lines.append("    " * self._indent + text)

    def __str__(self):
        return "\n".join(self.lines)
