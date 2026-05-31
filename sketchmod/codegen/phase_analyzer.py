from .graph import Graph, Node
from typing import Set, List, Dict, Tuple, Optional

# Node type categories
DATA_TRANSFORM_TYPES = {
    "column-select",
    "row-select",
    "dim-select",
    "normalize",
    "onehot",
    "train-test",
}
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
OUTPUT_TYPE = "output"
INPUT_DATA_TYPE = "input-data"
OPTIMIZER_TYPE = "optimizer"
VISUALIZATION_TYPE = "visualization"


def _traverse_phase(graph: Graph, phase: str) -> Set[str]:
    """
    phase: "train" (every_batch/both) or "eval" (last_batch/both)
    Returns set of node ids that are reachable and fully satisfied.
    """
    # Find start nodes (input-data)
    start_nodes = [
        nid for nid, node in graph.nodes.items() if node.type == INPUT_DATA_TYPE
    ]
    # Track which input ports of each node have an active incoming link
    active_inputs = {
        nid: {p.id: False for p in graph.nodes[nid].inputs} for nid in graph.nodes
    }
    reached_nodes = set(start_nodes)

    # BFS: node becomes active when all its inputs have at least one active link.
    # We'll iterate until no change.
    changed = True
    while changed:
        changed = False
        # For each node, check if all inputs are satisfied.
        for nid, node in graph.nodes.items():
            if nid in reached_nodes:
                continue
            all_inputs_satisfied = True
            for in_port in node.inputs:
                # Check if any link to this input is active in this phase
                found_active = False
                for link in graph.links:
                    if link.id_to == in_port.id:
                        src_port = graph.ports[link.id_from]
                        if (
                            phase == "train"
                            and src_port.activation_mode in ("every_batch", "both")
                        ) or (
                            phase == "eval"
                            and src_port.activation_mode in ("last_batch", "both")
                        ):
                            # also check that the source node is reached
                            if src_port.node_id in reached_nodes:
                                found_active = True
                                break
                if not found_active:
                    all_inputs_satisfied = False
                    break
            if all_inputs_satisfied:
                reached_nodes.add(nid)
                changed = True
    return reached_nodes


def analyze_phases(graph: Graph) -> Dict:
    # Get train and eval sets
    train_set = _traverse_phase(graph, "train")
    eval_set = _traverse_phase(graph, "eval")

    # Preprocessing: nodes in both sets, but exclude model types and output
    common = train_set.intersection(eval_set)
    preprocessing_set = {
        nid
        for nid in common
        if graph.nodes[nid].type not in MODEL_TYPES
        and graph.nodes[nid].type != OUTPUT_TYPE
    }

    # Train-specific data nodes (not in preprocessing and not model)
    train_data = (train_set - preprocessing_set) - {
        nid
        for nid in train_set
        if graph.nodes[nid].type in MODEL_TYPES or graph.nodes[nid].type == OUTPUT_TYPE
    }
    # Train model nodes (including output)
    train_model = (train_set - preprocessing_set) & {
        nid
        for nid in train_set
        if graph.nodes[nid].type in MODEL_TYPES or graph.nodes[nid].type == OUTPUT_TYPE
    }

    # Eval data and model
    eval_data = (eval_set - preprocessing_set) - {
        nid
        for nid in eval_set
        if graph.nodes[nid].type in MODEL_TYPES or graph.nodes[nid].type == OUTPUT_TYPE
    }
    eval_model = (eval_set - preprocessing_set) & {
        nid
        for nid in eval_set
        if graph.nodes[nid].type in MODEL_TYPES or graph.nodes[nid].type == OUTPUT_TYPE
    }

    # Topological sort for each group
    def topo_sort(nids: Set[str]) -> List[str]:
        # Kahn's algorithm on subgraph induced by nids
        in_degree = {nid: 0 for nid in nids}
        adj = {nid: [] for nid in nids}
        for nid in nids:
            for succ in graph.successors(nid):
                if succ in nids:
                    adj[nid].append(succ)
                    in_degree[succ] += 1
        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        order = []
        while queue:
            nid = queue.pop(0)
            order.append(nid)
            for succ in adj[nid]:
                in_degree[succ] -= 1
                if in_degree[succ] == 0:
                    queue.append(succ)
        return order

    preprocessing_order = topo_sort(preprocessing_set)
    train_data_order = topo_sort(train_data)
    train_model_order = topo_sort(train_model)
    eval_data_order = topo_sort(eval_data)
    eval_model_order = topo_sort(eval_model)

    # Find optimizer node (should be in train set)
    opt_node = None
    for nid in train_set:
        if graph.nodes[nid].type == OPTIMIZER_TYPE:
            opt_node = graph.nodes[nid]
            break

    # Find visualization nodes (in eval set usually)
    viz_nodes = [
        graph.nodes[nid]
        for nid in eval_set
        if graph.nodes[nid].type == VISUALIZATION_TYPE
    ]

    return {
        "preprocessing_order": preprocessing_order,
        "train_data_order": train_data_order,
        "train_model_order": train_model_order,
        "eval_data_order": eval_data_order,
        "eval_model_order": eval_model_order,
        "optimizer": opt_node,
        "visualizations": viz_nodes,
    }
