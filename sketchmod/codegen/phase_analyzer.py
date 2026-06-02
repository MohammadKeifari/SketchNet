from .graph import Graph, parse_graph
from typing import Set, List, Dict, Any


def _is_port_active(port, phase: str) -> bool:
    return phase in port.activation_phases


def _traverse_preprocessing(graph: Graph) -> Set[str]:
    """BFS from InputData nodes, following only links where both ports have 'preprocessing'."""
    active = set()
    queue = []

    # start from InputData nodes that have a preprocessing output
    for nid, node in graph.nodes.items():
        if node.type == "input-data" and any(
            _is_port_active(p, "preprocessing") for p in node.outputs
        ):
            active.add(nid)
            queue.append(nid)

    while queue:
        src_id = queue.pop(0)
        src_node = graph.nodes[src_id]
        for out_port in src_node.outputs + src_node.paramOutputs:
            if not _is_port_active(out_port, "preprocessing"):
                continue
            for link in graph.links:
                if link.id_from == out_port.id:
                    tgt_port = graph.ports[link.id_to]
                    tgt_id = tgt_port.node_id
                    if tgt_id in active:
                        continue
                    # Target port must have "preprocessing"
                    if not _is_port_active(tgt_port, "preprocessing"):
                        continue
                    # All input ports of the target node must be satisfied by active preprocessing nodes
                    tgt_node = graph.nodes[tgt_id]
                    all_inputs_satisfied = True
                    for in_port in tgt_node.inputs + tgt_node.paramInputs:
                        if not any(link2.id_to == in_port.id for link2 in graph.links):
                            continue
                        port_ok = False
                        for link2 in graph.links:
                            if link2.id_to == in_port.id:
                                src2 = graph.ports[link2.id_from]
                                if (
                                    src2.node_id in active
                                    and _is_port_active(src2, "preprocessing")
                                    and _is_port_active(in_port, "preprocessing")
                                ):
                                    port_ok = True
                                    break
                        if not port_ok:
                            all_inputs_satisfied = False
                            break
                    if all_inputs_satisfied:
                        active.add(tgt_id)
                        queue.append(tgt_id)

    # Now filter out nodes that have output ports with links that are not "preprocessing"
    final = set()
    for nid in active:
        node = graph.nodes[nid]
        outputs_ok = True
        for out_port in node.outputs + node.paramOutputs:
            if any(link.id_from == out_port.id for link in graph.links):
                if not _is_port_active(out_port, "preprocessing"):
                    outputs_ok = False
                    break
        if outputs_ok:
            final.add(nid)
    return final


def _traverse_train_eval(graph: Graph, phase: str, pre_set: Set[str]) -> Set[str]:
    """
    Training / Evaluation traversal.
    Nodes become active if:
      - For 'output', 'optimizer', 'visualization': at least one connected input port is satisfied.
      - For all other nodes: every connected input port must be satisfied.
      - All connected output ports must have the phase (OutputNode only needs at least one active output).
    Links from preprocessing nodes (in pre_set) always satisfy the target input if the target port has the phase.
    """
    active = set()
    changed = True
    while changed:
        changed = False
        for nid, node in graph.nodes.items():
            if nid in active:
                continue

            # ----- Determine how strict the input check should be -----
            strict_inputs = node.type not in ("output", "optimizer", "visualization")

            if strict_inputs:
                inputs_ok = True
                for in_port in node.inputs + node.paramInputs:
                    if not any(link.id_to == in_port.id for link in graph.links):
                        continue
                    port_satisfied = False
                    for link in graph.links:
                        if link.id_to == in_port.id:
                            src_port = graph.ports[link.id_from]
                            src_nid = src_port.node_id
                            if (
                                src_nid in active
                                and _is_port_active(src_port, phase)
                                and _is_port_active(in_port, phase)
                            ) or (
                                src_nid in pre_set and _is_port_active(in_port, phase)
                            ):
                                port_satisfied = True
                                break
                    if not port_satisfied:
                        inputs_ok = False
                        break
            else:
                # Relaxed: only need ONE connected input to be satisfied
                inputs_ok = False
                for in_port in node.inputs + node.paramInputs:
                    if not any(link.id_to == in_port.id for link in graph.links):
                        continue
                    for link in graph.links:
                        if link.id_to == in_port.id:
                            src_port = graph.ports[link.id_from]
                            src_nid = src_port.node_id
                            if (
                                src_nid in active
                                and _is_port_active(src_port, phase)
                                and _is_port_active(in_port, phase)
                            ) or (
                                src_nid in pre_set and _is_port_active(in_port, phase)
                            ):
                                inputs_ok = True
                                break
                    if inputs_ok:
                        break

            if not inputs_ok:
                continue

            # ----- Check outputs -----
            outputs_ok = True
            if node.type == "output":
                any_output_active = False
                has_linked_output = False
                for out_port in node.outputs:
                    if any(link.id_from == out_port.id for link in graph.links):
                        has_linked_output = True
                        if _is_port_active(out_port, phase):
                            any_output_active = True
                            break
                outputs_ok = any_output_active if has_linked_output else True
            else:
                for out_port in node.outputs + node.paramOutputs:
                    if any(link.id_from == out_port.id for link in graph.links):
                        if not _is_port_active(out_port, phase):
                            outputs_ok = False
                            break

            if outputs_ok:
                active.add(nid)
                changed = True

    return active


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
    pre_set = _traverse_preprocessing(graph)
    train_set = _traverse_train_eval(graph, "training", pre_set)
    eval_set = _traverse_train_eval(graph, "evaluation", pre_set)

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
    pre_set = _traverse_preprocessing(graph)

    if phase == "preprocessing":
        active_nodes = pre_set
    else:
        active_nodes = _traverse_train_eval(graph, phase, pre_set)

    highlighted_links = []
    for link in graph.links:
        src = graph.ports[link.id_from]
        tgt = graph.ports[link.id_to]
        if phase == "preprocessing":
            if (
                _is_port_active(src, "preprocessing")
                and _is_port_active(tgt, "preprocessing")
                and src.node_id in active_nodes
            ):
                highlighted_links.append(f"{link.id_from}→{link.id_to}")
        else:
            # link is highlighted if target port has the phase and (source is active or source is preprocessing)
            if _is_port_active(tgt, phase):
                if src.node_id in active_nodes and _is_port_active(src, phase):
                    highlighted_links.append(f"{link.id_from}→{link.id_to}")
                elif src.node_id in pre_set:  # carry-over from preprocessing
                    highlighted_links.append(f"{link.id_from}→{link.id_to}")
    return {"nodes": list(active_nodes), "links": highlighted_links}
