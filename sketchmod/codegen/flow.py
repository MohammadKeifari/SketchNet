"""
Flow Analyzer — analyzes the node graph to determine execution phases,
model boundaries, port activation, and code generation structure.
"""


class FlowAnalyzer:
    PREPROCESSING_TYPES = {
        "input-data",
        "normalize",
        "column-select",
        "row-select",
        "dim-select",
        "onehot",
        "train-test",
    }
    MODEL_TYPES = {
        "layer",
        "neuron",
        "conv2d",
        "flatten",
        "dropout",
        "batchnorm",
        "add",
        "concat",
    }
    OUTPUT_TYPES = {"output"}

    def __init__(self, graph):
        self.nodes = graph.get("nodes", [])
        self.links = graph.get("links", [])
        self._node_map = {n["id"]: n for n in self.nodes}
        self._port_map = {p["id"]: p for p in graph.get("ports", [])}

    def analyze(self):
        ordered = self._topological_order()
        preprocessing, model_nodes, output_node = self._find_boundaries(ordered)
        optimizers = [n for n in self.nodes if n["type"] == "optimizer"]
        viz_node = next((n for n in self.nodes if n["type"] == "visualization"), None)
        is_seq = self._is_sequential(model_nodes)

        # Simulate data flow for each activation mode
        phases = self._simulate_phases()

        return {
            "preprocessing": {"nodes": preprocessing},
            "model_nodes": model_nodes,
            "output_node": output_node,
            "is_sequential": is_seq,
            "phases": phases,
            "optimizers": optimizers,
            "visualization": viz_node,
        }

    def _simulate_phases(self):
        """Forward simulation: which nodes fire in each activation mode."""
        # Collect all unique activation modes from all ports
        all_modes = set()
        for port in self._port_map.values():
            mode = port.get("activationMode", "every_batch")
            all_modes.add(mode)

        phases = {}
        for mode in all_modes:
            active_nodes = self._simulate_phase(mode)
            # Determine if this phase loops
            is_loop = self._phase_has_optimizer(mode, active_nodes)
            phases[mode] = {
                "nodes": active_nodes,
                "is_loop": is_loop,
            }

        return phases

    def _simulate_phase(self, mode):
        """Forward simulation for a single activation mode.
        Returns set of node IDs that fire in this mode."""

        # Track which output ports produce data
        active_ports = set()
        # Track which nodes fire
        fired_nodes = set()

        # Start from InputData nodes — they always produce data
        input_nodes = [n for n in self.nodes if n["type"] == "input-data"]
        for node in input_nodes:
            for port in node.get("outputPorts", []):
                if self._port_active_in_mode(port, mode):
                    active_ports.add(port["id"])

        # Forward propagation until no new ports activate
        changed = True
        while changed:
            changed = False
            for node in self.nodes:
                if node["id"] in fired_nodes:
                    continue
                if node["type"] == "input-data":
                    continue  # Already handled

                # Check if any input port receives data
                receives_data = False
                for in_port in node.get("inputPorts", []):
                    # Does this port have an incoming link from an active port?
                    for link in self.links:
                        if link["to"] == in_port["id"] and link["from"] in active_ports:
                            if self._port_active_in_mode(in_port, mode):
                                receives_data = True
                                break
                    if receives_data:
                        break

                if receives_data:
                    fired_nodes.add(node["id"])
                    changed = True
                    # Activate output ports that match this mode
                    for out_port in node.get("outputPorts", []):
                        if self._port_active_in_mode(out_port, mode):
                            active_ports.add(out_port["id"])

        return fired_nodes

    def _port_active_in_mode(self, port, mode):
        """Check if a port is active in a given mode."""
        port_mode = port.get("activationMode", "every_batch")
        if port_mode == "both":
            return True
        return port_mode == mode

    def _phase_has_optimizer(self, mode, active_nodes):
        """Check if any optimizer receives data in this phase."""
        for node in self.nodes:
            if node["type"] != "optimizer":
                continue
            if node["id"] in active_nodes:
                return True
        return False

    def _find_boundaries(self, ordered):
        preprocessing = []
        model_nodes = []
        output_node = None
        found_model = False

        for node in ordered:
            if node["type"] in self.OUTPUT_TYPES:
                output_node = node
            elif node["type"] in self.MODEL_TYPES:
                model_nodes.append(node)
                found_model = True
            elif node["type"] in self.PREPROCESSING_TYPES:
                if found_model:
                    model_nodes.append(node)
                else:
                    preprocessing.append(node)

        return preprocessing, model_nodes, output_node

    def _topological_order(self):
        input_nodes = [n for n in self.nodes if n["type"] == "input-data"]
        if not input_nodes:
            return list(self.nodes)

        visited = set()
        result = []

        def dfs(node_id):
            if node_id in visited:
                return
            visited.add(node_id)
            for link in self._links_from(node_id):
                target = self._port_node_id(link["to"])
                if target and target not in visited:
                    dfs(target)
            result.append(node_id)

        for n in input_nodes:
            dfs(n["id"])

        result.reverse()
        return [self._node_map[nid] for nid in result if nid in self._node_map]

    def _is_sequential(self, model_nodes):
        for node in model_nodes:
            if node["type"] in ("add", "concat"):
                return False
            model_ids = {n["id"] for n in model_nodes}
            incoming = [
                l
                for l in self._links_to(node["id"])
                if self._port_node_id(l["from"]) in model_ids
            ]
            if len(incoming) > 1:
                return False
        return True

    def _port_node_id(self, port_id):
        if not port_id:
            return None
        parts = port_id.rsplit("_", 2)
        return parts[0] if len(parts) >= 3 else None

    def _links_from(self, node_id):
        return [l for l in self.links if self._port_node_id(l["from"]) == node_id]

    def _links_to(self, node_id):
        return [l for l in self.links if self._port_node_id(l["to"]) == node_id]
