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

    def test_block_restores_the_indent(self):
        """A block indents its body and cannot leave the indent dangling."""
        w = CodeWriter()
        with w.block("def foo():"):
            w.line("pass")
        w.line("foo()")
        self.assertEqual(str(w), "def foo():\n    pass\nfoo()")

    def test_nested_blocks(self):
        """Verify nested blocks."""
        w = CodeWriter()
        with w.block("for x in xs:"):
            with w.block("if x:"):
                w.line("print(x)")
        self.assertEqual(str(w), "for x in xs:\n    if x:\n        print(x)")

    def test_blank_collapses_trailing_whitespace(self):
        """Verify blank."""
        w = CodeWriter()
        w.line("a")
        w.blank()
        w.blank(2)
        w.line("b")
        self.assertEqual(str(w), "a\n\n\nb")
