"""
Topological sort for SketchNet graphs.

Used to determine execution order within a phase.
"""

from typing import List, Set, Dict
from .graph import Graph


def topological_sort(graph: Graph, node_ids: Set[str]) -> List[str]:
    """
    Return a topologically sorted list of `node_ids`.

    Respects both data and parameter dependencies.
    Nodes not in `node_ids` are ignored.
    """
    adj: Dict[str, List[str]] = {nid: [] for nid in node_ids}
    in_degree: Dict[str, int] = {nid: 0 for nid in node_ids}

    for nid in node_ids:
        # Data successors
        for succ in graph.successors(nid):
            if succ in node_ids:
                adj[nid].append(succ)
                in_degree[succ] += 1

        # Param successors (param output → param input)
        node = graph.nodes[nid]
        for pout in node.paramOutputs:
            for link in graph.links:
                if link.id_from == pout.id:
                    tgt_nid = graph.ports[link.id_to].node_id
                    if tgt_nid in node_ids:
                        adj[nid].append(tgt_nid)
                        in_degree[tgt_nid] += 1

    # Kahn's algorithm
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
