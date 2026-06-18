"""
Translators for SketchNet nodes → PyTorch code.
Single entry point: generate(w, phase, placement, is_first=False)
"""

import re
from .graph import Graph, Node
from .writer import CodeWriter


def _sanitize(id_str: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "_", id_str)


# ============================================================
#  BASE
# ============================================================
class BaseTranslator:
    node_type = None

    def __init__(self, node: Node, graph: Graph, var_map: dict):
        self.node = node
        self.graph = graph
        self.var_map = var_map

    def generate(
        self, w: CodeWriter, phase: str, placement: str, is_first: bool = False
    ):
        pass

    def _in_var(self):
        for port in self.node.inputs + self.node.paramInputs:
            for link in self.graph.links:
                if link.id_to == port.id:
                    src_id = link.id_from
                    if src_id in self.var_map:
                        return self.var_map[src_id]
                    src_nid = self.graph.ports[src_id].node_id
                    if src_nid in self.var_map:
                        return self.var_map[src_nid]
        return "None"

    def _store_output(self, var_name: str):
        self.var_map[self.node.id] = var_name
        if self.node.outputs:
            self.var_map[self.node.outputs[0].id] = var_name

    def _in_var_forward(self):
        for port in self.node.inputs:
            for link in self.graph.links:
                if link.id_to == port.id:
                    src_id = self.graph.ports[link.id_from].node_id
                    return f"outputs.get('{src_id}', inputs_dict.get('{src_id}'))"
        return "None"


# ============================================================
#  DATA TRANSFORM NODES
# ============================================================
class InputDataTranslator(BaseTranslator):
    node_type = "input-data"

    def generate(self, w, phase, placement, is_first=False):
        if placement != "data":
            return
        n = self.node
        ds = n.properties.get("dataShape")
        ds_id = n.properties.get("datasetId")
        ds_file = n.properties.get("datasetFile", "")
        ds_fmt = n.properties.get("datasetFormat", "")

        if ds_id and ds_file:
            ext = ds_fmt or ds_file.rsplit(".", 1)[-1]
            if ext in ("csv", "xlsx", "json", "parquet"):
                w.line("import pandas as pd")
                if ext == "csv":
                    w.line(f"df = pd.read_csv('data/{ds_file}')")
                elif ext == "xlsx":
                    w.line(f"df = pd.read_excel('data/{ds_file}')")
                elif ext == "json":
                    w.line(f"df = pd.read_json('data/{ds_file}')")
                elif ext == "parquet":
                    w.line(f"df = pd.read_parquet('data/{ds_file}')")
                w.line("raw_data = torch.tensor(df.values, dtype=torch.float32)")
            else:
                w.line(f"# Unsupported format '{ext}' – random data fallback")
                w.line("raw_data = torch.randn(200, 10)")
            self._store_output("raw_data")
        elif ds:
            parts = ds.strip("()").split(",")
            row_str = parts[0].strip()
            cols = [int(p.strip()) for p in parts[1:]]
            if row_str.isdigit():
                w.line(
                    f"raw_data = torch.randn({row_str}, {', '.join(str(c) for c in cols)})"
                )
            else:
                w.line(f"num_rows = 200  # placeholder for '{row_str}'")
                w.line(
                    f"raw_data = torch.randn(num_rows, {', '.join(str(c) for c in cols)})"
                )
            self._store_output("raw_data")
        else:
            w.line("raw_data = torch.randn(200, 10)")
            self._store_output("raw_data")


class ColumnSelectTranslator(BaseTranslator):
    node_type = "column-select"

    def generate(self, w, phase, placement, is_first=False):
        n = self.node
        sid = _sanitize(n.id)
        cols = n.properties.get("selectedColumns", [])
        col_str = n.properties.get("columnInput", "")

        if placement == "data":
            in_var = self._in_var()
            out_var = f"{sid}_out"
            if cols:
                col_list = ", ".join(str(c) for c in cols)
                w.line(f"{out_var} = {in_var}[:, [{col_list}]]")
            elif col_str:
                w.line(f"indices = list(range({col_str}))")
                w.line(f"{out_var} = {in_var}[:, indices]")
            else:
                w.line(f"{out_var} = {in_var}")
            self._store_output(out_var)

        elif placement == "forward":
            in_expr = self._in_var_forward()
            w.line(f"x = {in_expr}")
            if cols:
                col_list = ", ".join(str(c) for c in cols)
                w.line(f"x = x[:, [{col_list}]]")
            elif col_str:
                w.line(f"indices = list(range({col_str}))")
                w.line(f"x = x[:, indices]")
            w.line(f"outputs['{n.id}'] = x")


