"""
Flow Analyzer — analyzes the node graph to determine execution phases,
model boundaries, port activation, and code generation structure.
"""


class FlowAnalyzer:
    """Analyzes a SketchNet graph for code generation."""

    # Node type categories
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
    CONFIG_TYPES = {"optimizer", "visualization"}

    def __init__(self, graph):
        self.nodes = graph.get("nodes", [])
        self.links = graph.get("links", [])
        self.ports = graph.get("ports", [])
        self._node_map = {n["id"]: n for n in self.nodes}
        self._port_map = {p["id"]: p for p in self.ports}

    # ========== PUBLIC API ==========

    def analyze(self):
        """Run full analysis. Returns structured flow data."""
        ordered = self._topological_order()
        preprocessing, model_nodes, output_node = self._find_boundaries(ordered)

        # Find all optimizers
        optimizers = [n for n in self.nodes if n["type"] == "optimizer"]
        viz_node = next((n for n in self.nodes if n["type"] == "visualization"), None)

        # Build phase information
        phases = self._build_phases(model_nodes, output_node, optimizers)

        # Determine if model is sequential
        is_seq = self._is_sequential(model_nodes)

        return {
            "preprocessing": {
                "nodes": preprocessing,
            },
            "model_nodes": model_nodes,
            "output_node": output_node,
            "is_sequential": is_seq,
            "phases": phases,
            "optimizers": optimizers,
            "visualization": viz_node,
        }

    # ========== TOPOLOGICAL SORT ==========

    def _topological_order(self):
        """Return nodes in topological order from inputs to outputs."""
        input_nodes = self._find_by_type("input-data")
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

    # ========== BOUNDARY DETECTION ==========

    def _find_boundaries(self, ordered_nodes):
        """Split ordered nodes into preprocessing, model, and output."""
        preprocessing = []
        model_nodes = []
        output_node = None

        for node in ordered_nodes:
            if node["type"] in self.OUTPUT_TYPES:
                output_node = node
            elif node["type"] in self.MODEL_TYPES:
                # Everything from first model node onward is model (except config)
                if not model_nodes:
                    # First model node — all previous are preprocessing
                    pass
                model_nodes.append(node)
            elif node["type"] in self.PREPROCESSING_TYPES:
                if not model_nodes:
                    preprocessing.append(node)
                # else: preprocessing node after model start? unusual but allowed
            # CONFIG_TYPES are handled separately, not in these lists

        return preprocessing, model_nodes, output_node

    # ========== PHASE BUILDING ==========

    def _build_phases(self, model_nodes, output_node, optimizers):
        """Build training and evaluation phase descriptions."""
        phases = {
            "training": {
                "nodes": [],
                "active_ports": [],
                "loop": "epochs × batches",
                "data_sources": [],
            },
            "evaluation": {
                "nodes": [],
                "active_ports": [],
                "loop": "single pass, no_grad",
                "data_sources": [],
            },
        }

        if not output_node:
            return phases

        # Determine which output ports belong to which phase
        for port_data in output_node.get("outputPorts", []):
            role = port_data.get("role", "")
            port_id = port_data["id"]

            if role == "loss":
                phases["training"]["active_ports"].append(port_id)
            elif role in ("prediction", "evaluation"):
                phases["evaluation"]["active_ports"].append(port_id)

        # Model nodes are shared — they run in both phases
        phases["training"]["nodes"] = model_nodes
        phases["evaluation"]["nodes"] = model_nodes

        # Find data sources for each phase
        for phase_name, phase_data in phases.items():
            sources = self._find_phase_data_sources(phase_name, output_node)
            phase_data["data_sources"] = sources

        # Attach optimizers to training phase
        for opt in optimizers:
            phases["training"].setdefault("optimizers", []).append(opt)

        return phases

    def _find_phase_data_sources(self, phase, output_node):
        """Find which ports feed data into this phase."""
        wanted_role = "train" if phase == "training" else "test"
        sources = []

        # Check output node's input ports
        for port_data in output_node.get("inputPorts", []):
            if port_data.get("subType") == wanted_role:
                # Trace backward to find the source
                incoming = self._links_to_port(port_data["id"])
                for link in incoming:
                    src_port = self._get_port(link["from"])
                    if src_port:
                        sources.append(
                            {
                                "port_id": link["from"],
                                "node_id": self._port_node_id(link["from"]),
                                "subType": src_port.get("subType"),
                            }
                        )

        return sources

    # ========== SEQUENTIAL CHECK ==========

    def _is_sequential(self, model_nodes):
        """Check if model nodes form a simple chain (can use nn.Sequential)."""
        for node in model_nodes:
            if node["type"] in ("add", "concat"):
                return False
            # Check for multiple incoming connections within model
            incoming = [
                l
                for l in self._links_to(node["id"])
                if self._port_node_id(l["from"]) in {n["id"] for n in model_nodes}
            ]
            if len(incoming) > 1:
                return False
        return True

    # ========== PORT HELPERS ==========

    def _get_port(self, port_id):
        return self._port_map.get(port_id)

    def _port_node_id(self, port_id):
        """Extract node ID from port ID like 'n1_output_0'."""
        if not port_id:
            return None
        parts = port_id.rsplit("_", 2)
        if len(parts) >= 3:
            return parts[0]
        return None

    def _links_from(self, node_id):
        """All links where source is this node."""
        return [l for l in self.links if self._port_node_id(l["from"]) == node_id]

    def _links_to(self, node_id):
        """All links where target is this node."""
        return [l for l in self.links if self._port_node_id(l["to"]) == node_id]

    def _links_to_port(self, port_id):
        """All links where target is this specific port."""
        return [l for l in self.links if l["to"] == port_id]

    def _find_by_type(self, node_type):
        return [n for n in self.nodes if n["type"] == node_type]
