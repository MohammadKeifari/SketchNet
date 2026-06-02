from .graph import parse_graph
from .phase_analyzer import analyze_phases

MODEL_TYPES = {
    "neuron",
    "layer",
    "conv2d",
    "flatten",
    "dropout",
    "batchnorm",
    "add",
    "concat",
}


class GraphValidator:
    def __init__(self, graph_data):
        self.graph = parse_graph(graph_data)
        self.flow = analyze_phases(self.graph)

    def validate(self):
        errors = []
        warnings = []

        # --- basic connectivity ---
        self._check_input_output_present(errors)
        self._check_optimizer_connections(errors)
        self._check_link_weights(warnings)
        self._check_multi_port_cardinality(errors)
        self._check_phase_connectivity(warnings)
        self._check_preprocessing_models(warnings)

        return {
            "errors": errors,
            "warnings": warnings,
        }

    def _check_input_output_present(self, errors):
        has_input = any(n.type == "input-data" for n in self.graph.nodes.values())
        has_output = any(n.type == "output" for n in self.graph.nodes.values())
        if not has_input:
            errors.append({"message": "Missing Input Data node.", "nodeId": None})
        if not has_output:
            errors.append({"message": "Missing Output node.", "nodeId": None})

    def _check_optimizer_connections(self, errors):
        opt = self.flow.get("optimizer")
        if not opt:
            errors.append({"message": "Optimizer node is required.", "nodeId": None})
            return
        for port in opt.inputs:
            connected = any(l.id_to == port.id for l in self.graph.links)
            if not connected:
                role = port.role or f"port {port.index}"
                errors.append(
                    {
                        "message": f"Optimizer input '{role}' is not connected.",
                        "portId": port.id,
                    }
                )

    def _check_link_weights(self, warnings):
        for link in self.graph.links:
            if link.weight == 0.0:
                warnings.append(
                    {
                        "message": (
                            "Link weight is 0 (will be initialised to 1 in generated code "
                            "to avoid dead gradients). Consider setting a non‑zero value in the canvas."
                        ),
                        "linkKey": f"{link.id_from}→{link.id_to}",
                    }
                )

    def _check_multi_port_cardinality(self, errors):
        for node in self.graph.nodes.values():
            if node.type == "add":
                in_count = sum(
                    1
                    for l in self.graph.links
                    if l.id_to in {p.id for p in node.inputs}
                )
                if in_count != 2:
                    errors.append(
                        {
                            "message": f"Add node '{node.id}' requires exactly 2 inputs, found {in_count}.",
                            "nodeId": node.id,
                        }
                    )
            if node.type == "concat":
                in_count = sum(
                    1
                    for l in self.graph.links
                    if l.id_to in {p.id for p in node.inputs}
                )
                if in_count < 2:
                    errors.append(
                        {
                            "message": f"Concat node '{node.id}' requires at least 2 inputs, found {in_count}.",
                            "nodeId": node.id,
                        }
                    )

    def _check_phase_connectivity(self, warnings):
        train_set = set(self.flow["train_order"])
        eval_set = set(self.flow["eval_order"])
        all_model = {
            nid for nid in self.graph.nodes if self.graph.nodes[nid].type in MODEL_TYPES
        }
        for nid in all_model:
            in_train = nid in train_set
            in_eval = nid in eval_set
            if not in_train and not in_eval:
                warnings.append(
                    {
                        "message": f"Model node '{nid}' is not reachable in either training or evaluation phase.",
                        "nodeId": nid,
                    }
                )
        # Output node test input warning
        output = next(
            (n for n in self.graph.nodes.values() if n.type == "output"), None
        )
        if output:
            test_input = next((p for p in output.inputs if p.sub_type == "test"), None)
            if test_input:
                connected = any(l.id_to == test_input.id for l in self.graph.links)
                if connected:
                    src_port = self.graph.ports[
                        next(
                            l.id_from
                            for l in self.graph.links
                            if l.id_to == test_input.id
                        )
                    ]
                    if (
                        "training" in src_port.activation_phases
                        and "evaluation" not in src_port.activation_phases
                    ):
                        warnings.append(
                            {
                                "message": "Test input of Output node is fed by a train‑only port. "
                                "Evaluation may not receive separate test data.",
                                "portId": test_input.id,
                            }
                        )

    def _check_preprocessing_models(self, warnings):
        for nid in self.flow["preprocessing_order"]:
            if self.graph.nodes[nid].type in MODEL_TYPES:
                warnings.append(
                    {
                        "message": f"Model node '{nid}' is in the preprocessing phase and will not be trained. "
                        "Data will flow through an untrained layer.",
                        "nodeId": nid,
                    }
                )

    def _check_data_flow_phases(self, warnings):
        """Warn if a node's input port lacks a phase that its source output has."""
        from .phase_analyzer import _is_port_active

        for link in self.graph.links:
            src = self.graph.ports[link.id_from]
            tgt = self.graph.ports[link.id_to]
            for phase in ("preprocessing", "training", "evaluation"):
                if _is_port_active(src, phase) and not _is_port_active(tgt, phase):
                    warnings.append(
                        {
                            "message": f"Port {tgt.id} receives data from a '{phase}' port but is not active in that phase.",
                            "portId": tgt.id,
                        }
                    )
