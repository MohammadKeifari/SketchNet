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

    //propagation
    shapePropagationEnabled: true,

    // Node registry
    nodeRegistry: [],

    //save
    _currentModelId: null,
    _currentModelName: null,

    _highlightPhaseNodes: null, // Set of node instances that are highlighted
    _highlightPhaseLinks: null, // Set of link instances that are highlighted

    clipboard: null,
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
    //=========== register node =============
    registerNode(config) {
        this.nodeRegistry.push(config);
    },
    // ========== INIT ==========
    init() {
        this.canvas = document.getElementById("sketchCanvas");
        this.ctx = this.canvas.getContext("2d");

        // Check if loading a specific model
        const urlParams = new URLSearchParams(window.location.search);
        const loadModelId = urlParams.get("load");

        const hasSession = sessionStorage.getItem("sketchmod-graph");
        if (loadModelId) {
            // Check if session has THIS model
            if (hasSession) {
                const sessionData = JSON.parse(hasSession);
                if (sessionData.modelId === loadModelId) {
                    // Session has the latest — use it
                    this._loadFromSession();
                } else {
                    // Different model — load from server
                    this._loadModelFromServer(loadModelId);
                }
            } else {
                // No session — load from server
                this._loadModelFromServer(loadModelId);
            }
        } else {
            this._loadFromSession();
        }
        // Apply sidebar collapse preferences
        const container = document.querySelector(".sketchmod-container");
        const collapseLeft = container?.dataset.collapseLeft === "true";
        const collapseRight = container?.dataset.collapseRight === "true";

        if (collapseLeft) {
            document.querySelector(".toolbar-left")?.classList.add("collapsed");
        }
        if (collapseRight) {
            document
                .querySelector(".sidebar-right")
                ?.classList.add("collapsed");
        }

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
        document.addEventListener("click", (e) => {
            // Close context menu on any click
            this._hideContextMenu();

            // Close dataset picker when clicking outside
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

            // Dataset tab clicks
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

            // Close save modal on overlay click
            if (e.target.id === "saveModal") {
                this.closeSaveModal();
            }

            // Close validation modal on overlay click
            if (e.target.id === "validationModal") {
                this._closeValidationModal();
            }

            // Close export menu when clicking outside
            const exportMenu = document.getElementById("exportMenu");
            const exportBtn = document.getElementById("btnExport");
            if (
                exportMenu &&
                exportMenu.classList.contains("open") &&
                exportBtn &&
                !exportBtn.contains(e.target) &&
                !exportMenu.contains(e.target)
            ) {
                exportMenu.classList.remove("open");
                document
                    .getElementById("exportDropdown")
                    ?.classList.remove("open");
            }

            // Export menu item clicks
            const exportItem = e.target.closest(".export-menu-item");
            if (
                exportItem &&
                exportMenu &&
                exportMenu.classList.contains("open")
            ) {
                const type = exportItem.dataset.export;
                this._handleExport(type);
                exportMenu.classList.remove("open");
                document
                    .getElementById("exportDropdown")
                    ?.classList.remove("open");
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
        document.addEventListener("change", (e) => {
            if (e.target.id === "saveCoverInput") {
                const name = e.target.files[0]?.name || "No file chosen";
                const display = document.getElementById("saveCoverFileName");
                if (display) display.textContent = name;
            }
            if (e.target.id === "prop-port-subtype") {
                SketchMod._updatePortSubType(e.target);
            }
        });
        // Sidebar buttons
        document
            .getElementById("btnSave")
            ?.addEventListener("click", () => this.openSaveModal());
        // Export button
        document.getElementById("btnExport")?.addEventListener("click", (e) => {
            e.stopPropagation();
            this._toggleExportMenu();
        });

        // Close export menu when clicking outside
        document.addEventListener("click", (e) => {
            const menu = document.getElementById("exportMenu");
            const btn = document.getElementById("btnExport");
            if (
                menu &&
                menu.classList.contains("open") &&
                btn &&
                !btn.contains(e.target) &&
                !menu.contains(e.target)
            ) {
                menu.classList.remove("open");
                document
                    .getElementById("exportDropdown")
                    ?.classList.remove("open");
            }
        });

        // Export menu item clicks
        document.addEventListener("click", (e) => {
            const item = e.target.closest(".export-menu-item");
            if (!item) return;
            const menu = document.getElementById("exportMenu");
            if (!menu || !menu.classList.contains("open")) return;

            const type = item.dataset.export;
            this._handleExport(type);
            menu.classList.remove("open");
            document.getElementById("exportDropdown")?.classList.remove("open");
        });

        document
            .getElementById("btnCheck")
            ?.addEventListener("click", () => this._runCheck());
        document
            .getElementById("btnHighlightPath")
            ?.addEventListener("click", (e) => {
                e.stopPropagation();
                this._toggleHighlightMenu();
            });
        // Close highlight menu when clicking outside
        document.addEventListener("click", (e) => {
            const menu = document.getElementById("highlightMenu");
            const btn = document.getElementById("btnHighlightPath");
            if (
                menu &&
                menu.classList.contains("open") &&
                btn &&
                !btn.contains(e.target) &&
                !menu.contains(e.target)
            ) {
                menu.classList.remove("open");
                document
                    .getElementById("highlightDropdown")
                    ?.classList.remove("open");
            }
        });
        // Highlight menu item clicks
        document
            .querySelectorAll("#highlightMenu .export-menu-item")
            .forEach((item) => {
                item.addEventListener("click", () => {
                    const phase = item.dataset.phase;
                    if (phase === "all") {
                        this._showAllPhases();
                    } else {
                        this._highlightPhase(phase);
                    }
                    document
                        .getElementById("highlightMenu")
                        ?.classList.remove("open");
                    document
                        .getElementById("highlightDropdown")
                        ?.classList.remove("open");
                });
            });
        document
            .getElementById("btnClearPath")
            ?.addEventListener("click", () => this._clearHighlight());
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
        document
            .getElementById("modalCloseBtn")
            ?.addEventListener("click", () => this.closeSaveModal());
        document
            .getElementById("btnNewModel")
            ?.addEventListener("click", () => this._newModel());
        document
            .getElementById("btnClearValidation")
            ?.addEventListener("click", () => this._clearValidation());
        // Import JSON button opens modal
        document
            .getElementById("btnImportJson")
            ?.addEventListener("click", () => this.openImportModal());

        // File input change
        document
            .getElementById("importJsonFile")
            ?.addEventListener("change", (e) => {
                const name = e.target.files[0]?.name || "No file chosen";
                document.getElementById("importFileName").textContent = name;
            });

        // Import submit
        document
            .getElementById("btnImportSubmit")
            ?.addEventListener("click", () => this._handleImportSubmit());
        // Toolbar
        this._buildToolbar();

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
                if (action === "add-param-input") {
                    this._saveUndoState();
                    const port = node.addParamInput();
                    if (port) this.ports = this._collectPorts();
                }
                if (action === "add-param-output") {
                    this._saveUndoState();
                    const port = node.addParamOutput();
                    if (port) this.ports = this._collectPorts();
                }
                if (action === "remove-param-output") {
                    this._saveUndoState();
                    const port = node.removeParamOutput();
                    if (port) {
                        this.links = this.links.filter(
                            (l) => l.from !== port && l.to !== port,
                        );
                        this.ports = this._collectPorts();
                        node.updatePorts();
                    }
                }
                if (action === "remove-param-input") {
                    this._saveUndoState();
                    const port = node.removeParamInput();
                    if (port) {
                        this.links = this.links.filter(
                            (l) => l.from !== port && l.to !== port,
                        );
                        this.ports = this._collectPorts();
                        node.updatePorts();
                    }
                }
                if (action === "add-color-input") {
                    this._saveUndoState();
                    const port = node.addInput("color");
                    if (port) this.ports = this._collectPorts();
                }
                if (action === "remove-color-input") {
                    this._saveUndoState();
                    const port = node.removeInput(); // removes color port first (per removeInput logic)
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
                if (
                    this.selectedNodes.length === 1 &&
                    this.selectedNodes[0] === node
                ) {
                    this._showProperties(node);
                }
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
        this.resize();
        this._zoomFit();
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
        this._render();
        this._propagateShapes();
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
    //============ propagation =======
    _propagateShapes() {
        if (!this.shapePropagationEnabled) return;

        // Clear all port shapes
        for (const port of this.ports) {
            port.clearShape();
            if (port instanceof MultiPort) {
                port._incomingShapes = []; // Reset incoming shapes list
            }
        }

        // Start from InputData nodes
        const visited = new Set();
        const queue = [];
        for (const node of this.nodes) {
            if (node instanceof InputDataNode) {
                queue.push(node);
            }
        }

        while (queue.length > 0) {
            const node = queue.shift();
            if (visited.has(node.id)) continue;
            visited.add(node.id);

            const outputShapes = node.computeOutputShapes();
            for (let i = 0; i < node.outputs.length; i++) {
                if (i < outputShapes.length && outputShapes[i].shape) {
                    node.outputs[i].setShape(
                        outputShapes[i].shape,
                        outputShapes[i].dtype,
                        outputShapes[i].known,
                        outputShapes[i].symbolic,
                    );
                }
            }

            for (const outPort of node.outputs) {
                const links = this.links.filter((l) => l.from === outPort);
                for (const link of links) {
                    const targetPort = link.to;
                    const targetNode = targetPort.node;

                    if (outPort.shape && outPort.shape.shape) {
                        if (targetPort instanceof MultiPort) {
                            if (!targetPort._incomingShapes)
                                targetPort._incomingShapes = [];
                            targetPort._incomingShapes.push({
                                shape: outPort.shape.shape.map(
                                    (s) => new ShapeExpr(s),
                                ),
                                dtype: outPort.shape.dtype,
                                known: outPort.shape.known,
                                symbolic: outPort.shape.symbolic,
                            });
                            if (targetPort._incomingShapes.length === 1) {
                                targetPort.setShape(
                                    outPort.shape.shape.map(
                                        (s) => new ShapeExpr(s),
                                    ),
                                    outPort.shape.dtype,
                                    outPort.shape.known,
                                    outPort.shape.symbolic,
                                );
                            }
                        } else {
                            targetPort.setShape(
                                outPort.shape.shape.map(
                                    (s) => new ShapeExpr(s),
                                ),
                                outPort.shape.dtype,
                                outPort.shape.known,
                                outPort.shape.symbolic,
                            );
                        }
                    }

                    if (!visited.has(targetNode.id)) {
                        queue.push(targetNode);
                    }
                }
            }
        }

        if (this.selectedNodes.length === 1) {
            this._showProperties(this.selectedNodes[0]);
        }
        if (this.selectedPorts.length === 1) {
            this._showPortProperties();
        }
        for (const link of this.links) {
            link.computeWeightShape();
        }

        if (this.selectedNodes.length === 1) {
            this._showProperties(this.selectedNodes[0]);
        }
        if (this.selectedPorts.length === 1) {
            this._showPortProperties();
        }
        if (this.selectedLinks.length === 1) {
            this._showLinkProperties();
        }
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
        // Block canvas interactions when a modal is open
        if (
            document.getElementById("saveModal")?.style.display === "flex" ||
            document.getElementById("validationModal")?.style.display === "flex"
        ) {
            return;
        }
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
                if (idx >= 0) this.selectedNodes.splice(idx, 1);
                else this.selectedNodes.push(hit.node);
            } else {
                // If the clicked node is not already selected, select it exclusively
                if (!this.selectedNodes.includes(hit.node)) {
                    this.selectedNodes = [hit.node];
                }
                // otherwise keep the multi‑selection (drag will move all)
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
                this._showLinkProperties();
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
        const entry = this.nodeRegistry.find(
            (r) => r.type === this.currentTool,
        );
        if (entry) {
            this._addNode(this.currentTool, mx, my);
        }
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
                const hit = this._hitTest(e.offsetX, e.offsetY);
                if (hit && hit.port && hit.port !== this.linking.sourcePort) {
                    this._addLink(this.linking.sourcePort, hit.port);
                }
                this.linking.active = false;
                this.linking.sourcePort = null;
                this._render();
            } else {
                // User just clicked without dragging — select the port
                this.selectedPorts = [this.linking.sourcePort];
                this.selectedNodes = [];
                this.selectedLinks = [];
                this._showPortProperties();
                this._saveToSession();
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
        // Block all canvas keyboard shortcuts when a modal is open
        if (
            document.getElementById("saveModal")?.style.display === "flex" ||
            document.getElementById("validationModal")?.style.display ===
                "flex" ||
            document.getElementById("importModal")?.style.display === "flex"
        ) {
            return;
        }

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
        if ((e.ctrlKey || e.metaKey) && e.key === "0") {
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
        if ((e.ctrlKey || e.metaKey) && e.key === "c") {
            e.preventDefault();
            this._copySelected();
        }
        if ((e.ctrlKey || e.metaKey) && e.key === "v") {
            e.preventDefault();
            this._pasteClipboard();
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
        if (type === "input-data" || type === "output") return;
        const entry = this.nodeRegistry.find((r) => r.type === type);
        if (!entry) return;

        const w = this._toWorld(sx, sy);
        const id = type[0] + ++this.nodeCounter;
        const node = new entry.class(id, w.x, w.y);
        if (!node) return;

        this._saveUndoState();
        this.nodes.push(node);
        this.ports = this._collectPorts();
        this.selectedNodes = [node];
        this._showProperties(node);
        this._saveToSession();
        this._render();
        this._propagateShapes();
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
        this._propagateShapes();
        this._render();
    },

    _deleteLink(link) {
        this._saveUndoState();
        this.links = this.links.filter((l) => l !== link);
        this.selectedLinks = this.selectedLinks.filter((l) => l !== link);
        this._saveToSession();
        this._propagateShapes();
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
        this._propagateShapes();
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

        // Check for duplicate
        const exists = this.links.find(
            (l) => l.from === outPort && l.to === inPort,
        );
        if (exists) return;

        // Check connection limit on target port
        const currentConnections = this.links.filter(
            (l) => l.to === inPort,
        ).length;
        if (currentConnections >= inPort.connectionLimit) {
            // For single-connection ports, replace existing link
            if (inPort.connectionLimit === 1 && currentConnections === 1) {
                this.links = this.links.filter((l) => l.to !== inPort);
            } else {
                return; // MultiPort at capacity — shouldn't happen with Infinity
            }
        }

        this._saveUndoState();
        this.links.push(new Link(outPort, inPort));
        this._saveToSession();
        this._propagateShapes();
    },

    _collectPorts() {
        const all = [];
        for (const node of this.nodes) {
            all.push(
                ...node.inputs,
                ...node.outputs,
                ...node.paramInputs,
                ...node.paramOutputs,
            );
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

    //========= building toolbar ===========
    _buildToolbar() {
        const toolbar = document.getElementById("leftToolbar");
        if (!toolbar) return;

        const sections = {
            general: {
                title: "General",
                items: [
                    {
                        type: "select",
                        label: "Select",
                        active: true,
                        icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M3 3l7.07 16.97 2.51-7.39 7.39-2.51L3 3z"/></svg>`,
                    },
                    {
                        type: "pan",
                        label: "Pan",
                        icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="5 9 2 12 5 15"/><polyline points="9 5 12 2 15 5"/>
                        <polyline points="15 19 12 22 9 19"/><polyline points="19 9 22 12 19 15"/></svg>`,
                    },
                    {
                        type: "delete",
                        label: "Delete",
                        icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="3 6 5 6 21 6"/>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>`,
                    },
                ],
            },
            data: { title: "Data", items: [] },
            models: { title: "Models", items: [] },
            training: { title: "Training", items: [] },
        };

        // Group registered nodes by category
        for (const entry of this.nodeRegistry) {
            if (sections[entry.category]) {
                sections[entry.category].items.push(entry);
            }
        }

        // Build HTML
        let html = "";
        for (const [key, section] of Object.entries(sections)) {
            if (section.items.length === 0) continue;
            html += `<div class="toolbar-section">
            <div class="toolbar-section-title">${section.title}</div>`;
            for (const entry of section.items) {
                const activeClass = entry.active ? " active" : "";
                html += `
            <button class="tool-btn${activeClass}" data-tool="${entry.type}" title="${entry.label}">
                ${entry.icon || this._getDefaultIcon()}
                <span class="tool-label">${entry.label}</span>
            </button>`;
            }
            html += `</div>`;
        }

        toolbar.innerHTML = html;

        // Re-bind toolbar clicks
        toolbar.querySelectorAll(".tool-btn[data-tool]").forEach((btn) => {
            btn.addEventListener("click", () => this.setTool(btn.dataset.tool));
        });
    },

    _getDefaultIcon() {
        return `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="3" y="3" width="18" height="18" rx="2"/>
    </svg>`;
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
        this._propagateShapes();
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
        this._propagateShapes();
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
        this._propagateShapes();
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
        const addParamInput = menu.querySelector(
            '[data-action="add-param-input"]',
        );
        const addParamOutput = menu.querySelector(
            '[data-action="add-param-output"]',
        );
        const removeParamInput = menu.querySelector(
            '[data-action="remove-param-input"]',
        );
        const removeParamOutput = menu.querySelector(
            '[data-action="remove-param-output"]',
        );
        const deleteItem = menu.querySelector('[data-action="delete-node"]');

        // Visualization-specific items
        const addColorInput = menu.querySelector(
            '[data-action="add-color-input"]',
        );
        const removeColorInput = menu.querySelector(
            '[data-action="remove-color-input"]',
        );

        // Hide all optional items first
        if (addColorInput) addColorInput.style.display = "none";
        if (removeColorInput) removeColorInput.style.display = "none";

        if (node instanceof VisualizationNode) {
            // Show visualization-specific options
            addInput.style.display = node._canAddCoordInput() ? "flex" : "none";
            addOutput.style.display = "none";
            removeInput.style.display = node._canRemoveCoordInput()
                ? "flex"
                : "none";
            removeOutput.style.display = "none";
            addParamInput.style.display = "none";
            addParamOutput.style.display = "none";
            removeParamInput.style.display = "none";
            removeParamOutput.style.display = "none";
            deleteItem.style.display = "flex";

            if (addColorInput)
                addColorInput.style.display = node._canAddColorInput()
                    ? "flex"
                    : "none";
            if (removeColorInput)
                removeColorInput.style.display = node._canRemoveColorInput()
                    ? "flex"
                    : "none";
        } else {
            // Standard behavior for other nodes
            addInput.style.display = node.canAddInput() ? "flex" : "none";
            addOutput.style.display = node.canAddOutput() ? "flex" : "none";
            removeInput.style.display = node.canRemoveInput() ? "flex" : "none";
            removeOutput.style.display = node.canRemoveOutput()
                ? "flex"
                : "none";
            addParamInput.style.display = node.canAddParamInput()
                ? "flex"
                : "none";
            addParamOutput.style.display = node.canAddParamOutput()
                ? "flex"
                : "none";
            removeParamInput.style.display = node.canRemoveParamInput()
                ? "flex"
                : "none";
            removeParamOutput.style.display = node.canRemoveParamOutput()
                ? "flex"
                : "none";

            if (node instanceof InputDataNode || node instanceof OutputNode) {
                deleteItem.style.display = "none";
            } else {
                deleteItem.style.display = "flex";
            }
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
        this._propagateShapes();
        this._render();
    },

    _disconnectPort(port) {
        this._saveUndoState();
        // Remove all links connected to this port
        this.links = this.links.filter((l) => l.from !== port && l.to !== port);
        this._saveToSession();
        this._propagateShapes();
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

        // Port kind label
        let kindLabel = "Data Port";
        if (port instanceof MultiPort)
            kindLabel = `Multi Port (${connectedLinks.length} connections)`;
        if (port instanceof RolePort) kindLabel = `Role Port: ${port.role}`;
        if (port instanceof ParamPort) kindLabel = "Param Port";
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

        const shapeColor =
            port.hasShape() && port.shape.known
                ? "#ffffff"
                : "var(--text-secondary)";
        const shapeText = port.shapeDisplay();

        content.innerHTML = `
    <div class="prop-group">
        <label>Port</label>
        <p class="prop-hint">
            ${port.type === "input" ? "Input" : "Output"} #${port.index + 1} — ${port.node.type}
            <br><small>${kindLabel}</small>
        </p>
    </div>
    <div class="prop-group">
        <label>Shape</label>
        <p class="prop-hint" style="font-family: monospace; color: ${shapeColor}; font-size: 0.85rem;">
            ${shapeText}
        </p>
    </div>
    <div class="prop-group">
        <label>Active in phases</label>
        <div class="checkbox-group" id="prop-activation-phases">
            <label class="checkbox-label">
                <input type="checkbox" value="preprocessing"
                    ${port.activationPhases.includes("preprocessing") ? "checked" : ""}
                    onchange="SketchMod._updatePortPhase(this)">
                Preprocessing
            </label>
            <label class="checkbox-label">
                <input type="checkbox" value="training"
                    ${port.activationPhases.includes("training") ? "checked" : ""}
                    onchange="SketchMod._updatePortPhase(this)">
                Training
            </label>
            <label class="checkbox-label">
                <input type="checkbox" value="evaluation"
                    ${port.activationPhases.includes("evaluation") ? "checked" : ""}
                    onchange="SketchMod._updatePortPhase(this)">
                Evaluation
            </label>
        </div>
    </div>
    ${
        port.type === "input"
            ? `
    <div class="prop-group">
        <label>Bias</label>
        <input type="number" id="prop-port-bias" class="prop-input" 
               value="${port.bias || 0}" step="0.01"
               onchange="SketchMod._updatePortBias(this)">
    </div>
    `
            : ""
    }
    ${
        port.type === "output" && !port.role
            ? `
    <div class="prop-group">
        <label>Output Type</label>
        <select id="prop-port-subtype" class="prop-select" >
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
        // Bind the select change event
        const select = document.getElementById("prop-port-subtype");
        if (select) {
            select.addEventListener("change", () => {
                this._updatePortSubType(select);
            });
        }
    },

    _updatePortPhase(checkbox) {
        if (!this._currentPortForProps) return;
        this._saveUndoState();
        const phase = checkbox.value;
        const port = this._currentPortForProps;
        if (checkbox.checked) {
            if (!port.activationPhases.includes(phase))
                port.activationPhases.push(phase);
        } else {
            port.activationPhases = port.activationPhases.filter(
                (p) => p !== phase,
            );
        }
        this._saveToSession();
        this._render();
    },
    _updatePortBias(input) {
        if (!this._currentPortForProps) return;
        this._saveUndoState();
        this._currentPortForProps.bias = parseFloat(input.value) || 0;
        this._saveToSession();
    },
    _updatePortSubType(select) {
        if (!this._currentPortForProps) return;
        this._saveUndoState();
        this._currentPortForProps.subType = select.value || null;
        this._saveToSession();
        this._render();
    },
    _showLinkProperties() {
        const panel = document.getElementById("propertiesPanel");
        const content = document.getElementById("propertiesContent");
        panel.style.display = "block";

        if (this.selectedLinks.length === 0) {
            panel.style.display = "none";
            return;
        }

        if (this.selectedLinks.length > 1) {
            content.innerHTML = `<p class='prop-hint'>${this.selectedLinks.length} links selected</p>`;
            return;
        }

        const link = this.selectedLinks[0];
        const ws = link.weightShape;

        // Build shape info
        let shapeHTML = "";
        if (link.from.shape && link.from.shape.shape) {
            shapeHTML += `<div class="prop-group">
            <label>Input Shape</label>
            <p class="prop-hint" style="font-family: monospace; font-size: 0.8rem;">
                (${link.from.shape.shape.join(", ")})
            </p>
        </div>`;
        }
        if (link.to.shape && link.to.shape.shape) {
            shapeHTML += `<div class="prop-group">
            <label>Output Shape</label>
            <p class="prop-hint" style="font-family: monospace; font-size: 0.8rem;">
                (${link.to.shape.shape.join(", ")})
            </p>
        </div>`;
        }

        // Build weight section
        let weightHTML = "";
        if (link.hasWeight && ws && ws.shape) {
            const isScalarLike = ws.shape[0] === 1 && ws.shape[1] === 1;
            weightHTML = `
            <div class="prop-group">
                <label>Weight Shape</label>
                <p class="prop-hint" style="font-family: monospace; color: var(--accent); font-size: 0.85rem;">
                    ${link.weightShapeDisplay()}
                </p>
            </div>
            ${
                isScalarLike
                    ? `
            <div class="prop-group">
                <label>Weight Value</label>
                <input type="number" id="prop-link-weight" class="prop-input" 
                       value="${link.weight}" step="0.01"
                       onchange="SketchMod._updateLinkWeight(this)">
            </div>
            `
                    : `
            <div class="prop-group">
                <label>Initialization</label>
                <input type="number" id="prop-link-weight" class="prop-input" 
                       value="${link.weight}" step="0.01"
                       onchange="SketchMod._updateLinkWeight(this)">
                <p class="prop-hint">Scale for random initialization</p>
            </div>
            `
            }
        `;
        }

        content.innerHTML = `
        <div class="prop-group">
            <label>Link</label>
            <p class="prop-hint">${link.from.node.type} → ${link.to.node.type}</p>
        </div>
        ${weightHTML}
        <div class="prop-group">
            <button class="prop-btn prop-btn-danger" onclick="SketchMod._deleteLink(SketchMod.selectedLinks[0])">
                Delete Link
            </button>
        </div>
    `;
    },

    _updateLinkWeight(input) {
        if (this.selectedLinks.length !== 1) return;
        const link = this.selectedLinks[0];
        this._saveUndoState();
        link.weight = parseFloat(input.value) || 0;
        this._saveToSession();
    },
    _bindPropertiesEvents(node) {
        const actSelect = document.getElementById("prop-activation");
        if (actSelect) {
            actSelect.addEventListener("change", () => {
                this._saveUndoState();
                node.activation = actSelect.value;
                this._saveToSession();
                this._propagateShapes();
                this._render();
            });
        }
        const sizeInput = document.getElementById("prop-size");
        if (sizeInput) {
            sizeInput.addEventListener("change", () => {
                this._saveUndoState();
                node.numNeurons = parseInt(sizeInput.value) || 64;
                this._saveToSession();
                this._propagateShapes();
                this._render();
            });
        }
        const filtersInput = document.getElementById("prop-filters");
        if (filtersInput) {
            filtersInput.addEventListener("change", () => {
                this._saveUndoState();
                node.filters = parseInt(filtersInput.value) || 32;
                this._saveToSession();
                this._propagateShapes();
                this._render();
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

        if (
            this.selectedNodes.length === 1 &&
            this.selectedNodes[0] instanceof InputDataNode
        ) {
            const node = this.selectedNodes[0];
            node.datasetId = datasetId;
            node.datasetName = datasetName;

            // 1. Fetch dataset shape
            fetch(`/data/api/${datasetId}/shape/`)
                .then((res) => res.json())
                .then((data) => {
                    const shape = data.shape || "";
                    node.dataShape = shape;
                    const shapeInput =
                        document.getElementById("prop-manual-shape");
                    if (shapeInput) shapeInput.value = shape;
                    this._propagateShapes();
                    this._saveToSession();
                })
                .catch(() => {});

            // 2. Fetch dataset file info (name + format)
            fetch(`/data/api/${datasetId}/info/`)
                .then((res) => res.json())
                .then((data) => {
                    node.datasetFile = data.filename || "";
                    node.datasetFormat = data.format || "";
                    this._saveToSession();
                })
                .catch(() => {});
        }
    },

    // ========== SESSION ==========
    _saveToSession() {
        const data = {
            nodes: this.nodes.map((n) => n.toJSON()),
            links: this.links.map((l) => l.toJSON()),
            ports: this.ports.map((p) => p.toJSON()),
            nodeCounter: this.nodeCounter,
            modelId: this._currentModelId,
            modelName: this._currentModelName,
        };
        sessionStorage.setItem("sketchmod-graph", JSON.stringify(data));
        sessionStorage.setItem(
            "sketchmod-active-model-id",
            this._currentModelId || "",
        );
    },

    _loadFromSession() {
        const raw = sessionStorage.getItem("sketchmod-graph");
        if (!raw) return;
        try {
            const data = JSON.parse(raw);
            this.nodeCounter = data.nodeCounter || 0;
            this._currentModelId = data.modelId || null;
            this._currentModelName = data.modelName || null;
            this.nodes = [];
            this.links = [];

            for (const n of data.nodes) {
                const entry = this.nodeRegistry.find((r) => r.type === n.type);
                let node;
                if (entry) {
                    node = new entry.class(n.id, n.x, n.y);
                } else if (n.type === "input-data") {
                    node = new InputDataNode(n.id, n.x, n.y);
                } else if (n.type === "output") {
                    node = new OutputNode(n.id, n.x, n.y);
                }
                if (node) {
                    node.fromJSON(n);
                    this.nodes.push(node);
                }
            }
            this.ports = this._collectPorts();

            // Restore port shapes
            for (const p of data.ports || []) {
                const port = this.ports.find((pp) => pp.id === p.id);
                if (port && p.shape) {
                    port.setShape(
                        p.shape.shape,
                        p.shape.dtype,
                        p.shape.known,
                        p.shape.symbolic,
                    );
                    if (p.bias !== undefined) port.bias = p.bias;
                }
            }

            // Restore link weight shapes
            for (const l of data.links) {
                const from = this.ports.find((p) => p.id === l.from);
                const to = this.ports.find((p) => p.id === l.to);
                if (from && to) {
                    const link = new Link(from, to, l.weight);
                    if (l.weightShape) link.weightShape = l.weightShape;
                    if (l.hasWeight !== undefined) link.hasWeight = l.hasWeight;
                    this.links.push(link);
                }
            }
        } catch (e) {
            console.warn("Session restore failed:", e);
        }
        this._updateModelInfo();
        this._propagateShapes();
    },

    // ========== SERVER ==========
    _getGraphData() {
        return {
            nodes: this.nodes.map((n) => n.toJSON()),
            links: this.links.map((l) => l.toJSON()),
            ports: this.ports.map((p) => p.toJSON()),
            nodeCounter: this.nodeCounter,
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
            ports: this.ports.map((p) => p.toJSON()),
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
        this._propagateShapes();
        this._render();
        this._clearHighlight();
        this._clearValidation();
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
        this._propagateShapes();
        this._render();
        this._clearHighlight();
        this._clearValidation();
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
            const entry = this.nodeRegistry.find((r) => r.type === n.type);
            let node;
            if (entry) {
                node = new entry.class(n.id, n.x, n.y);
            } else if (n.type === "input-data") {
                node = new InputDataNode(n.id, n.x, n.y);
            } else if (n.type === "output") {
                node = new OutputNode(n.id, n.x, n.y);
            }
            if (node) {
                node.inputs = [];
                node.outputs = [];
                node.fromJSON(n);
                this.nodes.push(node);
            }
        }
        this.ports = this._collectPorts();

        // Restore port shapes
        if (state.ports) {
            for (const saved of state.ports) {
                const port = this.ports.find((p) => p.id === saved.id);
                if (!port) continue;
                if (saved.shape)
                    port.setShape(
                        saved.shape.shape,
                        saved.shape.dtype,
                        saved.shape.known,
                        saved.shape.symbolic,
                    );
                if (saved.bias !== undefined) port.bias = saved.bias;
                if (saved.activationPhases)
                    port.activationPhases = saved.activationPhases.slice();
                if (saved.activationMode) {
                    // backward compatibility
                    port.activationPhases = [saved.activationMode]; // convert old to new
                }
            }
        }

        // After ports are built in _loadFromSession and _restoreState:
        for (const l of state.links) {
            const from = this.ports.find((p) => p.id === l.from);
            const to = this.ports.find((p) => p.id === l.to);
            if (from && to) {
                const link = new Link(from, to, l.weight);
                if (l.weightShape) link.weightShape = l.weightShape;
                if (l.hasWeight !== undefined) link.hasWeight = l.hasWeight;
                this.links.push(link);
            }
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

        // Temp link line
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

        // Selection box (in screen space)
        if (this.isSelecting && this.selectionBox) {
            ctx.save();
            ctx.globalAlpha = 1;
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
            ctx.restore();
        }
    },

    _fetchDatasetShape(node) {
        if (!node.datasetId) return;
        const url = `/data/api/${node.datasetId}/columns/`;
        fetch(url)
            .then((res) => res.json())
            .then((data) => {
                // If API returns shape info, use it
                if (data.shape) {
                    const parts = data.shape
                        .replace(/[()]/g, "")
                        .split(",")
                        .map((s) => parseInt(s.trim()))
                        .filter((n) => !isNaN(n));
                    if (parts.length > 0) {
                        node.dataShape = data.shape;
                        this._propagateShapes();
                        this._render();
                    }
                }
            })
            .catch(() => {});
    },
    //=========== toggle and manual shape for dataset ==============
    _updateManualShape(input) {
        if (this.selectedNodes.length !== 1) return;
        const node = this.selectedNodes[0];
        if (!(node instanceof InputDataNode)) return;

        this._saveUndoState();
        let value = input.value.trim();
        // Auto-clean whitespace
        value = value
            .replace(/\s+/g, " ")
            .replace(/\s*,\s*/g, ", ")
            .replace(/\s*\)/g, ")")
            .replace(/\(\s*/g, "(");
        input.value = value;
        node.dataShape = value || null;
        this._saveToSession();
        this._propagateShapes();
        this._render();
    },

    //=========== column and row parsing and fetching methods ==============
    _updateColumnInput(input) {
        if (this.selectedNodes.length !== 1) return;
        const node = this.selectedNodes[0];
        if (!(node instanceof ColumnSelectNode)) return;

        this._saveUndoState();
        let value = input.value.trim();
        // Auto-clean whitespace
        value = value.replace(/\s+/g, "");
        input.value = value;

        node.columnInput = value;
        node.selectedColumns = this._parseColumnInput(value, node.columnCount);
        this._updateColumnPreview(node);
        this._saveToSession();
        this._propagateShapes();
        this._render();
    },

    _parseColumnInput(input, maxColumns) {
        if (!input) return [];
        const indices = new Set();
        const parts = input.split(",");
        const max = maxColumns > 0 ? maxColumns - 1 : null; // max valid index

        for (const part of parts) {
            const trimmed = part.trim();
            if (!trimmed) continue;

            if (trimmed.includes(":")) {
                const [startStr, endStr] = trimmed.split(":");
                let start = parseInt(startStr) || 0;
                let end = parseInt(endStr);
                if (isNaN(end)) end = max !== null ? max : undefined;

                // Convert negative indices to positive
                if (start < 0 && max !== null) start = max + 1 + start;
                if (end < 0 && max !== null) end = max + 1 + end;
                if (max !== null) {
                    start = Math.max(0, start);
                    end = Math.min(max, end);
                }
                for (let i = start; i <= end; i++) {
                    if (max === null || i <= max) indices.add(i);
                }
            } else {
                let idx = parseInt(trimmed);
                if (isNaN(idx)) continue;
                if (idx < 0 && max !== null) idx = max + 1 + idx;
                if (idx >= 0 && (max === null || idx <= max)) {
                    indices.add(idx);
                }
            }
        }
        return [...indices].sort((a, b) => a - b);
    },

    _updateColumnPreview(node) {
        const preview = document.getElementById("columnPreview");
        if (preview) {
            if (node.selectedColumns.length > 0) {
                preview.textContent =
                    node.selectedColumns.join(", ") +
                    ` (${node.selectedColumns.length} columns)`;
            } else {
                preview.textContent = "None selected";
            }
        }
    },

    _fetchColumnsForNode(node) {
        if (!node.datasetId) return;
        const url = `/data/api/${node.datasetId}/columns/`;
        fetch(url)
            .then((res) => res.json())
            .then((data) => {
                if (data.columns && data.columns.length > 0) {
                    node.availableColumns = data.columns;
                    node.columnCount = data.count;
                    if (node.selectedColumns.length === 0 && node.columnInput) {
                        node.selectedColumns = this._parseColumnInput(
                            node.columnInput,
                            data.count,
                        );
                    }
                    this._saveToSession();
                    if (this.selectedNodes.includes(node)) {
                        this._showProperties(node);
                    }
                }
            })
            .catch(() => {});
    },
    _updateRowMethod(select) {
        if (this.selectedNodes.length !== 1) return;
        const node = this.selectedNodes[0];
        if (!(node instanceof RowSelectNode)) return;
        this._saveUndoState();
        node.method = select.value;
        node.value = "";
        node.rowCount = 0;
        this._showProperties(node);
        this._saveToSession();
        this._propagateShapes();
        this._render();
    },

    _updateRowValue(input) {
        if (this.selectedNodes.length !== 1) return;
        const node = this.selectedNodes[0];
        if (!(node instanceof RowSelectNode)) return;
        this._saveUndoState();
        node.value = input.value.trim().replace(/\s+/g, "");
        input.value = node.value;
        node.rowCount = node._computeRowCount();
        this._showProperties(node);
        this._saveToSession();
        this._propagateShapes();
        this._render();
    },

    _updateRowSeed(input) {
        if (this.selectedNodes.length !== 1) return;
        const node = this.selectedNodes[0];
        if (!(node instanceof RowSelectNode)) return;
        this._saveUndoState();
        node.randomSeed = parseInt(input.value) || 42;
        this._saveToSession();
    },
    _updateDimSelect(input) {
        if (this.selectedNodes.length !== 1) return;
        const node = this.selectedNodes[0];
        if (!(node instanceof DimSelectNode)) return;

        this._saveUndoState();
        const dim = parseInt(input.dataset.dim);
        let value = input.value.replace(/\s+/g, "");
        input.value = value;
        node.dimSelections[dim] = value;
        this._showProperties(node);
        this._saveToSession();
        this._propagateShapes();
        this._render();
    },
    _updateOptimizerProp(prop, value) {
        if (this.selectedNodes.length !== 1) return;
        const node = this.selectedNodes[0];
        if (!(node instanceof OptimizerNode)) return;

        this._saveUndoState();

        // Handle numeric values
        const numericProps = [
            "learningRate",
            "adamBeta1",
            "adamBeta2",
            "adamEpsilon",
            "sgdMomentum",
            "weightDecay",
            "epochs",
            "batchSize",
            "gradientClip",
            "earlyStoppingPatience",
        ];
        const boolProps = ["shuffle", "nesterov", "earlyStopping"];

        if (numericProps.includes(prop)) {
            node[prop] =
                value === "" || value === null ? null : parseFloat(value);
            if (isNaN(node[prop])) node[prop] = null;
        } else if (boolProps.includes(prop)) {
            node[prop] = value === true || value === "true";
        } else {
            node[prop] = value;
        }

        if (prop === "earlyStopping" || prop === "optimizerType") {
            this._showProperties(node);
        }

        this._saveToSession();
        this._render();
    },
    _updateOneHotClasses(input) {
        if (this.selectedNodes.length !== 1) return;
        const node = this.selectedNodes[0];
        if (!(node instanceof OneHotEncodeNode)) return;

        this._saveUndoState();
        node.numClasses = parseInt(input.value) || 10;
        this._saveToSession();
        this._propagateShapes();
        this._render();
    },
    _updateVizProp(prop, value) {
        if (this.selectedNodes.length !== 1) return;
        const node = this.selectedNodes[0];
        if (!(node instanceof VisualizationNode)) return;

        this._saveUndoState();
        node[prop] = value;

        // If switching modes, refresh properties
        if (prop === "colorMode") {
            // Auto-add color input when switching to discrete/continuous
            if (
                (value === "discrete" || value === "continuous") &&
                !node._hasColorInput
            ) {
                const port = node._addColorInput();
                if (port) this.ports = this._collectPorts();
            }
            // Auto-remove color input when switching to none
            if (value === "none" && node._hasColorInput) {
                const port = node._removeColorInput();
                if (port) this.ports = this._collectPorts();
            }
            this._showProperties(node);
        }

        this._saveToSession();
        this._render();
    },

    _updateVizPaletteColor(index, value) {
        if (this.selectedNodes.length !== 1) return;
        const node = this.selectedNodes[0];
        if (!(node instanceof VisualizationNode)) return;

        this._saveUndoState();
        node.colorPalette[index] = value;
        this._saveToSession();
    },

    _addVizPaletteColor() {
        if (this.selectedNodes.length !== 1) return;
        const node = this.selectedNodes[0];
        if (!(node instanceof VisualizationNode)) return;

        this._saveUndoState();
        node.colorPalette.push("#6c5ce7"); // default new color
        this._showProperties(node); // refresh to show new row
        this._saveToSession();
    },

    _updatePrintLabel(input) {
        if (this.selectedNodes.length !== 1) return;
        const node = this.selectedNodes[0];
        if (!(node instanceof PrintNode)) return;
        this._saveUndoState();
        node.label = input.value;
        this._saveToSession();
        this._render();
    },

    _updateDeOneHotClasses(input) {
        if (this.selectedNodes.length !== 1) return;
        const node = this.selectedNodes[0];
        if (!(node instanceof DeOneHotNode)) return;
        this._saveUndoState();
        node.numClasses = parseInt(input.value) || 10;
        this._saveToSession();
        this._propagateShapes();
        this._render();
    },
    _updateAccuracyConfusion(checkbox) {
        if (this.selectedNodes.length !== 1) return;
        const node = this.selectedNodes[0];
        if (!(node instanceof AccuracyNode)) return;
        this._saveUndoState();
        node.showConfusion = checkbox.checked;
        this._saveToSession();
        this._render();
    },

    _removeVizPaletteColor(index) {
        if (this.selectedNodes.length !== 1) return;
        const node = this.selectedNodes[0];
        if (!(node instanceof VisualizationNode)) return;
        if (node.colorPalette.length <= 2) return;

        this._saveUndoState();
        node.colorPalette.splice(index, 1);
        this._showProperties(node); // refresh to re-render indices
        this._saveToSession();
    },
    _addDimRow() {
        if (this.selectedNodes.length !== 1) return;
        const node = this.selectedNodes[0];
        if (!(node instanceof DimSelectNode)) return;

        this._saveUndoState();
        node.dimSelections.push("");
        this._showProperties(node);
        this._saveToSession();
        this._render();
    },

    _removeDimRow(button) {
        if (this.selectedNodes.length !== 1) return;
        const node = this.selectedNodes[0];
        if (!(node instanceof DimSelectNode)) return;
        if (node.dimSelections.length <= 1) return;

        this._saveUndoState();
        const dim = parseInt(button.dataset.dim);
        node.dimSelections.splice(dim, 1);
        this._showProperties(node);
        this._saveToSession();
        this._render();
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

    _updateDropout(slider) {
        if (this.selectedNodes.length !== 1) return;
        const node = this.selectedNodes[0];
        if (!(node instanceof DropoutNode)) return;
        this._saveUndoState();
        node.rate = parseFloat(slider.value);
        this._showProperties(node);
        this._saveToSession();
        this._propagateShapes();
        this._render();
    },

    _updateConcatAxis(input) {
        if (this.selectedNodes.length !== 1) return;
        const node = this.selectedNodes[0];
        if (!(node instanceof ConcatenateNode)) return;
        this._saveUndoState();
        const val = parseInt(input.value);
        node.axis = isNaN(val) ? -1 : val;
        this._saveToSession();
        this._propagateShapes();
        this._render();
    },
    // ========== SAVE ==========
    _handleSave(event) {
        event.preventDefault();

        const name = document.getElementById("saveName")?.value.trim();
        if (!name) return;

        const description =
            document.getElementById("saveDescription")?.value.trim() || "";
        const viewAccess =
            document.querySelector('input[name="view_access"]:checked')
                ?.value || "public";
        const forkAccess =
            document.querySelector('input[name="fork_access"]:checked')
                ?.value || "private";
        const coverFile = document.getElementById("saveCoverInput")?.files[0];
        const graphData = JSON.stringify(SketchMod._getGraphData());
        const formData = new FormData();
        formData.append("name", name);
        formData.append("description", description);
        formData.append("view_access", viewAccess);
        formData.append("fork_access", forkAccess);
        formData.append("graph_data", graphData);
        if (coverFile) formData.append("cover_image", coverFile);

        const url = SketchMod._currentModelId
            ? `/models/${SketchMod._currentModelId}/update/`
            : "/models/save/";

        fetch(url, {
            method: "POST",
            body: formData,
            headers: {
                "X-CSRFToken": SketchMod._getCsrfToken(),
            },
        })
            .then((res) => res.json())
            .then((data) => {
                if (data.success) {
                    SketchMod._currentModelId = data.model_id;
                    SketchMod._currentModelName = data.name;
                    SketchMod._saveToSession();
                    SketchMod.closeSaveModal();
                    SketchMod._buildToolbar();
                    SketchMod._updateModelInfo();
                    SketchMod._showToast("Model saved!");
                } else {
                    alert(data.error || "Save failed");
                }
            })
            .catch((err) => {
                console.error("Save failed:", err);
                alert("Save failed. Check console.");
            });
    },
    _getCsrfToken() {
        return (
            document.querySelector("[name=csrfmiddlewaretoken]")?.value || ""
        );
    },

    openSaveModal() {
        if (this._currentModelId) {
            this._handleQuickSave();
            return;
        }
        document.getElementById("saveModal").style.display = "flex";
        document.getElementById("saveName").value =
            this._currentModelName || "";
        document.getElementById("saveDescription").value = "";
        const fileNameDisplay = document.getElementById("saveCoverFileName");
        if (fileNameDisplay) {
            fileNameDisplay.textContent = "No file chosen";
        }
        // Auto-focus the name field
        setTimeout(() => {
            document.getElementById("saveName")?.focus();
        }, 100);
    },

    closeSaveModal() {
        document.getElementById("saveModal").style.display = "none";
    },
    _handleQuickSave() {
        const graphData = JSON.stringify(SketchMod._getGraphData());

        const formData = new FormData();
        formData.append("graph_data", graphData);

        fetch(`/models/${SketchMod._currentModelId}/update/`, {
            method: "POST",
            body: formData,
            headers: {
                "X-CSRFToken": SketchMod._getCsrfToken(),
            },
        })
            .then((res) => res.json())
            .then((data) => {
                if (data.success) {
                    SketchMod._buildToolbar();
                    SketchMod._updateModelInfo();
                    SketchMod._showToast("Model updated!");
                } else {
                    alert(data.error || "Update failed");
                }
            })
            .catch((err) => {
                console.error("Update failed:", err);
            });
    },

    _showToast(message) {
        let toast = document.createElement("div");
        toast.className = "toast";
        toast.textContent = message;
        toast.style.cssText = `
        position: fixed; bottom: 30px; left: 50%; transform: translateX(-50%);
        background: var(--accent); color: #fff; padding: 10px 24px;
        border-radius: 20px; font-size: 0.9rem; font-weight: 600;
        z-index: 9999; opacity: 0; transition: opacity 0.3s;
        pointer-events: none;
    `;
        document.body.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = "1";
        }, 50);
        setTimeout(() => {
            toast.style.opacity = "0";
            setTimeout(() => toast.remove(), 300);
        }, 2000);
    },
    _loadModelFromServer(modelId) {
        fetch(`/models/${modelId}/data/`)
            .then((res) => res.json())
            .then((data) => {
                // Clear current graph
                this.nodes = [];
                this.links = [];
                this.ports = [];

                // Load nodes
                if (data.nodes) {
                    this.nodeCounter = data.nodeCounter || 0;
                    for (const n of data.nodes) {
                        const entry = this.nodeRegistry.find(
                            (r) => r.type === n.type,
                        );
                        let node;
                        if (entry) {
                            node = new entry.class(n.id, n.x, n.y);
                        } else if (n.type === "input-data") {
                            node = new InputDataNode(n.id, n.x, n.y);
                        } else if (n.type === "output") {
                            node = new OutputNode(n.id, n.x, n.y);
                        }
                        if (node) {
                            node.fromJSON(n);
                            this.nodes.push(node);
                        }
                    }
                    this.ports = this._collectPorts();
                }

                // Load links
                if (data.links) {
                    for (const l of data.links) {
                        const from = this.ports.find((p) => p.id === l.from);
                        const to = this.ports.find((p) => p.id === l.to);
                        if (from && to) {
                            const link = new Link(from, to, l.weight);
                            if (l.weightShape) link.weightShape = l.weightShape;
                            if (l.hasWeight !== undefined)
                                link.hasWeight = l.hasWeight;
                            this.links.push(link);
                        }
                    }
                }

                // Restore port shapes
                if (data.ports) {
                    for (const p of data.ports) {
                        const port = this.ports.find((pp) => pp.id === p.id);
                        if (port && p.shape) {
                            port.setShape(
                                p.shape.shape,
                                p.shape.dtype,
                                p.shape.known,
                                p.shape.symbolic,
                            );
                            if (p.bias !== undefined) port.bias = p.bias;
                        }
                    }
                }

                // Set model ownership
                this._currentModelId = modelId;
                this._currentModelName = data.name || "";

                this._saveToSession();
                this._buildToolbar();
                this._updateModelInfo();
                this._propagateShapes();
                this._render();
            })
            .catch((err) => {
                console.error("Failed to load model:", err);
                this._loadFromSession();
            });
    },
    _newModel() {
        if (confirm("Start a new model? Unsaved changes will be lost.")) {
            // Clear everything
            this.nodes = [];
            this.links = [];
            this.ports = [];
            this.nodeCounter = 0;
            this._currentModelId = null;
            this._currentModelName = null;

            // Clear session storage
            sessionStorage.removeItem("sketchmod-graph");
            sessionStorage.removeItem("sketchmod-active-model-id");

            // Create fresh default nodes
            this._createDefaultNodes();

            // Rebuild toolbar to show updated info
            this._buildToolbar();
            this._updateModelInfo();

            // Reset view
            this.offsetX = 0;
            this.offsetY = 0;
            this.scale = 1;
            this._render();

            // Remove the 'load' parameter from the URL so a refresh doesn't reload the old model
            if (window.history && window.history.replaceState) {
                const newUrl = window.location.pathname;
                window.history.replaceState({}, "", newUrl);
            }
        }
    },
    _updateModelInfo() {
        const infoDiv = document.getElementById("sidebarModelInfo");
        const nameEl = document.getElementById("sidebarModelName");
        const idEl = document.getElementById("sidebarModelId");

        if (this._currentModelName || this._currentModelId) {
            infoDiv.style.display = "block";
            nameEl.textContent = this._currentModelName || "Untitled";
            idEl.textContent = this._currentModelId || "";
        } else {
            infoDiv.style.display = "none";
        }
    },

    // ========== EXPORT METHODS ==========
    _toggleExportMenu() {
        const menu = document.getElementById("exportMenu");
        const dropdown = document.getElementById("exportDropdown");
        if (!menu || !dropdown) return;

        const isOpen = menu.classList.contains("open");
        if (isOpen) {
            menu.classList.remove("open");
            dropdown.classList.remove("open");
        } else {
            menu.classList.add("open");
            dropdown.classList.add("open");
        }
    },

    _handleExport(type) {
        // Only validate for Python exports
        const needsValidation = [
            "pytorch-py",
            "pytorch-zip",
            "python-clipboard",
        ].includes(type);

        if (needsValidation) {
            const graphData = JSON.stringify(this._getGraphData());

            fetch("/sketchmod/api/validate/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": this._getCsrfToken(),
                },
                body: JSON.stringify({ graph: graphData }),
            })
                .then((res) => res.json())
                .then((data) => {
                    if (data.success) {
                        this._applyValidationResults(data);
                        this._render();

                        if (!data.isValid) {
                            this._showValidationModal({
                                errors: data.errors,
                                warnings: data.warnings,
                                isValid: false,
                            });
                            this._showToast("Fix errors before exporting");
                            return;
                        }

                        this._doExport(type, graphData);
                    }
                });
            return;
        }

        // Image and JSON exports — no validation needed
        this._doExport(type);
    },
    _doExport(type, graphData) {
        // Image exports
        if (type === "image-png" || type === "image-jpeg") {
            this._exportImage(type.replace("image-", ""));
            return;
        }

        // JSON clipboard
        if (type === "json-clipboard") {
            const data = JSON.stringify(this._getGraphData(), null, 2);
            navigator.clipboard.writeText(data).then(() => {
                this._showToast("JSON copied!");
            });
            return;
        }

        // Zip export — generate .py + bundle dataset
        if (type === "pytorch-zip") {
            this._exportPyTorchZip();
            return;
        }

        // All other Python exports go through API
        fetch("/sketchmod/api/export/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": this._getCsrfToken(),
            },
            body: JSON.stringify({ graph: graphData, format: type }),
        })
            .then((res) => res.json())
            .then((data) => {
                if (data.success) {
                    if (type === "python-clipboard") {
                        navigator.clipboard.writeText(data.code).then(() => {
                            this._showToast("Python code copied!");
                        });
                    } else {
                        const blob = new Blob([data.code], {
                            type: "text/plain",
                        });
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement("a");
                        a.href = url;
                        a.download = data.filename;
                        a.click();
                        URL.revokeObjectURL(url);
                        this._showToast(`Downloaded ${data.filename}`);
                    }
                } else {
                    console.error("Export API error:", data.error);
                    this._showToast(
                        "Export failed: " + (data.error || "Unknown error"),
                    );
                }
            })
            .catch((err) => {
                console.error("Export failed:", err);
                this._showToast("Export failed. Check console.");
            });
    },
    _exportPyTorchZip() {
        const graphData = JSON.stringify(this._getGraphData());

        // Get the .py code from API
        fetch("/sketchmod/api/export/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": this._getCsrfToken(),
            },
            body: JSON.stringify({ graph: graphData, format: "pytorch-zip" }),
        })
            .then((res) => res.blob()) // Expect a zip blob
            .then((blob) => {
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = "model.zip";
                a.click();
                URL.revokeObjectURL(url);
                this._showToast("Downloaded model.zip");
            })
            .catch((err) => {
                console.error("Zip export failed:", err);
                this._showToast("Zip export failed. Check console.");
            });
    },

    _exportImage(format) {
        const prevScale = this.scale;
        const prevX = this.offsetX;
        const prevY = this.offsetY;

        this._zoomFit();
        this._render();

        setTimeout(() => {
            // Create an offscreen canvas with background
            const exportCanvas = document.createElement("canvas");
            exportCanvas.width = this.canvas.width;
            exportCanvas.height = this.canvas.height;
            const exportCtx = exportCanvas.getContext("2d");

            // Get the canvas wrapper's computed background styles
            const wrapper = document.getElementById("canvasWrapper");
            const wrapperStyle = getComputedStyle(wrapper);
            const bgColor = wrapperStyle.backgroundColor;

            // Parse CSS custom properties for grid colors
            const canvasBg = getComputedStyle(document.documentElement)
                .getPropertyValue("--canvas-bg")
                .trim();
            const gridSmall = getComputedStyle(document.documentElement)
                .getPropertyValue("--canvas-grid-small")
                .trim();
            const gridLarge = getComputedStyle(document.documentElement)
                .getPropertyValue("--canvas-grid-large")
                .trim();

            // Fill background color
            exportCtx.fillStyle = canvasBg || bgColor || "#0f1119";
            exportCtx.fillRect(0, 0, exportCanvas.width, exportCanvas.height);

            // Draw grid
            const gridSmallColor = gridSmall || "rgba(255,255,255,0.03)";
            const gridLargeColor = gridLarge || "rgba(255,255,255,0.06)";

            // Small grid (20px)
            exportCtx.strokeStyle = gridSmallColor;
            exportCtx.lineWidth = 0.5;
            for (let x = 0; x <= exportCanvas.width; x += 20) {
                exportCtx.beginPath();
                exportCtx.moveTo(x, 0);
                exportCtx.lineTo(x, exportCanvas.height);
                exportCtx.stroke();
            }
            for (let y = 0; y <= exportCanvas.height; y += 20) {
                exportCtx.beginPath();
                exportCtx.moveTo(0, y);
                exportCtx.lineTo(exportCanvas.width, y);
                exportCtx.stroke();
            }

            // Large grid (100px)
            exportCtx.strokeStyle = gridLargeColor;
            exportCtx.lineWidth = 1;
            for (let x = 0; x <= exportCanvas.width; x += 100) {
                exportCtx.beginPath();
                exportCtx.moveTo(x, 0);
                exportCtx.lineTo(x, exportCanvas.height);
                exportCtx.stroke();
            }
            for (let y = 0; y <= exportCanvas.height; y += 100) {
                exportCtx.beginPath();
                exportCtx.moveTo(0, y);
                exportCtx.lineTo(exportCanvas.width, y);
                exportCtx.stroke();
            }

            // Copy the main canvas content on top
            exportCtx.drawImage(this.canvas, 0, 0);

            // Export
            const dataUrl = exportCanvas.toDataURL(`image/${format}`, 0.95);
            const a = document.createElement("a");
            a.href = dataUrl;
            a.download = `model.${format}`;
            a.click();

            // Restore view
            this.scale = prevScale;
            this.offsetX = prevX;
            this.offsetY = prevY;
            this._render();
            this._showToast(`Exported model.${format}`);
        }, 100);
    },

    _exportJsonClipboard() {
        const data = JSON.stringify(this._getGraphData(), null, 2);
        navigator.clipboard
            .writeText(data)
            .then(() => {
                this._showToast("JSON copied!");
            })
            .catch(() => {
                alert("Failed to copy. Check console for the JSON.");
                console.log(data);
            });
    },

    // ========== VALIDATION ==========

    // Validation state
    errorLinkIds: new Set(),
    errorNodeIds: new Set(),
    errorPortIds: new Set(),
    warningLinkIds: new Set(),
    warningNodeIds: new Set(),
    warningPortIds: new Set(),

    _runCheck() {
        const graphData = JSON.stringify(this._getGraphData());

        fetch("/sketchmod/api/validate/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": this._getCsrfToken(),
            },
            body: JSON.stringify({ graph: graphData }),
        })
            .then((res) => res.json())
            .then((data) => {
                if (data.success) {
                    this._applyValidationResults(data);
                    this._showValidationModal({
                        errors: data.errors,
                        warnings: data.warnings,
                        isValid: data.isValid,
                    });
                    this._render();
                }
            })
            .catch((err) => {
                console.error("Validation failed:", err);
                this._showToast("Validation failed. Check console.");
            });
    },
    _applyValidationResults(data) {
        this.errorLinkIds = new Set();
        this.errorNodeIds = new Set();
        this.errorPortIds = new Set();
        this.warningLinkIds = new Set();
        this.warningNodeIds = new Set();
        this.warningPortIds = new Set();

        for (const e of data.errors) {
            if (e.nodeId) this.errorNodeIds.add(e.nodeId);
            if (e.portId) this.errorPortIds.add(e.portId);
            if (e.linkKey) this.errorLinkIds.add(e.linkKey);
        }
        for (const w of data.warnings) {
            if (w.nodeId) this.warningNodeIds.add(w.nodeId);
            if (w.portId) this.warningPortIds.add(w.portId);
            if (w.linkKey) this.warningLinkIds.add(w.linkKey);
        }
    },
    _closeValidationModal() {
        document.getElementById("validationModal").style.display = "none";
    },
    _clearValidation() {
        this.errorLinkIds = new Set();
        this.errorNodeIds = new Set();
        this.errorPortIds = new Set();
        this.warningLinkIds = new Set();
        this.warningNodeIds = new Set();
        this.warningPortIds = new Set();

        const btn = document.getElementById("btnClearValidation");
        if (btn) btn.style.display = "none";

        this._render();
    },
    _showValidationModal(result) {
        const modal = document.getElementById("validationModal");
        const content = document.getElementById("validationContent");
        const title = document.getElementById("validationModalTitle");
        const clearBtn = document.getElementById("btnClearValidation");

        if (!modal || !content) return;

        const { errors, warnings } = result;

        if (errors.length === 0 && warnings.length === 0) {
            title.textContent = "✓ All Clear";
            content.innerHTML = `
            <div class="validation-result success">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="20 6 9 17 4 12"/>
                </svg>
                <span>All checks passed! Your model is ready to export.</span>
            </div>`;
            if (clearBtn) clearBtn.style.display = "none";
        } else {
            const parts = [];
            if (errors.length)
                parts.push(
                    `${errors.length} error${errors.length > 1 ? "s" : ""}`,
                );
            if (warnings.length)
                parts.push(
                    `${warnings.length} warning${warnings.length > 1 ? "s" : ""}`,
                );
            title.textContent = `Validation: ${parts.join(", ")}`;

            let html = "";
            if (errors.length > 0) {
                html += `<div class="validation-section-label" style="color: #ef4444;">Errors</div>`;
                for (const e of errors) {
                    html += `
                <div class="validation-result error">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"/>
                        <line x1="15" y1="9" x2="9" y2="15"/>
                        <line x1="9" y1="9" x2="15" y2="15"/>
                    </svg>
                    <span>${e.message}</span>
                </div>`;
                }
            }
            if (warnings.length > 0) {
                html += `<div class="validation-section-label" style="color: #f59e0b;">Warnings</div>`;
                for (const w of warnings) {
                    html += `
                <div class="validation-result warning">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                        <line x1="12" y1="9" x2="12" y2="13"/>
                        <line x1="12" y1="17" x2="12.01" y2="17"/>
                    </svg>
                    <span>${w.message}</span>
                </div>`;
                }
            }
            content.innerHTML = html;
            if (clearBtn) clearBtn.style.display = "flex";
        }
        modal.style.display = "flex";
    },

    _showValidationPanel(result) {
        const modal = document.getElementById("validationModal");
        const content = document.getElementById("validationContent");
        const title = document.getElementById("validationModalTitle");
        if (!modal || !content) return;

        const { errors, warnings } = result;

        if (errors.length === 0 && warnings.length === 0) {
            title.textContent = "✓ All Clear";
            content.innerHTML = `
            <div class="validation-result success">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="20 6 9 17 4 12"/>
                </svg>
                <span>All checks passed! Your model is ready to export.</span>
            </div>`;
        } else {
            const errorCount = errors.length;
            const warnCount = warnings.length;
            const parts = [];
            if (errorCount)
                parts.push(`${errorCount} error${errorCount > 1 ? "s" : ""}`);
            if (warnCount)
                parts.push(`${warnCount} warning${warnCount > 1 ? "s" : ""}`);
            title.textContent = `Validation: ${parts.join(", ")}`;

            let html = "";

            if (errors.length > 0) {
                html += `<div class="validation-section-label" style="color: #ef4444;">Errors</div>`;
                for (const e of errors) {
                    html += `
                <div class="validation-result error">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"/>
                        <line x1="15" y1="9" x2="9" y2="15"/>
                        <line x1="9" y1="9" x2="15" y2="15"/>
                    </svg>
                    <span>${e.message}</span>
                </div>`;
                }
            }

            if (warnings.length > 0) {
                html += `<div class="validation-section-label" style="color: #f59e0b;">Warnings</div>`;
                for (const w of warnings) {
                    html += `
                <div class="validation-result warning">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                        <line x1="12" y1="9" x2="12" y2="13"/>
                        <line x1="12" y1="17" x2="12.01" y2="17"/>
                    </svg>
                    <span>${w.message}</span>
                </div>`;
                }
            }

            content.innerHTML = html;
        }

        modal.style.display = "flex";
    },
    _toggleHighlightMenu() {
        const menu = document.getElementById("highlightMenu");
        const dropdown = document.getElementById("highlightDropdown");
        if (!menu || !dropdown) return;

        const isOpen = menu.classList.contains("open");
        if (isOpen) {
            menu.classList.remove("open");
            dropdown.classList.remove("open");
        } else {
            // Close export menu if open
            document.getElementById("exportMenu")?.classList.remove("open");
            document.getElementById("exportDropdown")?.classList.remove("open");
            menu.classList.add("open");
            dropdown.classList.add("open");
        }
    },

    _highlightPhase(phase) {
        const graphData = JSON.stringify(this._getGraphData());

        fetch("/sketchmod/api/highlight-path/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": this._getCsrfToken(),
            },
            body: JSON.stringify({ graph: graphData, phase: phase }),
        })
            .then((res) => res.json())
            .then((data) => {
                if (data.success) {
                    this._clearHighlight();

                    // 1. Active nodes
                    this._highlightPhaseNodes = new Set();
                    for (const nid of data.nodes) {
                        const node = this.nodes.find((n) => n.id === nid);
                        if (node) this._highlightPhaseNodes.add(node);
                    }

                    // 2. Active links + collect active ports
                    this._highlightPhaseLinks = new Set();
                    const activePorts = new Set();
                    for (const key of data.links) {
                        const [fromId, toId] = key.split("→");
                        const link = this.links.find(
                            (l) => l.from.id === fromId && l.to.id === toId,
                        );
                        if (link) {
                            this._highlightPhaseLinks.add(link);
                            activePorts.add(link.from);
                            activePorts.add(link.to);
                        }
                    }

                    // 3. Also mark ports of active nodes that have the phase (even if no links)
                    for (const node of this._highlightPhaseNodes) {
                        for (const p of node.inputs.concat(
                            node.outputs,
                            node.paramInputs,
                            node.paramOutputs,
                        )) {
                            if (
                                p.activationPhases &&
                                p.activationPhases.includes(phase)
                            ) {
                                activePorts.add(p);
                            }
                        }
                    }

                    this._highlightPhasePorts = activePorts; // <-- this line is crucial
                    this._render();

                    const btn = document.getElementById("btnClearPath");
                    if (btn) btn.style.display = "flex";
                }
            })
            .catch((err) => {
                console.error("Highlight path failed:", err);
                this._showToast("Highlight failed. Check console.");
            });
    },
    _showAllPhases() {
        this._clearHighlight();

        const phases = ["preprocessing", "training", "evaluation"];

        // ---- 1. Fetch node & link info from API (unchanged) ----
        const phaseLinkSets = new Map();
        const phaseNodeSets = new Map();

        const fetchPromises = phases.map((phase) => {
            const graphData = JSON.stringify(this._getGraphData());
            return fetch("/sketchmod/api/highlight-path/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": this._getCsrfToken(),
                },
                body: JSON.stringify({ graph: graphData, phase: phase }),
            })
                .then((res) => res.json())
                .then((data) => {
                    if (!data.success) {
                        console.warn(`ShowAll: phase '${phase}' failed`, data);
                        return;
                    }
                    phaseNodeSets.set(phase, new Set(data.nodes));
                    phaseLinkSets.set(phase, new Set(data.links));
                })
                .catch((err) =>
                    console.error(`ShowAll fetch error (${phase}):`, err),
                );
        });

        Promise.all(fetchPromises).then(() => {
            // ---- 2. Build link & node maps from API results ----
            this._showAllLinks = new Map();
            this._showAllNodes = new Map();

            for (const [phase, linkSet] of phaseLinkSets) {
                for (const key of linkSet) {
                    const [fromId, toId] = key.split("→");
                    const link = this.links.find(
                        (l) => l.from.id === fromId && l.to.id === toId,
                    );
                    if (!link) continue;
                    if (!this._showAllLinks.has(link))
                        this._showAllLinks.set(link, new Set());
                    this._showAllLinks.get(link).add(phase);
                }
            }
            for (const [phase, nodeSet] of phaseNodeSets) {
                for (const nid of nodeSet) {
                    const node = this.nodes.find((n) => n.id === nid);
                    if (!node) continue;
                    if (!this._showAllNodes.has(node))
                        this._showAllNodes.set(node, new Set());
                    this._showAllNodes.get(node).add(phase);
                }
            }

            // ---- 3. Build port map DIRECTLY from user checkboxes ----
            this._showAllPorts = new Map();
            for (const port of this.ports) {
                if (port.activationPhases && port.activationPhases.length > 0) {
                    this._showAllPorts.set(
                        port,
                        new Set(port.activationPhases),
                    );
                }
            }

            this._render();
            const btn = document.getElementById("btnClearPath");
            if (btn) btn.style.display = "flex";
        });
    },
    _getShowAllColor: function (phases) {
        const map = {
            1: {
                preprocessing: "#ef4444",
                training: "#3b82f6",
                evaluation: "#eab308",
            },
            2: {
                "preprocessing,training": "#8b5cf6",
                "evaluation,preprocessing": "#f97316",
                "evaluation,training": "#22c55e",
            },
            3: "#ffffff",
        };
        if (phases.size === 1) {
            return map[1][[...phases][0]] || "#ffffff";
        } else if (phases.size === 2) {
            const key = [...phases].sort().join(",");
            return map[2][key] || "#ffffff";
        } else {
            return map[3];
        }
    },
    _clearHighlight() {
        this._highlightPhaseNodes = null;
        this._highlightPhaseLinks = null;
        this._highlightPhasePorts = null;
        this._showAllLinks = null;
        this._showAllNodes = null;
        this._showAllPorts = null;
        const btn = document.getElementById("btnClearPath");
        if (btn) btn.style.display = "none";
        this._render();
    },
    // ---------- Copy ----------
    _copySelected() {
        if (this.selectedNodes.length === 0) return;
        const selectedIds = new Set(this.selectedNodes.map((n) => n.id));
        const nodesData = this.selectedNodes.map((n) => n.toJSON());
        const linksData = this.links
            .filter(
                (l) =>
                    selectedIds.has(l.from.node.id) &&
                    selectedIds.has(l.to.node.id),
            )
            .map((l) => l.toJSON());

        this.clipboard = JSON.stringify({ nodes: nodesData, links: linksData });
        this._pasteCounter = 0; // ← reset counter for a fresh copy
        this._showToast(`${nodesData.length} node(s) copied`);
    },

    // ---------- Paste ----------
    _pasteClipboard() {
        if (!this.clipboard) return;

        let cb;
        try {
            cb = JSON.parse(this.clipboard);
        } catch (e) {
            console.error("[PASTE] Invalid clipboard JSON:", e);
            return;
        }
        if (!cb.nodes || cb.nodes.length === 0) return;

        this._saveUndoState();

        // Increase paste offset each time
        if (!this._pasteCounter) this._pasteCounter = 0;
        this._pasteCounter++;
        const offsetX = 50 * this._pasteCounter;
        const offsetY = 50 * this._pasteCounter;

        const oldToNewId = {}; // old node id → new node id
        const oldPortToNewPort = {}; // old port id → new Port object

        // ---- Create new nodes with UNIQUE ids ----
        for (const nd of cb.nodes) {
            let NodeClass;
            const entry = this.nodeRegistry.find((r) => r.type === nd.type);
            if (entry) {
                NodeClass = entry.class;
            } else if (nd.type === "input-data") {
                NodeClass = InputDataNode;
            } else if (nd.type === "output") {
                NodeClass = OutputNode;
            } else {
                console.warn("[PASTE] Unknown node type:", nd.type);
                continue;
            }

            // Force a unique ID: use a prefix that includes the paste counter to avoid any collision
            const uniqueId =
                nd.type[0] + this._pasteCounter + "_" + ++this.nodeCounter;
            oldToNewId[nd.id] = uniqueId;

            const node = new NodeClass(
                uniqueId,
                nd.x + offsetX,
                nd.y + offsetY,
            );
            node.fromJSON(nd);

            // Override whatever fromJSON set for id and position
            node.id = uniqueId;
            node.x = nd.x + offsetX;
            node.y = nd.y + offsetY;

            // Map old ports → new ports
            node.inputs.forEach((p, i) => {
                const oldId = nd.inputPorts?.[i]?.id;
                p.id = `${uniqueId}_input_${i}`;
                if (oldId) oldPortToNewPort[oldId] = p;
            });
            node.outputs.forEach((p, i) => {
                const oldId = nd.outputPorts?.[i]?.id;
                p.id = `${uniqueId}_output_${i}`;
                if (oldId) oldPortToNewPort[oldId] = p;
            });
            node.paramInputs.forEach((p, i) => {
                const oldId = nd.paramInputs?.[i]?.id;
                p.id = `${uniqueId}_param_in_${i}`;
                if (oldId) oldPortToNewPort[oldId] = p;
            });
            node.paramOutputs.forEach((p, i) => {
                const oldId = nd.paramOutputs?.[i]?.id;
                p.id = `${uniqueId}_param_out_${i}`;
                if (oldId) oldPortToNewPort[oldId] = p;
            });

            node.updatePorts();
            this.nodes.push(node);
        }

        this.ports = this._collectPorts();

        // ---- Recreate links between pasted nodes ----
        for (const ld of cb.links) {
            const newFrom = oldPortToNewPort[ld.from];
            const newTo = oldPortToNewPort[ld.to];
            if (newFrom && newTo) {
                this.links.push(new Link(newFrom, newTo, ld.weight));
            }
        }

        // Select the newly pasted nodes
        this.selectedNodes = this.nodes.filter((n) =>
            Object.values(oldToNewId).includes(n.id),
        );
        this.selectedLinks = [];
        this.selectedPorts = [];
        this._hideProperties();

        this._saveToSession();
        this._propagateShapes();
        this._render();
        this._showToast(`${cb.nodes.length} node(s) pasted`);
    },
    openImportModal() {
        document.getElementById("importModal").style.display = "flex";
        document.getElementById("importJsonText").value = "";
        document.getElementById("importFileName").textContent =
            "No file chosen";
        document.getElementById("importJsonFile").value = "";
        setTimeout(() => document.getElementById("importJsonText").focus(), 0);
    },

    closeImportModal() {
        document.getElementById("importModal").style.display = "none";
    },
    _handleImportSubmit() {
        const text = document.getElementById("importJsonText").value.trim();
        const file = document.getElementById("importJsonFile").files[0];

        if (!text && !file) {
            this._showToast("Paste JSON or choose a file.");
            return;
        }

        if (text) {
            // Paste method
            try {
                const graph = JSON.parse(text);
                this._importGraphFromJSON(graph);
                this.closeImportModal();
            } catch (err) {
                console.error("Invalid JSON:", err);
                this._showToast("Invalid JSON format.");
            }
            return;
        }

        if (file) {
            // File method
            const reader = new FileReader();
            reader.onload = (ev) => {
                try {
                    const graph = JSON.parse(ev.target.result);
                    this._importGraphFromJSON(graph);
                    this.closeImportModal();
                } catch (err) {
                    console.error("Invalid JSON file:", err);
                    this._showToast("Invalid JSON file.");
                }
            };
            reader.readAsText(file);
        }
    },
    _importGraphFromJSON(graph) {
        if (!graph.nodes || !graph.links) {
            this._showToast('JSON must contain "nodes" and "links".');
            return;
        }

        // Clear the current graph
        this.nodes = [];
        this.links = [];
        this.ports = [];
        this.nodeCounter = graph.nodeCounter || 0;

        // Reset model ownership
        this._currentModelId = null;
        this._currentModelName = null;
        sessionStorage.removeItem("sketchmod-active-model-id");

        // Remove the 'load' parameter from the URL
        if (window.history && window.history.replaceState) {
            const newUrl = window.location.pathname;
            window.history.replaceState({}, "", newUrl);
        }

        // Rebuild nodes
        for (const nd of graph.nodes) {
            const entry = this.nodeRegistry.find((r) => r.type === nd.type);
            let node;
            if (entry) {
                node = new entry.class(nd.id, nd.x, nd.y);
            } else if (nd.type === "input-data") {
                node = new InputDataNode(nd.id, nd.x, nd.y);
            } else if (nd.type === "output") {
                node = new OutputNode(nd.id, nd.x, nd.y);
            } else {
                console.warn("Unknown node type:", nd.type);
                continue;
            }
            node.fromJSON(nd);
            this.nodes.push(node);
        }

        this.ports = this._collectPorts();

        // Rebuild links
        for (const ld of graph.links) {
            const from = this.ports.find((p) => p.id === ld.from);
            const to = this.ports.find((p) => p.id === ld.to);
            if (from && to) {
                const link = new Link(from, to, ld.weight);
                if (ld.weightShape) link.weightShape = ld.weightShape;
                if (ld.hasWeight !== undefined) link.hasWeight = ld.hasWeight;
                this.links.push(link);
            }
        }

        // Restore port shapes & activation phases
        if (graph.ports) {
            for (const p of graph.ports) {
                const port = this.ports.find((pp) => pp.id === p.id);
                if (!port) continue;
                if (p.shape) {
                    port.setShape(
                        p.shape.shape,
                        p.shape.dtype,
                        p.shape.known,
                        p.shape.symbolic,
                    );
                }
                if (p.activationPhases) {
                    port.activationPhases = p.activationPhases;
                }
            }
        }

        this._saveToSession();
        this._propagateShapes();
        this._zoomFit();
        this._render();
        this._showToast("Model imported successfully.");
    },
    _updateOutputActivation(role, value) {
        if (this.selectedNodes.length !== 1) return;
        const node = this.selectedNodes[0];
        if (!(node instanceof OutputNode)) return;
        this._saveUndoState();
        node.outputActivations[role] = value;
        this._saveToSession();
        this._render();
    },
};
// ========== PORT BASE CLASS ==========
class Port {
    constructor(node, type, index, subType) {
        this.node = node;
        this.type = type; // "input" | "output"
        this.index = index;
        this.subType = subType || null;
        this.x = node.x;
        this.y = node.y;
        this.radius = 5;
        this.hoverRadius = 10;
        this.id = `${node.id}_${type}_${index}`;
        this.shape = null;
        this.bias = 0;
        this.activationPhases = this._defaultPhases();
    }
    _defaultPhases() {
        return [];
    }
    get connectionLimit() {
        return 1;
    }

