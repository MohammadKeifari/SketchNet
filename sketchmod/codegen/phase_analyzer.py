from .graph import Graph, parse_graph
from typing import Set, List, Dict, Optional, Any


def _traverse_phase(graph: Graph, phase: str) -> Set[str]:
    """
    Return nodes that are fully active in the given phase.
    A node is active if all its input ports have at least one incoming link
    from an active source port, or it is an InputData node with an active output port.
    """
    active_nodes = set()
    # Determine active input ports for each node
    # We'll iterate until stable
    changed = True
    while changed:
        changed = False
        for nid, node in graph.nodes.items():
            if nid in active_nodes:
                continue
            if node.type == "input-data":
                # active if any output port has the phase
                if any(phase in p.activation_phases for p in node.outputs):
                    active_nodes.add(nid)
                    changed = True
            else:
                # check all input ports are satisfied
                all_satisfied = True
                for in_port in node.inputs:
                    # find at least one incoming link where source port has the phase,
                    # target port has the phase, and source node is already active
                    satisfied = False
                    for link in graph.links:
                        if link.id_to == in_port.id:
                            src_port = graph.ports[link.id_from]
                            tgt_port = graph.ports[link.id_to]  # same as in_port
                            if (
                                phase in src_port.activation_phases
                                and phase in tgt_port.activation_phases
                                and src_port.node_id in active_nodes
                            ):
                                satisfied = True
                                break
                    if not satisfied:
                        all_satisfied = False
                        break
                if all_satisfied and node.inputs:  # must have inputs
                    active_nodes.add(nid)
                    changed = True
                # If node has no inputs, it's InputData (already handled)
    return active_nodes


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
    graph = parse_graph(graph_data)
    active_nodes = _traverse_phase(graph, phase)

    highlighted_links = []
    for link in graph.links:
        src_port = graph.ports[link.id_from]
        tgt_port = graph.ports[link.id_to]
        if (
            phase in src_port.activation_phases
            and phase in tgt_port.activation_phases
            and src_port.node_id in active_nodes
        ):
            highlighted_links.append(f"{link.id_from}→{link.id_to}")

    return {
        "nodes": list(active_nodes),
        "links": highlighted_links,
    }
