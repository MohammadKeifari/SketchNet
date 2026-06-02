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
DATA_TRANSFORM_TYPES = {
    "column-select",
    "row-select",
    "dim-select",
    "normalize",
    "onehot",
    "deonehot",
    "train-test",
}


class GraphValidator:
    def __init__(self, graph_data):
        self.graph = parse_graph(graph_data)
        self.flow = analyze_phases(self.graph)

    def validate(self):
        errors = []
        warnings = []

        self._check_input_output_present(errors)
        self._check_optimizer_connections(errors)
        self._check_link_weights(warnings)
        self._check_multi_port_cardinality(errors)
        self._check_phase_connectivity(warnings)
        self._check_preprocessing_models(warnings)
        self._check_label_encoding(warnings)

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
        """Warn only about real data‑flow problems: a link where source port has a phase
        but the target port is completely missing that phase."""
        for link in self.graph.links:
            src = self.graph.ports[link.id_from]
            tgt = self.graph.ports[link.id_to]
            for phase in ("preprocessing", "training", "evaluation"):
                if (
                    phase in src.activation_phases
                    and phase not in tgt.activation_phases
                ):
                    src_node = self.graph.nodes[src.node_id]
                    tgt_node = self.graph.nodes[tgt.node_id]
                    warnings.append(
                        {
                            "message": (
                                f"{src_node.type.capitalize()} '{src.node_id}' "
                                f"output {src.index} sends data in '{phase}' phase, "
                                f"but {tgt_node.type.capitalize()} '{tgt.node_id}' "
                                f"input {tgt.index} is not active in that phase."
                            ),
                            "portId": tgt.id,
                        }
                    )

    def _check_preprocessing_models(self, warnings):
        for nid in self.flow["preprocessing_order"]:
            node = self.graph.nodes[nid]
            if node.type in MODEL_TYPES:
                warnings.append(
                    {
                        "message": (
                            f"Model node '{node.type}' ({nid}) is in the preprocessing phase "
                            "and will not be trained. Data will flow through an untrained layer."
                        ),
                        "nodeId": nid,
                    }
                )

    def _check_label_encoding(self, warnings):
        opt = self.flow.get("optimizer")
        if not opt or len(opt.inputs) < 2:
            return
        labels_port = opt.inputs[1]
        for link in self.graph.links:
            if link.id_to == labels_port.id:
                src_node = self.graph.nodes[self.graph.ports[link.id_from].node_id]
                if (
                    src_node.type == "onehot"
                    and opt.properties.get("lossType") == "cross_entropy"
                ):
                    warnings.append(
                        {
                            "message": (
                                "CrossEntropyLoss expects integer class indices, but the labels "
                                "come through a OneHot node. Connect raw labels directly or switch "
                                "the loss to BCEWithLogitsLoss."
                            ),
                            "portId": labels_port.id,
                        }
                    )
