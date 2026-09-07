"""
Entry point for turning a SketchNet graph into a PyTorch script.

The work happens in two steps: :mod:`ir` resolves the graph into a fully
determined execution plan, and :mod:`emit` writes that plan out as source.
"""

from .ir import Plan, build_plan
from .emit import render


class CodeGenerator:
    """Generates a runnable PyTorch training script from a graph."""

    def __init__(self, graph_data: dict):
        """
        Args:
            graph_data: front-end JSON with "nodes", "links", "ports".
        """
        self.plan: Plan = build_plan(graph_data)

    def generate(self) -> str:
        return render(self.plan)
