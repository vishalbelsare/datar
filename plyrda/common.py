from abc import ABC
from pipda import Symbolic
from .utils import expand_collections

X = Symbolic('X')

class UnaryOp(ABC):

    def __init__(self, operand):
        self.operand = operand

class UnaryNeg(UnaryOp):
    ...

class UnaryPos(UnaryOp):
    ...

class UnaryInvert(UnaryOp):
    ...

class Collection(list):

    def __init__(self, args):
        super().__init__(args)

    def __neg__(self):
        return UnaryNeg(self)

    def __pos__(self):
        return UnaryPos(self)

    def __invert__(self):
        return UnaryInvert(self)