    setShape(shapeArray, dtype, known, symbolic) {
        if (!shapeArray) {
            this.shape = null;
            return;
        }
        this.shape = {
            shape: shapeArray.map((s) => ShapeExpr.from(s)),
            dtype: dtype || "float32",
            known: known || false,
            symbolic: symbolic || false,
        };
    }

    clearShape() {
        this.shape = null;
    }

    hasShape() {
        return this.shape && this.shape.shape && this.shape.shape.length > 0;
    }

    shapeDisplay() {
        if (!this.hasShape()) return "Unknown";
        const shapeStr =
            "(" + this.shape.shape.map((s) => s.toString()).join(", ") + ")";
        if (this.shape.symbolic) return shapeStr + " (abstract)";
        return shapeStr + (this.shape.known ? "" : " (estimated)");
    }

    getConnectionCount() {
        return SketchMod.links.filter((l) => l.from === this || l.to === this)
            .length;
    }

    draw(ctx) {
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
        ctx.fillStyle = this._getColor();
        ctx.fill();
        ctx.strokeStyle = "#1a1d2e";
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Show‑All ring
        if (SketchMod._showAllPorts && SketchMod._showAllPorts.has(this)) {
            try {
                const phases = SketchMod._showAllPorts.get(this);
                const c = SketchMod._getShowAllColor(phases);
                ctx.beginPath();
                ctx.arc(this.x, this.y, this.radius + 3, 0, Math.PI * 2);
                ctx.strokeStyle = c;
                ctx.lineWidth = 2;
                ctx.shadowColor = "transparent";
                ctx.shadowBlur = 0;
                ctx.stroke();
            } catch (e) {}
        }

        // Single‑phase highlight ring
        if (
            SketchMod._highlightPhasePorts &&
            SketchMod._highlightPhasePorts.has(this)
        ) {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.radius + 3, 0, Math.PI * 2);
            ctx.strokeStyle = "#4ade80";
            ctx.lineWidth = 2;
            ctx.shadowColor = "transparent";
            ctx.shadowBlur = 0;
            ctx.stroke();
        }
    }

    drawHighlight(ctx) {
        if (SketchMod.errorPortIds.has(this.id)) {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.hoverRadius, 0, Math.PI * 2);
            ctx.fillStyle = "rgba(239, 68, 68, 0.2)";
            ctx.fill();
            ctx.strokeStyle = "#ef4444";
            ctx.lineWidth = 2.5;
            ctx.stroke();
            return;
        }
        if (SketchMod.warningPortIds.has(this.id)) {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.hoverRadius, 0, Math.PI * 2);
            ctx.fillStyle = "rgba(245, 158, 11, 0.2)";
            ctx.fill();
            ctx.strokeStyle = "#f59e0b";
            ctx.lineWidth = 2.5;
            ctx.stroke();
            return;
        }
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.hoverRadius, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(255, 255, 255, 0.2)";
        ctx.fill();
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 2.5;
        ctx.stroke();
    }
    _getColor() {
        if (this.subType === "loss") return "#ef4444";
        if (this.subType === "labels") return "#f59e0b";
        if (this.subType === "train") return "#f59e0b";
        if (this.subType === "test") return "#4ade80";
        if (this.subType === "features") return "#ff00b7";
        if (this.subType === "main") return "#9e396f";
        if (this.subType === "skip") return "#ffcc00";
        if (this.subType === "coord") return "#60a5fa";
        if (this.subType === "color") return "#ff00b7";
        if (this.type === "input") return "#ef4444";
        if (this.type === "output") return "#60a5fa";
        return "#94a3b8";
    }

    toJSON() {
        return {
            id: this.id,
            type: this.type,
            index: this.index,
            subType: this.subType,
            shape: this.shape
                ? {
                      shape: this.shape.shape.map((s) => s.toString()),
                      dtype: this.shape.dtype,
                      known: this.shape.known,
                      symbolic: this.shape.symbolic,
                  }
                : null,
            bias: this.bias,
            portKind: this._getPortKind(),
            activationPhases: this.activationPhases,
        };
    }

    _getPortKind() {
        if (this instanceof MultiPort) return "multi";
        if (this instanceof RolePort) return "role";
        if (this instanceof ParamPort) return "param";
        return "data";
    }
}

