import unittest

from sketchmod.codegen.sanitize import py_string_literal, safe_filename, safe_slice_expr


class SanitizeTest(unittest.TestCase):
    def test_py_string_literal_escapes_quotes(self):
        self.assertEqual(py_string_literal('a"b'), '"a\\"b"')

    def test_safe_filename_rejects_traversal(self):
        self.assertIsNone(safe_filename("../etc/passwd"))
        self.assertEqual(safe_filename("model20.csv"), "model20.csv")

    def test_safe_slice_expr_allows_ranges(self):
        self.assertEqual(safe_slice_expr("0:5"), "0:5")
        self.assertIsNone(safe_slice_expr("0; import os"))


if __name__ == "__main__":
    unittest.main()
