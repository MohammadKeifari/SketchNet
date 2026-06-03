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
    def __init__(self, graph_data: dict):
        self.graph = parse_graph(graph_data)
        self.flow = analyze_phases(self.graph)
        self.var_map = {}  # node/port id -> variable name
        self.translators = {}  # node id -> translator instance

        for nid, node in self.graph.nodes.items():
            self.translators[nid] = get_translator(node, self.graph, self.var_map)

    def _sanitize_id(self, id_str):
        """Replace any non-alphanumeric (except underscore) with '_'."""
        return re.sub(r"[^a-zA-Z0-9_]", "_", id_str)

    def generate(self) -> str:
        w = CodeWriter()
        self._write_header(w)
        self._write_load_and_preprocess(w)
        self._write_model_class(w)
        self._write_training(w)
        self._write_evaluate_function(w)
        self._write_evaluation(w)
        self._write_main(w)
        return str(w)

    # ------------------------------------------------------------------
    def _node_active_strict(self, nid, phase):
        """Return True if every connected port of nid has `phase` in activationPhases."""
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
        w.line("import torch")
        w.line("import torch.nn as nn")
        w.line("import torch.optim as optim")
        w.line("from torch.utils.data import DataLoader, TensorDataset")
        w.line("import numpy as np")
        w.line("import matplotlib.pyplot as plt")
        w.line("")
        w.line("device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')")
        w.line("")

    # ------------------------------------------------------------------
    def _write_load_and_preprocess(self, w):
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

        # 3. Train branch data transforms (strict execution; if not active, pass through)
        train_data_nodes = [
            nid
            for nid in self.flow["train_order"]
            if nid not in self.flow["preprocessing_order"]
            and self.graph.nodes[nid].type not in MODEL_TYPES
        ]
        w.line("")
        w.line("# --- Train branch data transforms ---")
        for nid in train_data_nodes:
            if self._node_active_strict(nid, "training"):
                self.translators[nid].data_code(w, "train")
            else:
                node = self.graph.nodes[nid]
                src_id = None
                for link in self.graph.links:
                    if link.id_to in {p.id for p in node.inputs}:
                        src_id = self.graph.ports[link.id_from].node_id
                        break
                if src_id and src_id in self.var_map:
                    self.var_map[nid] = self.var_map[src_id]
                    w.line(
                        f"# {nid} is not active in training; reusing {self.var_map[src_id]}"
                    )
                    w.line(f"{nid}_out = {self.var_map[src_id]}")

        # 4. Eval branch data transforms (strict execution; if not active, pass through)
        eval_data_nodes = [
            nid
            for nid in self.flow["eval_order"]
            if nid not in self.flow["preprocessing_order"]
            and self.graph.nodes[nid].type not in MODEL_TYPES
        ]
        w.line("")
        w.line("# --- Test branch data transforms ---")
        for nid in eval_data_nodes:
            if self._node_active_strict(nid, "evaluation"):
                self.translators[nid].data_code(w, "eval")
            else:
                node = self.graph.nodes[nid]
                src_id = None
                for link in self.graph.links:
                    if link.id_to in {p.id for p in node.inputs}:
                        src_id = self.graph.ports[link.id_from].node_id
                        break
                if src_id and src_id in self.var_map:
                    self.var_map[nid] = self.var_map[src_id]
                    w.line(
                        f"# {nid} is not active in evaluation; reusing {self.var_map[src_id]}"
                    )
                    w.line(f"{nid}_out = {self.var_map[src_id]}")

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
        w.line("return X_train, y_train, X_test, y_test, pre_data")
        w.dedent()
        w.line("")

    def _write_evaluate_function(self, w):
        """
        Writes a function `evaluate(model, X_test, y_test, pre_data)` that:
        - unpacks pre_data into local variables
        - runs the model
        - executes any remaining eval data nodes
        - collects viz_data and predictions
        """
        w.line("def evaluate(model, X_test, y_test, pre_data):")
        w.indent()

        # Unpack pre_data into local variables so translators find them
        w.line("# Unpack preprocessed tensors")
        for key in self.var_map:
            w.line(f"{key} = pre_data['{key}']")

        w.line("")
        w.line("model.eval()")
        w.line("with torch.no_grad():")
        w.indent()
        eval_feed = self._get_feed_key("eval")
        w.line(f"outputs = model({{'{eval_feed}': X_test.to(device)}})")

        # Store model outputs with sanitised names and add to var_map
        output_node = next(
            (n for n in self.graph.nodes.values() if n.type == "output"), None
        )
        if output_node:
            for port in output_node.outputs:
                var_name = self._sanitize_id(port.id) + "_tensor"
                w.line(f"{var_name} = outputs['{port.id}']")
                self.var_map[port.id] = var_name
            if output_node.outputs:
                self.var_map[output_node.id] = (
                    self._sanitize_id(output_node.outputs[0].id) + "_tensor"
                )

        # Execute remaining eval data nodes (DeOneHot etc.)
        eval_order = self.flow["eval_order"]
        pre_set = self.flow.get("preprocessing_set", set())
        for nid in eval_order:
            node = self.graph.nodes[nid]
            if node.type in MODEL_TYPES or nid in pre_set:
                continue
            self.translators[nid].data_code(w, "eval")

        # Collect visualisation data
        w.line("viz_data = {}")
        for viz in self.flow.get("visualizations", []):
            for port in viz.inputs:
                for link in self.graph.links:
                    if link.id_to == port.id:
                        src_id = self.graph.ports[link.id_from].node_id
                        if src_id in self.var_map:
                            w.line(f"viz_data['{port.id}'] = {self.var_map[src_id]}")
                        break

        # Predictions for optional printing
        pred_port_id = None
        if output_node:
            pred_port = next(
                (p for p in output_node.outputs if p.role == "prediction"), None
            )
            if pred_port:
                pred_port_id = pred_port.id
        if pred_port_id:
            w.line(
                f"predictions = {self._sanitize_id(pred_port_id)}_tensor.cpu().numpy()"
            )
        else:
            w.line("predictions = list(outputs.values())[0].cpu().numpy()")
        w.dedent()  # end no_grad

        w.line("return predictions, viz_data")
        w.dedent()
        w.line("")

    # ------------------------------------------------------------------
    def _get_var_for_first_model_input(self, phase):
        # Map generator's short names to the full names used in port activationPhases
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
                    src_id = src_port.node_id
                    if src_id not in self.var_map:
                        continue
                    var = self.var_map[src_id]
                    if full_phase in src_port.activation_phases:
                        explicit_candidates.append(var)
                    else:
                        fallback_candidates.append(var)
        print(
            f"[DEBUG] phase={phase}, full_phase={full_phase}, explicit={explicit_candidates}, fallback={fallback_candidates}"
        )
        if explicit_candidates:
            return explicit_candidates[0]
        if fallback_candidates:
            return fallback_candidates[0]
        return "None"

    def _get_var_for_eval_labels(self):
        """
        Return the variable for test labels, or 'None' if not found.
        A label node must:
        - be a data‑transform or onehot/deonehot node
        - NOT feed any model node (directly)
        - feed the OutputNode's test input, or a visualization
        """
        output_node = next(
            (n for n in self.graph.nodes.values() if n.type == "output"), None
        )

        # Collect allowed target port ids
        allowed_targets = set()
        if output_node:
            test_input = next(
                (p for p in output_node.inputs if p.sub_type == "test"), None
            )
            if test_input:
                allowed_targets.add(test_input.id)
        for viz in self.flow.get("visualizations", []):
            for p in viz.inputs:
                allowed_targets.add(p.id)

        if not allowed_targets:
            return "None"

        for nid, node in self.graph.nodes.items():
            if node.type not in DATA_TRANSFORM_TYPES and node.type not in (
                "onehot",
                "deonehot",
            ):
                continue

            # 1. Must not feed any model node
            feeds_model = False
            for out_port in node.outputs:
                for link in self.graph.links:
                    if link.id_from == out_port.id:
                        tgt_id = self.graph.ports[link.id_to].node_id
                        if self.graph.nodes[tgt_id].type in MODEL_TYPES:
                            feeds_model = True
                            break
                if feeds_model:
                    break
            if feeds_model:
                continue

            # 2. Must feed an allowed target
            for out_port in node.outputs:
                for link in self.graph.links:
                    if link.id_from == out_port.id and link.id_to in allowed_targets:
                        if nid in self.var_map:
                            return self.var_map[nid]

        return "None"

    def _find_input_source(self, node_id):
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
        opt = self.flow.get("optimizer")
        if not opt:
            return "None"
        labels_port = opt.inputs[1] if len(opt.inputs) > 1 else None
        if not labels_port:
            return "None"

        for link in self.graph.links:
            if link.id_to == labels_port.id:
                src_id = self.graph.ports[link.id_from].node_id
                if src_id in self.var_map:
                    return self.var_map[src_id]
        return "None"

    # ------------------------------------------------------------------
    def _write_model_class(self, w):
        w.line("class Model(nn.Module):")
        w.indent()
        w.line("def __init__(self):")
        w.indent()
        w.line("super().__init__()")
        model_nodes = set()
        for phase in ("train_order", "eval_order"):
            for nid in self.flow.get(phase, []):
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
    def _write_training(self, w):
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
        w.line("")
        w.line(
            "print(f'Epoch {epoch+1:3d}/{epochs}  Train Loss: {avg_train_loss:.6f}  Val Loss: {avg_val_loss:.6f}')"
        )
        w.line("")
        w.line("if patience is not None:")
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
        w.dedent()  # end if test_loader
        w.dedent()  # end epoch loop
        w.line("")
        w.line("return model")
        w.dedent()  # end function
        w.line("")

    def _get_feed_key(self, phase):
        PHASE_MAP = {
            "preprocessing": "preprocessing",
            "train": "training",
            "eval": "evaluation",
        }
        full_phase = PHASE_MAP.get(phase, phase)

        order = self.flow[f"{phase}_order"]
        for nid in order:
            if self.graph.nodes[nid].type in MODEL_TYPES:
                # look for an input source that has the phase on its output port
                for in_port in self.graph.nodes[nid].inputs:
                    for link in self.graph.links:
                        if link.id_to == in_port.id:
                            src_port = self.graph.ports[link.id_from]
                            if full_phase in src_port.activation_phases:
                                return src_port.node_id
                # fallback: any connected source
                for in_port in self.graph.nodes[nid].inputs:
                    for link in self.graph.links:
                        if link.id_to == in_port.id:
                            return self.graph.ports[link.id_from].node_id
        return "input"

    def _get_loss_port_id(self):
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
        w.line("X_train = X_train.float()")
        w.line("if y_train is not None: y_train = y_train.float()")
        w.line("X_test = X_test.float()")
        w.line("if y_test is not None: y_test = y_test.float()")
        w.line("")
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
        w.line("predictions, viz_data = evaluate(model, X_test, y_test, pre_data)")
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
