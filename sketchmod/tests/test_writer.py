from django.test import SimpleTestCase
from sketchmod.codegen.writer import CodeWriter


class CodeWriterTests(SimpleTestCase):

    def test_empty_writer(self):
        w = CodeWriter()
        self.assertEqual(str(w), "")

    def test_single_line(self):
        w = CodeWriter()
        w.line("import torch")
        self.assertEqual(str(w), "import torch")

    def test_indentation(self):
        w = CodeWriter()
        w.line("def foo():")
        w.indent()
        w.line("x = 1")
        w.line("return x")
        w.dedent()
        w.line("")
        w.line("foo()")
        expected = "def foo():\n    x = 1\n    return x\n\nfoo()"
        self.assertEqual(str(w), expected)

    def test_nested_indent(self):
        w = CodeWriter()
        w.line("class A:")
        w.indent()
        w.line("def b(self):")
        w.indent()
        w.line("pass")
        w.dedent()
        w.dedent()
        expected = "class A:\n    def b(self):\n        pass"
        self.assertEqual(str(w), expected)

    def test_empty_lines_preserved(self):
        w = CodeWriter()
        w.line("a = 1")
        w.line("")
        w.line("b = 2")
        expected = "a = 1\n\nb = 2"
        self.assertEqual(str(w), expected)

    def test_multiple_dedent_safe(self):
        w = CodeWriter()
        w.indent()
        w.dedent()
        w.dedent()  # Should not go negative
        w.line("x = 1")
        self.assertEqual(str(w), "x = 1")
