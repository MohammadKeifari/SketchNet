from django.test import SimpleTestCase
from sketchmod.codegen.generator import CodeGenerator
from sketchmod.codegen.viz import VizGenerator


class VizGeneratorTests(SimpleTestCase):

    def _make_graph(self, nodes, links, ports=None):
        if ports is None:
            ports = []
            for n in nodes:
                for p in n.get("inputPorts", []):
                    ports.append(p)
                for p in n.get("outputPorts", []):
                    ports.append(p)
        return {"nodes": nodes, "links": links, "ports": ports}

    def _generate(self, nodes, links):
        graph = self._make_graph(nodes, links)
        gen = CodeGenerator(graph)
        viz_gen = VizGenerator(gen)
        return "\n".join(viz_gen.generate())

    def _make_viz_node(self, **kwargs):
        defaults = {
            "id": "viz1",
            "type": "visualization",
            "inputPorts": [],
            "outputPorts": [],
            "colorMode": "none",
            "colorPalette": ["#ef4444", "#4ade80", "#60a5fa", "#f59e0b", "#a78bfa"],
            "continuousMinColor": "#3b82f6",
            "continuousMaxColor": "#ef4444",
        }
        defaults.update(kwargs)
        return defaults

    # ========== BASIC ==========

    def test_no_viz_node_returns_empty(self):
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
                        "portKind": "data",
                    }
                ],
            },
        ]
        links = []
        code = self._generate(nodes, links)
        self.assertEqual(code.strip(), "")

    def test_viz_generates_matplotlib_import(self):
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
                        "portKind": "data",
                    }
                ],
            },
            self._make_viz_node(),
        ]
        links = []
        graph = self._make_graph(nodes, links)
        gen = CodeGenerator(graph)
        code = gen.generate()
        self.assertIn("import matplotlib.pyplot as plt", code)

    # ========== PLOT STRUCTURE ==========

    def test_plot_function_exists(self):
        nodes = [self._make_viz_node()]
        links = []
        code = self._generate(nodes, links)
        self.assertIn("def plot_results(train_losses, val_losses):", code)

    def test_plot_has_figure(self):
        nodes = [self._make_viz_node()]
        links = []
        code = self._generate(nodes, links)
        self.assertIn("plt.figure", code)

    def test_plot_shows_train_loss(self):
        nodes = [self._make_viz_node()]
        links = []
        code = self._generate(nodes, links)
        self.assertIn("plt.plot(train_losses", code)

    def test_plot_shows_val_loss(self):
        nodes = [self._make_viz_node()]
        links = []
        code = self._generate(nodes, links)
        self.assertIn("plt.plot(val_losses", code)

    def test_plot_has_labels(self):
        nodes = [self._make_viz_node()]
        links = []
        code = self._generate(nodes, links)
        self.assertIn("plt.xlabel", code)
        self.assertIn("plt.ylabel", code)

    def test_plot_has_legend(self):
        nodes = [self._make_viz_node()]
        links = []
        code = self._generate(nodes, links)
        self.assertIn("plt.legend()", code)

    def test_plot_has_grid(self):
        nodes = [self._make_viz_node()]
        links = []
        code = self._generate(nodes, links)
        self.assertIn("plt.grid", code)

    def test_plot_shows(self):
        nodes = [self._make_viz_node()]
        links = []
        code = self._generate(nodes, links)
        self.assertIn("plt.show()", code)

    def test_plot_has_save_comment(self):
        nodes = [self._make_viz_node()]
        links = []
        code = self._generate(nodes, links)
        self.assertIn("# Uncomment to save:", code)
        self.assertIn("# plt.savefig", code)

    def test_plot_called_in_main(self):
        nodes = [self._make_viz_node()]
        links = []
        graph = self._make_graph(nodes, links)
        gen = CodeGenerator(graph)
        code = gen.generate()
        self.assertIn("plot_results(train_losses, val_losses)", code)

    # ========== DISCRETE MODE ==========

    def test_discrete_mode_shows_palette(self):
        nodes = [
            self._make_viz_node(
                colorMode="discrete",
                colorPalette=["#ff0000", "#00ff00", "#0000ff", "#ffff00"],
            )
        ]
        links = []
        code = self._generate(nodes, links)
        self.assertIn("Color palette:", code)
        self.assertIn("#ff0000", code)

    def test_discrete_mode_save_comment(self):
        nodes = [self._make_viz_node(colorMode="discrete")]
        links = []
        code = self._generate(nodes, links)
        self.assertIn("dpi=150", code)

    # ========== CONTINUOUS MODE ==========

    def test_continuous_mode_shows_colors(self):
        nodes = [
            self._make_viz_node(
                colorMode="continuous",
                continuousMinColor="#111111",
                continuousMaxColor="#eeeeee",
            )
        ]
        links = []
        code = self._generate(nodes, links)
        self.assertIn("Color range:", code)
        self.assertIn("#111111", code)
        self.assertIn("#eeeeee", code)

    def test_continuous_mode_save_with_facecolor(self):
        nodes = [
            self._make_viz_node(
                colorMode="continuous",
                continuousMinColor="#000000",
                continuousMaxColor="#ffffff",
            )
        ]
        links = []
        code = self._generate(nodes, links)
        self.assertIn("facecolor=", code)

    # ========== NO COLOR MODE ==========

    def test_none_mode_no_palette_info(self):
        nodes = [self._make_viz_node(colorMode="none")]
        links = []
        code = self._generate(nodes, links)
        self.assertNotIn("Color palette:", code)
        self.assertNotIn("Color range:", code)

    # ========== MULTIPLE VIZ NODES ==========

    def test_multiple_viz_nodes_uses_first(self):
        nodes = [
            self._make_viz_node(id="viz1", colorMode="discrete"),
            self._make_viz_node(id="viz2", colorMode="continuous"),
        ]
        links = []
        code = self._generate(nodes, links)
        self.assertIn("Color palette:", code)
        self.assertNotIn("Color range:", code)

    # ========== VALID PYTHON ==========

    def test_generated_code_is_valid_python(self):
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
                        "portKind": "data",
                    }
                ],
            },
            self._make_viz_node(),
        ]
        links = []
        graph = self._make_graph(nodes, links)
        gen = CodeGenerator(graph)
        code = gen.generate()
        try:
            compile(code, "<test>", "exec")
        except SyntaxError as e:
            self.fail(f"Generated code has syntax error: {e}")
