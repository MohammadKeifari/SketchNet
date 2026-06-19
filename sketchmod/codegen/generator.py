"""
Main code generation engine for SketchNet.

Orchestrates the conversion of a graph into a runnable PyTorch script.
The generator:
1. Parses the front-end JSON into a Graph.
2. Runs phase analysis to partition nodes into preprocessing, training, and evaluation.
3. Uses translators to emit code for each node in the appropriate context.
4. Handles special nodes (optimizer, output, visualizations) with dedicated logic.
"""

import json
import re
from .graph import parse_graph
from .phase_analyzer import analyze_phases
from .writer import CodeWriter
from .translators import get_translator


class CodeGenerator:
    """Generates PyTorch training code from a SketchNet graph."""

    def __init__(self, graph_data: dict):
        """
        Initialize with JSON graph data.

        Args:
            graph_data: dictionary with "nodes", "links", "ports", "nodeCounter".
        """
        self.graph = parse_graph(graph_data)
        # Keep only the first optimizer for code generation
        self.graph = self._remove_extra_optimizers(self.graph)
        self.flow = analyze_phases(self.graph)
        self.var_map = {}  # port/node id -> variable name
        self.translators = {}  # node id -> translator instance

        for nid, node in self.graph.nodes.items():
            self.translators[nid] = get_translator(node, self.graph, self.var_map)

    # ------------------------------------------------------------------
    def generate(self) -> str:
        """Produce the complete PyTorch script."""
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
            # Check if evaluation enters the model at the same point as training
            eval_ok = self._eval_entry_matches()
            if eval_ok:
                self._emit_evaluate(w)
            else:
                w.line(
                    "# Evaluation skipped – enters model at a different point than training."
                )
        else:
            w.line("# No evaluation phase.")

        self._emit_main(w)
        return str(w)

    # ------------------------------------------------------------------
    #  HEADER
    # ------------------------------------------------------------------
    def _emit_header(self, w: CodeWriter):
        """Write imports and device selection."""
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
    #  LOAD & PREPROCESS
    # ------------------------------------------------------------------
    def _emit_load_and_preprocess(self, w: CodeWriter):
        """Emit the load_and_preprocess function.

        Executes all preprocessing nodes in topological order and returns a
        `pre_data` dictionary containing only the terminal outputs needed by
        training or evaluation.
        """
        w.line("def load_and_preprocess():")
        w.indent()

        order = self.flow["preprocessing_order"]
        for nid in order:
            self.translators[nid].generate(w, "preprocessing", "data")

        # Build pre_data with train/eval seed ports and param-sharing variables
        w.line("pre_data = {")
        for port_id in self.flow["train_seed_ports"]:
            if port_id in self.var_map:
                w.line(f"    '{port_id}': {self.var_map[port_id]},")
        for port_id in self.flow["eval_seed_ports"]:
            if port_id in self.var_map:
                w.line(f"    '{port_id}': {self.var_map[port_id]},")

        # Include param outputs (OneHot categories, Normalize statistics)
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

    # ------------------------------------------------------------------
    #  MODEL CLASS
    # ------------------------------------------------------------------
    def _get_model_nodes(self):
        """
        Identify training‑order nodes that belong to the model.

        The model consists of all nodes reachable backward from the output
        node via links whose ports are active in the training phase.
        Excludes preprocessing nodes (they already ran).
        """
        train_set = self.flow["train_set"]
        output_id = None
        for nid in train_set:
            if self.graph.nodes[nid].type == "output":
                output_id = nid
                break
        if output_id is None:
            return []

        reachable = set()
        queue = [output_id]
        while queue:
            cur = queue.pop(0)
            if cur in reachable:
                continue
            reachable.add(cur)
            for pred in self.graph.predecessors(cur):
                if pred in train_set and pred not in reachable:
                    queue.append(pred)

        pre_set = self.flow.get("preprocessing_set", set())
        # Keep only nodes that are NOT in preprocessing
        return [
            nid
            for nid in self.flow["train_order"]
            if nid in reachable and nid not in pre_set
        ]

    def _emit_model_class(self, w: CodeWriter):
        """Write the Model(nn.Module) class.

        All model nodes (as determined by _get_model_nodes) become part of
        the class.  Non‑model training nodes (label processing, etc.) are
        executed once before the training loop.
        """
        model_nodes = self._get_model_nodes()
        if not model_nodes:
            return

        w.line("class Model(nn.Module):")
        w.indent()
        w.line("def __init__(self):")
        w.indent()
        w.line("super().__init__()")
        for nid in model_nodes:
            self.translators[nid].generate(w, "training", "init")
        w.dedent()
        w.line("")
        w.line("def forward(self, inputs_dict):")
        w.indent()
        w.line("outputs = {}")
        for idx, nid in enumerate(model_nodes):
            is_first = idx == 0
            self.translators[nid].generate(w, "training", "forward", is_first=is_first)
        w.line("return outputs")
        w.dedent()
        w.dedent()
        w.line("")

    # ------------------------------------------------------------------
    #  TRAIN MODEL
    # ------------------------------------------------------------------
    def _emit_train_model(self, w: CodeWriter):
        """Emit the train_model function with training loop.

        Non‑model training nodes that process labels are executed once before
        the loop.  Analytics (Print, Accuracy) that depend on model outputs
        are executed inside the loop after the forward pass.
        """
        opt_node = self.flow["optimizer"]
        w.line("def train_model(model, pre_data, config):")
        w.indent()

        self._unpack_pre_data(w)

        model_nodes = set(self._get_model_nodes())
        pre_set = self.flow.get("preprocessing_set", set())

        # ---- Execute label‑processing nodes (non‑model, no dependency on model) ----
        for nid in self.flow["train_order"]:
            if nid in model_nodes or nid in pre_set:
                continue
            node = self.graph.nodes[nid]
            if node.type in ("optimizer", "visualization"):
                continue
            # Check if this node reads from a model node
            reads_from_model = False
            for port in node.inputs:
                for link in self.graph.links:
                    if link.id_to == port.id:
                        src_nid = self.graph.ports[link.id_from].node_id
                        if src_nid in model_nodes:
                            reads_from_model = True
                            break
                if reads_from_model:
                    break
            if reads_from_model:
                continue  # will run inside the loop
            self.translators[nid].generate(w, "training", "data")

        # ---- Feature & label extraction ----
        feat_var = self._get_var_for_first_model_input("train")
        label_var = self._get_var_for_optimizer_labels()

        w.line(f"features = {feat_var}.float()")
        w.line(f"labels = {label_var}")

        # ---- Loss & optimizer setup (including label cast) ----
        translator = self.translators[opt_node.id]
        translator.emit_training_setup(w)

        w.line("batch_size = config.get('batch_size', 32)")
        w.line("dataset = TensorDataset(features, labels)")
        w.line(
            "loader = DataLoader(dataset, batch_size=batch_size, shuffle=config.get('shuffle', True))"
        )
        w.line("")

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

        # ---- Run output‑dependent analytics (Print, Accuracy) ----
        # Store output port variables so they can be referenced
        output_node = next(
            (n for n in self.graph.nodes.values() if n.type == "output"), None
        )
        if output_node:
            for port in output_node.outputs:
                sanitized = self._sanitize(port.id) + "_tensor"
                w.line(f"{sanitized} = outputs['{port.id}']")
                self.var_map[port.id] = sanitized

        for nid in self.flow["train_order"]:
            if nid in model_nodes or nid in pre_set:
                continue
            node = self.graph.nodes[nid]
            if node.type in ("optimizer", "visualization"):
                continue
            reads_from_model = False
            for port in node.inputs:
                for link in self.graph.links:
                    if link.id_to == port.id:
                        src_nid = self.graph.ports[link.id_from].node_id
                        if src_nid in model_nodes:
                            reads_from_model = True
                            break
                if reads_from_model:
                    break
            if not reads_from_model:
                continue  # already executed before the loop
            self.translators[nid].generate(w, "training", "data")

        w.dedent()  # end batch loop
        w.line("avg_train_loss = total_loss / len(loader.dataset)")
        w.line("print(f'Epoch {epoch+1:3d}  Train Loss: {avg_train_loss:.6f}')")

        # Validation (only if test labels exist)
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
            w.line("with torch.inference_mode():")
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

    # ------------------------------------------------------------------
    #  EVALUATE
    # ------------------------------------------------------------------
    def _emit_evaluate(self, w: CodeWriter):
        """Emit the evaluate function.

        Runs the trained model on evaluation data and then executes
        any evaluation‑only nodes (DeOneHot, visualizations, etc.).
        """
        w.line("def evaluate(model, pre_data):")
        w.indent()
        self._unpack_pre_data(w)

        has_train = (
            len(self.flow["train_order"]) > 0 and self.flow["optimizer"] is not None
        )

        if has_train:
            w.line("model.eval()")
            w.line("with torch.inference_mode():")
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

        # Run evaluation‑only nodes not already executed by the model
        train_set = set(self.flow["train_order"])
        for nid in self.flow["eval_order"]:
            if nid in train_set:
                continue
            self.translators[nid].generate(w, "evaluation", "data")

        # Collect visualization data
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

    # ------------------------------------------------------------------
    #  MAIN
    # ------------------------------------------------------------------
    def _emit_main(self, w: CodeWriter):
        """Write the __main__ block."""
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

        if has_eval and self._eval_entry_matches():
            w.line("viz_data = evaluate(model, pre_data)")

        w.dedent()

    # ------------------------------------------------------------------
    #  HELPERS
    # ------------------------------------------------------------------
    def _sanitize(self, id_str: str) -> str:
        """Convert a graph ID into a valid Python variable name."""
        return re.sub(r"[^a-zA-Z0-9_]", "_", id_str)

    def _unpack_pre_data(self, w: CodeWriter):
        """Write lines that unpack pre_data into local variables."""
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

    def _get_first_model_node_id(self, phase: str) -> str | None:
        """Return the first node in the training order that belongs to the model subgraph."""
        model_nodes = set(self._get_model_nodes())
        order = self.flow.get("train_order", [])
        for nid in order:
            if nid in model_nodes:
                return nid
        return None

    def _get_feed_key(self, phase: str):
        """Return (source_node_id, variable_name) for the model input.

        For evaluation, prefers a source port that carries the evaluation
        phase to feed test data instead of training data.
        """
        PHASE_MAP = {"train": "training", "eval": "evaluation"}
        full_phase = PHASE_MAP[phase]
        nid = self._get_first_model_node_id(phase)
        if nid is None:
            return None, None
        node = self.graph.nodes[nid]

        # Prefer a source whose output port has the exact phase
        for port in node.inputs:
            for link in self.graph.links:
                if link.id_to == port.id:
                    src_port = self.graph.ports[link.id_from]
                    if full_phase in src_port.activation_phases:
                        src_node_id = src_port.node_id
                        var = self.var_map.get(src_port.id) or self.var_map.get(
                            src_node_id
                        )
                        if var:
                            return src_node_id, var

        # Fallback: any connected source
        for port in node.inputs:
            for link in self.graph.links:
                if link.id_to == port.id:
                    src_node_id = self.graph.ports[link.id_from].node_id
                    var = self.var_map.get(link.id_from) or self.var_map.get(
                        src_node_id
                    )
                    if var:
                        return src_node_id, var
        return None, None

    def _get_var_for_first_model_input(self, phase: str) -> str:
        """Return the variable name that feeds the first model node."""
        _, var = self._get_feed_key(phase)
        return var if var else "None"

    def _get_var_for_optimizer_labels(self) -> str:
        """Return the variable connected to the optimizer's label input."""
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

    def _get_var_for_eval_labels(self) -> str:
        """Return the test‑label variable connected to the output node."""
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

    def _get_loss_port_id(self) -> str | None:
        """Return the ID of the output port designated for loss computation."""
        output_node = next(
            (n for n in self.graph.nodes.values() if n.type == "output"), None
        )
        if output_node:
            for p in output_node.outputs:
                if p.role == "loss":
                    return p.id
        return None

    def _remove_extra_optimizers(self, graph):
        optimizer_nodes = [n for n in graph.nodes.values() if n.type == "optimizer"]
        if len(optimizer_nodes) <= 1:
            return graph

        keep_id = optimizer_nodes[0].id
        remove_ids = {n.id for n in optimizer_nodes[1:]}

        # Remove nodes
        graph.nodes = {
            nid: node for nid, node in graph.nodes.items() if nid not in remove_ids
        }

        # Remove their ports
        removed_ports = set()
        for n in optimizer_nodes[1:]:
            for p in n.inputs + n.outputs + n.paramInputs + n.paramOutputs:
                removed_ports.add(p.id)
        graph.ports = {
            pid: port for pid, port in graph.ports.items() if pid not in removed_ports
        }

        # Remove links involving removed ports
        graph.links = [
            l
            for l in graph.links
            if l.id_from not in removed_ports and l.id_to not in removed_ports
        ]

        return graph

    def _eval_entry_matches(self):
        """Return True if evaluation can reuse the trained model."""
        model_nodes = set(self._get_model_nodes())
        train_entry = None
        for nid in self.flow.get("train_order", []):
            if nid in model_nodes:
                train_entry = nid
                break
        eval_entry = None
        for nid in self.flow.get("eval_order", []):
            if nid in model_nodes:
                eval_entry = nid
                break
        if eval_entry is None:
            return True
        return train_entry == eval_entry
