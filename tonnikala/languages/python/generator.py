from tonnikala.ir import nodes
from tonnikala.languages.base import LanguageNode, ComplexNode, BaseGenerator

name_counter = 0

class PythonNode(LanguageNode):
    def make_string(self, text):
        if isinstance(text, bytes):
            text = text.decode('UTF-8')

        rv = repr(text)
        if rv.startswith('u'):
            rv = rv[1:]

        return rv

    def generate_yield(self, code):
        return self.generate_indented_code('__output__(%s)' % code)

    def gen_name(self):
        global name_counter
        name_counter += 1
        return "__tk_%d__" % name_counter

    def generate_varscope(self, generator):
        name = self.gen_name()
        yield self.generate_indented_code('def %s():' % name)
        self.indent_level += 1

        for i in generator():
            yield i

        self.indent_level -= 1
        yield self.generate_indented_code('%s()' % name)


class PyOutputNode(PythonNode):
    def __init__(self, text):
        super(PyOutputNode, self).__init__()
        self.text = text

    def generate(self):
        yield self.generate_yield(self.make_string(self.text))


class PyExpressionNode(PythonNode):
    def __init__(self, expression, tokens):
        super(PyExpressionNode, self).__init__()
        self.expr = expression
        self.tokens = tokens

    def generate(self):
        yield self.generate_yield('(%s)' % self.expr)


class PyComplexNode(ComplexNode, PythonNode):
    pass

class PyIfNode(PyComplexNode):
    def __init__(self, expression):
        super(PyIfNode, self).__init__()
        self.expression = expression

    def generate(self):
        yield self.generate_indented_code("if (%s):" % self.expression)
        for i in self.indented_children():
            yield i

class PyImportNode(PythonNode):
    def __init__(self, href, alias):
        super(PyImportNode, self).__init__()
        self.href = href
        self.alias = alias

    def generate(self):
        yield self.generate_indented_code(
           "%s = __self.__tonnikala__.import_defs('%s')" % (self.alias, self.href))
        

class PyForNode(PyComplexNode):
    def __init__(self, vars, expression):
        super(PyForNode, self).__init__()
        self.vars = vars
        self.expression = expression

    def generate_contents(self):
        yield self.generate_indented_code("for %s in %s:" % (self.vars, self.expression))
        for i in self.indented_children():
            yield i

    def generate(self):
        for i in self.generate_varscope(self.generate_contents):
            yield i

class PyDefineNode(PyComplexNode):
    def __init__(self, funcspec):
        super(PyDefineNode, self).__init__()
        if '(' not in funcspec:
            funcspec += '()'

        self.funcspec = funcspec
        

    def generate(self):
        yield self.generate_indented_code("def %s:" % self.funcspec)
        yield self.generate_indented_code("    __output__ = __self.__tonnikala__.Rope()")

        for i in self.indented_children():
            yield i

        yield self.generate_indented_code("    return __output__")

class PyComplexExprNode(PyComplexNode):
    def generate(self):
        for i in self.indented_children(increment=0):
            yield i

class PyRootNode(PyComplexNode):
    def __init__(self):
        super(PyRootNode, self).__init__()
        self.set_indent_level(0)

    def generate(self):
        yield 'class __Template(object):\n'
        yield '    __tonnikala__ = __tonnikala_runtime__\n'
        yield '    def render(__self, __context):\n'
        yield '        return __self.do_render(__context).join()\n'
        yield '    def do_render(__self, __context):\n'
        yield '        __output__ = __self.__tonnikala__.Rope()\n'

        for i in self.indented_children(increment=2):
            yield i

        yield '        return __output__\n'

class Generator(BaseGenerator):
    OutputNode      = PyOutputNode
    IfNode          = PyIfNode
    ForNode         = PyForNode
    DefineNode      = PyDefineNode
    ComplexExprNode = PyComplexExprNode
    ExpressionNode  = PyExpressionNode
    ImportNode      = PyImportNode
    RootNode        = PyRootNode
