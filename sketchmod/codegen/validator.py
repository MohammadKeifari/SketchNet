"""
Graph validation.

The validator draws one line: a graph either cannot be translated at all, or
it produces a script that runs.

* **Errors** mean the graph is not translatable -- a cycle, a missing
  connection, two inputs whose batch sizes cannot meet.  Code generation is
  blocked.
* **Warnings** mean the graph translates fine but describes something odd,
  such as a layer sitting in preprocessing where no optimizer can reach it.
  The message says what the generated code will actually do.

Every diagnostic carries a stable ``code`` so callers can match on it without
depending on the wording, plus ``nodeId`` / ``portId`` for canvas highlighting.
"""

import sympy

from .analysis import Analysis, MODEL_TYPES, PARAMETRIC_TYPES
from .graph import parse_graph
from .nodes import SUPPORTED_TYPES
from .phase_analyzer import analyze_phases

#: Minimum number of data inputs each node type needs to mean anything.
#: A node below its minimum has nothing to compute from, so the graph cannot
#: be translated into working code.
REQUIRED_INPUTS = {
    "neuron": 1,
    "layer": 1,
    "conv2d": 1,
    "dropout": 1,
    "batchnorm": 1,
    "flatten": 1,
    "column-select": 1,
    "row-select": 1,
    "dim-select": 1,
    "normalize": 1,
    "onehot": 1,
    "deonehot": 1,
    "train-test": 1,
    "reshape": 1,
    "add": 2,
    "concat": 2,
}


