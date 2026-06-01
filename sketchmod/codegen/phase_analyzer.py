from .graph import Graph
from typing import Set, List, Dict


def _traverse_phase(graph: Graph, phase: str) -> Set[str]:
    """Return nodes reachable when only links with `phase` in source port's activation_phases are active."""
    reached = set()
    # Start from input-data nodes if they have outputs with this phase, or any node with an input connected from such a source.
    # Simpler: iterate through all links; if source port has phase, and source node is reached, then target node becomes reached.
    # BFS
    # Initialize: any node whose input ports are all fed from ports that have the phase? Actually we follow the rule:
    # A node is reached if at least one input port receives data (from a source port with phase) and the source node is reached.
    # InputData node is always considered "reached" (it has no inputs).
    for nid, node in graph.nodes.items():
        if node.type == "input-data":
            # check if any of its output ports has the phase, then node can be start
            if any(phase in p.activation_phases for p in node.outputs):
                reached.add(nid)
    # BFS
    queue = list(reached)
    while queue:
        src_id = queue.pop(0)
        src_node = graph.nodes[src_id]
        for out_port in src_node.outputs:
            if phase in out_port.activation_phases:
                for link in graph.links:
                    if link.id_from == out_port.id:
                        tgt_port = graph.ports[link.id_to]
                        tgt_id = tgt_port.node_id
                        if tgt_id not in reached:
                            reached.add(tgt_id)
                            queue.append(tgt_id)
    return reached


def analyze_phases(graph: Graph) -> Dict:
    pre_set = _traverse_phase(graph, "preprocessing")
    train_set = _traverse_phase(graph, "training")
    eval_set = _traverse_phase(graph, "evaluation")

    # Topological sort within each set
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

    pre_order = topo_sort(pre_set)
    train_order = topo_sort(train_set)
    eval_order = topo_sort(eval_set)

    # Find optimizer node (should be in train_set)
    opt_node = None
    for nid in train_set:
        if graph.nodes[nid].type == "optimizer":
            opt_node = graph.nodes[nid]
            break

    # Find visualization nodes (should be in eval_set)
    viz_nodes = [
        graph.nodes[nid] for nid in eval_set if graph.nodes[nid].type == "visualization"
    ]

    return {
        "preprocessing_order": pre_order,
        "train_order": train_order,
        "eval_order": eval_order,
        "optimizer": opt_node,
        "visualizations": viz_nodes,
    }
