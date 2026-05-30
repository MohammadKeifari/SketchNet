from .base import BaseTranslator
from .layer import LayerTranslator
from .neuron import NeuronTranslator
from .conv2d import Conv2DTranslator
from .flatten import FlattenTranslator
from .dropout import DropoutTranslator
from .batchnorm import BatchNormTranslator
from .add import AddTranslator
from .concat import ConcatTranslator
from .input_data import InputDataTranslator
from .output import OutputTranslator
from .optimizer import OptimizerTranslator
from .train_test import TrainTestSplitTranslator
from .normalize import NormalizeTranslator
from .column_select import ColumnSelectTranslator
from .row_select import RowSelectTranslator
from .dim_select import DimSelectTranslator
from .onehot import OneHotEncodeTranslator
from .visualization import VisualizationTranslator

TRANSLATORS = {
    "layer": LayerTranslator,
    "neuron": NeuronTranslator,
    "conv2d": Conv2DTranslator,
    "flatten": FlattenTranslator,
    "dropout": DropoutTranslator,
    "batchnorm": BatchNormTranslator,
    "add": AddTranslator,
    "concat": ConcatTranslator,
    "input-data": InputDataTranslator,
    "output": OutputTranslator,
    "optimizer": OptimizerTranslator,
    "train-test": TrainTestSplitTranslator,
    "normalize": NormalizeTranslator,
    "column-select": ColumnSelectTranslator,
    "row-select": RowSelectTranslator,
    "dim-select": DimSelectTranslator,
    "onehot": OneHotEncodeTranslator,
    "visualization": VisualizationTranslator,
}


def get_translator(node, generator):
    cls = TRANSLATORS.get(node["type"], BaseTranslator)
    return cls(node, generator)
