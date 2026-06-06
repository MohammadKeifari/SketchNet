"""
Main code generation engine for SketchNet.

This module orchestrates the conversion of a SketchNet computation graph JSON
into executable PyTorch training code. The CodeGenerator class coordinates:
1. Graph parsing and phase analysis to determine execution order
2. Node translation through specialized translators
3. Code generation for data loading, model definition, training, and evaluation
4. Variable tracking to maintain consistency across code sections

The generated code follows a standard template:
- Imports and device setup
- load_and_preprocess(): Data loading and preprocessing
- Model class definition with __init__ and forward methods
- Training loop with loss computation and backpropagation
- Evaluation function for test data
- Evaluation phase with predictions and visualizations
- Main execution block
"""

import json
from .graph import parse_graph, Graph, Node
from .phase_analyzer import analyze_phases
from .writer import CodeWriter
from .translators import get_translator
import re

MODEL_TYPES = {
    "neuron",
    "layer",
    "conv2d",
    "flatten",
    "dropout",
    "batchnorm",
    "add",
    "concat",
    "output",
}

DATA_TRANSFORM_TYPES = {
    "column-select",
    "row-select",
    "dim-select",
    "normalize",
    "onehot",
    "deonehot",
    "train-test",
}


class CodeGenerator:
    """
    Generates executable PyTorch code from a SketchNet computation graph.

    The generator performs a multi-stage code generation process:
    1. Parses the JSON graph and analyzes execution phases
    2. Creates translator instances for each node
    3. Generates code sections in order (header, preprocessing, model, training, evaluation)
    4. Manages variable names to maintain consistency across sections

    Attributes:
        graph (Graph): The parsed computation graph.
        flow (Dict): Execution flow information from phase analysis.
        var_map (Dict): Mapping of node/port IDs to variable names.
        translators (Dict): Mapping of node IDs to translator instances.
    """

    def __init__(self, graph_data: dict):
        """
        Initialize the code generator with JSON graph data.

        Args:
            graph_data (dict): JSON representation of the computation graph from the frontend.
        """
        self.graph = parse_graph(graph_data)
        self.flow = analyze_phases(self.graph)
        self.var_map = {}  # node/port id -> variable name
        self.translators = {}  # node id -> translator instance

        for nid, node in self.graph.nodes.items():
            self.translators[nid] = get_translator(node, self.graph, self.var_map)

    def _sanitize_id(self, id_str):
        """
        Convert a graph ID into a valid Python variable name.

        Replaces any non-alphanumeric characters (except underscores) with underscores.

        Args:
            id_str (str): The graph element ID.

        Returns:
            str: A sanitized identifier suitable for Python code.
        """
        return re.sub(r"[^a-zA-Z0-9_]", "_", id_str)

    def _has_training(self) -> bool:
        # training is required if there is an optimizer
        if self.flow.get("optimizer") is not None:
            return True
        return any(
            self.graph.nodes[nid].type in MODEL_TYPES
            for nid in self.flow.get("train_set", set())
        )

    def _has_evaluation(self) -> bool:
        """Return True if any model node OR any analytics node (visualization, accuracy, print) is in the evaluation set."""
        eval_set = self.flow.get("eval_set", set())
        for nid in eval_set:
            node = self.graph.nodes[nid]
            if node.type in MODEL_TYPES | {"visualization", "accuracy", "print"}:
                return True
        return False

    def generate(self) -> str:
        """
        Generate the complete PyTorch training script.

        Orchestrates all code generation stages and assembles them into a single
        executable Python script.

        Returns:
            str: The complete generated Python code as a single string.
        """
        w = CodeWriter()
        self._write_header(w)
        self._write_load_and_preprocess(w)

        # Determine if we need to generate training/evaluation code
        has_optimizer = self.flow.get("optimizer") is not None
        has_model = (
            any(
                self.graph.nodes[nid].type in MODEL_TYPES
                for nid in self.flow.get("train_set", set())
            )
            or has_optimizer
        )  # optimizer implies model

        if has_model:
            self._write_model_class(w)
            self._write_training(w)
        else:
            w.line("# No model layers found – model and training loop skipped.")

        if self._has_evaluation():
            self._write_evaluate_function(w)
            self._write_evaluation(w)
        else:
            w.line("# No evaluation phase – evaluation and visualization skipped.")

        self._write_main(w)
        return str(w)

    # ------------------------------------------------------------------
    def _node_active_strict(self, nid, phase):
        """
        Check if a node is active in a phase using strict rules.

        A node is strictly active only if ALL its connected ports have the phase
        in their activation_phases list.

        Args:
            nid (str): The node ID.
            phase (str): The phase to check ("training" or "evaluation").

        Returns:
            bool: True if the node is active in the phase.
        """
        node = self.graph.nodes[nid]
        for p in node.inputs + node.paramInputs:
            if any(l.id_to == p.id for l in self.graph.links):
                if phase not in p.activation_phases:
                    return False
        for p in node.outputs + node.paramOutputs:
            if any(l.id_from == p.id for l in self.graph.links):
                if phase not in p.activation_phases:
                    return False
        return True

    def _write_header(self, w):
        """
        Write PyTorch imports and device initialization.

        Args:
            w (CodeWriter): The code writer.
        """
        w.line("import torch")
        w.line("import torch.nn as nn")
        w.line("import torch.optim as optim")
        w.line("from torch.utils.data import DataLoader, TensorDataset")
        w.line("import numpy as np")
        w.line("import matplotlib.pyplot as plt")
        w.line("")
        w.line("device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')")
        w.line("")

    def _write_preprocessing_visualizations(self, w):
        """
        Generate inline plotting code for visualization nodes active during preprocessing.
        Creates a local ``pre_viz_data`` dictionary that maps port IDs to the preprocessed
        variables, then calls the standard visualization code with the dict name replaced.
        """
        viz_nodes = [
            nid
            for nid in self.flow["preprocessing_order"]
            if self.graph.nodes[nid].type == "visualization"
        ]
        if not viz_nodes:
            return

        w.line("# --- Preprocessing visualizations ---")
        # Build a temporary viz_data dict for preprocessing variables
        w.line("pre_viz_data = {}")
        for nid in viz_nodes:
            node = self.graph.nodes[nid]
            for port in node.inputs:
                for link in self.graph.links:
                    if link.id_to == port.id:
                        src_port_id = link.id_from
                        if src_port_id in self.var_map:
                            w.line(
                                f"pre_viz_data['{port.id}'] = {self.var_map[src_port_id]}"
                            )
                        else:
                            src_id = self.graph.ports[src_port_id].node_id
                            if src_id in self.var_map:
                                w.line(
                                    f"pre_viz_data['{port.id}'] = {self.var_map[src_id]}"
                                )
                        break

        # Generate the standard visualization code, then replace 'viz_data' with 'pre_viz_data'
        from .writer import CodeWriter

        temp_writer = CodeWriter()
        for nid in viz_nodes:
            self.translators[nid].visualization_code(temp_writer)

        code = str(temp_writer)
        code = code.replace("viz_data", "pre_viz_data")
        for line in code.splitlines():
            w.line(line)

        w.line("# --- End preprocessing visualizations ---")
        w.line("")

    # ------------------------------------------------------------------
    def _write_load_and_preprocess(self, w):
        """Emit the load_and_preprocess function with data pipeline code."""
        w.line("def load_and_preprocess():")
        w.indent()

        # 1. InputData nodes (preprocessing)
        for nid in self.flow["preprocessing_order"]:
            node = self.graph.nodes[nid]
            if node.type == "input-data":
                self.translators[nid].data_code(w, "pre")

        # 2. Preprocessing nodes (strict execution)
        for nid in self.flow["preprocessing_order"]:
            node = self.graph.nodes[nid]
            if node.type != "input-data":
                self.translators[nid].data_code(w, "pre")

        self._write_preprocessing_visualizations(w)

        # 5. Determine variable names for the return
        train_feed = self._get_var_for_first_model_input("train")
        train_labels = self._get_var_for_optimizer_labels()
        test_feed = self._get_var_for_first_model_input("eval")
        test_labels = self._get_var_for_eval_labels()

        w.line(f"X_train = {train_feed}")
        w.line(f"y_train = {train_labels}")
        w.line(f"X_test = {test_feed}")
        w.line(f"y_test = {test_labels}")

        # 6. Build pre‑processed data dict for evaluation / visualisation
        w.line("pre_data = {")
        for key, var in self.var_map.items():
            w.line(f"    '{key}': {var},")
        w.line("}")
        self._x_test_var = test_feed
        self._y_test_var = test_labels
        w.line("return X_train, y_train, X_test, y_test, pre_data")
        w.dedent()
        w.line("")

    def _write_evaluate_function(self, w):
        """
        Writes a function `evaluate(model, X_test, y_test, pre_data)` that:
        - unpacks pre_data into local variables
        - runs the model **only if** any model node is active in the evaluation phase
        - executes remaining evaluation data nodes
        - collects viz_data and predictions
        """
        w.line("def evaluate(model, X_test, y_test, pre_data):")
        w.indent()  # inside evaluate

        # ---- 1. Unpack pre_data into local variables ----
        for key in self.var_map:
            sanitised = self._sanitize_id(key)
            w.line(f"{sanitised} = pre_data['{key}']")
            self.var_map[key] = sanitised

        w.line("")
        w.line("model.eval()")

        # ---- 2. Determine whether any model node is in the evaluation order ----
        eval_order = self.flow["eval_order"]
        model_in_eval = any(
            self.graph.nodes[nid].type in MODEL_TYPES for nid in eval_order
        )

        # ---- 3. Run model forward (if needed) ----
        if model_in_eval:
            w.line("with torch.no_grad():")
            w.indent()  # inside no_grad
            eval_feed = self._get_feed_key("eval")
            w.line(f"outputs = model({{'{eval_feed}': X_test.to(device)}})")

            output_node = next(
                (n for n in self.graph.nodes.values() if n.type == "output"), None
            )
            if output_node:
                for port in output_node.outputs:
                    sanitised = self._sanitize_id(port.id) + "_tensor"
                    w.line(f"{sanitised} = outputs['{port.id}']")
                    self.var_map[port.id] = sanitised
                if output_node.outputs:
                    first_sanitised = (
                        self._sanitize_id(output_node.outputs[0].id) + "_tensor"
                    )
                    self.var_map[output_node.id] = first_sanitised

            w.dedent()  # end no_grad
        else:
            w.line("# No model layers active in evaluation – skipping model forward")
            w.line("outputs = {}")

        # ---- 4. Execute remaining evaluation data nodes ----
        pre_set = self.flow.get("preprocessing_set", set())
        for nid in eval_order:
            node = self.graph.nodes[nid]
            if node.type in MODEL_TYPES or nid in pre_set:
                continue
            w.line(f"# Processing evaluation node {nid} ({node.type})")
            self.translators[nid].data_code(w, "eval")

        # ---- 5. Collect visualisation data ----
        w.line("viz_data = {}")
        for viz in self.flow.get("visualizations", []):
            for port in viz.inputs:
                for link in self.graph.links:
                    if link.id_to == port.id:
                        src_port_id = link.id_from
                        # 1) Try exact source port ID
                        if src_port_id in self.var_map:
                            w.line(
                                f"viz_data['{port.id}'] = {self.var_map[src_port_id]}"
                            )
                        else:
                            # 2) Fallback to source node ID
                            src_id = self.graph.ports[src_port_id].node_id
                            if src_id in self.var_map:
                                w.line(
                                    f"viz_data['{port.id}'] = {self.var_map[src_id]}"
                                )
                        break  # important: stop after first matching link

        # ---- 6. Predictions ----
        pred_port_id = None
        output_node = next(
            (n for n in self.graph.nodes.values() if n.type == "output"), None
        )
        if output_node:
            pred_port = next(
                (p for p in output_node.outputs if p.role == "prediction"), None
            )
            if pred_port:
                pred_port_id = pred_port.id
        if pred_port_id and model_in_eval:
            pred_var = self._sanitize_id(pred_port_id) + "_tensor"
            w.line(f"predictions = {pred_var}.cpu().numpy()")
        else:
            w.line("predictions = None  # no model prediction available")

        w.line("return predictions, viz_data")

        w.dedent()  # end evaluate function
        w.line("")

    # ------------------------------------------------------------------
    def _get_var_for_first_model_input(self, phase):
        """Resolve the variable name feeding the first model layer for a phase."""
        PHASE_MAP = {
            "preprocessing": "preprocessing",
            "train": "training",
            "eval": "evaluation",
        }
        full_phase = PHASE_MAP.get(phase, phase)

        order = self.flow[f"{phase}_order"]
        first_model = None
        for nid in order:
            if self.graph.nodes[nid].type in MODEL_TYPES:
                first_model = nid
                break
        if not first_model:
            return "None"

        explicit_candidates = []
        fallback_candidates = []

        for in_port in self.graph.nodes[first_model].inputs:
            for link in self.graph.links:
                if link.id_to == in_port.id:
                    src_port = self.graph.ports[link.id_from]
                    src_port_id = src_port.id  # port ID first
                    src_id = src_port.node_id

                    # 1) Check the source port ID
                    if src_port_id in self.var_map:
                        var = self.var_map[src_port_id]
                        if full_phase in src_port.activation_phases:
                            explicit_candidates.append(var)
                        else:
                            fallback_candidates.append(var)
                    # 2) Fall back to source node ID
                    elif src_id in self.var_map:
                        var = self.var_map[src_id]
                        if full_phase in src_port.activation_phases:
                            explicit_candidates.append(var)
                        else:
                            fallback_candidates.append(var)

        if explicit_candidates:
            return explicit_candidates[0]
        if fallback_candidates:
            return fallback_candidates[0]
        return "None"

    def _get_var_for_eval_labels(self):
        """Resolve the test-label variable connected to the output node."""
        output_node = next(
            (n for n in self.graph.nodes.values() if n.type == "output"), None
        )
        if not output_node:
            return "None"
        test_input = next((p for p in output_node.inputs if p.sub_type == "test"), None)
        if not test_input:
            return "None"

        for link in self.graph.links:
            if link.id_to == test_input.id:
                src_port_id = link.id_from
                # 1) Check source port ID first
                if src_port_id in self.var_map:
                    return self.var_map[src_port_id]
                # 2) Fallback to source node ID
                src_id = self.graph.ports[src_port_id].node_id
                if src_id in self.var_map:
                    return self.var_map[src_id]
        return "None"

    def _find_input_source(self, node_id):
        """Return the source node ID for a node's first input port."""
        node = self.graph.nodes[node_id]
        if not node.inputs:
            return None
        port = node.inputs[0]
        for link in self.graph.links:
            if link.id_to == port.id:
                return self.graph.ports[link.id_from].node_id
        return None

    # ------------------------------------------------------
    def _get_var_for_optimizer_labels(self):
        """Resolve the training-label variable connected to the optimizer."""
        opt = self.flow.get("optimizer")
        if not opt:
            return "None"
        labels_port = opt.inputs[1] if len(opt.inputs) > 1 else None
        if not labels_port:
            return "None"

        for link in self.graph.links:
            if link.id_to == labels_port.id:
                src_port_id = link.id_from
                # 1) Check source port ID first
                if src_port_id in self.var_map:
                    return self.var_map[src_port_id]
                # 2) Fallback to source node ID
                src_id = self.graph.ports[src_port_id].node_id
                if src_id in self.var_map:
                    return self.var_map[src_id]
        return "None"

    # ------------------------------------------------------------------
    def _write_model_class(self, w):
        """Emit the PyTorch Model class with init and forward methods."""
        w.line("class Model(nn.Module):")
        w.indent()
        w.line("def __init__(self):")
        w.indent()
        w.line("super().__init__()")
        model_nodes = set()
        pre_set = self.flow.get("preprocessing_set", set())
        for phase in ("train_order", "eval_order"):
            for nid in self.flow.get(phase, []):
                if nid in pre_set:
                    continue
                if self.graph.nodes[nid].type in MODEL_TYPES:
                    model_nodes.add(nid)
        ordered = []
        for nid in self.flow["train_order"]:
            if nid in model_nodes and nid not in ordered:
                ordered.append(nid)
        for nid in self.flow["eval_order"]:
            if nid in model_nodes and nid not in ordered:
                ordered.append(nid)
        for nid in ordered:
            self.translators[nid].init_code(w)
        w.dedent()
        w.line("")
        w.line("def forward(self, inputs_dict):")
        w.indent()
        w.line("outputs = {}")
        for nid in ordered:
            self.translators[nid].forward_code(w)
        w.line("return outputs")
        w.dedent()
        w.dedent()
        w.line("")

    # ------------------------------------------------------------------
    def _write_training_analytics(self, w):
        """Emit analytics node code inside the training loop."""
        train_analytics = [
            nid
            for nid in self.flow["train_order"]
            if nid not in self.flow["preprocessing_set"]
            and self.graph.nodes[nid].type not in MODEL_TYPES
        ]
        if not train_analytics:
            return

        # Temporarily add output port variables so translators can reference them
        output_node = next(
            (n for n in self.graph.nodes.values() if n.type == "output"), None
        )
        saved = {}
        if output_node:
            for port in output_node.outputs:
                saved[port.id] = self.var_map.get(port.id)
                self.var_map[port.id] = f"outputs['{port.id}']"

        for nid in train_analytics:
            self.translators[nid].data_code(w, "train")

        # Restore the original values (or remove if they were absent)
        if output_node:
            for port in output_node.outputs:
                if port.id in saved and saved[port.id] is not None:
                    self.var_map[port.id] = saved[port.id]
                else:
                    del self.var_map[port.id]

    def _write_training(self, w):
        """Emit the train_model function with optimizer and loss setup."""
        opt_node = self.flow.get("optimizer")
        if not opt_node:
            w.line("# No optimizer node – training loop not generated.")
            return
        w.line("def train_model(model, X_train, y_train, X_test, y_test, config=None):")
        w.indent()
        w.line("batch_size = config.get('batch_size', 32)")
        w.line("epochs = config.get('epochs', 10)")
        w.line("lr = config.get('learning_rate', 0.001)")
        w.line("loss_type = config.get('loss_type', 'mse')")
        w.line("")

        # --- Ensure labels are long for classification losses ---
        w.line("if loss_type in ('cross_entropy', 'nll'):")
        w.indent()
        w.line("y_train = y_train.long()")
        w.line("if y_test is not None: y_test = y_test.long()")
        w.dedent()
        w.line("")

        w.line("train_dataset = TensorDataset(X_train, y_train)")
        w.line(
            "train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=config.get('shuffle', True))"
        )
        w.line("")
        w.line("if y_test is not None:")
        w.indent()
        w.line("test_dataset = TensorDataset(X_test, y_test)")
        w.line(
            "test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)"
        )
        w.dedent()
        w.line("else:")
        w.indent()
        w.line("test_loader = None")
        w.line('print("No validation data – training only.")')
        w.dedent()
        w.line("")
        # Loss
        w.line("if loss_type == 'mse':")
        w.line("    criterion = nn.MSELoss()")
        w.line("elif loss_type == 'cross_entropy':")
        w.line("    criterion = nn.CrossEntropyLoss()")
        w.line("elif loss_type == 'bce':")
        w.line("    criterion = nn.BCEWithLogitsLoss()")
        w.line("elif loss_type == 'l1':")
        w.line("    criterion = nn.L1Loss()")
        w.line("elif loss_type == 'huber':")
        w.line("    criterion = nn.HuberLoss()")
        w.line("else:")
        w.line("    raise ValueError(f'Unknown loss type: {loss_type}')")
        w.line("")
        # Optimizer
        opt_type = opt_node.properties.get("optimizerType", "adam")
        w.line(f"if config.get('optimizer_type', '{opt_type}') == 'adam':")
        w.line("    optimizer = optim.Adam(model.parameters(), lr=lr,")
        w.line(
            "                               betas=(config.get('adam_beta1', 0.9), config.get('adam_beta2', 0.999)),"
        )
        w.line("                               eps=config.get('adam_epsilon', 1e-8),")
        w.line(
            "                               weight_decay=config.get('weight_decay', 0))"
        )
        w.line("elif config.get('optimizer_type') == 'sgd':")
        w.line("    optimizer = optim.SGD(model.parameters(), lr=lr,")
        w.line("                            momentum=config.get('sgd_momentum', 0.9),")
        w.line(
            "                            weight_decay=config.get('weight_decay', 0),"
        )
        w.line("                            nesterov=config.get('nesterov', False))")
        w.line("elif config.get('optimizer_type') == 'adamw':")
        w.line("    optimizer = optim.AdamW(model.parameters(), lr=lr,")
        w.line(
            "                             betas=(config.get('adam_beta1', 0.9), config.get('adam_beta2', 0.999)),"
        )
        w.line("                             eps=config.get('adam_epsilon', 1e-8),")
        w.line(
            "                             weight_decay=config.get('weight_decay', 0))"
        )
        w.line("")
        w.line("best_loss = float('inf')")
        w.line(
            "patience = config.get('early_stopping_patience', 10) if config.get('early_stopping') else None"
        )
        w.line("no_improve = 0")
        w.line("")
        w.line("for epoch in range(epochs):")
        w.indent()
        w.line("model.train()")
        w.line("total_loss = 0.0")
        w.line("for batch_X, batch_y in train_loader:")
        w.indent()
        w.line("batch_X, batch_y = batch_X.to(device), batch_y.to(device)")
        feed_key = self._get_feed_key("train")
        w.line(f"outputs = model({{'{feed_key}': batch_X}})")
        loss_port = self._get_loss_port_id()
        if loss_port:
            w.line(f"pred = outputs['{loss_port}']")
        else:
            w.line("pred = list(outputs.values())[0]")
        w.line("loss = criterion(pred, batch_y)")
        w.line("")
        w.line("# Training analytics")
        self._write_training_analytics(w)
        w.line("")
        w.line("")
        w.line("optimizer.zero_grad()")
        w.line("loss.backward()")
        if opt_node.properties.get("gradientClip") is not None:
            w.line(
                f"torch.nn.utils.clip_grad_norm_(model.parameters(), {opt_node.properties['gradientClip']})"
            )
        w.line("optimizer.step()")
        w.line("total_loss += loss.item() * batch_X.size(0)")
        w.dedent()  # end batch loop
        w.line("avg_train_loss = total_loss / len(train_loader.dataset)")
        w.line("")
        # Validation
        w.line("model.eval()")
        w.line("if test_loader is not None:")
        w.indent()
        w.line("val_loss = 0.0")
        w.line("with torch.no_grad():")
        w.indent()
        w.line("for batch_X, batch_y in test_loader:")
        w.indent()
        w.line("batch_X, batch_y = batch_X.to(device), batch_y.to(device)")
        eval_feed_key = self._get_feed_key("eval")
        w.line(f"outputs = model({{'{eval_feed_key}': batch_X}})")
        if loss_port:
            w.line(f"pred = outputs['{loss_port}']")
        else:
            w.line("pred = list(outputs.values())[0]")
        w.line("loss = criterion(pred, batch_y)")
        w.line("val_loss += loss.item() * batch_X.size(0)")
        w.dedent()  # end test batch loop
        w.dedent()  # end no_grad
        w.line("avg_val_loss = val_loss / len(test_loader.dataset)")
        w.dedent()  # end if test_loader is not None
        w.line("")
        # Print epoch summary (always)
        w.line("if test_loader is not None:")
        w.indent()
        w.line(
            "print(f'Epoch {epoch+1:3d}/{epochs}  Train Loss: {avg_train_loss:.6f}  Val Loss: {avg_val_loss:.6f}')"
        )
        w.dedent()
        w.line("else:")
        w.indent()
        w.line(
            "print(f'Epoch {epoch+1:3d}/{epochs}  Train Loss: {avg_train_loss:.6f}')"
        )
        w.dedent()
        w.line("")
        # Early stopping
        w.line("if patience is not None and test_loader is not None:")
        w.indent()
        w.line("if avg_val_loss < best_loss:")
        w.indent()
        w.line("best_loss = avg_val_loss")
        w.line("no_improve = 0")
        w.dedent()
        w.line("else:")
        w.indent()
        w.line("no_improve += 1")
        w.line("if no_improve >= patience:")
        w.indent()
        w.line('print("Early stopping triggered.")')
        w.line("break")
        w.dedent()
        w.dedent()
        w.dedent()  # end if patience
        w.dedent()  # end epoch loop
        w.line("")
        w.line("return model")
        w.dedent()  # end function
        w.line("")

    def _get_feed_key(self, phase):
        """Return the dict key used to feed tensors into the model for a phase."""
        PHASE_MAP = {
            "preprocessing": "preprocessing",
            "train": "training",
            "eval": "evaluation",
        }
        full_phase = PHASE_MAP.get(phase, phase)

        order = self.flow[f"{phase}_order"]
        for nid in order:
            if self.graph.nodes[nid].type in MODEL_TYPES:
                # first model node – look for a feeding node whose output has the phase
                for in_port in self.graph.nodes[nid].inputs:
                    for link in self.graph.links:
                        if link.id_to == in_port.id:
                            src_port = self.graph.ports[link.id_from]
                            if full_phase in src_port.activation_phases:
                                return src_port.node_id  # <-- node ID
                # fallback: any connected source node
                for in_port in self.graph.nodes[nid].inputs:
                    for link in self.graph.links:
                        if link.id_to == in_port.id:
                            return self.graph.ports[link.id_from].node_id
        return "input"

    def _get_loss_port_id(self):
        """Return the output port ID used for loss computation."""
        output_node = next(
            (n for n in self.graph.nodes.values() if n.type == "output"), None
        )
        if output_node:
            loss_port = next((p for p in output_node.outputs if p.role == "loss"), None)
            if loss_port:
                return loss_port.id
        return None

    # ------------------------------------------------------------------
    def _write_evaluation(self, w):
        """Emit the visualize function for evaluation-phase plots."""
        w.line("def visualize(viz_data):")
        w.indent()
        w.line("if not viz_data:")
        w.indent()
        w.line('print("No visualization data connected.")')
        w.line("return")
        w.dedent()
        viz_nodes = self.flow.get("visualizations", [])
        if viz_nodes:
            for viz in viz_nodes:
                self.translators[viz.id].visualization_code(w)
        else:
            w.line("pass")
        w.dedent()
        w.line("")

    # ------------------------------------------------------------------
    def _write_main(self, w):
        w.line("if __name__ == '__main__':")
        w.indent()
        w.line("X_train, y_train, X_test, y_test, pre_data = load_and_preprocess()")

        has_optimizer = self.flow.get("optimizer") is not None

        if has_optimizer:
            w.line("X_train = X_train.float()")
            w.line("if y_train is not None: y_train = y_train.float()")
        if self._has_evaluation() and self._x_test_var != "None":
            w.line("X_test = X_test.float()")
            w.line("if y_test is not None: y_test = y_test.float()")

        w.line("")

        if has_optimizer:
            opt_node = self.flow.get("optimizer")
            if opt_node:
                config_code = self.translators[opt_node.id].optimizer_code(w)
                w.line(f"opt_config = {config_code}")
            else:
                w.line("opt_config = {}")
            w.line("")
            w.line("model = Model().to(device)")
            w.line(
                "model = train_model(model, X_train, y_train, X_test, y_test, opt_config)"
            )
            w.line('print("Training complete.")')
            w.line("")

        if self._has_evaluation():
            if not has_optimizer:
                w.line("# No model created – evaluation skipped")
            else:
                w.line(
                    "predictions, viz_data = evaluate(model, X_test, y_test, pre_data)"
                )
                w.line("if y_test is not None:")
                w.indent()
                w.line("mse = np.mean((predictions - y_test.numpy())**2)")
                w.line('print(f"Test MSE: {mse:.6f}")')
                w.dedent()
                w.line("else:")
                w.indent()
                w.line('print("No test labels – skipping evaluation.")')
                w.dedent()
                w.line("visualize(viz_data)")

        w.dedent()
