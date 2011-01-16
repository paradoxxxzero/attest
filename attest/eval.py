from . import ast
from .codegen import to_source
import inspect

try:
    import __builtin__ as builtins
except ImportError:
    import builtins


# Partially based on codegen.SourceGenerator by Armin Ronacher
class ExpressionEvaluator(ast.NodeVisitor):

    def __init__(self, expr, globals, locals):
        self.expr = expr
        self.globals, self.locals = globals, locals
        self.names = dict(vars(builtins), **dict(globals, **locals))
        self._parts = []
        node = ast.parse(self.expr).body[0].value
        self.visit(node)

    @property
    def result(self):
        return ''.join(self._parts)

    def eval(self, node):
        return eval(to_source(node), self.globals, self.locals)

    def write(self, s):
        self._parts.append(s)

    def visit_Compare(self, node):
        self.write('(')
        self.visit(node.left)
        for op, right in zip(node.ops, node.comparators):
            self.write(' %s ' % ast.CMPOP_SYMBOLS[type(op)])
            self.visit(right)
        self.write(')')

    def visit_BoolOp(self, node):
        self.write('(')
        for i, value in enumerate(node.values):
            if i:
                self.write(' %s ' % ast.BOOLOP_SYMBOLS[type(node.op)])
            self.visit(value)
        self.write(')')

    def visit_Call(self, node):
        want_comma = []
        def write_comma():
            if want_comma:
                self.write(', ')
            else:
                want_comma.append(True)
        self.visit(node.func)
        self.write('(')
        for arg in node.args:
            write_comma()
            self.visit(arg)
        for keyword in node.keywords:
            write_comma()
            self.write(keyword.arg + '=')
            self.visit(keyword.value)
        if node.starargs is not None:
            write_comma()
            self.write('*')
            self.visit(node.starargs)
        if node.kwargs is not None:
            write_comma()
            self.write('**')
            self.visit(node.kwargs)
        self.write(')')

    def visit_Attribute(self, node):
        self.write(node.value.id)
        self.write('.')
        self.write(node.attr)

    def visit_Name(self, node):
        value = self.names[node.id]
        if hasattr(value, '__name__'):
            self.write(value.__name__)
        else:
            self.write(repr(value))

    def generic_visit(self, node):
        self.write(repr(self.eval(node)))


def evalexpr(expr, globals=None, locals=None):
    """Expands names and computations in an expression string, but retains
    function calls, type literals and comparative/boolean operations.

    >>> value = 1 + 1
    >>> evalexpr('value == int("2") and value < 5 - 2')
    "((2 == int('2')) and (2 < 3))"

    """
    if globals is None:
        globals = inspect.stack()[1][0].f_globals
    if locals is None:
        locals = inspect.stack()[1][0].f_locals
    return ExpressionEvaluator(expr, globals, locals).result