class RowSelectTranslator(BaseTranslator):
    node_type = "row-select"

    def generate(self, w, phase, placement, is_first=False):
        n = self.node
        sid = _sanitize(n.id)
        method = n.properties.get("method", "first-n")
        value = n.properties.get("value", "100")
        seed = n.properties.get("randomSeed", 42)

        if placement == "data":
            in_var = self._in_var()
            out_var = f"{sid}_out"
            self._emit_row_select(w, in_var, out_var, method, value, seed)
            self._store_output(out_var)
        elif placement == "forward":
            in_expr = self._in_var_forward()
            w.line(f"x = {in_expr}")
            self._emit_row_select(w, "x", "x", method, value, seed)
            w.line(f"outputs['{n.id}'] = x")

    def _emit_row_select(self, w, in_var, out_var, method, value, seed):
        if method == "first-n":
            n_rows = int(value) if value.isdigit() else 100
            w.line(f"{out_var} = {in_var}[:{n_rows}]")
        elif method == "random":
            n_rows = int(value) if value.isdigit() else 100
            w.line(f"gen = torch.Generator().manual_seed({seed})")
            w.line(f"perm = torch.randperm({in_var}.size(0), generator=gen)")
            w.line(f"{out_var} = {in_var}[perm[:{n_rows}]]")
        elif method == "slice":
            parts = value.split(":")
            start = parts[0] if parts[0] else "0"
            end = parts[1] if parts[1] else f"{in_var}.size(0)"
            w.line(f"{out_var} = {in_var}[{start}:{end}]")
        elif method == "indices":
            w.line(f"indices = [{value}]")
            w.line(f"{out_var} = {in_var}[indices]")


class DimSelectTranslator(BaseTranslator):
    node_type = "dim-select"

    def generate(self, w, phase, placement, is_first=False):
        n = self.node
        sid = _sanitize(n.id)
        dims = n.properties.get("dimSelections", [])

        if placement == "data":
            in_var = self._in_var()
            out_var = f"{sid}_out"
            self._emit_dim_select(w, in_var, out_var, dims)
            self._store_output(out_var)
        elif placement == "forward":
            in_expr = self._in_var_forward()
            w.line(f"x = {in_expr}")
            self._emit_dim_select(w, "x", "x", dims)
            w.line(f"outputs['{n.id}'] = x")

    def _emit_dim_select(self, w, in_var, out_var, dims):
        slices = []
        for s in dims:
            if not s or s.strip() in (":", ""):
                slices.append(":")
            else:
                slices.append(f"[{s}]")
        if all(s == ":" for s in slices):
            w.line(f"{out_var} = {in_var}")
        else:
            w.line(f"{out_var} = {in_var}[:, {', '.join(slices)}]")


class NormalizeTranslator(BaseTranslator):
    node_type = "normalize"

    def generate(self, w, phase, placement, is_first=False):
        n = self.node
        sid = _sanitize(n.id)
        method = n.properties.get("method", "standard")

        param_in = None
        if n.paramInputs:
            for link in self.graph.links:
                if link.id_to == n.paramInputs[0].id:
                    param_in = link.id_from
                    break

        if placement == "data":
            in_var = self._in_var()
            out_var = f"{sid}_out"
            if param_in:
                src_mean = self.var_map.get(param_in + "_mean", "None")
                src_std = self.var_map.get(param_in + "_std", "None")
                if method == "standard":
                    w.line(f"{out_var} = ({in_var} - {src_mean}) / ({src_std} + 1e-8)")
                else:
                    w.line(
                        f"{out_var} = ({in_var} - {src_mean}) / ({src_std} - {src_mean} + 1e-8)"
                    )
                self._store_output(out_var)
            else:
                if method == "standard":
                    w.line(f"mean = {in_var}.mean(dim=0, keepdim=True)")
                    w.line(f"std = {in_var}.std(dim=0, keepdim=True) + 1e-8")
                    w.line(f"{out_var} = ({in_var} - mean) / std")
                    if n.paramOutputs:
                        self.var_map[n.paramOutputs[0].id + "_mean"] = "mean"
                        self.var_map[n.paramOutputs[0].id + "_std"] = "std"
                else:
                    w.line(f"min_val = {in_var}.min(dim=0, keepdim=True)[0]")
                    w.line(f"max_val = {in_var}.max(dim=0, keepdim=True)[0]")
                    w.line(
                        f"{out_var} = ({in_var} - min_val) / (max_val - min_val + 1e-8)"
                    )
                    if n.paramOutputs:
                        self.var_map[n.paramOutputs[0].id + "_mean"] = "min_val"
                        self.var_map[n.paramOutputs[0].id + "_std"] = "max_val"
                self._store_output(out_var)

        elif placement == "forward":
            in_expr = self._in_var_forward()
            w.line(f"x = {in_expr}")
            if method == "standard":
                w.line(
                    f"x = (x - x.mean(dim=0, keepdim=True)) / (x.std(dim=0, keepdim=True) + 1e-8)"
                )
            else:
                w.line(f"min_val = x.min(dim=0, keepdim=True)[0]")
                w.line(f"max_val = x.max(dim=0, keepdim=True)[0]")
                w.line(f"x = (x - min_val) / (max_val - min_val + 1e-8)")
            w.line(f"outputs['{n.id}'] = x")


