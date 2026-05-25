/**
 * SketchMod Canvas Engine
 * Pure HTML5 Canvas — no libraries.
 */

const SketchMod = {
    canvas: null,
    ctx: null,
    nodes: [],
    links: [],
    ports: [],
    nodeCounter: 0,
    currentTool: "select",

    // Pan/Zoom
    offsetX: 0,
    offsetY: 0,
    scale: 1,
    isPanning: false,
    panStartX: 0,
    panStartY: 0,
    spacePressed: false,

    // Selection state
    selectedNodes: [], // Array of selected nodes
    selectedLinks: [], // Array of selected links
    selectedPorts: [], // Array of selected ports
    isDraggingNode: false,
    dragOffsetX: 0,
    dragOffsetY: 0,
    selectionBox: null, // { startX, startY, endX, endY } for drag-select
    isSelecting: false, // True when dragging a selection box
    shiftPressed: false,

    // Linking (drag from port to port)
    linking: {
        active: false,
        sourcePort: null,
        startX: 0,
        startY: 0,
        mouseX: undefined,
        mouseY: undefined,
    },

    //history
    undoStack: [],
    redoStack: [],
    maxUndo: 50,

    _getNodeColor() {
        const theme =
            document.documentElement.getAttribute("data-theme") || "light";
        const colors = {
            light: { fill: "#6c5ce7", stroke: "#5a4bd1" },
            dark: { fill: "#7c6ff0", stroke: "#a29bfe" },
            rose: { fill: "#e8536c", stroke: "#d43d56" },
            "dark-rose": { fill: "#f0627a", stroke: "#ff8a9e" },
            forest: { fill: "#3a8a3a", stroke: "#2d6e2d" },
            "forest-dark": { fill: "#4caf50", stroke: "#66d968" },
            honey: { fill: "#d4a800", stroke: "#b89200" },
            "honey-dark": { fill: "#f0c040", stroke: "#ffd866" },
            system: { fill: "#6c5ce7", stroke: "#5a4bd1" },
        };
        // If system, check device preference
        if (theme === "system" || !colors[theme]) {
            const prefersDark = window.matchMedia(
                "(prefers-color-scheme: dark)",
            ).matches;
            return prefersDark ? colors.dark : colors.light;
        }
        return colors[theme] || colors.light;
    },

    // ========== INIT ==========
    init() {
        this.canvas = document.getElementById("sketchCanvas");
        this.ctx = this.canvas.getContext("2d");
        this.resize();
        window.addEventListener("resize", () => this.resize());
        this.canvas.addEventListener("mousedown", (e) => this._onMouseDown(e));
        this.canvas.addEventListener("mousemove", (e) => this._onMouseMove(e));
        this.canvas.addEventListener("mouseup", (e) => this._onMouseUp(e));
        this.canvas.addEventListener("wheel", (e) => this._onScroll(e));
        this.canvas.addEventListener("contextmenu", (e) => e.preventDefault());
        document.addEventListener("keydown", (e) => this._onKeyDown(e));
        document.addEventListener("keyup", (e) => {
            if (e.code === "Space") this.spacePressed = false;
            if (e.code === "ShiftLeft" || e.code === "ShiftRight")
                this.shiftPressed = false;
        });
        document.addEventListener("click", () => this._hideContextMenu());
        // Dataset picker events (delegated)
        document.addEventListener("click", (e) => {
            // Close picker when clicking outside
            const picker = document.getElementById("datasetPicker");
            const display = document.getElementById("datasetSelectDisplay");
            if (
                picker &&
                display &&
                !picker.contains(e.target) &&
                !display.contains(e.target)
            ) {
                picker.style.display = "none";
            }

            // Tab clicks
            if (e.target.classList.contains("dataset-tab")) {
                document
                    .querySelectorAll(".dataset-tab")
                    .forEach((t) => t.classList.remove("active"));
                e.target.classList.add("active");
                this._loadDatasets(
                    e.target.dataset.section,
                    document.getElementById("datasetSearch")?.value || "",
                );
            }
        });

        // Dataset search input
        document.addEventListener("input", (e) => {
            if (e.target.id === "datasetSearch") {
                const section =
                    document.querySelector(".dataset-tab.active")?.dataset
                        .section || "all";
                this._loadDatasets(section, e.target.value);
            }
        });
        // Sidebar buttons
        document
            .getElementById("btnSave")
            ?.addEventListener("click", () => this._saveToServer());
        document
            .getElementById("btnTranslate")
            ?.addEventListener("click", () => this._translate());
        // Undo and redo button
        document
            .getElementById("btnUndo")
            ?.addEventListener("click", () => this._undo());
        document
            .getElementById("btnRedo")
            ?.addEventListener("click", () => this._redo());
        // Zoom buttons
        document
            .getElementById("btnZoomIn")
            ?.addEventListener("click", () => this._zoomStep(1.25));
        document
            .getElementById("btnZoomOut")
            ?.addEventListener("click", () => this._zoomStep(0.8));
        document
            .getElementById("btnZoomFit")
            ?.addEventListener("click", () => this._zoomFit());
        // Toolbar
        document.querySelectorAll(".tool-btn[data-tool]").forEach((btn) => {
            btn.addEventListener("click", () => this.setTool(btn.dataset.tool));
        });

        // Context menu actions
        document.querySelectorAll(".context-menu-item").forEach((item) => {
            item.addEventListener("click", () => {
                const menu = document.getElementById("contextMenu");
                const node = menu._targetNode;
                const action = item.dataset.action;

                if (action === "add-input") {
                    this._saveUndoState();
                    const port = node.addInput();
                    if (port) this.ports = this._collectPorts();
                }
                if (action === "add-output") {
                    this._saveUndoState();
                    const port = node.addOutput();
                    if (port) this.ports = this._collectPorts();
                }
                if (action === "remove-input") {
                    this._saveUndoState();
                    const port = node.removeInput();
                    if (port) {
                        this.links = this.links.filter(
                            (l) => l.from !== port && l.to !== port,
                        );
                        this.ports = this._collectPorts();
                        node.updatePorts();
                    }
                }
                if (action === "remove-output") {
                    this._saveUndoState();
                    const port = node.removeOutput();
                    if (port) {
                        this.links = this.links.filter(
                            (l) => l.from !== port && l.to !== port,
                        );
                        this.ports = this._collectPorts();
                        node.updatePorts();
                    }
                }
                if (action === "delete-node") {
                    this._saveUndoState();
                    this._deleteNode(node);
                }

                this._hideContextMenu();
                this._saveToSession();
                this._render();
            });
        });
        // Port context menu actions
        document
            .querySelectorAll("#portContextMenu .context-menu-item")
            .forEach((item) => {
                item.addEventListener("click", () => {
                    const menu = document.getElementById("portContextMenu");
                    const port = menu._targetPort;
                    const action = item.dataset.action;

                    if (action === "delete-port") {
                        this._deletePort(port);
                    }
                    if (action === "disconnect-port") {
                        this._disconnectPort(port);
                    }

                    this._hidePortContextMenu();
                });
            });

        // Hide port menu on outside click
        document.addEventListener("click", () => {
            this._hidePortContextMenu();
        });

        this._loadFromSession();

        // Ensure input/output exist
        if (this.nodes.length === 0) {
            this._createDefaultNodes();
        }

        this._render();
        this._saveUndoState();
    },

    resize() {
        const wrapper = document.getElementById("canvasWrapper");
        this.canvas.width = wrapper.clientWidth;
        this.canvas.height = wrapper.clientHeight;
        this._render();
    },

    _createDefaultNodes() {
        const cx = this.canvas.width / 2;
        const cy = this.canvas.height / 2;
        const input = new InputDataNode("input-main", cx - 300, cy);
        const output = new OutputNode("output-main", cx + 300, cy);
        this.nodes.push(input, output);
        this.ports = this._collectPorts();
        this._saveToSession();
    },

    // ========== COORDINATES ==========
    _toWorld(sx, sy) {
        return {
            x: (sx - this.offsetX) / this.scale,
            y: (sy - this.offsetY) / this.scale,
        };
    },

    _toScreen(wx, wy) {
        return {
            x: wx * this.scale + this.offsetX,
            y: wy * this.scale + this.offsetY,
        };
    },
    // ========== scroll ==========
    _onScroll(e) {
        e.preventDefault();
        const zoom = e.deltaY < 0 ? 1.08 : 0.93;
        const newScale = this.scale * zoom;
        if (newScale < 0.05 || newScale > 15) return;
        this.offsetX = e.offsetX - (e.offsetX - this.offsetX) * zoom;
        this.offsetY = e.offsetY - (e.offsetY - this.offsetY) * zoom;
        this.scale = newScale;
        this._updateZoomIndicator();
        this._render();
    },
    // ========== MOUSE ==========
    _onMouseDown(e) {
        const mx = e.offsetX;
        const my = e.offsetY;

        // === RIGHT CLICK ===
        if (e.button === 2) {
            const hit = this._hitTest(mx, my);

            // Right-click on port
            if (hit && hit.port) {
                this._showPortContextMenu(e.clientX, e.clientY, hit.port);
                return;
            }

            // Right-click on node
            if (hit && hit.node) {
                if (!this.selectedNodes.includes(hit.node)) {
                    this.selectedNodes = [hit.node];
                }
                this._showContextMenu(e.clientX, e.clientY, hit.node);
                return;
            }

            return;
        }

        // === LEFT CLICK ===
        if (e.button !== 0) return;

        // Pan
        if (this.spacePressed || this.currentTool === "pan") {
            this.isPanning = true;
            this.panStartX = mx - this.offsetX;
            this.panStartY = my - this.offsetY;
            return;
        }

        const hit = this._hitTest(mx, my);

        // Delete tool
        if (this.currentTool === "delete") {
            if (hit && hit.port) {
                this._deletePort(hit.port);
                return;
            }
            if (hit && hit.node) {
                this._deleteNode(hit.node);
                return;
            }
            if (hit && hit.link) {
                this._deleteLink(hit.link);
                return;
            }
            return;
        }

        // Click on port — drag to connect or click to select
        if (hit && hit.port) {
            this.linking.active = true;
            this.linking.sourcePort = hit.port;
            this.linking.startX = mx;
            this.linking.startY = my;
            this._render();
            return;
        }

        // Click on node
        if (hit && hit.node) {
            if (this.shiftPressed) {
                const idx = this.selectedNodes.indexOf(hit.node);
                if (idx >= 0) {
                    this.selectedNodes.splice(idx, 1);
                } else {
                    this.selectedNodes.push(hit.node);
                }
            } else {
                this.selectedNodes = [hit.node];
            }
            this.selectedLinks = [];
            this.selectedPorts = [];

            if (this.selectedNodes.length === 1) {
                this._showProperties(this.selectedNodes[0]);
            } else {
                this._hideProperties();
            }

            this.isDraggingNode = true;
            this.dragOffsets = this.selectedNodes.map((n) => {
                const s = this._toScreen(n.x, n.y);
                return { node: n, ox: mx - s.x, oy: my - s.y };
            });
            this._render();
            return;
        }

        // Click on link
        if (hit && hit.link) {
            if (this.shiftPressed) {
                const idx = this.selectedLinks.indexOf(hit.link);
                if (idx >= 0) {
                    this.selectedLinks.splice(idx, 1);
                } else {
                    this.selectedLinks.push(hit.link);
                }
            } else {
                this.selectedLinks = [hit.link];
                this.selectedNodes = [];
                this.selectedPorts = [];
                this._hideProperties();
            }
            this._render();
            return;
        }

        // Click on empty
        if (this.currentTool === "select") {
            this.isSelecting = true;
            this.selectionBox = { startX: mx, startY: my, endX: mx, endY: my };
            if (!this.shiftPressed) {
                this.selectedNodes = [];
                this.selectedLinks = [];
                this.selectedPorts = [];
                this._hideProperties();
            }
            return;
        }

        // Deselect all on empty click with other tools
        this.selectedNodes = [];
        this.selectedLinks = [];
        this.selectedPorts = [];
        this.linking.active = false;
        this.linking.sourcePort = null;
        this._hideProperties();
        this._render();

        // Place node
        if (this.currentTool === "neuron") this._addNode("neuron", mx, my);
        else if (this.currentTool === "layer") this._addNode("layer", mx, my);
        else if (this.currentTool === "column-select")
            this._addNode("column-select", mx, my);
        else if (this.currentTool === "train-test")
            this._addNode("train-test", mx, my);
        else if (this.currentTool === "normalize")
            this._addNode("normalize", mx, my);
    },

    _onMouseMove(e) {
        const mx = e.offsetX;
        const my = e.offsetY;

        if (this.isPanning) {
            this.offsetX = mx - this.panStartX;
            this.offsetY = my - this.panStartY;
            this._render();
            return;
        }

        // Dragging nodes
        if (this.isDraggingNode && this.dragOffsets) {
            for (const d of this.dragOffsets) {
                const world = this._toWorld(mx - d.ox, my - d.oy);
                d.node.x = world.x;
                d.node.y = world.y;
                d.node.updatePorts();
            }
            this._saveToSession();
            this._render();
            return;
        }

        // Selection box
        if (this.isSelecting && this.selectionBox) {
            this.selectionBox.endX = mx;
            this.selectionBox.endY = my;
            this._render();
            return;
        }
        // Track mouse for temp link line
        if (this.linking.active) {
            this.linking.mouseX = mx;
            this.linking.mouseY = my;
            this._render();
        }
        // Cursor
        const hit = this._hitTest(mx, my);
        if (hit && hit.port) this.canvas.style.cursor = "pointer";
        else if (hit && hit.node) this.canvas.style.cursor = "move";
        else if (this.currentTool === "pan" || this.spacePressed)
            this.canvas.style.cursor = "grab";
        else if (this.currentTool === "link")
            this.canvas.style.cursor = "crosshair";
        else this.canvas.style.cursor = "default";
    },

    _onMouseUp(e) {
        // Handle port drag-link or select
        if (this.linking.active && this.linking.sourcePort) {
            const dx = e.offsetX - this.linking.startX;
            const dy = e.offsetY - this.linking.startY;
            const dragged = Math.sqrt(dx * dx + dy * dy) > 4;

            if (dragged) {
                // User dragged — try to connect
                const hit = this._hitTest(e.offsetX, e.offsetY);
                if (hit && hit.port && hit.port !== this.linking.sourcePort) {
                    this._addLink(this.linking.sourcePort, hit.port);
                }
            } else {
                // User just clicked without dragging — select the port
                this.selectedPorts = [this.linking.sourcePort];
                this.selectedNodes = [];
                this.selectedLinks = [];
                this._showPortProperties();
            }

            this.linking.active = false;
            this.linking.sourcePort = null;
            this._render();
        }

        // Finish selection box
        if (this.isSelecting && this.selectionBox) {
            const box = this.selectionBox;
            const x1 = Math.min(box.startX, box.endX);
            const y1 = Math.min(box.startY, box.endY);
            const x2 = Math.max(box.startX, box.endX);
            const y2 = Math.max(box.startY, box.endY);

            const w1 = this._toWorld(x1, y1);
            const w2 = this._toWorld(x2, y2);

            for (const node of this.nodes) {
                const b = node.getBounds();
                const nx = b.x;
                const ny = b.y;
                const nw = b.w;
                const nh = b.h;
                if (
                    nx + nw >= w1.x &&
                    nx <= w2.x &&
                    ny + nh >= w1.y &&
                    ny <= w2.y
                ) {
                    if (!this.selectedNodes.includes(node)) {
                        this.selectedNodes.push(node);
                    }
                }
            }
            this.selectedLinks = [];
            this.selectedPorts = [];
            if (this.selectedNodes.length === 1) {
                this._showProperties(this.selectedNodes[0]);
            }
            this.isSelecting = false;
            this.selectionBox = null;
            this._render();
        }

        // Save undo state after node dragging finishes
        if (this.isDraggingNode) {
            this._saveUndoState();
        }

        this.isPanning = false;
        this.isDraggingNode = false;
        this.dragOffsets = null;
    },

    _onKeyDown(e) {
        if (e.code === "Space") {
            this.spacePressed = true;
            e.preventDefault();
        }
        if (e.code === "ShiftLeft" || e.code === "ShiftRight") {
            this.shiftPressed = true;
        }
        if (e.key === "s") this.setTool("select");
        if (e.key === "h") this.setTool("pan");
        if (e.key === "d") this.setTool("delete");
        if (e.key === "Delete") {
            this._deleteSelected();
        }
        if (e.key === "Escape") {
            this.selectedNodes = [];
            this.selectedLinks = [];
            this.selectedPorts = [];
            this._hideProperties();
            this._render();
        }
        if (e.key === "+" || e.key === "=") {
            this._zoomStep(1.25);
            e.preventDefault();
        }
        if (e.key === "-") {
            this._zoomStep(0.8);
            e.preventDefault();
        }
        if (e.key === "0") {
            this._zoomFit();
            e.preventDefault();
        }
        if ((e.ctrlKey || e.metaKey) && e.key === "z" && !e.shiftKey) {
            e.preventDefault();
            this._undo();
        }
        if ((e.ctrlKey || e.metaKey) && e.key === "z" && e.shiftKey) {
            e.preventDefault();
            this._redo();
        }
        if ((e.ctrlKey || e.metaKey) && e.key === "y") {
            e.preventDefault();
            this._redo();
        }
    },

    // ========== HIT TEST ==========
    _hitTest(sx, sy) {
        const w = this._toWorld(sx, sy);
        // Ports first
        for (const port of this.ports) {
            const ps = this._toScreen(port.x, port.y);
            const dx = sx - ps.x;
            const dy = sy - ps.y;
            if (Math.sqrt(dx * dx + dy * dy) < port.radius * this.scale + 4) {
                return { port };
            }
        }
        // Nodes
        for (let i = this.nodes.length - 1; i >= 0; i--) {
            if (this.nodes[i].containsPoint(w.x, w.y)) {
                return { node: this.nodes[i] };
            }
        }
        // Links
        for (const link of this.links) {
            if (link.hitTest(w.x, w.y)) {
                return { link };
            }
        }
        return null;
    },

    // ========== NODES ==========
    _addNode(type, sx, sy) {
        if (type === "input-data" || type === "output") return; //disabling multiple input and output nodes
        const w = this._toWorld(sx, sy);
        const id = type[0] + ++this.nodeCounter;
        let node;
        if (type === "neuron") node = new NeuronNode(id, w.x, w.y);
        else if (type === "layer") node = new LayerNode(id, w.x, w.y);
        else if (type === "column-select")
            node = new ColumnSelectNode(id, w.x, w.y);
        else if (type === "train-test")
            node = new TrainTestSplitNode(id, w.x, w.y);
        else if (type === "normalize") node = new NormalizeNode(id, w.x, w.y);
        if (!node) return;

        this._saveUndoState();
        this.nodes.push(node);
        this.ports = this._collectPorts();
        this.selectedNodes = [node];
        this._showProperties(node);
        this._saveToSession();
        this._render();
    },

    _deleteNode(node) {
        if (node instanceof InputDataNode || node instanceof OutputNode) return;
        this.links = this.links.filter(
            (l) => l.from.node !== node && l.to.node !== node,
        );

        this._saveUndoState();
        this.nodes = this.nodes.filter((n) => n !== node);
        this.ports = this._collectPorts();
        this.selectedNodes = this.selectedNodes.filter((n) => n !== node);
        if (this.selectedNodes.length === 0) {
            this._hideProperties();
        }
        this._saveToSession();
        this._render();
    },

    _deleteLink(link) {
        this._saveUndoState();
        this.links = this.links.filter((l) => l !== link);
        this.selectedLinks = this.selectedLinks.filter((l) => l !== link);
        this._saveToSession();
        this._render();
    },

    _deleteSelected() {
        for (const node of [...this.selectedNodes]) {
            if (
                !(node instanceof InputDataNode) &&
                !(node instanceof OutputNode)
            ) {
                this._deleteNode(node);
            }
        }
        for (const link of [...this.selectedLinks]) {
            this._deleteLink(link);
        }
        this.selectedNodes = [];
        this.selectedLinks = [];
        this._hideProperties();
        this._render();
    },
    _addLink(fromPort, toPort) {
        if (fromPort === toPort) return;
        // Must be output → input
        let outPort, inPort;
        if (fromPort.type === "output" && toPort.type === "input") {
            outPort = fromPort;
            inPort = toPort;
        } else if (fromPort.type === "input" && toPort.type === "output") {
            outPort = toPort;
            inPort = fromPort;
        } else {
            return; // Same type — can't connect
        }
        const exists = this.links.find(
            (l) => l.from === outPort && l.to === inPort,
        );
        if (exists) return;

        this._saveUndoState();
        this.links.push(new Link(outPort, inPort));
        this._saveToSession();
    },

    _collectPorts() {
        const all = [];
        for (const node of this.nodes) {
            all.push(...node.inputs, ...node.outputs);
        }
        return all;
    },
    // ========== ZOOM METHODS ==========
    _zoomStep(factor) {
        const cx = this.canvas.width / 2;
        const cy = this.canvas.height / 2;
        const newScale = this.scale * factor;
        if (newScale < 0.05 || newScale > 15) return;
        this.offsetX = cx - (cx - this.offsetX) * factor;
        this.offsetY = cy - (cy - this.offsetY) * factor;
        this.scale = newScale;
        this._updateZoomIndicator();
        this._render();
    },

    _zoomFit() {
        if (this.nodes.length === 0) {
            this.scale = 1;
            this.offsetX = 0;
            this.offsetY = 0;
            this._updateZoomIndicator();
            this._render();
            return;
        }

        // Find bounds of all nodes
        let minX = Infinity,
            minY = Infinity,
            maxX = -Infinity,
            maxY = -Infinity;
        for (const node of this.nodes) {
            const b = node.getBounds();
            if (b.x < minX) minX = b.x;
            if (b.y < minY) minY = b.y;
            if (b.x + b.w > maxX) maxX = b.x + b.w;
            if (b.y + b.h > maxY) maxY = b.y + b.h;
        }

        const graphW = maxX - minX + 100;
        const graphH = maxY - minY + 100;
        const canvasW = this.canvas.width;
        const canvasH = this.canvas.height;

        const scaleX = canvasW / graphW;
        const scaleY = canvasH / graphH;
        this.scale = Math.min(scaleX, scaleY, 2);

        const centerX = (minX + maxX) / 2;
        const centerY = (minY + maxY) / 2;

        this.offsetX = canvasW / 2 - centerX * this.scale;
        this.offsetY = canvasH / 2 - centerY * this.scale;

        this._updateZoomIndicator();
        this._render();
    },

    _updateZoomIndicator() {
        const indicator = document.getElementById("zoomIndicator");
        if (indicator) {
            indicator.textContent = Math.round(this.scale * 100) + "%";
        }
    },
    // ========== Update data nodes ==========
    _updateColumnSelect(checkbox) {
        if (this.selectedNodes.length !== 1) return;
        const node = this.selectedNodes[0];
        if (!(node instanceof ColumnSelectNode)) return;
        this._saveUndoState();

        if (checkbox.checked) {
            if (!node.selectedColumns.includes(checkbox.value)) {
                node.selectedColumns.push(checkbox.value);
            }
        } else {
            node.selectedColumns = node.selectedColumns.filter(
                (c) => c !== checkbox.value,
            );
        }
        this._saveToSession();
        this._render();
    },

    _updateTrainTest(slider) {
        if (this.selectedNodes.length !== 1) return;
        const node = this.selectedNodes[0];
        if (!(node instanceof TrainTestSplitNode)) return;
        this._saveUndoState();

        node.trainRatio = parseFloat(slider.value);
        node.testRatio = 1 - node.trainRatio;

        // Update display
        const values = slider.parentElement.querySelector(".range-values");
        if (values) {
            values.innerHTML = `
            <span>Train: ${Math.round(node.trainRatio * 100)}%</span>
            <span>Test: ${Math.round(node.testRatio * 100)}%</span>
        `;
        }
        this._saveToSession();
        this._render();
    },

    _updateTrainTestSeed(input) {
        if (this.selectedNodes.length !== 1) return;
        const node = this.selectedNodes[0];
        if (!(node instanceof TrainTestSplitNode)) return;
        this._saveUndoState();

        node.randomSeed = parseInt(input.value) || 42;
        this._saveToSession();
    },

    _updateNormalize(select) {
        if (this.selectedNodes.length !== 1) return;
        const node = this.selectedNodes[0];
        if (!(node instanceof NormalizeNode)) return;
        this._saveUndoState();

        node.method = select.value;
        this._saveToSession();
        this._render();
    },

    // ========== CONTEXT MENU ==========
    _showContextMenu(x, y, node) {
        const menu = document.getElementById("contextMenu");
        menu.style.display = "block";
        menu.style.left = x + "px";
        menu.style.top = y + "px";
        menu._targetNode = node;

        const addInput = menu.querySelector('[data-action="add-input"]');
        const addOutput = menu.querySelector('[data-action="add-output"]');
        const removeInput = menu.querySelector('[data-action="remove-input"]');
        const removeOutput = menu.querySelector(
            '[data-action="remove-output"]',
        );
        const deleteItem = menu.querySelector('[data-action="delete-node"]');

        addInput.style.display = node.canAddInput() ? "flex" : "none";
        addOutput.style.display = node.canAddOutput() ? "flex" : "none";
        removeInput.style.display = node.canRemoveInput() ? "flex" : "none";
        removeOutput.style.display = node.canRemoveOutput() ? "flex" : "none";

        // Can't delete input/output nodes
        if (node instanceof InputDataNode || node instanceof OutputNode) {
            deleteItem.style.display = "none";
        } else {
            deleteItem.style.display = "flex";
        }
    },

    _hideContextMenu() {
        document.getElementById("contextMenu").style.display = "none";
        document.getElementById("portContextMenu").style.display = "none";
    },
    // ========== Port CONTEXT MENU ==========
    _showPortContextMenu(x, y, port) {
        const menu = document.getElementById("portContextMenu");
        const nodeMenu = document.getElementById("contextMenu");
        nodeMenu.style.display = "none";
        menu.style.display = "block";
        menu.style.left = x + "px";
        menu.style.top = y + "px";
        menu._targetPort = port;
    },

    _hidePortContextMenu() {
        document.getElementById("portContextMenu").style.display = "none";
    },

    _deletePort(port) {
        const node = port.node;

        if (port.type === "input" && !node.canRemoveInput()) return;
        if (port.type === "output" && !node.canRemoveOutput()) return;

        if (port.type === "input") {
            node.inputs = node.inputs.filter((p) => p !== port);
            node.inputs.forEach((p, i) => {
                p.index = i;
                p.id = `${node.id}_input_${i}`;
            });
        } else {
            node.outputs = node.outputs.filter((p) => p !== port);
            node.outputs.forEach((p, i) => {
                p.index = i;
                p.id = `${node.id}_output_${i}`;
            });
        }

        this._saveUndoState();
        this.links = this.links.filter((l) => l.from !== port && l.to !== port);
        this.ports = this._collectPorts();
        node.updatePorts();
        this._saveToSession();
        this._render();
    },

    _disconnectPort(port) {
        this._saveUndoState();
        // Remove all links connected to this port
        this.links = this.links.filter((l) => l.from !== port && l.to !== port);
        this._saveToSession();
        this._render();
    },
    // ========== PROPERTIES ==========
    _showProperties(node) {
        const panel = document.getElementById("propertiesPanel");
        const content = document.getElementById("propertiesContent");
        panel.style.display = "block";
        content.innerHTML = node.getPropertiesHTML();
        this._bindPropertiesEvents(node);
    },

    _hideProperties() {
        document.getElementById("propertiesPanel").style.display = "none";
    },
    _showPortProperties() {
        const panel = document.getElementById("propertiesPanel");
        const content = document.getElementById("propertiesContent");
        panel.style.display = "block";

        if (this.selectedPorts.length === 0) {
            panel.style.display = "none";
            return;
        }

        if (this.selectedPorts.length > 1) {
            content.innerHTML = `<p class='prop-hint'>${this.selectedPorts.length} ports selected</p>`;
            return;
        }

        const port = this.selectedPorts[0];
        const connectedLinks = this.links.filter(
            (l) => l.from === port || l.to === port,
        );

        const allSubTypes = [
            { value: "", label: "Default" },
            { value: "train", label: "Train" },
            { value: "test", label: "Test" },
            { value: "features", label: "Features" },
            { value: "labels", label: "Labels" },
        ];

        // Filter by node's allowed output types
        let subTypeOptions;
        if (port.type === "output" && port.node.allowedOutputTypes) {
            subTypeOptions = allSubTypes.filter(
                (o) =>
                    o.value === "" ||
                    port.node.allowedOutputTypes.includes(o.value),
            );
        } else {
            subTypeOptions = allSubTypes;
        }

        content.innerHTML = `
        <div class="prop-group">
            <label>Port</label>
            <p class="prop-hint">${port.type === "input" ? "Input" : "Output"} #${port.index + 1} — ${port.node.type}</p>
        </div>
        ${
            port.type === "output"
                ? `
        <div class="prop-group">
            <label>Output Type</label>
            <select id="prop-port-subtype" class="prop-select" onchange="SketchMod._updatePortSubType(this)">
                ${subTypeOptions
                    .map(
                        (o) => `
                    <option value="${o.value}" ${port.subType === o.value ? "selected" : ""}>${o.label}</option>
                `,
                    )
                    .join("")}
            </select>
        </div>
        `
                : ""
        }
        <div class="prop-group">
            <label>Connections</label>
            <p class="prop-hint">${connectedLinks.length} link${connectedLinks.length !== 1 ? "s" : ""}</p>
        </div>
        <div class="prop-group">
            <button class="prop-btn prop-btn-danger" onclick="SketchMod._disconnectPort(SketchMod.selectedPorts[0])">
                Disconnect All
            </button>
        </div>
    `;

        this._currentPortForProps = port;
    },

    _updatePortSubType(select) {
        if (!this._currentPortForProps) return;
        this._saveUndoState();

        this._currentPortForProps.subType = select.value || null;
        this._saveToSession();
        this._render();
    },
    _bindPropertiesEvents(node) {
        const actSelect = document.getElementById("prop-activation");
        if (actSelect) {
            actSelect.addEventListener("change", () => {
                this._saveUndoState();
                node.activation = actSelect.value;
                this._saveToSession();
            });
        }
        const sizeInput = document.getElementById("prop-size");
        if (sizeInput) {
            sizeInput.addEventListener("change", () => {
                this._saveUndoState();
                node.numNeurons = parseInt(sizeInput.value) || 64;
                this._saveToSession();
            });
        }
    },
    _toggleDatasetPicker() {
        const picker = document.getElementById("datasetPicker");
        if (!picker) return;
        const isOpen = picker.style.display !== "none";
        picker.style.display = isOpen ? "none" : "block";
        if (!isOpen) this._loadDatasets("all", "");
    },

    _loadDatasets(section, search) {
        const list = document.getElementById("datasetList");
        if (!list) return;
        list.innerHTML = '<div class="dataset-loading">Loading...</div>';

        let url = `/data/api/list/?section=${section}&search=${encodeURIComponent(search)}`;
        fetch(url)
            .then((res) => res.json())
            .then((data) => {
                if (data.datasets.length === 0) {
                    list.innerHTML =
                        '<div class="dataset-empty">No datasets found</div>';
                    return;
                }
                list.innerHTML = data.datasets
                    .map(
                        (d) => `
                <div class="dataset-item" onclick="SketchMod._selectDataset('${d.id}', '${d.name.replace(/'/g, "\\'")}')">
                    <div class="dataset-item-info">
                        <span class="dataset-item-name">${d.name}</span>
                        <span class="dataset-item-meta">${d.format} · ${d.owner} · ${d.created_at}</span>
                    </div>
                    ${d.is_private ? '<span class="dataset-badge">Private</span>' : ""}
                </div>
            `,
                    )
                    .join("");
            })
            .catch(() => {
                list.innerHTML =
                    '<div class="dataset-empty">Failed to load datasets</div>';
            });
    },

    _selectDataset(datasetId, datasetName) {
        this.selectedDatasetId = datasetId;
        this.selectedDatasetName = datasetName;
        document.getElementById("selectedDatasetName").textContent =
            datasetName;
        document.getElementById("datasetPicker").style.display = "none";

        // Update the selected node
        if (
            this.selectedNodes.length === 1 &&
            this.selectedNodes[0] instanceof InputDataNode
        ) {
            this.selectedNodes[0].datasetId = datasetId;
            this.selectedNodes[0].datasetName = datasetName;
            this._showProperties(this.selectedNodes[0]);
            this._saveToSession();
        }
    },

    // ========== SESSION ==========
    _saveToSession() {
        const data = {
            nodes: this.nodes.map((n) => n.toJSON()),
            links: this.links.map((l) => l.toJSON()),
            nodeCounter: this.nodeCounter,
        };
        sessionStorage.setItem("sketchmod-graph", JSON.stringify(data));
    },

    _loadFromSession() {
        const raw = sessionStorage.getItem("sketchmod-graph");
        if (!raw) return;
        try {
            const data = JSON.parse(raw);
            this.nodeCounter = data.nodeCounter || 0;
            this.nodes = [];
            this.links = [];

            for (const n of data.nodes) {
                let node;
                if (n.type === "neuron") node = new NeuronNode(n.id, n.x, n.y);
                else if (n.type === "layer")
                    node = new LayerNode(n.id, n.x, n.y);
                else if (n.type === "input-data")
                    node = new InputDataNode(n.id, n.x, n.y);
                else if (n.type === "output")
                    node = new OutputNode(n.id, n.x, n.y);
                else if (n.type === "column-select")
                    node = new ColumnSelectNode(n.id, n.x, n.y);
                else if (n.type === "train-test")
                    node = new TrainTestSplitNode(n.id, n.x, n.y);
                else if (n.type === "normalize")
                    node = new NormalizeNode(n.id, n.x, n.y);
                if (node) {
                    node.fromJSON(n);
                    this.nodes.push(node);
                }
            }
            this.ports = this._collectPorts();

            for (const l of data.links) {
                const from = this.ports.find((p) => p.id === l.from);
                const to = this.ports.find((p) => p.id === l.to);
                if (from && to) this.links.push(new Link(from, to, l.weight));
            }
        } catch (e) {
            console.warn("Session restore failed:", e);
        }
    },

    // ========== SERVER ==========
    _saveToServer() {
        const data = this._getGraphData();
        console.log(
            "Saving to server:",
            data.nodes.length,
            "nodes,",
            data.links.length,
            "links",
        );
        // TODO: POST to API
    },

    _translate() {
        const code = this._compileToPython();
        const blob = new Blob([code], { type: "text/plain" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "model.py";
        a.click();
        URL.revokeObjectURL(url);
    },

    _compileToPython() {
        let code = [];
        code.push("import torch");
        code.push("import torch.nn as nn");
        code.push("");
        code.push("class SketchNetModel(nn.Module):");
        code.push("    def __init__(self):");
        code.push("        super().__init__()");
        code.push("        self.layers = nn.Sequential(");

        for (const node of this.nodes) {
            if (node.type === "layer") {
                code.push(
                    `            nn.Linear(in_features, ${node.numNeurons}),`,
                );
                if (node.activation === "relu")
                    code.push("            nn.ReLU(),");
                if (node.activation === "sigmoid")
                    code.push("            nn.Sigmoid(),");
                if (node.activation === "tanh")
                    code.push("            nn.Tanh(),");
            }
        }
        code.push("        )");
        code.push("");
        code.push("    def forward(self, x):");
        code.push("        return self.layers(x)");
        return code.join("\n");
    },

    _getGraphData() {
        return {
            nodes: this.nodes.map((n) => n.toJSON()),
            links: this.links.map((l) => l.toJSON()),
        };
    },

    // ========== TOOLS ==========
    setTool(toolName) {
        this.currentTool = toolName;
        document
            .querySelectorAll(".tool-btn")
            .forEach((b) => b.classList.remove("active"));
        const btn = document.querySelector(`[data-tool="${toolName}"]`);
        if (btn) btn.classList.add("active");
    },
    // ========== history ==========
    _saveUndoState() {
        const state = {
            nodes: this.nodes.map((n) => n.toJSON()),
            links: this.links.map((l) => l.toJSON()),
            nodeCounter: this.nodeCounter,
        };
        this.undoStack.push(state);
        if (this.undoStack.length > this.maxUndo) {
            this.undoStack.shift();
        }
        this.redoStack = [];
    },
    _undo() {
        if (this.undoStack.length === 0) return;
        this.selectedNodes = [];
        this.selectedLinks = [];
        this.selectedPorts = [];
        this._hideProperties();
        this.redoStack.push(this._captureState());
        this._restoreState(this.undoStack.pop());
        this.ports = this._collectPorts();
        this._render();
    },

    _redo() {
        if (this.redoStack.length === 0) return;
        this.selectedNodes = [];
        this.selectedLinks = [];
        this.selectedPorts = [];
        this._hideProperties();
        this.undoStack.push(this._captureState());
        this._restoreState(this.redoStack.pop());
        this.ports = this._collectPorts();
        this._render();
    },

    _captureState() {
        return {
            nodes: this.nodes.map((n) => n.toJSON()),
            links: this.links.map((l) => l.toJSON()),
            nodeCounter: this.nodeCounter,
        };
    },

    _restoreState(state) {
        this.nodes = [];
        this.links = [];
        this.nodeCounter = state.nodeCounter;
        for (const n of state.nodes) {
            let node;
            if (n.type === "neuron") node = new NeuronNode(n.id, n.x, n.y);
            else if (n.type === "layer") node = new LayerNode(n.id, n.x, n.y);
            else if (n.type === "input-data")
                node = new InputDataNode(n.id, n.x, n.y);
            else if (n.type === "output") node = new OutputNode(n.id, n.x, n.y);
            else if (n.type === "column-select")
                node = new ColumnSelectNode(n.id, n.x, n.y);
            else if (n.type === "train-test")
                node = new TrainTestSplitNode(n.id, n.x, n.y);
            else if (n.type === "normalize")
                node = new NormalizeNode(n.id, n.x, n.y);
            if (node) {
                // Clear default ports created by constructor
                node.inputs = [];
                node.outputs = [];
                node.fromJSON(n);
                this.nodes.push(node);
            }
        }
        this.ports = this._collectPorts();
        for (const l of state.links) {
            const from = this.ports.find((p) => p.id === l.from);
            const to = this.ports.find((p) => p.id === l.to);
            if (from && to) this.links.push(new Link(from, to, l.weight));
        }
    },

    // ========== RENDER ==========
    _render() {
        const ctx = this.ctx;
        const w = this.canvas.width;
        const h = this.canvas.height;
        ctx.clearRect(0, 0, w, h);
        ctx.save();
        ctx.translate(this.offsetX, this.offsetY);
        ctx.scale(this.scale, this.scale);

        // Links
        for (const link of this.links) {
            link.draw(ctx, this.selectedLinks.includes(link));
        }

        // Temp link line while dragging from port
        if (this.linking.active && this.linking.sourcePort) {
            const from = this.linking.sourcePort;
            let toX, toY;
            if (this.linking.mouseX !== undefined) {
                const world = this._toWorld(
                    this.linking.mouseX,
                    this.linking.mouseY,
                );
                toX = world.x;
                toY = world.y;
            } else {
                toX = from.x + 100;
                toY = from.y;
            }
            ctx.strokeStyle = "var(--accent)";
            ctx.lineWidth = 2;
            ctx.setLineDash([6, 4]);
            ctx.beginPath();
            ctx.moveTo(from.x, from.y);
            ctx.lineTo(toX, toY);
            ctx.stroke();
            ctx.setLineDash([]);

            ctx.beginPath();
            ctx.arc(toX, toY, 4, 0, Math.PI * 2);
            ctx.fillStyle = "var(--accent)";
            ctx.fill();
        }

        // Nodes
        for (const node of this.nodes) {
            node.draw(ctx, this.selectedNodes.includes(node));
        }

        // Ports
        for (const port of this.ports) {
            const isSelected = this.selectedPorts.includes(port);
            if (isSelected) port.drawHighlight(ctx);
            port.draw(ctx);
        }

        ctx.restore();

        // Draw selection box (in screen space, after restore)
        if (this.isSelecting && this.selectionBox) {
            const box = this.selectionBox;
            const x = Math.min(box.startX, box.endX);
            const y = Math.min(box.startY, box.endY);
            const bw = Math.abs(box.endX - box.startX);
            const bh = Math.abs(box.endY - box.startY);
            ctx.fillStyle = "rgba(108, 92, 231, 0.1)";
            ctx.fillRect(x, y, bw, bh);
            ctx.strokeStyle = "var(--accent)";
            ctx.lineWidth = 1;
            ctx.setLineDash([4, 4]);
            ctx.strokeRect(x, y, bw, bh);
            ctx.setLineDash([]);
        }
    },

    // ========== removing ports ==========
    _removePort(node, type) {
        if (type === "input" && node.inputs.length === 0) return;
        if (type === "output" && node.outputs.length === 0) return;

        this._saveUndoState();
        // Remove the last port of that type
        let port;
        if (type === "input") {
            port = node.inputs.pop();
        } else {
            port = node.outputs.pop();
        }

        // Remove any links connected to this port
        this.links = this.links.filter((l) => l.from !== port && l.to !== port);

        // Rebuild port list
        this.ports = this._collectPorts();
        node.updatePorts();
    },
};

// ========== NODE CLASSES ==========

class BaseNode {
    constructor(id, x, y, type) {
        this.id = id;
        this.x = x;
        this.y = y;
        this.type = type;
        this.inputs = [];
        this.outputs = [];

        // Constraints — override in subclasses
        this.maxInputs = Infinity;
        this.minInputs = 0;
        this.maxOutputs = Infinity;
        this.minOutputs = 0;
        this.allowedInputTypes = null; // null = any, ["features"] = only features
        this.allowedOutputTypes = null; // null = any, ["train", "test"] = only train or test
    }

    containsPoint(px, py) {
        const b = this.getBounds();
        return px >= b.x && px <= b.x + b.w && py >= b.y && py <= b.y + b.h;
    }

    canAddInput(portType) {
        if (this.inputs.length >= this.maxInputs) return false;
        if (
            this.allowedInputTypes &&
            portType &&
            !this.allowedInputTypes.includes(portType)
        )
            return false;
        return true;
    }

    canAddOutput(portType) {
        if (this.outputs.length >= this.maxOutputs) return false;
        if (
            this.allowedOutputTypes &&
            portType &&
            !this.allowedOutputTypes.includes(portType)
        )
            return false;
        return true;
    }

    canRemoveInput() {
        return this.inputs.length > this.minInputs;
    }

    canRemoveOutput() {
        return this.outputs.length > this.minOutputs;
    }

    addInput(subType) {
        if (!this.canAddInput(subType)) return null;
        const p = new Port(this, "input", this.inputs.length, subType || null);
        this.inputs.push(p);
        this.updatePorts();
        return p;
    }

    addOutput(subType) {
        if (!this.canAddOutput(subType)) return null;
        const p = new Port(
            this,
            "output",
            this.outputs.length,
            subType || null,
        );
        this.outputs.push(p);
        this.updatePorts();
        return p;
    }

    removeInput() {
        if (!this.canRemoveInput()) return null;
        const port = this.inputs.pop();
        return port;
    }

    removeOutput() {
        if (!this.canRemoveOutput()) return null;
        const port = this.outputs.pop();
        return port;
    }
    getPorts() {
        return [...this.inputs, ...this.outputs];
    }

    updatePorts() {}

    toJSON() {
        return {
            id: this.id,
            type: this.type,
            x: this.x,
            y: this.y,
            inputPorts: this.inputs.map((p) => ({
                id: p.id,
                index: p.index,
                subType: p.subType,
            })),
            outputPorts: this.outputs.map((p) => ({
                id: p.id,
                index: p.index,
                subType: p.subType,
            })),
            numInputs: this.inputs.length,
            numOutputs: this.outputs.length,
            activation: this.activation,
            numNeurons: this.numNeurons,
        };
    }

    fromJSON(data) {
        this.inputs = [];
        this.outputs = [];
        // Restore inputs with their subTypes
        if (data.inputPorts) {
            for (const p of data.inputPorts) {
                const port = new Port(
                    this,
                    "input",
                    p.index,
                    p.subType || null,
                );
                port.id = p.id;
                this.inputs.push(port);
            }
        } else {
            for (let i = 0; i < (data.numInputs || 0); i++) this.addInput();
        }
        // Restore outputs with their subTypes
        if (data.outputPorts) {
            for (const p of data.outputPorts) {
                const port = new Port(
                    this,
                    "output",
                    p.index,
                    p.subType || null,
                );
                port.id = p.id;
                this.outputs.push(port);
            }
        } else {
            for (let i = 0; i < (data.numOutputs || 0); i++) this.addOutput();
        }
        if (data.activation) this.activation = data.activation;
        if (data.numNeurons) this.numNeurons = data.numNeurons;
        this.updatePorts();
    }

    getPropertiesHTML() {
        return "";
    }
}

class NeuronNode extends BaseNode {
    constructor(id, x, y) {
        super(id, x, y, "neuron");
        this.radius = 28;
        this.activation = "relu";

        this.maxInputs = Infinity;
        this.minInputs = 1;
        this.maxOutputs = Infinity;
        this.minOutputs = 1;

        this.addInput();
        this.addOutput();
    }

    getBounds() {
        return {
            x: this.x - this.radius,
            y: this.y - this.radius,
            w: this.radius * 2,
            h: this.radius * 2,
        };
    }

    containsPoint(px, py) {
        return Math.hypot(px - this.x, py - this.y) <= this.radius;
    }

    updatePorts() {
        const r = this.radius + 8;
        this.inputs.forEach((p, i) => {
            const a =
                this.inputs.length === 1
                    ? Math.PI
                    : Math.PI - 0.6 + (i / (this.inputs.length - 1)) * 1.2;
            p.x = this.x + Math.cos(a) * r;
            p.y = this.y + Math.sin(a) * r;
        });
        this.outputs.forEach((p, i) => {
            const a =
                this.outputs.length === 1
                    ? 0
                    : -0.6 + (i / (this.outputs.length - 1)) * 1.2;
            p.x = this.x + Math.cos(a) * r;
            p.y = this.y + Math.sin(a) * r;
        });
    }

    draw(ctx, selected) {
        const color = SketchMod._getNodeColor();

        if (selected) {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.radius + 2, 0, Math.PI * 2);
            ctx.fillStyle = "var(--accent-glow)";
            ctx.fill();
        }

        ctx.beginPath();
        ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
        ctx.fillStyle = color.fill;
        ctx.fill();
        ctx.strokeStyle = selected ? "#ffffff" : color.stroke;
        ctx.lineWidth = selected ? 2.5 : 1.5;
        ctx.stroke();

        ctx.fillStyle = "#ffffff";
        ctx.font = "bold 15px Inter, sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText("N", this.x, this.y);
    }

    getPropertiesHTML() {
        return `<div class="prop-group"><label>Activation</label><select id="prop-activation" class="prop-select">
            <option value="relu" ${this.activation === "relu" ? "selected" : ""}>ReLU</option>
            <option value="sigmoid" ${this.activation === "sigmoid" ? "selected" : ""}>Sigmoid</option>
            <option value="tanh" ${this.activation === "tanh" ? "selected" : ""}>Tanh</option>
        </select></div>`;
    }
}

class LayerNode extends BaseNode {
    constructor(id, x, y) {
        super(id, x, y, "layer");
        this.width = 110;
        this.height = 65;
        this.numNeurons = 64;
        this.activation = "relu";

        this.maxInputs = 1;
        this.minInputs = 1;
        this.maxOutputs = 1;
        this.minOutputs = 1;

        this.addInput();
        this.addOutput();
    }

    getBounds() {
        return {
            x: this.x - this.width / 2,
            y: this.y - this.height / 2,
            w: this.width,
            h: this.height,
        };
    }

    updatePorts() {
        const hw = this.width / 2 + 8;
        this.inputs.forEach((p, i) => {
            p.x = this.x - hw;
            p.y =
                this.y -
                this.height / 2 +
                (this.height / (this.inputs.length + 1)) * (i + 1);
        });
        this.outputs.forEach((p, i) => {
            p.x = this.x + hw;
            p.y =
                this.y -
                this.height / 2 +
                (this.height / (this.outputs.length + 1)) * (i + 1);
        });
    }

    draw(ctx, selected) {
        const color = SketchMod._getNodeColor();
        const x = this.x - this.width / 2;
        const y = this.y - this.height / 2;

        if (selected) {
            ctx.beginPath();
            ctx.roundRect(x - 1, y - 1, this.width + 2, this.height + 2, 10);
            ctx.fillStyle = "var(--accent-glow)";
            ctx.fill();
        }

        ctx.beginPath();
        ctx.roundRect(x, y, this.width, this.height, 8);
        ctx.fillStyle = color.fill;
        ctx.fill();
        ctx.strokeStyle = selected ? "#ffffff" : color.stroke;
        ctx.lineWidth = selected ? 2.5 : 1.5;
        ctx.stroke();

        ctx.fillStyle = "#ffffff";
        ctx.font = "bold 14px Inter, sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(this.numNeurons + "", this.x, this.y - 9);
        ctx.font = "11px Inter, sans-serif";
        ctx.fillText("Layer", this.x, this.y + 12);
    }

    getPropertiesHTML() {
        return `<div class="prop-group"><label>Neurons</label><input type="number" id="prop-size" class="prop-input" value="${this.numNeurons}" min="1" max="4096"></div>
        <div class="prop-group"><label>Activation</label><select id="prop-activation" class="prop-select">
            <option value="relu" ${this.activation === "relu" ? "selected" : ""}>ReLU</option>
            <option value="sigmoid" ${this.activation === "sigmoid" ? "selected" : ""}>Sigmoid</option>
            <option value="tanh" ${this.activation === "tanh" ? "selected" : ""}>Tanh</option>
        </select></div>`;
    }
}

class InputDataNode extends BaseNode {
    constructor(id, x, y) {
        super(id, x, y, "input-data");
        this.width = 100;
        this.height = 55;
        this.datasetId = null;
        this.datasetName = null;
        this.dataShape = null;

        this.maxInputs = 0;
        this.minInputs = 0;
        this.maxOutputs = 2;
        this.minOutputs = 1;
        this.allowedOutputTypes = ["features", "labels"];

        this.addOutput();
    }

    getBounds() {
        return {
            x: this.x - this.width / 2,
            y: this.y - this.height / 2,
            w: this.width,
            h: this.height,
        };
    }

    updatePorts() {
        this.outputs.forEach((p, i) => {
            p.x = this.x + this.width / 2 + 8;
            p.y =
                this.y -
                this.height / 2 +
                (this.height / (this.outputs.length + 1)) * (i + 1);
        });
    }

    draw(ctx, selected) {
        const color = SketchMod._getNodeColor();
        const x = this.x - this.width / 2;
        const y = this.y - this.height / 2;

        if (selected) {
            ctx.beginPath();
            ctx.roundRect(x - 4, y - 4, this.width + 8, this.height + 8, 8);
            ctx.fillStyle = "var(--accent-glow)";
            ctx.fill();
        }

        ctx.beginPath();
        ctx.roundRect(x, y, this.width, this.height, 7);
        ctx.fillStyle = color.fill;
        ctx.fill();
        ctx.strokeStyle = selected ? "#ffffff" : color.stroke;
        ctx.lineWidth = selected ? 2.5 : 1.5;
        ctx.stroke();

        ctx.fillStyle = "#ffffff";
        ctx.font = "bold 13px Inter, sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText("Input", this.x, this.y);
    }

    getPropertiesHTML() {
        return `
        <div class="prop-group">
            <label>Dataset</label>
            <div class="dataset-selector" id="datasetSelector">
                <div class="dataset-select-display" id="datasetSelectDisplay" onclick="SketchMod._toggleDatasetPicker()">
                    <span id="selectedDatasetName">${this.datasetName || "Select a dataset..."}</span>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="6 9 12 15 18 9"/>
                    </svg>
                </div>
                <div class="dataset-picker" id="datasetPicker" style="display: none;">
                    <div class="dataset-picker-tabs">
                        <button class="dataset-tab active" data-section="all">All</button>
                        <button class="dataset-tab" data-section="mine">My</button>
                        <button class="dataset-tab" data-section="liked">Liked</button>
                    </div>
                    <input type="text" class="prop-input dataset-search" id="datasetSearch" placeholder="Search datasets...">
                    <div class="dataset-list" id="datasetList">
                        <div class="dataset-loading">Loading...</div>
                    </div>
                </div>
            </div>
        </div>
        ${this.datasetId ? `<div class="prop-group"><label>Dataset ID</label><p class="prop-hint" style="font-family: monospace;">${this.datasetId}</p></div>` : ""}
        <div class="prop-group">
            <label>Shape</label>
            <p class="prop-hint">${this.dataShape || "Unknown — connect a dataset first"}</p>
        </div>
    `;
    }

    toJSON() {
        const base = super.toJSON();
        return {
            ...base,
            datasetId: this.datasetId,
            datasetName: this.datasetName,
            dataShape: this.dataShape,
        };
    }

    fromJSON(data) {
        super.fromJSON(data);
        if (data.datasetId) this.datasetId = data.datasetId;
        if (data.datasetName) this.datasetName = data.datasetName;
        if (data.dataShape) this.dataShape = data.dataShape;
    }
}

class OutputNode extends BaseNode {
    constructor(id, x, y) {
        super(id, x, y, "output");
        this.width = 100;
        this.height = 55;

        this.maxInputs = Infinity;
        this.minInputs = 1;
        this.maxOutputs = 0;
        this.minOutputs = 0;

        this.addInput();
    }

    getBounds() {
        return {
            x: this.x - this.width / 2,
            y: this.y - this.height / 2,
            w: this.width,
            h: this.height,
        };
    }

    updatePorts() {
        this.inputs.forEach((p, i) => {
            p.x = this.x - this.width / 2 - 8;
            p.y =
                this.y -
                this.height / 2 +
                (this.height / (this.inputs.length + 1)) * (i + 1);
        });
    }

    draw(ctx, selected) {
        const color = SketchMod._getNodeColor();
        const x = this.x - this.width / 2;
        const y = this.y - this.height / 2;

        if (selected) {
            ctx.beginPath();
            ctx.roundRect(x - 1, y - 1, this.width + 2, this.height + 2, 8);
            ctx.fillStyle = "var(--accent-glow)";
            ctx.fill();
        }

        ctx.beginPath();
        ctx.roundRect(x, y, this.width, this.height, 7);
        ctx.fillStyle = color.fill;
        ctx.fill();
        ctx.strokeStyle = selected ? "#ffffff" : color.stroke;
        ctx.lineWidth = selected ? 2.5 : 1.5;
        ctx.stroke();

        ctx.fillStyle = "#ffffff";
        ctx.font = "bold 13px Inter, sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText("Output", this.x, this.y);
    }

    getPropertiesHTML() {
        return "<p class='prop-hint'>Output node — collects results.</p>";
    }
}
// ========== COLUMN SELECT NODE ==========
class ColumnSelectNode extends BaseNode {
    constructor(id, x, y) {
        super(id, x, y, "column-select");
        this.width = 100;
        this.height = 60;
        this.selectedColumns = [];
        this.availableColumns = [];

        this.maxInputs = 1;
        this.minInputs = 1;
        this.maxOutputs = 1;
        this.minOutputs = 1;

        this.addInput();
        this.addOutput();
    }

    getBounds() {
        return {
            x: this.x - this.width / 2,
            y: this.y - this.height / 2,
            w: this.width,
            h: this.height,
        };
    }

    updatePorts() {
        const hw = this.width / 2 + 8;
        this.inputs.forEach((p, i) => {
            p.x = this.x - hw;
            p.y =
                this.y -
                this.height / 2 +
                (this.height / (this.inputs.length + 1)) * (i + 1);
        });
        this.outputs.forEach((p, i) => {
            p.x = this.x + hw;
            p.y =
                this.y -
                this.height / 2 +
                (this.height / (this.outputs.length + 1)) * (i + 1);
        });
    }

    draw(ctx, selected) {
        const color = SketchMod._getNodeColor();
        const x = this.x - this.width / 2;
        const y = this.y - this.height / 2;

        if (selected) {
            ctx.beginPath();
            ctx.roundRect(x - 4, y - 4, this.width + 8, this.height + 8, 8);
            ctx.fillStyle = "var(--accent-glow)";
            ctx.fill();
        }

        ctx.beginPath();
        ctx.roundRect(x, y, this.width, this.height, 7);
        ctx.fillStyle = color.fill;
        ctx.fill();
        ctx.strokeStyle = selected ? "#ffffff" : color.stroke;
        ctx.lineWidth = selected ? 2.5 : 1.5;
        ctx.stroke();

        ctx.fillStyle = "#ffffff";
        ctx.font = "bold 11px Inter, sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        const label =
            this.selectedColumns.length > 0
                ? this.selectedColumns.length + " cols"
                : "Columns";
        ctx.fillText(label, this.x, this.y);
    }

    toJSON() {
        const base = super.toJSON();
        return {
            ...base,
            selectedColumns: this.selectedColumns,
            availableColumns: this.availableColumns,
        };
    }

    fromJSON(data) {
        super.fromJSON(data);
        if (data.selectedColumns) this.selectedColumns = data.selectedColumns;
        if (data.availableColumns)
            this.availableColumns = data.availableColumns;
    }

    getPropertiesHTML() {
        const colList =
            this.availableColumns.length > 0
                ? this.availableColumns
                      .map(
                          (c) => `
                <label class="checkbox-label">
                    <input type="checkbox" value="${c}" ${this.selectedColumns.includes(c) ? "checked" : ""}
                           onchange="SketchMod._updateColumnSelect(this)">
                    ${c}
                </label>
            `,
                      )
                      .join("")
                : "<p class='prop-hint'>Connect a dataset to see columns</p>";

        return `
            <div class="prop-group">
                <label>Select Columns</label>
                <div class="checkbox-group" id="columnCheckboxes">${colList}</div>
            </div>
        `;
    }
}

// ========== TRAIN/TEST SPLIT NODE ==========
class TrainTestSplitNode extends BaseNode {
    constructor(id, x, y) {
        super(id, x, y, "train-test");
        this.width = 110;
        this.height = 70;
        this.trainRatio = 0.7;
        this.testRatio = 0.3;
        this.randomSeed = 42;

        this.maxInputs = 1;
        this.minInputs = 1;
        this.maxOutputs = 2;
        this.minOutputs = 2;
        this.allowedOutputTypes = ["train", "test"];

        this.addInput();
        this.addOutput("train");
        this.addOutput("test");
    }

    getBounds() {
        return {
            x: this.x - this.width / 2,
            y: this.y - this.height / 2,
            w: this.width,
            h: this.height,
        };
    }

    updatePorts() {
        const hw = this.width / 2 + 8;
        this.inputs.forEach((p, i) => {
            p.x = this.x - hw;
            p.y =
                this.y -
                this.height / 2 +
                (this.height / (this.inputs.length + 1)) * (i + 1);
        });
        this.outputs.forEach((p, i) => {
            p.x = this.x + hw;
            p.y =
                this.y -
                this.height / 2 +
                (this.height / (this.outputs.length + 1)) * (i + 1);
        });
    }

    draw(ctx, selected) {
        const color = SketchMod._getNodeColor();
        const x = this.x - this.width / 2;
        const y = this.y - this.height / 2;

        if (selected) {
            ctx.beginPath();
            ctx.roundRect(x - 4, y - 4, this.width + 8, this.height + 8, 8);
            ctx.fillStyle = "var(--accent-glow)";
            ctx.fill();
        }

        ctx.beginPath();
        ctx.roundRect(x, y, this.width, this.height, 7);
        ctx.fillStyle = color.fill;
        ctx.fill();
        ctx.strokeStyle = selected ? "#ffffff" : color.stroke;
        ctx.lineWidth = selected ? 2.5 : 1.5;
        ctx.stroke();

        ctx.fillStyle = "#ffffff";
        ctx.font = "bold 12px Inter, sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText("Train/Test", this.x, this.y - 8);
        ctx.font = "10px Inter, sans-serif";
        ctx.fillText(
            `${Math.round(this.trainRatio * 100)}/${Math.round(this.testRatio * 100)}`,
            this.x,
            this.y + 10,
        );
    }

    toJSON() {
        const base = super.toJSON();
        return {
            ...base,
            trainRatio: this.trainRatio,
            testRatio: this.testRatio,
            randomSeed: this.randomSeed,
        };
    }

    fromJSON(data) {
        super.fromJSON(data);
        if (data.trainRatio) this.trainRatio = data.trainRatio;
        if (data.testRatio) this.testRatio = data.testRatio;
        if (data.randomSeed) this.randomSeed = data.randomSeed;
    }

    getPropertiesHTML() {
        return `
            <div class="prop-group">
                <label>Train Ratio</label>
                <input type="range" id="prop-train-ratio" class="prop-range" min="0.1" max="0.9" step="0.05"
                       value="${this.trainRatio}" oninput="SketchMod._updateTrainTest(this)">
                <div class="range-values">
                    <span>Train: ${Math.round(this.trainRatio * 100)}%</span>
                    <span>Test: ${Math.round(this.testRatio * 100)}%</span>
                </div>
            </div>
            <div class="prop-group">
                <label>Random Seed</label>
                <input type="number" id="prop-random-seed" class="prop-input" value="${this.randomSeed}"
                       onchange="SketchMod._updateTrainTestSeed(this)">
            </div>
        `;
    }
}

// ========== NORMALIZE NODE ==========
class NormalizeNode extends BaseNode {
    constructor(id, x, y) {
        super(id, x, y, "normalize");
        this.width = 100;
        this.height = 55;
        this.method = "standard";

        this.maxInputs = 1;
        this.minInputs = 1;
        this.maxOutputs = 1;
        this.minOutputs = 1;

        this.addInput();
        this.addOutput();
    }

    getBounds() {
        return {
            x: this.x - this.width / 2,
            y: this.y - this.height / 2,
            w: this.width,
            h: this.height,
        };
    }

    updatePorts() {
        const hw = this.width / 2 + 8;
        this.inputs.forEach((p, i) => {
            p.x = this.x - hw;
            p.y =
                this.y -
                this.height / 2 +
                (this.height / (this.inputs.length + 1)) * (i + 1);
        });
        this.outputs.forEach((p, i) => {
            p.x = this.x + hw;
            p.y =
                this.y -
                this.height / 2 +
                (this.height / (this.outputs.length + 1)) * (i + 1);
        });
    }

    draw(ctx, selected) {
        const color = SketchMod._getNodeColor();
        const x = this.x - this.width / 2;
        const y = this.y - this.height / 2;

        if (selected) {
            ctx.beginPath();
            ctx.roundRect(x - 4, y - 4, this.width + 8, this.height + 8, 8);
            ctx.fillStyle = "var(--accent-glow)";
            ctx.fill();
        }

        ctx.beginPath();
        ctx.roundRect(x, y, this.width, this.height, 7);
        ctx.fillStyle = color.fill;
        ctx.fill();
        ctx.strokeStyle = selected ? "#ffffff" : color.stroke;
        ctx.lineWidth = selected ? 2.5 : 1.5;
        ctx.stroke();

        ctx.fillStyle = "#ffffff";
        ctx.font = "bold 11px Inter, sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(
            this.method === "standard" ? "Standard" : "MinMax",
            this.x,
            this.y - 6,
        );
        ctx.font = "10px Inter, sans-serif";
        ctx.fillText("Normalize", this.x, this.y + 12);
    }

    toJSON() {
        const base = super.toJSON();
        return { ...base, method: this.method };
    }

    fromJSON(data) {
        super.fromJSON(data);
        if (data.method) this.method = data.method;
    }

    getPropertiesHTML() {
        return `
            <div class="prop-group">
                <label>Method</label>
                <select id="prop-normalize-method" class="prop-select" onchange="SketchMod._updateNormalize(this)">
                    <option value="standard" ${this.method === "standard" ? "selected" : ""}>Standard (Z-score)</option>
                    <option value="minmax" ${this.method === "minmax" ? "selected" : ""}>Min-Max (0 to 1)</option>
                </select>
            </div>
        `;
    }
}
// ========== PORT ==========

