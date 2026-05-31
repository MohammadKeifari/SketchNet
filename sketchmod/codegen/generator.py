import json
from .graph import parse_graph, Graph, Node
from .phase_analyzer import analyze_phases
from .writer import CodeWriter
from .translators import get_translator


class CodeGenerator:
    def __init__(self, graph_data: dict):
        self.graph = parse_graph(graph_data)
        self.flow = analyze_phases(self.graph)
        self.var_map = {}  # node/port id -> variable name
        self.translators = {}  # node id -> translator instance

        # Instantiate translators for all nodes
        for nid, node in self.graph.nodes.items():
            self.translators[nid] = get_translator(node, self.graph, self.var_map)

    def generate(self) -> str:
        w = CodeWriter()
        self._write_header(w)
        self._write_load_and_preprocess(w)
        self._write_model_class(w)
        self._write_training(w)
        self._write_evaluation(w)
        self._write_main(w)
        return str(w)

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

    def _write_load_and_preprocess(self, w):
        w.line("def load_and_preprocess():")
        w.indent()

        # 1. InputData node(s)
        input_nodes = [n for n in self.graph.nodes.values() if n.type == "input-data"]
        for node in input_nodes:
            self.translators[node.id].data_code(w, "pre")

        # 2. Preprocessing nodes
        for nid in self.flow["preprocessing_order"]:
            if self.graph.nodes[nid].type != "input-data":  # already handled
                self.translators[nid].data_code(w, "pre")

        # 3. Train branch data transforms
        w.line("")
        w.line("# --- Train branch data transforms ---")
        for nid in self.flow["train_data_order"]:
            self.translators[nid].data_code(w, "train")

        # 4. Test branch data transforms
        w.line("")
        w.line("# --- Test branch data transforms ---")
        for nid in self.flow["eval_data_order"]:
            self.translators[nid].data_code(w, "eval")

        # 5. Determine variable names for X_train, y_train, X_test, y_test
        # We need to find the tensors that feed the model and optimizer.
        opt_node = self.flow.get("optimizer")
        train_feed, train_labels = None, None
        test_feed = None

        # Training input: first model node's input source
        train_model = self.flow["train_model_order"]
        if train_model:
            first = train_model[0]
            # find source node id feeding its first input
            src_id = self._find_input_source(first)
            if src_id and src_id in self.var_map:
                train_feed = self.var_map[src_id]
            # else use placeholder
        if not train_feed:
            train_feed = "train_features"

        # Training labels: from optimizer's labels input
        if opt_node:
            labels_port = opt_node.inputs[1] if len(opt_node.inputs) > 1 else None
            if labels_port:
                label_src = None
                for link in self.graph.links:
                    if link.id_to == labels_port.id:
                        label_src = self.graph.ports[link.id_from].node_id
                        break
                if label_src and label_src in self.var_map:
                    train_labels = self.var_map[label_src]
        if not train_labels:
            train_labels = "train_labels_placeholder"

        # Test input: first eval model node's input source
        eval_model = self.flow["eval_model_order"]
        if eval_model:
            first = eval_model[0]
            src_id = self._find_input_source(first)
            if src_id and src_id in self.var_map:
                test_feed = self.var_map[src_id]
        if not test_feed:
            test_feed = "test_features"

        # Test labels: we might not need them for evaluation, but we'll try to find from test data pipeline
        test_labels = "test_labels_placeholder"

        w.line(f"X_train = {train_feed}")
        w.line(f"y_train = {train_labels}")
        w.line(f"X_test = {test_feed}")
        w.line(f"y_test = {test_labels}")
        w.line("return X_train, y_train, X_test, y_test")
        w.dedent()
        w.line("")

    def _find_input_source(self, node_id):
        """Return the node id that feeds the first input port of node_id."""
        node = self.graph.nodes[node_id]
        if not node.inputs:
            return None
        port = node.inputs[0]
        for link in self.graph.links:
            if link.id_to == port.id:
                return self.graph.ports[link.id_from].node_id
        return None

    def _write_model_class(self, w):
        w.line("class Model(nn.Module):")
        w.indent()
        w.line("def __init__(self):")
        w.indent()
        w.line("super().__init__()")
        # Collect model nodes from both train and eval orders (unique, topo sorted)
        model_nodes = set(
            self.flow["train_model_order"] + self.flow["eval_model_order"]
        )
        # Topological sort: use the order from flow
        ordered = []
        for nid in self.flow["train_model_order"]:
            if nid in model_nodes and nid not in ordered:
                ordered.append(nid)
        for nid in self.flow["eval_model_order"]:
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
        w.line("test_dataset = TensorDataset(X_test, y_test)")
        w.line(
            "train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=config.get('shuffle', True))"
        )
        w.line(
            "test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)"
        )
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
        # Early stopping setup
        w.line("best_loss = float('inf')")
        w.line(
            "patience = config.get('early_stopping_patience', 10) if config.get('early_stopping') else None"
        )
        w.line("no_improve = 0")
        w.line("")
        # Training loop
        w.line("for epoch in range(epochs):")
        w.indent()
        w.line("model.train()")
        w.line("total_loss = 0.0")
        w.line("for batch_X, batch_y in train_loader:")
        w.indent()
        w.line("batch_X, batch_y = batch_X.to(device), batch_y.to(device)")
        # Feed dict: determine which source node id to use
        feed_key = self._get_train_feed_key()
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
        w.dedent()
        w.line("avg_train_loss = total_loss / len(train_loader.dataset)")
        w.line("")
        # Validation
        w.line("model.eval()")
        w.line("val_loss = 0.0")
        w.line("with torch.no_grad():")
        w.indent()
        w.line("for batch_X, batch_y in test_loader:")
        w.indent()
        w.line("batch_X, batch_y = batch_X.to(device), batch_y.to(device)")
        eval_feed_key = self._get_eval_feed_key()
        w.line(f"outputs = model({{'{eval_feed_key}': batch_X}})")
        if loss_port:
            w.line(f"pred = outputs['{loss_port}']")
        else:
            w.line("pred = list(outputs.values())[0]")
        w.line("loss = criterion(pred, batch_y)")
        w.line("val_loss += loss.item() * batch_X.size(0)")
        w.dedent()
        w.dedent()
        w.line("avg_val_loss = val_loss / len(test_loader.dataset)")
        w.line("")
        w.line(
            f"print(f'Epoch {{epoch+1:3d}}/{{epochs}}  Train Loss: {{avg_train_loss:.6f}}  Val Loss: {{avg_val_loss:.6f}}')"
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
        w.dedent()
        w.line("")
        w.line("return model")
        w.dedent()
        w.line("")

    def _get_train_feed_key(self):
        train_model = self.flow["train_model_order"]
        if train_model:
            src_id = self._find_input_source(train_model[0])
            if src_id:
                return src_id
        return "input"

    def _get_eval_feed_key(self):
        eval_model = self.flow["eval_model_order"]
        if eval_model:
            src_id = self._find_input_source(eval_model[0])
            if src_id:
                return src_id
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

    def _write_evaluation(self, w):
        w.line("def evaluate(model, X_test, y_test):")
        w.indent()
        w.line("model.eval()")
        w.line("with torch.no_grad():")
        w.indent()
        eval_feed = self._get_eval_feed_key()
        w.line(f"outputs = model({{'{eval_feed}': X_test.to(device)}})")
        pred_port_id = None
        eval_port_id = None
        output_node = next(
            (n for n in self.graph.nodes.values() if n.type == "output"), None
        )
        if output_node:
            pred_port = next(
                (p for p in output_node.outputs if p.role == "prediction"), None
            )
            eval_port = next(
                (p for p in output_node.outputs if p.role == "evaluation"), None
            )
            if pred_port:
                pred_port_id = pred_port.id
            if eval_port:
                eval_port_id = eval_port.id
        if pred_port_id:
            w.line(f"predictions = outputs['{pred_port_id}'].cpu().numpy()")
        else:
            w.line("predictions = list(outputs.values())[0].cpu().numpy()")
        if eval_port_id:
            w.line(f"eval_values = outputs['{eval_port_id}'].cpu().numpy()")
        else:
            w.line("eval_values = predictions")
        w.line("mse = np.mean((predictions - y_test.numpy())**2)")
        w.line('print(f"Test MSE: {mse:.6f}")')
        w.line("return predictions, eval_values")
        w.dedent()
        w.dedent()
        w.line("")

        # Visualization
        viz_nodes = self.flow.get("visualizations", [])
        if viz_nodes:
            w.line("def visualize(predictions, y_test, eval_values):")
            w.indent()
            for viz in viz_nodes:
                self.translators[viz.id].visualization_code(w)
            w.dedent()
            w.line("")
        else:
            w.line("def visualize(predictions, y_test, eval_values):")
            w.indent()
            w.line("pass")
            w.dedent()
            w.line("")

    def _write_main(self, w):
        w.line("if __name__ == '__main__':")
        w.indent()
        w.line("X_train, y_train, X_test, y_test = load_and_preprocess()")
        w.line("X_train = X_train.float()")
        w.line("y_train = y_train.float()")
        w.line("X_test = X_test.float()")
        w.line("y_test = y_test.float()")
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
        w.line("predictions, eval_values = evaluate(model, X_test, y_test)")
        w.line("visualize(predictions, y_test, eval_values)")
        w.dedent()
