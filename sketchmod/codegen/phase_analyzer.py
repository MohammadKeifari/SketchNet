from .graph import Graph, parse_graph
from typing import Set, List, Dict, Any


def _is_port_active(port, phase: str) -> bool:
    """A port is active for a phase if the phase is in its activationPhases list."""
    return phase in port.activation_phases


def _active_nodes(graph: Graph, phase: str) -> Set[str]:
    """
    Nodes that are fully active in the given phase.
    A node is active only when **every** connected port (input or output)
    that has at least one link is active for that phase.
    """
    active = set()
    for nid, node in graph.nodes.items():
        # --- inputs ---
        inputs_ok = True
        for in_port in node.inputs + node.paramInputs:
            # ignore ports that have no incoming links
            if any(link.id_to == in_port.id for link in graph.links):
                if not _is_port_active(in_port, phase):
                    inputs_ok = False
                    break
        if not inputs_ok:
            continue

        # --- outputs ---
        outputs_ok = True
        for out_port in node.outputs + node.paramOutputs:
            if any(link.id_from == out_port.id for link in graph.links):
                if not _is_port_active(out_port, phase):
                    outputs_ok = False
                    break
        if outputs_ok:
            active.add(nid)
    return active


def _topo_sort(nids: Set[str], graph: Graph) -> List[str]:
    """Kahn's topological sort for the subset of nodes."""
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
    Returns the node sets and topological orders for each phase,
    based purely on the user's activationPhases checkboxes.
    """
    pre_set = _active_nodes(graph, "preprocessing")
    train_set = _active_nodes(graph, "training")
    eval_set = _active_nodes(graph, "evaluation")

    pre_order = _topo_sort(pre_set, graph)
    train_order = _topo_sort(train_set, graph)
    eval_order = _topo_sort(eval_set, graph)

    # Optimizer is always part of training
    opt_node = next(
        (graph.nodes[nid] for nid in train_set if graph.nodes[nid].type == "optimizer"),
        None,
    )

    # Visualization nodes belong to evaluation
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
    API helper – returns the list of active nodes and highlighted links
    for the chosen phase, using the same checkbox rules.
    """
    graph = parse_graph(graph_data)
    active_nodes = _active_nodes(graph, phase)

    highlighted_links = []
    for link in graph.links:
        src_port = graph.ports[link.id_from]
        tgt_port = graph.ports[link.id_to]
        if _is_port_active(src_port, phase) and _is_port_active(tgt_port, phase):
            highlighted_links.append(f"{link.id_from}→{link.id_to}")

    return {"nodes": list(active_nodes), "links": highlighted_links}
