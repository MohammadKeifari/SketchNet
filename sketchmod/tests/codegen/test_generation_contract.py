"""
The generation contract: a graph is either rejected, or it produces a script.

Every example graph, plus a family of systematic mutations of each one, must
satisfy exactly one of:

* ``GraphValidator.validate()["isValid"]`` is False, or
* ``CodeGenerator.generate()`` returns source that compiles.

A graph that the validator accepts but the generator chokes on is the failure
this suite exists to catch.  Mutations are deliberately crude -- drop a link,
strip a phase, duplicate a node -- because that is what a half-finished canvas
looks like.
"""

import copy
import json
import unittest
from pathlib import Path

from sketchmod.codegen.generator import CodeGenerator
from sketchmod.codegen.validator import GraphValidator

EXAMPLES_DIR = Path(__file__).resolve().parent / "examples"
TEMPLATES_DIR = (
    Path(__file__).resolve().parents[2] / "static" / "sketchmod" / "templates"
)
TEMPLATE_WARNING_ALLOWLIST = {"missing-dataset"}
PHASES = ("preprocessing", "training", "evaluation")


def load_examples():
    return sorted(EXAMPLES_DIR.glob("model*.JSON"), key=lambda p: p.stem.lower())


def drop_each_link(graph):
    """One mutation per link, with that link removed."""
    for index, link in enumerate(graph.get("links", [])):
        mutant = copy.deepcopy(graph)
        del mutant["links"][index]
        yield f"drop-link-{link.get('from')}->{link.get('to')}", mutant


def drop_each_phase(graph):
    """One mutation per phase, with that phase stripped from every port."""
    for phase in PHASES:
        mutant = copy.deepcopy(graph)
        for port in mutant.get("ports", []):
            port["activationPhases"] = [
                p for p in port.get("activationPhases", []) if p != phase
            ]
        yield f"drop-phase-{phase}", mutant


def duplicate_each_node(graph):
    """One mutation per node, with that node (and its ports) cloned."""
    for node in list(graph.get("nodes", [])):
        mutant = copy.deepcopy(graph)
        clone = copy.deepcopy(node)
        clone["id"] = f"{node['id']}__clone"
        mutant["nodes"].append(clone)
        for port in list(mutant.get("ports", [])):
            if port.get("nodeId") == node["id"]:
                port_clone = copy.deepcopy(port)
                port_clone["id"] = f"{port['id']}__clone"
                port_clone["nodeId"] = clone["id"]
                mutant["ports"].append(port_clone)
        yield f"duplicate-node-{node['id']}", mutant


MUTATORS = (drop_each_link, drop_each_phase, duplicate_each_node)


class GenerationContractTests(unittest.TestCase):
    """Rejected, or runnable - never accepted-but-broken."""

    def assert_contract(self, name, graph):
        try:
            report = GraphValidator(graph).validate()
        except Exception as error:  # noqa: BLE001 - the validator must not crash
            self.fail(f"{name}: validator raised {type(error).__name__}: {error}")

        if not report["isValid"]:
            self.assertTrue(
                report["errors"], f"{name}: invalid but reported no error"
            )
            return

        try:
            code = CodeGenerator(graph).generate()
        except Exception as error:  # noqa: BLE001 - accepted graphs must generate
            self.fail(
                f"{name}: validator accepted the graph but generation raised "
                f"{type(error).__name__}: {error}"
            )

        try:
            compile(code, f"<{name}>", "exec")
        except SyntaxError as error:
            self.fail(f"{name}: generated code does not compile: {error}")

    def test_examples_satisfy_the_contract(self):
        for path in load_examples():
            with self.subTest(example=path.stem):
                self.assert_contract(path.stem, json.loads(path.read_text()))

    def test_mutations_satisfy_the_contract(self):
        for path in load_examples():
            graph = json.loads(path.read_text())
            for mutate in MUTATORS:
                for label, mutant in mutate(graph):
                    with self.subTest(example=path.stem, mutation=label):
                        self.assert_contract(f"{path.stem}/{label}", mutant)

    def test_every_diagnostic_carries_a_code(self):
        for path in load_examples():
            report = GraphValidator(json.loads(path.read_text())).validate()
            for item in report["errors"] + report["warnings"]:
                with self.subTest(example=path.stem, message=item["message"]):
                    self.assertTrue(item.get("code"), "diagnostic has no code")
                    self.assertTrue(item.get("message"), "diagnostic has no message")


class StarterTemplateTests(unittest.TestCase):
    """Learn starter templates must be valid graphs, not merely translatable."""

    def test_templates_are_valid_and_compile(self):
        templates = sorted(TEMPLATES_DIR.glob("*.json"))
        self.assertGreaterEqual(len(templates), 4, "expected the four Learn templates")
        for path in templates:
            with self.subTest(template=path.stem):
                graph = json.loads(path.read_text(encoding="utf-8"))
                report = GraphValidator(graph).validate()
                self.assertTrue(
                    report["isValid"],
                    f"{path.stem} was rejected: {report['errors']}",
                )
                self.assertEqual(report["errors"], [])
                extra = {
                    item["code"]
                    for item in report["warnings"]
                    if item["code"] not in TEMPLATE_WARNING_ALLOWLIST
                }
                self.assertEqual(
                    extra,
                    set(),
                    f"{path.stem} raised unexpected warnings: {extra}",
                )
                code = CodeGenerator(graph).generate()
                compile(code, f"<{path.stem}>", "exec")


if __name__ == "__main__":
    unittest.main()