// ========== DATA PORT ==========
class DataPort extends Port {
    constructor(node, type, index, subType) {
        super(node, type, index, subType);
    }

    get connectionLimit() {
        return 1;
    }

    draw(ctx) {
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
        ctx.fillStyle = this._getColor();
        ctx.fill();
        ctx.strokeStyle = "#1a1d2e";
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Show‑All ring
        if (SketchMod._showAllPorts && SketchMod._showAllPorts.has(this)) {
            try {
                const phases = SketchMod._showAllPorts.get(this);
                const c = SketchMod._getShowAllColor(phases);
                ctx.beginPath();
                ctx.arc(this.x, this.y, this.radius + 3, 0, Math.PI * 2);
                ctx.strokeStyle = c;
                ctx.lineWidth = 2;
                ctx.shadowColor = "transparent";
                ctx.shadowBlur = 0;
                ctx.stroke();
            } catch (e) {}
        }

        // Single‑phase highlight ring
        if (
            SketchMod._highlightPhasePorts &&
            SketchMod._highlightPhasePorts.has(this)
        ) {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.radius + 3, 0, Math.PI * 2);
            ctx.strokeStyle = "#4ade80";
            ctx.lineWidth = 2;
            ctx.shadowColor = "transparent";
            ctx.shadowBlur = 0;
            ctx.stroke();
        }
    }

    _getColor() {
        if (this.subType === "loss") return "#ef4444";
        if (this.subType === "labels") return "#f59e0b";
        if (this.subType === "train") return "#f59e0b";
        if (this.subType === "test") return "#4ade80";
        if (this.subType === "features") return "#ff00b7";
        if (this.subType === "main") return "#9e396f";
        if (this.subType === "skip") return "#ffcc00";
        if (this.subType === "coord") return "#60a5fa";
        if (this.subType === "color") return "#ff00b7";
        if (this.subType === "predictions") return "#60a5fa";
        if (this.type === "input") return "#ef4444";
        if (this.type === "output") return "#60a5fa";
        return "#94a3b8";
    }

    _getPortKind() {
        return "data";
    }

    toJSON() {
        return {
            ...super.toJSON(),
            portKind: "data",
        };
    }
}

