/**
 * SketchMod Canvas Manager
 * Initializes Fabric.js canvas and manages global state.
 */

const SketchMod = {
    canvas: null,
    currentTool: "select",
    nodes: [],
    links: [],
    nodeCounter: 0,

    init() {
        this.canvas = new fabric.Canvas("sketchCanvas", {
            selection: true,
            backgroundColor: null,
            width: document.getElementById("canvasWrapper").clientWidth,
            height: document.getElementById("canvasWrapper").clientHeight,
        });

        // Handle window resize
        window.addEventListener("resize", () => {
            this.canvas.setWidth(
                document.getElementById("canvasWrapper").clientWidth,
            );
            this.canvas.setHeight(
                document.getElementById("canvasWrapper").clientHeight,
            );
            this.canvas.renderAll();
        });

        // Mouse events for tool actions
        this.canvas.on("mouse:down", (e) => this.handleCanvasClick(e));

        // Enable panning with middle mouse
        this.canvas.on("mouse:down", (e) => {
            if (e.e.button === 1) {
                this.canvas.isDragging = true;
                this.canvas.selection = false;
            }
        });

        this.canvas.on("mouse:move", (e) => {
            if (this.canvas.isDragging) {
                const delta = new fabric.Point(e.e.movementX, e.e.movementY);
                this.canvas.relativePan(delta);
            }
        });

        this.canvas.on("mouse:up", () => {
            this.canvas.isDragging = false;
        });

        // Scroll to zoom
        this.canvas.on("mouse:wheel", (opt) => {
            const delta = opt.e.deltaY;
            let zoom = this.canvas.getZoom();
            zoom *= 0.999 ** delta;
            if (zoom > 20) zoom = 20;
            if (zoom < 0.01) zoom = 0.01;
            this.canvas.zoomToPoint(
                { x: opt.e.offsetX, y: opt.e.offsetY },
                zoom,
            );
            opt.e.preventDefault();
            opt.e.stopPropagation();
        });

        console.log("SketchMod canvas initialized");
    },

    handleCanvasClick(e) {
        const tool = this.currentTool;
        const pointer = this.canvas.getPointer(e.e);

        // Skip if clicking on an existing object (unless delete tool)
        if (e.target && tool !== "delete") return;

        switch (tool) {
            case "neuron":
                this.createNeuron(pointer.x, pointer.y);
                break;
            case "layer":
                this.createLayer(pointer.x, pointer.y);
                break;
            case "data-input":
                this.createDataInput(pointer.x, pointer.y);
                break;
            case "delete":
                if (e.target) {
                    this.canvas.remove(e.target);
                }
                break;
        }
    },

    setTool(toolName) {
        this.currentTool = toolName;

        if (toolName === "pan") {
            this.canvas.selection = false;
            this.canvas.defaultCursor = "grab";
        } else if (toolName === "delete") {
            this.canvas.selection = false;
            this.canvas.defaultCursor = "pointer";
            this.canvas.hoverCursor = "crosshair";
        } else {
            this.canvas.selection = true;
            this.canvas.defaultCursor = "default";
            this.canvas.hoverCursor = "move";
        }
    },

    getGraphData() {
        return {
            nodes: this.nodes.map((n) => n.toJSON()),
            links: this.links.map((l) => l.toJSON()),
        };
    },
};

document.addEventListener("DOMContentLoaded", () => {
    SketchMod.init();
});
