from .graph import Graph, parse_graph
from typing import Set, List, Dict, Any


def _traverse_phase(graph: Graph, phase: str, pre_set: Set[str] = None) -> Set[str]:
    """
    pre_set: set of node ids that belong to the PREPROCESSING phase.
    For training/evaluation, we do NOT include those nodes in the returned set,
    but we allow links from them to carry data into the current phase.
    """
    active_nodes = set()

    if pre_set is None:
        # Preprocessing phase – only InputData with 'preprocessing' output can start
        for nid, node in graph.nodes.items():
            if node.type == "input-data" and any(
                "preprocessing" in p.activation_phases for p in node.outputs
            ):
                active_nodes.add(nid)
    else:
        # Training / Evaluation – start with empty set (preprocessing nodes are NOT active)
        pass  # active_nodes remains empty

    changed = True
    while changed:
        changed = False
        for nid, node in graph.nodes.items():
            if nid in active_nodes:
                continue

            # ----- check all input ports (data, multi, role, param) -----
            inputs_ok = True
            for in_port in node.inputs + node.paramInputs:
                satisfied = False
                for link in graph.links:
                    if link.id_to == in_port.id:
                        src_port = graph.ports[link.id_from]
                        src_nid = src_port.node_id

                        if pre_set is None:
                            # Preprocessing phase: both ports must have 'preprocessing'
                            if (
                                "preprocessing" in src_port.activation_phases
                                and "preprocessing" in in_port.activation_phases
                                and src_nid in active_nodes
                            ):
                                satisfied = True
                                break
                        else:
                            # Training/Evaluation phase:
                            # - if source node is already active in this phase → normal check
                            # - if source node is in preprocessing set → allow as long as
                            #   the source port is an output (preprocessing outputs are always available)
                            if src_nid in active_nodes:
                                if phase in src_port.activation_phases:
                                    satisfied = True
                                    break
                            elif pre_set is not None and src_nid in pre_set:
                                # Preprocessing node – its outputs are available
                                if src_port.type == "output":
                                    satisfied = True
                                    break
                if not satisfied:
                    inputs_ok = False
                    break

            if not inputs_ok:
                continue

            # ----- check output ports (only for training/evaluation) -----
            outputs_ok = True
            if pre_set is not None:
                for out_port in node.outputs:
                    has_link = any(link.id_from == out_port.id for link in graph.links)
                    if has_link and phase not in out_port.activation_phases:
                        outputs_ok = False
                        break

            if outputs_ok and (node.inputs or node.paramInputs):
                active_nodes.add(nid)
                changed = True

    return active_nodes


def highlight_path(graph_data: dict, phase: str) -> dict:
    graph = parse_graph(graph_data)
    pre_set = _traverse_phase(graph, "preprocessing", pre_set=None)

    if phase == "preprocessing":
        active_nodes = pre_set
    else:
        active_nodes = _traverse_phase(graph, phase, pre_set=pre_set)

    highlighted_links = []
    for link in graph.links:
        src_port = graph.ports[link.id_from]
        tgt_port = graph.ports[link.id_to]
        if phase == "preprocessing":
            if (
                "preprocessing" in src_port.activation_phases
                and src_port.node_id in active_nodes
            ):
                highlighted_links.append(f"{link.id_from}→{link.id_to}")
        else:
            # Link is highlighted if source node is active (or is in preprocessing)
            # and the link carries data into the phase.
            src_nid = src_port.node_id
            if (src_nid in active_nodes or src_nid in pre_set) and (
                phase in src_port.activation_phases
                or (src_nid in pre_set and src_port.type == "output")
            ):
                highlighted_links.append(f"{link.id_from}→{link.id_to}")

    return {"nodes": list(active_nodes), "links": highlighted_links}


def _topo_sort(nids: Set[str], graph: Graph) -> List[str]:
    # same as before
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
    # 1. Preprocessing phase
    pre_set = _traverse_phase(graph, "preprocessing", pre_set=None)
    # 2. Training phase – start from preprocessing nodes
    train_set = _traverse_phase(graph, "training", pre_set=pre_set)
    # 3. Evaluation phase – start from preprocessing nodes
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
        src_port = graph.ports[link.id_from]
        tgt_port = graph.ports[link.id_to]
        if phase == "preprocessing":
            if (
                "preprocessing" in src_port.activation_phases
                and src_port.node_id in active_nodes
            ):
                highlighted_links.append(f"{link.id_from}→{link.id_to}")
        else:
            if src_port.node_id in active_nodes and (
                phase in src_port.activation_phases
                or (src_port.node_id in pre_set and src_port.type == "output")
            ):
                highlighted_links.append(f"{link.id_from}→{link.id_to}")

    return {"nodes": list(active_nodes), "links": highlighted_links}
