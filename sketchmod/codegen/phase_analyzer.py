"""
Phase analysis for SketchNet computation graphs.

This module determines which nodes and connections are active during different
execution phases (preprocessing, training, evaluation). It performs topological
sorting to determine execution order and identifies special nodes like optimizers
and visualizations.

Key concepts:
- Preprocessing: Initial data loading and transformation (e.g., train-test split)
- Training: Forward/backward passes during model training
- Evaluation: Forward pass on test data for evaluation metrics

The analysis uses both "strict" mode (for visualization) and "carry-over" mode
(for code generation) to handle links from preprocessing nodes that may not
explicitly mark their outputs with training/evaluation phases.
"""

from .graph import Graph, parse_graph
from typing import Set, List, Dict, Any


def _is_port_active(port, phase: str) -> bool:
    """
    Check if a port is active during a given phase.
    
    Args:
        port (Port): The port to check.
        phase (str): The phase name ("preprocessing", "training", or "evaluation").
        
    Returns:
        bool: True if the phase is in the port's activationPhases list.
    """
    return phase in port.activation_phases


# ------------------------------------------------------------
#  STRICT (checkbox‑only) – used for highlight_path
# ------------------------------------------------------------
def _active_nodes_strict(graph: Graph, phase: str) -> Set[str]:
    """
    Determine nodes active in a phase using strict rules.
    
    A node is considered active only when ALL connected input and output ports
    have the given phase in their activation_phases. This is used for visualization
    highlighting to show only the guaranteed execution path.
    
    Args:
        graph (Graph): The computation graph.
        phase (str): The phase to analyze ("preprocessing", "training", "evaluation").
        
    Returns:
        Set[str]: Set of node IDs that are active in this phase.
    """
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
    """
    Traverse the graph to find all nodes in the preprocessing phase.
    
    Uses breadth-first search starting from input-data nodes, following only
    links where both the source and target ports have "preprocessing" in their
    activation phases. This determines which data transformations occur before
    the train/eval split.
    
    Args:
        graph (Graph): The computation graph.
        
    Returns:
        Set[str]: Set of node IDs in the preprocessing phase.
    """
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
    Traverse the graph to find all nodes active during training or evaluation.
    
    Uses iterative refinement to find all nodes that can be activated during
    the given phase. Implements "carry-over" logic where preprocessing nodes
    can feed into training/evaluation nodes even if their ports don't explicitly
    mark those phases (since preprocessing data is available).
    
    Special handling for output nodes: only requires one active input instead of all.
    
    Args:
        graph (Graph): The computation graph.
        phase (str): The phase to analyze ("training" or "evaluation").
        pre_set (Set[str]): Set of preprocessing node IDs (for carry-over logic).
        
    Returns:
        Set[str]: Set of node IDs active in this phase.
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

                            # Allow the link if:
                            #  - the source is already active in the current phase, OR
                            #  - the source is a preprocessing node (carry‑over)
                            # and both the source and target ports have the required phase.
                            if (
                                (src_nid in active or src_nid in pre_set)
                                and _is_port_active(src_port, phase)
                                and _is_port_active(in_port, phase)
                            ):
                                port_satisfied = True
                                break

                            # Param port carry‑over remains unchanged
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
    """
    Topologically sort a set of nodes.
    
    Uses Kahn's algorithm (BFS-based topological sort) to order nodes
    such that dependencies are satisfied (predecessors come before successors).
    
    Args:
        nids (Set[str]): Set of node IDs to sort.
        graph (Graph): The computation graph.
        
    Returns:
        List[str]: Topologically sorted list of node IDs.
    """
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
    Analyze the computation graph to determine execution phases and node ordering.
    
    Performs three main tasks:
    1. Identifies which nodes are active in preprocessing, training, and evaluation
    2. Topologically sorts nodes within each phase for execution order
    3. Locates special nodes (optimizer, visualizations)
    
    Args:
        graph (Graph): The computation graph.
        
    Returns:
        dict: Analysis results with keys:
            - "preprocessing_order": List of node IDs in preprocessing execution order
            - "train_order": List of node IDs in training execution order
            - "eval_order": List of node IDs in evaluation execution order
            - "preprocessing_set": Set of preprocessing node IDs
            - "train_set": Set of training node IDs
            - "eval_set": Set of evaluation node IDs
            - "optimizer": The optimizer Node object (or None)
            - "visualizations": List of visualization Node objects
    """
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
    """
    Determine which nodes and links to highlight for a given execution phase.
    
    Used by the frontend to visually show the execution path through the graph
    for a specific phase. Uses strict mode to only highlight guaranteed paths.
    
    Args:
        graph_data (dict): JSON graph data.
        phase (str): The phase to highlight ("preprocessing", "training", "evaluation").
        
    Returns:
        dict: Highlighting information with keys:
            - "nodes": List of active node IDs
            - "links": List of active link identifiers (e.g., "port1→port2")
    """
    graph = parse_graph(graph_data)
    active_nodes = _active_nodes_strict(graph, phase)
    highlighted_links = []
    for link in graph.links:
        src = graph.ports[link.id_from]
        tgt = graph.ports[link.id_to]
        if _is_port_active(src, phase) and _is_port_active(tgt, phase):
            highlighted_links.append(f"{link.id_from}→{link.id_to}")
    return {"nodes": list(active_nodes), "links": highlighted_links}