class OneHotTranslator(BaseTranslator):
    node_type = "onehot"

    def generate(self, w, phase, placement, is_first=False):
        n = self.node
        sid = _sanitize(n.id)
        num_classes = n.properties.get("numClasses", 10)

        if placement == "data":
            in_var = self._in_var()
            out_var = f"{sid}_out"
            self._emit_onehot(w, in_var, out_var, num_classes)
            self._store_output(out_var)
            if n.paramOutputs:
                w.line(f"categories = torch.arange({num_classes})")
                self.var_map[n.paramOutputs[0].id] = "categories"
        elif placement == "forward":
            in_expr = self._in_var_forward()
            w.line(f"x = {in_expr}")
            self._emit_onehot(w, "x", "x", num_classes)
            w.line(f"outputs['{n.id}'] = x")

    def _emit_onehot(self, w, in_var, out_var, num_classes):
        w.line(f"{in_var}_squeezed = {in_var}.squeeze(-1).long()")
        w.line(
            f"{out_var} = torch.nn.functional.one_hot({in_var}_squeezed, num_classes={num_classes}).float()"
        )


class DeOneHotTranslator(BaseTranslator):
    node_type = "deonehot"

    def generate(self, w, phase, placement, is_first=False):
        n = self.node
        sid = _sanitize(n.id)
        if placement in ("data", "forward"):
            in_var = self._in_var()
            out_var = f"{sid}_out"
            self._emit_deonehot(w, in_var, out_var, n)
            if placement == "data":
                self._store_output(out_var)
            else:
                w.line(f"outputs['{n.id}'] = x")

    def _emit_deonehot(self, w, in_var, out_var, node):
        param_var = None
        if node.paramInputs:
            for link in self.graph.links:
                if link.id_to == node.paramInputs[0].id:
                    param_var = self.var_map.get(link.id_from)
                    break
        if param_var:
            w.line(f"categories = {param_var}")
        w.line(f"if {in_var}.dim() == 2:")
        w.indent()
        w.line(f"{out_var} = torch.argmax({in_var}, dim=-1)")
        w.dedent()
        w.line("else:")
        w.indent()
        w.line(f"{out_var} = {in_var}")
        w.dedent()


class TrainTestSplitTranslator(BaseTranslator):
    node_type = "train-test"

    def generate(self, w, phase, placement, is_first=False):
        if placement != "data":
            return
        n = self.node
        ratio = n.properties.get("trainRatio", 0.7)
        seed = n.properties.get("randomSeed", 42)
        in_var = self._in_var()
        sid = _sanitize(n.id)
        t_var = f"train_data_{sid}"
        te_var = f"test_data_{sid}"
        w.line(f"train_size = int({in_var}.size(0) * {ratio})")
        w.line(f"gen = torch.Generator().manual_seed({seed})")
        w.line(f"perm = torch.randperm({in_var}.size(0), generator=gen)")
        w.line(f"{t_var} = {in_var}[perm[:train_size]]")
        w.line(f"{te_var} = {in_var}[perm[train_size:]]")
        for port in n.outputs:
            if port.index == 0:
                self.var_map[port.id] = t_var
            else:
                self.var_map[port.id] = te_var
        self.var_map[n.id] = t_var


