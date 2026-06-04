from .graph import Graph, parse_graph
from typing import Set, List, Dict, Any


def _is_port_active(port, phase: str) -> bool:
    """True if the phase is in the port's activationPhases list."""
    return phase in port.activation_phases


# ------------------------------------------------------------
#  STRICT (checkbox‑only) – used for highlight_path
# ------------------------------------------------------------
def _active_nodes_strict(graph: Graph, phase: str) -> Set[str]:
    """Node is active only when every connected port has the phase."""
    active = set()
    for nid, node in graph.nodes.items():
        # inputs
        inputs_ok = True
        for in_port in node.inputs + node.paramInputs:
            if any(link.id_to == in_port.id for link in graph.links):
                if not _is_port_active(in_port, phase):
                    inputs_ok = False
                    break
        if not inputs_ok:
            continue
        # outputs
        outputs_ok = True
        for out_port in node.outputs + node.paramOutputs:
            if any(link.id_from == out_port.id for link in graph.links):
                if not _is_port_active(out_port, phase):
                    outputs_ok = False
                    break
        if outputs_ok:
            active.add(nid)
    return active


# ------------------------------------------------------------
#  CARRY‑OVER (code generation & validation)
# ------------------------------------------------------------
def _traverse_preprocessing(graph: Graph) -> Set[str]:
    """BFS from InputData, following only links where both ports have 'preprocessing'."""
    active = set()
    queue = []
    for nid, node in graph.nodes.items():
        if node.type == "input-data" and any(
            "preprocessing" in p.activation_phases for p in node.outputs
        ):
            active.add(nid)
            queue.append(nid)

    while queue:
        src_id = queue.pop(0)
        for out_port in graph.nodes[src_id].outputs + graph.nodes[src_id].paramOutputs:
            if "preprocessing" not in out_port.activation_phases:
                continue
            for link in graph.links:
                if link.id_from == out_port.id:
                    tgt_port = graph.ports[link.id_to]
                    tgt_id = tgt_port.node_id
                    if tgt_id in active:
                        continue
                    if "preprocessing" not in tgt_port.activation_phases:
                        continue
                    tgt_node = graph.nodes[tgt_id]
                    # all input ports of target must be satisfied by active preprocessing nodes
                    all_inputs_satisfied = True
                    for in_port in tgt_node.inputs + tgt_node.paramInputs:
                        if not any(link2.id_to == in_port.id for link2 in graph.links):
                            continue
                        ok = False
                        for link2 in graph.links:
                            if link2.id_to == in_port.id:
                                src2 = graph.ports[link2.id_from]
                                if (
                                    src2.node_id in active
                                    and "preprocessing" in src2.activation_phases
                                    and "preprocessing" in in_port.activation_phases
                                ):
                                    ok = True
                                    break
                        if not ok:
                            all_inputs_satisfied = False
                            break
                    if all_inputs_satisfied:
                        # also check output ports (node may have outputs that lack preprocessing)
                        outputs_ok = True
                        for p in tgt_node.outputs + tgt_node.paramOutputs:
                            if any(link3.id_from == p.id for link3 in graph.links):
                                if "preprocessing" not in p.activation_phases:
                                    outputs_ok = False
                                    break
                        if outputs_ok:
                            active.add(tgt_id)
                            queue.append(tgt_id)
    return active


def _traverse_train_eval(graph: Graph, phase: str, pre_set: Set[str]) -> Set[str]:
    """
    Training / Evaluation traversal.
    - Links from preprocessing nodes (in pre_set) are allowed even if the source
      port lacks the phase (carry‑over).
    - OutputNode only needs one active input and one active output.
    - Param ports from preprocessing nodes are always satisfied (carry‑over).
    """
    active = set()
    changed = True
    while changed:
        changed = False
        for nid, node in graph.nodes.items():
            if nid in active:
                continue

            # ----- Input check -----
            if node.type == "output":
                # relaxed: only need one satisfied input
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
                            ):
                                inputs_ok = True
                                break
                    if inputs_ok:
                        break
            else:
                inputs_ok = True
                for in_port in node.inputs + node.paramInputs:
                    if not any(link.id_to == in_port.id for link in graph.links):
                        continue
                    port_satisfied = False
                    for link in graph.links:
                        if link.id_to == in_port.id:
                            src_port = graph.ports[link.id_from]
                            src_nid = src_port.node_id
                            # Normal flow
                            if (
                                src_nid in active
                                and _is_port_active(src_port, phase)
                                and _is_port_active(in_port, phase)
                            ) or (
                                src_nid in pre_set and _is_port_active(in_port, phase)
                            ):
                                port_satisfied = True
                                break
                            # Param port carry‑over: ignore phase if source is preprocessing
                            if in_port.port_kind == "param" and src_nid in pre_set:
                                port_satisfied = True
                                break
                    if not port_satisfied:
                        inputs_ok = False
                        break

            if not inputs_ok:
                continue

            # ----- Output check -----
            outputs_ok = True
            if node.type == "output":
                any_output_active = False
                for out_port in node.outputs:
                    if any(link.id_from == out_port.id for link in graph.links):
                        if _is_port_active(out_port, phase):
                            any_output_active = True
                            break
                outputs_ok = any_output_active
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
        "preprocessing_set": pre_set,
        "train_set": train_set,
        "eval_set": eval_set,
        "optimizer": opt_node,
        "visualizations": viz_nodes,
    }


def highlight_path(graph_data: dict, phase: str) -> dict:
    graph = parse_graph(graph_data)
    active_nodes = _active_nodes_strict(graph, phase)
    highlighted_links = []
    for link in graph.links:
        src = graph.ports[link.id_from]
        tgt = graph.ports[link.id_to]
        if _is_port_active(src, phase) and _is_port_active(tgt, phase):
            highlighted_links.append(f"{link.id_from}→{link.id_to}")
    return {"nodes": list(active_nodes), "links": highlighted_links}
