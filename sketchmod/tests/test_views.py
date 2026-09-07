import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from models_library.models import SketchModel

User = get_user_model()

# Minimal graph that passes validation (no errors, only warnings)
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
    "ports": [],
    "nodeCounter": 2,
}


class ViewsTest(TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.owner = User.objects.create_user(
            username="owner", email="owner@example.com", password="testpass123"
        )
        self.public_model = SketchModel.objects.create(
            name="Public Model",
            graph_data={"nodes": [], "links": [], "ports": [], "nodeCounter": 0},
            owner=self.owner,
            view_access="public",
        )
        self.private_model = SketchModel.objects.create(
            name="Private Model",
            graph_data={"nodes": [], "links": [], "ports": [], "nodeCounter": 0},
            owner=self.owner,
            view_access="private",
        )
        # URLs
        self.canvas_url = reverse("sketchmod:canvas")
        self.export_url = reverse("sketchmod:export_api")
        self.validate_url = reverse("sketchmod:validate_api")
        self.highlight_url = reverse("sketchmod:highlight_path_api")

    # ---------- Canvas ----------
    def test_canvas_requires_login(self):
        """Blank canvas requires login."""
        response = self.client.get(self.canvas_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_canvas_anonymous_readonly_public(self):
        """Anonymous users can view public models in read-only mode."""
        url = f"{self.canvas_url}?load={self.public_model.model_id}&readonly=1"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["readonly"])
        self.assertContains(response, "Viewing public model")

    def test_canvas_anonymous_private_readonly_denied(self):
        """Anonymous users cannot view private models."""
        url = f"{self.canvas_url}?load={self.private_model.model_id}&readonly=1"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_canvas_authenticated(self):
        """Verify canvas authenticated."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(self.canvas_url)
        self.assertEqual(response.status_code, 200)

    def test_canvas_owner_load_without_readonly(self):
        """Logged-in owner can open edit mode without readonly flag."""
        self.client.login(username="owner", password="testpass123")
        url = f"{self.canvas_url}?load={self.public_model.model_id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["readonly"])

    # ---------- Export API ----------
    def test_export_unauthenticated(self):
        """Anonymous users can export valid graphs."""
        graph_str = json.dumps(VALID_GRAPH)
        response = self.client.post(
            self.export_url,
            data=json.dumps({"graph": graph_str, "format": "pytorch-py"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

    def test_export_valid_graph(self):
        """Verify export valid graph."""
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

    def test_export_does_not_leak_internal_errors(self):
        """Unexpected export failures return a generic message."""
        self.client.login(username="testuser", password="testpass123")
        payload = {"graph": {"nodes": "not-a-list"}}
        response = self.client.post(
            self.export_url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertIn(response.status_code, (400, 500))
        self.assertNotIn("Traceback", response.content.decode())

    def test_export_invalid_json(self):
        """Verify export invalid json."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(
            self.export_url, data="not json", content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_export_rejects_invalid_graph(self):
        """Export requires a valid graph."""
        self.client.login(username="testuser", password="testpass123")
        invalid = {"nodes": [], "links": [], "ports": []}
        response = self.client.post(
            self.export_url,
            data=json.dumps({"graph": json.dumps(invalid), "format": "pytorch-py"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])

    # ---------- Validate API ----------
    def test_validate_unauthenticated(self):
        """Anonymous users can validate graphs."""
        response = self.client.post(
            self.validate_url,
            data=json.dumps({"graph": json.dumps(VALID_GRAPH)}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

    def test_validate_valid_graph(self):
        """Verify validate valid graph."""
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
        # With no optimizer we get a warning but no errors
        self.assertTrue(data["isValid"])
        self.assertEqual(len(data["errors"]), 0)
        self.assertGreaterEqual(len(data["warnings"]), 1)

    def test_validate_missing_optimizer_warning(self):
        """Validator warns about missing optimizer."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(
            self.validate_url,
            data=json.dumps({"graph": json.dumps(VALID_GRAPH)}),
            content_type="application/json",
        )
        data = response.json()
        warnings = data["warnings"]
        self.assertTrue(any("No optimizer node" in w["message"] for w in warnings))

    def test_validate_optimizer_wrong_phase_error(self):
        """Validator reports error if optimizer is not in training phase."""
        graph = json.loads(json.dumps(VALID_GRAPH))
        # add optimizer node in preprocessing
        opt_node = {
            "id": "opt",
            "type": "optimizer",
            "x": 0,
            "y": 0,
            "inputPorts": [
                {
                    "id": "opt_input_0",
                    "type": "input",
                    "index": 0,
                    "subType": None,
                    "shape": None,
                    "bias": 0,
                    "portKind": "role",
                    "activationPhases": ["preprocessing"],
                    "role": "loss",
                },
                {
                    "id": "opt_input_1",
                    "type": "input",
                    "index": 1,
                    "subType": None,
                    "shape": None,
                    "bias": 0,
                    "portKind": "role",
                    "activationPhases": ["preprocessing"],
                    "role": "labels",
                },
            ],
            "outputPorts": [],
            "numInputs": 2,
            "numOutputs": 0,
            "bias": 0,
            "hasBias": False,
            "paramInputs": [],
            "paramOutputs": [],
            "numParamInputs": 0,
            "numParamOutputs": 0,
            "lossType": "mse",
            "optimizerType": "adam",
            "learningRate": 0.001,
        }
        graph["nodes"].append(opt_node)
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(
            self.validate_url,
            data=json.dumps({"graph": json.dumps(graph)}),
            content_type="application/json",
        )
        data = response.json()
        self.assertFalse(data["isValid"])
        errors = data["errors"]
        self.assertTrue(any(e["code"] == "optimizer-not-training" for e in errors))

    # ---------- Highlight Path API ----------
    def test_highlight_unauthenticated(self):
        """Anonymous users can highlight paths."""
        response = self.client.post(
            self.highlight_url,
            data=json.dumps(
                {"graph": json.dumps(VALID_GRAPH), "phase": "preprocessing"}
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

    def test_highlight_valid(self):
        """Verify highlight valid."""
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

    # ---------- Dataset Columns API ----------
    def test_dataset_columns_nonexistent(self):
        """Verify dataset columns nonexistent."""
        url = reverse("sketchmod:api_dataset_columns", args=["nonexist"])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    # ---------- Starter templates ----------
    def test_template_load_known_slug(self):
        """A known Learn template is stored on the session and redirects to canvas."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(
            reverse("sketchmod:template_load", args=["linear-regression"])
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("sketchmod:canvas"))
        graph = self.client.session.get("template_graph")
        self.assertIsInstance(graph, dict)
        self.assertTrue(any(node.get("type") == "input-data" for node in graph["nodes"]))
        self.assertNotIn("template_error", self.client.session)

    def test_template_load_unknown_slug(self):
        """An unknown slug records a template error and does not store a graph."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(
            reverse("sketchmod:template_load", args=["does-not-exist"])
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("sketchmod:canvas"))
        self.assertNotIn("template_graph", self.client.session)
        self.assertEqual(
            self.client.session.get("template_error"),
            "Template 'does-not-exist' not found.",
        )

    def test_template_load_rejects_dotdot_slug(self):
        """Path-like template slugs are rejected without filesystem lookup."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(
            reverse("sketchmod:template_load", args=[".."])
        )
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("template_graph", self.client.session)
        self.assertEqual(
            self.client.session.get("template_error"),
            "Template '..' not found.",
        )