# ============================================================
#  MODEL LAYERS
# ============================================================
class NeuronTranslator(BaseTranslator):
    node_type = "neuron"

    def _guess_in_features(self):
        for port in self.node.inputs:
            for link in self.graph.links:
                if link.id_to == port.id:
                    # First try the source port's shape (most reliable)
                    src_port = self.graph.ports[link.id_from]
                    if (
                        src_port.shape
                        and src_port.shape.shape
                        and len(src_port.shape.shape) >= 2
                    ):
                        dim = src_port.shape.shape[-1]
                        try:
                            val = int(dim)
                            if val > 0:
                                return val
                        except (ValueError, TypeError):
                            pass
                    # Fallback: link weight_shape
                    if link.weight_shape:
                        shape = link.weight_shape.get("shape", [])
                        if len(shape) >= 2:
                            try:
                                val = int(shape[1])
                                if val > 0:
                                    return val
                            except (ValueError, TypeError):
                                pass
        raise ValueError(f"Cannot infer in_features for {self.node.id}")

    def generate(self, w, phase, placement, is_first=False):
        n = self.node
        sid = _sanitize(n.id)
        if placement == "init":
            in_f = self._guess_in_features()
            w.line(f"self.fc_{sid} = nn.Linear({in_f}, 1)")
        elif placement == "forward":
            src_ids = []
            for port in n.inputs:
                for link in self.graph.links:
                    if link.id_to == port.id:
                        src = self.graph.ports[link.id_from].node_id
                        if src not in src_ids:
                            src_ids.append(src)

            if is_first:
                # First node – read from inputs_dict (may have multiple sources)
                if not src_ids:
                    expr = "None"
                else:
                    expr = f"inputs_dict.get('{src_ids[0]}'"
                    for src in src_ids[1:]:
                        expr += f", inputs_dict.get('{src}')"
                    expr += ")"
                w.line(f"x = {expr}")
            else:
                # Not first node
                if not src_ids:
                    w.line("x = None")
                elif len(src_ids) == 1:
                    # Single source – simple read from outputs
                    src = src_ids[0]
                    w.line(f"x = outputs.get('{src}', inputs_dict.get('{src}'))")
                else:
                    # Multiple sources – try each in outputs first, then fallback
                    w.line("x = None")
                    for src in src_ids:
                        w.line(f"if x is None and '{src}' in outputs:")
                        w.indent()
                        w.line(f"x = outputs['{src}']")
                        w.dedent()
                    w.line("if x is None:")
                    w.indent()
                    fallback = f"inputs_dict.get('{src_ids[0]}'"
                    for src in src_ids[1:]:
                        fallback += f", inputs_dict.get('{src}')"
                    fallback += ")"
                    w.line(f"x = {fallback}")
                    w.dedent()

            w.line(f"x = self.fc_{sid}(x)")
            act = n.properties.get("activation", "relu")
            if act != "linear":
                if act in ("leaky_relu", "elu", "selu", "gelu", "mish"):
                    w.line(f"x = torch.nn.functional.{act}(x)")
                elif act == "softmax":
                    w.line("x = torch.softmax(x, dim=-1)")
                else:
                    w.line(f"x = torch.{act}(x)")
            w.line(f"outputs['{n.id}'] = x")


class LayerTranslator(NeuronTranslator):
    node_type = "layer"

    def generate(self, w, phase, placement, is_first=False):
        n = self.node
        sid = _sanitize(n.id)
        if placement == "init":
            in_f = self._guess_in_features()
            out_f = n.properties.get("numNeurons", 64)
            w.line(f"self.fc_{sid} = nn.Linear({in_f}, {out_f})")
        else:
            super().generate(w, phase, placement, is_first)


class Conv2DTranslator(BaseTranslator):
    node_type = "conv2d"

    def _guess_in_channels(self):
        for port in self.node.inputs:
            for link in self.graph.links:
                if link.id_to == port.id:
                    src = self.graph.ports[link.id_from]
                    if src.shape and src.shape.shape and len(src.shape.shape) >= 2:
                        try:
                            return int(src.shape.shape[1])
                        except (ValueError, TypeError):
                            pass
        return 1

    def generate(self, w, phase, placement, is_first=False):
        n = self.node
        sid = _sanitize(n.id)
        if placement == "init":
            in_ch = self._guess_in_channels()
            out_ch = n.properties.get("filters", 32)
            k = n.properties.get("kernelSize", 3)
            s = n.properties.get("stride", 1)
            p = n.properties.get("padding", 0)
            bias = n.properties.get("hasBias", True)
            w.line(
                f"self.conv_{sid} = nn.Conv2d({in_ch}, {out_ch}, kernel_size={k}, stride={s}, padding={p}, bias={bias})"
            )
        elif placement == "forward":
            if is_first:
                src = self.graph.predecessors(n.id)[0]
                w.line(f"x = inputs_dict.get('{src}', inputs_dict.get('{src}'))")
            else:
                src = self.graph.predecessors(n.id)[0]
                w.line(f"x = outputs.get('{src}', inputs_dict.get('{src}'))")
            w.line(f"x = self.conv_{sid}(x)")
            act = n.properties.get("activation", "relu")
            if act != "linear":
                if act in ("leaky_relu", "elu", "selu", "gelu", "mish"):
                    w.line(f"x = torch.nn.functional.{act}(x)")
                elif act == "softmax":
                    w.line("x = torch.softmax(x, dim=1)")
                else:
                    w.line(f"x = torch.{act}(x)")
            w.line(f"outputs['{n.id}'] = x")


