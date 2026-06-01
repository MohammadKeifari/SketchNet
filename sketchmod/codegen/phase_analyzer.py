from .graph import Graph, parse_graph
from typing import Set, List, Dict, Any


def _traverse_phase(graph: Graph, phase: str, pre_set: Set[str] = None) -> Set[str]:
    """
    Returns the set of node IDs that are fully active in the given phase.
    - pre_set: if provided (for training/evaluation), contains nodes that belong to the
      PREPROCESSING phase. They are NOT added to the active set, but their output ports
      are allowed to feed into the current phase (see _is_link_active).
    """
    active_nodes = set()

    # Initial seeds
    if pre_set is None:
        # Preprocessing: start from InputData nodes that have a 'preprocessing' output
        for nid, node in graph.nodes.items():
            if node.type == "input-data" and any(
                "preprocessing" in p.activation_phases for p in node.outputs
            ):
                active_nodes.add(nid)
    # Training/evaluation: no initial seeds (preprocessing nodes are NOT active)

    changed = True
    while changed:
        changed = False
        for nid, node in graph.nodes.items():
            if nid in active_nodes:
                continue

            # ---- Check all input ports ----
            inputs_ok = True
            for in_port in node.inputs + node.paramInputs:
                port_satisfied = False
                for link in graph.links:
                    if link.id_to == in_port.id:
                        src_port = graph.ports[link.id_from]
                        src_nid = src_port.node_id

                        # Is this link "active" for the current phase?
                        if _is_link_active(link, phase, pre_set, active_nodes, graph):
                            port_satisfied = True
                            break
                if not port_satisfied:
                    inputs_ok = False
                    break

            if not inputs_ok:
                continue

            # ---- Check all output ports ----
            outputs_ok = True
            if node.outputs:  # only if the node has outputs
                for out_port in node.outputs:
                    # If this output port has any outgoing link, it MUST have the phase
                    has_link = any(l.id_from == out_port.id for l in graph.links)
                    if has_link and phase not in out_port.activation_phases:
                        outputs_ok = False
                        break

            if outputs_ok and (node.inputs or node.paramInputs):
                active_nodes.add(nid)
                changed = True

    return active_nodes


def _is_link_active(link, phase, pre_set, active_nodes, graph):
    """
    Returns True if the link can be used to satisfy an input during the given phase.
    This is separate from visual highlighting; it determines whether data can flow.
    """
    src_port = graph.ports[link.id_from]
    tgt_port = graph.ports[link.id_to]
    src_nid = src_port.node_id

    if phase == "preprocessing":
        # Strict rule: both ports must have 'preprocessing' AND source node active
        return (
            "preprocessing" in src_port.activation_phases
            and "preprocessing" in tgt_port.activation_phases
            and src_nid in active_nodes
        )
    else:
        # Training / Evaluation
        # 1. Normal flow: source node is active in this phase and source port has the phase
        if src_nid in active_nodes and phase in src_port.activation_phases:
            return True
        # 2. Carry-over from preprocessing: source node is in pre_set (not active),
        #    source port is an output, and target port has the phase
        if pre_set is not None and src_nid in pre_set and src_port.type == "output":
            return phase in tgt_port.activation_phases
        return False


def _topo_sort(nids: Set[str], graph: Graph) -> List[str]:
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
    pre_set = _traverse_phase(graph, "preprocessing", pre_set=None)
    train_set = _traverse_phase(graph, "training", pre_set=pre_set)
    eval_set = _traverse_phase(graph, "evaluation", pre_set=pre_set)

    pre_order = _topo_sort(pre_set, graph)
    train_order = _topo_sort(train_set, graph)
    eval_order = _topo_sort(eval_set, graph)

    opt_node = next(
        (graph.nodes[nid] for nid in train_set if graph.nodes[nid].type == "optimizer"),
        None,
    )
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
    pre_set = _traverse_phase(graph, "preprocessing", pre_set=None)

    if phase == "preprocessing":
        active_nodes = pre_set
    else:
        active_nodes = _traverse_phase(graph, phase, pre_set=pre_set)

    highlighted_links = []
    for link in graph.links:
        if _should_highlight_link(link, phase, pre_set, active_nodes, graph):
            highlighted_links.append(f"{link.id_from}→{link.id_to}")

    return {"nodes": list(active_nodes), "links": highlighted_links}


def _should_highlight_link(link, phase, pre_set, active_nodes, graph):
    """Visual highlighting rule: same as activation, except for training/eval we allow
    links from preprocessing outputs even if the source port lacks the phase."""
    src_port = graph.ports[link.id_from]
    tgt_port = graph.ports[link.id_to]
    src_nid = src_port.node_id

    if phase == "preprocessing":
        return (
            "preprocessing" in src_port.activation_phases
            and "preprocessing" in tgt_port.activation_phases
            and src_nid in active_nodes
        )
    else:
        # Normal flow
        if (
            src_nid in active_nodes
            and phase in src_port.activation_phases
            and phase in tgt_port.activation_phases
        ):
            return True
        # Carry-over from preprocessing: source node in pre_set, source port is output,
        # and target port has the phase (source port's phases are ignored)
        if pre_set is not None and src_nid in pre_set and src_port.type == "output":
            return phase in tgt_port.activation_phases
        return False