// ========== MULTI PORT ==========
class MultiPort extends Port {
    constructor(node, type, index, subType, maxConnections) {
        super(node, type, index, subType);
        this._maxConnections = maxConnections || Infinity;
    }

    get connectionLimit() {
        return this._maxConnections;
    }

    draw(ctx) {
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
        ctx.fillStyle = this._getColor();
        ctx.fill();
        ctx.strokeStyle = "#1a1d2e";
        ctx.lineWidth = 2;
        ctx.stroke();

        const count = this.getConnectionCount();
        if (count > 1) {
            ctx.fillStyle = "#ffffff";
            ctx.font = "bold 7px Inter, sans-serif";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText(count, this.x, this.y + 0.3);
        }

        // Show‑All ring
        if (SketchMod._showAllPorts && SketchMod._showAllPorts.has(this)) {
            try {
                const phases = SketchMod._showAllPorts.get(this);
                const c = SketchMod._getShowAllColor(phases);
                ctx.beginPath();
                ctx.arc(this.x, this.y, this.radius + 3, 0, Math.PI * 2);
                ctx.strokeStyle = c;
                ctx.lineWidth = 2;
                ctx.shadowColor = "transparent";
                ctx.shadowBlur = 0;
                ctx.stroke();
            } catch (e) {}
        }

        // Single‑phase highlight ring
        if (
            SketchMod._highlightPhasePorts &&
            SketchMod._highlightPhasePorts.has(this)
        ) {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.radius + 3, 0, Math.PI * 2);
            ctx.strokeStyle = "#4ade80";
            ctx.lineWidth = 2;
            ctx.shadowColor = "transparent";
            ctx.shadowBlur = 0;
            ctx.stroke();
        }
    }

    _getColor() {
        return "#a78bfa"; // Purple for multi-ports
    }

    _getPortKind() {
        return "multi";
    }

    toJSON() {
        return {
            ...super.toJSON(),
            portKind: "multi",
        };
    }
}

// ========== ROLE PORT ==========
class RolePort extends Port {
    constructor(node, type, index, role) {
        super(node, type, index, null);
        this.role = role || null; // "loss", "prediction", "evaluation", "labels", "color"
    }
    _defaultPhases() {
        const roleDefaults = {
            loss: ["training"],
            prediction: ["evaluation"],
            evaluation: ["evaluation"],
            labels: ["training"],
            color: ["evaluation"],
        };
        return this.role ? roleDefaults[this.role] || [] : [];
    }
    get connectionLimit() {
        return 1;
    }
    draw(ctx) {
        ctx.beginPath();
        ctx.moveTo(this.x, this.y - this.radius - 1);
        ctx.lineTo(this.x + this.radius + 1, this.y);
        ctx.lineTo(this.x, this.y + this.radius + 1);
        ctx.lineTo(this.x - this.radius - 1, this.y);
        ctx.closePath();
        ctx.fillStyle = this._getColor();
        ctx.fill();
        ctx.strokeStyle = "#1a1d2e";
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Show‑All ring (circle for visibility)
        if (SketchMod._showAllPorts && SketchMod._showAllPorts.has(this)) {
            try {
                const phases = SketchMod._showAllPorts.get(this);
                const c = SketchMod._getShowAllColor(phases);
                ctx.beginPath();
                ctx.arc(this.x, this.y, this.radius + 3, 0, Math.PI * 2);
                ctx.strokeStyle = c;
                ctx.lineWidth = 2;
                ctx.shadowColor = "transparent";
                ctx.shadowBlur = 0;
                ctx.stroke();
            } catch (e) {}
        }

        // Single‑phase highlight ring
        if (
            SketchMod._highlightPhasePorts &&
            SketchMod._highlightPhasePorts.has(this)
        ) {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.radius + 3, 0, Math.PI * 2);
            ctx.strokeStyle = "#4ade80";
            ctx.lineWidth = 2;
            ctx.shadowColor = "transparent";
            ctx.shadowBlur = 0;
            ctx.stroke();
        }
    }
    _getPortKind() {
        return "role";
    }

    _getColor() {
        if (this.role === "loss") return "#53BF9D";
        if (this.role === "prediction") return "#BD4291";
        if (this.role === "evaluation") return "#FFC54D ";
        if (this.role === "labels") return "#f59e0b";
        if (this.role === "color") return "#ff00b7";
        return "#94a3b8";
    }

    toJSON() {
        return {
            ...super.toJSON(),
            role: this.role,
            portKind: "role",
        };
    }
}

// ========== PARAM PORT ==========
class ParamPort extends Port {
    constructor(node, type, index) {
        super(node, type, index, null);
        this.id = `${node.id}_${type === "input" ? "param_in" : "param_out"}_${index}`;
    }
    _defaultPhases() {
        return ["preprocessing"];
    }
    get connectionLimit() {
        return 1;
    }

    draw(ctx) {
        const size = this.radius + 0.5;
        ctx.beginPath();
        ctx.moveTo(this.x, this.y - size);
        ctx.lineTo(this.x + size, this.y);
        ctx.lineTo(this.x, this.y + size);
        ctx.lineTo(this.x - size, this.y);
        ctx.closePath();
        ctx.fillStyle = this._getColor();
        ctx.fill();
        ctx.strokeStyle = "#1a1d2e";
        ctx.lineWidth = 2;
        ctx.stroke();

        // Show‑All ring (circle for visibility)
        if (SketchMod._showAllPorts && SketchMod._showAllPorts.has(this)) {
            try {
                const phases = SketchMod._showAllPorts.get(this);
                const c = SketchMod._getShowAllColor(phases);
                ctx.beginPath();
                ctx.arc(this.x, this.y, this.radius + 3, 0, Math.PI * 2);
                ctx.strokeStyle = c;
                ctx.lineWidth = 2;
                ctx.shadowColor = "transparent";
                ctx.shadowBlur = 0;
                ctx.stroke();
            } catch (e) {}
        }

        // Single‑phase highlight ring
        if (
            SketchMod._highlightPhasePorts &&
            SketchMod._highlightPhasePorts.has(this)
        ) {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.radius + 3, 0, Math.PI * 2);
            ctx.strokeStyle = "#4ade80";
            ctx.lineWidth = 2;
            ctx.shadowColor = "transparent";
            ctx.shadowBlur = 0;
            ctx.stroke();
        }
    }
    _getColor() {
        if (this.type === "input") return "#fbbf24"; // Bright amber
        if (this.type === "output") return "#38bdf8"; // Sky blue
        return "#fbbf24";
    }

    _getPortKind() {
        return "param";
    }

    toJSON() {
        return {
            ...super.toJSON(),
            portKind: "param",
        };
    }
}

// ========== SHAPE EXPRESSION ==========
class ShapeExpr {
    constructor(value) {
        if (value instanceof ShapeExpr) {
            this.terms = new Map(value.terms);
            this.isSymbolic = value.isSymbolic;
        } else if (typeof value === "number") {
            this.terms = new Map();
            if (value !== 0) {
                this.terms.set("", value); // "" key = constant term
            }
            this.isSymbolic = false;
        } else if (typeof value === "string") {
            const trimmed = value.trim();
            const num = Number(trimmed);
            if (!isNaN(num) && String(num) === trimmed) {
                this.terms = new Map();
                if (num !== 0) {
                    this.terms.set("", num);
                }
                this.isSymbolic = false;
            } else {
                // Parse the string into terms
                this.terms = ShapeExpr._parse(trimmed);
                this.isSymbolic = this._hasSymbols();
            }
        } else {
            this.terms = new Map();
            this.isSymbolic = false;
        }
    }

    static from(value) {
        if (value instanceof ShapeExpr) return new ShapeExpr(value);
        return new ShapeExpr(value);
    }

    // ========== PARSING ==========
    static _parse(expr) {
        const terms = new Map();
        if (!expr || expr.trim() === "") return terms;

        // Split by + and - (handling negative terms)
        // Replace " - " with " + -" for splitting
        let normalized = expr.replace(/\s*-\s*/g, " + -");
        // Split by +
        const parts = normalized.split(/\s*\+\s*/);

        for (const part of parts) {
            const trimmed = part.trim();
            if (!trimmed) continue;

            // Match patterns: "3 * x", "x", "-2 * y", "5", "-3"
            const match = trimmed.match(/^(-?\d*\.?\d*)\s*\*?\s*(.*)$/);
            if (!match) continue;

            let coeffStr = match[1];
            let symbol = match[2].trim();

            // Handle cases like "x" (coeffStr = "", symbol = "x")
            if (coeffStr === "" || coeffStr === "-") {
                coeffStr = coeffStr === "-" ? "-1" : "1";
            }
            // Handle cases like "5" (coeffStr = "5", symbol = "")
            if (symbol === "" && coeffStr !== "") {
                symbol = ""; // constant term
            }

            const coeff = parseFloat(coeffStr);
            if (isNaN(coeff)) continue;

            const existing = terms.get(symbol) || 0;
            const sum = existing + coeff;
            if (sum === 0) {
                terms.delete(symbol);
            } else {
                terms.set(symbol, sum);
            }
        }

        return terms;
    }

    _hasSymbols() {
        for (const [key, _] of this.terms) {
            if (key !== "") return true;
        }
        return false;
    }

    // ========== OPERATIONS ==========
    add(other) {
        other = ShapeExpr.from(other);
        const result = new ShapeExpr(0);
        result.terms = new Map(this.terms);

        for (const [symbol, coeff] of other.terms) {
            const existing = result.terms.get(symbol) || 0;
            const sum = existing + coeff;
            if (sum === 0) {
                result.terms.delete(symbol);
            } else {
                result.terms.set(symbol, sum);
            }
        }

        result.isSymbolic = result._hasSymbols();
        if (result.terms.size === 0) {
            result.terms.set("", 0);
            result.isSymbolic = false;
        }
        return result;
    }

    subtract(other) {
        other = ShapeExpr.from(other);
        const negated = new ShapeExpr(0);
        for (const [symbol, coeff] of other.terms) {
            negated.terms.set(symbol, -coeff);
        }
        negated.isSymbolic = negated._hasSymbols();
        return this.add(negated);
    }

    multiply(other) {
        other = ShapeExpr.from(other);

        // If either is zero, return zero
        if (this.isZero() || other.isZero()) {
            return new ShapeExpr(0);
        }

        // If both are constants, just multiply
        if (!this.isSymbolic && !other.isSymbolic) {
            const a = this.terms.get("") || 0;
            const b = other.terms.get("") || 0;
            return new ShapeExpr(a * b);
        }

        // If one is a constant and the other is symbolic
        if (!this.isSymbolic) {
            const constVal = this.terms.get("") || 1;
            const result = new ShapeExpr(0);
            for (const [symbol, coeff] of other.terms) {
                result.terms.set(symbol, coeff * constVal);
            }
            result.isSymbolic = result._hasSymbols();
            return result;
        }
        if (!other.isSymbolic) {
            return other.multiply(this);
        }

        // Both symbolic — can't simplify (would need x*y terms)
        // Fall back to string representation
        return new ShapeExpr(`${this.toString()} * ${other.toString()}`);
    }

    divide(other) {
        other = ShapeExpr.from(other);

        if (other.isZero()) return new ShapeExpr(0);

        // If both are constants
        if (!this.isSymbolic && !other.isSymbolic) {
            const a = this.terms.get("") || 0;
            const b = other.terms.get("") || 1;
            return new ShapeExpr(Math.floor(a / b));
        }

        // If dividing symbolic by constant
        if (!other.isSymbolic) {
            const constVal = other.terms.get("") || 1;
            const result = new ShapeExpr(0);
            for (const [symbol, coeff] of this.terms) {
                result.terms.set(symbol, coeff / constVal);
            }
            result.isSymbolic = result._hasSymbols();
            return result;
        }

        // Symbolic division — can't simplify
        return new ShapeExpr(`${this.toString()} / ${other.toString()}`);
    }

    // ========== COMPARISON ==========
    equals(other) {
        other = ShapeExpr.from(other);
        if (this.terms.size !== other.terms.size) return false;
        for (const [symbol, coeff] of this.terms) {
            if (other.terms.get(symbol) !== coeff) return false;
        }
        return true;
    }

    isZero() {
        if (this.terms.size === 0) return true;
        if (
            this.terms.size === 1 &&
            this.terms.has("") &&
            this.terms.get("") === 0
        )
            return true;
        return false;
    }

    isNumber() {
        return !this.isSymbolic;
    }

    toNumber() {
        return this.isSymbolic ? NaN : this.terms.get("") || 0;
    }

    greaterThan(other) {
        other = ShapeExpr.from(other);
        if (!this.isSymbolic && !other.isSymbolic) {
            return this.value > other.value;
        }
        return false; // Can't compare symbolic
    }

    lessThan(other) {
        other = ShapeExpr.from(other);
        if (!this.isSymbolic && !other.isSymbolic) {
            return this.value < other.value;
        }
        return false;
    }

    // ========== DISPLAY ==========
    toString() {
        if (this.terms.size === 0) return "0";

        const parts = [];
        // Sort so constants come first, then symbols alphabetically
        const sorted = [...this.terms.entries()].sort((a, b) => {
            if (a[0] === "") return -1;
            if (b[0] === "") return 1;
            return a[0].localeCompare(b[0]);
        });

        for (const [symbol, coeff] of sorted) {
            if (symbol === "") {
                parts.push(String(coeff));
            } else if (coeff === 1) {
                parts.push(symbol);
            } else if (coeff === -1) {
                parts.push(`-${symbol}`);
            } else {
                parts.push(`${coeff} * ${symbol}`);
            }
        }

        let result = parts.join(" + ");
        // Clean up "x + -2" → "x - 2"
        result = result.replace(/\+\s*-/g, "- ");
        return result;
    }

    toJSON() {
        return this.toString();
    }

    static fromJSON(str) {
        return new ShapeExpr(str);
    }
}
// ========== NODE CLASSES ==========

class BaseNode {
    constructor(id, x, y, type) {
        this.id = id;
        this.x = x;
        this.y = y;
        this.type = type;
        this.inputs = [];
        this.outputs = [];
        this.paramInputs = [];
        this.paramOutputs = [];
        this.fitted = false;

        // Constraints — override in subclasses
        this.maxInputs = Infinity;
        this.minInputs = 0;
        this.maxOutputs = Infinity;
        this.minOutputs = 0;
        this.allowedInputTypes = null; // null = any, ["features"] = only features
        this.allowedOutputTypes = null; // null = any, ["train", "test"] = only train or test
        this.maxParamInputs = 0;
        this.minParamInputs = 0;
        this.maxParamOutputs = 0;
        this.minParamOutputs = 0;
        this.bias = 0;
        this.hasBias = false;
    }

    computeOutputShapes() {
        return this.outputs.map(() => ({
            shape: null,
            dtype: "float32",
            known: false,
            symbolic: false,
        }));
    }
    containsPoint(px, py) {
        const b = this.getBounds();
        return px >= b.x && px <= b.x + b.w && py >= b.y && py <= b.y + b.h;
    }