class FlattenTranslator(BaseTranslator):
    node_type = "flatten"

    def generate(self, w, phase, placement, is_first=False):
        n = self.node
        sid = _sanitize(n.id)
        if placement == "init":
            w.line(f"self.flatten_{sid} = nn.Flatten()")
        elif placement == "forward":
            if is_first:
                src = self.graph.predecessors(n.id)[0]
                w.line(f"x = inputs_dict.get('{src}', inputs_dict.get('{src}'))")
            else:
                src = self.graph.predecessors(n.id)[0]
                w.line(f"x = outputs.get('{src}', inputs_dict.get('{src}'))")
            w.line(f"x = self.flatten_{sid}(x)")
            w.line(f"outputs['{n.id}'] = x")
        elif placement == "data":
            in_var = self._in_var()
            out_var = f"{sid}_out"
            w.line(f"if {in_var}.dim() == 2 and {in_var}.size(-1) == 1:")
            w.indent()
            w.line(f"{out_var} = {in_var}.squeeze(-1)")
            w.dedent()
            w.line("else:")
            w.indent()
            w.line(f"{out_var} = torch.flatten({in_var}, start_dim=1)")
            w.dedent()
            self._store_output(out_var)


class DropoutTranslator(BaseTranslator):
    node_type = "dropout"

    def generate(self, w, phase, placement, is_first=False):
        n = self.node
        sid = _sanitize(n.id)
        if placement == "init":
            rate = n.properties.get("rate", 0.5)
            w.line(f"self.dropout_{sid} = nn.Dropout(p={rate})")
        elif placement == "forward":
            if is_first:
                src = self.graph.predecessors(n.id)[0]
                w.line(f"x = inputs_dict.get('{src}', inputs_dict.get('{src}'))")
            else:
                src = self.graph.predecessors(n.id)[0]
                w.line(f"x = outputs.get('{src}', inputs_dict.get('{src}'))")
            w.line(f"x = self.dropout_{sid}(x)")
            w.line(f"outputs['{n.id}'] = x")


class BatchNormTranslator(BaseTranslator):
    node_type = "batchnorm"

    def _guess_num_features(self):
        for port in self.node.inputs:
            for link in self.graph.links:
                if link.id_to == port.id:
                    src = self.graph.ports[link.id_from]
                    if src.shape and src.shape.shape and len(src.shape.shape) >= 2:
                        dim = src.shape.shape[-1]
                        try:
                            return int(dim) if dim.is_concrete else 1
                        except (ValueError, TypeError):
                            pass
        for nid in self.graph.predecessors(self.node.id):
            pred = self.graph.nodes[nid]
            if pred.type == "layer":
                return pred.properties.get("numNeurons", 1)
            if pred.type == "neuron":
                return 1
        return 1

    def generate(self, w, phase, placement, is_first=False):
        n = self.node
        sid = _sanitize(n.id)
        if placement == "init":
            num_f = self._guess_num_features()
            w.line(f"self.bn_{sid} = nn.BatchNorm1d(num_features={num_f})")
        elif placement == "forward":
            if is_first:
                src = self.graph.predecessors(n.id)[0]
                w.line(f"x = inputs_dict.get('{src}', inputs_dict.get('{src}'))")
            else:
                src = self.graph.predecessors(n.id)[0]
                w.line(f"x = outputs.get('{src}', inputs_dict.get('{src}'))")
            w.line(f"x = self.bn_{sid}(x)")
            w.line(f"outputs['{n.id}'] = x")


class AddTranslator(BaseTranslator):
    node_type = "add"

    def generate(self, w, phase, placement, is_first=False):
        n = self.node
        if placement != "forward":
            return
        preds = self.graph.predecessors(n.id)
        if len(preds) >= 2:
            w.line(f"a = outputs.get('{preds[0]}', inputs_dict.get('{preds[0]}'))")
            w.line(f"b = outputs.get('{preds[1]}', inputs_dict.get('{preds[1]}'))")
            w.line("if a is not None and b is not None:")
            w.indent()
            w.line("x = a + b")
            w.line(f"outputs['{n.id}'] = x")
            w.dedent()
        else:
            w.line(f"outputs['{n.id}'] = None  # Add needs 2 inputs")


class ConcatTranslator(BaseTranslator):
    node_type = "concat"

    def generate(self, w, phase, placement, is_first=False):
        n = self.node
        if placement != "forward":
            return
        preds = self.graph.predecessors(n.id)
        axis = n.properties.get("axis", -1)
        if len(preds) >= 2:
            w.line("tensors = []")
            for p in preds:
                w.line(f"tmp = outputs.get('{p}', inputs_dict.get('{p}'))")
                w.line("if tmp is not None: tensors.append(tmp)")
            w.line("if len(tensors) > 1:")
            w.indent()
            w.line(f"x = torch.cat(tensors, dim={axis})")
            w.line(f"outputs['{n.id}'] = x")
            w.dedent()
            w.line("else:")
            w.indent()
            w.line(f"outputs['{n.id}'] = None")
            w.dedent()
        else:
            w.line(f"outputs['{n.id}'] = None  # Concat needs >=2 inputs")