class Port {
    constructor(node, type, index, subType) {
        this.node = node;
        this.type = type;
        this.index = index;
        this.subType = subType || null;
        this.x = node.x;
        this.y = node.y;
        this.radius = 5;
        this.hoverRadius = 10;
        this.id = `${node.id}_${type}_${index}`;
    }

    draw(ctx) {
        // Fill
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
        ctx.fillStyle = this._getColor();
        ctx.fill();

        // Border
        ctx.strokeStyle = "#1a1d2e";
        ctx.lineWidth = 1.5;
        ctx.stroke();
    }

    drawHighlight(ctx) {
        // Glow ring when selected
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.hoverRadius, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(255, 255, 255, 0.2)";
        ctx.fill();
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 2.5;
        ctx.stroke();
    }

    _getColor() {
        if (this.subType === "train") return "#f59e0b";
        if (this.subType === "test") return "#4ade80";
        if (this.subType === "features") return "#ff00b7";
        if (this.subType === "labels") return "#a78bfa";
        if (this.type === "input") return "#ef4444";
        if (this.type === "output") return "#60a5fa";
        return "#94a3b8";
    }

    containsPoint(sx, sy) {
        const ps = {
            x: this.x * SketchMod.scale + SketchMod.offsetX,
            y: this.y * SketchMod.scale + SketchMod.offsetY,
        };
        return (
            Math.hypot(sx - ps.x, sy - ps.y) <
            this.hoverRadius * SketchMod.scale + 4
        );
    }