    addInput(subType) {
        if (!this.canAddInput(subType)) return null;
        const p = new Port(
            this,
            "input",
            this.inputs.length,
            subType || null,
            "data",
        );
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
            "data",
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
    addParamInput() {
        if (this.paramInputs.length >= this.maxParamInputs) return null;
        const p = new ParamPort(this, "input", this.paramInputs.length);
        this.paramInputs.push(p);
        this.updatePorts();
        return p;
    }

    addParamOutput() {
        if (this.paramOutputs.length >= this.maxParamOutputs) return null;
        const p = new ParamPort(this, "output", this.paramOutputs.length);
        this.paramOutputs.push(p);
        this.updatePorts();
        return p;
    }
    removeParamInput() {
        if (!this.canRemoveParamInput()) return null;
        const port = this.paramInputs.pop();
        return port;
    }

    removeParamOutput() {
        if (!this.canRemoveParamOutput()) return null;
        const port = this.paramOutputs.pop();
        return port;
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
    canAddParamInput() {
        return this.paramInputs.length < this.maxParamInputs;
    }

    canAddParamOutput() {
        return this.paramOutputs.length < this.maxParamOutputs;
    }

    canRemoveParamInput() {
        return this.paramInputs.length > this.minParamInputs;
    }

    canRemoveParamOutput() {
        return this.paramOutputs.length > this.minParamOutputs;
    }

    getPorts() {
        return [
            ...this.inputs,
            ...this.outputs,
            ...this.paramInputs,
            ...this.paramOutputs,
        ];
    }

    updatePorts() {}

    toJSON() {
        return {
            id: this.id,
            type: this.type,
            x: this.x,
            y: this.y,
            inputPorts: this.inputs.map((p) => p.toJSON()),
            outputPorts: this.outputs.map((p) => p.toJSON()),
            numInputs: this.inputs.length,
            numOutputs: this.outputs.length,
            activation: this.activation,
            numNeurons: this.numNeurons,
            bias: this.bias,
            hasBias: this.hasBias,
            paramInputs: this.paramInputs.map((p) => p.toJSON()),
            paramOutputs: this.paramOutputs.map((p) => p.toJSON()),
            numParamInputs: this.paramInputs.length,
            numParamOutputs: this.paramOutputs.length,
        };
    }

    fromJSON(data) {
        this.inputs = [];
        this.outputs = [];
        this.paramInputs = [];
        this.paramOutputs = [];

        // Restore input ports
        if (data.inputPorts) {
            for (const p of data.inputPorts) {
                const port = this._createPortFromJSON(p, "input");
                if (port) {
                    port.id = p.id;
                    this.inputs.push(port);
                }
            }
        } else {
            for (let i = 0; i < (data.numInputs || 0); i++) this.addInput();
        }

        // Restore output ports
        if (data.outputPorts) {
            for (const p of data.outputPorts) {
                const port = this._createPortFromJSON(p, "output");
                if (port) {
                    port.id = p.id;
                    this.outputs.push(port);
                }
            }
        } else {
            for (let i = 0; i < (data.numOutputs || 0); i++) this.addOutput();
        }

        // Restore param inputs
        if (data.paramInputs) {
            for (const p of data.paramInputs) {
                const port = new ParamPort(this, "input", p.index);
                port.id = p.id;
                this.paramInputs.push(port);
            }
        }

        // Restore param outputs
        if (data.paramOutputs) {
            for (const p of data.paramOutputs) {
                const port = new ParamPort(this, "output", p.index);
                port.id = p.id;
                this.paramOutputs.push(port);
            }
        }

        if (data.activation) this.activation = data.activation;
        if (data.numNeurons) this.numNeurons = data.numNeurons;
        if (data.bias !== undefined) this.bias = data.bias;
        if (data.hasBias !== undefined) this.hasBias = data.hasBias;
        this.updatePorts();
    }

    _createPortFromJSON(p, type) {
        const kind = p.portKind || "data";
        let port;
        switch (kind) {
            case "multi":
                port = new MultiPort(this, type, p.index, p.subType || null);
                break;
            case "role":
                port = new RolePort(this, type, p.index, p.role || null);
                break;
            case "param":
                port = new ParamPort(this, type, p.index);
                break;
            default:
                port = new DataPort(this, type, p.index, p.subType || null);
        }
        port.id = p.id;
        if (p.activationPhases) {
            port.activationPhases = p.activationPhases;
        } else {
            // fallback: set defaults based on node type (we'll have a helper)
            port.activationPhases = this._getDefaultPhasesForPort(port);
        }
        return port;
    }

    getPropertiesHTML() {
        return "";
    }
    validateConnections(incomingCount) {
        return [];
    }
    _emptyShapes() {
        return this.outputs.map(() => ({
            shape: null,
            dtype: "float32",
            known: false,
            symbolic: false,
        }));
    }

    _makeShapes(shape, symbolic, known) {
        return this.outputs.map(() => ({
            shape,
            dtype: "float32",
            known: !!known,
            symbolic: !!symbolic,
        }));
    }
    _getAllInputShapeObjs() {
        const shapes = [];
        for (const port of this.inputs) {
            if (port instanceof MultiPort && port._incomingShapes) {
                // Return all incoming shapes for MultiPort
                for (const s of port._incomingShapes) {
                    shapes.push(s);
                }
            } else {
                const link = SketchMod.links.find((l) => l.to === port);
                if (link && link.from.shape && link.from.shape.shape) {
                    shapes.push(link.from.shape);
                }
            }
        }
        return shapes;
    }

    _getFirstInputShapeObj() {
        for (const port of this.inputs) {
            const link = SketchMod.links.find((l) => l.to === port);
            if (link && link.from.shape && link.from.shape.shape) {
                return link.from.shape;
            }
        }
        return null;
    }
    _getShapeSummaryHTML() {
        let html = "";

        if (this.inputs.length > 0) {
            html += '<div class="prop-group"><label>Input Shapes</label>';
            for (let i = 0; i < this.inputs.length; i++) {
                const port = this.inputs[i];

                if (
                    port instanceof MultiPort &&
                    port._incomingShapes &&
                    port._incomingShapes.length > 0
                ) {
                    // Show all incoming shapes
                    for (let j = 0; j < port._incomingShapes.length; j++) {
                        const s = port._incomingShapes[j];
                        const shapeStr = "(" + s.shape.join(", ") + ")";
                        const color = s.known
                            ? "var(--accent)"
                            : "var(--text-secondary)";
                        html += `<p class="prop-hint" style="font-family: monospace; color: ${color}; font-size: 0.8rem;">
                        Port ${i + 1}.${j + 1}: ${shapeStr}${s.symbolic ? " (abstract)" : ""}
                    </p>`;
                    }
                } else {
                    const shapeText = port.shapeDisplay();
                    const color =
                        port.hasShape() && port.shape.known
                            ? "var(--accent)"
                            : "var(--text-secondary)";
                    html += `<p class="prop-hint" style="font-family: monospace; color: ${color}; font-size: 0.8rem;">
                    Port ${i + 1}: ${shapeText}
                </p>`;
                }
            }
            html += "</div>";
        }

        // Output ports
        if (this.outputs.length > 0) {
            html += '<div class="prop-group"><label>Output Shapes</label>';
            for (let i = 0; i < this.outputs.length; i++) {
                const port = this.outputs[i];
                const shapeText = port.shapeDisplay();
                const color =
                    port.hasShape() && port.shape.known
                        ? "var(--accent)"
                        : "var(--text-secondary)";
                html += `<p class="prop-hint" style="font-family: monospace; color: ${color}; font-size: 0.8rem;">
                Port ${i + 1}: ${shapeText}
            </p>`;
            }
            html += "</div>";
        }

        return html;
    }

    _updateNodeBias(input) {
        if (this.selectedNodes.length !== 1) return;
        const node = this.selectedNodes[0];
        if (!node.hasBias) return;
        this._saveUndoState();
        node.bias = parseFloat(input.value) || 0;
        this._saveToSession();
    }
}

// ========== NODE FACTORY ==========
class RectNode extends BaseNode {
    // For rectangular nodes (Layer, ColumnSelect, RowSelect, Normalize, DimSelect, InputData, Output)
    constructor(id, x, y, type, width, height) {
        super(id, x, y, type);
        this.width = width;
        this.height = height;
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
        const vh = this.height / 2 + 8;

        // Data input ports on left
        this.inputs.forEach((p, i) => {
            p.x = this.x - hw;
            p.y =
                this.y -
                this.height / 2 +
                (this.height / (this.inputs.length + 1)) * (i + 1);
        });

        // Data output ports on right
        this.outputs.forEach((p, i) => {
            p.x = this.x + hw;
            p.y =
                this.y -
                this.height / 2 +
                (this.height / (this.outputs.length + 1)) * (i + 1);
        });

        // Param output ports on top
        this.paramOutputs.forEach((p, i) => {
            p.x =
                this.x -
                this.width / 2 +
                (this.width / (this.paramOutputs.length + 1)) * (i + 1);
            p.y = this.y - vh;
        });

        // Param input ports on bottom
        this.paramInputs.forEach((p, i) => {
            p.x =
                this.x -
                this.width / 2 +
                (this.width / (this.paramInputs.length + 1)) * (i + 1);
            p.y = this.y + vh;
        });
    }

    draw(ctx, selected) {
        const color = SketchMod._getNodeColor();
        const x = this.x - this.width / 2;
        const y = this.y - this.height / 2;

        // Error / Warning outlines
        if (SketchMod.errorNodeIds.has(this.id)) {
            ctx.beginPath();
            ctx.roundRect(x - 3, y - 3, this.width + 6, this.height + 6, 10);
            ctx.fillStyle = "rgba(239, 68, 68, 0.15)";
            ctx.fill();
            ctx.strokeStyle = "#ef4444";
            ctx.lineWidth = 2;
            ctx.stroke();
        } else if (SketchMod.warningNodeIds.has(this.id)) {
            ctx.beginPath();
            ctx.roundRect(x - 3, y - 3, this.width + 6, this.height + 6, 10);
            ctx.fillStyle = "rgba(245, 158, 11, 0.1)";
            ctx.fill();
            ctx.strokeStyle = "#f59e0b";
            ctx.lineWidth = 2;
            ctx.stroke();
        }

        // Selection glow
        if (selected) {
            ctx.beginPath();
            ctx.roundRect(x - 1, y - 1, this.width + 2, this.height + 2, 8);
            ctx.fillStyle = "var(--accent-glow)";
            ctx.fill();
        }

        // Main body
        ctx.beginPath();
        ctx.roundRect(x, y, this.width, this.height, 7);
        ctx.fillStyle = color.fill;
        ctx.fill();
        ctx.strokeStyle = selected ? "#ffffff" : color.stroke;
        ctx.lineWidth = selected ? 2.5 : 1.5;
        ctx.stroke();

        // Show‑All outline (drawn on top, never throws)
        if (SketchMod._showAllNodes && SketchMod._showAllNodes.has(this)) {
            try {
                const phases = SketchMod._showAllNodes.get(this);
                const sc = SketchMod._getShowAllColor(phases);
                ctx.beginPath();
                ctx.roundRect(
                    x - 4,
                    y - 4,
                    this.width + 8,
                    this.height + 8,
                    10,
                );
                ctx.strokeStyle = sc;
                ctx.lineWidth = 3;
                ctx.shadowColor = "transparent";
                ctx.shadowBlur = 0;
                ctx.stroke();
            } catch (e) {}
        }

        // Single‑phase highlight
        if (
            SketchMod._highlightPhaseNodes &&
            SketchMod._highlightPhaseNodes.has(this)
        ) {
            ctx.beginPath();
            ctx.roundRect(x - 4, y - 4, this.width + 8, this.height + 8, 10);
            ctx.strokeStyle = "#4ade80";
            ctx.lineWidth = 3;
            ctx.shadowColor = "transparent";
            ctx.shadowBlur = 0;
            ctx.stroke();
        }

        // Label
        ctx.fillStyle = "#ffffff";
        ctx.font = "bold 13px Inter, sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        this.drawLabel(ctx);
    }
    drawLabel(ctx) {
        ctx.fillText("?", this.x, this.y);
    }
}

class CircleNode extends BaseNode {
    // For circle nodes (Neuron)
    constructor(id, x, y, type, radius) {
        super(id, x, y, type);
        this.radius = radius;
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

        // Data input ports on left
        this.inputs.forEach((p, i) => {
            const a =
                this.inputs.length === 1
                    ? Math.PI
                    : Math.PI - 0.6 + (i / (this.inputs.length - 1)) * 1.2;
            p.x = this.x + Math.cos(a) * r;
            p.y = this.y + Math.sin(a) * r;
        });

        // Data output ports on right
        this.outputs.forEach((p, i) => {
            const a =
                this.outputs.length === 1
                    ? 0
                    : -0.6 + (i / (this.outputs.length - 1)) * 1.2;
            p.x = this.x + Math.cos(a) * r;
            p.y = this.y + Math.sin(a) * r;
        });

        // Param output ports on top
        this.paramOutputs.forEach((p, i) => {
            const a =
                this.paramOutputs.length === 1
                    ? -Math.PI / 2
                    : -Math.PI / 2 -
                      0.4 +
                      (i / (this.paramOutputs.length - 1)) * 0.8;
            p.x = this.x + Math.cos(a) * r;
            p.y = this.y + Math.sin(a) * r;
        });

        // Param input ports on bottom
        this.paramInputs.forEach((p, i) => {
            const a =
                this.paramInputs.length === 1
                    ? Math.PI / 2
                    : Math.PI / 2 -
                      0.4 +
                      (i / (this.paramInputs.length - 1)) * 0.8;
            p.x = this.x + Math.cos(a) * r;
            p.y = this.y + Math.sin(a) * r;
        });
    }

    draw(ctx, selected) {
        const color = SketchMod._getNodeColor();

        if (SketchMod.errorNodeIds.has(this.id)) {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.radius + 4, 0, Math.PI * 2);
            ctx.fillStyle = "rgba(239, 68, 68, 0.15)";
            ctx.fill();
            ctx.strokeStyle = "#ef4444";
            ctx.lineWidth = 2;
            ctx.stroke();
        } else if (SketchMod.warningNodeIds.has(this.id)) {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.radius + 4, 0, Math.PI * 2);
            ctx.fillStyle = "rgba(245, 158, 11, 0.1)";
            ctx.fill();
            ctx.strokeStyle = "#f59e0b";
            ctx.lineWidth = 2;
            ctx.stroke();
        }

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

        if (SketchMod._showAllNodes && SketchMod._showAllNodes.has(this)) {
            try {
                const phases = SketchMod._showAllNodes.get(this);
                const sc = SketchMod._getShowAllColor(phases);
                ctx.beginPath();
                ctx.arc(this.x, this.y, this.radius + 5, 0, Math.PI * 2);
                ctx.strokeStyle = sc;
                ctx.lineWidth = 3;
                ctx.shadowColor = "transparent";
                ctx.shadowBlur = 0;
                ctx.stroke();
            } catch (e) {}
        }

        if (
            SketchMod._highlightPhaseNodes &&
            SketchMod._highlightPhaseNodes.has(this)
        ) {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.radius + 5, 0, Math.PI * 2);
            ctx.strokeStyle = "#4ade80";
            ctx.lineWidth = 3;
            ctx.shadowColor = "transparent";
            ctx.shadowBlur = 0;
            ctx.stroke();
        }

        ctx.fillStyle = "#ffffff";
        ctx.font = "bold 15px Inter, sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        this.drawLabel(ctx);
    }
    drawLabel(ctx) {
        ctx.fillText("?", this.x, this.y);
    }
}

// ========== NEURON ==========
class NeuronNode extends CircleNode {
    constructor(id, x, y) {
        super(id, x, y, "neuron", 28);
        this.activation = "relu";
        this.maxInputs = 1;
        this.minInputs = 1;
        this.maxOutputs = 1;
        this.minOutputs = 1;
        this.hasBias = true;
        this.bias = 0;

        this.inputs.push(new MultiPort(this, "input", 0, null));
        this.addOutput();
        this.inputs[0].activationPhases = ["training", "evaluation"];
        this.outputs[0].activationPhases = ["training", "evaluation"];
        this.updatePorts();
    }

    canAddInput() {
        return false;
    }
    canRemoveInput() {
        return false;
    }

    drawLabel(ctx) {
        ctx.fillText("N", this.x, this.y);
    }
    validateConnections(incomingCount) {
        const errors = [];
        if (incomingCount < 1) {
            errors.push(`${this.type}: requires at least 1 input connection`);
        }
        return errors;
    }

    computeOutputShapes() {
        const allShapes = this._getAllInputShapeObjs();
        if (allShapes.length === 0) return this._emptyShapes();

        const batchDim = allShapes[0].shape[0];
        let symbolic = allShapes[0].symbolic;
        let known = allShapes[0].known;

        for (const s of allShapes) {
            if (s.symbolic) symbolic = true;
            if (!s.known) known = false;
        }

        return this._makeShapes(
            [new ShapeExpr(batchDim), new ShapeExpr(1)],
            symbolic,
            known,
        );
    }

    getPropertiesHTML() {
        return (
            this._getShapeSummaryHTML() +
            this._activationSelect() +
            `<div class="prop-group">
            <label>Bias</label>
            <input type="number" id="prop-bias" class="prop-input" value="${this.bias}" step="0.01"
                   onchange="SketchMod._updateNodeBias(this)">
            <p class="prop-hint">Bias value (scalar)</p>
        </div>`
        );
    }
    _activationSelect() {
        return `<div class="prop-group"><label>Activation</label><select id="prop-activation" class="prop-select">
            <option value="relu" ${this.activation === "relu" ? "selected" : ""}>ReLU</option>
            <option value="sigmoid" ${this.activation === "sigmoid" ? "selected" : ""}>Sigmoid</option>
            <option value="tanh" ${this.activation === "tanh" ? "selected" : ""}>Tanh</option>
        </select></div>`;
    }
}

// ========== LAYER ==========
class LayerNode extends RectNode {
    constructor(id, x, y) {
        super(id, x, y, "layer", 110, 65);
        this.numNeurons = 64;
        this.activation = "relu";
        this.maxInputs = 1;
        this.minInputs = 1;
        this.maxOutputs = 1;
        this.minOutputs = 1;
        this.hasBias = true;
        this.bias = 0;

        this.inputs.push(new MultiPort(this, "input", 0, null));
        this.addOutput();
        this.inputs[0].activationPhases = ["training", "evaluation"];
        this.outputs[0].activationPhases = ["training", "evaluation"];
        this.updatePorts();
    }

    canAddInput() {
        return false;
    }
    canRemoveInput() {
        return false;
    }
    drawLabel(ctx) {
        ctx.fillText(this.numNeurons + "", this.x, this.y - 9);
        ctx.font = "11px Inter, sans-serif";
        ctx.fillText("Layer", this.x, this.y + 12);
    }
    validateConnections(incomingCount) {
        const errors = [];
        if (incomingCount < 1) {
            errors.push(`${this.type}: requires at least 1 input connection`);
        }
        return errors;
    }
    computeOutputShapes() {
        const allShapes = this._getAllInputShapeObjs();
        if (allShapes.length === 0) return this._emptyShapes();

        const batchDim = allShapes[0].shape[0];
        let symbolic = allShapes[0].symbolic;
        let known = allShapes[0].known;

        for (const s of allShapes) {
            if (s.symbolic) symbolic = true;
            if (!s.known) known = false;
        }

        return this._makeShapes(
            [new ShapeExpr(batchDim), new ShapeExpr(this.numNeurons)],
            symbolic,
            known,
        );
    }
    getPropertiesHTML() {
        return (
            this._getShapeSummaryHTML() +
            `${this._activationSelect()}
            <div class="prop-group"><label>Neurons</label><input type="number" id="prop-size" class="prop-input" value="${this.numNeurons}" min="1" max="4096"></div>
        <div class="prop-group">
            <label>Bias Initializer</label>
            <input type="number" id="prop-bias" class="prop-input" value="${this.bias}" step="0.01"
                   onchange="SketchMod._updateNodeBias(this)">
            <p class="prop-hint">Initial value for bias vector (${this.numNeurons},)</p>
        </div>
        `
        );
    }
    _activationSelect() {
        return NeuronNode.prototype._activationSelect.call(this);
    }
}

// ========== INPUT DATA ==========
class InputDataNode extends RectNode {
    constructor(id, x, y) {
        super(id, x, y, "input-data", 100, 55);
        this.datasetId = null;
        this.datasetName = null;
        this.dataShape = null;
        this.maxInputs = 0;
        this.minInputs = 0;
        this.maxOutputs = 1;
        this.minOutputs = 1;
        this.allowedOutputTypes = ["features", "labels"];
        this.addOutput();
        this.outputs[0].activationPhases = ["preprocessing"];
    }
    drawLabel(ctx) {
        ctx.fillText("Input", this.x, this.y);
    }
    computeOutputShapes() {
        let shape = null,
            symbolic = false;
        if (this.dataShape) {
            const cleaned = this.dataShape.replace(/[()]/g, "");
            const parts = cleaned.split(",").map((s) => {
                const n = parseInt(s.trim());
                if (!isNaN(n) && n.toString() === s.trim()) return n;
                symbolic = true;
                return s.trim();
            });
            if (parts.length > 0) shape = parts;
        }
        return this._makeShapes(shape, symbolic, !!shape);
    }
    getPropertiesHTML() {
        return (
            this._getShapeSummaryHTML() +
            `
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
            ${this.datasetId ? `<div class="prop-group"><label>Dataset ID</label><p class="prop-hint" style="font-family: monospace;">${this.datasetId}</p></div>` : ""}
        </div>
        <div class="prop-group">
            <label>Shape</label>
            <input type="text" id="prop-manual-shape" class="prop-input" 
                   placeholder="e.g. (None, 28, 28)" 
                   value="${this.dataShape || ""}"
                   onchange="SketchMod._updateManualShape(this)">
            <p class="prop-hint">You can override the dataset shape manually.</p>
        </div>
    `
        );
    }

    toJSON() {
        const b = super.toJSON();
        return {
            ...b,
            datasetId: this.datasetId,
            datasetName: this.datasetName,
            dataShape: this.dataShape,
            datasetFile: this.datasetFile,
            datasetFormat: this.datasetFormat,
        };
    }
    fromJSON(d) {
        super.fromJSON(d);
        if (d.datasetId) this.datasetId = d.datasetId;
        if (d.datasetName) this.datasetName = d.datasetName;
        if (d.dataShape) this.dataShape = d.dataShape;
        if (d.datasetFile) this.datasetFile = d.datasetFile;
        if (d.datasetFormat) this.datasetFormat = d.datasetFormat;
    }
}

// ========== OUTPUT ==========
class OutputNode extends RectNode {
    constructor(id, x, y) {
        super(id, x, y, "output", 100, 70);
        this.maxInputs = 2;
        this.minInputs = 2;
        this.maxOutputs = 3;
        this.minOutputs = 3;

        // Two inputs: train data (every batch) and test data (final eval)
        this.addInput("train");
        this.addInput("test");

        // Three outputs: loss, prediction, evaluation
        this.outputs.push(new RolePort(this, "output", 0, "loss"));
        this.outputs.push(new RolePort(this, "output", 1, "prediction"));
        this.outputs.push(new RolePort(this, "output", 2, "evaluation"));
        this.inputs[0].activationPhases = ["training"];
        this.inputs[1].activationPhases = ["evaluation"];
        this.outputs[0].activationPhases = ["training"]; // loss
        this.outputs[1].activationPhases = ["evaluation"]; // prediction
        this.outputs[2].activationPhases = ["evaluation"]; // evaluation

        this.outputActivations = {
            loss: "none",
            prediction: "none",
            evaluation: "none",
        };
        this.updatePorts();
    }

    toJSON() {
        const b = super.toJSON();
        return {
            ...b,
            outputActivations: this.outputActivations,
        };
    }

    fromJSON(d) {
        super.fromJSON(d);
        if (d.outputActivations) this.outputActivations = d.outputActivations;
    }

    updatePorts() {
        const hw = this.width / 2 + 8;
        const totalIn = this.inputs.length;
        const totalOut = this.outputs.length;

        // Position all inputs on LEFT
        this.inputs.forEach((p, i) => {
            p.x = this.x - hw;
            p.y =
                this.y -
                this.height / 2 +
                (this.height / (totalIn + 1)) * (i + 1);
        });

        // Position all outputs on RIGHT
        this.outputs.forEach((p, i) => {
            p.x = this.x + hw;
            p.y =
                this.y -
                this.height / 2 +
                (this.height / (totalOut + 1)) * (i + 1);
        });
    }

    drawLabel(ctx) {
        ctx.fillText("Output", this.x, this.y);
    }
    validateConnections(incomingCount) {
        const errors = [];
        if (incomingCount > 1) {
            errors.push(
                `${this.type}: only accepts 1 input connection, but has ${incomingCount}`,
            );
        }
        return errors;
    }
    computeOutputShapes() {
        let foundShape = null;
        for (const inPort of this.inputs) {
            const link = SketchMod.links.find((l) => l.to === inPort);
            if (link && link.from.shape && link.from.shape.shape) {
                foundShape = link.from.shape;
                break;
            }
        }
        if (foundShape) {
            return this.outputs.map(() => ({
                shape: foundShape.shape.map((s) => new ShapeExpr(s)),
                dtype: foundShape.dtype,
                known: foundShape.known,
                symbolic: foundShape.symbolic,
            }));
        }
        return this._emptyShapes();
    }

    canAddOutput() {
        return false;
    }
    canRemoveOutput() {
        return false;
    }
    addOutput() {
        return null;
    }
    removeOutput() {
        return null;
    }

    getPropertiesHTML() {
        let html = this._getShapeSummaryHTML();

        // Input ports legend
        html += `
        <div class="prop-group">
            <label>Input Ports</label>
            <div class="port-legend">
                <span class="port-legend-item">
                    <svg width="10" height="10" viewBox="0 0 10 10">
                        <circle cx="5" cy="5" r="4" fill="#f59e0b" stroke="#1a1d2e" stroke-width="1"/>
                    </svg>
                    train
                </span>
                <span class="port-legend-item">
                    <svg width="10" height="10" viewBox="0 0 10 10">
                        <circle cx="5" cy="5" r="4" fill="#4ade80" stroke="#1a1d2e" stroke-width="1"/>
                    </svg>
                    test
                </span>
            </div>
        </div>
    `;

        // Output ports legend
        html += `
        <div class="prop-group">
            <label>Output Ports</label>
            <div class="port-legend">
                <span class="port-legend-item">
                    <svg width="10" height="10" viewBox="0 0 10 10">
                        <circle cx="5" cy="5" r="4" fill="#53BF9D" stroke="#1a1d2e" stroke-width="1"/>
                    </svg>
                    Loss
                </span>
                <span class="port-legend-item">
                    <svg width="10" height="10" viewBox="0 0 10 10">
                        <circle cx="5" cy="5" r="4" fill="#BD4291" stroke="#1a1d2e" stroke-width="1"/>
                    </svg>
                    Prediction
                </span>
                <span class="port-legend-item">
                    <svg width="10" height="10" viewBox="0 0 10 10">
                        <circle cx="5" cy="5" r="4" fill="#FFC54D" stroke="#1a1d2e" stroke-width="1"/>
                    </svg>
                    Evaluation
                </span>
            </div>
        </div>
    `;

        // Output activation selectors
        const roles = ["prediction", "evaluation"];
        for (const role of roles) {
            const current = this.outputActivations[role] || "none";
            html += `
        <div class="prop-group">
            <label>${role.charAt(0).toUpperCase() + role.slice(1)} Output</label>
            <select class="prop-select" onchange="SketchMod._updateOutputActivation('${role}', this.value)">
                <option value="none" ${current === "none" ? "selected" : ""}>None (raw logits)</option>
                <option value="softmax" ${current === "softmax" ? "selected" : ""}>Softmax (probabilities)</option>
                <option value="argmax" ${current === "argmax" ? "selected" : ""}>Argmax (class indices)</option>
            </select>
        </div>`;
        }

        html += `<p class="prop-hint">Loss port always uses raw logits.</p>`;
        return html;
    }
}
// ========== COLUMN SELECT NODE ==========
class ColumnSelectNode extends RectNode {
    constructor(id, x, y) {
        super(id, x, y, "column-select", 100, 60);
        this.selectedColumns = [];
        this.columnInput = "";
        this.availableColumns = [];
        this.columnCount = 0;
        this.datasetId = null;
        this.maxInputs = 1;
        this.minInputs = 1;
        this.maxOutputs = 1;
        this.minOutputs = 1;
        this.addInput();
        this.addOutput();
        this.inputs[0].activationPhases = ["preprocessing"];
        this.outputs[0].activationPhases = ["preprocessing"];
    }