class OutputTranslator(BaseTranslator):
    node_type = "output"

    def generate(self, w, phase, placement, is_first=False):
        n = self.node
        if placement != "forward":
            return
        src = None
        for port in n.inputs:
            for link in self.graph.links:
                if link.id_to == port.id:
                    src = self.graph.ports[link.id_from].node_id
                    break
            if src:
                break
        if src:
            w.line(f"if '{src}' in outputs or '{src}' in inputs_dict:")
            w.indent()
            w.line(f"x = outputs.get('{src}', inputs_dict.get('{src}'))")
            for out_port in n.outputs:
                role = out_port.role
                act = n.properties.get("outputActivations", {}).get(role, "none")
                if role == "loss" or act == "none":
                    w.line(f"outputs['{out_port.id}'] = x")
                elif act == "softmax":
                    w.line(f"outputs['{out_port.id}'] = torch.softmax(x, dim=-1)")
                elif act == "argmax":
                    w.line(f"outputs['{out_port.id}'] = torch.argmax(x, dim=-1)")
            w.line(f"outputs['{n.id}'] = x")
            w.dedent()
        else:
            w.line(f"outputs['{n.id}'] = None")


# ============================================================
#  SPECIAL NODES
# ============================================================
class OptimizerTranslator(BaseTranslator):
    node_type = "optimizer"

    def emit_training_setup(self, w: CodeWriter):
        props = self.node.properties
        loss = props.get("lossType", "mse")
        opt = props.get("optimizerType", "adam")
        lr = props.get("learningRate", 0.001)

        loss_map = {
            "mse": "nn.MSELoss()",
            "cross_entropy": "nn.CrossEntropyLoss()",
            "bce": "nn.BCEWithLogitsLoss()",
            "l1": "nn.L1Loss()",
            "huber": "nn.HuberLoss()",
        }
        w.line(f"criterion = {loss_map.get(loss, 'nn.MSELoss()')}")

        if opt == "adam":
            w.line(f"optimizer = optim.Adam(model.parameters(), lr={lr},")
            w.line(
                f"                            betas=({props.get('adamBeta1', 0.9)}, {props.get('adamBeta2', 0.999)}),"
            )
            w.line(f"                            eps={props.get('adamEpsilon', 1e-8)},")
            w.line(
                f"                            weight_decay={props.get('weightDecay', 0)})"
            )
        elif opt == "sgd":
            w.line(f"optimizer = optim.SGD(model.parameters(), lr={lr},")
            w.line(
                f"                            momentum={props.get('sgdMomentum', 0.9)},"
            )
            w.line(
                f"                            weight_decay={props.get('weightDecay', 0)},"
            )
            w.line(
                f"                            nesterov={props.get('nesterov', False)})"
            )
        elif opt == "adamw":
            w.line(f"optimizer = optim.AdamW(model.parameters(), lr={lr},")
            w.line(
                f"                             betas=({props.get('adamBeta1', 0.9)}, {props.get('adamBeta2', 0.999)}),"
            )
            w.line(
                f"                             eps={props.get('adamEpsilon', 1e-8)},"
            )
            w.line(
                f"                             weight_decay={props.get('weightDecay', 0)})"
            )
        else:
            w.line(f"optimizer = optim.Adam(model.parameters(), lr={lr})")

        if loss in ("cross_entropy", "nll"):
            w.line("labels = labels.long()  # required for CrossEntropyLoss")

    def get_config(self) -> str:
        props = self.node.properties
        lines = [
            f"'learning_rate': {props.get('learningRate', 0.001)}",
            f"'epochs': {props.get('epochs', 10)}",
            f"'batch_size': {props.get('batchSize', 32)}",
            f"'shuffle': {'True' if props.get('shuffle', True) else 'False'}",
            f"'gradient_clip': {props.get('gradientClip') if props.get('gradientClip') is not None else 'None'}",
            f"'early_stopping': {'True' if props.get('earlyStopping') else 'False'}",
            f"'early_stopping_patience': {props.get('earlyStoppingPatience', 10)}",
        ]
        return "{\n" + ",\n".join(f"        {l}" for l in lines) + "\n    }"


