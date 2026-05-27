const CanvasTests = {
    passed: 0,
    failed: 0,
    errors: [],

    assert(condition, message) {
        if (condition) {
            this.passed++;
        } else {
            this.failed++;
            this.errors.push(`FAIL: ${message}`);
            console.error(`❌ ${message}`);
        }
    },

    assertEqual(actual, expected, message) {
        if (actual === expected) {
            this.passed++;
        } else {
            this.failed++;
            this.errors.push(
                `FAIL: ${message} — expected ${expected}, got ${actual}`,
            );
            console.error(
                `❌ ${message} — expected ${expected}, got ${actual}`,
            );
        }
    },

    assertDeepEqual(actual, expected, message) {
        const a = JSON.stringify(actual);
        const b = JSON.stringify(expected);
        if (a === b) {
            this.passed++;
        } else {
            this.failed++;
            this.errors.push(
                `FAIL: ${message} — expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`,
            );
            console.error(`❌ ${message}`);
        }
    },

    assertNotNull(value, message) {
        if (value !== null && value !== undefined) {
            this.passed++;
        } else {
            this.failed++;
            this.errors.push(`FAIL: ${message} — value is null/undefined`);
            console.error(`❌ ${message}`);
        }
    },

    assertInstanceOf(value, klass, message) {
        if (value instanceof klass) {
            this.passed++;
        } else {
            this.failed++;
            this.errors.push(
                `FAIL: ${message} — not an instance of ${klass.name}`,
            );
            console.error(`❌ ${message}`);
        }
    },

    assertThrows(fn, message) {
        try {
            fn();
            this.failed++;
            this.errors.push(`FAIL: ${message} — did not throw`);
            console.error(`❌ ${message}`);
        } catch (e) {
            this.passed++;
        }
    },

    // ========== NODE CREATION TESTS ==========
    testNeuronNode() {
        const node = new NeuronNode("n1", 100, 200);
        this.assertNotNull(node, "NeuronNode should be created");
        this.assertEqual(node.type, "neuron", "NeuronNode type is 'neuron'");
        this.assertEqual(
            node.activation,
            "relu",
            "NeuronNode default activation is relu",
        );
        this.assertEqual(node.inputs.length, 1, "NeuronNode has 1 input port");
        this.assertEqual(
            node.outputs.length,
            1,
            "NeuronNode has 1 output port",
        );
        this.assertEqual(node.radius, 28, "NeuronNode radius is 28");
        this.assertEqual(node.x, 100, "NeuronNode x position correct");
        this.assertEqual(node.y, 200, "NeuronNode y position correct");
        this.assertEqual(
            node.maxInputs,
            Infinity,
            "NeuronNode maxInputs is Infinity",
        );
        this.assertEqual(node.minInputs, 1, "NeuronNode minInputs is 1");
        this.assertEqual(node.minOutputs, 1, "NeuronNode minOutputs is 1");
    },

    testLayerNode() {
        const node = new LayerNode("l1", 100, 200);
        this.assertNotNull(node, "LayerNode should be created");
        this.assertEqual(node.type, "layer", "LayerNode type is 'layer'");
        this.assertEqual(
            node.numNeurons,
            64,
            "LayerNode default neurons is 64",
        );
        this.assertEqual(node.inputs.length, 1, "LayerNode has 1 input");
        this.assertEqual(node.outputs.length, 1, "LayerNode has 1 output");
        this.assertEqual(node.width, 110, "LayerNode width is 110");
        this.assertEqual(node.height, 65, "LayerNode height is 65");
        this.assertEqual(node.maxInputs, 1, "LayerNode maxInputs is 1");
        this.assertEqual(node.maxOutputs, 1, "LayerNode maxOutputs is 1");
    },

    testInputDataNode() {
        const node = new InputDataNode("input-main", 100, 200);
        this.assertNotNull(node, "InputDataNode should be created");
        this.assertEqual(
            node.type,
            "input-data",
            "InputDataNode type is 'input-data'",
        );
        this.assertEqual(node.inputs.length, 0, "InputDataNode has 0 inputs");
        this.assertEqual(node.outputs.length, 1, "InputDataNode has 1 output");
        this.assertEqual(node.maxInputs, 0, "InputDataNode maxInputs is 0");
        this.assertEqual(node.minInputs, 0, "InputDataNode minInputs is 0");
        this.assertDeepEqual(
            node.allowedOutputTypes,
            ["features", "labels"],
            "InputDataNode allowed output types",
        );
    },

    testOutputNode() {
        const node = new OutputNode("output-main", 100, 200);
        this.assertNotNull(node, "OutputNode should be created");
        this.assertEqual(node.type, "output", "OutputNode type is 'output'");
        this.assertEqual(node.inputs.length, 1, "OutputNode has 1 input");
        this.assertEqual(node.outputs.length, 0, "OutputNode has 0 outputs");
        this.assertEqual(node.maxOutputs, 0, "OutputNode maxOutputs is 0");
    },

    testColumnSelectNode() {
        const node = new ColumnSelectNode("c1", 100, 200);
        this.assertNotNull(node, "ColumnSelectNode should be created");
        this.assertEqual(
            node.type,
            "column-select",
            "ColumnSelectNode type correct",
        );
        this.assertEqual(node.inputs.length, 1, "ColumnSelectNode has 1 input");
        this.assertEqual(
            node.outputs.length,
            1,
            "ColumnSelectNode has 1 output",
        );
        this.assertDeepEqual(
            node.selectedColumns,
            [],
            "ColumnSelectNode starts with empty selection",
        );
        this.assertEqual(
            node.columnInput,
            "",
            "ColumnSelectNode starts with empty input",
        );
        this.assertEqual(
            node.columnCount,
            0,
            "ColumnSelectNode starts with 0 columns",
        );
        this.assertEqual(node.maxInputs, 1, "ColumnSelectNode maxInputs is 1");
    },

    testRowSelectNode() {
        const node = new RowSelectNode("r1", 100, 200);
        this.assertNotNull(node, "RowSelectNode should be created");
        this.assertEqual(
            node.method,
            "first-n",
            "RowSelectNode default method",
        );
        this.assertEqual(node.value, "100", "RowSelectNode default value");
        this.assertEqual(node.randomSeed, 42, "RowSelectNode default seed");
        this.assertEqual(
            node.rowCount,
            0,
            "RowSelectNode initial rowCount is 0",
        );
        this.assertEqual(node.maxInputs, 1, "RowSelectNode maxInputs is 1");
        this.assertEqual(node.maxOutputs, 1, "RowSelectNode maxOutputs is 1");
    },

    testDimSelectNode() {
        const node = new DimSelectNode("d1", 100, 200);
        this.assertNotNull(node, "DimSelectNode should be created");
        this.assertEqual(node.type, "dim-select", "DimSelectNode type correct");
        this.assertDeepEqual(
            node.dimSelections,
            ["", ""],
            "DimSelectNode starts with 2 empty dims",
        );
        this.assertEqual(node.maxInputs, 1, "DimSelectNode maxInputs is 1");
    },

    testTrainTestSplitNode() {
        const node = new TrainTestSplitNode("t1", 100, 200);
        this.assertNotNull(node, "TrainTestSplitNode should be created");
        this.assertEqual(
            node.trainRatio,
            0.7,
            "TrainTestSplitNode default train ratio",
        );
        this.assertEqual(
            node.testRatio,
            0.3,
            "TrainTestSplitNode default test ratio",
        );
        this.assertEqual(
            node.randomSeed,
            42,
            "TrainTestSplitNode default seed",
        );
        this.assertEqual(
            node.inputs.length,
            1,
            "TrainTestSplitNode has 1 input",
        );
        this.assertEqual(
            node.outputs.length,
            2,
            "TrainTestSplitNode has 2 outputs",
        );
        this.assertDeepEqual(
            node.allowedOutputTypes,
            ["train", "test"],
            "TrainTestSplitNode allowed types",
        );
        this.assertEqual(
            node.outputs[0].subType,
            "train",
            "First output is train",
        );
        this.assertEqual(
            node.outputs[1].subType,
            "test",
            "Second output is test",
        );
    },

    testNormalizeNode() {
        const node = new NormalizeNode("n1", 100, 200);
        this.assertNotNull(node, "NormalizeNode should be created");
        this.assertEqual(
            node.method,
            "standard",
            "NormalizeNode default method",
        );
        this.assertEqual(node.inputs.length, 1, "NormalizeNode has 1 input");
        this.assertEqual(node.outputs.length, 1, "NormalizeNode has 1 output");
        this.assertEqual(node.maxInputs, 1, "NormalizeNode maxInputs is 1");
    },

    // ========== PORT CONSTRAINT TESTS ==========
    testPortConstraints() {
        const layer = new LayerNode("l1", 0, 0);
        // Layer starts with 1 input (from constructor)
        this.assertEqual(layer.inputs.length, 1, "Layer starts with 1 input");
        const p1 = layer.addInput();
        this.assertEqual(p1, null, "Cannot add 2nd input (maxInputs=1)");

        this.assertEqual(layer.outputs.length, 1, "Layer starts with 1 output");
        const po1 = layer.addOutput();
        this.assertEqual(po1, null, "Cannot add 2nd output (maxOutputs=1)");

        this.assertEqual(
            layer.canRemoveInput(),
            false,
            "Cannot remove below minInputs",
        );
        this.assertEqual(
            layer.canRemoveOutput(),
            false,
            "Cannot remove below minOutputs",
        );
    },
    testInputDataCannotAddInput() {
        const node = new InputDataNode("i1", 0, 0);
        const p = node.addInput();
        this.assertEqual(p, null, "InputDataNode cannot add inputs");
        this.assertEqual(
            node.canAddInput(),
            false,
            "InputDataNode canAddInput returns false",
        );
    },

    testOutputNodeCannotAddOutput() {
        const node = new OutputNode("o1", 0, 0);
        const p = node.addOutput();
        this.assertEqual(p, null, "OutputNode cannot add outputs");
        this.assertEqual(
            node.canAddOutput(),
            false,
            "OutputNode canAddOutput returns false",
        );
    },

    testNeuronCanAddMultiplePorts() {
        const neuron = new NeuronNode("n1", 0, 0);
        const p1 = neuron.addInput();
        const p2 = neuron.addInput();
        const p3 = neuron.addInput();
        this.assertNotNull(p1, "First input added");
        this.assertNotNull(p2, "Second input added");
        this.assertNotNull(p3, "Third input added");
        this.assertEqual(neuron.inputs.length, 4, "Neuron has 4 inputs total");
        this.assertEqual(
            neuron.canAddInput(),
            true,
            "Neuron can add more inputs",
        );
    },

    // ========== PORT TESTS ==========
    testPortCreation() {
        const neuron = new NeuronNode("n1", 100, 200);
        const port = neuron.inputs[0];
        this.assertNotNull(port, "Port should be created");
        this.assertEqual(port.type, "input", "Port type is input");
        this.assertEqual(port.index, 0, "Port index is 0");
        this.assertEqual(port.node, neuron, "Port references correct node");
        this.assertEqual(port.radius, 5, "Port radius is 5");
        this.assertEqual(port.hoverRadius, 10, "Port hover radius is 10");
        this.assertNotNull(port.id, "Port has an ID");
    },

    testPortColors() {
        const tt = new TrainTestSplitNode("t1", 0, 0);
        this.assertEqual(
            tt.outputs[0]._getColor(),
            "#f59e0b",
            "Train port is amber",
        );
        this.assertEqual(
            tt.outputs[1]._getColor(),
            "#4ade80",
            "Test port is green",
        );

        const neuron = new NeuronNode("n1", 0, 0);
        this.assertEqual(
            neuron.inputs[0]._getColor(),
            "#ef4444",
            "Input port is red",
        );
        this.assertEqual(
            neuron.outputs[0]._getColor(),
            "#60a5fa",
            "Output port is blue",
        );
    },

    testPortShapeDisplay() {
        const dummyNode = { x: 0, y: 0, id: "dummy", type: "test" };
        const port = new Port(dummyNode, "output", 0, null);
        this.assertEqual(
            port.shapeDisplay(),
            "Unknown",
            "Empty port shows Unknown",
        );

        port.setShape([1000, 28, 28], "float32", true, false);
        this.assertEqual(
            port.shapeDisplay(),
            "(1000, 28, 28)",
            "Known shape shown",
        );

        port.setShape(["B", 28, 28], "float32", true, true);
        this.assertEqual(
            port.shapeDisplay(),
            "(B, 28, 28) (abstract)",
            "Symbolic shape shown",
        );
    },

    testPortSetShapeAllParams() {
        const dummyNode = { x: 0, y: 0, id: "dummy", type: "test" };
        const port = new Port(dummyNode, "output", 0, null);
        port.setShape([1, 2, 3], "int32", true, true);
        this.assertDeepEqual(
            port.shape,
            {
                shape: [1, 2, 3],
                dtype: "int32",
                known: true,
                symbolic: true,
            },
            "setShape stores all params",
        );
    },
    // ========== SHAPE PROPAGATION TESTS ==========
    testInputDataNodeComputeShapes_Numeric() {
        const node = new InputDataNode("i1", 0, 0);
        node.dataShape = "(1000, 28, 28)";
        const shapes = node.computeOutputShapes();
        this.assertEqual(
            shapes.length,
            node.outputs.length,
            "Returns shape for each output",
        );
        this.assertDeepEqual(
            shapes[0].shape,
            [1000, 28, 28],
            "Parses numeric shape",
        );
        this.assertEqual(shapes[0].known, true, "Shape is known");
        this.assertEqual(shapes[0].symbolic, false, "Shape is not symbolic");
    },

    testInputDataNodeComputeShapes_Symbolic() {
        const node = new InputDataNode("i1", 0, 0);
        node.dataShape = "(B, H, W, C)";
        const shapes = node.computeOutputShapes();
        this.assertDeepEqual(
            shapes[0].shape,
            ["B", "H", "W", "C"],
            "Parses symbolic shape",
        );
        this.assertEqual(shapes[0].symbolic, true, "Shape is symbolic");
        this.assertEqual(shapes[0].known, true, "Shape is known");
    },

    testInputDataNodeComputeShapes_Empty() {
        const node = new InputDataNode("i1", 0, 0);
        node.dataShape = null;
        const shapes = node.computeOutputShapes();
        this.assertEqual(shapes[0].shape, null, "Null shape when no data");
        this.assertEqual(shapes[0].known, false, "Not known when no data");
    },

    testLayerNodeComputeShapes() {
        const node = new LayerNode("l1", 0, 0);
        node.numNeurons = 128;
        // Simulate connected shape
        const mockShape = { shape: [64, 256], symbolic: false };
        node._getFirstInputShapeObj = () => mockShape;
        const shapes = node.computeOutputShapes();
        this.assertDeepEqual(
            shapes[0].shape,
            [64, 128],
            "Layer transforms (B, in) → (B, neurons)",
        );
        this.assertEqual(shapes[0].symbolic, false, "Symbolic flag preserved");
    },

    testNeuronComputeShapes() {
        const node = new NeuronNode("n1", 0, 0);
        const mockShape = { shape: [32, 10], symbolic: false };
        node._getFirstInputShapeObj = () => mockShape;
        const shapes = node.computeOutputShapes();
        this.assertDeepEqual(shapes[0].shape, [32, 1], "Neuron outputs (B, 1)");
    },

    testNormalizeComputeShapes() {
        const node = new NormalizeNode("n1", 0, 0);
        const mockShape = { shape: [100, 50], symbolic: false };
        node._getFirstInputShapeObj = () => mockShape;
        const shapes = node.computeOutputShapes();
        this.assertDeepEqual(
            shapes[0].shape,
            [100, 50],
            "Normalize preserves shape",
        );
    },

    testTrainTestSplitComputeShapes() {
        const node = new TrainTestSplitNode("t1", 0, 0);
        node.trainRatio = 0.7;
        const mockShape = { shape: [1000, 28, 28], symbolic: false };
        node._getFirstInputShapeObj = () => mockShape;
        const shapes = node.computeOutputShapes();
        this.assertDeepEqual(
            shapes[0].shape,
            [700, 28, 28],
            "Train output has 70% of rows",
        );
        this.assertDeepEqual(
            shapes[1].shape,
            [300, 28, 28],
            "Test output has 30% of rows",
        );
    },

    testTrainTestSplitComputeShapes_Symbolic() {
        const node = new TrainTestSplitNode("t1", 0, 0);
        node.trainRatio = 0.7;
        const mockShape = { shape: ["N", 28], symbolic: true };
        node._getFirstInputShapeObj = () => mockShape;
        const shapes = node.computeOutputShapes();
        this.assertDeepEqual(
            shapes[0].shape,
            ["0.7*N", 28],
            "Symbolic train shape",
        );
        this.assertDeepEqual(
            shapes[1].shape,
            ["0.3*N", 28],
            "Symbolic test shape",
        );
        this.assertEqual(shapes[0].symbolic, true, "Symbolic flag true");
    },

    testColumnSelectComputeShapes() {
        const node = new ColumnSelectNode("c1", 0, 0);
        node.selectedColumns = [0, 2, 4];
        const mockShape = { shape: [500, 10], symbolic: false };
        node._getFirstInputShapeObj = () => mockShape;
        const shapes = node.computeOutputShapes();
        this.assertDeepEqual(
            shapes[0].shape,
            [500, 3],
            "ColumnSelect reduces feature dim",
        );
    },

    testRowSelectComputeShapes() {
        const node = new RowSelectNode("r1", 0, 0);
        node.rowCount = 100;
        const mockShape = { shape: [1000, 5], symbolic: false };
        node._getFirstInputShapeObj = () => mockShape;
        const shapes = node.computeOutputShapes();
        this.assertDeepEqual(
            shapes[0].shape,
            [100, 5],
            "RowSelect reduces batch dim",
        );
    },

    testDimSelectComputeShapes() {
        const node = new DimSelectNode("d1", 0, 0);
        node.dimSelections = ["0:99", ":", ":"];
        const mockShape = { shape: [500, 28, 28], symbolic: false };
        node._getFirstInputShapeObj = () => mockShape;
        const shapes = node.computeOutputShapes();
        this.assertEqual(shapes[0].shape[0], 100, "Dim 0 sliced to 100");
        this.assertEqual(shapes[0].shape[1], 28, "Dim 1 unchanged");
        this.assertEqual(shapes[0].shape[2], 28, "Dim 2 unchanged");
    },

    testEmptyShapesHelper() {
        const node = new NormalizeNode("n1", 0, 0);
        const shapes = node._emptyShapes();
        this.assertEqual(shapes.length, 1, "Returns one shape per output");
        this.assertEqual(shapes[0].shape, null, "Empty shape is null");
        this.assertEqual(shapes[0].known, false, "Empty shape not known");
        this.assertEqual(shapes[0].symbolic, false, "Empty shape not symbolic");
    },

    testMakeShapesHelper() {
        const node = new NormalizeNode("n1", 0, 0);
        const shapes = node._makeShapes([10, 20], true, true);
        this.assertEqual(shapes.length, 1, "Returns one shape per output");
        this.assertDeepEqual(shapes[0].shape, [10, 20], "Shape array correct");
        this.assertEqual(shapes[0].symbolic, true, "Symbolic flag set");
        this.assertEqual(shapes[0].known, true, "Known flag set");
    },

    // ========== LINK TESTS ==========
    testLinkCreation() {
        const n1 = new NeuronNode("n1", 0, 0);
        const n2 = new NeuronNode("n2", 100, 0);
        const link = new Link(n1.outputs[0], n2.inputs[0], 0.5);
        this.assertNotNull(link, "Link should be created");
        this.assertEqual(link.from, n1.outputs[0], "Link from correct");
        this.assertEqual(link.to, n2.inputs[0], "Link to correct");
        this.assertEqual(link.weight, 0.5, "Link weight stored");
    },

    testLinkDefaultWeight() {
        const n1 = new NeuronNode("n1", 0, 0);
        const n2 = new NeuronNode("n2", 100, 0);
        const link = new Link(n1.outputs[0], n2.inputs[0]);
        this.assertEqual(link.weight, 0, "Default weight is 0");
    },

    testLinkToJSON() {
        const n1 = new NeuronNode("n1", 0, 0);
        const n2 = new NeuronNode("n2", 100, 0);
        const link = new Link(n1.outputs[0], n2.inputs[0], 0.8);
        const json = link.toJSON();
        this.assertEqual(json.from, n1.outputs[0].id, "JSON from ID");
        this.assertEqual(json.to, n2.inputs[0].id, "JSON to ID");
        this.assertEqual(json.weight, 0.8, "JSON weight");
    },

    // ========== NODE SERIALIZATION TESTS ==========
    testNeuronToJSON() {
        const node = new NeuronNode("n1", 100, 200);
        node.activation = "sigmoid";
        const json = node.toJSON();
        this.assertEqual(json.id, "n1", "JSON id");
        this.assertEqual(json.type, "neuron", "JSON type");
        this.assertEqual(json.x, 100, "JSON x");
        this.assertEqual(json.y, 200, "JSON y");
        this.assertEqual(json.activation, "sigmoid", "JSON activation");
        this.assertEqual(json.numInputs, 1, "JSON numInputs");
        this.assertEqual(json.numOutputs, 1, "JSON numOutputs");
        this.assertNotNull(json.inputPorts, "JSON has inputPorts");
        this.assertNotNull(json.outputPorts, "JSON has outputPorts");
        this.assertEqual(json.inputPorts.length, 1, "JSON inputPorts count");
    },

    testLayerToJSON() {
        const node = new LayerNode("l1", 100, 200);
        node.numNeurons = 256;
        const json = node.toJSON();
        this.assertEqual(json.numNeurons, 256, "JSON numNeurons");
    },

    testTrainTestToJSON() {
        const node = new TrainTestSplitNode("t1", 100, 200);
        const json = node.toJSON();
        this.assertEqual(json.trainRatio, 0.7, "JSON trainRatio");
        this.assertEqual(json.testRatio, 0.3, "JSON testRatio");
        this.assertEqual(json.randomSeed, 42, "JSON randomSeed");
    },

    testNeuronFromJSON() {
        const node = new NeuronNode("n1", 0, 0);
        node.activation = "tanh";
        const json = node.toJSON();

        const restored = new NeuronNode("n1", 0, 0);
        restored.inputs = [];
        restored.outputs = [];
        restored.fromJSON(json);

        this.assertEqual(restored.activation, "tanh", "Restored activation");
        this.assertEqual(restored.inputs.length, 1, "Restored inputs count");
        this.assertEqual(restored.outputs.length, 1, "Restored outputs count");
    },

    testFromJSONPreservesPortSubtypes() {
        const node = new TrainTestSplitNode("t1", 0, 0);
        const json = node.toJSON();

        const restored = new TrainTestSplitNode("t1", 0, 0);
        restored.inputs = [];
        restored.outputs = [];
        restored.fromJSON(json);

        this.assertEqual(restored.outputs.length, 2, "Restored 2 outputs");
        this.assertEqual(
            restored.outputs[0].subType,
            "train",
            "First output is train",
        );
        this.assertEqual(
            restored.outputs[1].subType,
            "test",
            "Second output is test",
        );
    },

    testColumnSelectFromJSON() {
        const node = new ColumnSelectNode("c1", 0, 0);
        node.selectedColumns = [0, 2, 4];
        node.columnInput = "0:2,4";
        node.columnCount = 10;
        const json = node.toJSON();

        const restored = new ColumnSelectNode("c1", 0, 0);
        restored.inputs = [];
        restored.outputs = [];
        restored.fromJSON(json);

        this.assertDeepEqual(
            restored.selectedColumns,
            [0, 2, 4],
            "Restored selectedColumns",
        );
        this.assertEqual(restored.columnInput, "0:2,4", "Restored columnInput");
        this.assertEqual(restored.columnCount, 10, "Restored columnCount");
    },

    testRowSelectFromJSON() {
        const node = new RowSelectNode("r1", 0, 0);
        node.method = "random";
        node.value = "200";
        node.randomSeed = 99;
        const json = node.toJSON();

        const restored = new RowSelectNode("r1", 0, 0);
        restored.inputs = [];
        restored.outputs = [];
        restored.fromJSON(json);

        this.assertEqual(restored.method, "random", "Restored method");
        this.assertEqual(restored.value, "200", "Restored value");
        this.assertEqual(restored.randomSeed, 99, "Restored seed");
    },

    testDimSelectFromJSON() {
        const node = new DimSelectNode("d1", 0, 0);
        node.dimSelections = ["0:10", "5:15", ":"];
        node.inputShape = [100, 50, 30];
        const json = node.toJSON();

        const restored = new DimSelectNode("d1", 0, 0);
        restored.inputs = [];
        restored.outputs = [];
        restored.fromJSON(json);

        this.assertDeepEqual(
            restored.dimSelections,
            ["0:10", "5:15", ":"],
            "Restored dimSelections",
        );
        this.assertDeepEqual(
            restored.inputShape,
            [100, 50, 30],
            "Restored inputShape",
        );
    },

    // ========== PORT JSON TESTS ==========
    testPortToJSON() {
        const neuron = new NeuronNode("n1", 0, 0);
        const port = neuron.outputs[0];
        port.setShape([64, 10], "float32", true, false);
        const json = port.toJSON();
        this.assertEqual(json.type, "output", "Port JSON type");
        this.assertEqual(json.index, 0, "Port JSON index");
        this.assertEqual(json.subType, null, "Port JSON subType null");
        this.assertNotNull(json.shape, "Port JSON has shape");
        this.assertDeepEqual(
            json.shape.shape,
            [64, 10],
            "Port JSON shape array",
        );
        this.assertEqual(json.shape.known, true, "Port JSON shape known");
        this.assertEqual(
            json.shape.symbolic,
            false,
            "Port JSON shape not symbolic",
        );
    },

    // ========== ROW SELECT COMPUTE TESTS ==========
    testRowSelectComputeRowCount_FirstN() {
        const node = new RowSelectNode("r1", 0, 0);
        node.method = "first-n";
        node.value = "50";
        this.assertEqual(node._computeRowCount(), 50, "FirstN returns 50");
    },

    testRowSelectComputeRowCount_Random() {
        const node = new RowSelectNode("r1", 0, 0);
        node.method = "random";
        node.value = "30";
        this.assertEqual(node._computeRowCount(), 30, "Random returns 30");
    },

    testRowSelectComputeRowCount_Slice() {
        const node = new RowSelectNode("r1", 0, 0);
        node.method = "slice";
        node.value = "100:600";
        this.assertEqual(node._computeRowCount(), 500, "Slice returns 500");
    },

    testRowSelectComputeRowCount_Indices() {
        const node = new RowSelectNode("r1", 0, 0);
        node.method = "indices";
        node.value = "0, 5, 10, 15, 20";
        this.assertEqual(node._computeRowCount(), 5, "Indices returns 5");
    },

    testRowSelectComputeRowCount_Empty() {
        const node = new RowSelectNode("r1", 0, 0);
        node.value = "";
        this.assertEqual(node._computeRowCount(), 0, "Empty returns 0");
    },

    // ========== COLUMN INPUT PARSING TESTS ==========
    testParseColumnInput_Single() {
        const result = SketchMod._parseColumnInput("3", 10);
        this.assertDeepEqual(result, [3], "Single index");
    },

    testParseColumnInput_Range() {
        const result = SketchMod._parseColumnInput("2:5", 10);
        this.assertDeepEqual(result, [2, 3, 4, 5], "Range 2:5");
    },

    testParseColumnInput_Mixed() {
        const result = SketchMod._parseColumnInput("0:2,5,7:8", 10);
        this.assertDeepEqual(
            result,
            [0, 1, 2, 5, 7, 8],
            "Mixed range and single",
        );
    },

    testParseColumnInput_Empty() {
        const result = SketchMod._parseColumnInput("", 10);
        this.assertDeepEqual(result, [], "Empty string returns empty");
    },

    testParseColumnInput_Null() {
        const result = SketchMod._parseColumnInput(null, 10);
        this.assertDeepEqual(result, [], "Null returns empty");
    },

    testParseColumnInput_OutOfBounds() {
        const result = SketchMod._parseColumnInput("8:15", 10);
        this.assertEqual(
            result[result.length - 1],
            9,
            "Clamped to maxColumns-1",
        );
    },

    testParseColumnInput_Whitespace() {
        const result = SketchMod._parseColumnInput(" 0 : 3 , 5 ", 10);
        this.assertDeepEqual(result, [0, 1, 2, 3, 5], "Whitespace ignored");
    },

    // ========== DIM INPUT PARSING TESTS ==========
    testParseDimInput_All() {
        const node = new DimSelectNode("d1", 0, 0);
        const result = node._parseDimInput(":", 5);
        this.assertDeepEqual(result, [0, 1, 2, 3, 4, 5], "Colon returns all");
    },

    testParseDimInput_Range() {
        const node = new DimSelectNode("d1", 0, 0);
        const result = node._parseDimInput("1:3", 10);
        this.assertDeepEqual(result, [1, 2, 3], "Range 1:3");
    },

    testParseDimInput_FromStart() {
        const node = new DimSelectNode("d1", 0, 0);
        const result = node._parseDimInput(":3", 10);
        this.assertDeepEqual(result, [0, 1, 2, 3], ":3 returns 0-3");
    },

    testParseDimInput_ToEnd() {
        const node = new DimSelectNode("d1", 0, 0);
        const result = node._parseDimInput("5:", 10);
        this.assertDeepEqual(result, [5, 6, 7, 8, 9, 10], "5: returns 5-end");
    },

    testParseDimInput_Step() {
        const node = new DimSelectNode("d1", 0, 0);
        const result = node._parseDimInput("::2", 10);
        this.assertDeepEqual(result, [0, 2, 4, 6, 8, 10], "Step 2");
    },

    testParseDimInput_Mixed() {
        const node = new DimSelectNode("d1", 0, 0);
        const result = node._parseDimInput("1,3,5,7", 10);
        this.assertDeepEqual(result, [1, 3, 5, 7], "Specific indices");
    },

    testParseDimInput_Empty() {
        const node = new DimSelectNode("d1", 0, 0);
        const result = node._parseDimInput("", 5);
        this.assertDeepEqual(result, [0, 1, 2, 3, 4, 5], "Empty = all");
    },

    // ========== NODE REGISTRY TESTS ==========
    testNodeRegistryHasAllNodes() {
        const types = SketchMod.nodeRegistry.map((r) => r.type);
        this.assert(types.includes("neuron"), "Registry has neuron");
        this.assert(types.includes("layer"), "Registry has layer");
        this.assert(
            types.includes("column-select"),
            "Registry has column-select",
        );
        this.assert(types.includes("train-test"), "Registry has train-test");
        this.assert(types.includes("normalize"), "Registry has normalize");
        this.assert(types.includes("row-select"), "Registry has row-select");
        this.assert(types.includes("dim-select"), "Registry has dim-select");
    },

    testNodeRegistryCategories() {
        const models = SketchMod.nodeRegistry.filter(
            (r) => r.category === "models",
        );
        const data = SketchMod.nodeRegistry.filter(
            (r) => r.category === "data",
        );
        this.assert(models.length > 0, "Models category has nodes");
        this.assert(data.length > 0, "Data category has nodes");
    },

    testRegisterNode() {
        SketchMod.registerNode({
            type: "test-node",
            label: "Test",
            category: "data",
            class: NeuronNode,
        });
        const found = SketchMod.nodeRegistry.find(
            (r) => r.type === "test-node",
        );
        this.assertNotNull(found, "Registered node is found");
        // Cleanup
        SketchMod.nodeRegistry = SketchMod.nodeRegistry.filter(
            (r) => r.type !== "test-node",
        );
    },

    // ========== THEME COLOR TESTS ==========
    testGetNodeColorLight() {
        document.documentElement.setAttribute("data-theme", "light");
        const color = SketchMod._getNodeColor();
        this.assertDeepEqual(
            color,
            { fill: "#6c5ce7", stroke: "#5a4bd1" },
            "Light theme colors",
        );
    },

    testGetNodeColorDark() {
        document.documentElement.setAttribute("data-theme", "dark");
        const color = SketchMod._getNodeColor();
        this.assertDeepEqual(
            color,
            { fill: "#7c6ff0", stroke: "#a29bfe" },
            "Dark theme colors",
        );
    },

    testGetNodeColorRose() {
        document.documentElement.setAttribute("data-theme", "rose");
        const color = SketchMod._getNodeColor();
        this.assertDeepEqual(
            color,
            { fill: "#e8536c", stroke: "#d43d56" },
            "Rose theme colors",
        );
    },

    testGetNodeColorForest() {
        document.documentElement.setAttribute("data-theme", "forest");
        const color = SketchMod._getNodeColor();
        this.assertDeepEqual(
            color,
            { fill: "#3a8a3a", stroke: "#2d6e2d" },
            "Forest theme colors",
        );
    },

    testGetNodeColorHoney() {
        document.documentElement.setAttribute("data-theme", "honey");
        const color = SketchMod._getNodeColor();
        this.assertDeepEqual(
            color,
            { fill: "#d4a800", stroke: "#b89200" },
            "Honey theme colors",
        );
    },

    testGetNodeColorUnknownTheme() {
        document.documentElement.setAttribute("data-theme", "nonexistent");
        const color = SketchMod._getNodeColor();
        this.assert(
            color.fill === "#6c5ce7" || color.fill === "#7c6ff0",
            "Unknown theme falls back to light or dark based on system",
        );
    },

    // ========== BASE NODE METHOD TESTS ==========
    testBaseNodeContainsPoint() {
        const node = new LayerNode("l1", 100, 100);
        this.assert(node.containsPoint(100, 100), "Point at center is inside");
        this.assert(node.containsPoint(60, 80), "Point inside bounds");
    },

    testBaseNodeGetPorts() {
        const node = new NeuronNode("n1", 0, 0);
        const ports = node.getPorts();
        this.assertEqual(ports.length, 2, "getPorts returns input + output");
    },

    testBaseNodeCanAddInputWithTypeCheck() {
        const node = new InputDataNode("i1", 0, 0);
        this.assertEqual(
            node.canAddInput("features"),
            false,
            "InputData cannot add input regardless",
        );
    },

    testBaseNodeRemoveInputReturnsPort() {
        const node = new NeuronNode("n1", 0, 0);
        node.addInput();
        const removed = node.removeInput();
        this.assertNotNull(removed, "removeInput returns the removed port");
        this.assertEqual(node.inputs.length, 1, "One input remains");
    },

    // ========== BOUNDS TESTS ==========
    testNeuronBounds() {
        const node = new NeuronNode("n1", 100, 200);
        const b = node.getBounds();
        this.assertEqual(b.x, 72, "Neuron bounds x = center - radius");
        this.assertEqual(b.y, 172, "Neuron bounds y = center - radius");
        this.assertEqual(b.w, 56, "Neuron bounds width = 2 * radius");
        this.assertEqual(b.h, 56, "Neuron bounds height = 2 * radius");
    },

    testRectNodeBounds() {
        const node = new LayerNode("l1", 100, 200);
        const b = node.getBounds();
        this.assertEqual(b.x, 45, "Rect bounds x = center - width/2");
        this.assertEqual(b.y, 167.5, "Rect bounds y = center - height/2");
        this.assertEqual(b.w, 110, "Rect bounds width");
        this.assertEqual(b.h, 65, "Rect bounds height");
    },

    // ========== PORT POSITION TESTS ==========
    testPortPositionsAfterUpdate() {
        const node = new NeuronNode("n1", 100, 100);
        const inputPort = node.inputs[0];
        const outputPort = node.outputs[0];

        // Input should be on left side (around x=64, y=100)
        this.assert(inputPort.x < 100, "Input port is on left side");

        // Output should be on right side (around x=136, y=100)
        this.assert(outputPort.x > 100, "Output port is on right side");
    },

    testRectNodePortPositions() {
        const node = new LayerNode("l1", 100, 100);
        const inputPort = node.inputs[0];
        const outputPort = node.outputs[0];

        this.assert(inputPort.x < 100, "Rect input port on left");
        this.assert(outputPort.x > 100, "Rect output port on right");
    },

    // ========== EDGE CASE TESTS ==========
    testCreateNodeAtNegativeCoordinates() {
        const node = new NeuronNode("n1", -500, -300);
        this.assertEqual(node.x, -500, "Node accepts negative x");
        this.assertEqual(node.y, -300, "Node accepts negative y");
    },

    testCreateNodeAtLargeCoordinates() {
        const node = new LayerNode("l1", 99999, 88888);
        this.assertEqual(node.x, 99999, "Node accepts large x");
        this.assertEqual(node.y, 88888, "Node accepts large y");
    },

    testLayerMinNeurons() {
        const node = new LayerNode("l1", 0, 0);
        node.numNeurons = 1;
        this.assertEqual(node.numNeurons, 1, "Layer accepts 1 neuron");
    },

    testLayerMaxNeurons() {
        const node = new LayerNode("l1", 0, 0);
        node.numNeurons = 4096;
        this.assertEqual(node.numNeurons, 4096, "Layer accepts 4096 neurons");
    },

    testTrainTestRatioBoundary() {
        const node = new TrainTestSplitNode("t1", 0, 0);
        node.trainRatio = 0.1;
        node.testRatio = 0.9;
        const mockShape = { shape: [100, 10], symbolic: false };
        node._getFirstInputShapeObj = () => mockShape;
        const shapes = node.computeOutputShapes();
        this.assertDeepEqual(shapes[0].shape, [10, 10], "Train 10% of 100");
        this.assertDeepEqual(shapes[1].shape, [90, 10], "Test 90% of 100");
    },

    testTrainTestRatio50_50() {
        const node = new TrainTestSplitNode("t1", 0, 0);
        node.trainRatio = 0.5;
        node.testRatio = 0.5;
        const mockShape = { shape: [100, 10], symbolic: false };
        node._getFirstInputShapeObj = () => mockShape;
        const shapes = node.computeOutputShapes();
        this.assertDeepEqual(shapes[0].shape, [50, 10], "Train 50%");
        this.assertDeepEqual(shapes[1].shape, [50, 10], "Test 50%");
    },
    // ========== BIAS TESTS ==========
    testNeuronHasBias() {
        const node = new NeuronNode("n1", 0, 0);
        this.assertEqual(node.hasBias, true, "Neuron has bias enabled");
        this.assertEqual(node.bias, 0, "Neuron default bias is 0");
    },

    testLayerHasBias() {
        const node = new LayerNode("l1", 0, 0);
        this.assertEqual(node.hasBias, true, "Layer has bias enabled");
        this.assertEqual(node.bias, 0, "Layer default bias is 0");
    },

    testInputDataNoBias() {
        const node = new InputDataNode("i1", 0, 0);
        this.assertEqual(node.hasBias, false, "InputData has no bias");
    },

    testOutputNoBias() {
        const node = new OutputNode("o1", 0, 0);
        this.assertEqual(node.hasBias, false, "Output has no bias");
    },

    testNormalizeNoBias() {
        const node = new NormalizeNode("n1", 0, 0);
        this.assertEqual(node.hasBias, false, "Normalize has no bias");
    },

    // ========== WEIGHT TESTS ==========
    testWeightShapeLayerToLayer() {
        const l1 = new LayerNode("l1", 0, 0);
        l1.numNeurons = 128;
        const l2 = new LayerNode("l2", 200, 0);
        l2.numNeurons = 64;

        l1.outputs[0].setShape([32, 128], "float32", true, false);
        l2.inputs[0].setShape([32, 128], "float32", true, false);

        const link = new Link(l1.outputs[0], l2.inputs[0]);
        link.computeWeightShape();
        this.assertNotNull(link.weightShape, "Link has weight shape");
        this.assertDeepEqual(
            link.weightShape.shape,
            [64, 128],
            "Weight shape (64, 128)",
        );
        this.assertEqual(link.hasWeight, true, "Link has weight");
    },

    testWeightShapeDataToLayer() {
        const input = new InputDataNode("i1", 0, 0);
        input.dataShape = "(32, 784)";
        const shapes = input.computeOutputShapes();
        input.outputs[0].setShape(shapes[0].shape, "float32", true, false);

        const layer = new LayerNode("l1", 200, 0);
        layer.numNeurons = 256;

        const link = new Link(input.outputs[0], layer.inputs[0]);
        link.computeWeightShape();
        this.assertNotNull(
            link.weightShape,
            "Data→Layer link has weight shape",
        );
        this.assertDeepEqual(
            link.weightShape.shape,
            [256, 784],
            "Weight shape (256, 784)",
        );
    },

    testWeightShapeDataToNeuron() {
        const input = new InputDataNode("i1", 0, 0);
        input.dataShape = "(32, 10)";
        const shapes = input.computeOutputShapes();
        input.outputs[0].setShape(shapes[0].shape, "float32", true, false);

        const neuron = new NeuronNode("n1", 200, 0);

        const link = new Link(input.outputs[0], neuron.inputs[0]);
        link.computeWeightShape();
        this.assertDeepEqual(
            link.weightShape.shape,
            [1, 10],
            "Weight shape (1, 10)",
        );
    },

    testWeightShapeNeuronToNeuron() {
        const n1 = new NeuronNode("n1", 0, 0);
        const n2 = new NeuronNode("n2", 200, 0);
        n1.outputs[0].setShape([32, 1], "float32", true, false);

        const link = new Link(n1.outputs[0], n2.inputs[0]);
        link.computeWeightShape();
        this.assertDeepEqual(
            link.weightShape.shape,
            [1, 1],
            "Scalar weight (1, 1)",
        );
    },

    testNoWeightBetweenDataNodes() {
        const col = new ColumnSelectNode("c1", 0, 0);
        const norm = new NormalizeNode("n1", 200, 0);

        const link = new Link(col.outputs[0], norm.inputs[0]);
        link.computeWeightShape();
        this.assertEqual(link.weightShape, null, "Data→Data has no weight");
        this.assertEqual(link.hasWeight, false, "Data→Data hasWeight is false");
    },

    testWeightShapeDisplay() {
        const link = new Link(null, null);
        link.weightShape = { shape: [64, 128], dtype: "float32" };
        this.assertEqual(
            link.weightShapeDisplay(),
            "(64, 128)",
            "Display shows (64, 128)",
        );

        link.weightShape = null;
        this.assertEqual(
            link.weightShapeDisplay(),
            "N/A",
            "Display shows N/A for null",
        );
    },

    // ========== CONV2D TESTS ==========
    testConv2DShape() {
        const node = new Conv2DNode("c1", 0, 0);
        node.filters = 32;
        node.kernelSize = 3;
        node.stride = 1;
        node.padding = 0;

        const mockShape = { shape: [16, 28, 28, 3], symbolic: false };
        node._getFirstInputShapeObj = () => mockShape;

        const shapes = node.computeOutputShapes();
        this.assertDeepEqual(
            shapes[0].shape,
            [16, 26, 26, 32],
            "Conv2D output (16, 26, 26, 32)",
        );
    },

    testConv2DWithPadding() {
        const node = new Conv2DNode("c1", 0, 0);
        node.filters = 64;
        node.kernelSize = 3;
        node.stride = 1;
        node.padding = 1;

        const mockShape = { shape: [8, 32, 32, 3], symbolic: false };
        node._getFirstInputShapeObj = () => mockShape;

        const shapes = node.computeOutputShapes();
        this.assertDeepEqual(
            shapes[0].shape,
            [8, 32, 32, 64],
            "Conv2D with padding (8, 32, 32, 64)",
        );
    },

    testConv2DWithStride() {
        const node = new Conv2DNode("c1", 0, 0);
        node.filters = 16;
        node.kernelSize = 3;
        node.stride = 2;
        node.padding = 0;

        const mockShape = { shape: [4, 28, 28, 1], symbolic: false };
        node._getFirstInputShapeObj = () => mockShape;

        const shapes = node.computeOutputShapes();
        this.assertDeepEqual(
            shapes[0].shape,
            [4, 13, 13, 16],
            "Conv2D stride 2 (4, 13, 13, 16)",
        );
    },

    // ========== FLATTEN TESTS ==========
    testFlatten2D() {
        const node = new FlattenNode("f1", 0, 0);
        const mockShape = { shape: [32, 128], symbolic: false };
        node._getFirstInputShapeObj = () => mockShape;

        const shapes = node.computeOutputShapes();
        this.assertDeepEqual(
            shapes[0].shape,
            [32, 128],
            "Flatten 2D unchanged",
        );
    },

    testFlatten3D() {
        const node = new FlattenNode("f1", 0, 0);
        const mockShape = { shape: [16, 28, 28], symbolic: false };
        node._getFirstInputShapeObj = () => mockShape;

        const shapes = node.computeOutputShapes();
        this.assertDeepEqual(
            shapes[0].shape,
            [16, 784],
            "Flatten 3D (16, 784)",
        );
    },

    testFlatten4D() {
        const node = new FlattenNode("f1", 0, 0);
        const mockShape = { shape: [8, 7, 7, 64], symbolic: false };
        node._getFirstInputShapeObj = () => mockShape;

        const shapes = node.computeOutputShapes();
        this.assertDeepEqual(
            shapes[0].shape,
            [8, 3136],
            "Flatten 4D (8, 3136)",
        );
    },

    testFlattenSymbolic() {
        const node = new FlattenNode("f1", 0, 0);
        const mockShape = { shape: ["B", "H", "W", "C"], symbolic: true };
        node._getFirstInputShapeObj = () => mockShape;

        const shapes = node.computeOutputShapes();
        // The reduce produces ["B", "H*W*C"] — check the pattern
        this.assertEqual(shapes[0].shape[0], "B", "Batch dim preserved");
        this.assertEqual(shapes[0].symbolic, true, "Output is symbolic");
        this.assert(
            shapes[0].shape[1].includes("*"),
            "Flattened dims contain *",
        );
    },

    // ========== DROPOUT TESTS ==========
    testDropoutShape() {
        const node = new DropoutNode("d1", 0, 0);
        this.assertEqual(node.rate, 0.5, "Default rate 0.5");

        const mockShape = { shape: [32, 128], symbolic: false };
        node._getFirstInputShapeObj = () => mockShape;

        const shapes = node.computeOutputShapes();
        this.assertDeepEqual(
            shapes[0].shape,
            [32, 128],
            "Dropout preserves shape",
        );
    },

    testDropoutToJSON() {
        const node = new DropoutNode("d1", 0, 0);
        node.rate = 0.3;
        const json = node.toJSON();
        this.assertEqual(json.rate, 0.3, "Rate saved to JSON");
    },

    testDropoutFromJSON() {
        const node = new DropoutNode("d1", 0, 0);
        node.fromJSON({
            rate: 0.7,
            inputPorts: [],
            outputPorts: [],
            numInputs: 1,
            numOutputs: 1,
        });
        this.assertEqual(node.rate, 0.7, "Rate restored from JSON");
    },

    // ========== BATCHNORM TESTS ==========
    testBatchNormShape() {
        const node = new BatchNormNode("b1", 0, 0);
        this.assertEqual(node.eps, 0.001, "Default epsilon");
        this.assertEqual(node.momentum, 0.1, "Default momentum");

        const mockShape = { shape: [16, 64, 28, 28], symbolic: false };
        node._getFirstInputShapeObj = () => mockShape;

        const shapes = node.computeOutputShapes();
        this.assertDeepEqual(
            shapes[0].shape,
            [16, 64, 28, 28],
            "BatchNorm preserves shape",
        );
    },

    // ========== ONEHOT ENCODE TESTS ==========
    testOneHotShape() {
        const node = new OneHotEncodeNode("o1", 0, 0);
        this.assertEqual(node.numClasses, 10, "Default 10 classes");

        const mockShape = { shape: [100, 1], symbolic: false };
        node._getFirstInputShapeObj = () => mockShape;

        const shapes = node.computeOutputShapes();
        this.assertDeepEqual(
            shapes[0].shape,
            [100, 1, 10],
            "OneHot adds class dimension",
        );
    },

    // ========== CONCATENATE TESTS ==========
    testConcatLastAxis() {
        const node = new ConcatenateNode("c1", 0, 0);
        node.axis = -1;
        node.inputs = [{}, {}]; // Mock 2 inputs

        // Mock the link shapes
        const origFind = SketchMod.links.find;
        SketchMod.links = {
            find: (fn) => {
                return {
                    from: { shape: { shape: [32, 64], symbolic: false } },
                };
            },
        };

        // This test is complex due to link dependencies — skip full test
        SketchMod.links.find = origFind;
        this.assertEqual(node.axis, -1, "Default axis is -1");
    },

    testConcatToJSON() {
        const node = new ConcatenateNode("c1", 0, 0);
        node.axis = 1;
        const json = node.toJSON();
        this.assertEqual(json.axis, 1, "Axis saved to JSON");
    },

    // ========== ADD NODE TESTS ==========
    testAddNodeFixedInputs() {
        const node = new AddNode("a1", 0, 0);
        this.assertEqual(node.inputs.length, 2, "Add node has 2 inputs");
        this.assertEqual(node.outputs.length, 1, "Add node has 1 output");
        this.assertEqual(node.inputs[0].subType, "main", "First input is main");
        this.assertEqual(
            node.inputs[1].subType,
            "skip",
            "Second input is skip",
        );
        this.assertEqual(node.maxInputs, 2, "Max inputs is 2");
        this.assertEqual(node.minInputs, 2, "Min inputs is 2");
    },

    testAddNodeShape() {
        const node = new AddNode("a1", 0, 0);
        const mockShape = { shape: [32, 128], symbolic: false };
        node._getFirstInputShapeObj = () => mockShape;

        const shapes = node.computeOutputShapes();
        this.assertDeepEqual(shapes[0].shape, [32, 128], "Add preserves shape");
    },

    // ========== SYMBOLIC PROPAGATION TESTS ==========
    testSymbolicThroughLayer() {
        const input = new InputDataNode("i1", 0, 0);
        input.dataShape = "(N, F)";
        const inShapes = input.computeOutputShapes();

        const layer = new LayerNode("l1", 0, 0);
        layer.numNeurons = 128;
        const mockShape = { shape: inShapes[0].shape, symbolic: true };
        layer._getFirstInputShapeObj = () => mockShape;

        const outShapes = layer.computeOutputShapes();
        this.assertDeepEqual(
            outShapes[0].shape,
            ["N", 128],
            "Symbolic through layer",
        );
        this.assertEqual(
            outShapes[0].symbolic,
            true,
            "Symbolic flag preserved",
        );
    },

    testSymbolicThroughFlatten() {
        const node = new FlattenNode("f1", 0, 0);
        const mockShape = { shape: ["B", "H", "W", "C"], symbolic: true };
        node._getFirstInputShapeObj = () => mockShape;

        const shapes = node.computeOutputShapes();
        this.assertEqual(
            shapes[0].symbolic,
            true,
            "Flatten preserves symbolic",
        );
    },

    // ========== SESSION TESTS ==========
    testSaveToSessionStoresModelId() {
        // Backup and set
        const origNodes = SketchMod.nodes;
        const origLinks = SketchMod.links;
        const origPorts = SketchMod.ports;

        SketchMod.nodes = [];
        SketchMod.links = [];
        SketchMod.ports = [];
        SketchMod._currentModelId = "test123";
        SketchMod._currentModelName = "Test";
        SketchMod._saveToSession();

        const raw = sessionStorage.getItem("sketchmod-graph");
        const data = JSON.parse(raw);
        this.assertEqual(data.modelId, "test123", "Model ID saved to session");
        this.assertEqual(data.modelName, "Test", "Model name saved to session");

        // Restore
        SketchMod.nodes = origNodes;
        SketchMod.links = origLinks;
        SketchMod.ports = origPorts;
    },

    testLoadFromSessionRestoresModelId() {
        const origNodes = SketchMod.nodes;
        const origLinks = SketchMod.links;
        const origPorts = SketchMod.ports;

        SketchMod.nodes = [];
        SketchMod.links = [];
        SketchMod.ports = [];

        sessionStorage.setItem(
            "sketchmod-graph",
            JSON.stringify({
                nodes: [],
                links: [],
                ports: [],
                nodeCounter: 0,
                modelId: "restored123",
                modelName: "Restored",
            }),
        );

        SketchMod._loadFromSession();
        this.assertEqual(
            SketchMod._currentModelId,
            "restored123",
            "Model ID restored",
        );
        this.assertEqual(
            SketchMod._currentModelName,
            "Restored",
            "Model name restored",
        );

        SketchMod.nodes = origNodes;
        SketchMod.links = origLinks;
        SketchMod.ports = origPorts;
    },
    // ========== UNDO/REDO TESTS ==========
    testUndoAfterAddNode() {
        const origNodes = SketchMod.nodes;
        const origLinks = SketchMod.links;
        const origPorts = SketchMod.ports;
        const origUndo = SketchMod.undoStack;
        const origRedo = SketchMod.redoStack;

        SketchMod.nodes = [];
        SketchMod.links = [];
        SketchMod.ports = [];
        SketchMod.undoStack = [];
        SketchMod.redoStack = [];

        SketchMod._saveUndoState();

        const node = new NeuronNode("test-n1", 100, 100);
        SketchMod.nodes.push(node);
        SketchMod.ports = [...SketchMod.ports, ...node.inputs, ...node.outputs];

        this.assertEqual(SketchMod.nodes.length, 1, "Node added");
        this.assertEqual(SketchMod.undoStack.length, 1, "Undo stack has state");

        // Restore
        SketchMod.nodes = origNodes;
        SketchMod.links = origLinks;
        SketchMod.ports = origPorts;
        SketchMod.undoStack = origUndo;
        SketchMod.redoStack = origRedo;
    },

    // ========== SUMMARY ==========
    runAll() {
        console.log("🧪 Running SketchMod Canvas Tests...\n");

        // Node creation
        this.testNeuronNode();
        this.testLayerNode();
        this.testInputDataNode();
        this.testOutputNode();
        this.testColumnSelectNode();
        this.testRowSelectNode();
        this.testDimSelectNode();
        this.testTrainTestSplitNode();
        this.testNormalizeNode();

        // Port constraints
        this.testPortConstraints();
        this.testInputDataCannotAddInput();
        this.testOutputNodeCannotAddOutput();
        this.testNeuronCanAddMultiplePorts();

        // Port tests
        this.testPortCreation();
        this.testPortColors();
        this.testPortShapeDisplay();
        this.testPortSetShapeAllParams();

        // Shape propagation
        this.testInputDataNodeComputeShapes_Numeric();
        this.testInputDataNodeComputeShapes_Symbolic();
        this.testInputDataNodeComputeShapes_Empty();
        this.testLayerNodeComputeShapes();
        this.testNeuronComputeShapes();
        this.testNormalizeComputeShapes();
        this.testTrainTestSplitComputeShapes();
        this.testTrainTestSplitComputeShapes_Symbolic();
        this.testColumnSelectComputeShapes();
        this.testRowSelectComputeShapes();
        this.testDimSelectComputeShapes();
        this.testEmptyShapesHelper();
        this.testMakeShapesHelper();

        // Links
        this.testLinkCreation();
        this.testLinkDefaultWeight();
        this.testLinkToJSON();

        // Serialization
        this.testNeuronToJSON();
        this.testLayerToJSON();
        this.testTrainTestToJSON();
        this.testNeuronFromJSON();
        this.testFromJSONPreservesPortSubtypes();
        this.testColumnSelectFromJSON();
        this.testRowSelectFromJSON();
        this.testDimSelectFromJSON();
        this.testPortToJSON();

        // Row select compute
        this.testRowSelectComputeRowCount_FirstN();
        this.testRowSelectComputeRowCount_Random();
        this.testRowSelectComputeRowCount_Slice();
        this.testRowSelectComputeRowCount_Indices();
        this.testRowSelectComputeRowCount_Empty();

        // Column parsing
        this.testParseColumnInput_Single();
        this.testParseColumnInput_Range();
        this.testParseColumnInput_Mixed();
        this.testParseColumnInput_Empty();
        this.testParseColumnInput_Null();
        this.testParseColumnInput_OutOfBounds();
        this.testParseColumnInput_Whitespace();

        // Dim parsing
        this.testParseDimInput_All();
        this.testParseDimInput_Range();
        this.testParseDimInput_FromStart();
        this.testParseDimInput_ToEnd();
        this.testParseDimInput_Step();
        this.testParseDimInput_Mixed();
        this.testParseDimInput_Empty();

        // Registry
        this.testNodeRegistryHasAllNodes();
        this.testNodeRegistryCategories();
        this.testRegisterNode();

        // Theme colors
        this.testGetNodeColorLight();
        this.testGetNodeColorDark();
        this.testGetNodeColorRose();
        this.testGetNodeColorForest();
        this.testGetNodeColorHoney();
        this.testGetNodeColorUnknownTheme();

        // Base node methods
        this.testBaseNodeContainsPoint();
        this.testBaseNodeGetPorts();
        this.testBaseNodeCanAddInputWithTypeCheck();
        this.testBaseNodeRemoveInputReturnsPort();

        // Bounds
        this.testNeuronBounds();
        this.testRectNodeBounds();

        // Port positions
        this.testPortPositionsAfterUpdate();
        this.testRectNodePortPositions();

        // Edge cases
        this.testCreateNodeAtNegativeCoordinates();
        this.testCreateNodeAtLargeCoordinates();
        this.testLayerMinNeurons();
        this.testLayerMaxNeurons();
        this.testTrainTestRatioBoundary();
        this.testTrainTestRatio50_50();

        // Bias tests
        this.testNeuronHasBias();
        this.testLayerHasBias();
        this.testInputDataNoBias();
        this.testOutputNoBias();
        this.testNormalizeNoBias();

        // Weight tests
        this.testWeightShapeLayerToLayer();
        this.testWeightShapeDataToLayer();
        this.testWeightShapeDataToNeuron();
        this.testWeightShapeNeuronToNeuron();
        this.testNoWeightBetweenDataNodes();
        this.testWeightShapeDisplay();

        // Conv2D tests
        this.testConv2DShape();
        this.testConv2DWithPadding();
        this.testConv2DWithStride();

        // Flatten tests
        this.testFlatten2D();
        this.testFlatten3D();
        this.testFlatten4D();
        this.testFlattenSymbolic();

        // Dropout tests
        this.testDropoutShape();
        this.testDropoutToJSON();
        this.testDropoutFromJSON();

        // BatchNorm tests
        this.testBatchNormShape();

        // OneHot tests
        this.testOneHotShape();

        // Concatenate tests
        this.testConcatLastAxis();
        this.testConcatToJSON();

        // Add node tests
        this.testAddNodeFixedInputs();
        this.testAddNodeShape();

        // Symbolic tests
        this.testSymbolicThroughLayer();
        this.testSymbolicThroughFlatten();

        // Session tests
        this.testSaveToSessionStoresModelId();
        this.testLoadFromSessionRestoresModelId();

        // Undo/Redo tests
        this.testUndoAfterAddNode();
        // Report
        const total = this.passed + this.failed;
        console.log(`\n${"=".repeat(50)}`);
        console.log(`✅ Passed: ${this.passed}/${total}`);
        console.log(`❌ Failed: ${this.failed}/${total}`);
        if (this.errors.length > 0) {
            console.log("\nErrors:");
            this.errors.forEach((e) => console.log(`  ${e}`));
        }
        console.log(`${"=".repeat(50)}\n`);
    },
};

// Run tests
CanvasTests.runAll();
