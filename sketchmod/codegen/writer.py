"""
Code writer utility for generating indented Python code.

This module provides a simple utility class for building multi-line Python code
with proper indentation management. It's used throughout the code generation
process to construct the generated training script.
"""


class CodeWriter:
    """
    Manages writing Python code with automatic indentation.
    
    This utility tracks the current indentation level and formats lines accordingly.
    It's particularly useful for generating code with nested blocks (classes, functions,
    control structures) where indentation must be maintained correctly.
    
    Attributes:
        lines (List[str]): List of code lines accumulated so far.
        _indent (int): Current indentation level (number of 4-space indents).
    """
    def __init__(self):
        """Initialize the code writer with empty lines and zero indentation."""
        self.lines = []
        self._indent = 0

    def indent(self):
        """Increase the indentation level by one (adds 4 spaces per level)."""
        self._indent += 1

    def dedent(self):
        """Decrease the indentation level by one (minimum 0)."""
        if self._indent > 0:
            self._indent -= 1

    def line(self, text=""):
        """
        Append a line of code with current indentation.
        
        Args:
            text (str): The code line to add. If empty, adds a blank line. Defaults to "".
        """
        self.lines.append("    " * self._indent + text)

    def __str__(self):
        """
        Get the complete generated code as a single string.
        
        Returns:
            str: All accumulated lines joined by newlines.
        """
        return "\n".join(self.lines)