class VisualizationTranslator(BaseTranslator):
    node_type = "visualization"

    def generate(self, w, phase, placement, is_first=False):
        if placement != "data":
            return
        n = self.node
        coord_ports = [p for p in n.inputs if p.sub_type == "coord"]
        color_port = next((p for p in n.inputs if p.role == "color"), None)

        w.line(f"# Visualization '{n.id}'")
        w.line("plt.figure()")
        var_names = []
        for i, port in enumerate(coord_ports):
            vname = f"data_{_sanitize(port.id)}"
            src_var = None
            for link in self.graph.links:
                if link.id_to == port.id:
                    src = self.var_map.get(link.id_from)
                    if src is None:
                        src_nid = self.graph.ports[link.id_from].node_id
                        src = self.var_map.get(src_nid, "None")
                    src_var = src
                    break
            if src_var:
                w.line(f"{vname} = {src_var}")
            else:
                w.line(f"{vname} = None")
            var_names.append(vname)

        if color_port:
            src_var = None
            for link in self.graph.links:
                if link.id_to == color_port.id:
                    src = self.var_map.get(link.id_from)
                    if src is None:
                        src_nid = self.graph.ports[link.id_from].node_id
                        src = self.var_map.get(src_nid, "None")
                    src_var = src
                    break
            if src_var:
                w.line(f"colors = {src_var}")
            else:
                w.line("colors = None")
        else:
            w.line("colors = None")

        cmode = n.properties.get("colorMode", "none")
        cmap = "None"
        if cmode == "discrete" and color_port:
            palette = n.properties.get("colorPalette", [])
            if palette:
                w.line("from matplotlib.colors import ListedColormap")
                hexes = ", ".join(f"'{c}'" for c in palette)
                w.line(f"custom_cmap = ListedColormap([{hexes}])")
                cmap = "custom_cmap"
            else:
                cmap = "'tab10'"
        elif cmode == "continuous" and color_port:
            w.line("from matplotlib.colors import LinearSegmentedColormap")
            minc = n.properties.get("continuousMinColor", "#3b82f6")
            maxc = n.properties.get("continuousMaxColor", "#ef4444")
            w.line(
                f"custom_cmap = LinearSegmentedColormap.from_list('cust', ['{minc}', '{maxc}'])"
            )
            cmap = "custom_cmap"

        if len(coord_ports) == 1:
            w.line(f"plt.hist({var_names[0]}.flatten(), bins=20)")
        elif len(coord_ports) == 2:
            if color_port and cmap != "None":
                w.line(
                    f"plt.scatter({var_names[0]}.flatten(), {var_names[1]}.flatten(), "
                    f"c=colors.flatten(), alpha=0.5, cmap={cmap})"
                )
                if cmode == "continuous":
                    w.line("cbar = plt.colorbar()")
                    w.line("cbar.set_label('Value')")
            else:
                w.line(
                    f"plt.scatter({var_names[0]}.flatten(), {var_names[1]}.flatten(), alpha=0.5)"
                )
        elif len(coord_ports) == 3:
            w.line("fig = plt.figure()")
            w.line("ax = fig.add_subplot(111, projection='3d')")
            if color_port and cmap != "None":
                w.line(
                    f"ax.scatter({var_names[0]}, {var_names[1]}, {var_names[2]}, "
                    f"c=colors.flatten(), alpha=0.5, cmap={cmap})"
                )
            else:
                w.line(f"ax.scatter({var_names[0]}, {var_names[1]}, {var_names[2]})")
        w.line(f"plt.title('Visualization {n.id}')")
        w.line("plt.grid(True)")
        w.line("plt.show()")


class PrintTranslator(BaseTranslator):
    node_type = "print"

    def generate(self, w, phase, placement, is_first=False):
        if placement not in ("data", "forward"):
            return
        n = self.node
        label = n.properties.get("label", "") or n.id
        if placement == "forward":
            src_port_id = None
            for port in n.inputs:
                for link in self.graph.links:
                    if link.id_to == port.id:
                        src_port_id = link.id_from
                        break
                if src_port_id:
                    break
            if src_port_id:
                expr = f"outputs.get('{src_port_id}', inputs_dict.get('{src_port_id}'))"
                w.line(f'print("{label}:", {expr}.shape, {expr})')
            else:
                w.line(f'print("{label}: no input")')
        else:
            for i, port in enumerate(n.inputs):
                for link in self.graph.links:
                    if link.id_to == port.id:
                        src = self.var_map.get(link.id_from)
                        if src is None:
                            src_nid = self.graph.ports[link.id_from].node_id
                            src = self.var_map.get(src_nid, "None")
                        w.line(f'print("{label}[{i}]:", {src}.shape, {src})')
                        break