    drawLabel(ctx) {
        const label =
            this.selectedColumns.length > 0
                ? this.selectedColumns.length + " cols"
                : "Columns";
        ctx.fillText(label, this.x, this.y);
    }
    validateConnections(incomingCount) {
        const errors = [];
        if (incomingCount > 1) {
            errors.push(
                `${this.type}: only accepts 1 input connection, but has ${incomingCount}`,
            );
        }
        return errors;
    }
    computeOutputShapes() {
        const s = this._getFirstInputShapeObj();
        if (!s) return this._emptyShapes();

        const count =
            this.selectedColumns.length > 0
                ? this.selectedColumns.length
                : this.columnInput
                  ? this._countFromInput()
                  : s.shape[1];

        return this._makeShapes(
            [new ShapeExpr(s.shape[0]), new ShapeExpr(count)],
            s.symbolic,
            this.selectedColumns.length > 0,
        );
    }

    _countFromInput() {
        const indices = SketchMod._parseColumnInput(
            this.columnInput,
            this.columnCount - 1,
        );
        return indices.length || null;
    }

    toJSON() {
        return {
            ...super.toJSON(),
            selectedColumns: this.selectedColumns,
            columnInput: this.columnInput,
            availableColumns: this.availableColumns,
            columnCount: this.columnCount,
            datasetId: this.datasetId,
        };
    }
    fromJSON(d) {
        super.fromJSON(d);
        if (d.selectedColumns) this.selectedColumns = d.selectedColumns;
        if (d.columnInput) this.columnInput = d.columnInput;
        if (d.availableColumns) this.availableColumns = d.availableColumns;
        if (d.columnCount) this.columnCount = d.columnCount;
        if (d.datasetId) this.datasetId = d.datasetId;
    }

    getPropertiesHTML() {
        const hasDataset = this.columnCount > 0;

        return (
            this._getShapeSummaryHTML() +
            `
        ${
            hasDataset
                ? `
        <div class="prop-group">
            <label>Columns</label>
            <p class="prop-hint">${this.columnCount} column${this.columnCount !== 1 ? "s" : ""} available</p>
            <div class="checkbox-group" id="columnCheckboxes" style="max-height: 120px;">
                ${this.availableColumns
                    .map(
                        (name, i) => `
                    <label class="checkbox-label">
                        <input type="checkbox" value="${i}" 
                               ${this.selectedColumns.includes(i) ? "checked" : ""}
                               onchange="SketchMod._updateColumnSelect(this)">
                        ${i}: ${name}
                    </label>
                `,
                    )
                    .join("")}
            </div>
        </div>
        `
                : ""
        }
        <div class="prop-group">
            <label>Custom Selection</label>
            <input type="text" id="prop-column-input" class="prop-input" 
                   placeholder="e.g. 0:3, 5, 7" 
                   value="${this.columnInput}"
                   onchange="SketchMod._updateColumnInput(this)">
            <p class="prop-hint">Python slice notation: <code>start:end</code>, single indices, comma-separated</p>
            <p class="prop-hint">Python negative indices supported: <code>-1</code> = last column, <code>0:-1</code> = all except last</p>
        </div>
        <div class="prop-group">
            <label>Selected</label>
            <p class="prop-hint" id="columnPreview">
                ${
                    this.selectedColumns.length > 0
                        ? this.selectedColumns.join(", ") +
                          ` (${this.selectedColumns.length} columns)`
                        : "None selected"
                }
            </p>
        </div>
    `
        );
    }
}
// ========== ROW SELECT NODE ==========
class RowSelectNode extends RectNode {
    constructor(id, x, y) {
        super(id, x, y, "row-select", 100, 60);
        this.method = "first-n";
        this.value = "100";
        this.randomSeed = 42;
        this.rowCount = 0;
        this.maxInputs = 1;
        this.minInputs = 1;
        this.maxOutputs = 1;
        this.minOutputs = 1;
        this.addInput();
        this.addOutput();
        this.inputs[0].activationPhases = ["preprocessing"];
        this.outputs[0].activationPhases = ["preprocessing"];
    }

    drawLabel(ctx) {
        const label = this.rowCount > 0 ? this.rowCount + " rows" : "Rows";
        ctx.fillText(label, this.x, this.y);
    }
    validateConnections(incomingCount) {
        const errors = [];
        if (incomingCount > 1) {
            errors.push(
                `${this.type}: only accepts 1 input connection, but has ${incomingCount}`,
            );
        }
        return errors;
    }
    computeOutputShapes() {
        const s = this._getFirstInputShapeObj();
        if (!s) return this._emptyShapes();

        const rows =
            this.rowCount > 0 ? new ShapeExpr(this.rowCount) : s.shape[0];

        return this._makeShapes(
            [rows, ...s.shape.slice(1).map((x) => new ShapeExpr(x))],
            s.symbolic,
            this.rowCount > 0,
        );
    }

    _computeRowCount() {
        const v = this.value.trim();
        if (!v) return 0;

        switch (this.method) {
            case "first-n":
                return parseInt(v) || 0;
            case "random":
                return parseInt(v) || 0;
            case "slice":
                const parts = v.split(":");
                if (parts.length === 2) {
                    const start = parseInt(parts[0]) || 0;
                    const end = parseInt(parts[1]) || 0;
                    return Math.max(0, end - start);
                }
                return 0;
            case "indices":
                return v
                    .split(",")
                    .filter((s) => s.trim() && !isNaN(parseInt(s.trim())))
                    .length;
            default:
                return 0;
        }
    }
    toJSON() {
        return {
            ...super.toJSON(),
            method: this.method,
            value: this.value,
            randomSeed: this.randomSeed,
            rowCount: this.rowCount,
        };
    }
    fromJSON(d) {
        super.fromJSON(d);
        if (d.method) this.method = d.method;
        if (d.value) this.value = d.value;
        if (d.randomSeed) this.randomSeed = d.randomSeed;
        if (d.rowCount) this.rowCount = d.rowCount;
    }

    getPropertiesHTML() {
        const methods = [
            { value: "first-n", label: "First N rows" },
            { value: "random", label: "Random sample" },
            { value: "slice", label: "Slice (start:end)" },
            { value: "indices", label: "Specific indices" },
        ];

        return (
            this._getShapeSummaryHTML() +
            `
            <div class="prop-group">
                <label>Method</label>
                <select id="prop-row-method" class="prop-select" onchange="SketchMod._updateRowMethod(this)">
                    ${methods
                        .map(
                            (m) => `
                        <option value="${m.value}" ${this.method === m.value ? "selected" : ""}>${m.label}</option>
                    `,
                        )
                        .join("")}
                </select>
            </div>
            <div class="prop-group">
                <label>Value</label>
                <input type="text" id="prop-row-value" class="prop-input" 
                       value="${this.value}"
                       placeholder="${this._getPlaceholder()}"
                       onchange="SketchMod._updateRowValue(this)">
                <p class="prop-hint">${this._getHint()}</p>
            </div>
            ${
                this.method === "random"
                    ? `
            <div class="prop-group">
                <label>Random Seed</label>
                <input type="number" id="prop-row-seed" class="prop-input" value="${this.randomSeed}"
                       onchange="SketchMod._updateRowSeed(this)">
            </div>
            `
                    : ""
            }
            <div class="prop-group">
                <label>Preview</label>
                <p class="prop-hint">${this.rowCount > 0 ? `~${this.rowCount} rows` : "Enter a value"}</p>
            </div>
        `
        );
    }

    _getPlaceholder() {
        switch (this.method) {
            case "first-n":
                return "100";
            case "random":
                return "100";
            case "slice":
                return "0:500";
            case "indices":
                return "0, 5, 10, 15";
            default:
                return "";
        }
    }

    _getHint() {
        switch (this.method) {
            case "first-n":
                return "Number of rows from the start";
            case "random":
                return "Number of rows to sample randomly";
            case "slice":
                return "Python slice: start:end";
            case "indices":
                return "Comma-separated indices";
            default:
                return "";
        }
    }
}
// ========== DIM SELECT NODE ==========
class DimSelectNode extends RectNode {
    constructor(id, x, y) {
        super(id, x, y, "dim-select", 110, 70);
        this.inputShape = null;
        this.dimSelections = ["", ""];
        this.computedIndices = [];
        this.maxInputs = 1;
        this.minInputs = 1;
        this.maxOutputs = 1;
        this.minOutputs = 1;
        this.addInput();
        this.addOutput();
        this.inputs[0].activationPhases = ["preprocessing"];
        this.outputs[0].activationPhases = ["preprocessing"];
    }

    drawLabel(ctx) {
        const dims = this.dimSelections.length;
        const used = this.dimSelections.filter((d) => d && d !== ":").length;
        ctx.fillText(dims + "D", this.x, this.y - 6);
        ctx.font = "10px Inter, sans-serif";
        ctx.fillText(
            used > 0 ? used + " sliced" : "Select",
            this.x,
            this.y + 12,
        );
    }
    validateConnections(incomingCount) {
        const errors = [];
        if (incomingCount > 1) {
            errors.push(
                `${this.type}: only accepts 1 input connection, but has ${incomingCount}`,
            );
        }
        return errors;
    }

    computeOutputShapes() {
        const s = this._getFirstInputShapeObj();
        if (!s) return this._emptyShapes();
        const outShape = [];
        for (let i = 0; i < this.dimSelections.length; i++) {
            const indices = this._parseDimInput(
                this.dimSelections[i],
                typeof s.shape[i] === "number" ? s.shape[i] - 1 : null,
            );
            outShape.push(
                indices.length > 0 ? indices.length : s.shape[i] || 1,
            );
        }
        const allEmpty = this.dimSelections.every(
            (d) => !d || d === ":" || d.trim() === "",
        );
        return this._makeShapes(outShape, s.symbolic, !allEmpty);
    }

    _parseDimInput(input, maxIndex) {
        if (!input || input.trim() === "" || input.trim() === ":") {
            if (maxIndex !== null && maxIndex >= 0) {
                const result = [];
                for (let i = 0; i <= maxIndex; i++) result.push(i);
                return result;
            }
            return [];
        }

        const clean = input.replace(/\s+/g, "");
        if (!clean) return [];

        const indices = new Set();
        const parts = clean.split(",");

        for (const part of parts) {
            if (!part) continue;

            if (part.includes(":")) {
                const colonParts = part.split(":");
                if (colonParts.length === 2) {
                    const startStr = colonParts[0];
                    const endStr = colonParts[1];
                    if (startStr === "" && endStr === "") {
                        // ":" → all
                        if (maxIndex !== null) {
                            for (let i = 0; i <= maxIndex; i++) indices.add(i);
                        }
                    } else if (startStr === "") {
                        // ":N" → 0 to N
                        const end = parseInt(endStr);
                        if (!isNaN(end)) {
                            for (
                                let i = 0;
                                i <= end &&
                                (maxIndex === null || i <= maxIndex);
                                i++
                            )
                                indices.add(i);
                        }
                    } else if (endStr === "") {
                        // "N:" → N to max
                        const start = parseInt(startStr);
                        if (!isNaN(start) && maxIndex !== null) {
                            for (let i = start; i <= maxIndex; i++)
                                indices.add(i);
                        }
                    } else {
                        const start = parseInt(startStr) || 0;
                        const end = parseInt(endStr);
                        if (!isNaN(end)) {
                            for (
                                let i = start;
                                i <= end &&
                                (maxIndex === null || i <= maxIndex);
                                i++
                            )
                                indices.add(i);
                        }
                    }
                } else if (colonParts.length === 3) {
                    // "::step"
                    const step = parseInt(colonParts[2]) || 1;
                    if (maxIndex !== null) {
                        for (let i = 0; i <= maxIndex; i += step)
                            indices.add(i);
                    }
                }
            } else {
                const idx = parseInt(part);
                if (!isNaN(idx) && idx >= 0) indices.add(idx);
            }
        }

        return [...indices].sort((a, b) => a - b);
    }
    _computeOutputShape() {
        const shape = [];
        for (let i = 0; i < this.dimSelections.length; i++) {
            const indices = this._parseDimInput(
                this.dimSelections[i],
                this.inputShape ? this.inputShape[i] - 1 : null,
            );
            shape.push(
                indices.length > 0
                    ? indices.length
                    : this.inputShape
                      ? this.inputShape[i]
                      : "?",
            );
        }
        return shape;
    }
    toJSON() {
        return {
            ...super.toJSON(),
            inputShape: this.inputShape,
            dimSelections: this.dimSelections,
            computedIndices: this.computedIndices,
        };
    }
    fromJSON(d) {
        super.fromJSON(d);
        if (d.inputShape) this.inputShape = d.inputShape;
        if (d.dimSelections) this.dimSelections = d.dimSelections;
        if (d.computedIndices) this.computedIndices = d.computedIndices;
    }

    getPropertiesHTML() {
        const shapeKnown = this.inputShape && this.inputShape.length > 0;
        const shapePreview = this._computeOutputShape();

        let dimRows = "";
        for (let i = 0; i < this.dimSelections.length; i++) {
            const dimSize =
                shapeKnown && this.inputShape[i] !== undefined
                    ? this.inputShape[i]
                    : "?";
            dimRows += `
                <div class="dim-row">
                    <span class="dim-label">Dim ${i} (${dimSize})</span>
                    <input type="text" class="prop-input dim-input" 
                           value="${this.dimSelections[i] || ""}"
                           placeholder=":"
                           data-dim="${i}"
                           onchange="SketchMod._updateDimSelect(this)">
                    <button class="dim-remove" data-dim="${i}" 
                            onclick="SketchMod._removeDimRow(this)" 
                            title="Remove dimension">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="18" y1="6" x2="6" y2="18"/>
                            <line x1="6" y1="6" x2="18" y2="18"/>
                        </svg>
                    </button>
                </div>
            `;
        }

        return (
            this._getShapeSummaryHTML() +
            `
            ${
                shapeKnown
                    ? `
            <div class="prop-group">
                <label>Input Shape</label>
                <p class="prop-hint">(${this.inputShape.join(", ")})</p>
            </div>
            `
                    : `
            <div class="prop-group">
                <label>Input Shape</label>
                <p class="prop-hint">Unknown — connect data first</p>
            </div>
            `
            }
            <div class="prop-group">
                <label>Dimensions</label>
                <div class="dim-list" id="dimList">
                    ${dimRows}
                </div>
                <button class="prop-btn prop-btn-add" onclick="SketchMod._addDimRow()">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="12" y1="5" x2="12" y2="19"/>
                        <line x1="5" y1="12" x2="19" y2="12"/>
                    </svg>
                    Add Dimension
                </button>
            </div>
            <div class="prop-group">
                <label>Output Shape</label>
                <p class="prop-hint">(${shapePreview.join(", ")})</p>
            </div>
        `
        );
    }
}
// ========== TRAIN/TEST SPLIT NODE ==========
class TrainTestSplitNode extends RectNode {
    constructor(id, x, y) {
        super(id, x, y, "train-test", 110, 70);
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
        this.outputs[0].activationPhases = ["training"];
        this.outputs[1].activationPhases = ["evaluation"];
    }

    drawLabel(ctx) {
        ctx.fillText("Train/Test", this.x, this.y - 8);
        ctx.font = "10px Inter, sans-serif";
        ctx.fillText(
            `${Math.round(this.trainRatio * 100)}/${Math.round(this.testRatio * 100)}`,
            this.x,
            this.y + 10,
        );
    }
    validateConnections(incomingCount) {
        const errors = [];
        if (incomingCount > 1) {
            errors.push(
                `${this.type}: only accepts 1 input connection, but has ${incomingCount}`,
            );
        }
        return errors;
    }
    computeOutputShapes() {
        const s = this._getFirstInputShapeObj();
        if (!s) return this._emptyShapes();

        const batch = s.shape[0];
        const trainRows = batch.isNumber()
            ? new ShapeExpr(Math.floor(batch.toNumber() * this.trainRatio))
            : batch.multiply(this.trainRatio);
        const testRows = batch.isNumber()
            ? batch.subtract(trainRows)
            : batch.multiply(this.testRatio);

        return [
            {
                shape: [
                    trainRows,
                    ...s.shape.slice(1).map((x) => new ShapeExpr(x)),
                ],
                dtype: "float32",
                known: true,
                symbolic: s.symbolic || !batch.isNumber(),
            },
            {
                shape: [
                    testRows,
                    ...s.shape.slice(1).map((x) => new ShapeExpr(x)),
                ],
                dtype: "float32",
                known: true,
                symbolic: s.symbolic || !batch.isNumber(),
            },
        ];
    }

    toJSON() {
        return {
            ...super.toJSON(),
            trainRatio: this.trainRatio,
            testRatio: this.testRatio,
            randomSeed: this.randomSeed,
        };
    }
    fromJSON(d) {
        super.fromJSON(d);
        if (d.trainRatio) this.trainRatio = d.trainRatio;
        if (d.testRatio) this.testRatio = d.testRatio;
        if (d.randomSeed) this.randomSeed = d.randomSeed;
    }

    getPropertiesHTML() {
        return (
            this._getShapeSummaryHTML() +
            `
            <div class="prop-group">
                <label>Output Ports</label>
                <div class="port-legend">
                    <span class="port-legend-item">
                        <svg width="10" height="10" viewBox="0 0 10 10">
                            <circle cx="5" cy="5" r="4" fill="#f59e0b" stroke="#1a1d2e" stroke-width="1"/>
                        </svg>
                        train
                    </span>
                    <span class="port-legend-item">
                        <svg width="10" height="10" viewBox="0 0 10 10">
                            <circle cx="5" cy="5" r="4" fill="#4ade80" stroke="#1a1d2e" stroke-width="1"/>
                        </svg>
                        test
                    </span>
                </div>
            </div>
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
        `
        );
    }
}

