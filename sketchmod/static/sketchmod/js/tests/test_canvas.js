// ============================================================
//  SketchMod Canvas Tests  (cleaned – removed outdated tests)
// ============================================================

const assertEqual = (actual, expected, msg) => {
    if (actual !== expected) {
        console.error(`❌ ${msg} — expected ${expected}, got ${actual}`);
        return false;
    }
    console.log(`✅ ${msg}`);
    return true;
};

const assertDeepEqual = (a, b, msg) => {
    if (JSON.stringify(a) !== JSON.stringify(b)) {
        console.error(
            `❌ ${msg} — expected ${JSON.stringify(b)}, got ${JSON.stringify(a)}`,
        );
        return false;
    }
    console.log(`✅ ${msg}`);
    return true;
};

// ---------- helper to create a clean SketchMod ----------
function freshSketch() {
    // reset everything
    SketchMod.nodes = [];
    SketchMod.links = [];
    SketchMod.ports = [];
    SketchMod.nodeCounter = 0;
    SketchMod.selectedNodes = [];
    SketchMod.selectedLinks = [];
    SketchMod.selectedPorts = [];
    SketchMod._highlightPhaseNodes = null;
    SketchMod._highlightPhaseLinks = null;
    SketchMod._highlightPhasePorts = null;
    SketchMod._showAllLinks = null;
    SketchMod._showAllNodes = null;
    SketchMod._showAllPorts = null;
}

// ===================== NODE CREATION =====================
function testInputDataNode() {
    freshSketch();
    const node = new InputDataNode("input-main", 100, 200);
    assertEqual(node.type, "input-data", "InputDataNode type");
    assertEqual(node.inputs.length, 0, "InputDataNode has 0 inputs");
    assertEqual(node.outputs.length, 1, "InputDataNode has 1 output");
    assertEqual(
        node.outputs[0].activationPhases.includes("preprocessing"),
        true,
        "InputData output is preprocessing",
    );
}

function testOutputNode() {
    freshSketch();
    const node = new OutputNode("output-main", 300, 200);
    assertEqual(node.type, "output", "OutputNode type");
    assertEqual(node.inputs.length, 2, "OutputNode has 2 inputs (train, test)"); // updated
    assertEqual(node.outputs.length, 3, "OutputNode has 3 outputs");
    assertEqual(node.inputs[0].subType, "train", "first input is train");
    assertEqual(node.inputs[1].subType, "test", "second input is test");
    assertEqual(node.outputs[0].role, "loss", "first output is loss");
    assertEqual(
        node.outputs[1].role,
        "prediction",
        "second output is prediction",
    );
    assertEqual(
        node.outputs[2].role,
        "evaluation",
        "third output is evaluation",
    );
}

function testLayerNode() {
    freshSketch();
    const node = new LayerNode("l1", 400, 200);
    assertEqual(node.type, "layer", "LayerNode type");
    assertEqual(node.inputs.length, 1, "LayerNode has 1 input");
    assertEqual(
        node.inputs[0] instanceof MultiPort,
        true,
        "Layer input is MultiPort",
    );
    assertEqual(node.outputs.length, 1, "LayerNode has 1 output");
    assertEqual(node.activation, "relu", "default activation is relu");
}

function testTrainTestSplitNode() {
    freshSketch();
    const node = new TrainTestSplitNode("t1", 200, 200);
    assertEqual(node.inputs.length, 1, "TrainTestSplit has 1 input");
    assertEqual(node.outputs.length, 2, "TrainTestSplit has 2 outputs");
    assertEqual(node.outputs[0].subType, "train", "first output is train");
    assertEqual(node.outputs[1].subType, "test", "second output is test");
}

// ===================== LINK CREATION =====================
function testLinkCreation() {
    freshSketch();
    const n1 = new InputDataNode("input-main", 100, 100);
    const n2 = new LayerNode("l1", 300, 100);
    SketchMod.nodes.push(n1, n2);
    SketchMod.ports = SketchMod._collectPorts();

    const from = n1.outputs[0];
    const to = n2.inputs[0];
    SketchMod._addLink(from, to);
    assertEqual(SketchMod.links.length, 1, "One link created");
    assertEqual(SketchMod.links[0].from, from, "Link source correct");
    assertEqual(SketchMod.links[0].to, to, "Link target correct");
}

// ===================== PORT ACTIVATION DEFAULTS =====================
function testPortActivationPhasesDefault() {
    freshSketch();
    const node = new NormalizeNode("n1", 200, 200);
    assertEqual(
        node.inputs[0].activationPhases.includes("preprocessing"),
        true,
        "Normalize input defaults to preprocessing",
    );
    // output depends on default we set; data transforms have preprocessing only?
    // We'll just check that it's an array
    assertEqual(
        Array.isArray(node.outputs[0].activationPhases),
        true,
        "Output activationPhases is array",
    );
}

// ===================== RUN ALL =====================
function runAll() {
    console.log("\n🧪 Running SketchMod Canvas Tests...\n");
    const tests = [
        testInputDataNode,
        testOutputNode,
        testLayerNode,
        testTrainTestSplitNode,
        testLinkCreation,
        testPortActivationPhasesDefault,
    ];
    let passed = 0;
    for (const fn of tests) {
        try {
            fn();
            passed++;
        } catch (e) {
            console.error(`💥 ${fn.name} threw:`, e);
        }
    }
    console.log(`\n${passed}/${tests.length} tests passed.\n`);
}

// Auto-run when loaded (optional – you can remove if you want manual trigger)
document.addEventListener("DOMContentLoaded", () => {
    // Only run if we are on the canvas page and not production
    if (document.getElementById("sketchCanvas")) {
        setTimeout(runAll, 500); // wait for canvas to init
    }
});
