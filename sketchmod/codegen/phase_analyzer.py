"""
Phase analysis for SketchNet graphs.
"""

from __future__ import annotations
from typing import Set, List, Dict, Tuple, Optional
from .graph import Graph, Node, Port, parse_graph


def _has_phase(port: Port, phase: str) -> bool:
    return phase in port.activation_phases


def _get_connected_data_inputs(node: Node, graph: Graph) -> List[Port]:
    connected = []
    for port in node.inputs:
        if port.port_kind == "data" and any(l.id_to == port.id for l in graph.links):
            connected.append(port)
    return connected


def _get_connected_param_inputs(node: Node, graph: Graph) -> List[Port]:
    connected = []
    for port in node.paramInputs:
        if any(l.id_to == port.id for l in graph.links):
            connected.append(port)
    return connected


def _is_data_input_satisfied(
    port: Port,
    graph: Graph,
    phase: str,
    active_set: Set[str],
    seed_ports: Optional[Set[str]] = None,
) -> bool:
    for link in graph.links:
        if link.id_to != port.id:
            continue
        src_port = graph.ports[link.id_from]
        src_node_id = src_port.node_id

        if src_node_id not in active_set:
            if seed_ports is not None and src_port.id in seed_ports:
                pass
            else:
                continue

        if not _has_phase(src_port, phase):
            continue
        if not _has_phase(port, phase):
            continue
        return True
    return False


def _is_param_input_satisfied(
    port: Port,
    graph: Graph,
    active_set: Set[str],
) -> bool:
    for link in graph.links:
        if link.id_to != port.id:
            continue
        src_node_id = graph.ports[link.id_from].node_id
        if src_node_id in active_set:
            return True
    return False


def _can_activate_regular_node(
    node: Node,
    graph: Graph,
    phase: str,
    active_set: Set[str],
    seed_ports: Optional[Set[str]],
) -> bool:
    """
    A regular node is active if EVERY connected data input is satisfied
    AND (when the node has outputs) at least one output port carries the phase.
    Param inputs must all be satisfied (they are dependencies, not data).
    """
    # ----- data inputs: ALL must be satisfied -----
    data_inputs = _get_connected_data_inputs(node, graph)
    if not data_inputs:
        # No data inputs → node cannot be activated by BFS (must be a seed)
        return False

    for port in data_inputs:
        if not _is_data_input_satisfied(port, graph, phase, active_set, seed_ports):
            return False

    # ----- param inputs: all must be satisfied (no phase check) -----
    for port in _get_connected_param_inputs(node, graph):
        if not _is_param_input_satisfied(port, graph, active_set):
            return False

    # ----- outputs: if the node has outputs, at least one must have the phase -----
    if node.outputs:
        if not any(
            _has_phase(p, phase)
            for p in node.outputs
            if any(l.id_from == p.id for l in graph.links)
        ):
            return False

    return True


def _can_activate_output_node(
    node: Node,
    graph: Graph,
    phase: str,
    active_set: Set[str],
    seed_ports: Optional[Set[str]],
) -> bool:
    any_input = False
    for port in _get_connected_data_inputs(node, graph):
        if _is_data_input_satisfied(port, graph, phase, active_set, seed_ports):
            any_input = True
            break
    if not any_input:
        return False
    for port in node.outputs:
        if _has_phase(port, phase):
            return True
    return False


def _traverse_phase(
    graph: Graph,
    phase: str,
    initial_seeds: Set[str],
    seed_ports: Optional[Set[str]] = None,
) -> Set[str]:
    active = set(initial_seeds)
    changed = True
    while changed:
        changed = False
        for nid, node in graph.nodes.items():
            if nid in active:
                continue
            if node.type == "output":
                if _can_activate_output_node(node, graph, phase, active, seed_ports):
                    active.add(nid)
                    changed = True
            else:
                if _can_activate_regular_node(node, graph, phase, active, seed_ports):
                    active.add(nid)
                    changed = True
    return active


def _topo_sort(graph: Graph, node_ids: Set[str]) -> List[str]:
    adj = {nid: [] for nid in node_ids}
    in_degree = {nid: 0 for nid in node_ids}
    for nid in node_ids:
        for succ in graph.successors(nid):
            if succ in node_ids:
                adj[nid].append(succ)
                in_degree[succ] += 1
        node = graph.nodes[nid]
        for pout in node.paramOutputs:
            for link in graph.links:
                if link.id_from == pout.id:
                    tgt_nid = graph.ports[link.id_to].node_id
                    if tgt_nid in node_ids:
                        adj[nid].append(tgt_nid)
                        in_degree[tgt_nid] += 1
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


def analyze_phases(graph: Graph) -> dict:
    # Preprocessing
    pre_seeds = set()
    for nid, node in graph.nodes.items():
        if node.type == "input-data" and any(
            _has_phase(p, "preprocessing") for p in node.outputs
        ):
            pre_seeds.add(nid)
    pre_set = _traverse_phase(graph, "preprocessing", pre_seeds)
    pre_order = _topo_sort(graph, pre_set)

    # Terminal ports for training/eval
    train_seed_ports = set()
    eval_seed_ports = set()
    for nid in pre_set:
        node = graph.nodes[nid]
        for port in node.outputs:
            if _has_phase(port, "training"):
                train_seed_ports.add(port.id)
            if _has_phase(port, "evaluation"):
                eval_seed_ports.add(port.id)

    train_set = _traverse_phase(graph, "training", set(), train_seed_ports)
    train_order = _topo_sort(graph, train_set)

    eval_set = _traverse_phase(graph, "evaluation", set(), eval_seed_ports)
    eval_order = _topo_sort(graph, eval_set)

    optimizer = None
    for nid in train_set:
        if graph.nodes[nid].type == "optimizer":
            optimizer = graph.nodes[nid]
            break

    visualizations = [
        graph.nodes[nid]
        for nid in pre_set | train_set | eval_set
        if graph.nodes[nid].type == "visualization"
    ]

    return {
        "preprocessing_order": pre_order,
        "train_order": train_order,
        "eval_order": eval_order,
        "preprocessing_set": pre_set,
        "train_set": train_set,
        "eval_set": eval_set,
        "optimizer": optimizer,
        "visualizations": visualizations,
    }


def highlight_path(graph_data: dict, phase: str) -> dict:
    """
    Return the active nodes (from phase analysis) and the links whose
    **both ports** carry the given phase.
    """
    graph = parse_graph(graph_data)
    flow = analyze_phases(graph)

    phase_map = {
        "preprocessing": "preprocessing_set",
        "training": "train_set",
        "evaluation": "eval_set",
    }
    set_key = phase_map.get(phase)
    active_nodes = flow[set_key] if set_key else set()

    highlighted_links = []
    for link in graph.links:
        src_port = graph.ports[link.id_from]
        tgt_port = graph.ports[link.id_to]
        if _has_phase(src_port, phase) and _has_phase(tgt_port, phase):
            highlighted_links.append(f"{link.id_from}→{link.id_to}")

    return {"nodes": list(active_nodes), "links": highlighted_links}