// ========== NORMALIZE ==========
class NormalizeNode extends RectNode {
    constructor(id, x, y) {
        super(id, x, y, "normalize", 100, 55);
        this.method = "standard";
        this.maxInputs = 1;
        this.minInputs = 1;
        this.maxOutputs = 1;
        this.minOutputs = 1;
        this.maxParamInputs = 1;
        this.minParamInputs = 0;
        this.maxParamOutputs = 1;
        this.minParamOutputs = 0;
        this.addInput();
        this.addOutput();
        this.inputs[0].activationPhases = ["preprocessing"];
        this.outputs[0].activationPhases = ["preprocessing"];
    }
    drawLabel(ctx) {
        ctx.fillText(
            this.method === "standard" ? "Standard" : "MinMax",
            this.x,
            this.y - 6,
        );
        ctx.font = "10px Inter, sans-serif";
        ctx.fillText("Normalize", this.x, this.y + 12);
    }
    validateConnections(incomingCount) {
        const errors = [];
        if (incomingCount > 1) {
            errors.push(
                `${this.type}: only accepts 1 input connection, but has ${incomingCount}`,
            );
        }
        return errors;
    }
    computeOutputShapes() {
        const s = this._getFirstInputShapeObj();
        if (!s) return this._emptyShapes();
        return this._makeShapes([...s.shape], s.symbolic, true);
    }
    toJSON() {
        return { ...super.toJSON(), method: this.method };
    }
    fromJSON(d) {
        super.fromJSON(d);
        if (d.method) this.method = d.method;
    }
    getPropertiesHTML() {
        const hasParamIn = this.paramInputs.length > 0;
        const hasParamOut = this.paramOutputs.length > 0;

        let paramHTML = "";
        if (hasParamIn || hasParamOut) {
            paramHTML = `
        <div class="prop-group">
            <label>Param Ports</label>
            <div class="port-legend">`;
            if (hasParamIn) {
                paramHTML += `
                <span class="port-legend-item">
                    <svg width="10" height="10" viewBox="0 0 10 10">
                        <polygon points="5,1 9,5 5,9 1,5" fill="#fbbf24" stroke="#1a1d2e" stroke-width="1"/>
                    </svg>
                    Param Input — receives fitted statistics
                </span>`;
            }
            if (hasParamOut) {
                paramHTML += `
                <span class="port-legend-item">
                    <svg width="10" height="10" viewBox="0 0 10 10">
                        <polygon points="5,1 9,5 5,9 1,5" fill="#38bdf8" stroke="#1a1d2e" stroke-width="1"/>
                    </svg>
                    Param Output — passes fitted statistics
                </span>`;
            }
            paramHTML += `
            </div>
        </div>`;
        }

        return `
        ${this._getShapeSummaryHTML()}
        ${paramHTML}
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
// ========== CONV2D NODE ==========
class Conv2DNode extends RectNode {
    constructor(id, x, y) {
        super(id, x, y, "conv2d", 120, 80);
        this.filters = 32;
        this.kernelSize = 3;
        this.stride = 1;
        this.padding = 0;
        this.activation = "relu";
        this.hasBias = true;
        this.bias = 0;
        this.maxInputs = 1;
        this.minInputs = 1;
        this.maxOutputs = 1;
        this.minOutputs = 1;
        this.addInput();
        this.addOutput();
        this.inputs[0].activationPhases = ["training", "evaluation"];
        this.outputs[0].activationPhases = ["training", "evaluation"];
    }

    drawLabel(ctx) {
        ctx.font = "bold 12px Inter, sans-serif";
        ctx.fillText(this.filters + "", this.x, this.y - 12);
        ctx.font = "9px Inter, sans-serif";
        ctx.fillText("Conv2D", this.x, this.y + 2);
        ctx.fillText(
            this.kernelSize + "×" + this.kernelSize,
            this.x,
            this.y + 14,
        );
    }
    validateConnections(incomingCount) {
        const errors = [];
        if (incomingCount > 1) {
            errors.push(
                `${this.type}: only accepts 1 input connection, but has ${incomingCount}`,
            );
        }
        return errors;
    }

    computeOutputShapes() {
        const s = this._getFirstInputShapeObj();
        if (!s || s.shape.length < 3) return this._emptyShapes();

        const H = s.shape[s.shape.length - 3];
        const W = s.shape[s.shape.length - 2];

        const H_out = ShapeExpr.from(H)
            .subtract(this.kernelSize)
            .add(2 * this.padding)
            .divide(this.stride)
            .add(1);
        const W_out = ShapeExpr.from(W)
            .subtract(this.kernelSize)
            .add(2 * this.padding)
            .divide(this.stride)
            .add(1);

        const shape = [
            ...s.shape.slice(0, -3).map((x) => new ShapeExpr(x)),
            H_out,
            W_out,
            new ShapeExpr(this.filters),
        ];

        return this._makeShapes(shape, s.symbolic, true);
    }

    toJSON() {
        return {
            ...super.toJSON(),
            filters: this.filters,
            kernelSize: this.kernelSize,
            stride: this.stride,
            padding: this.padding,
            activation: this.activation,
            bias: this.bias,
        };
    }

    fromJSON(d) {
        super.fromJSON(d);
        if (d.filters) this.filters = d.filters;
        if (d.kernelSize) this.kernelSize = d.kernelSize;
        if (d.stride) this.stride = d.stride;
        if (d.padding) this.padding = d.padding;
        if (d.activation) this.activation = d.activation;
        if (d.bias !== undefined) this.bias = d.bias;
    }

    getPropertiesHTML() {
        return (
            this._getShapeSummaryHTML() +
            `<div class="prop-group"><label>Filters</label><input type="number" id="prop-filters" class="prop-input" value="${this.filters}" min="1" max="2048"></div>
            <div class="prop-group"><label>Kernel Size</label><input type="number" id="prop-kernel" class="prop-input" value="${this.kernelSize}" min="1" max="11"></div>
            <div class="prop-group"><label>Stride</label><input type="number" id="prop-stride" class="prop-input" value="${this.stride}" min="1" max="5"></div>
            <div class="prop-group"><label>Padding</label><input type="number" id="prop-padding" class="prop-input" value="${this.padding}" min="0" max="5"></div>
            <div class="prop-group"><label>Activation</label><select id="prop-activation" class="prop-select">
                <option value="relu" ${this.activation === "relu" ? "selected" : ""}>ReLU</option>
                <option value="sigmoid" ${this.activation === "sigmoid" ? "selected" : ""}>Sigmoid</option>
                <option value="tanh" ${this.activation === "tanh" ? "selected" : ""}>Tanh</option>
            </select></div>
            <div class="prop-group">
                <label>Bias</label>
                <input type="number" id="prop-bias" class="prop-input" value="${this.bias}" step="0.01">
                <p class="prop-hint">Bias per filter (${this.filters},)</p>
            </div>`
        );
    }
}
// ========== FLATTEN NODE ==========
class FlattenNode extends RectNode {
    constructor(id, x, y) {
        super(id, x, y, "flatten", 90, 50);
        this.maxInputs = 1;
        this.minInputs = 1;
        this.maxOutputs = 1;
        this.minOutputs = 1;
        this.addInput();
        this.addOutput();
        this.inputs[0].activationPhases = ["training", "evaluation"];
        this.outputs[0].activationPhases = ["training", "evaluation"];
    }

    drawLabel(ctx) {
        ctx.font = "bold 12px Inter, sans-serif";
        ctx.fillText("Flatten", this.x, this.y);
    }
    validateConnections(incomingCount) {
        const errors = [];
        if (incomingCount > 1) {
            errors.push(
                `${this.type}: only accepts 1 input connection, but has ${incomingCount}`,
            );
        }
        return errors;
    }

    computeOutputShapes() {
        const s = this._getFirstInputShapeObj();
        if (!s) return this._emptyShapes();

        const batchDim = new ShapeExpr(s.shape[0]);
        let flattened = new ShapeExpr(1);
        for (let i = 1; i < s.shape.length; i++) {
            flattened = flattened.multiply(s.shape[i]);
        }

        return this._makeShapes([batchDim, flattened], s.symbolic, true);
    }

    toJSON() {
        return super.toJSON();
    }
    fromJSON(d) {
        super.fromJSON(d);
    }

    getPropertiesHTML() {
        return (
            this._getShapeSummaryHTML() +
            "<p class='prop-hint'>Flattens all dimensions except batch into a single feature vector.</p>"
        );
    }
}

// ========== DROPOUT NODE ==========
class DropoutNode extends RectNode {
    constructor(id, x, y) {
        super(id, x, y, "dropout", 90, 50);
        this.rate = 0.5;
        this.maxInputs = 1;
        this.minInputs = 1;
        this.maxOutputs = 1;
        this.minOutputs = 1;
        this.addInput();
        this.addOutput();
        this.inputs[0].activationPhases = ["training", "evaluation"];
        this.outputs[0].activationPhases = ["training", "evaluation"];
    }

    drawLabel(ctx) {
        ctx.font = "bold 12px Inter, sans-serif";
        ctx.fillText("Dropout", this.x, this.y - 6);
        ctx.font = "10px Inter, sans-serif";
        ctx.fillText(Math.round(this.rate * 100) + "%", this.x, this.y + 10);
    }
    validateConnections(incomingCount) {
        const errors = [];
        if (incomingCount > 1) {
            errors.push(
                `${this.type}: only accepts 1 input connection, but has ${incomingCount}`,
            );
        }
        return errors;
    }
    computeOutputShapes() {
        const s = this._getFirstInputShapeObj();
        if (!s) return this._emptyShapes();
        return this._makeShapes([...s.shape], s.symbolic, true);
    }

    toJSON() {
        return { ...super.toJSON(), rate: this.rate };
    }
    fromJSON(d) {
        super.fromJSON(d);
        if (d.rate) this.rate = d.rate;
    }

    getPropertiesHTML() {
        return (
            this._getShapeSummaryHTML() +
            `<div class="prop-group"><label>Dropout Rate</label>
            <input type="range" id="prop-dropout-rate" class="prop-range" min="0" max="0.9" step="0.05"
                   value="${this.rate}" oninput="SketchMod._updateDropout(this)">
            <div class="range-values"><span>${Math.round(this.rate * 100)}%</span></div></div>`
        );
    }
}
// ========== BATCHNORM NODE ==========
class BatchNormNode extends RectNode {
    constructor(id, x, y) {
        super(id, x, y, "batchnorm", 100, 55);
        this.eps = 0.001;
        this.momentum = 0.1;
        this.maxInputs = 1;
        this.minInputs = 1;
        this.maxOutputs = 1;
        this.minOutputs = 1;
        this.addInput();
        this.addOutput();
        this.inputs[0].activationPhases = ["training", "evaluation"];
        this.outputs[0].activationPhases = ["training", "evaluation"];
    }

    drawLabel(ctx) {
        ctx.font = "bold 12px Inter, sans-serif";
        ctx.fillText("BatchNorm", this.x, this.y);
    }
    validateConnections(incomingCount) {
        const errors = [];
        if (incomingCount > 1) {
            errors.push(
                `${this.type}: only accepts 1 input connection, but has ${incomingCount}`,
            );
        }
        return errors;
    }

    computeOutputShapes() {
        const s = this._getFirstInputShapeObj();
        if (!s) return this._emptyShapes();
        return this._makeShapes([...s.shape], s.symbolic, true);
    }

    toJSON() {
        return { ...super.toJSON(), eps: this.eps, momentum: this.momentum };
    }
    fromJSON(d) {
        super.fromJSON(d);
        if (d.eps) this.eps = d.eps;
        if (d.momentum) this.momentum = d.momentum;
    }

    getPropertiesHTML() {
        return (
            this._getShapeSummaryHTML() +
            `<div class="prop-group"><label>Epsilon</label><input type="number" id="prop-eps" class="prop-input" value="${this.eps}" step="0.0001" min="0.00001" max="0.1"></div>
            <div class="prop-group"><label>Momentum</label><input type="number" id="prop-momentum" class="prop-input" value="${this.momentum}" step="0.01" min="0" max="1"></div>
            <p class="prop-hint">Normalizes activations across the batch. Shape unchanged.</p>`
        );
    }
}
// ========== ONEHOT ENCODE NODE ==========
class OneHotEncodeNode extends RectNode {
    constructor(id, x, y) {
        super(id, x, y, "onehot", 110, 55);
        this.numClasses = 10;
        this.maxInputs = 1;
        this.minInputs = 1;
        this.maxOutputs = 1;
        this.minOutputs = 1;
        this.maxParamInputs = 1;
        this.minParamInputs = 0;
        this.maxParamOutputs = 1;
        this.minParamOutputs = 0;
        this.addInput();
        this.addOutput();
        this.inputs[0].activationPhases = ["preprocessing"];
        this.outputs[0].activationPhases = ["preprocessing"];
    }

    drawLabel(ctx) {
        ctx.font = "bold 11px Inter, sans-serif";
        ctx.fillText("OneHot", this.x, this.y - 6);
        ctx.font = "9px Inter, sans-serif";
        ctx.fillText(this.numClasses + " classes", this.x, this.y + 10);
    }
    validateConnections(incomingCount) {
        const errors = [];
        if (incomingCount > 1) {
            errors.push(
                `${this.type}: only accepts 1 input connection, but has ${incomingCount}`,
            );
        }
        return errors;
    }
    computeOutputShapes() {
        const s = this._getFirstInputShapeObj();
        if (!s) return this._emptyShapes();

        const shape = [...s.shape];
        const lastDim = shape[shape.length - 1];
        // If the last dimension is exactly 1, replace it with numClasses (squeeze)
        if (lastDim.isNumber() && lastDim.toNumber() === 1) {
            shape[shape.length - 1] = new ShapeExpr(this.numClasses);
        } else {
            shape.push(this.numClasses);
        }
        return this._makeShapes(shape, s.symbolic, true);
    }

    toJSON() {
        return { ...super.toJSON(), numClasses: this.numClasses };
    }
    fromJSON(d) {
        super.fromJSON(d);
        if (d.numClasses) this.numClasses = d.numClasses;
    }

    getPropertiesHTML() {
        const hasParamIn = this.paramInputs.length > 0;
        const hasParamOut = this.paramOutputs.length > 0;

        let paramHTML = "";
        if (hasParamIn || hasParamOut) {
            paramHTML = `
        <div class="prop-group">
            <label>Param Ports</label>
            <div class="port-legend">
                ${
                    hasParamIn
                        ? `
                <span class="port-legend-item">
                    <svg width="10" height="10" viewBox="0 0 10 10">
                        <polygon points="5,1 9,5 5,9 1,5" fill="#fbbf24" stroke="#1a1d2e" stroke-width="1"/>
                    </svg>
                    Param Input — receives fitted categories
                </span>`
                        : ""
                }
                ${
                    hasParamOut
                        ? `
                <span class="port-legend-item">
                    <svg width="10" height="10" viewBox="0 0 10 10">
                        <polygon points="5,1 9,5 5,9 1,5" fill="#38bdf8" stroke="#1a1d2e" stroke-width="1"/>
                    </svg>
                    Param Output — passes fitted categories
                </span>`
                        : ""
                }
            </div>
        </div>`;
        }

        return (
            this._getShapeSummaryHTML() +
            paramHTML +
            `<div class="prop-group"><label>Number of Classes</label>
            <input type="number" id="prop-classes" class="prop-input" value="${this.numClasses}" min="2" max="10000"
                   onchange="SketchMod._updateOneHotClasses(this)">
        </div>
        <p class="prop-hint">Converts integer labels to one-hot vectors. Adds a dimension.</p>`
        );
    }
}
// ========== One‑Hot Decoder ==========
class DeOneHotNode extends RectNode {
    constructor(id, x, y) {
        super(id, x, y, "deonehot", 110, 55);
        this.maxInputs = 1;
        this.minInputs = 1;
        this.maxOutputs = 1;
        this.minOutputs = 1;

        // Allow param input/output for sharing the encoding map
        this.maxParamInputs = 1;
        this.minParamInputs = 0;
        this.maxParamOutputs = 0; // only receives, doesn't send
        this.minParamOutputs = 0;

        this.addInput();
        this.addOutput();
        this.inputs[0].activationPhases = ["preprocessing"];
        this.outputs[0].activationPhases = ["preprocessing"];
    }

    drawLabel(ctx) {
        ctx.font = "bold 11px Inter, sans-serif";
        ctx.fillText("DeOneHot", this.x, this.y);
    }

    computeOutputShapes() {
        const s = this._getFirstInputShapeObj();
        if (!s) return this._emptyShapes();
        // Input shape: (batch, num_classes) → output shape: (batch,)
        if (s.shape.length < 2) return this._emptyShapes();
        return this._makeShapes(
            [s.shape[0]], // batch dim, last dim removed
            s.symbolic,
            true,
        );
    }

    toJSON() {
        return { ...super.toJSON() };
    }

    fromJSON(d) {
        super.fromJSON(d);
    }

    getPropertiesHTML() {
        let paramHTML = "";
        if (this.paramInputs.length > 0) {
            paramHTML = `
        <div class="prop-group">
            <label>Param Ports</label>
            <div class="port-legend">
                <span class="port-legend-item">
                    <svg width="10" height="10" viewBox="0 0 10 10">
                        <polygon points="5,1 9,5 5,9 1,5" fill="#fbbf24" stroke="#1a1d2e" stroke-width="1"/>
                    </svg>
                    Param Input — receives categories from OneHot encoder
                </span>
            </div>
        </div>`;
        }

        return (
            this._getShapeSummaryHTML() +
            paramHTML +
            `<p class="prop-hint">Converts one-hot vectors back to class indices.</p>`
        );
    }
}

class PrintNode extends RectNode {
    constructor(id, x, y) {
        super(id, x, y, "print", 80, 50);
        this.label = "";
        this.nodeColor = "#fbbf24";
        this.maxInputs = Infinity;
        this.minInputs = 1;
        this.maxOutputs = 0;
        this.minOutputs = 0;
        this.addInput();
        this.updatePorts();
    }

    drawLabel(ctx) {
        ctx.fillText("Print", this.x, this.y);
    }

    computeOutputShapes() {
        return [];
    }

    getPropertiesHTML() {
        return `
            <div class="prop-group">
                <label>Label</label>
                <input type="text" id="prop-print-label" class="prop-input"
                       value="${this.label || ""}"
                       placeholder="e.g. Shape of X"
                       onchange="SketchMod._updatePrintLabel(this)">
            </div>
            <div class="prop-group">
                <label>Input Ports</label>
                <p class="prop-hint">${this.inputs.length} tensor input(s) – prints shape to console</p>
            </div>
        `;
    }

    toJSON() {
        return { ...super.toJSON(), label: this.label };
    }
    fromJSON(d) {
        super.fromJSON(d);
        if (d.label) this.label = d.label;
    }
}
class AccuracyNode extends RectNode {
    constructor(id, x, y) {
        super(id, x, y, "accuracy", 90, 60);
        this.showConfusion = false;
        this.nodeColor = "#a78bfa";
        this.maxInputs = 2;
        this.minInputs = 2;
        this.maxOutputs = 0;
        this.minOutputs = 0;

        // Manually push DataPorts with unique subtypes so colours appear immediately
        this.inputs.push(new DataPort(this, "input", 0, "predictions"));
        this.inputs.push(new DataPort(this, "input", 1, "labels"));
        this.inputs[0].activationPhases = ["evaluation"];
        this.inputs[1].activationPhases = ["evaluation"];
        this.updatePorts();
    }

    drawLabel(ctx) {
        ctx.fillText("Accuracy", this.x, this.y);
    }

    computeOutputShapes() {
        return [];
    }

    getPropertiesHTML() {
        return `
            <div class="prop-group">
                <label>Show Confusion Matrix</label>
                <label class="checkbox-label">
                    <input type="checkbox" id="prop-show-confusion"
                           ${this.showConfusion ? "checked" : ""}
                           onchange="SketchMod._updateAccuracyConfusion(this)">
                    Plot confusion matrix
                </label>
            </div>
            <div class="prop-group">
                <label>Input Ports</label>
                <div class="port-legend">
                    <span class="port-legend-item">
                        <svg width="10" height="10" viewBox="0 0 10 10">
                            <circle cx="5" cy="5" r="4" fill="#60a5fa" stroke="#1a1d2e" stroke-width="1"/>
                        </svg>
                        Predictions
                    </span>
                    <span class="port-legend-item">
                        <svg width="10" height="10" viewBox="0 0 10 10">
                            <circle cx="5" cy="5" r="4" fill="#f59e0b" stroke="#1a1d2e" stroke-width="1"/>
                        </svg>
                        Labels
                    </span>
                </div>
            </div>
        `;
    }

    toJSON() {
        return { ...super.toJSON(), showConfusion: this.showConfusion };
    }

    fromJSON(d) {
        super.fromJSON(d);
        if (d.showConfusion !== undefined) this.showConfusion = d.showConfusion;
    }
}
// ========== CONCATENATE NODE ==========
class ConcatenateNode extends RectNode {
    constructor(id, x, y) {
        super(id, x, y, "concat", 100, 65);
        this.axis = -1;
        this.maxInputs = 1;
        this.minInputs = 1;
        this.maxOutputs = 1;
        this.minOutputs = 1;

        // Single MultiPort for all incoming connections
        this.inputs.push(new MultiPort(this, "input", 0, null));
        this.addOutput();
        this.inputs[0].activationPhases = ["training", "evaluation"];
        this.outputs[0].activationPhases = ["training", "evaluation"];
        this.updatePorts();
    }
    canAddInput() {
        return false;
    }
    canRemoveInput() {
        return false;
    }
    drawLabel(ctx) {
        ctx.font = "bold 12px Inter, sans-serif";
        ctx.fillText("Concat", this.x, this.y - 5);
        ctx.font = "9px Inter, sans-serif";
        const axisLabel = this.axis === -1 ? "last" : this.axis;
        ctx.fillText("axis: " + axisLabel, this.x, this.y + 10);
    }
    validateConnections(incomingCount) {
        const errors = [];
        if (incomingCount < 2) {
            errors.push(
                `Concat: requires at least 2 input connections, has ${incomingCount}`,
            );
        }
        return errors;
    }

    computeOutputShapes() {
        const allShapes = this._getAllInputShapeObjs();
        if (allShapes.length < 2) return this._emptyShapes();

        const baseShape = allShapes[0].shape.map((s) => new ShapeExpr(s));
        const rank = baseShape.length;
        const axis = this.axis === -1 ? rank - 1 : this.axis;

        if (axis < 0 || axis >= rank) return this._emptyShapes();

        let totalConcatDim = null; // ← Start with null, not 0
        let symbolic = false;
        let known = true;

        for (const s of allShapes) {
            if (s.shape.length !== rank) return this._emptyShapes();
            if (s.symbolic) symbolic = true;
            if (!s.known) known = false;

            for (let d = 0; d < rank; d++) {
                if (d !== axis && !s.shape[d].equals(baseShape[d])) {
                    return this._emptyShapes();
                }
            }

            // First shape sets the initial value, rest are added
            if (totalConcatDim === null) {
                totalConcatDim = new ShapeExpr(s.shape[axis]);
            } else {
                totalConcatDim = totalConcatDim.add(s.shape[axis]);
            }
        }

        const outputShape = [...baseShape];
        outputShape[axis] = totalConcatDim;
        return this._makeShapes(outputShape, symbolic, known);
    }

    toJSON() {
        return { ...super.toJSON(), axis: this.axis };
    }
    fromJSON(d) {
        super.fromJSON(d);
        if (d.axis !== undefined) this.axis = d.axis;
    }

    getPropertiesHTML() {
        return (
            this._getShapeSummaryHTML() +
            `<div class="prop-group"><label>Concatenate Axis</label>
        <input type="number" id="prop-concat-axis" class="prop-input" value="${this.axis}" 
               onchange="SketchMod._updateConcatAxis(this)">
        <p class="prop-hint">-1 = last dimension, 0 = batch, 1 = first feature dim, etc.</p></div>
        <p class="prop-hint">Joins multiple tensors along the specified axis. All other dimensions must match.</p>`
        );
    }
}
// ========== ADD NODE (SKIP CONNECTION) ==========
class AddNode extends RectNode {
    constructor(id, x, y) {
        super(id, x, y, "add", 90, 55);
        this.maxInputs = 1;
        this.minInputs = 1;
        this.maxOutputs = 1;
        this.minOutputs = 1;

        // Single MultiPort for all incoming connections
        this.inputs.push(new MultiPort(this, "input", 0, "main"));
        this.addOutput();
        this.updatePorts();
        this.inputs[0].activationPhases = ["training", "evaluation"];
        this.outputs[0].activationPhases = ["training", "evaluation"];
    }

    drawLabel(ctx) {
        ctx.font = "bold 14px Inter, sans-serif";
        ctx.fillText("+", this.x, this.y);
    }
    validateConnections(incomingCount) {
        const errors = [];
        if (incomingCount !== 2) {
            errors.push(
                `Add: requires exactly 2 input connections, has ${incomingCount}`,
            );
        }
        return errors;
    }
    computeOutputShapes() {
        const allShapes = this._getAllInputShapeObjs();
        if (allShapes.length < 2) return this._emptyShapes();

        const base = allShapes[0];
        for (let i = 1; i < allShapes.length; i++) {
            if (
                JSON.stringify(allShapes[i].shape) !==
                JSON.stringify(base.shape)
            ) {
                return this._emptyShapes();
            }
        }

        const symbolic = allShapes.some((s) => s.symbolic);
        return this._makeShapes([...base.shape], symbolic, base.known);
    }
    canAddInput() {
        return false;
    }
    canRemoveInput() {
        return false;
    }
    toJSON() {
        return super.toJSON();
    }
    fromJSON(d) {
        super.fromJSON(d);
    }

    getPropertiesHTML() {
        return (
            this._getShapeSummaryHTML() +
            "<p class='prop-hint'>Element-wise addition of two inputs. Both inputs must have the same shape. Used for skip/residual connections.</p>"
        );
    }
}
// ========== OPTIMIZER NODE ==========
class OptimizerNode extends RectNode {
    constructor(id, x, y) {
        super(id, x, y, "optimizer", 120, 85);

        // Loss config
        this.lossType = "cross_entropy"; // cross_entropy, mse, bce, nll, l1, huber
        this.lossOptions = [
            { value: "cross_entropy", label: "Cross Entropy" },
            { value: "mse", label: "MSE" },
            { value: "bce", label: "BCE" },
            { value: "nll", label: "NLL" },
            { value: "l1", label: "L1" },
            { value: "huber", label: "Huber" },
        ];

        // Optimizer config
        this.optimizerType = "adam"; // adam, sgd, adamw
        this.optimizerOptions = [
            { value: "adam", label: "Adam" },
            { value: "sgd", label: "SGD" },
            { value: "adamw", label: "AdamW" },
        ];
        this.learningRate = 0.001;
        this.adamBeta1 = 0.9;
        this.adamBeta2 = 0.999;
        this.adamEpsilon = 1e-8;
        this.sgdMomentum = 0.9;
        this.weightDecay = 0;
        this.nesterov = false;

        // Training loop config
        this.epochs = 10;
        this.batchSize = 32;
        this.shuffle = true;
        this.gradientClip = null; // null = no clipping
        this.earlyStopping = false;
        this.earlyStoppingPatience = 10;

        // Ports: 2 inputs, 0 outputs
        this.maxInputs = 2;
        this.minInputs = 2;
        this.maxOutputs = 0;
        this.minOutputs = 0;

        this.inputs.push(new RolePort(this, "input", 0, "loss"));
        this.inputs.push(new RolePort(this, "input", 1, "labels"));
        this.inputs[0].activationPhases = ["training"]; // loss
        this.inputs[1].activationPhases = ["training"]; // labels
        this.updatePorts();
    }

    updatePorts() {
        const hw = this.width / 2 + 8;
        const total = this.inputs.length;

        this.inputs.forEach((p, i) => {
            p.x = this.x - hw;
            p.y =
                this.y -
                this.height / 2 +
                (this.height / (total + 1)) * (i + 1);
        });
    }

    drawLabel(ctx) {
        ctx.font = "bold 11px Inter, sans-serif";
        const lossLabel =
            this.lossOptions.find((o) => o.value === this.lossType)?.label ||
            "Loss";
        ctx.fillText(lossLabel, this.x, this.y - 10);
        ctx.font = "9px Inter, sans-serif";
        const optLabel =
            this.optimizerOptions.find((o) => o.value === this.optimizerType)
                ?.label || "Adam";
        ctx.fillText(optLabel + " · " + this.epochs + "ep", this.x, this.y + 6);
        ctx.fillText(
            "bs=" + this.batchSize + " lr=" + this.learningRate,
            this.x,
            this.y + 18,
        );
    }
    validateConnections(incomingCount) {
        const errors = [];
        if (incomingCount !== 2) {
            errors.push(
                `Optimizer: requires 2 input connections (loss + labels), has ${incomingCount}`,
            );
        }
        return errors;
    }
    computeOutputShapes() {
        return [];
    }

    toJSON() {
        return {
            ...super.toJSON(),
            lossType: this.lossType,
            optimizerType: this.optimizerType,
            learningRate: this.learningRate,
            adamBeta1: this.adamBeta1,
            adamBeta2: this.adamBeta2,
            adamEpsilon: this.adamEpsilon,
            sgdMomentum: this.sgdMomentum,
            weightDecay: this.weightDecay,
            nesterov: this.nesterov,
            epochs: this.epochs,
            batchSize: this.batchSize,
            shuffle: this.shuffle,
            gradientClip: this.gradientClip,
            earlyStopping: this.earlyStopping,
            earlyStoppingPatience: this.earlyStoppingPatience,
        };
    }

    fromJSON(d) {
        super.fromJSON(d);
        if (d.lossType) this.lossType = d.lossType;
        if (d.optimizerType) this.optimizerType = d.optimizerType;
        if (d.learningRate !== undefined) this.learningRate = d.learningRate;
        if (d.adamBeta1 !== undefined) this.adamBeta1 = d.adamBeta1;
        if (d.adamBeta2 !== undefined) this.adamBeta2 = d.adamBeta2;
        if (d.adamEpsilon !== undefined) this.adamEpsilon = d.adamEpsilon;
        if (d.sgdMomentum !== undefined) this.sgdMomentum = d.sgdMomentum;
        if (d.weightDecay !== undefined) this.weightDecay = d.weightDecay;
        if (d.nesterov !== undefined) this.nesterov = d.nesterov;
        if (d.epochs) this.epochs = d.epochs;
        if (d.batchSize) this.batchSize = d.batchSize;
        if (d.shuffle !== undefined) this.shuffle = d.shuffle;
        if (d.gradientClip !== undefined) this.gradientClip = d.gradientClip;
        if (d.earlyStopping !== undefined) this.earlyStopping = d.earlyStopping;
        if (d.earlyStoppingPatience !== undefined)
            this.earlyStoppingPatience = d.earlyStoppingPatience;
    }

    getPropertiesHTML() {
        const lossOptionsHTML = this.lossOptions
            .map(
                (o) =>
                    `<option value="${o.value}" ${this.lossType === o.value ? "selected" : ""}>${o.label}</option>`,
            )
            .join("");

        const optOptionsHTML = this.optimizerOptions
            .map(
                (o) =>
                    `<option value="${o.value}" ${this.optimizerType === o.value ? "selected" : ""}>${o.label}</option>`,
            )
            .join("");

        // Optimizer-specific fields
        let optimizerSpecificHTML = "";
        if (this.optimizerType === "adam" || this.optimizerType === "adamw") {
            optimizerSpecificHTML += `
            <div class="prop-group">
                <label>Beta1</label>
                <input type="number" id="prop-adam-beta1" class="prop-input" value="${this.adamBeta1}" step="0.01" min="0" max="1"
                       onchange="SketchMod._updateOptimizerProp('adamBeta1', this.value)">
            </div>
            <div class="prop-group">
                <label>Beta2</label>
                <input type="number" id="prop-adam-beta2" class="prop-input" value="${this.adamBeta2}" step="0.001" min="0" max="1"
                       onchange="SketchMod._updateOptimizerProp('adamBeta2', this.value)">
            </div>
            <div class="prop-group">
                <label>Epsilon</label>
                <input type="number" id="prop-adam-epsilon" class="prop-input" value="${this.adamEpsilon}" step="0.00000001" min="0"
                       onchange="SketchMod._updateOptimizerProp('adamEpsilon', this.value)">
            </div>`;
        }
        if (this.optimizerType === "sgd") {
            optimizerSpecificHTML += `
            <div class="prop-group">
                <label>Momentum</label>
                <input type="number" id="prop-sgd-momentum" class="prop-input" value="${this.sgdMomentum}" step="0.01" min="0" max="1"
                       onchange="SketchMod._updateOptimizerProp('sgdMomentum', this.value)">
            </div>
            <div class="prop-group">
                <label>
                    <input type="checkbox" id="prop-nesterov" ${this.nesterov ? "checked" : ""}
                           onchange="SketchMod._updateOptimizerProp('nesterov', this.checked)">
                    Nesterov
                </label>
            </div>`;
        }
        if (this.optimizerType === "adamw" || this.optimizerType === "sgd") {
            optimizerSpecificHTML += `
            <div class="prop-group">
                <label>Weight Decay</label>
                <input type="number" id="prop-weight-decay" class="prop-input" value="${this.weightDecay}" step="0.0001" min="0"
                       onchange="SketchMod._updateOptimizerProp('weightDecay', this.value)">
            </div>`;
        }

        return `
            ${this._getShapeSummaryHTML()}
            <div class="prop-group">
            <label>Input Ports</label>
            <div class="port-legend">
                <span class="port-legend-item">
                    <svg width="10" height="10" viewBox="0 0 10 10">
                        <circle cx="5" cy="5" r="4" fill="#53BF9D" stroke="#1a1d2e" stroke-width="1"/>
                    </svg>
                    Loss — from OutputNode
                </span>
                <span class="port-legend-item">
                    <svg width="10" height="10" viewBox="0 0 10 10">
                        <circle cx="5" cy="5" r="4" fill="#f59e0b" stroke="#1a1d2e" stroke-width="1"/>
                    </svg>
                    Labels — from data pipeline
                </span>
            </div>
        </div>
        <div class="prop-group">
            <label>Loss Function</label>
            <select id="prop-loss-type" class="prop-select" onchange="SketchMod._updateOptimizerProp('lossType', this.value)">
                ${lossOptionsHTML}
            </select>
        </div>
            
            <div class="prop-group">
                <label>Optimizer</label>
                <select id="prop-optimizer-type" class="prop-select" onchange="SketchMod._updateOptimizerProp('optimizerType', this.value)">
                    ${optOptionsHTML}
                </select>
            </div>
            <div class="prop-group">
                <label>Learning Rate</label>
                <input type="number" id="prop-lr" class="prop-input" value="${this.learningRate}" step="0.0001" min="0"
                       onchange="SketchMod._updateOptimizerProp('learningRate', this.value)">
            </div>
            ${optimizerSpecificHTML}
            <div class="prop-group">
                <label>Epochs</label>
                <input type="number" id="prop-epochs" class="prop-input" value="${this.epochs}" min="1" max="10000"
                       onchange="SketchMod._updateOptimizerProp('epochs', this.value)">
            </div>
            <div class="prop-group">
                <label>Batch Size</label>
                <input type="number" id="prop-batch-size" class="prop-input" value="${this.batchSize}" min="1" max="4096"
                       onchange="SketchMod._updateOptimizerProp('batchSize', this.value)">
            </div>
            <div class="prop-group">
                <label>
                    <input type="checkbox" id="prop-shuffle" ${this.shuffle ? "checked" : ""}
                           onchange="SketchMod._updateOptimizerProp('shuffle', this.checked)">
                    Shuffle
                </label>
            </div>
            <div class="prop-group">
                <label>Gradient Clip (optional)</label>
                <input type="number" id="prop-grad-clip" class="prop-input" value="${this.gradientClip || ""}" step="0.1" min="0"
                       placeholder="None"
                       onchange="SketchMod._updateOptimizerProp('gradientClip', this.value || null)">
            </div>
            <div class="prop-group">
                <label>
                    <input type="checkbox" id="prop-early-stopping" 
                        ${this.earlyStopping ? "checked" : ""}
                        onchange="SketchMod._updateOptimizerProp('earlyStopping', this.checked)">
                    Early Stopping
                </label>
            </div>
            ${
                this.earlyStopping
                    ? `
            <div class="prop-group">
                <label>Patience (epochs)</label>
                <input type="number" id="prop-patience" class="prop-input" 
                    value="${this.earlyStoppingPatience}" min="1" max="100" step="1"
                    onchange="SketchMod._updateOptimizerProp('earlyStoppingPatience', this.value)">
                <p class="prop-hint">Stop training if validation loss doesn't improve for this many epochs</p>
            </div>
            `
                    : ""
            }
            
        `;
    }
}
// ========== VISUALIZATION NODE ==========
class VisualizationNode extends RectNode {
    constructor(id, x, y) {
        super(id, x, y, "visualization", 120, 75);

        this.maxInputs = 4; // 3 coords + 1 color
        this.minInputs = 1;
        this.maxOutputs = 0;
        this.minOutputs = 0;

        this.colorMode = "none";
        this.colorPalette = [
            "#ef4444",
            "#4ade80",
            "#60a5fa",
            "#f59e0b",
            "#a78bfa",
        ];
        this.continuousMinColor = "#3b82f6";
        this.continuousMaxColor = "#ef4444";

        // Start with 2 coord inputs
        this.inputs.push(new DataPort(this, "input", 0, "coord"));
        this.inputs.push(new DataPort(this, "input", 1, "coord"));
        // for coord inputs and color input
        for (const port of this.inputs) {
            port.activationPhases = ["evaluation"];
        }
        this.updatePorts();
    }

    _coordPorts() {
        return this.inputs.filter(
            (p) => !(p instanceof RolePort) && p.subType !== "color",
        );
    }

    _colorPort() {
        return (
            this.inputs.find(
                (p) => p instanceof RolePort && p.role === "color",
            ) || null
        );
    }

    _hasColorInput() {
        return this._colorPort() !== null;
    }

    _canAddCoordInput() {
        return this._coordPorts().length < 3;
    }

    _canRemoveCoordInput() {
        return this._coordPorts().length > this.minInputs;
    }

    _canAddColorInput() {
        return this._colorPort() === null;
    }

    _canRemoveColorInput() {
        return this._colorPort() !== null;
    }

    canAddInput(subType) {
        if (subType === "color") return this._canAddColorInput();
        return this._canAddCoordInput();
    }

    canRemoveInput() {
        return this._canRemoveColorInput() || this._canRemoveCoordInput();
    }

    addInput(subType) {
        if (subType === "color") {
            if (!this._canAddColorInput()) return null;
            const p = new RolePort(this, "input", this.inputs.length, "color");
            this.inputs.push(p);
            this.updatePorts();
            return p;
        }
        if (!this._canAddCoordInput()) return null;
        const p = new DataPort(this, "input", this.inputs.length, "coord");
        this.inputs.push(p);
        this.updatePorts();
        return p;
    }

    removeInput() {
        // Prefer removing color port first
        if (this._canRemoveColorInput()) {
            const port = this._colorPort();
            this.inputs = this.inputs.filter((p) => p !== port);
            this._renumberPorts();
            this.updatePorts();
            return port;
        }
        if (!this._canRemoveCoordInput()) return null;
        const ports = this._coordPorts();
        const port = ports[ports.length - 1];
        this.inputs = this.inputs.filter((p) => p !== port);
        this._renumberPorts();
        this.updatePorts();
        return port;
    }

    _renumberPorts() {
        this.inputs.forEach((p, i) => {
            p.index = i;
            p.id = `${this.id}_input_${i}`;
        });
    }

    updatePorts() {
        const hw = this.width / 2 + 8;
        const total = this.inputs.length;
        this.inputs.forEach((p, i) => {
            p.x = this.x - hw;
            p.y =
                this.y -
                this.height / 2 +
                (this.height / (total + 1)) * (i + 1);
        });
    }

    drawLabel(ctx) {
        const coordCount = this._coordPorts().length;
        ctx.font = "bold 12px Inter, sans-serif";
        ctx.fillText(`${coordCount}D Viz`, this.x, this.y - 6);
        ctx.font = "9px Inter, sans-serif";
        const modeLabel =
            this.colorMode === "discrete"
                ? "Discrete"
                : this.colorMode === "continuous"
                  ? "Continuous"
                  : "No Color";
        ctx.fillText(modeLabel, this.x, this.y + 10);
    }

    computeOutputShapes() {
        return [];
    }

    toJSON() {
        return {
            ...super.toJSON(),
            colorMode: this.colorMode,
            colorPalette: this.colorPalette,
            continuousMinColor: this.continuousMinColor,
            continuousMaxColor: this.continuousMaxColor,
        };
    }
    fromJSON(d) {
        super.fromJSON(d);
        if (d.colorMode) this.colorMode = d.colorMode;
        if (d.colorPalette) this.colorPalette = d.colorPalette;
        if (d.continuousMinColor)
            this.continuousMinColor = d.continuousMinColor;
        if (d.continuousMaxColor)
            this.continuousMaxColor = d.continuousMaxColor;
    }

    getPropertiesHTML() {
        const coordPorts = this._coordPorts();
        const coordCount = coordPorts.length;

        // Port legend
        let portLegendHTML = `
        <div class="prop-group">
            <label>Input Ports</label>
            <div class="port-legend">
                <span class="port-legend-item">
                    <svg width="10" height="10" viewBox="0 0 10 10">
                        <circle cx="5" cy="5" r="4" fill="#60a5fa" stroke="#1a1d2e" stroke-width="1"/>
                    </svg>
                    Coordinates (${coordCount}/3)
                </span>`;
        if (this._hasColorInput()) {
            portLegendHTML += `
                <span class="port-legend-item">
                    <svg width="10" height="10" viewBox="0 0 10 10">
                        <circle cx="5" cy="5" r="4" fill="#ff00b7" stroke="#1a1d2e" stroke-width="1"/>
                    </svg>
                    Color mapping
                </span>`;
        }
        portLegendHTML += `</div></div>`;

        // Color mode radio
        let modeHTML = `
        <div class="prop-group">
            <label>Color Mode</label>
            <div class="radio-group">
                <label class="radio-label">
                    <input type="radio" name="viz-color-mode" value="none"
                           ${this.colorMode === "none" ? "checked" : ""}
                           onchange="SketchMod._updateVizProp('colorMode', 'none')">
                    None
                </label>
                <label class="radio-label">
                    <input type="radio" name="viz-color-mode" value="discrete"
                           ${this.colorMode === "discrete" ? "checked" : ""}
                           onchange="SketchMod._updateVizProp('colorMode', 'discrete')">
                    Discrete
                </label>
                <label class="radio-label">
                    <input type="radio" name="viz-color-mode" value="continuous"
                           ${this.colorMode === "continuous" ? "checked" : ""}
                           onchange="SketchMod._updateVizProp('colorMode', 'continuous')">
                    Continuous
                </label>
            </div>
        </div>`;

        // Discrete palette
        let discreteHTML = "";
        if (this.colorMode === "discrete") {
            discreteHTML = `
            <div class="prop-group">
                <label>Color Palette</label>
                <div class="color-palette-list" id="vizPaletteList">
                    ${this.colorPalette
                        .map(
                            (color, i) => `
                        <div class="color-palette-row">
                            <span class="color-palette-index">${i}</span>
                            <input type="color" class="color-palette-picker"
                                   value="${color}"
                                   onchange="SketchMod._updateVizPaletteColor(${i}, this.value)">
                            <button class="color-palette-remove"
                                    onclick="SketchMod._removeVizPaletteColor(${i})"
                                    ${this.colorPalette.length <= 2 ? "disabled" : ""}
                                    title="Remove color">
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <line x1="18" y1="6" x2="6" y2="18"/>
                                    <line x1="6" y1="6" x2="18" y2="18"/>
                                </svg>
                            </button>
                        </div>
                    `,
                        )
                        .join("")}
                </div>
                <button class="prop-btn prop-btn-add" onclick="SketchMod._addVizPaletteColor()">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="12" y1="5" x2="12" y2="19"/>
                        <line x1="5" y1="12" x2="19" y2="12"/>
                    </svg>
                    Add Color
                </button>
                <p class="prop-hint">Classes beyond the last color use the last color.</p>
            </div>`;
        }

        // Continuous
        let continuousHTML = "";
        if (this.colorMode === "continuous") {
            continuousHTML = `
            <div class="prop-group">
                <label>Min Color (value 0.0)</label>
                <input type="color" class="prop-input" style="height: 36px; padding: 4px;"
                       value="${this.continuousMinColor}"
                       onchange="SketchMod._updateVizProp('continuousMinColor', this.value)">
            </div>
            <div class="prop-group">
                <label>Max Color (value 1.0)</label>
                <input type="color" class="prop-input" style="height: 36px; padding: 4px;"
                       value="${this.continuousMaxColor}"
                       onchange="SketchMod._updateVizProp('continuousMaxColor', this.value)">
            </div>
            <p class="prop-hint">Expects normalized values [0,1]. Out-of-range values are clamped.</p>`;
        }

        return `
            ${portLegendHTML}
            ${modeHTML}
            ${discreteHTML}
            ${continuousHTML}
        `;
    }
}

// ========== LINK ==========

class Link {
    constructor(from, to, weight) {
        this.from = from;
        this.to = to;
        this.weight = weight || 1;
        this.weightShape = null;
        this.hasWeight = false; // True for Data→Model and Model→Model connections
    }

    computeWeightShape() {
        const fromNode = this.from.node;
        const toNode = this.to.node;

        // Determine if this connection needs a weight
        const fromIsModel =
            fromNode instanceof NeuronNode || fromNode instanceof LayerNode;
        const toIsModel =
            toNode instanceof NeuronNode || toNode instanceof LayerNode;
        const fromIsData = !fromIsModel && !(fromNode instanceof OutputNode);
        const toIsOutput = toNode instanceof OutputNode;

        // Only Data→Model and Model→Model have weights
        this.hasWeight =
            (fromIsData && toIsModel) || (fromIsModel && toIsModel);

        if (!this.hasWeight) {
            this.weightShape = null;
            return;
        }

        let inFeatures = null; // Current layer features (columns of W)
        let outFeatures = null; // Next layer features (rows of W)

        // Input features = last dim of source node's output shape
        if (fromNode.outputs.length > 0) {
            const outPort = fromNode.outputs[0];
            if (outPort.shape && outPort.shape.shape) {
                inFeatures =
                    outPort.shape.shape[outPort.shape.shape.length - 1];
            }
        }

        // Output features = target node's neuron count
        if (toNode instanceof LayerNode) {
            outFeatures = toNode.numNeurons;
        } else if (toNode instanceof NeuronNode) {
            outFeatures = 1;
        }

        if (inFeatures !== null && outFeatures !== null) {
            this.weightShape = {
                shape: [outFeatures, inFeatures], // (next_layer, current_layer)
                dtype: "float32",
            };
        } else {
            this.weightShape = null;
        }
    }

    weightShapeDisplay() {
        if (!this.weightShape) return "N/A";
        return "(" + this.weightShape.shape.join(", ") + ")";
    }

    draw(ctx, selected) {
        const linkKey = this.from.id + "→" + this.to.id;
        const isHL =
            SketchMod._highlightPhaseLinks &&
            SketchMod._highlightPhaseLinks.has(this);
        const isShowAll =
            SketchMod._showAllLinks && SketchMod._showAllLinks.has(this);

        ctx.shadowColor = "transparent";
        ctx.shadowBlur = 0;

        let strokeColor, fillColor, lineWidth;

        if (isShowAll) {
            try {
                const phases = SketchMod._showAllLinks.get(this);
                const c = SketchMod._getShowAllColor(phases);
                strokeColor = c;
                fillColor = c;
                lineWidth = 3;
            } catch (e) {
                isShowAll = false;
            }
        }

        if (!isShowAll) {
            if (isHL) {
                strokeColor = "#4ade80";
                fillColor = "#4ade80";
                lineWidth = 3;
                ctx.shadowColor = "#4ade80";
                ctx.shadowBlur = 6;
            } else if (SketchMod.errorLinkIds.has(linkKey)) {
                strokeColor = "#ef4444";
                fillColor = "#ef4444";
                lineWidth = 3;
            } else if (SketchMod.warningLinkIds.has(linkKey)) {
                strokeColor = "#f59e0b";
                fillColor = "#f59e0b";
                lineWidth = 2.5;
            } else if (selected) {
                strokeColor = "#ffffff";
                fillColor = "#ffffff";
                lineWidth = 3;
            } else if (this.hasWeight) {
                strokeColor = "#000000";
                fillColor = "#000000";
                lineWidth = 2.5;
            } else {
                strokeColor = "#000000";
                fillColor = "#000000";
                lineWidth = 1.5;
            }
        }

        ctx.beginPath();
        ctx.moveTo(this.from.x, this.from.y);
        ctx.lineTo(this.to.x, this.to.y);
        ctx.strokeStyle = strokeColor;
        ctx.lineWidth = lineWidth;
        ctx.stroke();

        ctx.shadowColor = "transparent";
        ctx.shadowBlur = 0;

        // Arrowhead
        const dx = this.to.x - this.from.x;
        const dy = this.to.y - this.from.y;
        const totalDistance = Math.hypot(dx, dy);
        if (totalDistance < 0.001) return;

        const portOffset = 4;
        let tipX = this.to.x,
            tipY = this.to.y;
        if (totalDistance > portOffset) {
            const ratio = (totalDistance - portOffset) / totalDistance;
            tipX = this.from.x + dx * ratio;
            tipY = this.from.y + dy * ratio;
        }

        const angle = Math.atan2(tipY - this.from.y, tipX - this.from.x);
        const size = 8;
        ctx.beginPath();
        ctx.moveTo(tipX, tipY);
        ctx.lineTo(
            tipX - size * Math.cos(angle - 0.5),
            tipY - size * Math.sin(angle - 0.5),
        );
        ctx.lineTo(
            tipX - size * Math.cos(angle + 0.5),
            tipY - size * Math.sin(angle + 0.5),
        );
        ctx.closePath();

        ctx.fillStyle = fillColor;
        ctx.fill();

        ctx.shadowColor = "transparent";
        ctx.shadowBlur = 0;
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

    toJSON() {
        return {
            from: this.from.id,
            to: this.to.id,
            weight: this.weight,
            weightShape: this.weightShape,
            hasWeight: this.hasWeight,
        };
    }
}
// ========== REGISTER NODES ==========
SketchMod.registerNode({
    type: "neuron",
    label: "Neuron",
    category: "models",
    class: NeuronNode,
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="3"/><line x1="12" y1="9" x2="12" y2="2"/>
        <line x1="12" y1="22" x2="12" y2="15"/><line x1="9" y1="12" x2="2" y2="12"/>
        <line x1="22" y1="12" x2="15" y2="12"/></svg>`,
});

