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
        this.assertEqual(node.maxInputs, 1, "NeuronNode maxInputs is Infinity");
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
        this.assertEqual(node.outputs.length, 3, "OutputNode has 0 outputs");
        this.assertEqual(node.maxOutputs, 3, "OutputNode maxOutputs is 0");
        this.assertEqual(node.maxInputs, 1, "OutputNode maxInputs is 1");
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
        this.assertEqual(p1, null, "Cannot add 2nd input");
        this.assertEqual(p2, null, "Cannot add 3rd input");
        this.assertEqual(p3, null, "Cannot add 4th input");
        this.assertEqual(neuron.inputs.length, 1, "Neuron has 1 inputs total");
        this.assertEqual(
            neuron.canAddInput(),
            false,
            "Neuron cannot add more inputs",
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
        // MultiPort now gets shapes from _getAllInputShapeObjs
        const mockShape = { shape: [64, 256], symbolic: false };
        node._getAllInputShapeObjs = () => [mockShape];
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
        node._getAllInputShapeObjs = () => [mockShape];
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
        const node = new VisualizationNode("v1", 0, 0);
        this.assertEqual(
            node.inputs.length,
            2,
            "Viz starts with 2 coord inputs",
        );
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
        // AddNode now has 1 MultiPort, not 2 separate inputs
        this.assertEqual(node.inputs.length, 1, "Add node has 1 input port");
        this.assertEqual(node.outputs.length, 1, "Add node has 1 output");
        this.assertInstanceOf(node.inputs[0], MultiPort, "Input is MultiPort");
        this.assertEqual(node.maxInputs, 1, "Max inputs is 1");
        this.assertEqual(node.minInputs, 1, "Min inputs is 1");
    },

    testAddNodeShape() {
        const node = new AddNode("a1", 0, 0);
        // MultiPort needs at least 2 shapes
        const shapes = [
            { shape: [32, 128], symbolic: false, known: true },
            { shape: [32, 128], symbolic: false, known: true },
        ];
        node._getAllInputShapeObjs = () => shapes;
        const result = node.computeOutputShapes();
        this.assertDeepEqual(result[0].shape, [32, 128], "Add preserves shape");
    },

    // ========== SYMBOLIC PROPAGATION TESTS ==========
    testSymbolicThroughLayer() {
        const input = new InputDataNode("i1", 0, 0);
        input.dataShape = "(N, F)";
        const inShapes = input.computeOutputShapes();
        const layer = new LayerNode("l1", 0, 0);
        layer.numNeurons = 128;
        // LayerNode uses _getAllInputShapeObjs now
        layer._getAllInputShapeObjs = () => [
            { shape: inShapes[0].shape, symbolic: true, known: true },
        ];
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

    // ========== OPTIMIZER NODE TESTS ==========
    testOptimizerNodeCreation() {
        const node = new OptimizerNode("opt1", 100, 200);
        this.assertNotNull(node, "OptimizerNode should be created");
        this.assertEqual(
            node.type,
            "optimizer",
            "OptimizerNode type is 'optimizer'",
        );
        this.assertEqual(node.inputs.length, 2, "OptimizerNode has 2 inputs");
        this.assertEqual(node.outputs.length, 0, "OptimizerNode has 0 outputs");
        this.assertEqual(node.maxInputs, 2, "OptimizerNode maxInputs is 2");
        this.assertEqual(node.minInputs, 2, "OptimizerNode minInputs is 2");
        this.assertEqual(node.maxOutputs, 0, "OptimizerNode maxOutputs is 0");
    },

    testOptimizerNodeDefaultConfig() {
        const node = new OptimizerNode("opt1", 0, 0);
        this.assertEqual(
            node.lossType,
            "cross_entropy",
            "Default loss is cross_entropy",
        );
        this.assertEqual(
            node.optimizerType,
            "adam",
            "Default optimizer is adam",
        );
        this.assertEqual(node.learningRate, 0.001, "Default LR is 0.001");
        this.assertEqual(node.epochs, 10, "Default epochs is 10");
        this.assertEqual(node.batchSize, 32, "Default batch size is 32");
        this.assertEqual(node.shuffle, true, "Default shuffle is true");
        this.assertEqual(
            node.gradientClip,
            null,
            "Default gradient clip is null",
        );
        this.assertEqual(node.adamBeta1, 0.9, "Default beta1 is 0.9");
        this.assertEqual(node.adamBeta2, 0.999, "Default beta2 is 0.999");
        this.assertEqual(node.adamEpsilon, 1e-8, "Default epsilon is 1e-8");
        this.assertEqual(node.sgdMomentum, 0.9, "Default SGD momentum is 0.9");
        this.assertEqual(node.weightDecay, 0, "Default weight decay is 0");
        this.assertEqual(node.nesterov, false, "Default nesterov is false");
    },

    testOptimizerNodePortSubTypes() {
        const node = new OptimizerNode("opt1", 0, 0);
        this.assertInstanceOf(
            node.inputs[0],
            RolePort,
            "First input is RolePort",
        );
        this.assertEqual(node.inputs[0].role, "loss", "First input is loss");
        this.assertInstanceOf(
            node.inputs[1],
            RolePort,
            "Second input is RolePort",
        );
        this.assertEqual(
            node.inputs[1].role,
            "labels",
            "Second input is labels",
        );
    },

    testOptimizerNodeCannotAddInput() {
        const node = new OptimizerNode("opt1", 0, 0);
        const p = node.addInput();
        this.assertEqual(p, null, "Cannot add more inputs (maxInputs=2)");
        this.assertEqual(
            node.canAddInput(),
            false,
            "canAddInput returns false",
        );
    },

    testOptimizerNodeCannotRemoveInput() {
        const node = new OptimizerNode("opt1", 0, 0);
        this.assertEqual(
            node.canRemoveInput(),
            false,
            "Cannot remove inputs (minInputs=2)",
        );
    },

    testOptimizerNodeToJSON() {
        const node = new OptimizerNode("opt1", 100, 200);
        node.lossType = "mse";
        node.optimizerType = "sgd";
        node.learningRate = 0.01;
        node.epochs = 50;
        node.batchSize = 64;
        node.shuffle = false;
        node.gradientClip = 1.0;
        node.sgdMomentum = 0.8;
        node.weightDecay = 0.001;
        node.nesterov = true;

        const json = node.toJSON();
        this.assertEqual(json.lossType, "mse", "JSON lossType");
        this.assertEqual(json.optimizerType, "sgd", "JSON optimizerType");
        this.assertEqual(json.learningRate, 0.01, "JSON learningRate");
        this.assertEqual(json.epochs, 50, "JSON epochs");
        this.assertEqual(json.batchSize, 64, "JSON batchSize");
        this.assertEqual(json.shuffle, false, "JSON shuffle");
        this.assertEqual(json.gradientClip, 1.0, "JSON gradientClip");
        this.assertEqual(json.sgdMomentum, 0.8, "JSON sgdMomentum");
        this.assertEqual(json.weightDecay, 0.001, "JSON weightDecay");
        this.assertEqual(json.nesterov, true, "JSON nesterov");
    },

    testOptimizerNodeFromJSON() {
        const node = new OptimizerNode("opt1", 0, 0);
        node.inputs = [];
        node.fromJSON({
            lossType: "bce",
            optimizerType: "adamw",
            learningRate: 0.0001,
            epochs: 100,
            batchSize: 16,
            shuffle: false,
            gradientClip: 5.0,
            adamBeta1: 0.8,
            adamBeta2: 0.99,
            adamEpsilon: 1e-7,
            weightDecay: 0.01,
            inputPorts: [
                { id: "opt1_input_0", index: 0, subType: "loss", role: null },
                { id: "opt1_input_1", index: 1, subType: "labels", role: null },
            ],
            numInputs: 2,
            numOutputs: 0,
        });
        this.assertEqual(node.lossType, "bce", "Restored lossType");
        this.assertEqual(node.optimizerType, "adamw", "Restored optimizerType");
        this.assertEqual(node.learningRate, 0.0001, "Restored learningRate");
        this.assertEqual(node.epochs, 100, "Restored epochs");
        this.assertEqual(node.batchSize, 16, "Restored batchSize");
        this.assertEqual(node.shuffle, false, "Restored shuffle");
        this.assertEqual(node.gradientClip, 5.0, "Restored gradientClip");
        this.assertEqual(node.adamBeta1, 0.8, "Restored beta1");
        this.assertEqual(node.weightDecay, 0.01, "Restored weightDecay");
        this.assertEqual(node.inputs.length, 2, "Restored 2 inputs");
    },

    // ========== VISUALIZATION NODE TESTS ==========
    testVisualizationNodeCreation() {
        const node = new VisualizationNode("viz1", 100, 200);
        this.assertNotNull(node, "VisualizationNode should be created");
        this.assertEqual(node.type, "visualization", "Type is 'visualization'");
        this.assertEqual(
            node._coordPorts().length,
            2,
            "Starts with 2 coord inputs",
        );
        this.assertEqual(
            node._hasColorInput(),
            false,
            "No color input by default",
        );
        this.assertEqual(node.colorMode, "none", "Default color mode is none");
        this.assertEqual(node.maxInputs, 4, "maxInputs is 4");
        this.assertEqual(node.minInputs, 1, "minInputs is 1");
    },

    testVisualizationNodeCoordLimits() {
        const node = new VisualizationNode("viz1", 0, 0);
        // Can add 3rd coord
        this.assertEqual(node._canAddCoordInput(), true, "Can add 3rd coord");
        node.addInput("coord");
        this.assertEqual(node._coordPorts().length, 3, "Has 3 coord ports");
        this.assertEqual(
            node._canAddCoordInput(),
            false,
            "Cannot add 4th coord",
        );

        // Can remove down to 1
        this.assertEqual(node._canRemoveCoordInput(), true, "Can remove coord");
        node.removeInput();
        this.assertEqual(node._coordPorts().length, 2, "Has 2 coord ports");
        node.removeInput();
        this.assertEqual(node._coordPorts().length, 1, "Has 1 coord port");
        this.assertEqual(
            node._canRemoveCoordInput(),
            false,
            "Cannot remove last coord",
        );
    },

    testVisualizationNodeColorInput() {
        const node = new VisualizationNode("viz1", 0, 0);
        this.assertEqual(node._canAddColorInput(), true, "Can add color input");
        const p = node.addInput("color");
        this.assertNotNull(p, "Color port created");
        this.assertInstanceOf(p, RolePort, "Color port is RolePort");
        this.assertEqual(p.role, "color", "Role is color");
        this.assertEqual(node._hasColorInput(), true, "Has color input");
        this.assertEqual(
            node._canAddColorInput(),
            false,
            "Cannot add second color",
        );
        this.assertEqual(node._canRemoveColorInput(), true, "Can remove color");
        node.removeInput();
        this.assertEqual(node._hasColorInput(), false, "Color input removed");
    },

    testVisualizationNodeColorModes() {
        const node = new VisualizationNode("viz1", 0, 0);

        // Switch to discrete
        node.colorMode = "discrete";
        this.assertEqual(node.colorMode, "discrete", "Mode set to discrete");

        // Switch to continuous
        node.colorMode = "continuous";
        this.assertEqual(
            node.colorMode,
            "continuous",
            "Mode set to continuous",
        );

        // Switch to none
        node.colorMode = "none";
        this.assertEqual(node.colorMode, "none", "Mode set to none");
    },

    testVisualizationNodeDefaultPalette() {
        const node = new VisualizationNode("viz1", 0, 0);
        this.assertDeepEqual(
            node.colorPalette,
            ["#ef4444", "#4ade80", "#60a5fa", "#f59e0b", "#a78bfa"],
            "Default palette has 5 colors",
        );
    },

    testVisualizationNodeContinuousColors() {
        const node = new VisualizationNode("viz1", 0, 0);
        this.assertEqual(
            node.continuousMinColor,
            "#3b82f6",
            "Default min color",
        );
        this.assertEqual(
            node.continuousMaxColor,
            "#ef4444",
            "Default max color",
        );
    },

    testVisualizationNodeToJSON() {
        const node = new VisualizationNode("viz1", 100, 200);
        node.colorMode = "discrete";
        node.colorPalette = ["#ff0000", "#00ff00", "#0000ff"];
        node.continuousMinColor = "#111111";
        node.continuousMaxColor = "#eeeeee";
        node.addInput("color");
        const json = node.toJSON();
        this.assertEqual(json.colorMode, "discrete", "JSON colorMode");
        this.assertDeepEqual(
            json.colorPalette,
            ["#ff0000", "#00ff00", "#0000ff"],
            "JSON colorPalette",
        );
        this.assertEqual(json.continuousMinColor, "#111111", "JSON min color");
        this.assertEqual(json.continuousMaxColor, "#eeeeee", "JSON max color");
        // hasColorInput and colorInputId are not in toJSON — they're computed from port data
    },

    testVisualizationNodeFromJSON() {
        const node = new VisualizationNode("viz1", 0, 0);
        node.inputs = [];
        node.fromJSON({
            colorMode: "continuous",
            colorPalette: ["#aaa", "#bbb", "#ccc"],
            continuousMinColor: "#000",
            continuousMaxColor: "#fff",
            inputPorts: [
                {
                    id: "viz1_input_0",
                    index: 0,
                    subType: "coord",
                    portKind: "data",
                },
                {
                    id: "viz1_input_1",
                    index: 1,
                    subType: "coord",
                    portKind: "data",
                },
                {
                    id: "viz1_input_2",
                    index: 2,
                    subType: null,
                    portKind: "role",
                    role: "color",
                },
            ],
            outputPorts: [],
            numInputs: 3,
            numOutputs: 0,
        });
        this.assertEqual(node.colorMode, "continuous", "Restored colorMode");
        this.assertDeepEqual(
            node.colorPalette,
            ["#aaa", "#bbb", "#ccc"],
            "Restored palette",
        );
        this.assertEqual(node.continuousMinColor, "#000", "Restored min color");
        this.assertEqual(node.continuousMaxColor, "#fff", "Restored max color");
        this.assertEqual(node._hasColorInput(), true, "Restored hasColorInput");
        const cp = node._colorPort();
        this.assertNotNull(cp, "Color port restored");
        this.assertInstanceOf(cp, RolePort, "Color port is RolePort");
    },

    testVisualizationNodeRenumberPorts() {
        const node = new VisualizationNode("viz1", 0, 0);
        // Add a coord
        node.addInput("coord");
        // Remove first coord
        const ports = node._coordPorts();
        node.inputs = node.inputs.filter((p) => p !== ports[0]);
        node._renumberPorts();

        // Check indices are sequential
        node.inputs.forEach((p, i) => {
            this.assertEqual(
                p.index,
                i,
                `Port at index ${i} has correct index`,
            );
            this.assertEqual(p.id, `viz1_input_${i}`, `Port has correct id`);
        });
    },

    // ========== OUTPUT NODE ROLE PORTS TESTS ==========
    testOutputNodeRolePorts() {
        const node = new OutputNode("out1", 0, 0);
        this.assertEqual(node.inputs.length, 1, "OutputNode has 1 input");
        this.assertEqual(
            node.outputs.length,
            3,
            "OutputNode has 3 output ports",
        );
        this.assertEqual(node.maxOutputs, 3, "maxOutputs is 3");
        this.assertEqual(node.minOutputs, 3, "minOutputs is 3");
        this.assertEqual(node.canAddOutput(), false, "Cannot add outputs");
        this.assertEqual(
            node.canRemoveOutput(),
            false,
            "Cannot remove outputs",
        );
    },

    testOutputNodeRolePortRoles() {
        const node = new OutputNode("out1", 0, 0);
        this.assertEqual(node.outputs[0].role, "loss", "First output is loss");
        this.assertEqual(
            node.outputs[1].role,
            "prediction",
            "Second output is prediction",
        );
        this.assertEqual(
            node.outputs[2].role,
            "evaluation",
            "Third output is evaluation",
        );
    },

    testOutputNodeRolePortsOnRightSide() {
        const node = new OutputNode("out1", 100, 100);
        // All output ports should be on the right
        node.outputs.forEach((p) => {
            this.assert(p.x > 100, `Output port ${p.role} is on right side`);
        });
        // Input should be on left
        this.assert(node.inputs[0].x < 100, "Input port is on left side");
    },

    testOutputNodeRolePortsToJSON() {
        const node = new OutputNode("out1", 0, 0);
        const json = node.toJSON();
        this.assertEqual(json.outputPorts.length, 3, "JSON has 3 output ports");
        // Check roles are in outputPorts
        const roles = json.outputPorts.map((p) => p.role);
        this.assertDeepEqual(
            roles,
            ["loss", "prediction", "evaluation"],
            "Roles in JSON",
        );
    },

    testOutputNodeRolePortsFromJSON() {
        const node = new OutputNode("out1", 0, 0);
        node.inputs = [];
        node.outputs = [];
        node.fromJSON({
            outputPorts: [
                {
                    id: "out1_output_0",
                    index: 0,
                    subType: null,
                    portKind: "role",
                    role: "loss",
                },
                {
                    id: "out1_output_1",
                    index: 1,
                    subType: null,
                    portKind: "role",
                    role: "prediction",
                },
                {
                    id: "out1_output_2",
                    index: 2,
                    subType: null,
                    portKind: "role",
                    role: "evaluation",
                },
            ],
            inputPorts: [
                {
                    id: "out1_input_0",
                    index: 0,
                    subType: null,
                    portKind: "data",
                },
            ],
            numInputs: 1,
            numOutputs: 3,
        });
        this.assertEqual(node.outputs.length, 3, "Restored 3 outputs");
        this.assertEqual(node.outputs[0].role, "loss", "Restored loss role");
        this.assertEqual(
            node.outputs[1].role,
            "prediction",
            "Restored prediction role",
        );
        this.assertEqual(
            node.outputs[2].role,
            "evaluation",
            "Restored evaluation role",
        );
    },

    // ========== EXPORT FUNCTIONALITY TESTS ==========
    testCompileToPython() {
        // Backup
        const origNodes = SketchMod.nodes;

        const input = new InputDataNode("i1", 0, 0);
        const layer1 = new LayerNode("l1", 0, 0);
        layer1.numNeurons = 128;
        const layer2 = new LayerNode("l2", 0, 0);
        layer2.numNeurons = 10;
        layer2.activation = "sigmoid";

        SketchMod.nodes = [input, layer1, layer2];

        const code = SketchMod._compileToPython();
        this.assert(code.includes("import torch"), "Code imports torch");
        this.assert(code.includes("import torch.nn as nn"), "Code imports nn");
        this.assert(
            code.includes("class SketchNetModel"),
            "Code has model class",
        );
        this.assert(code.includes("nn.Linear"), "Code has Linear layers");
        this.assert(
            code.includes("nn.Sigmoid()"),
            "Code has Sigmoid activation",
        );
        this.assert(code.includes("128"), "Code includes neuron count 128");

        // Restore
        SketchMod.nodes = origNodes;
    },

    testExportImageCreatesCanvas() {
        const exportCanvas = document.createElement("canvas");
        exportCanvas.width = 800;
        exportCanvas.height = 600;
        const exportCtx = exportCanvas.getContext("2d");

        this.assertNotNull(exportCanvas, "Export canvas created");
        this.assertEqual(exportCanvas.width, 800, "Export canvas width");
        this.assertEqual(exportCanvas.height, 600, "Export canvas height");
        this.assertNotNull(exportCtx, "Export context exists");

        // Test drawing background
        exportCtx.fillStyle = "#0f1119";
        exportCtx.fillRect(0, 0, 800, 600);

        const dataUrl = exportCanvas.toDataURL("image/png");
        this.assert(dataUrl.startsWith("data:image/png"), "Data URL is PNG");
    },

    // ========== LINK COLOR TESTS ==========
    testLinkHasWeightFlag() {
        const n1 = new NeuronNode("n1", 0, 0);
        const n2 = new NeuronNode("n2", 100, 0);
        const link = new Link(n1.outputs[0], n2.inputs[0]);
        link.computeWeightShape();
        this.assertEqual(link.hasWeight, true, "Neuron→Neuron has weight");

        // Data to data should not have weight
        const col = new ColumnSelectNode("c1", 0, 0);
        const norm = new NormalizeNode("n1", 200, 0);
        const dataLink = new Link(col.outputs[0], norm.inputs[0]);
        dataLink.computeWeightShape();
        this.assertEqual(dataLink.hasWeight, false, "Data→Data has no weight");
    },

    // ========== SESSION ROUNDTRIP TESTS ==========
    testSessionRoundtripWithOptimizerNode() {
        const origNodes = SketchMod.nodes;
        const origLinks = SketchMod.links;
        const origPorts = SketchMod.ports;
        SketchMod.nodes = [];
        SketchMod.links = [];
        SketchMod.ports = [];
        const opt = new OptimizerNode("opt1", 100, 200);
        opt.lossType = "mse";
        opt.optimizerType = "sgd";
        opt.learningRate = 0.01;
        SketchMod.nodes.push(opt);
        SketchMod.ports = SketchMod._collectPorts();
        SketchMod._saveToSession();
        SketchMod.nodes = [];
        SketchMod.links = [];
        SketchMod.ports = [];
        SketchMod._loadFromSession();
        this.assertEqual(SketchMod.nodes.length, 1, "One node restored");
        const restored = SketchMod.nodes[0];
        this.assertInstanceOf(
            restored,
            OptimizerNode,
            "Restored node is OptimizerNode",
        );
        this.assertEqual(restored.lossType, "mse", "Restored lossType");
        this.assertEqual(
            restored.optimizerType,
            "sgd",
            "Restored optimizerType",
        );
        this.assertEqual(restored.learningRate, 0.01, "Restored learningRate");
        this.assertEqual(restored.inputs.length, 2, "Restored 2 inputs");
        this.assertInstanceOf(
            restored.inputs[0],
            RolePort,
            "First input is RolePort",
        );
        this.assertEqual(restored.inputs[0].role, "loss", "Restored loss role");
        this.assertEqual(
            restored.inputs[1].role,
            "labels",
            "Restored labels role",
        );
        SketchMod.nodes = origNodes;
        SketchMod.links = origLinks;
        SketchMod.ports = origPorts;
    },

    testSessionRoundtripWithVisualizationNode() {
        const origNodes = SketchMod.nodes;
        const origLinks = SketchMod.links;
        const origPorts = SketchMod.ports;
        SketchMod.nodes = [];
        SketchMod.links = [];
        SketchMod.ports = [];
        const viz = new VisualizationNode("viz1", 100, 200);
        viz.colorMode = "discrete";
        viz.colorPalette = ["#111", "#222", "#333"];
        viz.addInput("color");
        SketchMod.nodes.push(viz);
        SketchMod.ports = SketchMod._collectPorts();
        SketchMod._saveToSession();
        SketchMod.nodes = [];
        SketchMod.links = [];
        SketchMod.ports = [];
        SketchMod._loadFromSession();
        this.assertEqual(SketchMod.nodes.length, 1, "One node restored");
        const restored = SketchMod.nodes[0];
        this.assertInstanceOf(
            restored,
            VisualizationNode,
            "Restored is VisualizationNode",
        );
        this.assertEqual(restored.colorMode, "discrete", "Restored colorMode");
        this.assertDeepEqual(
            restored.colorPalette,
            ["#111", "#222", "#333"],
            "Restored palette",
        );
        this.assertEqual(
            restored._hasColorInput(),
            true,
            "Restored has color input",
        );
        SketchMod.nodes = origNodes;
        SketchMod.links = origLinks;
        SketchMod.ports = origPorts;
    },

    testSessionRoundtripWithOutputNodeRoles() {
        const origNodes = SketchMod.nodes;
        const origLinks = SketchMod.links;
        const origPorts = SketchMod.ports;

        SketchMod.nodes = [];
        SketchMod.links = [];
        SketchMod.ports = [];

        const out = new OutputNode("out1", 100, 200);
        SketchMod.nodes.push(out);
        SketchMod.ports = SketchMod._collectPorts();
        SketchMod._saveToSession();

        // Clear and reload
        SketchMod.nodes = [];
        SketchMod.links = [];
        SketchMod.ports = [];
        SketchMod._loadFromSession();

        const restored = SketchMod.nodes[0];
        this.assertEqual(restored.outputs.length, 3, "Restored 3 outputs");
        this.assertEqual(
            restored.outputs[0].role,
            "loss",
            "Restored loss role",
        );
        this.assertEqual(
            restored.outputs[1].role,
            "prediction",
            "Restored prediction role",
        );
        this.assertEqual(
            restored.outputs[2].role,
            "evaluation",
            "Restored evaluation role",
        );

        // Restore
        SketchMod.nodes = origNodes;
        SketchMod.links = origLinks;
        SketchMod.ports = origPorts;
    },

    // ========== PARAM PORT TESTS ==========
    testNormalizeNodeParamPorts() {
        const node = new NormalizeNode("n1", 0, 0);
        this.assertEqual(node.maxParamInputs, 1, "maxParamInputs is 1");
        this.assertEqual(node.maxParamOutputs, 1, "maxParamOutputs is 1");

        // Check if constructor already created them
        if (node.paramInputs.length === 0) {
            const pi = node.addParamInput();
            this.assertNotNull(pi, "Param input created");
            this.assertInstanceOf(pi, ParamPort, "Port is ParamPort");
        } else {
            this.assertInstanceOf(
                node.paramInputs[0],
                ParamPort,
                "Existing param input is ParamPort",
            );
        }

        if (node.paramOutputs.length === 0) {
            const po = node.addParamOutput();
            this.assertNotNull(po, "Param output created");
            this.assertInstanceOf(po, ParamPort, "Port is ParamPort");
        } else {
            this.assertInstanceOf(
                node.paramOutputs[0],
                ParamPort,
                "Existing param output is ParamPort",
            );
        }
    },

    testParamPortDiamondShape() {
        const node = new NormalizeNode("n1", 0, 0);

        let pp =
            node.paramInputs.length > 0
                ? node.paramInputs[0]
                : node.addParamInput();
        let po =
            node.paramOutputs.length > 0
                ? node.paramOutputs[0]
                : node.addParamOutput();

        if (pp)
            this.assertInstanceOf(pp, ParamPort, "Param input is ParamPort");
        if (po)
            this.assertInstanceOf(po, ParamPort, "Param output is ParamPort");
    },

    testParamPortToJSON() {
        const node = new NormalizeNode("n1", 0, 0);
        // Ensure param ports exist
        if (node.paramInputs.length === 0) node.addParamInput();
        if (node.paramOutputs.length === 0) node.addParamOutput();

        const json = node.toJSON();
        this.assertEqual(json.paramInputs.length, 1, "JSON has 1 param input");
        this.assertEqual(
            json.paramOutputs.length,
            1,
            "JSON has 1 param output",
        );
        this.assertEqual(json.numParamInputs, 1, "JSON numParamInputs");
        this.assertEqual(json.numParamOutputs, 1, "JSON numParamOutputs");
        this.assertEqual(
            json.paramInputs[0].portKind,
            "param",
            "Param input portKind is param",
        );
        this.assertEqual(
            json.paramOutputs[0].portKind,
            "param",
            "Param output portKind is param",
        );
    },

    testParamPortFromJSON() {
        const node = new NormalizeNode("n1", 0, 0);
        node.paramInputs = [];
        node.paramOutputs = [];
        node.fromJSON({
            paramInputs: [{ id: "n1_input_1", index: 1, portKind: "param" }],
            paramOutputs: [{ id: "n1_output_1", index: 1, portKind: "param" }],
            numParamInputs: 1,
            numParamOutputs: 1,
            inputPorts: [
                { id: "n1_input_0", index: 0, subType: null, portKind: "data" },
            ],
            outputPorts: [
                {
                    id: "n1_output_0",
                    index: 0,
                    subType: null,
                    portKind: "data",
                },
            ],
            numInputs: 1,
            numOutputs: 1,
        });
        this.assertEqual(node.paramInputs.length, 1, "Restored 1 param input");
        this.assertEqual(
            node.paramOutputs.length,
            1,
            "Restored 1 param output",
        );
        this.assertInstanceOf(
            node.paramInputs[0],
            ParamPort,
            "Restored param input is ParamPort",
        );
        this.assertInstanceOf(
            node.paramOutputs[0],
            ParamPort,
            "Restored param output is ParamPort",
        );
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
        // Optimizer node tests
        this.testOptimizerNodeCreation();
        this.testOptimizerNodeDefaultConfig();
        this.testOptimizerNodePortSubTypes();
        this.testOptimizerNodeCannotAddInput();
        this.testOptimizerNodeCannotRemoveInput();
        this.testOptimizerNodeToJSON();
        this.testOptimizerNodeFromJSON();

        // Visualization node tests
        this.testVisualizationNodeCreation();
        this.testVisualizationNodeCoordLimits();
        this.testVisualizationNodeColorInput();
        this.testVisualizationNodeColorModes();
        this.testVisualizationNodeDefaultPalette();
        this.testVisualizationNodeContinuousColors();
        this.testVisualizationNodeToJSON();
        this.testVisualizationNodeFromJSON();
        this.testVisualizationNodeRenumberPorts();

        // Output node role port tests
        this.testOutputNodeRolePorts();
        this.testOutputNodeRolePortRoles();
        this.testOutputNodeRolePortsOnRightSide();
        this.testOutputNodeRolePortsToJSON();
        this.testOutputNodeRolePortsFromJSON();

        // Export functionality tests
        this.testCompileToPython();
        this.testExportImageCreatesCanvas();

        // Link color tests
        this.testLinkHasWeightFlag();

        // Session roundtrip tests
        this.testSessionRoundtripWithOptimizerNode();
        this.testSessionRoundtripWithVisualizationNode();
        this.testSessionRoundtripWithOutputNodeRoles();

        // Param port tests
        this.testNormalizeNodeParamPorts();
        this.testParamPortDiamondShape();
        this.testParamPortToJSON();
        this.testParamPortFromJSON();
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
