/**
 * Auto‑layout engine for SketchNet graphs.
 * Compact horizontal layout with natural branching – no stacking,
 * nodes are close together, and the whole graph centres around the main axis.
 *
 * Usage: const positions = SketchLayout.compute(nodes, links);
 * Returns a Map<nodeId, {x, y}>.
 */
const SketchLayout = (() => {
    // ---- Tunables ----
    const LAYER_GAP_X = 140; // horizontal spacing between consecutive non‑empty layers
    const NODE_GAP_Y = 28; // minimum vertical gap between node borders
    const START_X = 80;
    const CENTER_Y = 300; // main axis
    const MAX_ITER = 12; // barycentric refinement passes

    // ---- Public ----
    function compute(nodes, links) {
        // Normalise link endpoints to port ids
        const normLinks = links.map((l) => ({
            from: typeof l.from === "string" ? l.from : l.from.id,
            to: typeof l.to === "string" ? l.to : l.to.id,
        }));
        const { adj, pred, succ } = buildAdjacency(nodes, normLinks);
        const rawLayers = assignLayers(nodes, adj, pred); // may contain empty layers
        const compact = compactLayers(rawLayers); // renumber to remove gaps
        const order = barycentricOrder(compact, pred, succ, 8);
        const positions = assignCoordinates(nodes, order, pred, succ);
        specialNodes(nodes, positions, order, pred);
        return positions;
    }

    // ========================================================================
    //  Build adjacency (data flow only, ignore param links)
    // ========================================================================
    function buildAdjacency(nodes, links) {
        const adj = {},
            pred = {},
            succ = {};
        for (const n of nodes) {
            adj[n.id] = [];
            pred[n.id] = [];
            succ[n.id] = [];
        }
        const portMap = buildPortMap(nodes);
        for (const l of links) {
            if (!portMap[l.from] || !portMap[l.to]) continue;
            const sp = portMap[l.from],
                tp = portMap[l.to];
            if (sp.portKind === "param" || tp.portKind === "param") continue;
            const s = sp.node.id,
                t = tp.node.id;
            if (!adj[s].includes(t)) adj[s].push(t);
            if (!pred[t].includes(s)) pred[t].push(s);
            if (!succ[s].includes(t)) succ[s].push(t);
        }
        return { adj, pred, succ };
    }

    function buildPortMap(nodes) {
        const m = {};
        for (const n of nodes)
            for (const p of n.inputs.concat(
                n.outputs,
                n.paramInputs,
                n.paramOutputs,
            ))
                m[p.id] = p;
        return m;
    }

    // ========================================================================
    //  Layer assignment – ASAP depth (max pred depth + 1)
    // ========================================================================
    function assignLayers(nodes, adj, pred) {
        const depth = {};
        const queue = [];
        for (const n of nodes) {
            if (pred[n.id].length === 0 || n.type === "input-data") {
                depth[n.id] = 0;
                queue.push(n.id);
            }
        }
        while (queue.length) {
            const cur = queue.shift();
            for (const s of adj[cur]) {
                const cand = depth[cur] + 1;
                if (depth[s] === undefined || cand > depth[s]) {
                    depth[s] = cand;
                    if (!queue.includes(s)) queue.push(s);
                }
            }
        }
        for (const n of nodes) if (depth[n.id] === undefined) depth[n.id] = 0;

        // Build raw layers (index = depth)
        const layers = [];
        for (const n of nodes) {
            const d = depth[n.id];
            if (!layers[d]) layers[d] = [];
            layers[d].push(n.id);
        }
        return layers;
    }

    // Remove empty layers and renumber consecutively
    function compactLayers(layers) {
        const compact = [];
        for (let i = 0; i < layers.length; i++) {
            if (layers[i] && layers[i].length > 0) compact.push(layers[i]);
        }
        return compact;
    }

    // ========================================================================
    //  Barycentric ordering (reduce crossings)
    // ========================================================================
    function barycentricOrder(layers, pred, succ, passes) {
        for (let p = 0; p < passes; p++) {
            // Forward sweep (by predecessor positions)
            for (let i = 1; i < layers.length; i++) {
                const cur = layers[i];
                const prev = layers[i - 1] || [];
                const bary = {};
                for (const nid of cur) {
                    const pr = pred[nid] || [];
                    let sum = 0,
                        cnt = 0;
                    for (const pid of pr) {
                        const idx = prev.indexOf(pid);
                        if (idx >= 0) {
                            sum += idx;
                            cnt++;
                        }
                    }
                    bary[nid] = cnt > 0 ? sum / cnt : 0;
                }
                cur.sort((a, b) => (bary[a] || 0) - (bary[b] || 0));
                layers[i] = cur;
            }
            // Backward sweep (by successor positions)
            for (let i = layers.length - 2; i >= 0; i--) {
                const cur = layers[i];
                const next = layers[i + 1] || [];
                const bary = {};
                for (const nid of cur) {
                    const su = succ[nid] || [];
                    let sum = 0,
                        cnt = 0;
                    for (const sid of su) {
                        const idx = next.indexOf(sid);
                        if (idx >= 0) {
                            sum += idx;
                            cnt++;
                        }
                    }
                    bary[nid] = cnt > 0 ? sum / cnt : 0;
                }
                cur.sort((a, b) => (bary[a] || 0) - (bary[b] || 0));
                layers[i] = cur;
            }
        }
        return layers;
    }

    // ========================================================================
    //  Assign coordinates (centered vertically, compact horizontally)
    // ========================================================================
    function assignCoordinates(nodes, layers, pred, succ) {
        const nodeMap = {};
        for (const n of nodes) nodeMap[n.id] = n;
        const pos = {}; // nodeId -> {x, y, h}

        // ----- Initial placement -----
        for (let li = 0; li < layers.length; li++) {
            const layer = layers[li];
            const heights = layer.map((id) => nodeHeight(nodeMap[id]));
            const totalH = heights.reduce(
                (s, h) => s + h + NODE_GAP_Y,
                -NODE_GAP_Y,
            ); // sum heights + gaps
            let y = CENTER_Y - totalH / 2;
            const x = START_X + li * LAYER_GAP_X;
            for (let j = 0; j < layer.length; j++) {
                const nid = layer[j];
                const h = heights[j];
                y += h / 2;
                pos[nid] = { x, y, h };
                y += h / 2 + NODE_GAP_Y;
            }
        }

        // ----- Refinement: pull toward neighbour average, then remove overlaps -----
        for (let iter = 0; iter < MAX_ITER; iter++) {
            const newY = {};
            for (const nid in pos) {
                const pr = (pred[nid] || []).filter((p) => pos[p]);
                const su = (succ[nid] || []).filter((s) => pos[s]);
                const neighbours = pr.concat(su);
                if (neighbours.length > 0) {
                    let sum = 0;
                    for (const nb of neighbours) sum += pos[nb].y;
                    newY[nid] = sum / neighbours.length;
                } else {
                    newY[nid] = pos[nid].y;
                }
            }

            // Apply newY within each layer, respecting ordering and minimum gap
            for (let li = 0; li < layers.length; li++) {
                const layer = layers[li];
                // sort layer by newY
                layer.sort((a, b) => (newY[a] || 0) - (newY[b] || 0));

                // Re‑assign Y with gap enforcement, but try to stay close to newY
                let curY = -Infinity;
                for (const nid of layer) {
                    const h = pos[nid].h;
                    const target =
                        newY[nid] !== undefined ? newY[nid] : pos[nid].y;
                    // ensure we don't go below previous node's bottom
                    const minY =
                        curY +
                        (curY === -Infinity ? 0 : pos[nid].h / 2 + NODE_GAP_Y);
                    let y = Math.max(target - h / 2, minY);
                    pos[nid].y = y + h / 2;
                    curY = y + h;
                }
            }
        }

        // Convert to Map
        const positions = new Map();
        for (const nid in pos)
            positions.set(nid, { x: pos[nid].x, y: pos[nid].y });
        return positions;
    }

    // ========================================================================
    //  Special nodes (output far right, optimizer next to it)
    // ========================================================================
    function specialNodes(nodes, positions, layers, pred) {
        const outputNode = nodes.find((n) => n.type === "output");
        if (outputNode) {
            let maxX = 0;
            for (const n of nodes) {
                const p = positions.get(n.id);
                if (p && p.x > maxX) maxX = p.x;
            }
            const pr = pred[outputNode.id] || [];
            let sumY = 0,
                cnt = 0;
            for (const pid of pr) {
                const ppos = positions.get(pid);
                if (ppos) {
                    sumY += ppos.y;
                    cnt++;
                }
            }
            const outY = cnt > 0 ? sumY / cnt : CENTER_Y;
            positions.set(outputNode.id, { x: maxX + LAYER_GAP_X, y: outY });
        }
        const optNode = nodes.find((n) => n.type === "optimizer");
        if (optNode && outputNode) {
            const outPos = positions.get(outputNode.id);
            if (outPos)
                positions.set(optNode.id, {
                    x: outPos.x + LAYER_GAP_X * 1.1,
                    y: outPos.y,
                });
        }
    }

    // ========================================================================
    //  Helpers
    // ========================================================================
    function nodeHeight(node) {
        if (node.height) return node.height;
        if (node.radius) return node.radius * 2;
        if (node.type === "neuron") return 56;
        if (
            [
                "layer",
                "column-select",
                "normalize",
                "train-test",
                "reshape",
            ].includes(node.type)
        )
            return 65;
        if (node.type === "output") return 70;
        if (node.type === "optimizer") return 85;
        if (node.type === "visualization") return 75;
        return 60;
    }

    return { compute };
})();