SketchMod.registerNode({
    type: "layer",
    label: "Layer",
    category: "models",
    class: LayerNode,
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="2" y="4" width="20" height="4" rx="1"/>
        <rect x="2" y="10" width="20" height="4" rx="1"/>
        <rect x="2" y="16" width="20" height="4" rx="1"/></svg>`,
});

SketchMod.registerNode({
    type: "column-select",
    label: "Column Select",
    category: "data",
    class: ColumnSelectNode,
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="3" y="3" width="7" height="7" rx="1"/>
        <rect x="14" y="3" width="7" height="7" rx="1"/>
        <rect x="3" y="14" width="7" height="7" rx="1"/>
        <rect x="14" y="14" width="7" height="7" rx="1"/></svg>`,
});

SketchMod.registerNode({
    type: "train-test",
    label: "Train/Test",
    category: "data",
    class: TrainTestSplitNode,
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M16 3h5v5"/><path d="M8 3H3v5"/><path d="M3 16v5h5"/>
        <path d="M21 16v5h-5"/><line x1="3" y1="3" x2="21" y2="21"/></svg>`,
});

SketchMod.registerNode({
    type: "normalize",
    label: "Normalize",
    category: "data",
    class: NormalizeNode,
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="4" y1="20" x2="20" y2="20"/>
        <polyline points="4 20 8 12 12 16 16 6 20 10"/></svg>`,
});

SketchMod.registerNode({
    type: "row-select",
    label: "Row Select",
    category: "data",
    class: RowSelectNode,
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="3" y="3" width="7" height="18" rx="1"/>
        <rect x="14" y="3" width="7" height="18" rx="1"/></svg>`,
});

SketchMod.registerNode({
    type: "dim-select",
    label: "Dim Select",
    category: "data",
    class: DimSelectNode,
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="3" y="3" width="18" height="18" rx="2"/>
        <rect x="7" y="7" width="10" height="4" rx="1"/>
        <rect x="7" y="13" width="10" height="4" rx="1"/></svg>`,
});

SketchMod.registerNode({
    type: "conv2d",
    label: "Conv2D",
    category: "models",
    class: Conv2DNode,
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="3" y="3" width="18" height="18" rx="2"/>
        <rect x="6" y="6" width="12" height="12" rx="1"/>
        <circle cx="12" cy="12" r="3"/></svg>`,
});
SketchMod.registerNode({
    type: "flatten",
    label: "Flatten",
    category: "models",
    class: FlattenNode,
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="3" y="3" width="18" height="18" rx="2"/>
        <line x1="8" y1="12" x2="16" y2="12"/>
        <line x1="12" y1="8" x2="12" y2="16"/></svg>`,
});
SketchMod.registerNode({
    type: "dropout",
    label: "Dropout",
    category: "models",
    class: DropoutNode,
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="6" cy="6" r="2"/><circle cx="12" cy="6" r="2"/>
        <circle cx="18" cy="6" r="2"/><circle cx="9" cy="12" r="2"/>
        <circle cx="15" cy="12" r="2"/><circle cx="6" cy="18" r="2"/>
        <circle cx="12" cy="18" r="2"/><circle cx="18" cy="18" r="2"/>
        <line x1="4" y1="4" x2="8" y2="8"/><line x1="10" y1="4" x2="14" y2="8"/>
        <line x1="16" y1="4" x2="20" y2="8"/></svg>`,
});
SketchMod.registerNode({
    type: "batchnorm",
    label: "BatchNorm",
    category: "models",
    class: BatchNormNode,
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M12 20V10"/><path d="M18 20V4"/><path d="M6 20v-4"/>
        <line x1="2" y1="20" x2="22" y2="20"/></svg>`,
});
SketchMod.registerNode({
    type: "onehot",
    label: "OneHot Encode",
    category: "data",
    class: OneHotEncodeNode,
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="3" y="3" width="4" height="18" rx="1"/>
        <rect x="10" y="3" width="4" height="18" rx="1"/>
        <rect x="17" y="3" width="4" height="18" rx="1"/>
        <rect x="4" y="8" width="2" height="6" fill="currentColor" opacity="0.3"/></svg>`,
});
SketchMod.registerNode({
    type: "deonehot",
    label: "DeOneHot",
    category: "data",
    class: DeOneHotNode,
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="3" y="3" width="18" height="18" rx="2"/>
        <rect x="7" y="7" width="10" height="4" rx="1"/>
        <line x1="7" y1="14" x2="17" y2="14"/>
    </svg>`,
});
SketchMod.registerNode({
    type: "concat",
    label: "Concatenate",
    category: "data",
    class: ConcatenateNode,
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="3" y="6" width="8" height="4" rx="1"/>
        <rect x="3" y="14" width="8" height="4" rx="1"/>
        <rect x="13" y="6" width="8" height="12" rx="1"/></svg>`,
});
SketchMod.registerNode({
    type: "add",
    label: "Add (Skip)",
    category: "models",
    class: AddNode,
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <line x1="12" y1="8" x2="12" y2="16"/>
        <line x1="8" y1="12" x2="16" y2="12"/></svg>`,
});
SketchMod.registerNode({
    type: "optimizer",
    label: "Optimizer",
    category: "training",
    class: OptimizerNode,
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="3"/>
        <path d="M12 1v4"/><path d="M12 19v4"/>
        <path d="M4.22 4.22l2.83 2.83"/><path d="M16.95 16.95l2.83 2.83"/>
        <path d="M1 12h4"/><path d="M19 12h4"/>
        <path d="M4.22 19.78l2.83-2.83"/><path d="M16.95 7.05l2.83-2.83"/>
    </svg>`,
});
SketchMod.registerNode({
    type: "visualization",
    label: "Visualization",
    category: "data",
    class: VisualizationNode,
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="6" cy="6" r="2"/><circle cx="18" cy="6" r="2"/>
        <circle cx="12" cy="14" r="2"/><circle cx="6" cy="18" r="2"/>
        <circle cx="18" cy="18" r="2"/>
        <line x1="6" y1="8" x2="6" y2="16"/><line x1="18" y1="8" x2="18" y2="16"/>
        <line x1="8" y1="6" x2="16" y2="6"/><line x1="8" y1="18" x2="16" y2="18"/>
    </svg>`,
});
SketchMod.registerNode({
    type: "print",
    label: "Print",
    category: "data",
    class: PrintNode,
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polyline points="6 9 6 2 18 2 18 9"/><path d="M6 12H4a2 2 0 0 0-2 2v4a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-4a2 2 0 0 0-2-2h-2"/>
        <rect x="6" y="14" width="12" height="8"/></svg>`,
});

SketchMod.registerNode({
    type: "accuracy",
    label: "Accuracy",
    category: "data",
    class: AccuracyNode,
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
        <polyline points="22 4 12 14.01 9 11.01"/></svg>`,
});
// ========== STARTUP ==========
document.addEventListener("DOMContentLoaded", () => SketchMod.init());

// ========== GLOBAL MODAL HELPERS ==========
function closeSaveModal() {
    if (SketchMod && SketchMod.closeSaveModal) {
        SketchMod.closeSaveModal();
    }
}

function openSaveModal() {
    if (SketchMod && SketchMod.openSaveModal) {
        SketchMod.openSaveModal();
    }
}
function handleSave(event) {
    event.preventDefault();
    SketchMod._handleSave(event);
    return false;
}
