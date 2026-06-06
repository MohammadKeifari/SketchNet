"""
Main code generation engine for SketchNet.
Orchestrates the conversion of a graph into a runnable PyTorch script.
"""

import json
import re
from .graph import parse_graph
from .phase_analyzer import analyze_phases
from .writer import CodeWriter
from .translators import get_translator

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


class CodeGenerator:
    def __init__(self, graph_data: dict):
        self.graph = parse_graph(graph_data)
        self.flow = analyze_phases(self.graph)
        self.var_map = {}
        self.translators = {}

        for nid, node in self.graph.nodes.items():
            self.translators[nid] = get_translator(node, self.graph, self.var_map)

    def generate(self) -> str:
        w = CodeWriter()
        self._emit_header(w)
        self._emit_load_and_preprocess(w)

        has_opt = self.flow["optimizer"] is not None
        has_train = len(self.flow["train_order"]) > 0
        has_eval = len(self.flow["eval_order"]) > 0

        if has_train and has_opt:
            self._emit_model_class(w)
            self._emit_train_model(w)
        else:
            w.line("# No training phase with optimizer – training skipped.")

        if has_eval:
            self._emit_evaluate(w)
        else:
            w.line("# No evaluation phase.")

        self._emit_main(w)
        return str(w)

    def _emit_header(self, w):
        w.line("import torch")
        w.line("import torch.nn as nn")
        w.line("import torch.optim as optim")
        w.line("from torch.utils.data import DataLoader, TensorDataset")
        w.line("import numpy as np")
        w.line("import matplotlib.pyplot as plt")
        w.line("")
        w.line("device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')")
        w.line("")

    def _emit_load_and_preprocess(self, w):
        w.line("def load_and_preprocess():")
        w.indent()

        order = self.flow["preprocessing_order"]
        for nid in order:
            self.translators[nid].generate(w, "preprocessing", "data")

        w.line("pre_data = {")
        for port_id in self.flow["train_seed_ports"]:
            if port_id in self.var_map:
                w.line(f"    '{port_id}': {self.var_map[port_id]},")
        for port_id in self.flow["eval_seed_ports"]:
            if port_id in self.var_map:
                w.line(f"    '{port_id}': {self.var_map[port_id]},")
        for nid in order:
            node = self.graph.nodes[nid]
            if node.type == "onehot" and node.paramOutputs:
                pid = node.paramOutputs[0].id
                if pid in self.var_map:
                    w.line(f"    '{pid}': {self.var_map[pid]},")
            if node.type == "normalize" and node.paramOutputs:
                pid = node.paramOutputs[0].id
                for suffix in ("_mean", "_std"):
                    key = pid + suffix
                    if key in self.var_map:
                        w.line(f"    '{key}': {self.var_map[key]},")
        w.line("}")
        w.line("return pre_data")
        w.dedent()
        w.line("")

    def _emit_model_class(self, w):
        train_order = self.flow["train_order"]
        w.line("class Model(nn.Module):")
        w.indent()
        w.line("def __init__(self):")
        w.indent()
        w.line("super().__init__()")
        for nid in train_order:
            self.translators[nid].generate(w, "training", "init")
        w.dedent()
        w.line("")
        w.line("def forward(self, inputs_dict):")
        w.indent()
        w.line("outputs = {}")
        for idx, nid in enumerate(train_order):
            self.translators[nid].generate(
                w, "training", "forward", is_first=(idx == 0)
            )
        w.line("return outputs")
        w.dedent()
        w.dedent()
        w.line("")

    def _emit_train_model(self, w):
        opt_node = self.flow["optimizer"]
        w.line("def train_model(model, pre_data, config):")
        w.indent()

        self._unpack_pre_data(w)

        feat_var = self._get_var_for_first_model_input("train")
        label_var = self._get_var_for_optimizer_labels()

        w.line(f"features = {feat_var}.float()")
        w.line(f"labels = {label_var}")

        w.line("batch_size = config.get('batch_size', 32)")
        w.line("dataset = TensorDataset(features, labels)")
        w.line(
            "loader = DataLoader(dataset, batch_size=batch_size, shuffle=config.get('shuffle', True))"
        )
        w.line("")

        translator = self.translators[opt_node.id]
        translator.emit_training_setup(w)

        w.line("best_loss = float('inf')")
        w.line(
            "patience = config.get('early_stopping_patience', 10) if config.get('early_stopping') else None"
        )
        w.line("no_improve = 0")
        w.line("")

        w.line("for epoch in range(config.get('epochs', 10)):")
        w.indent()
        w.line("model.train()")
        w.line("total_loss = 0.0")
        w.line("for batch_X, batch_y in loader:")
        w.indent()
        w.line("batch_X, batch_y = batch_X.to(device), batch_y.to(device)")
        feed_key, _ = self._get_feed_key("train")
        w.line(f"inputs_dict = {{'{feed_key}': batch_X}}")
        w.line("outputs = model(inputs_dict)")

        loss_port = self._get_loss_port_id()
        if loss_port:
            w.line(f"loss = criterion(outputs['{loss_port}'], batch_y)")
        else:
            w.line("loss = criterion(list(outputs.values())[0], batch_y)")

        if opt_node.properties.get("gradientClip") is not None:
            w.line(
                f"torch.nn.utils.clip_grad_norm_(model.parameters(), {opt_node.properties['gradientClip']})"
            )
        w.line("optimizer.zero_grad()")
        w.line("loss.backward()")
        w.line("optimizer.step()")
        w.line("total_loss += loss.item() * batch_X.size(0)")
        w.dedent()
        w.line("avg_train_loss = total_loss / len(loader.dataset)")
        w.line("print(f'Epoch {epoch+1:3d}  Train Loss: {avg_train_loss:.6f}')")

        test_label_var = self._get_var_for_eval_labels()
        if test_label_var != "None":
            w.line(
                f"val_features = {self._get_var_for_first_model_input('eval')}.float()"
            )
            w.line(f"val_labels = {test_label_var}")
            loss_type = opt_node.properties.get("lossType", "mse")
            if loss_type in ("cross_entropy", "nll"):
                w.line("val_labels = val_labels.long()")
            w.line("model.eval()")
            w.line("with torch.no_grad():")
            w.indent()
            eval_feed_key, _ = self._get_feed_key("eval")
            w.line(f"outputs = model({{'{eval_feed_key}': val_features.to(device)}})")
            if loss_port:
                w.line(
                    f"val_loss = criterion(outputs['{loss_port}'], val_labels.to(device)).item()"
                )
            else:
                w.line(
                    "val_loss = criterion(list(outputs.values())[0], val_labels.to(device)).item()"
                )
            w.dedent()
            w.line("print(f'           Val Loss: {val_loss:.6f}')")
            w.line("if patience is not None:")
            w.indent()
            w.line("if val_loss < best_loss:")
            w.indent()
            w.line("best_loss = val_loss")
            w.line("no_improve = 0")
            w.dedent()
            w.line("else:")
            w.indent()
            w.line("no_improve += 1")
            w.line("if no_improve >= patience:")
            w.indent()
            w.line("print('Early stopping.')")
            w.line("break")
            w.dedent()
            w.dedent()
            w.dedent()

        w.dedent()
        w.line("return model")
        w.dedent()
        w.line("")

    def _emit_evaluate(self, w):
        w.line("def evaluate(model, pre_data):")
        w.indent()
        self._unpack_pre_data(w)

        has_train = (
            len(self.flow["train_order"]) > 0 and self.flow["optimizer"] is not None
        )

        if has_train:
            w.line("model.eval()")
            w.line("with torch.no_grad():")
            w.indent()
            eval_feed_key, eval_feed_var = self._get_feed_key("eval")
            w.line(
                f"eval_in = {{'{eval_feed_key}': {eval_feed_var}.float().to(device)}}"
            )
            w.line("outputs = model(eval_in)")
            output_node = next(
                (n for n in self.graph.nodes.values() if n.type == "output"), None
            )
            if output_node:
                for port in output_node.outputs:
                    sanitized = self._sanitize(port.id) + "_tensor"
                    w.line(f"{sanitized} = outputs['{port.id}']")
                    self.var_map[port.id] = sanitized
            w.dedent()
        else:
            w.line("# No trained model – running evaluation nodes untrained")

        train_set = set(self.flow["train_order"])
        for nid in self.flow["eval_order"]:
            if nid in train_set:
                continue
            self.translators[nid].generate(w, "evaluation", "data")

        viz_nodes = [
            nid
            for nid in self.flow["eval_order"]
            if self.graph.nodes[nid].type == "visualization"
        ]
        if viz_nodes:
            w.line("viz_data = {}")
            for viz_nid in viz_nodes:
                viz = self.graph.nodes[viz_nid]
                for port in viz.inputs:
                    for link in self.graph.links:
                        if link.id_to == port.id:
                            src = self.var_map.get(link.id_from)
                            if src is None:
                                src_nid = self.graph.ports[link.id_from].node_id
                                src = self.var_map.get(src_nid, "None")
                            w.line(f"viz_data['{port.id}'] = {src}")
                            break
        w.line("return viz_data if 'viz_data' in dir() else {}")
        w.dedent()
        w.line("")

    def _emit_main(self, w):
        w.line("if __name__ == '__main__':")
        w.indent()
        w.line("pre_data = load_and_preprocess()")

        has_opt = self.flow["optimizer"] is not None
        has_train = len(self.flow["train_order"]) > 0 and has_opt
        has_eval = len(self.flow["eval_order"]) > 0

        if has_train:
            opt_node = self.flow["optimizer"]
            config = self.translators[opt_node.id].get_config()
            w.line(f"config = {config}")
            w.line("model = Model().to(device)")
            w.line("model = train_model(model, pre_data, config)")
            w.line("print('Training complete.')")
            w.line("")
        else:
            w.line("model = None")

        if has_eval:
            w.line("viz_data = evaluate(model, pre_data)")

        w.dedent()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _sanitize(self, id_str: str) -> str:
        return re.sub(r"[^a-zA-Z0-9_]", "_", id_str)

    def _unpack_pre_data(self, w):
        for port_id in self.flow["train_seed_ports"]:
            if port_id in self.var_map:
                var = self.var_map[port_id]
                w.line(f"{var} = pre_data['{port_id}']")
        for port_id in self.flow["eval_seed_ports"]:
            if port_id in self.var_map:
                var = self.var_map[port_id]
                w.line(f"{var} = pre_data['{port_id}']")
        for nid in self.flow["preprocessing_order"]:
            node = self.graph.nodes[nid]
            if node.type == "onehot" and node.paramOutputs:
                pid = node.paramOutputs[0].id
                if pid in self.var_map:
                    w.line(f"{self.var_map[pid]} = pre_data['{pid}']")
            if node.type == "normalize" and node.paramOutputs:
                pid = node.paramOutputs[0].id
                for suffix in ("_mean", "_std"):
                    key = pid + suffix
                    if key in self.var_map:
                        w.line(f"{self.var_map[key]} = pre_data['{key}']")
        w.line("")

    def _get_first_model_node_id(self, phase):
        order = self.flow[f"{phase}_order"]
        for nid in order:
            if self.graph.nodes[nid].type in MODEL_TYPES:
                return nid
        return None

    def _get_feed_key(self, phase: str):
        PHASE_MAP = {"train": "training", "eval": "evaluation"}
        full_phase = PHASE_MAP[phase]
        nid = self._get_first_model_node_id(phase)
        if nid is None:
            return None, None
        node = self.graph.nodes[nid]
        for port in node.inputs:
            for link in self.graph.links:
                if link.id_to == port.id:
                    src_port = self.graph.ports[link.id_from]
                    if full_phase in src_port.activation_phases:
                        src_node_id = src_port.node_id
                        var = self.var_map.get(src_port.id) or self.var_map.get(
                            src_node_id
                        )
                        return src_node_id, var
        for port in node.inputs:
            for link in self.graph.links:
                if link.id_to == port.id:
                    src_node_id = self.graph.ports[link.id_from].node_id
                    var = self.var_map.get(link.id_from) or self.var_map.get(
                        src_node_id
                    )
                    return src_node_id, var
        return None, None

    def _get_var_for_first_model_input(self, phase):
        _, var = self._get_feed_key(phase)
        return var if var else "None"

    def _get_var_for_optimizer_labels(self):
        opt = self.flow.get("optimizer")
        if not opt or len(opt.inputs) < 2:
            return "None"
        labels_port = opt.inputs[1]
        for link in self.graph.links:
            if link.id_to == labels_port.id:
                src = link.id_from
                if src in self.var_map:
                    return self.var_map[src]
                src_nid = self.graph.ports[src].node_id
                if src_nid in self.var_map:
                    return self.var_map[src_nid]
        return "None"

    def _get_var_for_eval_labels(self):
        output_node = next(
            (n for n in self.graph.nodes.values() if n.type == "output"), None
        )
        if not output_node:
            return "None"
        for port in output_node.inputs:
            for link in self.graph.links:
                if link.id_to == port.id:
                    src_port = self.graph.ports[link.id_from]
                    if "evaluation" in src_port.activation_phases:
                        for l2 in self.graph.links:
                            if l2.id_to == src_port.id:
                                if l2.id_from in self.var_map:
                                    return self.var_map[l2.id_from]
                                src_nid = self.graph.ports[l2.id_from].node_id
                                if src_nid in self.var_map:
                                    return self.var_map[src_nid]
        return "None"

    def _get_loss_port_id(self):
        output_node = next(
            (n for n in self.graph.nodes.values() if n.type == "output"), None
        )
        if output_node:
            for p in output_node.outputs:
                if p.role == "loss":
                    return p.id
        return None
