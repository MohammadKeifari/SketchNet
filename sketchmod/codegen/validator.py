from .graph import parse_graph
from .phase_analyzer import analyze_phases


class GraphValidator:
    def __init__(self, graph_data):
        self.graph = parse_graph(graph_data)
        self.flow = analyze_phases(self.graph)

    def validate(self):
        errors = []
        warnings = []

        # ---------- basic connectivity ----------
        self._check_input_output_present(errors)
        self._check_optimizer_connections(errors)
        self._check_link_weights(warnings)
        self._check_multi_port_cardinality(errors)
        self._check_phase_connectivity(warnings)

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
        # check both input ports are connected
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
                            f"Link weight is 0 (will be initialised to 1 in generated code "
                            f"to avoid dead gradients). Consider setting a non‑zero value in the canvas."
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
        # Warn if a model node has no path during training or evaluation
        train_set = self.flow.get("train_model_order", [])
        eval_set = self.flow.get("eval_model_order", [])
        all_model = set(train_set) | set(eval_set)
        for nid in all_model:
            in_train = nid in train_set
            in_eval = nid in eval_set
            if not in_train and not in_eval:
                warnings.append(
                    {
                        "message": f"Model node '{nid}' is not reachable in either phase.",
                        "nodeId": nid,
                    }
                )
        # Warn if output node's test input is not connected to a test‑phase source
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
                    if src_port.activation_mode == "every_batch":
                        warnings.append(
                            {
                                "message": "Test input of Output node is fed by a train‑only port (every_batch). "
                                "Evaluation may not receive separate test data.",
                                "portId": test_input.id,
                            }
                        )
