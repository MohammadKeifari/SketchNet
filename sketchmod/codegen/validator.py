from .translators import get_translator


class GraphValidator:

    def __init__(self, graph):
        self.nodes = graph.get("nodes", [])
        self.links = graph.get("links", [])
        self.ports = graph.get("ports", [])
        self._node_map = {n["id"]: n for n in self.nodes}
        self._port_map = {p["id"]: p for p in self.ports}

    def validate(self):
        errors = []
        warnings = []

        # Phase 1: Structural checks
        self._check_input_data(errors, warnings)
        self._check_output_exists(errors)
        self._check_cycles(warnings)
        self._check_orphans(warnings)

        # Phase 2: Path tracing
        every_batch_nodes = self._trace_path("every_batch")
        last_batch_nodes = self._trace_path("last_batch")

        self._check_path_exists(every_batch_nodes, last_batch_nodes, errors)
        self._check_activation_consistency(
            every_batch_nodes, last_batch_nodes, warnings
        )

        # Phase 3: Per-node validation
        for node in self.nodes:
            t = get_translator(node, self)
            result = t.validate()
            for e in result.get("errors", []):
                errors.append(
                    {
                        "nodeId": node["id"],
                        "message": e,
                    }
                )
            for w in result.get("warnings", []):
                warnings.append(
                    {
                        "nodeId": node["id"],
                        "message": w,
                    }
                )

        # Phase 4: Shape compatibility
        self._check_shape_compatibility(errors)

        # Phase 5: Training config
        self._check_optimizer(errors, warnings)

        # Phase 6: Port-level checks
        self._check_dataport_connections(warnings)

        return {
            "errors": errors,
            "warnings": warnings,
            "isValid": len(errors) == 0,
        }

    # ========== PHASE 1: STRUCTURAL ==========

    def _check_input_data(self, errors, warnings):
        input_nodes = [n for n in self.nodes if n["type"] == "input-data"]
        if not input_nodes:
            errors.append(
                {
                    "message": "No InputData node in the graph",
                }
            )
            return

        for node in input_nodes:
            outgoing = self._links_from(node["id"])
            if not outgoing:
                warnings.append(
                    {
                        "nodeId": node["id"],
                        "message": "InputData: no outgoing connections",
                    }
                )

    def _check_output_exists(self, errors):
        output_nodes = [n for n in self.nodes if n["type"] == "output"]
        if not output_nodes:
            errors.append(
                {
                    "message": "No OutputNode in the graph",
                }
            )

    def _check_cycles(self, warnings):
        visited = set()
        in_stack = set()
        has_cycle = [False]

        def dfs(node_id):
            if node_id in in_stack:
                has_cycle[0] = True
                return
            if node_id in visited:
                return
            visited.add(node_id)
            in_stack.add(node_id)
            for link in self._links_from(node_id):
                target = self._port_node_id(link["to"])
                if target:
                    dfs(target)
            in_stack.discard(node_id)

        for node in self.nodes:
            if node["id"] not in visited:
                dfs(node["id"])
            if has_cycle[0]:
                break

        if has_cycle[0]:
            warnings.append(
                {
                    "message": "Cycle detected in graph — data may loop infinitely",
                }
            )

    def _check_orphans(self, warnings):
        for node in self.nodes:
            if node["type"] in ("input-data", "output", "optimizer", "visualization"):
                continue
            has_in = bool(self._links_to(node["id"]))
            has_out = bool(self._links_from(node["id"]))
            if not has_in and not has_out:
                warnings.append(
                    {
                        "nodeId": node["id"],
                        "message": f"{node['type']}: node is not connected to anything",
                    }
                )

    # ========== PHASE 2: PATH TRACING ==========

    def _trace_path(self, activation_mode):
        """Forward simulation: which nodes fire in this activation mode."""
        active_ports = set()
        fired_nodes = set()

        for node in self.nodes:
            if node["type"] == "input-data":
                for port in node.get("outputPorts", []):
                    if self._port_active(port, activation_mode):
                        active_ports.add(port["id"])

        changed = True
        while changed:
            changed = False
            for node in self.nodes:
                if node["id"] in fired_nodes or node["type"] == "input-data":
                    continue

                receives = False
                for in_port in node.get("inputPorts", []):
                    for link in self.links:
                        if link["to"] == in_port["id"] and link["from"] in active_ports:
                            if self._port_active(in_port, activation_mode):
                                receives = True
                                break
                    if receives:
                        break

                if receives:
                    fired_nodes.add(node["id"])
                    changed = True
                    for out_port in node.get("outputPorts", []):
                        if self._port_active(out_port, activation_mode):
                            active_ports.add(out_port["id"])

        return fired_nodes

    def _port_active(self, port, mode):
        port_mode = port.get("activationMode", "every_batch")
        if port_mode == "both":
            return True
        return port_mode == mode

    def _check_path_exists(self, every_batch, last_batch, errors):
        output_nodes = [n for n in self.nodes if n["type"] == "output"]
        if not output_nodes:
            return

        output_id = output_nodes[0]["id"]
        reachable = output_id in every_batch or output_id in last_batch

        if not reachable:
            errors.append(
                {
                    "message": "No path from InputData to OutputNode",
                }
            )

    def _check_activation_consistency(self, every_batch, last_batch, warnings):
        """A last_batch output shouldn't be the only path to an every_batch input."""
        for node in self.nodes:
            for out_port in node.get("outputPorts", []):
                if self._port_active(out_port, "last_batch") and not self._port_active(
                    out_port, "every_batch"
                ):
                    # This port only activates on last_batch
                    # Check if any downstream every_batch ports depend on it
                    downstream = self._trace_downstream(out_port["id"])
                    for ds_id in downstream:
                        ds_node = self._node_map.get(ds_id, {})
                        for ds_port in ds_node.get("inputPorts", []):
                            if self._port_active(ds_port, "every_batch"):
                                warnings.append(
                                    {
                                        "nodeId": node["id"],
                                        "portId": out_port["id"],
                                        "message": f"Port '{out_port['id']}' is last_batch only but feeds every_batch port '{ds_port['id']}' — data will never arrive during training",
                                    }
                                )

    def _trace_downstream(self, port_id):
        """Find all node IDs reachable from a port."""
        reachable = set()
        queue = [port_id]
        while queue:
            current = queue.pop(0)
            for link in self.links:
                if link["from"] == current:
                    target = self._port_node_id(link["to"])
                    if target and target not in reachable:
                        reachable.add(target)
                        target_node = self._node_map.get(target, {})
                        for op in target_node.get("outputPorts", []):
                            queue.append(op["id"])
        return reachable

    # ========== PHASE 4: SHAPE COMPATIBILITY ==========

    def _check_shape_compatibility(self, errors):
        for node in self.nodes:
            incoming = self._links_to(node["id"])
            if len(incoming) < 2:
                continue

            shapes = []
            for link in incoming:
                src_port = self._port_map.get(link["from"], {})
                shape_data = src_port.get("shape", {})
                if shape_data and shape_data.get("shape"):
                    shapes.append(shape_data["shape"])

            if len(shapes) < 2:
                continue

            if node["type"] == "add":
                base = shapes[0]
                for i, s in enumerate(shapes[1:], 1):
                    if s != base:
                        errors.append(
                            {
                                "nodeId": node["id"],
                                "message": "Add: all inputs must have identical shapes",
                            }
                        )
                        break

            elif node["type"] == "concat":
                axis = node.get("axis", -1)
                rank = len(shapes[0])
                axis = rank - 1 if axis == -1 else axis

                for i, s in enumerate(shapes[1:], 1):
                    if len(s) != rank:
                        errors.append(
                            {
                                "nodeId": node["id"],
                                "message": f"Concat: input has different rank ({len(s)} vs {rank})",
                            }
                        )
                        continue
                    for d in range(rank):
                        if d != axis and str(s[d]) != str(shapes[0][d]):
                            errors.append(
                                {
                                    "nodeId": node["id"],
                                    "message": f"Concat: dimension {d} differs across inputs",
                                }
                            )
                            break

    # ========== PHASE 5: TRAINING CONFIG ==========

    def _check_optimizer(self, errors, warnings):
        optimizers = [n for n in self.nodes if n["type"] == "optimizer"]
        output_nodes = [n for n in self.nodes if n["type"] == "output"]
        has_output = len(output_nodes) > 0

        if not optimizers:
            if has_output:
                warnings.append(
                    {
                        "message": "No OptimizerNode found — model can be exported but cannot be trained",
                    }
                )
            return

        for opt in optimizers:
            # Check required ports are connected
            for port_data in opt.get("inputPorts", []):
                port_id = port_data["id"]
                role = port_data.get("role", "unknown")
                connected = any(l["to"] == port_id for l in self.links)
                if not connected:
                    errors.append(
                        {
                            "nodeId": opt["id"],
                            "portId": port_id,
                            "message": f"Optimizer: {role} port is not connected",
                        }
                    )

            # Hyperparameter checks
            if opt.get("learningRate", 0) <= 0:
                errors.append(
                    {
                        "nodeId": opt["id"],
                        "message": "Optimizer: learning rate must be positive",
                    }
                )
            if opt.get("epochs", 0) < 1:
                errors.append(
                    {
                        "nodeId": opt["id"],
                        "message": "Optimizer: epochs must be at least 1",
                    }
                )
            if opt.get("batchSize", 0) < 1:
                errors.append(
                    {
                        "nodeId": opt["id"],
                        "message": "Optimizer: batch size must be at least 1",
                    }
                )
            if opt.get("earlyStopping") and opt.get("earlyStoppingPatience", 0) < 1:
                errors.append(
                    {
                        "nodeId": opt["id"],
                        "message": "Optimizer: early stopping patience must be at least 1",
                    }
                )

    # ========== PHASE 6: PORT-LEVEL ==========

    def _check_dataport_connections(self, warnings):
        for node in self.nodes:
            for port_data in node.get("inputPorts", []):
                if port_data.get("portKind") != "data":
                    continue

                port_id = port_data["id"]
                incoming = [l for l in self.links if l["to"] == port_id]

                if len(incoming) == 2:
                    # Check: one every_batch + one last_batch
                    sources = []
                    for link in incoming:
                        src_port = self._port_map.get(link["from"], {})
                        mode = src_port.get("activationMode", "every_batch")
                        sources.append(mode)

                    has_every = "every_batch" in sources or "both" in sources
                    has_last = "last_batch" in sources or "both" in sources

                    if not (has_every and has_last):
                        warnings.append(
                            {
                                "nodeId": node["id"],
                                "portId": port_id,
                                "message": "DataPort has 2 connections but not one training + one evaluation source",
                            }
                        )

    # ========== HELPERS ==========

    def _port_node_id(self, port_id):
        if not port_id:
            return None
        parts = port_id.rsplit("_", 2)
        return parts[0] if len(parts) >= 3 else None

    def _links_from(self, node_id):
        return [l for l in self.links if self._port_node_id(l["from"]) == node_id]

    def _links_to(self, node_id):
        return [l for l in self.links if self._port_node_id(l["to"]) == node_id]

    def get_links_to(self, node_id):
        return self._links_to(node_id)

    def _port_map_get(self, port_id):
        return self._port_map.get(port_id, {})