class GraphValidator:
    """Checks a graph before code generation."""

    def __init__(self, graph_data):
        self.graph = parse_graph(graph_data)
        self.flow = analyze_phases(self.graph)
        self.a = Analysis(self.graph, self.flow)
        self.errors = []
        self.warnings = []

    # ------------------------------------------------------------------
    def validate(self):
        self.errors = []
        self.warnings = []

        for check in (
            self._required_nodes,
            self._known_node_types,
            self._data_flow_cycles,
            self._param_cycles,
            self._required_connections,
            self._optimizer_wiring,
            self._batch_size_conflicts,
        ):
            check()

        for check in (
            self._missing_optimizer,
            self._multiple_optimizers,
            self._untrained_layers,
            self._visualization_in_training,
            self._unreachable_preprocessing,
            self._evaluation_entry_point,
            self._loss_label_agreement,
            self._accuracy_inputs,
            self._visualization_samples,
            self._reshape_feasibility,
            self._early_stopping_without_validation,
            self._input_data_source,
        ):
            check()

        return {
            "errors": self.errors,
            "warnings": self.warnings,
            "isValid": not self.errors,
        }

    # ------------------------------------------------------------------
    def _error(self, code, message, **where):
        self.errors.append({"code": code, "message": message, **where})

    def _warn(self, code, message, **where):
        self.warnings.append({"code": code, "message": message, **where})

    def _nodes_of(self, *types):
        return [n for n in self.graph.nodes.values() if n.type in types]

    @staticmethod
    def _shape_text(shape_info):
        if not shape_info or not shape_info.shape:
            return "unknown"
        return "(" + ", ".join(str(d) for d in shape_info.shape) + ")"

    def _has_cycle(self, param_links: bool) -> bool:
        adjacency = {nid: [] for nid in self.graph.nodes}
        for link in self.graph.links:
            source = self.graph.ports[link.id_from]
            target = self.graph.ports[link.id_to]
            is_param = source.port_kind == "param" and target.port_kind == "param"
            if is_param == param_links:
                adjacency[source.node_id].append(target.node_id)

        WHITE, GREY, BLACK = 0, 1, 2
        colour = {nid: WHITE for nid in self.graph.nodes}

        def visit(node_id):
            colour[node_id] = GREY
            for neighbour in adjacency[node_id]:
                if colour[neighbour] == GREY:
                    return True
                if colour[neighbour] == WHITE and visit(neighbour):
                    return True
            colour[node_id] = BLACK
            return False

        return any(
            colour[nid] == WHITE and visit(nid) for nid in list(self.graph.nodes)
        )

    # ==================================================================
    #  Errors: the graph cannot be translated
    # ==================================================================
    def _required_nodes(self):
        if not self._nodes_of("input-data"):
            self._error(
                "missing-input",
                "Missing Input Data node: there is no data to run through the graph.",
                nodeId=None,
            )
        if self._nodes_of("output"):
            return
        # Without an optimizer the graph is still a valid preprocessing and
        # plotting pipeline; only training genuinely needs somewhere to read
        # the loss from.
        if self._nodes_of("optimizer"):
            self._error(
                "missing-output",
                "Missing Output node: the optimizer has no model output to "
                "compute a loss from.",
                nodeId=None,
            )
        else:
            self._warn(
                "missing-output",
                "Missing Output node - the script will preprocess and visualize "
                "data, but define no model.",
                nodeId=None,
            )

    def _known_node_types(self):
        for node in self.graph.nodes.values():
            if node.type not in SUPPORTED_TYPES:
                self._error(
                    "unknown-node-type",
                    f"Node '{node.id}' has unsupported type '{node.type}'.",
                    nodeId=node.id,
                )

    def _data_flow_cycles(self):
        if self._has_cycle(param_links=False):
            self._error(
                "data-flow-cycle",
                "Data-flow cycle detected - the graph is not a DAG, "
                "so there is no order in which the nodes can run.",
                nodeId=None,
            )

    def _param_cycles(self):
        if self._has_cycle(param_links=True):
            self._error(
                "param-cycle",
                "Param-port cycle detected - the shared parameters depend on "
                "each other, so none of them can be computed first.",
                nodeId=None,
            )

    def _required_connections(self):
        for node in self.graph.nodes.values():
            needed = REQUIRED_INPUTS.get(node.type)
            if needed is None:
                continue
            # Count links, not ports: several tensors may arrive on one port.
            arriving = sum(len(self.a.links_into(port.id)) for port in node.inputs)
            if node.type == "add" and arriving != needed:
                self._error(
                    "missing-input-connection",
                    f"Add node '{node.id}' requires exactly {needed} inputs, "
                    f"found {arriving}.",
                    nodeId=node.id,
                )
            elif node.type == "concat" and arriving < needed:
                self._error(
                    "missing-input-connection",
                    f"Concat node '{node.id}' requires at least {needed} inputs, "
                    f"found {arriving}.",
                    nodeId=node.id,
                )
            elif node.type not in ("add", "concat") and arriving < needed:
                self._error(
                    "missing-input-connection",
                    f"'{node.type}' ({node.id}) requires at least "
                    f"{needed} input connection.",
                    nodeId=node.id,
                )

    def _optimizer_wiring(self):
        for node in self._nodes_of("optimizer"):
            if node.id not in self.flow["train_set"]:
                self._error(
                    "optimizer-not-training",
                    f"Optimizer '{node.id}' is not reached by the training phase, "
                    "so no training loop can be generated.",
                    nodeId=node.id,
                )
                return

        optimizer = self.a.optimizer
        if optimizer is None:
            return

        # An Output node with nothing feeding it is only a problem once
        # something wants to train against it.
        output = self.a.output_node
        if output is not None and not self.a.connected_inputs(output):
            self._error(
                "missing-input-connection",
                f"Output node '{output.id}' has no input connected, so the "
                "optimizer has no predictions to compute a loss from.",
                nodeId=output.id,
            )

        if len(optimizer.inputs) < 2 or not self.a.first_source(optimizer.inputs[1]):
            self._error(
                "optimizer-missing-labels",
                f"Optimizer '{optimizer.id}' has no labels connected, "
                "so there is nothing to compute a loss against.",
                nodeId=optimizer.id,
            )
        if optimizer.inputs and not self.a.first_source(optimizer.inputs[0]):
            self._error(
                "optimizer-missing-loss",
                f"Optimizer '{optimizer.id}' has no loss input connected.",
                nodeId=optimizer.id,
            )
        model_nodes = self.a.model_nodes()
        trainable = [
            nid
            for nid in model_nodes
            if self.graph.nodes[nid].type in PARAMETRIC_TYPES
        ]
        if not trainable:
            self._error(
                "no-trainable-parameters",
                f"Optimizer '{optimizer.id}' reaches no layer with weights, so "
                "there is nothing for it to optimize. Add a Layer, Neuron, "
                "Conv2D or BatchNorm between the data and the Output node.",
                nodeId=optimizer.id,
            )

        model_ids = set(model_nodes)
        reaches_model = any(
            source.node_id not in model_ids
            for nid in model_nodes
            for port in self.graph.nodes[nid].inputs
            if port.port_kind != "param"
            for source in self.a.active_sources(port, "training")
        )
        if model_nodes and not reaches_model:
            self._error(
                "model-input-missing",
                "No data reaches the model during training - every input to the "
                "model comes from inside the model itself.",
                nodeId=model_nodes[0],
            )

    def _batch_size_conflicts(self):
        """Two inputs that meet inside one layer during the same phase must agree."""
        for node in self.graph.nodes.values():
            if node.type not in PARAMETRIC_TYPES:
                continue
            arriving = []
            for port in node.inputs:
                for source in self.a.sources(port):
                    shared = set(port.activation_phases) & set(source.activation_phases)
                    if shared and source.shape and source.shape.shape:
                        arriving.append((source.shape, shared))

            for index, (shape, phases) in enumerate(arriving):
                for other_shape, other_phases in arriving[index + 1 :]:
                    if not (phases & other_phases):
                        continue
                    if str(shape.shape[0]) == str(other_shape.shape[0]):
                        continue
                    self._error(
                        "batch-size-mismatch",
                        f"Model node '{node.id}' has multiple inputs with different "
                        f"batch sizes ({shape.shape[0]} vs {other_shape.shape[0]}) "
                        f"that are active in the same phase(s): "
                        f"{phases & other_phases}. Batch sizes must match when "
                        "feeding into the same model node.",
                        nodeId=node.id,
                    )
                    return

    # ==================================================================
    #  Warnings: translatable, but probably not what you meant
    # ==================================================================
    def _missing_optimizer(self):
        if not self._nodes_of("optimizer"):
            self._warn(
                "no-optimizer",
                "No optimizer node - the script will load and transform data "
                "but never train.",
                nodeId=None,
            )

    def _multiple_optimizers(self):
        optimizers = self._nodes_of("optimizer")
        if len(optimizers) > 1:
            self._warn(
                "multiple-optimizers",
                f"Graph contains {len(optimizers)} optimizer nodes. "
                "Only the first one will be used.",
                nodeId=None,
            )

    def _untrained_layers(self):
        """A layer the optimizer cannot reach stays randomly initialized."""
        trained = set(self.a.model_nodes())
        for phase, key in (("preprocessing", "preprocessing_set"), ("evaluation", "eval_set")):
            for nid in sorted(self.flow.get(key, set())):
                node = self.graph.nodes[nid]
                if node.type not in MODEL_TYPES or nid in trained:
                    continue
                if phase == "evaluation" and nid in self.flow.get("preprocessing_set", set()):
                    continue
                self._warn(
                    "untrained-layer",
                    f"{node.type.capitalize()} '{nid}' runs in {phase}, so it is "
                    "applied untrained: its weights stay randomly initialized and "
                    "it will scramble the data rather than learn from it.",
                    nodeId=nid,
                )

    def _visualization_in_training(self):
        for nid in sorted(self.flow.get("train_set", set())):
            if self.graph.nodes[nid].type == "visualization":
                self._warn(
                    "visualization-in-training",
                    f"Visualization '{nid}' is in the training phase and will be "
                    "skipped - it would redraw on every batch.",
                    nodeId=nid,
                )

    def _unreachable_preprocessing(self):
        if self.flow.get("preprocessing_set") and not (
            self.flow.get("train_set") or self.flow.get("eval_set")
        ):
            self._warn(
                "preprocessing-dead-end",
                "Preprocessing does not reach training or evaluation - "
                "only data loading will be generated.",
                nodeId=None,
            )

    def _evaluation_entry_point(self):
        if self.a.evaluation_reuses_model():
            return
        self._warn(
            "evaluation-entry-mismatch",
            f"Evaluation enters the model at '{self.a.model_entry('evaluation')}', "
            f"but the model starts at '{self.a.model_entry('training')}'. "
            "Evaluation will be skipped because it cannot reuse the trained model.",
            nodeId=self.a.model_entry("evaluation"),
        )

    def _label_port(self):
        optimizer = self.a.optimizer
        if not optimizer or len(optimizer.inputs) < 2:
            return None, None
        port = optimizer.inputs[1]
        return port, self.a.first_source(port)

    def _loss_label_agreement(self):
        optimizer = self.a.optimizer
        port, source = self._label_port()
        if source is None:
            return
        loss_type = optimizer.properties.get("lossType", "mse")
        origin = self.graph.nodes[source.node_id]

        if origin.type == "onehot" and loss_type == "cross_entropy":
            self._warn(
                "label-loss-mismatch",
                "CrossEntropyLoss expects class indices, but labels come from a "
                "OneHot node. They will be argmax-ed back to indices.",
                portId=port.id,
            )
        elif origin.type != "onehot" and loss_type == "bce":
            self._warn(
                "label-loss-mismatch",
                "BCEWithLogitsLoss expects one-hot labels, but labels appear to "
                "be class indices.",
                portId=port.id,
            )

        if loss_type not in ("cross_entropy", "nll"):
            return
        shape = source.shape
        if shape is None or not shape.shape:
            self._warn(
                "label-shape-unknown",
                f"Optimizer '{optimizer.id}' uses {loss_type} loss, but the label "
                "shape cannot be determined. Model might not work.",
                nodeId=optimizer.id,
            )
            return
        if len(shape.shape) == 2 and Analysis.dim(source, -1) == 1:
            self._warn(
                "label-shape-squeezed",
                f"Optimizer '{optimizer.id}' uses {loss_type} loss. Label shape is "
                f"{self._shape_text(shape)} - will be automatically squeezed to (N).",
                nodeId=optimizer.id,
            )
        elif len(shape.shape) > 2:
            self._warn(
                "label-shape-unknown",
                f"Optimizer '{optimizer.id}' uses {loss_type} loss, but the label "
                f"shape is {self._shape_text(shape)}. Model might not work.",
                nodeId=optimizer.id,
            )

    def _accuracy_inputs(self):
        for node in self._nodes_of("accuracy"):
            if len(self.a.connected_inputs(node)) < 2:
                self._warn(
                    "accuracy-missing-input",
                    f"Accuracy node '{node.id}' expects 2 inputs "
                    "(predictions, labels).",
                    nodeId=node.id,
                )
                continue

            label_port = node.inputs[1] if len(node.inputs) >= 2 else None
            source = self.a.first_source(label_port) if label_port else None
            if source is None or Analysis.rank(source) != 2:
                continue
            width = Analysis.dim(source, -1)
            if width is not None and width > 1:
                self._warn(
                    "accuracy-label-reshape",
                    f"Accuracy label input port '{label_port.id}' appears to be "
                    f"one-hot encoded (shape {self._shape_text(source.shape)}). "
                    "It will be argmax-ed automatically.",
                    portId=label_port.id,
                )
            elif width == 1:
                self._warn(
                    "accuracy-label-reshape",
                    f"Accuracy label input port '{label_port.id}' has shape (N,1) - "
                    "automatically squeezed to (N).",
                    portId=label_port.id,
                )

    def _visualization_samples(self):
        for node in self._nodes_of("visualization"):
            lengths = []
            for port in node.inputs:
                if port.sub_type != "coord":
                    continue
                source = self.a.first_source(port)
                if source and source.shape and source.shape.shape:
                    lengths.append((port.id, source.shape.shape[0]))
            if len(lengths) < 2:
                continue
            first_id, first = lengths[0]
            for other_id, other in lengths[1:]:
                if str(first) != str(other):
                    self._warn(
                        "visualization-sample-mismatch",
                        f"Visualization '{node.id}' ports {first_id} and {other_id} "
                        f"have different sample sizes ({first} vs {other}).",
                        nodeId=node.id,
                    )
                    break

    def _reshape_feasibility(self):
        for node in self._nodes_of("reshape"):
            source = next(
                (s for port in node.inputs for s in self.a.sources(port)), None
            )
            if source is None or not source.shape or not source.shape.shape:
                continue

            target = str(node.properties.get("targetShape", ""))
            parts = [p.strip() for p in target.strip("()").split(",") if p.strip()]
            if not parts:
                continue

            if parts.count("-1") > 1:
                self._warn(
                    "reshape-ambiguous",
                    f"Reshape node '{node.id}' has multiple -1 dimensions - "
                    "PyTorch can only infer one.",
                    nodeId=node.id,
                )
                continue

            # Symbolic names are read off the input at runtime, so only the
            # concrete part of the target constrains the element count.
            fixed = sympy.Integer(1)
            symbolic = False
            for part in parts:
                if part == "-1":
                    continue
                try:
                    fixed *= int(part)
                except ValueError:
                    symbolic = True

            total = sympy.Integer(1)
            for dimension in source.shape.shape:
                total *= dimension._value
            if not total.is_Integer or not fixed.is_Integer:
                continue

            inferred = symbolic or "-1" in parts
            if not inferred:
                if total != fixed:
                    self._warn(
                        "reshape-infeasible",
                        f"Reshape node '{node.id}' total elements mismatch "
                        f"({total} vs {fixed}).",
                        nodeId=node.id,
                    )
            elif fixed != 0 and total % fixed != 0:
                self._warn(
                    "reshape-infeasible",
                    f"Reshape node '{node.id}' cannot infer dimension - "
                    f"{total} is not divisible by {fixed}.",
                    nodeId=node.id,
                )

    def _early_stopping_without_validation(self):
        optimizer = self.a.optimizer
        if not optimizer:
            return
        properties = optimizer.properties
        if (
            properties.get("earlyStopping")
            and properties.get("validationMode", "none") == "none"
        ):
            self._warn(
                "early-stopping-without-validation",
                "Early stopping is enabled but validation mode is 'none' - "
                "there is no metric to stop on, so it will have no effect.",
                nodeId=optimizer.id,
            )

    def _input_data_source(self):
        for node in self._nodes_of("input-data"):
            shape = node.properties.get("dataShape")
            if not node.properties.get("datasetId") and not shape:
                self._warn(
                    "missing-dataset",
                    f"InputData node '{node.id}' has no dataset attached and no "
                    "shape defined. The generated code will use random data.",
                    nodeId=node.id,
                )
            elif shape and ("None" in str(shape) or "?" in str(shape)):
                self._warn(
                    "unclear-data-shape",
                    f"InputData node '{node.id}' has an unclear shape '{shape}'. "
                    "Symbolic dimensions will be replaced with placeholder values.",
                    nodeId=node.id,
                )