    toJSON() {
        return {
            id: this.id,
            type: this.type,
            index: this.index,
            subType: this.subType,
        };
    }
}

// ========== LINK ==========

class Link {
    constructor(from, to, weight) {
        this.from = from;
        this.to = to;
        this.weight = weight || 0;
    }

    hitTest(px, py) {
        const dx = this.to.x - this.from.x;
        const dy = this.to.y - this.from.y;
        const len2 = dx * dx + dy * dy;
        if (len2 === 0) return false;
        const t = Math.max(
            0,
            Math.min(
                1,
                ((px - this.from.x) * dx + (py - this.from.y) * dy) / len2,
            ),
        );
        const cx = this.from.x + t * dx;
        const cy = this.from.y + t * dy;
        return Math.hypot(px - cx, py - cy) < 8;
    }

    draw(ctx, selected) {
        ctx.beginPath();
        ctx.moveTo(this.from.x, this.from.y);
        ctx.lineTo(this.to.x, this.to.y);
        ctx.strokeStyle = selected ? "var(--accent)" : "var(--text-secondary)";
        ctx.lineWidth = selected ? 3 : 2;
        ctx.stroke();

        const angle = Math.atan2(
            this.to.y - this.from.y,
            this.to.x - this.from.x,
        );
        const size = 8;
        ctx.beginPath();
        ctx.moveTo(this.to.x, this.to.y);
        ctx.lineTo(
            this.to.x - size * Math.cos(angle - 0.5),
            this.to.y - size * Math.sin(angle - 0.5),
        );
        ctx.lineTo(
            this.to.x - size * Math.cos(angle + 0.5),
            this.to.y - size * Math.sin(angle + 0.5),
        );
        ctx.closePath();
        ctx.fillStyle = selected ? "var(--accent)" : "var(--text-secondary)";
        ctx.fill();
    }

    toJSON() {
        return { from: this.from.id, to: this.to.id, weight: this.weight };
    }
}

// ========== STARTUP ==========
document.addEventListener("DOMContentLoaded", () => SketchMod.init());
