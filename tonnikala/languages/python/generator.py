from tonnikala.ir import nodes
from tonnikala.languages.base import LanguageNode, ComplexNode, BaseGenerator
from tonnikala.languages.python.astmangle import FreeVarFinder
import ast

name_counter = 0
ALWAYS_BUILTINS = '''
    False
    True
    None
'''.split()

class PythonNode(LanguageNode):
    def __init__(self, *a, **kw):
        super(PythonNode, self).__init__(*a, **kw)
        self.free_variables = set()
        self.masked_variables = set()
        self.generated_variables = set()

    def make_string(self, text):
        if isinstance(text, bytes):
            text = text.decode('UTF-8')

        rv = repr(text)
        if rv.startswith('u'):
            rv = rv[1:]

        return rv

    def generate_yield(self, code, escape=False):
        method = ''
        if escape:
           method = '.escape'

        return self.generate_indented_code('__output__%s(%s)' % (method, code))

    def gen_name(self):
        global name_counter
        name_counter += 1
        return "__tk_%d__" % name_counter

    def generate_function(self, name, generator, add_buffer=False, buffer_class='__tonnikala__.Buffer'):
        yield self.generate_indented_code('def %s():' % name)
        self.indent_level += 1

        if add_buffer:
            yield self.generate_indented_code('__output__ = %s()' % buffer_class)

        for i in generator():
            yield i

        if add_buffer:
            yield self.generate_indented_code('return __output__')

        self.indent_level -= 1
        
    def generate_varscope(self, generator):
        name = self.gen_name()
        for i in self.generate_function(name, generator):
            yield i

        yield self.generate_indented_code('%s()' % name)

    def get_generated_variables(self):
        return set(self.generated_variables)

    def get_free_variables(self):
        return set(self.free_variables) - set(self.masked_variables)


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
        self.free_variables = FreeVarFinder.for_expression(self.expr).get_free_variables()

    def generate(self):
        yield self.generate_yield('%s' % self.expr, escape=True)


class PyComplexNode(ComplexNode, PythonNode):
    def get_free_variables(self):
        rv = set(self.free_variables)
        gens = set(self.generated_variables)
        for c in self.children:
            rv.update(c.get_free_variables())
            gens.update(c.get_generated_variables())

        return rv - self.masked_variables - gens


class PyIfNode(PyComplexNode):
    def __init__(self, expression):
        super(PyIfNode, self).__init__()
        self.expression = expression
        self.free_variables = FreeVarFinder.for_expression(self.expression).get_free_variables()

    def generate(self):
        yield self.generate_indented_code("if (%s):" % self.expression)
        for i in self.indented_children():
            yield i


class PyImportNode(PythonNode):
    def __init__(self, href, alias):
        super(PyImportNode, self).__init__()
        self.href = href
        self.alias = alias
        self.generated_variables = set([self.alias])

    def generate(self):
        yield self.generate_indented_code(
           "%s = __tonnikala__.import_defs('%s')" % (self.alias, self.href))


class PyAttributeNode(PyComplexNode):
    def __init__(self, name, value):
        super(PyAttributeNode, self).__init__()
        self.name = name

    def generate(self):
        funcname = self.gen_name()
        for i in self.generate_function(funcname, lambda: self.indented_children(0), 
                     add_buffer=True, buffer_class='__tonnikala__.AttrBuffer'):
            yield i

        yield self.generate_yield('__tonnikala__.output_attr("%s", %s)'
            % (self.name, funcname))

class PyAttrsNode(PythonNode):
    def __init__(self, expression):
        super(PyAttrsNode, self).__init__()
        self.expression = expression
        self.free_variables = FreeVarFinder.for_expression(expression).get_free_variables()

    def generate(self):
        yield self.generate_yield('__tonnikala__.output_attrs(%s)' 
            % self.expression)

class PyForNode(PyComplexNode):
    def __init__(self, vars, expression):
        super(PyForNode, self).__init__()
        self.vars = vars
        self.expression = expression
        self.free_variables = FreeVarFinder.for_expression(expression).get_free_variables()

        # evaluate the for target as a tuple!
        self.masked_variables  = FreeVarFinder.for_expression(vars).get_free_variables()
        self.free_variables   -= self.masked_variables

        # sic
        self.generated_variables = self.masked_variables

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
        self.def_clause = "def %s:" % self.funcspec
        fvf = FreeVarFinder.for_statement(self.def_clause + "pass")
        self.generated_variables = fvf.get_generated_variables()
        self.masked_variables = fvf.get_masked_variables()
        self.free_variables = fvf.get_free_variables() - fvf.get_generated_variables()
        print self.generated_variables, self.free_variables

    def generate(self):
        yield self.generate_indented_code("def %s:" % self.funcspec)
        yield self.generate_indented_code("    __output__ = __tonnikala__.Buffer()")

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
        free_variables = self.get_free_variables()
        free_variables.difference_update(ALWAYS_BUILTINS)
        yield 'def __binder__(__tonnikala__context__):\n'
        yield '    __tonnikala__ = __tonnikala_runtime__\n'

        for i in free_variables:
            yield '    if "%s" in __tonnikala__context__: %s = __tonnikala__context__["%s"]\n' % (i, i, i)

        yield '    class __Template__(object):\n'
        yield '        def __main__(__self__):\n'
        yield '            __output__ = __tonnikala__.Buffer()\n'

        for i in self.indented_children(increment=3):
            yield i

        yield '            return __output__\n'
        yield '    return __Template__()\n'


class Generator(BaseGenerator):
    OutputNode      = PyOutputNode
    IfNode          = PyIfNode
    ForNode         = PyForNode
    DefineNode      = PyDefineNode
    ComplexExprNode = PyComplexExprNode
    ExpressionNode  = PyExpressionNode
    ImportNode      = PyImportNode
    RootNode        = PyRootNode
    AttributeNode   = PyAttributeNode
    AttrsNode       = PyAttrsNode
