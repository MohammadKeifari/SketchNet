from .graph import Graph, parse_graph
from typing import Set, List, Dict, Optional, Any


def _traverse_phase(graph: Graph, phase: str) -> Set[str]:
    """
    BFS traversal that follows links whose source port has `phase` in its
    activation_phases list.  Returns the set of node IDs reachable.
    """
    reached = set()

    # InputData nodes are always considered "reached" if they have an output
    # port with this phase.
    for nid, node in graph.nodes.items():
        if node.type == "input-data":
            if any(phase in p.activation_phases for p in node.outputs):
                reached.add(nid)

    queue = list(reached)

    while queue:
        src_id = queue.pop(0)
        src_node = graph.nodes[src_id]

        for out_port in src_node.outputs:
            if phase not in out_port.activation_phases:
                continue

            for link in graph.links:
                if link.id_from == out_port.id:
                    tgt_port = graph.ports[link.id_to]
                    tgt_id = tgt_port.node_id
                    if tgt_id not in reached:
                        reached.add(tgt_id)
                        queue.append(tgt_id)

    return reached


def _topo_sort(nids: Set[str], graph: Graph) -> List[str]:
    """Kahn's algorithm on the sub‑graph induced by nids."""
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


def analyze_phases(graph: Graph) -> Dict[str, Any]:
    """
    Returns a dictionary with:
        - preprocessing_order : topo‑sorted list of node ids in preprocessing phase
        - train_order         : topo‑sorted list for training phase
        - eval_order          : topo‑sorted list for evaluation phase
        - optimizer           : the optimizer Node (if any)
        - visualizations      : list of visualization Nodes
    """
    pre_set = _traverse_phase(graph, "preprocessing")
    train_set = _traverse_phase(graph, "training")
    eval_set = _traverse_phase(graph, "evaluation")

    pre_order = _topo_sort(pre_set, graph)
    train_order = _topo_sort(train_set, graph)
    eval_order = _topo_sort(eval_set, graph)

    # Find optimizer node (should be in training phase)
    opt_node = None
    for nid in train_set:
        if graph.nodes[nid].type == "optimizer":
            opt_node = graph.nodes[nid]
            break

    # Find visualization nodes (should be in evaluation phase)
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


def highlight_path(graph_data: dict, phase: str) -> dict:
    """
    API helper: given the raw graph JSON and a phase name,
    returns a dict with 'nodes' (list of node IDs) and 'links'
    (list of link keys like "fromPortId→toPortId") that are active
    in that phase.
    """
    graph = parse_graph(graph_data)
    reached_nodes = _traverse_phase(graph, phase)

    highlighted_links = []
    for link in graph.links:
        src_port = graph.ports[link.id_from]
        if phase in src_port.activation_phases and src_port.node_id in reached_nodes:
            highlighted_links.append(f"{link.id_from}→{link.id_to}")

    return {
        "nodes": list(reached_nodes),
        "links": highlighted_links,
    }
