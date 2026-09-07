"""
Execution plan for a SketchNet graph.

This module turns a graph plus its phase analysis into a fully resolved
description of the script to write: which statement goes in which function,
what every variable is called, and which tensor reaches ``forward`` in each
phase.  By the time a :class:`Plan` exists, no decision is left to runtime --
that is what removes the dictionary lookups and ``None`` guards the old
generator had to emit.
"""

import re
from dataclasses import dataclass, field

from .analysis import Analysis, remove_extra_optimizers
from .graph import parse_graph
from .naming import Names, snake
from .nodes import NodeCtx, emitter_for, loss_expression
from .phase_analyzer import analyze_phases

_REFERENCE = re.compile(r"^[A-Za-z_]\w*(\.[A-Za-z_]\w*)*$")

# Identifiers the train/eval bodies write themselves, so no node may take them.
_TRAIN_RESERVED = (
    "criterion",
    "optimizer",
    "loader",
    "epoch",
    "total_loss",
    "loss",
    "out",
    "metric",
    "best_metric",
    "stale_epochs",
    "val_size",
    "val_order",
    "val_x",
    "val_y",
    "val_out",
    "val_loss",
    "val_acc",
)
_EVAL_RESERVED = ("out",)


def _is_reference(expr) -> bool:
    """True when an expression is a bare name we can pass around as-is."""
    return bool(expr) and bool(_REFERENCE.match(expr))


# ======================================================================
#  Plan pieces
# ======================================================================
@dataclass
class ModelInput:
    """One ``forward()`` parameter, with the tensor each phase supplies.

    Sources that share a phase are concatenated into a single tensor by the
    caller; sources on different phases are the same logical input seen from
    two phases, so they share one parameter and differ only at the call site.
    """

    param: str
    train_sources: list = field(default_factory=list)
    eval_sources: list = field(default_factory=list)
    train_expr: str = None
    eval_expr: str = None


@dataclass
class Validation:
    split: float
    metric: str
    prediction: str
    early_stopping: bool
    patience: int


@dataclass
class TrainPlan:
    setup: list = field(default_factory=list)
    feature_tensors: list = field(default_factory=list)
    labels: str = "labels"
    loop_vars: list = field(default_factory=list)
    loss_field: str = "loss"
    gradient_clip: object = None
    body: list = field(default_factory=list)
    validation: Validation = None


@dataclass
class EvalPlan:
    call_args: list = field(default_factory=list)
    body: list = field(default_factory=list)
    uses_model: bool = True


@dataclass
class Plan:
    constants: list = field(default_factory=list)
    load_lines: list = field(default_factory=list)
    data_fields: list = field(default_factory=list)
    submodules: list = field(default_factory=list)
    forward_params: list = field(default_factory=list)
    forward_lines: list = field(default_factory=list)
    output_fields: list = field(default_factory=list)
    train: TrainPlan = None
    evaluation: EvalPlan = None
    needs_pandas: bool = False
    needs_pyplot: bool = False
    skip_reason: str = None


# ======================================================================
#  Value scopes
# ======================================================================
class DataExports:
    """Fields of the ``Data`` NamedTuple, created the first time they are used.

    Only values that a later function actually reads become fields, so
    ``load_data`` returns exactly what is live and nothing more.
    """

    def __init__(self):
        self.fields = []
        self._by_expr = {}
        self._names = Names()

    def reference(self, local_expr: str) -> str:
        if local_expr not in self._by_expr:
            stem = local_expr if _is_reference(local_expr) else "value"
            name = self._names.fresh(stem)
            self.fields.append((name, local_expr))
            self._by_expr[local_expr] = name
        return f"data.{self._by_expr[local_expr]}"


class Scope:
    """Expressions for graph values inside one function body."""

    def __init__(self, names: Names, parent=None, importer=None):
        self.names = names
        self.parent = parent
        self.importer = importer
        self.lines = []
        self._values = {}
        self._params = {}

    def value(self, port_id):
        if port_id in self._values:
            return self._values[port_id]
        if self.parent is not None:
            inherited = self.parent.value(port_id)
            if inherited is not None:
                return self.importer(inherited) if self.importer else inherited
        return None

    def params(self, port_id):
        if port_id in self._params:
            return self._params[port_id]
        if self.parent is not None:
            inherited = self.parent.params(port_id)
            if inherited:
                if self.importer:
                    return [self.importer(part) for part in inherited]
                return inherited
        return None

    def set_value(self, port_id, expr):
        self._values[port_id] = expr

    def set_params(self, port_id, exprs):
        self._params[port_id] = list(exprs)

    def bind(self, port, node, expr):
        """Give ``expr`` a name and record it, unless it is already a name."""
        if _is_reference(expr):
            self._values[port.id] = expr
            return expr
        name = self.names.bind(port.id, _preferred_name(port, node))
        self.lines.append(f"{name} = {expr}")
        self._values[port.id] = name
        return name


