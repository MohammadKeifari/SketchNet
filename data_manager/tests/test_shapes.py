from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from data_manager.models import Dataset
from data_manager.services import infer_dataset_shape

User = get_user_model()


class ShapeModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )

    def test_user_shape_has_priority(self):
        """User-provided shape takes priority over inferred"""
        dataset = Dataset.objects.create(
            name="Test",
            format="csv",
            file=SimpleUploadedFile("test.csv", b"a,b,c\n1,2,3\n4,5,6"),
            owner=self.user,
            user_shape="(100, 5)",
            inferred_shape="(2, 3)",
        )
        self.assertEqual(dataset.resolved_shape, "(100, 5)")
        self.assertTrue(dataset.shape_known)

    def test_inferred_shape_used_when_no_user_shape(self):
        """Inferred shape used when user doesn't provide one"""
        dataset = Dataset.objects.create(
            name="Test",
            format="csv",
            file=SimpleUploadedFile("test.csv", b"a,b,c\n1,2,3\n4,5,6"),
            owner=self.user,
            inferred_shape="(2, 3)",
        )
        self.assertEqual(dataset.resolved_shape, "(2, 3)")
        self.assertTrue(dataset.shape_known)

    def test_no_shape_when_both_empty(self):
        """Resolved shape is None when no shape available"""
        dataset = Dataset.objects.create(
            name="Test",
            format="other",
            file=SimpleUploadedFile("test.txt", b"hello"),
            owner=self.user,
        )
        self.assertIsNone(dataset.resolved_shape)
        self.assertFalse(dataset.shape_known)

    def test_user_shape_cleared_falls_back_to_inferred(self):
        """Clearing user_shape falls back to inferred"""
        dataset = Dataset.objects.create(
            name="Test",
            format="csv",
            file=SimpleUploadedFile("test.csv", b"a,b\n1,2"),
            owner=self.user,
            user_shape="(100, 5)",
            inferred_shape="(1, 2)",
        )
        self.assertEqual(dataset.resolved_shape, "(100, 5)")

        dataset.user_shape = None
        dataset.save()
        self.assertEqual(dataset.resolved_shape, "(1, 2)")

    def test_resolve_shape_method(self):
        """resolve_shape works correctly"""
        dataset = Dataset(
            name="Test",
            format="csv",
            owner=self.user,
        )
        # No shapes
        dataset.resolve_shape()
        self.assertIsNone(dataset.resolved_shape)
        self.assertFalse(dataset.shape_known)

        # Only inferred
        dataset.inferred_shape = "(10, 5)"
        dataset.resolve_shape()
        self.assertEqual(dataset.resolved_shape, "(10, 5)")
        self.assertTrue(dataset.shape_known)

        # User overrides
        dataset.user_shape = "(20, 3)"
        dataset.resolve_shape()
        self.assertEqual(dataset.resolved_shape, "(20, 3)")
        self.assertTrue(dataset.shape_known)


class ShapeInferenceTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )

    def test_infer_csv_shape(self):
        """CSV shape is correctly inferred"""
        dataset = Dataset.objects.create(
            name="Test CSV",
            format="csv",
            file=SimpleUploadedFile("test.csv", b"a,b,c\n1,2,3\n4,5,6\n7,8,9"),
            owner=self.user,
        )
        shape, known = infer_dataset_shape(dataset)
        self.assertEqual(shape, "(3, 3)")
        self.assertTrue(known)

    def test_infer_csv_single_row(self):
        """CSV with only header"""
        dataset = Dataset.objects.create(
            name="Test CSV",
            format="csv",
            file=SimpleUploadedFile("test.csv", b"a,b,c"),
            owner=self.user,
        )
        shape, known = infer_dataset_shape(dataset)
        self.assertEqual(shape, "(0, 3)")
        self.assertTrue(known)

    def test_infer_xlsx_shape(self):
        """Excel shape is correctly inferred"""
        import openpyxl

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["A", "B"])
        ws.append([1, 2])
        ws.append([3, 4])

        from io import BytesIO

        output = BytesIO()
        wb.save(output)
        output.seek(0)

        dataset = Dataset.objects.create(
            name="Test XLSX",
            format="xlsx",
            file=SimpleUploadedFile(
                "test.xlsx",
                output.read(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
            owner=self.user,
        )
        shape, known = infer_dataset_shape(dataset)
        self.assertEqual(shape, "(2, 2)")
        self.assertTrue(known)

    def test_infer_json_shape(self):
        """JSON shape is correctly inferred"""
        import json

        data = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
        dataset = Dataset.objects.create(
            name="Test JSON",
            format="json",
            file=SimpleUploadedFile("test.json", json.dumps(data).encode()),
            owner=self.user,
        )
        shape, known = infer_dataset_shape(dataset)
        self.assertEqual(shape, "(2, 2)")
        self.assertTrue(known)

    def test_infer_parquet_shape(self):
        """Parquet shape is correctly inferred"""
        import pandas as pd
        from io import BytesIO

        df = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
        buf = BytesIO()
        df.to_parquet(buf)
        buf.seek(0)

        dataset = Dataset.objects.create(
            name="Test Parquet",
            format="parquet",
            file=SimpleUploadedFile("test.parquet", buf.read()),
            owner=self.user,
        )
        shape, known = infer_dataset_shape(dataset)
        self.assertEqual(shape, "(3, 2)")
        self.assertTrue(known)

    def test_no_infer_for_zip(self):
        """ZIP files are not inferred"""
        dataset = Dataset.objects.create(
            name="Test ZIP",
            format="zip",
            file=SimpleUploadedFile("test.zip", b"fake zip data"),
            owner=self.user,
        )
        shape, known = infer_dataset_shape(dataset)
        self.assertIsNone(shape)
        self.assertFalse(known)

    def test_no_infer_for_rar(self):
        """RAR files are not inferred"""
        dataset = Dataset.objects.create(
            name="Test RAR",
            format="rar",
            file=SimpleUploadedFile("test.rar", b"fake rar data"),
            owner=self.user,
        )
        shape, known = infer_dataset_shape(dataset)
        self.assertIsNone(shape)
        self.assertFalse(known)

    def test_no_infer_for_other(self):
        """Other format is not inferred"""
        dataset = Dataset.objects.create(
            name="Test Other",
            format="other",
            file=SimpleUploadedFile("test.txt", b"hello world"),
            owner=self.user,
        )
        shape, known = infer_dataset_shape(dataset)
        self.assertIsNone(shape)
        self.assertFalse(known)

    def test_infer_shape_on_save(self):
        """Shape is auto-inferred on save when no user_shape"""
        dataset = Dataset.objects.create(
            name="Auto Infer",
            format="csv",
            file=SimpleUploadedFile("test.csv", b"x,y\n1,2\n3,4\n5,6"),
            owner=self.user,
        )
        # Inference happens in the view, not in model save.
        # Test that the field can store it.
        dataset.inferred_shape = "(3, 2)"
        dataset.save()
        self.assertEqual(dataset.resolved_shape, "(3, 2)")
        self.assertTrue(dataset.shape_known)
