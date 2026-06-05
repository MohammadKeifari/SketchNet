from django.test import SimpleTestCase
from sketchmod.codegen.writer import CodeWriter


class CodeWriterTest(SimpleTestCase):
    def test_empty_writer(self):
        """Verify empty writer."""
        w = CodeWriter()
        self.assertEqual(str(w), "")

    def test_single_line(self):
        """Verify single line."""
        w = CodeWriter()
        w.line("hello")
        self.assertEqual(str(w), "hello")

    def test_indentation(self):
        """Verify indentation."""
        w = CodeWriter()
        w.line("def foo():")
        w.indent()
        w.line("pass")
        w.dedent()
        w.line("foo()")
        expected = "def foo():\n    pass\nfoo()"
        self.assertEqual(str(w), expected)

    def test_nested_indent(self):
        """Verify nested indent."""
        w = CodeWriter()
        w.line("a")
        w.indent()
        w.line("b")
        w.indent()
        w.line("c")
        w.dedent()
        w.line("d")
        w.dedent()
        w.line("e")
        expected = "a\n    b\n        c\n    d\ne"
        self.assertEqual(str(w), expected)
