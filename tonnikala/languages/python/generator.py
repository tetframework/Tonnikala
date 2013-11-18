# -*- coding: utf-8 -*-

# notice: this module cannot be sanely written to take use of
# unicode_literals, bc some of the arguments need to be str on 
# both python2 and 3
from __future__ import absolute_import, division, print_function

from tonnikala.ir import nodes
from tonnikala.languages.base import LanguageNode, ComplexNode, BaseGenerator
from tonnikala.languages.python.astmangle import FreeVarFinder
import ast
from ast import *
from six import string_types

name_counter = 0
ALWAYS_BUILTINS = '''
    False
    True
    None
'''.split()


def SimpleCall(func, args=None):
    return Call(func=func, args=args or [], keywords=[], starargs=None, kwargs=None)


def SimpleFunctionDef(name):
    return FunctionDef(
        name=name,
        args=arguments(
            args=[],
            vararg=None,
            varargannotation=None,
            kwonlyargs=[],
            kwarg=None,
            kwargannotation=None,
            defaults=[],
            kw_defaults=[]),
        body=[Pass()],
        decorator_list=[],
        returns=None
    )


def NameX(id, store=False):
    return Name(id=id, ctx=Load() if not store else Store())


def get_expression_ast(expression, mode='eval'):
    if not isinstance(expression, string_types):
        return expression

    tree = ast.parse(expression, mode=mode)
    return tree.body


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
        return rv


    def generate_output_ast(self, code, escape=False):
        func = Name(id='__output__', ctx=Load())
        if escape:
            func = Attribute(value=func, attr='escape', ctx=Load())

        if not isinstance(code, list):
            code = [ code ]

        rv = Expr(SimpleCall(func, code))
        rv.is_output = True
        return [ rv ]


    def gen_name(self):
        global name_counter
        name_counter += 1
        return "__tk_%d__" % name_counter


    def generate_buffer_frame(self, body, buffer_class='__tonnikala__.Buffer'):
        new_body = []
        new_body.append(Assign(
            targets=[NameX('__output__', store=True)],
            value=SimpleCall(
                get_expression_ast(buffer_class)
            )
        ))

        new_body.extend(body)
        new_body.append(Return(value=NameX('__output__')))
        return new_body
        

    def generate_function(self, name, body, add_buffer=False, 
                          buffer_class='__tonnikala__.Buffer'):

        func = SimpleFunctionDef(name)
        new_body = func.body = [ ]

        if add_buffer:
            new_body.extend(self.generate_buffer_frame(body, buffer_class))

        else:
            new_body.extend(body)

        if not new_body:
            new_body.append(Pass())

        return func


    def generate_varscope(self, body):
        name = self.gen_name()
        rv = [
            self.generate_function(name, body),
            Expr(SimpleCall(NameX(name)))
        ]
        return rv


    def get_generated_variables(self):
        return set(self.generated_variables)


    def get_free_variables(self):
        return set(self.free_variables) - set(self.masked_variables)


class PyOutputNode(PythonNode):
    def __init__(self, text):
        super(PyOutputNode, self).__init__()
        self.text = text


    def get_expressions(self):
        return [ self.get_expression() ]


    def get_expression(self):
        return Str(s=(self.text))


    def generate_ast(self):
        return self.generate_output_ast(self.get_expression())


class PyExpressionNode(PythonNode):
    def __init__(self, expression, tokens):
        super(PyExpressionNode, self).__init__()
        self.expr = expression
        self.tokens = tokens
        self.free_variables = FreeVarFinder.for_expression(self.expr).get_free_variables()


    def get_expressions(self):
        return [ self.get_expression() ]


    def get_expression(self):
        return SimpleCall(
            NameX('__tonnikala__escape__'),
            [ self.get_unescaped_expression() ]
        )


    def get_unescaped_expression(self):
        return get_expression_ast(self.expr)


    def generate_ast(self):
        return self.generate_output_ast(self.get_expression())


class PyComplexNode(ComplexNode, PythonNode):
    def generate_child_ast(self):
        rv = []
        for i in self.children:
            rv.extend(i.generate_ast())

        return rv


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


    def generate_ast(self):
        node = If(
           test=get_expression_ast(self.expression),
           body=self.generate_child_ast(),
           orelse=[]
        )
        return [ node ]


