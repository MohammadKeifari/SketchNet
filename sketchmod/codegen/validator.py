"""
Graph validation for SketchNet code generation.

Checks the graph for errors (block code generation) and warnings
(informational).  The validator is phase‑agnostic: any node can appear
in any phase, but some combinations are suspicious.
"""

from .graph import parse_graph
from .phase_analyzer import analyze_phases


class GraphValidator:
    def __init__(self, graph_data):
        self.graph = parse_graph(graph_data)
        self.flow = analyze_phases(self.graph)

    def validate(self):
        errors = []
        warnings = []

        self._check_input_output_present(errors)
        self._check_optimizer_phase(errors)
        self._check_param_port_cycles(errors)
        self._check_required_inputs(errors)
        self._check_multiple_train_entries(errors)

        self._check_optimizer_missing(warnings)
        self._check_model_in_preprocessing(warnings)
        self._check_model_eval_without_train(warnings)
        self._check_visualization_in_training(warnings)
        self._check_preprocessing_reaches_train_eval(warnings)
        self._check_label_loss_compatibility(warnings)
        self._check_accuracy_inputs(warnings)
        self._check_visualization_shapes(warnings)
        self._check_accuracy_label_reshape(warnings)
        self._check_reshape_feasibility(warnings)
        self._check_multiple_optimizers(warnings)
        self._check_eval_entry_point(warnings)

        return {
            "errors": errors,
            "warnings": warnings,
            "isValid": len(errors) == 0,
        }

    def _get_model_nodes(self):
        """
        Identify training‑order nodes that belong to the model.
        Same logic as generator.py.
        """
        train_set = self.flow["train_set"]
        output_id = None
        for nid in train_set:
            if self.graph.nodes[nid].type == "output":
                output_id = nid
                break
        if output_id is None:
            return []

        reachable = set()
        queue = [output_id]
        while queue:
            cur = queue.pop(0)
            if cur in reachable:
                continue
            reachable.add(cur)
            for pred in self.graph.predecessors(cur):
                if pred in train_set and pred not in reachable:
                    queue.append(pred)

        pre_set = self.flow.get("preprocessing_set", set())
        return [
            nid
            for nid in self.flow["train_order"]
            if nid in reachable and nid not in pre_set
        ]

    # ----------------------------------------------------------------
    #  ERRORS
    # ----------------------------------------------------------------
    def _check_input_output_present(self, errors):
        has_input = any(n.type == "input-data" for n in self.graph.nodes.values())
        has_output = any(n.type == "output" for n in self.graph.nodes.values())
        if not has_input:
            errors.append({"message": "Missing Input Data node.", "nodeId": None})
        if not has_output:
            errors.append({"message": "Missing Output node.", "nodeId": None})

    def _check_optimizer_phase(self, errors):
        for nid, node in self.graph.nodes.items():
            if node.type == "optimizer":
                if nid not in self.flow["train_set"]:
                    errors.append(
                        {
                            "message": "Optimizer node must be in the training phase.",
                            "nodeId": nid,
                        }
                    )
                return

    def _check_param_port_cycles(self, errors):
        adj = {nid: [] for nid in self.graph.nodes}
        for link in self.graph.links:
            src = self.graph.ports[link.id_from]
            tgt = self.graph.ports[link.id_to]
            if src.port_kind == "param" and tgt.port_kind == "param":
                adj[src.node_id].append(tgt.node_id)

        WHITE, GRAY, BLACK = 0, 1, 2
        color = {nid: WHITE for nid in self.graph.nodes}

        def dfs(u):
            color[u] = GRAY
            for v in adj[u]:
                if color[v] == GRAY:
                    return True
                if color[v] == WHITE and dfs(v):
                    return True
            color[u] = BLACK
            return False

        for nid in self.graph.nodes:
            if color[nid] == WHITE and dfs(nid):
                errors.append(
                    {
                        "message": "Param‑port cycle detected – no valid execution order.",
                        "nodeId": None,
                    }
                )
                return

    def _check_required_inputs(self, errors):
        for node in self.graph.nodes.values():
            in_count = sum(
                1 for l in self.graph.links if l.id_to in {p.id for p in node.inputs}
            )
            if node.type in (
                "neuron",
                "layer",
                "conv2d",
                "dropout",
                "batchnorm",
            ):
                if in_count < 1:
                    errors.append(
                        {
                            "message": f"'{node.type}' ({node.id}) requires at least 1 input connection.",
                            "nodeId": node.id,
                        }
                    )
            elif node.type == "add":
                if in_count != 2:
                    errors.append(
                        {
                            "message": f"Add node '{node.id}' requires exactly 2 inputs, found {in_count}.",
                            "nodeId": node.id,
                        }
                    )
            elif node.type == "concat":
                if in_count < 2:
                    errors.append(
                        {
                            "message": f"Concat node '{node.id}' requires at least 2 inputs, found {in_count}.",
                            "nodeId": node.id,
                        }
                    )

    def _check_multiple_train_entries(self, errors):
        model_nodes = self._get_model_nodes()
        if not model_nodes:
            return
        # Find model nodes with no predecessors that are also model nodes
        # (they are entry points)
        entries = []
        for nid in model_nodes:
            preds = self.graph.predecessors(nid)
            model_preds = [p for p in preds if p in model_nodes]
            if not model_preds:
                entries.append(nid)
        if len(entries) > 1:
            errors.append(
                {
                    "message": (
                        f"Multiple training entry points detected: {entries}. "
                        "The model must have a single entry point."
                    ),
                    "nodeId": entries[0],
                }
            )

    # ----------------------------------------------------------------
    #  WARNINGS
    # ----------------------------------------------------------------
    def _check_optimizer_missing(self, warnings):
        if self.flow.get("optimizer") is None:
            warnings.append(
                {
                    "message": "No optimizer node – training loop will not be generated.",
                    "nodeId": None,
                }
            )

    def _check_model_in_preprocessing(self, warnings):
        for nid in self.flow["preprocessing_order"]:
            node = self.graph.nodes[nid]
            if node.type in (
                "neuron",
                "layer",
                "conv2d",
                "dropout",
                "batchnorm",
            ):
                warnings.append(
                    {
                        "message": f"Model node '{node.type}' ({nid}) is in preprocessing and will be untrained.",
                        "nodeId": nid,
                    }
                )

    def _check_model_eval_without_train(self, warnings):
        eval_set = self.flow["eval_set"]
        train_set = self.flow["train_set"]
        for nid in eval_set - train_set:
            node = self.graph.nodes[nid]
            if node.type in (
                "neuron",
                "layer",
                "conv2d",
                "dropout",
                "batchnorm",
            ):
                warnings.append(
                    {
                        "message": f"Model node '{node.type}' ({nid}) is in evaluation but not training – will be untrained.",
                        "nodeId": nid,
                    }
                )

    def _check_visualization_in_training(self, warnings):
        for nid in self.flow["train_set"]:
            node = self.graph.nodes[nid]
            if node.type == "visualization":
                warnings.append(
                    {
                        "message": f"Visualization '{nid}' is in the training phase and will be skipped.",
                        "nodeId": nid,
                    }
                )

    def _check_preprocessing_reaches_train_eval(self, warnings):
        pre_set = self.flow["preprocessing_set"]
        train_set = self.flow["train_set"]
        eval_set = self.flow["eval_set"]
        if pre_set and not train_set and not eval_set:
            warnings.append(
                {
                    "message": "Preprocessing does not reach training or evaluation – only data loading will be generated.",
                    "nodeId": None,
                }
            )

    def _check_label_loss_compatibility(self, warnings):
        opt = self.flow.get("optimizer")
        if not opt or len(opt.inputs) < 2:
            return
        labels_port = opt.inputs[1]
        loss_type = opt.properties.get("lossType", "mse")
        for link in self.graph.links:
            if link.id_to == labels_port.id:
                src_node = self.graph.nodes[self.graph.ports[link.id_from].node_id]
                if src_node.type == "onehot" and loss_type == "cross_entropy":
                    warnings.append(
                        {
                            "message": "CrossEntropyLoss expects class indices, but labels come from a OneHot node.",
                            "portId": labels_port.id,
                        }
                    )
                elif src_node.type != "onehot" and loss_type == "bce":
                    warnings.append(
                        {
                            "message": "BCEWithLogitsLoss expects one‑hot labels, but labels appear to be class indices.",
                            "portId": labels_port.id,
                        }
                    )
                break

    def _check_accuracy_inputs(self, warnings):
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

    def _check_visualization_shapes(self, warnings):
        for node in self.graph.nodes.values():
            if node.type != "visualization":
                continue
            coord_ports = [p for p in node.inputs if p.sub_type == "coord"]
            first_dims = []
            for port in coord_ports:
                # Follow the link to get the source port's shape
                src_shape = None
                for link in self.graph.links:
                    if link.id_to == port.id:
                        src_port = self.graph.ports[link.id_from]
                        src_shape = src_port.shape
                        break
                if src_shape and src_shape.shape and len(src_shape.shape) >= 1:
                    first_dims.append((port.id, src_shape.shape[0]))
            if len(first_dims) >= 2:
                first_id, first_val = first_dims[0]
                for other_id, other_val in first_dims[1:]:
                    if str(first_val) != str(other_val):
                        warnings.append(
                            {
                                "message": (
                                    f"Visualization '{node.id}' ports {first_id} and {other_id} "
                                    f"have different sample sizes ({first_val} vs {other_val})."
                                ),
                                "nodeId": node.id,
                            }
                        )
                        break

    def _check_accuracy_label_reshape(self, warnings):
        """Warn if the accuracy label input will be automatically squeezed or argmaxed."""
        for node in self.graph.nodes.values():
            if node.type != "accuracy":
                continue
            label_port = node.inputs[1] if len(node.inputs) >= 2 else None
            if not label_port:
                continue
            for link in self.graph.links:
                if link.id_to == label_port.id:
                    src_port = self.graph.ports[link.id_from]
                    shape = src_port.shape
                    if shape and shape.shape and len(shape.shape) == 2:
                        dim = shape.shape[-1]
                        try:
                            last_dim = int(dim) if dim.is_concrete else -1
                        except (ValueError, TypeError):
                            last_dim = -1
                        if last_dim > 1:
                            warnings.append(
                                {
                                    "message": (
                                        f"Accuracy label input port '{label_port.id}' "
                                        f"appears to be one‑hot encoded (shape {shape.shape}). "
                                        "It will be argmax‑ed automatically."
                                    ),
                                    "portId": label_port.id,
                                }
                            )
                        elif last_dim == 1:
                            warnings.append(
                                {
                                    "message": (
                                        f"Accuracy label input port '{label_port.id}' "
                                        f"has shape (N,1) – automatically squeezed to (N)."
                                    ),
                                    "portId": label_port.id,
                                }
                            )
                    break

    def _check_reshape_feasibility(self, warnings):
        import sympy

        for node in self.graph.nodes.values():
            if node.type != "reshape":
                continue
            inp = None
            for port in node.inputs:
                for link in self.graph.links:
                    if link.id_to == port.id:
                        src_port = self.graph.ports[link.id_from]
                        inp = src_port.shape
                        break
                if inp:
                    break
            if not inp or not inp.shape:
                continue
            target_str = node.properties.get("targetShape", "")
            parts = [x.strip() for x in target_str.strip("()").split(",") if x.strip()]
            infer_count = sum(1 for p in parts if p == "-1")
            if infer_count > 1:
                warnings.append(
                    {
                        "message": f"Reshape node '{node.id}' has multiple -1 dimensions – PyTorch cannot infer.",
                        "nodeId": node.id,
                    }
                )
                continue
            total_inp = sympy.Integer(1)
            for d in inp.shape:
                total_inp = total_inp * d._value
            total_target = sympy.Integer(1)
            for p in parts:
                if p == "-1":
                    continue
                try:
                    total_target = total_target * int(p)
                except ValueError:
                    pass  # symbolic, can't verify
            if infer_count == 0:
                if total_target != total_inp:
                    warnings.append(
                        {
                            "message": f"Reshape node '{node.id}' total elements mismatch ({total_inp} vs {total_target}).",
                            "nodeId": node.id,
                        }
                    )
            else:
                if total_inp % total_target != 0:
                    warnings.append(
                        {
                            "message": f"Reshape node '{node.id}' cannot infer dimension – {total_inp} not divisible by {total_target}.",
                            "nodeId": node.id,
                        }
                    )

    def _check_multiple_optimizers(self, warnings):
        optimizer_count = sum(
            1 for n in self.graph.nodes.values() if n.type == "optimizer"
        )
        if optimizer_count > 1:
            warnings.append(
                {
                    "message": (
                        f"Graph contains {optimizer_count} optimizer nodes. "
                        "Only the first one will be used."
                    ),
                    "nodeId": None,
                }
            )

    def _check_eval_entry_point(self, warnings):
        model_nodes = self._get_model_nodes()
        if not model_nodes:
            return
        train_entry = None
        for nid in self.flow.get("train_order", []):
            if nid in model_nodes:
                train_entry = nid
                break
        eval_entry = None
        for nid in self.flow.get("eval_order", []):
            if nid in model_nodes:
                eval_entry = nid
                break
        if train_entry and eval_entry and train_entry != eval_entry:
            warnings.append(
                {
                    "message": (
                        f"Evaluation enters the model at '{eval_entry}', "
                        f"but the model starts at '{train_entry}'. "
                        "Evaluation will be skipped because it cannot reuse the trained model."
                    ),
                    "nodeId": eval_entry,
                }
            )