def _preferred_name(port, node) -> str:
    """Variable name for a port: the node id, disambiguated when it has several."""
    stem = emitter_for(node).value_name or snake(node.id)
    if len(node.outputs) <= 1:
        return stem
    suffix = port.sub_type or port.role or f"out{port.index}"
    return f"{stem}_{suffix}"


# ======================================================================
#  Builder
# ======================================================================
class PlanBuilder:
    def __init__(self, graph_data: dict):
        self.graph = remove_extra_optimizers(parse_graph(graph_data))
        self.flow = None
        self.plan = Plan()

    def build(self) -> Plan:
        self.flow = analyze_phases(self.graph)
        self.a = Analysis(self.graph, self.flow)

        self.pre_set = set(self.flow.get("preprocessing_set", set()))
        self.train_set = set(self.flow.get("train_set", set()))
        self.eval_set = set(self.flow.get("eval_set", set()))
        self.model_ids = set(self.a.model_nodes())
        self.optimizer = self.a.optimizer
        self.output_node = self.a.output_node
        self.output_field = {}
        self.bindings = {}
        self.model_inputs = []
        self.model_phase = "training" if self.train_set else "evaluation"

        self.exports = DataExports()
        self.load = Scope(Names())

        self._build_load()
        self._bind_model_inputs()
        self._build_model()
        self._build_train()
        self._build_evaluate()
        self._finish()
        return self.plan

    # ------------------------------------------------------------------
    #  Shared node emission
    # ------------------------------------------------------------------
    def _phase_sources(self, port, phase):
        active = self.a.active_sources(port, phase)
        return active if active else self.a.sources(port)

    def _context(self, node, phase, scope, resolve, in_model=False, attr=None):
        by_port, inputs, sources, source_ports = [], [], [], []
        for port in node.inputs:
            if port.port_kind == "param":
                by_port.append(None)
                continue
            parts, ports = resolve(port)
            if not parts:
                by_port.append(None)
                continue
            merged = (
                parts[0]
                if len(parts) == 1
                else f"torch.cat([{', '.join(parts)}], dim=1)"
            )
            by_port.append(merged)
            inputs.append(merged)
            sources.extend(parts)
            source_ports.extend(ports)

        param_sources = [self.a.first_source(p) for p in node.paramInputs]

        def resolve_param(index):
            source = param_sources[index] if index < len(param_sources) else None
            return scope.params(source.id) if source else None

        return NodeCtx(
            node=node,
            analysis=self.a,
            phase=phase,
            inputs=inputs,
            sources=sources,
            source_ports=source_ports,
            resolve_param=resolve_param,
            by_port=by_port,
            in_model=in_model,
            attr=attr,
            names=scope.names,
        )

    def _resolve_from_scope(self, scope, phase):
        def resolve(port):
            parts, ports = [], []
            for source in self._phase_sources(port, phase):
                expr = scope.value(source.id)
                if expr is None:
                    continue
                parts.append(expr)
                ports.append(source)
            return parts, ports

        return resolve

    @staticmethod
    def _expects_input(node) -> bool:
        return any(port.port_kind != "param" for port in node.inputs)

    def _emit(self, node, phase, scope, resolve, in_model=False, attr=None):
        """Run one node's emitter and record its values in ``scope``."""
        emitter = emitter_for(node)
        ctx = self._context(node, phase, scope, resolve, in_model, attr)

        # A node whose inputs never arrived computes nothing; emitting it would
        # only produce expressions over `None`. The validator reports the cause.
        if self._expects_input(node) and not ctx.inputs:
            return ctx

        prelude = emitter.prelude(ctx)
        param_values = emitter.param_expressions(ctx)
        values = emitter.expressions(ctx)
        statements = emitter.statements(ctx)

        scope.lines.extend(prelude)
        for port, exprs in zip(node.paramOutputs, param_values):
            if exprs:
                scope.set_params(port.id, exprs)
        for port, expr in zip(node.outputs, values):
            if expr is not None:
                scope.bind(port, node, expr)
        scope.lines.extend(statements)

        if node.type == "visualization" and statements:
            self.plan.needs_pyplot = True
        if node.type == "input-data" and prelude:
            self.plan.needs_pandas = True
        return ctx

    # ------------------------------------------------------------------
    #  load_data
    # ------------------------------------------------------------------
    def _build_load(self):
        resolve = self._resolve_from_scope(self.load, "preprocessing")
        for nid in self.flow.get("preprocessing_order", []):
            node = self.graph.nodes[nid]
            if node.type == "optimizer":
                continue
            self._emit(node, "preprocessing", self.load, resolve)
        self.plan.load_lines = self.load.lines

    # ------------------------------------------------------------------
    #  forward() parameters
    # ------------------------------------------------------------------
    def _external_sources(self, port, phase):
        return [
            source
            for source in self.a.active_sources(port, phase)
            if source.node_id not in self.model_ids
        ]

    def _bind_model_inputs(self):
        """Group every model entry port into the smallest set of parameters.

        The signature is defined by the phase the model is built for.  A port
        that only evaluation reaches is not an entry point -- it means
        evaluation enters the model somewhere else, which the validator
        reports and which makes the trained weights unusable.
        """
        by_key = {}
        primary = self.model_phase
        for nid in self.a.model_nodes():
            node = self.graph.nodes[nid]
            for port in node.inputs:
                if port.port_kind == "param":
                    continue
                train_sources = self._external_sources(port, "training")
                eval_sources = self._external_sources(port, "evaluation")
                anchor = train_sources if primary == "training" else eval_sources
                if not anchor:
                    continue
                key = (
                    tuple(s.id for s in train_sources),
                    tuple(s.id for s in eval_sources),
                )
                if key not in by_key:
                    by_key[key] = ModelInput(
                        param="",
                        train_sources=train_sources,
                        eval_sources=eval_sources,
                    )
                self.bindings[port.id] = by_key[key]

        self.model_inputs = list(by_key.values())
        names = Names()
        single = len(self.model_inputs) == 1
        for binding in self.model_inputs:
            origin = binding.train_sources or binding.eval_sources
            stem = "x" if single else f"x_{snake(origin[0].node_id)}"
            binding.param = names.fresh(stem)

    # ------------------------------------------------------------------
    #  Model class
    # ------------------------------------------------------------------
    def _resolve_forward(self, scope):
        def resolve(port):
            parts, ports = [], []
            used_param = False
            for source in self._phase_sources(port, self.model_phase):
                if source.node_id in self.model_ids:
                    expr = scope.value(source.id)
                    if expr is not None:
                        parts.append(expr)
                        ports.append(source)
                    continue
                binding = self.bindings.get(port.id)
                if binding is None:
                    continue
                ports.append(source)
                if not used_param:
                    parts.append(binding.param)
                    used_param = True
            return parts, ports

        return resolve

    def _build_model(self):
        model_nodes = self.a.model_nodes()
        if not model_nodes or self.optimizer is None:
            if self.optimizer is None:
                self.plan.skip_reason = "no optimizer node, so there is nothing to train"
            elif not model_nodes:
                self.plan.skip_reason = "no model layers reach the output node"
            return

        attrs = Names()
        scope = Scope(Names(reserved=[b.param for b in self.model_inputs]))
        resolve = self._resolve_forward(scope)

        for nid in model_nodes:
            node = self.graph.nodes[nid]
            if node.type == "output":
                self._build_output(node, scope, resolve)
                continue
            attr = attrs.fresh(snake(node.id))
            ctx = self._emit(node, self.model_phase, scope, resolve, True, attr)
            self.plan.submodules.extend(emitter_for(node).submodules(ctx))

        if not self.plan.output_fields:
            self.plan.skip_reason = "the Output node has nothing connected to it"
            self.plan.submodules = []
            return

        self.plan.forward_params = [b.param for b in self.model_inputs]
        self.plan.forward_lines = scope.lines

    def _build_output(self, node, scope, resolve):
        ctx = self._context(node, self.model_phase, scope, resolve, in_model=True)
        if not ctx.inputs:
            return
        values = emitter_for(node).expressions(ctx)
        fields = Names()
        for port, expr in zip(node.outputs, values):
            name = fields.fresh(port.role or f"out{port.index}")
            self.output_field[port.id] = name
            self.plan.output_fields.append((name, expr))

    # ------------------------------------------------------------------
    #  train()
    # ------------------------------------------------------------------
    def _depends_on_model(self):
        """Nodes whose value is only available once the model has run."""
        dependent = set()
        for nid in self.flow.get("train_order", []):
            node = self.graph.nodes[nid]
            for port in node.inputs:
                for source in self.a.sources(port):
                    if source.node_id in self.model_ids or source.node_id in dependent:
                        dependent.add(nid)
                        break
                if nid in dependent:
                    break
        return dependent

    def _model_scope(self, reserved):
        """A scope over ``data`` plus the model's outputs."""
        scope = Scope(
            Names(reserved=reserved),
            parent=self.load,
            importer=self.exports.reference,
        )
        for port_id, field_name in self.output_field.items():
            scope.set_value(port_id, f"out.{field_name}")
        return scope

    def _build_train(self):
        if self.plan.skip_reason:
            return

        train = TrainPlan()
        scope = self._model_scope(_TRAIN_RESERVED)
        resolve = self._resolve_from_scope(scope, "training")

        # Claim the names this function writes itself before nodes take them.
        single = len(self.model_inputs) == 1
        feature_names = [
            scope.names.fresh("features" if single else f"features_{b.param}")
            for b in self.model_inputs
        ]
        labels_name = scope.names.fresh("labels")

        dependent = self._depends_on_model()
        extras = [
            nid
            for nid in self.flow.get("train_order", [])
            if nid not in self.model_ids
            and nid not in self.pre_set
            and self.graph.nodes[nid].type not in ("optimizer", "visualization")
        ]

        # Everything the model does not depend on runs once, before the loop.
        for nid in extras:
            if nid not in dependent:
                self._emit(self.graph.nodes[nid], "training", scope, resolve)

        for binding in self.model_inputs:
            binding.train_expr = self._phase_expression(scope, binding.train_sources)

        train.setup = list(scope.lines)
        scope.lines = []

        for name, binding in zip(feature_names, self.model_inputs):
            if binding.train_expr is None:
                continue
            scope.lines.append(f"{name} = {binding.train_expr}")
            train.feature_tensors.append(name)
            train.loop_vars.append(binding.param)

        if not train.feature_tensors:
            self.plan.skip_reason = "no data reaches the model during training"
            return

        labels = self._label_expression(scope)
        if labels is None:
            self.plan.skip_reason = "the optimizer has no labels connected"
            return
        train.labels = labels_name
        scope.lines.append(f"{labels_name} = {labels}")

        props = self.optimizer.properties
        scope.lines.append(
            f"criterion = {loss_expression(props.get('lossType', 'mse'))}"
        )
        scope.lines.append(f"optimizer = {_optimizer_expression(props)}")
        train.setup.extend(scope.lines)
        scope.lines = []

        loss_port = self.a.loss_port()
        train.loss_field = (
            self.output_field.get(loss_port.id) if loss_port else None
        ) or (self.plan.output_fields[0][0] if self.plan.output_fields else "loss")

        # The rest reads the model's outputs, so it belongs inside the loop.
        for nid in extras:
            if nid in dependent:
                self._emit(self.graph.nodes[nid], "training", scope, resolve)
        train.body = scope.lines

        train.gradient_clip = props.get("gradientClip")
        train.validation = self._validation_spec()
        self.plan.train = train

    def _phase_expression(self, scope, sources):
        """The single tensor a phase supplies for one forward parameter."""
        parts = [
            expr
            for expr in (scope.value(source.id) for source in sources)
            if expr is not None
        ]
        if not parts:
            return None
        if len(parts) == 1:
            return parts[0]
        return f"torch.cat([{', '.join(parts)}], dim=1)"

    def _label_port(self):
        if not self.optimizer or len(self.optimizer.inputs) < 2:
            return None
        return self.a.first_source(self.optimizer.inputs[1])

    def _label_expression(self, scope):
        """The optimizer's target tensor, cast to what the loss function needs."""
        port = self._label_port()
        expression = scope.value(port.id) if port else None
        if expression is None:
            return None
        loss_type = self.optimizer.properties.get("lossType", "mse")
        if loss_type in ("cross_entropy", "nll"):
            expression += _class_index_suffix(port)
        return expression

    def _validation_spec(self):
        props = self.optimizer.properties
        if props.get("validationMode", "none") != "split":
            return None
        metric = props.get("validationMetric", "loss")
        prediction = self._validation_prediction() if metric == "accuracy" else None
        return Validation(
            split=props.get("validationSplit", 0.2),
            metric=metric,
            prediction=prediction,
            early_stopping=bool(props.get("earlyStopping")),
            patience=props.get("earlyStoppingPatience", 10),
        )

    def _validation_prediction(self):
        """Expression giving predicted class indices from a validation batch."""
        node = self.output_node
        port = None
        if node:
            port = next((p for p in node.outputs if p.role == "prediction"), None)
        if port is None:
            return "val_out." + (self.plan.output_fields[0][0] if self.plan.output_fields else "loss")
        expression = f"val_out.{self.output_field.get(port.id, 'prediction')}"
        if Analysis.rank(port) == 1:
            return expression
        return f"{expression}.argmax(dim=1)"

    # ------------------------------------------------------------------
    #  evaluate()
    # ------------------------------------------------------------------
    def _build_evaluate(self):
        eval_order = self.flow.get("eval_order", [])
        if not eval_order:
            return
        if self.plan.train is not None and not self.a.evaluation_reuses_model():
            return

        uses_model = self.plan.train is not None
        plan = EvalPlan(uses_model=uses_model)
        scope = self._model_scope(_EVAL_RESERVED)
        resolve = self._resolve_from_scope(scope, "evaluation")

        if uses_model:
            for binding in self.model_inputs:
                binding.eval_expr = self._phase_expression(scope, binding.eval_sources)
                argument = binding.eval_expr or binding.train_expr
                if argument:
                    plan.call_args.append(f"{argument}.to(DEVICE)")

        for nid in eval_order:
            node = self.graph.nodes[nid]
            # Values from earlier phases arrive through `data`; never recompute them.
            if nid in self.pre_set or nid in self.model_ids:
                continue
            if uses_model and nid in self.train_set:
                continue
            if node.type == "optimizer":
                continue
            if not uses_model and self._reads_model_output(node):
                continue
            self._emit(node, "evaluation", scope, resolve)

        plan.body = scope.lines
        if plan.body or plan.call_args:
            self.plan.evaluation = plan

    def _reads_model_output(self, node):
        return any(
            source.node_id in self.model_ids
            for port in node.inputs
            for source in self.a.sources(port)
        )

    # ------------------------------------------------------------------
    #  Finishing touches
    # ------------------------------------------------------------------
    def _finish(self):
        self.plan.data_fields = self.exports.fields
        if self.optimizer is not None and self.plan.train is not None:
            props = self.optimizer.properties
            self.plan.constants = [
                ("EPOCHS", props.get("epochs", 10)),
                ("BATCH_SIZE", props.get("batchSize", 32)),
                ("SHUFFLE", bool(props.get("shuffle", True))),
            ]
            validation = self.plan.train.validation
            if validation and validation.early_stopping:
                self.plan.constants.append(("PATIENCE", validation.patience))


