class GraphValidator:
    """Validates a graph for errors and warnings."""

    def __init__(self, graph):
        self.graph = graph
        self.nodes = graph.get("nodes", [])
        self.links = graph.get("links", [])
        self.ports = graph.get("ports", [])
        self._node_map = {n["id"]: n for n in self.nodes}
        self._port_map = {p["id"]: p for p in self.ports}

    def validate(self):
        self.errors = []
        self.warnings = []

        self._check_connections()
        self._check_inputdata_connectivity()
        self._check_output_connectivity()
        self._check_cycles()
        self._check_graph_connectivity()
        self._check_orphan_nodes()
        self._check_node_configs()
        self._check_dimension_compatibility()
        self._check_optimizer()
        self._check_batch_compatibility()

        return {
            "errors": self.errors,
            "warnings": self.warnings,
        }

    # ========== HELPERS ==========

    def _get_node(self, node_id):
        return self._node_map.get(node_id)

    def _get_port(self, port_id):
        return self._port_map.get(port_id)

    def _port_node_id(self, port_id):
        """Extract node ID from a port ID."""
        if not port_id:
            return None
        parts = port_id.rsplit("_", 2)
        if len(parts) >= 3:
            return parts[0]
        return None

    def _links_to(self, node_id):
        return [l for l in self.links if self._port_node_id(l["to"]) == node_id]

    def _links_from(self, node_id):
        return [l for l in self.links if self._port_node_id(l["from"]) == node_id]

    def _port_incoming_shapes(self, port_id):
        """Get all shapes arriving at a port from connected links."""
        shapes = []
        for link in self.links:
            if link["to"] == port_id:
                from_port = self._get_port(link["from"])
                if (
                    from_port
                    and from_port.get("shape")
                    and from_port["shape"].get("shape")
                ):
                    shapes.append(from_port["shape"])
        return shapes

    def _add_error(self, node_id=None, port_id=None, link=None, message=""):
        self.errors.append(
            {
                "nodeId": node_id,
                "portId": port_id,
                "linkKey": (link["from"] + "→" + link["to"]) if link else None,
                "message": message,
            }
        )

    def _add_warning(self, node_id=None, port_id=None, link=None, message=""):
        self.warnings.append(
            {
                "nodeId": node_id,
                "portId": port_id,
                "linkKey": (link["from"] + "→" + link["to"]) if link else None,
                "message": message,
            }
        )

    # ========== CHECKS ==========

    def _check_connections(self):
        """Check per-node connection rules."""
        for node in self.nodes:
            incoming = self._links_to(node["id"])
            count = len(incoming)
            node_type = node["type"]

            # Single-input nodes
            single_input = {
                "conv2d",
                "flatten",
                "dropout",
                "batchnorm",
                "normalize",
                "onehot",
                "column-select",
                "row-select",
                "dim-select",
                "train-test",
                "output",
            }
            if node_type in single_input and count > 1:
                self._add_error(
                    node_id=node["id"],
                    message=f"{node_type}: only accepts 1 input connection, has {count}",
                )

            # MultiPort nodes (can have many connections via one port)
            if node_type in ("layer", "neuron") and count < 1:
                self._add_error(
                    node_id=node["id"],
                    message=f"{node_type}: requires at least 1 input connection",
                )

            # AddNode: needs at least 2
            if node_type == "add" and count < 2:
                self._add_error(
                    node_id=node["id"],
                    message=f"Add: requires at least 2 input connections, has {count}",
                )

            # ConcatenateNode: needs at least 2
            if node_type == "concat" and count < 2:
                self._add_error(
                    node_id=node["id"],
                    message=f"Concat: requires at least 2 input connections, has {count}",
                )

            # OptimizerNode: needs exactly 2
            if node_type == "optimizer" and count != 2:
                self._add_error(
                    node_id=node["id"],
                    message=f"Optimizer: requires 2 input connections (loss + labels), has {count}",
                )

    def _check_inputdata_connectivity(self):
        for node in self.nodes:
            if node["type"] == "input-data":
                outgoing = self._links_from(node["id"])
                if not outgoing:
                    self._add_warning(
                        node_id=node["id"],
                        message="InputData: no outgoing connections",
                    )

    def _check_output_connectivity(self):
        for node in self.nodes:
            if node["type"] == "output":
                incoming = self._links_to(node["id"])
                if not incoming:
                    self._add_error(
                        node_id=node["id"],
                        message="Output: input port is not connected — no data reaches the output",
                    )

    def _check_cycles(self):
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
                dfs(self._port_node_id(link["to"]))
            in_stack.discard(node_id)

        for node in self.nodes:
            if node["id"] not in visited:
                dfs(node["id"])
            if has_cycle[0]:
                break

        if has_cycle[0]:
            self._add_error(message="Cycle detected in graph")

    def _check_graph_connectivity(self):
        input_nodes = [n for n in self.nodes if n["type"] == "input-data"]
        output_nodes = [n for n in self.nodes if n["type"] == "output"]

        if not output_nodes:
            self._add_error(message="No OutputNode in the graph")
            return

        if input_nodes:
            reachable = set()
            queue = [n["id"] for n in input_nodes]
            while queue:
                nid = queue.pop(0)
                if nid in reachable:
                    continue
                reachable.add(nid)
                for link in self._links_from(nid):
                    target = self._port_node_id(link["to"])
                    if target:
                        queue.append(target)

            if not any(n["id"] in reachable for n in output_nodes):
                self._add_error(message="No path from InputData to OutputNode")

    def _check_orphan_nodes(self):
        for node in self.nodes:
            if node["type"] in ("input-data", "output"):
                continue
            has_in = bool(self._links_to(node["id"]))
            has_out = bool(self._links_from(node["id"]))
            if not has_in and not has_out:
                self._add_warning(
                    node_id=node["id"],
                    message=f"{node['type']}: node is not connected to anything",
                )

    def _check_node_configs(self):
        for node in self.nodes:
            if node["type"] == "dropout" and node.get("rate", 0) > 0.8:
                self._add_warning(
                    node_id=node["id"],
                    message=f"Dropout: rate is very high ({int(node['rate'] * 100)}%)",
                )
            if node["type"] == "train-test":
                ratio = node.get("trainRatio", 0)
                if ratio <= 0 or ratio >= 1:
                    self._add_error(
                        node_id=node["id"],
                        message="TrainTestSplit: train ratio must be between 0 and 1",
                    )
            if node["type"] == "onehot" and node.get("numClasses", 10) < 2:
                self._add_error(
                    node_id=node["id"],
                    message="OneHotEncode: number of classes must be at least 2",
                )

    def _check_dimension_compatibility(self):
        for node in self.nodes:
            incoming = self._links_to(node["id"])
            if len(incoming) < 2:
                continue

            shapes = []
            for link in incoming:
                from_port = self._get_port(link["from"])
                if (
                    from_port
                    and from_port.get("shape")
                    and from_port["shape"].get("shape")
                ):
                    shapes.append(from_port["shape"]["shape"])

            if len(shapes) < 2:
                continue

            if node["type"] == "add":
                base = shapes[0]
                for i, s in enumerate(shapes[1:], 1):
                    if s != base:
                        self._add_error(
                            node_id=node["id"],
                            link=incoming[i],
                            message="Add: all inputs must have identical shapes",
                        )

            elif node["type"] == "concat":
                axis = node.get("axis", -1)
                rank = len(shapes[0])
                axis = rank - 1 if axis == -1 else axis

                for i, s in enumerate(shapes[1:], 1):
                    if len(s) != rank:
                        self._add_error(
                            node_id=node["id"],
                            link=incoming[i],
                            message=f"Concat: input has different rank ({len(s)} vs {rank})",
                        )
                        continue
                    for d in range(rank):
                        if d != axis and s[d] != shapes[0][d]:
                            self._add_error(
                                node_id=node["id"],
                                link=incoming[i],
                                message=f"Concat: dimension {d} differs across inputs",
                            )
                            break

    def _check_optimizer(self):
        for node in self.nodes:
            if node["type"] != "optimizer":
                continue

            # Check required ports
            for port_data in node.get("inputPorts", []):
                port_id = port_data["id"]
                connected = any(l["to"] == port_id for l in self.links)
                if not connected:
                    role = port_data.get("role", port_data.get("subType", "unknown"))
                    self._add_error(
                        node_id=node["id"],
                        port_id=port_id,
                        message=f"Optimizer: {role} port is not connected",
                    )

            # Hyperparameter checks
            if node.get("learningRate", 0) <= 0:
                self._add_error(
                    node_id=node["id"],
                    message="Optimizer: learning rate must be positive",
                )
            if node.get("epochs", 0) < 1:
                self._add_error(
                    node_id=node["id"], message="Optimizer: epochs must be at least 1"
                )
            if node.get("batchSize", 0) < 1:
                self._add_error(
                    node_id=node["id"],
                    message="Optimizer: batch size must be at least 1",
                )
            if node.get("earlyStopping") and node.get("earlyStoppingPatience", 0) < 1:
                self._add_error(
                    node_id=node["id"],
                    message="Optimizer: early stopping patience must be at least 1",
                )

        # Check for optimizer existence
        has_optimizer = any(n["type"] == "optimizer" for n in self.nodes)
        has_output = any(n["type"] == "output" for n in self.nodes)
        if not has_optimizer and has_output:
            self._add_warning(
                message="No OptimizerNode found — model can be exported but cannot be trained"
            )

    def _check_batch_compatibility(self):
        for node in self.nodes:
            for port_data in node.get("inputPorts", []):
                if port_data.get("portKind") != "multi":
                    continue

                shapes = self._port_incoming_shapes(port_data["id"])
                if len(shapes) < 2:
                    continue

                batches = []
                for s in shapes:
                    b = s["shape"][0]
                    batches.append(b)

                unique = set(str(b) for b in batches)
                if len(unique) > 1:
                    numeric = [b for b in batches if isinstance(b, (int, float))]
                    min_batch = min(numeric) if numeric else "?"
                    self._add_warning(
                        node_id=node["id"],
                        port_id=port_data["id"],
                        message=f"Batch dimensions differ ({', '.join(unique)}). "
                        f"Data with smaller batch ({min_batch}) will loop to match.",
                    )

    def _check_dataport_connections(self):
        for node in self.nodes:
            for port_data in node.get("inputPorts", []):
                if port_data.get("portKind") != "data":
                    continue

                incoming = self._links_to_port(port_data["id"])
                if len(incoming) > 2:
                    self._add_error(...)

                if len(incoming) == 2:
                    # Must be one train + one test
                    sources = [self._get_port(l["from"]) for l in incoming]
                    phases = {s.get("activationPhase", "training") for s in sources}
                    if phases != {"training", "evaluation"}:
                        self._add_error(
                            message="DataPort with 2 connections must have one training and one evaluation source"
                        )