class AccuracyTranslator(BaseTranslator):
    node_type = "accuracy"

    def generate(self, w, phase, placement, is_first=False):
        if placement not in ("data", "forward"):
            return
        n = self.node
        show_cm = n.properties.get("showConfusion", False)

        # ---- find source port IDs ----
        pred_src = None
        label_src = None
        if placement == "forward":
            sources = []
            for port in n.inputs:
                for link in self.graph.links:
                    if link.id_to == port.id:
                        sources.append(link.id_from)
                        break
            if len(sources) >= 2:
                pred_src = sources[0]
                label_src = sources[1]
        else:
            for port in n.inputs:
                for link in self.graph.links:
                    if link.id_to == port.id:
                        if port.index == 0:
                            pred_src = link.id_from
                        else:
                            label_src = link.id_from
                        break

        if not pred_src or not label_src:
            w.line("# Accuracy node missing inputs")
            return

        # ---- variable names ----
        pred_var = self.var_map.get(pred_src)
        label_var = self.var_map.get(label_src)
        if pred_var is None:
            pred_nid = self.graph.ports[pred_src].node_id
            pred_var = self.var_map.get(pred_nid, "None")
        if label_var is None:
            label_nid = self.graph.ports[label_src].node_id
            label_var = self.var_map.get(label_nid, "None")

        # ---- prediction handling (purely shape‑based) ----
        pred_op = ""
        pred_port = self.graph.ports[pred_src]
        shape = pred_port.shape
        if shape and shape.shape and len(shape.shape) >= 2:
            dim = shape.shape[-1]
            if dim.is_concrete:
                if int(dim) > 1:
                    pred_op = f"{pred_var}.argmax(dim=1)"
                else:
                    pred_op = f"{pred_var}.squeeze(-1).long()"
            else:
                # symbolic last dim → assume >1 and argmax
                pred_op = f"{pred_var}.argmax(dim=1)"
        else:
            pred_op = f"{pred_var}.long()"

        # ---- label handling (purely shape‑based) ----
        label_op = ""
        label_port = self.graph.ports[label_src]
        shape = label_port.shape
        if shape and shape.shape and len(shape.shape) >= 2:
            dim = shape.shape[-1]
            if dim.is_concrete:
                if int(dim) > 1:
                    label_op = f"{label_var}.argmax(dim=1)"
                else:
                    label_op = f"{label_var}.squeeze(-1).long()"
            else:
                label_op = f"{label_var}.argmax(dim=1)"
        else:
            label_op = f"{label_var}.long()"

        w.line(f"pred_labels = {pred_op}")
        w.line(f"true_labels = {label_op}")
        w.line("acc = (pred_labels == true_labels).float().mean()")
        w.line('print(f"Accuracy: {acc.item():.4f}")')

        if show_cm:
            w.line("from sklearn.metrics import confusion_matrix")
            w.line("cm = confusion_matrix(true_labels.cpu(), pred_labels.cpu())")
            w.line('print("Confusion Matrix:")')
            w.line("print(cm)")


class ReshapeTranslator(BaseTranslator):
    node_type = "reshape"

    def generate(self, w, phase, placement, is_first=False):
        n = self.node
        sid = _sanitize(n.id)
        target_str = n.properties.get("targetShape", "(batch, -1)")
        parts = [x.strip() for x in target_str.strip("()").split(",") if x.strip()]
        tuple_parts = []
        for p in parts:
            if p == "-1":
                tuple_parts.append("-1")
            else:
                try:
                    int(p)
                    tuple_parts.append(p)
                except ValueError:
                    # assume symbolic name, can't be used directly – treat as -1
                    tuple_parts.append("-1")
        target_tuple = "(" + ", ".join(tuple_parts) + ")"

        if placement == "data":
            in_var = self._in_var()
            out_var = f"{sid}_out"
            w.line(f"{out_var} = {in_var}.reshape({target_tuple})")
            self._store_output(out_var)
        elif placement == "forward":
            in_expr = self._in_var_forward()
            w.line(f"x = {in_expr}")
            w.line(f"x = x.reshape({target_tuple})")
            w.line(f"outputs['{n.id}'] = x")


# ============================================================
#  REGISTRY
# ============================================================
TRANSLATOR_REGISTRY = {
    "input-data": InputDataTranslator,
    "column-select": ColumnSelectTranslator,
    "row-select": RowSelectTranslator,
    "dim-select": DimSelectTranslator,
    "normalize": NormalizeTranslator,
    "onehot": OneHotTranslator,
    "deonehot": DeOneHotTranslator,
    "train-test": TrainTestSplitTranslator,
    "neuron": NeuronTranslator,
    "layer": LayerTranslator,
    "conv2d": Conv2DTranslator,
    "flatten": FlattenTranslator,
    "dropout": DropoutTranslator,
    "batchnorm": BatchNormTranslator,
    "add": AddTranslator,
    "concat": ConcatTranslator,
    "output": OutputTranslator,
    "optimizer": OptimizerTranslator,
    "visualization": VisualizationTranslator,
    "print": PrintTranslator,
    "accuracy": AccuracyTranslator,
    "reshape": ReshapeTranslator,
}


def get_translator(node: Node, graph: Graph, var_map: dict) -> BaseTranslator:
    cls = TRANSLATOR_REGISTRY.get(node.type, BaseTranslator)
    return cls(node, graph, var_map)
