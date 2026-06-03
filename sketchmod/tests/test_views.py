import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()

# Minimal valid graph JSON that the validator and exporter can process
VALID_GRAPH = {
    "nodes": [
        {
            "id": "input-main",
            "type": "input-data",
            "x": 100,
            "y": 100,
            "inputPorts": [],
            "outputPorts": [
                {
                    "id": "input-main_output_0",
                    "type": "output",
                    "index": 0,
                    "subType": None,
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["preprocessing"],
                }
            ],
            "numInputs": 0,
            "numOutputs": 1,
            "bias": 0,
            "hasBias": False,
            "paramInputs": [],
            "paramOutputs": [],
            "numParamInputs": 0,
            "numParamOutputs": 0,
            "datasetId": None,
            "datasetName": None,
            "dataShape": None,
        },
        {
            "id": "output-main",
            "type": "output",
            "x": 300,
            "y": 100,
            "inputPorts": [
                {
                    "id": "output-main_input_0",
                    "type": "input",
                    "index": 0,
                    "subType": "train",
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["training"],
                },
                {
                    "id": "output-main_input_1",
                    "type": "input",
                    "index": 1,
                    "subType": "test",
                    "shape": None,
                    "bias": 0,
                    "portKind": "data",
                    "activationPhases": ["evaluation"],
                },
            ],
            "outputPorts": [
                {
                    "id": "output-main_output_0",
                    "type": "output",
                    "index": 0,
                    "subType": None,
                    "shape": None,
                    "bias": 0,
                    "portKind": "role",
                    "activationPhases": ["training"],
                    "role": "loss",
                },
                {
                    "id": "output-main_output_1",
                    "type": "output",
                    "index": 1,
                    "subType": None,
                    "shape": None,
                    "bias": 0,
                    "portKind": "role",
                    "activationPhases": ["evaluation"],
                    "role": "prediction",
                },
                {
                    "id": "output-main_output_2",
                    "type": "output",
                    "index": 2,
                    "subType": None,
                    "shape": None,
                    "bias": 0,
                    "portKind": "role",
                    "activationPhases": ["evaluation"],
                    "role": "evaluation",
                },
            ],
            "numInputs": 2,
            "numOutputs": 3,
            "bias": 0,
            "hasBias": False,
            "paramInputs": [],
            "paramOutputs": [],
            "numParamInputs": 0,
            "numParamOutputs": 0,
        },
    ],
    "links": [],
    "ports": [],  # will be populated by canvas.js normally, but backend doesn't require ports array for validation
    "nodeCounter": 2,
}


class ViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        # URLs
        self.canvas_url = reverse("sketchmod:canvas")
        self.export_url = reverse("sketchmod:export_api")
        self.validate_url = reverse("sketchmod:validate_api")
        self.highlight_url = reverse("sketchmod:highlight_path_api")

    # ---------- Canvas View ----------
    def test_canvas_requires_login(self):
        response = self.client.get(self.canvas_url)
        self.assertEqual(response.status_code, 302)  # redirect to login

    def test_canvas_authenticated(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(self.canvas_url)
        self.assertEqual(response.status_code, 200)

    # ---------- Export API ----------
    def test_export_unauthenticated(self):
        response = self.client.post(
            self.export_url, {}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 302)

    def test_export_valid_graph(self):
        self.client.login(username="testuser", password="testpass123")
        graph_str = json.dumps(VALID_GRAPH)
        response = self.client.post(
            self.export_url,
            data=json.dumps({"graph": graph_str, "format": "pytorch-py"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("code", data)
        self.assertIn("filename", data)

    def test_export_invalid_json(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(
            self.export_url, data="not json", content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    # ---------- Validate API ----------
    def test_validate_unauthenticated(self):
        response = self.client.post(
            self.validate_url, {}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 302)

    def test_validate_valid_graph(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(
            self.validate_url,
            data=json.dumps({"graph": json.dumps(VALID_GRAPH)}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("errors", data)
        self.assertIn("warnings", data)
        self.assertIn("isValid", data)

    def test_validate_missing_optimizer_warning(self):
        """Validator should warn about missing optimizer."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(
            self.validate_url,
            data=json.dumps({"graph": json.dumps(VALID_GRAPH)}),
            content_type="application/json",
        )
        data = response.json()
        errors = data["errors"]
        self.assertTrue(
            any("Optimizer node is required" in e["message"] for e in errors)
        )

    # ---------- Highlight Path API ----------
    def test_highlight_unauthenticated(self):
        response = self.client.post(
            self.highlight_url, {}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 302)

    def test_highlight_valid(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(
            self.highlight_url,
            data=json.dumps(
                {"graph": json.dumps(VALID_GRAPH), "phase": "preprocessing"}
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("nodes", data)
        self.assertIn("links", data)

    # ---------- Dataset Columns API (public) ----------
    def test_dataset_columns_nonexistent(self):
        url = reverse("sketchmod:api_dataset_columns", args=["nonexist"])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
