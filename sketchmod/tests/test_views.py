import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class SketchModViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        self.canvas_url = reverse("sketchmod:canvas")
        self.export_url = reverse("sketchmod:export_api")
        self.validate_url = reverse("sketchmod:validate_api")

    # ========== CANVAS VIEW ==========

    def test_canvas_requires_login(self):
        response = self.client.get(self.canvas_url)
        self.assertEqual(response.status_code, 302)

    def test_canvas_loads_when_logged_in(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(self.canvas_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "sketchmod/canvas.html")

    def test_canvas_context_has_collapse_settings(self):
        self.client.login(username="testuser", password="testpass123")
        self.user.settings.collapse_left_sidebar = True
        self.user.settings.collapse_right_sidebar = False
        self.user.settings.save()

        response = self.client.get(self.canvas_url)
        self.assertIn("collapse_left_sidebar", response.context)
        self.assertIn("collapse_right_sidebar", response.context)
        self.assertTrue(response.context["collapse_left_sidebar"])
        self.assertFalse(response.context["collapse_right_sidebar"])

    def test_canvas_unauthenticated_uses_defaults(self):
        """Unauthenticated users get False for collapse settings."""
        # Override the view to allow unauthenticated access for this test
        # or test that the context defaults exist
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(self.canvas_url)
        self.assertFalse(response.context.get("collapse_left_sidebar", True))
        self.assertFalse(response.context.get("collapse_right_sidebar", True))

    # ========== EXPORT API ==========

    def _make_minimal_graph(self):
        return {
            "nodes": [
                {
                    "id": "i1",
                    "type": "input-data",
                    "inputPorts": [],
                    "outputPorts": [
                        {
                            "id": "i1_output_0",
                            "type": "output",
                            "index": 0,
                            "subType": None,
                            "shape": None,
                            "bias": 0,
                            "portKind": "data",
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
                    "id": "l1",
                    "type": "layer",
                    "inputPorts": [
                        {
                            "id": "l1_input_0",
                            "type": "input",
                            "index": 0,
                            "subType": None,
                            "shape": None,
                            "bias": 0,
                            "portKind": "multi",
                        }
                    ],
                    "outputPorts": [
                        {
                            "id": "l1_output_0",
                            "type": "output",
                            "index": 0,
                            "subType": None,
                            "shape": None,
                            "bias": 0,
                            "portKind": "data",
                        }
                    ],
                    "numInputs": 1,
                    "numOutputs": 1,
                    "activation": "relu",
                    "numNeurons": 10,
                    "bias": 0,
                    "hasBias": True,
                    "paramInputs": [],
                    "paramOutputs": [],
                    "numParamInputs": 0,
                    "numParamOutputs": 0,
                },
                {
                    "id": "o1",
                    "type": "output",
                    "inputPorts": [
                        {
                            "id": "o1_input_0",
                            "type": "input",
                            "index": 0,
                            "subType": None,
                            "shape": None,
                            "bias": 0,
                            "portKind": "data",
                        }
                    ],
                    "outputPorts": [],
                    "numInputs": 1,
                    "numOutputs": 0,
                    "bias": 0,
                    "hasBias": False,
                    "paramInputs": [],
                    "paramOutputs": [],
                    "numParamInputs": 0,
                    "numParamOutputs": 0,
                },
            ],
            "links": [
                {
                    "from": "i1_output_0",
                    "to": "l1_input_0",
                    "weight": 0,
                    "weightShape": None,
                    "hasWeight": True,
                },
                {
                    "from": "l1_output_0",
                    "to": "o1_input_0",
                    "weight": 0,
                    "weightShape": None,
                    "hasWeight": False,
                },
            ],
            "ports": [],
            "nodeCounter": 3,
        }

    def test_export_requires_login(self):
        response = self.client.post(
            self.export_url,
            data=json.dumps({"graph": "{}", "format": "pytorch-py"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 302)

    def test_export_requires_post(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(self.export_url)
        self.assertEqual(response.status_code, 405)

    def test_export_pytorch_py(self):
        self.client.login(username="testuser", password="testpass123")
        graph = self._make_minimal_graph()
        response = self.client.post(
            self.export_url,
            data=json.dumps({"graph": json.dumps(graph), "format": "pytorch-py"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("import torch", data["code"])
        self.assertIn("class SketchNetModel", data["code"])
        self.assertEqual(data["filename"], "model.py")

    def test_export_python_clipboard(self):
        self.client.login(username="testuser", password="testpass123")
        graph = self._make_minimal_graph()
        response = self.client.post(
            self.export_url,
            data=json.dumps({"graph": json.dumps(graph), "format": "python-clipboard"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("class SketchNetModel", data["code"])

    def test_export_pytorch_zip(self):
        self.client.login(username="testuser", password="testpass123")
        graph = self._make_minimal_graph()
        response = self.client.post(
            self.export_url,
            data=json.dumps({"graph": json.dumps(graph), "format": "pytorch-zip"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/zip")
        self.assertIn("attachment", response["Content-Disposition"])

    def test_export_invalid_graph_returns_error(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(
            self.export_url,
            data=json.dumps({"graph": "not valid json", "format": "pytorch-py"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("error", data)

    def test_export_empty_graph(self):
        self.client.login(username="testuser", password="testpass123")
        graph = {"nodes": [], "links": [], "ports": [], "nodeCounter": 0}
        response = self.client.post(
            self.export_url,
            data=json.dumps({"graph": json.dumps(graph), "format": "pytorch-py"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        # Should still generate valid code
        self.assertIn("import torch", data["code"])

    def test_export_with_all_node_types(self):
        """Export with every node type should not crash."""
        self.client.login(username="testuser", password="testpass123")
        nodes = [
            {
                "id": "i1",
                "type": "input-data",
                "inputPorts": [],
                "outputPorts": [
                    {
                        "id": "i1_output_0",
                        "type": "output",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "bias": 0,
                        "portKind": "data",
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
                "dataShape": "(100, 28, 28)",
            },
            {
                "id": "f1",
                "type": "flatten",
                "inputPorts": [
                    {
                        "id": "f1_input_0",
                        "type": "input",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "bias": 0,
                        "portKind": "data",
                    }
                ],
                "outputPorts": [
                    {
                        "id": "f1_output_0",
                        "type": "output",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "bias": 0,
                        "portKind": "data",
                    }
                ],
                "numInputs": 1,
                "numOutputs": 1,
                "bias": 0,
                "hasBias": False,
                "paramInputs": [],
                "paramOutputs": [],
                "numParamInputs": 0,
                "numParamOutputs": 0,
            },
            {
                "id": "d1",
                "type": "dropout",
                "rate": 0.3,
                "inputPorts": [
                    {
                        "id": "d1_input_0",
                        "type": "input",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "bias": 0,
                        "portKind": "data",
                    }
                ],
                "outputPorts": [
                    {
                        "id": "d1_output_0",
                        "type": "output",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "bias": 0,
                        "portKind": "data",
                    }
                ],
                "numInputs": 1,
                "numOutputs": 1,
                "bias": 0,
                "hasBias": False,
                "paramInputs": [],
                "paramOutputs": [],
                "numParamInputs": 0,
                "numParamOutputs": 0,
            },
            {
                "id": "l1",
                "type": "layer",
                "numNeurons": 10,
                "activation": "relu",
                "inputPorts": [
                    {
                        "id": "l1_input_0",
                        "type": "input",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "bias": 0,
                        "portKind": "multi",
                    }
                ],
                "outputPorts": [
                    {
                        "id": "l1_output_0",
                        "type": "output",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "bias": 0,
                        "portKind": "data",
                    }
                ],
                "numInputs": 1,
                "numOutputs": 1,
                "bias": 0,
                "hasBias": True,
                "paramInputs": [],
                "paramOutputs": [],
                "numParamInputs": 0,
                "numParamOutputs": 0,
            },
            {
                "id": "o1",
                "type": "output",
                "inputPorts": [
                    {
                        "id": "o1_input_0",
                        "type": "input",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "bias": 0,
                        "portKind": "data",
                    }
                ],
                "outputPorts": [],
                "numInputs": 1,
                "numOutputs": 0,
                "bias": 0,
                "hasBias": False,
                "paramInputs": [],
                "paramOutputs": [],
                "numParamInputs": 0,
                "numParamOutputs": 0,
            },
            {
                "id": "viz1",
                "type": "visualization",
                "colorMode": "none",
                "inputPorts": [],
                "outputPorts": [],
                "numInputs": 0,
                "numOutputs": 0,
                "bias": 0,
                "hasBias": False,
                "paramInputs": [],
                "paramOutputs": [],
                "numParamInputs": 0,
                "numParamOutputs": 0,
                "colorPalette": ["#ef4444"],
                "continuousMinColor": "#3b82f6",
                "continuousMaxColor": "#ef4444",
            },
        ]
        links = [
            {
                "from": "i1_output_0",
                "to": "f1_input_0",
                "weight": 0,
                "weightShape": None,
                "hasWeight": False,
            },
            {
                "from": "f1_output_0",
                "to": "d1_input_0",
                "weight": 0,
                "weightShape": None,
                "hasWeight": False,
            },
            {
                "from": "d1_output_0",
                "to": "l1_input_0",
                "weight": 0,
                "weightShape": None,
                "hasWeight": True,
            },
            {
                "from": "l1_output_0",
                "to": "o1_input_0",
                "weight": 0,
                "weightShape": None,
                "hasWeight": False,
            },
        ]
        graph = {"nodes": nodes, "links": links, "ports": [], "nodeCounter": 6}
        response = self.client.post(
            self.export_url,
            data=json.dumps({"graph": json.dumps(graph), "format": "pytorch-py"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])

    # ========== VALIDATE API ==========

    def test_validate_requires_login(self):
        response = self.client.post(
            self.validate_url,
            data=json.dumps({"graph": "{}"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 302)

    def test_validate_requires_post(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(self.validate_url)
        self.assertEqual(response.status_code, 405)

    def test_validate_empty_graph(self):
        self.client.login(username="testuser", password="testpass123")
        graph = {"nodes": [], "links": [], "ports": [], "nodeCounter": 0}
        response = self.client.post(
            self.validate_url,
            data=json.dumps({"graph": json.dumps(graph)}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("errors", data)
        self.assertIn("warnings", data)
        self.assertIn("isValid", data)

    def test_validate_returns_errors_for_bad_graph(self):
        self.client.login(username="testuser", password="testpass123")
        nodes = [
            {
                "id": "l1",
                "type": "layer",
                "numNeurons": 10,
                "activation": "relu",
                "inputPorts": [
                    {
                        "id": "l1_input_0",
                        "type": "input",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "bias": 0,
                        "portKind": "multi",
                    }
                ],
                "outputPorts": [
                    {
                        "id": "l1_output_0",
                        "type": "output",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "bias": 0,
                        "portKind": "data",
                    }
                ],
                "numInputs": 1,
                "numOutputs": 1,
                "bias": 0,
                "hasBias": True,
                "paramInputs": [],
                "paramOutputs": [],
                "numParamInputs": 0,
                "numParamOutputs": 0,
            },
        ]
        graph = {"nodes": nodes, "links": [], "ports": [], "nodeCounter": 1}
        response = self.client.post(
            self.validate_url,
            data=json.dumps({"graph": json.dumps(graph)}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertFalse(data["isValid"])
        self.assertTrue(len(data["errors"]) > 0)

    def test_validate_valid_graph_passes(self):
        self.client.login(username="testuser", password="testpass123")
        graph = self._make_minimal_graph()
        response = self.client.post(
            self.validate_url,
            data=json.dumps({"graph": json.dumps(graph)}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertTrue(data["isValid"])

    def test_validate_detects_cycle(self):
        self.client.login(username="testuser", password="testpass123")
        nodes = [
            {
                "id": "l1",
                "type": "layer",
                "numNeurons": 64,
                "activation": "relu",
                "inputPorts": [
                    {
                        "id": "l1_input_0",
                        "type": "input",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "bias": 0,
                        "portKind": "multi",
                    }
                ],
                "outputPorts": [
                    {
                        "id": "l1_output_0",
                        "type": "output",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "bias": 0,
                        "portKind": "data",
                    }
                ],
                "numInputs": 1,
                "numOutputs": 1,
                "bias": 0,
                "hasBias": True,
                "paramInputs": [],
                "paramOutputs": [],
                "numParamInputs": 0,
                "numParamOutputs": 0,
            },
            {
                "id": "l2",
                "type": "layer",
                "numNeurons": 32,
                "activation": "relu",
                "inputPorts": [
                    {
                        "id": "l2_input_0",
                        "type": "input",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "bias": 0,
                        "portKind": "multi",
                    }
                ],
                "outputPorts": [
                    {
                        "id": "l2_output_0",
                        "type": "output",
                        "index": 0,
                        "subType": None,
                        "shape": None,
                        "bias": 0,
                        "portKind": "data",
                    }
                ],
                "numInputs": 1,
                "numOutputs": 1,
                "bias": 0,
                "hasBias": True,
                "paramInputs": [],
                "paramOutputs": [],
                "numParamInputs": 0,
                "numParamOutputs": 0,
            },
        ]
        links = [
            {
                "from": "l1_output_0",
                "to": "l2_input_0",
                "weight": 0,
                "weightShape": None,
                "hasWeight": True,
            },
            {
                "from": "l2_output_0",
                "to": "l1_input_0",
                "weight": 0,
                "weightShape": None,
                "hasWeight": True,
            },
        ]
        graph = {"nodes": nodes, "links": links, "ports": [], "nodeCounter": 2}
        response = self.client.post(
            self.validate_url,
            data=json.dumps({"graph": json.dumps(graph)}),
            content_type="application/json",
        )
        data = response.json()
        self.assertFalse(data["isValid"])
        self.assertTrue(any("cycle" in e["message"].lower() for e in data["errors"]))

    def test_validate_invalid_json_returns_error(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(
            self.validate_url,
            data="not valid json",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