def PyUnlessNode(self, expression):
    expression = get_expression_ast(expression)
    expression = UnaryOp(op=Not(), operand=expression)
    return PyIfNode(expression)


class PyImportNode(PythonNode):
    def __init__(self, href, alias):
        super(PyImportNode, self).__init__()
        self.href = href
        self.alias = alias
        self.generated_variables = set([self.alias])


    def generate_ast(self):
        node = Assign(
            targets = [NameX(self.alias)],
            value = 
                SimpleCall(
                    func=
                        Attribute(value=NameX('__tonnikala__'), 
                                  attr='import_defs', ctx=Load()), 
                    args=[Str(s=self.href)]
                )
        )
        return node


class PyAttributeNode(PyComplexNode):
    def __init__(self, name, value):
        super(PyAttributeNode, self).__init__()
        self.name = name


    def get_expressions(self):
        rv = []
        for i in self.children:
            rv.extend(i.get_expressions())

        return rv


    def generate_ast(self):
        if len(self.children) == 1 and \
                isinstance(self.children[0], PyExpressionNode):
            
            # special case, the attribute contains a single 
            # expression, these are handled by __output__.output_boolean_attr,
            # given the name, and unescaped expression!
            return [ Expr(SimpleCall(
                func=Attribute(
                    value=NameX('__output__'),
                    attr='output_boolean_attr',
                    ctx=Load()
                ),
                args=[
                     Str(s=self.name),
                     self.children[0].get_unescaped_expression()
                ]
            )) ]

        # otherwise just return the output for the attribute code
        # like before
        return self.generate_output_ast(
            [ Str(s=' %s="' % self.name) ] + 
            self.get_expressions() +
            [ Str(s='"') ]
        )


class PyAttrsNode(PythonNode):
    def __init__(self, expression):
        super(PyAttrsNode, self).__init__()
        self.expression = expression
        self.free_variables = FreeVarFinder.for_expression(expression).get_free_variables()


    def generate(self):
        expression = get_expression_ast(self.expression)
        
        output = SimpleCall(
            func=Attribute(
                value=NameX('__tonnikala__'),
                attr='output_attrs',
                ctx=Load()
            ),
            args=[expression]
        )

        return self.generate_output_ast(output)


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
        body = get_expression_ast(
            "for %s in %s: pass" % 
            (self.vars, self.expression),
            'exec'
        )
        for_node      = body[0]
        for_node.body = self.generate_child_ast()
        return [ for_node ]


    def generate_ast(self):
        return self.generate_varscope(self.generate_contents())


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


    def generate_ast(self):
        body = get_expression_ast(
            "def %s:pass" % self.funcspec,
            "exec"
        )
        def_node = body[0]
        def_node.body = self.generate_buffer_frame(
            self.generate_child_ast()
        )
        
        return [ def_node ]


class PyComplexExprNode(PyComplexNode):
    def get_expressions(self):
        return [ i.get_expression() for i in self.children ]


    def generate_ast(self):
        return self.generate_output_ast(self.get_expressions())


class PyRootNode(PyComplexNode):
    def __init__(self):
        super(PyRootNode, self).__init__()


    def generate_ast(self):
        free_variables = self.get_free_variables()
        free_variables.difference_update(ALWAYS_BUILTINS)

        code  = 'def __binder__(__tonnikala__context__):\n'
        code += '    __tonnikala__ = __tonnikala_runtime__\n'
        code += '    __tonnikala__escape__ = __tonnikala__.escape\n'

        for i in free_variables:
            code += '    if "%s" in __tonnikala__context__: %s = __tonnikala__context__["%s"]\n' % (i, i, i)

        code += '    class __Template__(object):\n'
        code += '        def __main__(__self__):\n'
        code += '            __output__ = __tonnikala__.Buffer()\n'
        code += '            return "template_placeholder"\n'
        code += '            return __output__\n'
        code += '    return __Template__()\n'

        tree = ast.parse(code)

        class MainLocator(ast.NodeVisitor):
            found = None
            def visit_FunctionDef(self, node):
                if node.name == '__main__':
                    self.found = node
                else:
                    self.generic_visit(node)

        locator = MainLocator()
        locator.visit(tree)
        main_func = locator.found
        main_func.body[1:2] = self.generate_child_ast()

        ast.fix_missing_locations(tree)

        return tree


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
    UnlessNode      = PyUnlessNode
