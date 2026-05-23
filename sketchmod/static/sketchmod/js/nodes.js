/**
 * Node creation and management
 */

SketchMod.createNeuron = function (x, y) {
    const id = `neuron_${++this.nodeCounter}`;

    // Create circle
    const circle = new fabric.Circle({
        radius: 25,
        fill: "#8b5cf6",
        stroke: "#6d28d9",
        strokeWidth: 2,
        left: x - 25,
        top: y - 25,
        id: id,
        nodeType: "neuron",
    });

    // Label
    const label = new fabric.Text("N", {
        fontSize: 16,
        fill: "#fff",
        fontWeight: "bold",
        fontFamily: "Inter, sans-serif",
        left: x - 6,
        top: y - 9,
        selectable: false,
    });

    // Group
    const group = new fabric.Group([circle, label], {
        left: x - 25,
        top: y - 25,
        id: id,
        nodeType: "neuron",
        subTargetCheck: true,
    });

    // Context menu
    group.on("mousedown", function (e) {
        if (e.button === 3) {
            e.e.preventDefault();
            showContextMenu(e.e.clientX, e.e.clientY, id);
        }
    });

    this.canvas.add(group);
    this.nodes.push(group);
    return group;
};

SketchMod.createLayer = function (x, y) {
    const id = `layer_${++this.nodeCounter}`;

    const rect = new fabric.Rect({
        width: 100,
        height: 60,
        fill: "#8b5cf6",
        stroke: "#6d28d9",
        strokeWidth: 2,
        rx: 8,
        ry: 8,
        id: id,
        nodeType: "layer",
    });

    const label = new fabric.Text("Layer", {
        fontSize: 14,
        fill: "#fff",
        fontWeight: "bold",
        fontFamily: "Inter, sans-serif",
        left: 18,
        top: 19,
        selectable: false,
    });

    const group = new fabric.Group([rect, label], {
        left: x - 50,
        top: y - 30,
        id: id,
        nodeType: "layer",
        subTargetCheck: true,
    });

    this.canvas.add(group);
    this.nodes.push(group);
    return group;
};

SketchMod.createDataInput = function (x, y) {
    const id = `data_${++this.nodeCounter}`;

    const rect = new fabric.Rect({
        width: 80,
        height: 50,
        fill: "#3b82f6",
        stroke: "#1d4ed8",
        strokeWidth: 2,
        rx: 8,
        ry: 8,
        id: id,
        nodeType: "data-input",
    });

    const label = new fabric.Text("Data", {
        fontSize: 13,
        fill: "#fff",
        fontWeight: "bold",
        fontFamily: "Inter, sans-serif",
        left: 16,
        top: 14,
        selectable: false,
    });

    const group = new fabric.Group([rect, label], {
        left: x - 40,
        top: y - 25,
        id: id,
        nodeType: "data-input",
        subTargetCheck: true,
    });

    this.canvas.add(group);
    this.nodes.push(group);
    return group;
};