# ======================================================================
#  Small helpers
# ======================================================================
def _class_index_suffix(port) -> str:
    """How to turn a label tensor into the class indices CrossEntropy wants."""
    rank = Analysis.rank(port)
    width = Analysis.dim(port, -1)
    if rank == 1 or rank is None:
        return ".long()"
    if width == 1:
        return ".squeeze(-1).long()"
    if width and width > 1:
        return ".argmax(dim=1)"
    return ".long()"


def _optimizer_expression(props: dict) -> str:
    """Build the optimizer call, listing only settings that differ from torch's."""
    kind = props.get("optimizerType", "adam")
    arguments = ["model.parameters()", f"lr={props.get('learningRate', 0.001)}"]

    def add(name, value, default):
        if value != default:
            arguments.append(f"{name}={value}")

    if kind in ("adam", "adamw"):
        beta1 = props.get("adamBeta1", 0.9)
        beta2 = props.get("adamBeta2", 0.999)
        if (beta1, beta2) != (0.9, 0.999):
            arguments.append(f"betas=({beta1}, {beta2})")
        add("eps", props.get("adamEpsilon", 1e-8), 1e-8)
        add("weight_decay", props.get("weightDecay", 0), 0)
        name = "Adam" if kind == "adam" else "AdamW"
        return f"optim.{name}({', '.join(arguments)})"

    if kind == "sgd":
        add("momentum", props.get("sgdMomentum", 0.9), 0)
        add("weight_decay", props.get("weightDecay", 0), 0)
        if props.get("nesterov", False):
            arguments.append("nesterov=True")
        return f"optim.SGD({', '.join(arguments)})"

    if kind == "rmsprop":
        add("weight_decay", props.get("weightDecay", 0), 0)
        return f"optim.RMSprop({', '.join(arguments)})"

    return f"optim.Adam({', '.join(arguments)})"


def build_plan(graph_data: dict) -> Plan:
    return PlanBuilder(graph_data).build()
