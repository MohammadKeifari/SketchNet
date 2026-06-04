"""
Graph validation for SketchNet code generation.

This module validates the structure and connections of a computation graph before
code generation. It checks for required nodes, correct connections, proper cardinality
of multi-input operations, and compatibility between loss functions and label formats.

Validation produces errors (which block code generation) and warnings (which alert
the user to potential issues but allow generation to proceed).
"""

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
    """
    Validates a computation graph for correctness and completeness.

    This validator checks the graph for errors (missing required nodes, incorrect
    connections) and warnings (potential issues like untrained layers in preprocessing,
    loss-label mismatches, etc.).

    Attributes:
        graph: The parsed Graph object.
        flow (Dict): Execution flow information from phase analysis.
    """

    def __init__(self, graph_data):
        """
        Initialize the validator with JSON graph data.

        Args:
            graph_data (dict): JSON graph data (same format as CodeGenerator accepts).
        """
        self.graph = parse_graph(graph_data)
        self.flow = analyze_phases(self.graph)

    def validate(self):
        """
        Run all validation checks on the graph.

        Returns:
            dict: Validation result with keys:
                - "errors": List of error dicts (blocks code generation)
                - "warnings": List of warning dicts (informational only)
                - "isValid": Boolean (True if no errors)
        """
        errors = []
        warnings = []

        self._check_input_output_present(errors)
        self._check_optimizer_connections(warnings)
        self._check_link_weights(warnings)
        self._check_multi_port_cardinality(errors)
        self._check_model_connectivity(warnings)
        self._check_preprocessing_models(warnings)
        self._check_label_encoding(warnings)
        self._check_loss_label_compatibility(errors, warnings)
        self._check_accuracy_inputs(warnings)
        self._check_visualization_shapes(warnings)

        return {
            "errors": errors,
            "warnings": warnings,
            "isValid": len(errors) == 0,
        }

    # ---------- Errors ----------

    def _check_input_output_present(self, errors):
        """
        Check that the graph has at least one input-data and one output node.

        Args:
            errors (List): List to append error dicts to.
        """
        has_input = any(n.type == "input-data" for n in self.graph.nodes.values())
        has_output = any(n.type == "output" for n in self.graph.nodes.values())
        if not has_input:
            errors.append({"message": "Missing Input Data node.", "nodeId": None})
        if not has_output:
            errors.append({"message": "Missing Output node.", "nodeId": None})

    def _check_optimizer_connections(self, warnings):
        opt = self.flow.get("optimizer")
        if not opt:
            warnings.append(
                {
                    "message": "Optimizer node is missing. Training loop will not be generated.",
                    "nodeId": None,
                }
            )
            return
        for port in opt.inputs:
            connected = any(l.id_to == port.id for l in self.graph.links)
            if not connected:
                role = port.role or f"port {port.index}"
                warnings.append(
                    {
                        "message": f"Optimizer input '{role}' is not connected. Training may fail.",
                        "portId": port.id,
                    }
                )

    def _check_multi_port_cardinality(self, errors):
        """
        Check that multi-input nodes (add, concat) have the correct number of inputs.

        Args:
            errors (List): List to append error dicts to.
        """
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

    # ---------- Warnings ----------

    def _check_link_weights(self, warnings):
        """
        Warn if a weighted link has weight 0 (would block gradients).

        Args:
            warnings (List): List to append warning dicts to.
        """
        for link in self.graph.links:
            if link.has_weight and link.weight == 0.0:
                warnings.append(
                    {
                        "message": (
                            "Link weight is 0 (will be initialised to 1 in generated code "
                            "to avoid dead gradients). Consider setting a non‑zero value in the canvas."
                        ),
                        "linkKey": f"{link.id_from}→{link.id_to}",
                    }
                )

    def _check_model_connectivity(self, warnings):
        """
        Warn if a model node is not reachable in any phase (training or evaluation).

        Args:
            warnings (List): List to append warning dicts to.
        """
        train_set = set(self.flow["train_order"])
        eval_set = set(self.flow["eval_order"])
        for nid, node in self.graph.nodes.items():
            if node.type in MODEL_TYPES:
                if nid not in train_set and nid not in eval_set:
                    warnings.append(
                        {
                            "message": f"Model node '{node.type}' ({nid}) is not reachable in training or evaluation.",
                            "nodeId": nid,
                        }
                    )

    def _check_preprocessing_models(self, warnings):
        """
        Warn if a model layer appears in the preprocessing phase (will be untrained).

        Args:
            warnings (List): List to append warning dicts to.
        """
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
        """
        Warn if one-hot encoded labels are used with CrossEntropyLoss.

        Args:
            warnings (List): List to append warning dicts to.
        """
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

    def _check_loss_label_compatibility(self, errors, warnings):
        """
        Check that the label tensor shape is compatible with the chosen loss function.

        Args:
            errors (List): List to append error dicts to.
            warnings (List): List to append warning dicts to.
        """
        opt = self.flow.get("optimizer")
        if not opt or len(opt.inputs) < 2:
            return
        loss_type = opt.properties.get("lossType", "mse")
        labels_port = opt.inputs[1]

        src_node = None
        for link in self.graph.links:
            if link.id_to == labels_port.id:
                src_node = self.graph.nodes[self.graph.ports[link.id_from].node_id]
                break
        if src_node is None:
            return

        is_onehot = src_node.type == "onehot"

        if not is_onehot and src_node.type in DATA_TRANSFORM_TYPES:
            for in_port in src_node.inputs:
                for link in self.graph.links:
                    if link.id_to == in_port.id:
                        upstream = self.graph.nodes[
                            self.graph.ports[link.id_from].node_id
                        ]
                        if upstream.type == "onehot":
                            warnings.append(
                                {
                                    "message": (
                                        f"Labels pass through a {src_node.type} node after OneHot. "
                                        "The validator cannot verify shape compatibility. "
                                        "Ensure the loss function matches the final label tensor shape."
                                    ),
                                    "nodeId": src_node.id,
                                }
                            )
                            return

        if is_onehot:
            if loss_type not in ("bce", "mse", "l1", "huber"):
                errors.append(
                    {
                        "message": (
                            "Labels are one‑hot encoded, but the loss function expects "
                            f"class indices. Use BCEWithLogitsLoss or MSELoss for one‑hot labels."
                        ),
                        "portId": labels_port.id,
                    }
                )
        else:
            if loss_type in ("bce",):
                errors.append(
                    {
                        "message": (
                            "Labels appear to be integer class indices, but "
                            "BCEWithLogitsLoss expects one-hot targets. "
                            "Connect the OneHot node output instead, or switch to CrossEntropyLoss."
                        ),
                        "portId": labels_port.id,
                    }
                )

    def _check_accuracy_inputs(self, warnings):
        """
        Warn if an accuracy node doesn't have both predictions and labels connected.

        Args:
            warnings (List): List to append warning dicts to.
        """
        for node in self.graph.nodes.values():
            if node.type == "accuracy":
                connected = sum(
                    1 for p in node.inputs for l in self.graph.links if l.id_to == p.id
                )
                if connected < 2:
                    warnings.append(
                        {
                            "message": f"Accuracy node '{node.id}' expects 2 inputs (predictions, labels).",
                            "nodeId": node.id,
                        }
                    )

    def _check_preprocessing_only(self, warnings):
        train_set = self.flow.get("train_set", set())
        eval_set = self.flow.get("eval_set", set())
        preprocessing_set = self.flow.get("preprocessing_set", set())
        # Consider nodes that are model/output/optimizer as “real” training/eval
        has_train = any(
            nid in train_set
            and self.graph.nodes[nid].type in MODEL_TYPES | {"output", "optimizer"}
            for nid in train_set
        )
        has_eval = any(
            nid in eval_set
            and self.graph.nodes[nid].type
            in MODEL_TYPES | {"output", "optimizer", "visualization"}
            for nid in eval_set
        )
        if not has_train and not has_eval and preprocessing_set:
            warnings.append(
                {
                    "message": (
                        "No training or evaluation path is reachable from preprocessing outputs. "
                        "The generated code will contain only data loading and preprocessing."
                    ),
                    "nodeId": None,
                }
            )

    def _check_visualization_shapes(self, warnings):
        for node in self.graph.nodes.values():
            if node.type != "visualization":
                continue
            coord_ports = [p for p in node.inputs if p.sub_type == "coord"]

            # 1) Warn if any coord port has >1 column (2D tensor)
            for port in coord_ports:
                shape = port.shape
                if shape and shape.shape and len(shape.shape) > 1:
                    last_dim = shape.shape[-1]
                    try:
                        if int(last_dim) > 1:
                            warnings.append(
                                {
                                    "message": (
                                        f"Visualization '{node.id}' coordinate port "
                                        f"'{port.id}' has shape {shape.shape} with >1 column. "
                                        "Use ColumnSelect to reduce to a single column before connecting."
                                    ),
                                    "portId": port.id,
                                }
                            )
                    except (ValueError, TypeError):
                        pass  # symbolic size, can't decide

            # 2) Warn if sample sizes differ between coord ports
            first_dims = []
            for port in coord_ports:
                shape = port.shape
                if shape and shape.shape and len(shape.shape) >= 1:
                    first_dims.append((port.id, shape.shape[0]))
            if len(first_dims) >= 2:
                first_id, first_val = first_dims[0]
                for other_id, other_val in first_dims[1:]:
                    if str(first_val) != str(other_val):
                        warnings.append(
                            {
                                "message": (
                                    f"Visualization '{node.id}' coordinate ports {first_id} and {other_id} "
                                    f"have different sample sizes ({first_val} vs {other_val}). "
                                    "The scatter plot will fail."
                                ),
                                "nodeId": node.id,
                            }
                        )
