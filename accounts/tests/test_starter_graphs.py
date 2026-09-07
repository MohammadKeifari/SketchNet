from types import SimpleNamespace

from django.test import SimpleTestCase

from accounts.seed.graphs import (
    attach_dataset,
    digits_cnn,
    linear_classifier,
    linear_regressor,
    mlp_classifier,
    mlp_regressor,
    skip_classifier,
    validate_graph,
)


def _dataset(dataset_id="Ab12Cd34", name="Demo", shape="(100, 5)"):
    return SimpleNamespace(
        dataset_id=dataset_id,
        name=name,
        resolved_shape=shape,
    )


class StarterGraphTests(SimpleTestCase):
    def test_linear_regressor_valid(self):
        graph = attach_dataset(linear_regressor(10), _dataset(shape="(442, 11)"))
        self.assertEqual(validate_graph(graph), [])

    def test_linear_classifier_valid(self):
        graph = attach_dataset(
            linear_classifier(30, 2), _dataset(shape="(569, 31)")
        )
        self.assertEqual(validate_graph(graph), [])

    def test_mlp_classifier_valid(self):
        graph = attach_dataset(mlp_classifier(4, 3, hidden=16), _dataset())
        self.assertEqual(validate_graph(graph), [])
        hidden = next(n for n in graph["nodes"] if n["id"] == "hidden")
        self.assertEqual(hidden["numNeurons"], 16)
        self.assertEqual(hidden["activation"], "relu")

    def test_mlp_regressor_valid(self):
        graph = attach_dataset(mlp_regressor(10, hidden=32), _dataset(shape="(400, 11)"))
        self.assertEqual(validate_graph(graph), [])
        hidden = next(n for n in graph["nodes"] if n["id"] == "hidden")
        self.assertEqual(hidden["activation"], "relu")

    def test_digits_cnn_valid(self):
        graph = attach_dataset(digits_cnn(), _dataset(shape="(1797, 65)"))
        self.assertEqual(validate_graph(graph), [])
        reshape = next(n for n in graph["nodes"] if n["id"] == "reshape")
        self.assertEqual(reshape["targetShape"], "(-1, 1, 8, 8)")

    def test_skip_classifier_valid(self):
        graph = attach_dataset(skip_classifier(13, 3), _dataset(shape="(178, 14)"))
        self.assertEqual(validate_graph(graph), [])

    def test_attach_dataset_sets_input_fields(self):
        ds = _dataset(dataset_id="irisIris", name="Iris")
        graph = attach_dataset(mlp_classifier(4, 3), ds)
        node = next(n for n in graph["nodes"] if n["type"] == "input-data")
        self.assertEqual(node["datasetId"], "irisIris")
        self.assertEqual(node["datasetName"], "Iris")
        self.assertEqual(node["dataShape"], "(100, 5)")
        self.assertNotIn("datasetFile", node)

    def test_attach_dataset_sets_file_fields(self):
        ds = SimpleNamespace(
            dataset_id="iris",
            name="Iris",
            resolved_shape="(150, 5)",
            dataset_file="iris.csv",
            format="csv",
        )
        graph = attach_dataset(mlp_classifier(4, 3), ds)
        node = next(n for n in graph["nodes"] if n["type"] == "input-data")
        self.assertEqual(node["datasetFile"], "iris.csv")
        self.assertEqual(node["datasetFormat"], "csv")
        self.assertEqual(node["dataShape"], "(150, 5)")
