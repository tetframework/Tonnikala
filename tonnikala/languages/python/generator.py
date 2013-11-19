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
import ast
from six import string_types

name_counter = 0
ALWAYS_BUILTINS = '''
    False
    True
    None
'''.split()


def SimpleCall(func, args=None):
    return Call(func=func, args=args or [], keywords=[], starargs=None, kwargs=None)


try:
    unicode
    def create_argument_list(arguments):
        return [ Name(id=id, ctx=Param()) for id in arguments ]
        
except:
    def create_argument_list(arguments):
        return [ arg(arg=id, annotation=None) for id in arguments ]

def SimpleFunctionDef(name, arguments=None):
    arguments = create_argument_list(arguments)
    return FunctionDef(
        name=name,
        args=ast.arguments(
            args=arguments,
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


def gen_name():
    global name_counter
    name_counter += 1
    return "__tk_%d__" % name_counter


def static_eval(expr):
    if isinstance(expr, UnaryOp) and isinstance(expr.op, Not):
        return not static_eval(expr.operand)

    return literal_eval(expr)


def static_expr_to_bool(expr):
    try:
        return bool(static_eval(expr))
    except:
        return None

class PythonNode(LanguageNode):
    def __init__(self, *a, **kw):
        super(PythonNode, self).__init__(*a, **kw)
        self.free_variables = set()
        self.masked_variables = set()
        self.generated_variables = set()


    def generate_output_ast(self, code, escape=False):
        func = Name(id='__tk__output__', ctx=Load())

        if not isinstance(code, list):
            code = [ code ]

        rv = []
        for i in code:
            e = Expr(SimpleCall(func, [i]))
            e.output_args = [i]
            rv.append(e)
        return rv


    def generate_buffer_frame(self, body):
        new_body = []
        new_body.append(Assign(
            targets=[
                Tuple(elts=[
                    NameX('__tk__output__', store=True),
                    NameX('__tk__buffer__', store=True)
                ], ctx=Store())
            ],
            value=SimpleCall(
                NameX('__tk__mkbuffer__')
            )
        ))

        new_body.extend(body)
        new_body.append(Return(value=NameX('__tk__buffer__')))
        return new_body


    def generate_function(self, name, body, add_buffer=False, arguments=None):
        func = SimpleFunctionDef(name, arguments=arguments)
        new_body = func.body = [ ]
             
        if add_buffer:
            new_body.extend(self.generate_buffer_frame(body))

        else:
            new_body.extend(body)

        if not new_body:
            new_body.append(Pass())

        return func


    def generate_varscope(self, body):
        name = gen_name()
        rv = [
            self.generate_function(name, body, 
                arguments=['__tk__output__', '__tk__escape__']),
            Expr(SimpleCall(NameX(name), [ NameX('__tk__output__'), NameX('__tk__escape__') ]))
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
            NameX('__tk__escape__'),
            [ self.get_unescaped_expression() ]
        )


    def get_unescaped_expression(self):
        return get_expression_ast(self.expr)


    def generate_ast(self):
        return self.generate_output_ast(self.get_expression())


def coalesce_strings(args):
    rv = []
    str_on = None

    for i in args:
        if isinstance(i, Str):
            if str_on:
                str_on.s += i.s
                continue
            str_on = i

        else:
            str_on = None
        rv.append(i)

    return rv

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
        test = get_expression_ast(self.expression)
        boolean = static_expr_to_bool(test)

        if boolean == False:
            return []

        if boolean == True:
            return self.generate_child_ast()

        node = If(
           test=test,
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
            # expression, these are handled by
            # __tk__output__.output_boolean_attr,
            # given the name, and unescaped expression!
            return [ Expr(SimpleCall(
                func=Attribute(
                    value=NameX('__tk__buffer__'),
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
            NameX('__tk__output_attrs__'),
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
        # return self.generate_varscope(self.generate_contents())
        return self.generate_contents()


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
        def_node.is_pydef = True

        return [ def_node ]


class PyComplexExprNode(PyComplexNode):
    def get_expressions(self):
        return [ i.get_expression() for i in self.children ]


    def generate_ast(self):
        return self.generate_output_ast(self.get_expressions())


def ast_equals(tree1, tree2):
    x1 = ast.dump(tree1)
    x2 = ast.dump(tree2)
    print(x1, x2)
    return x1 == x2

def coalesce_outputs(tree):
    """
    Coalesce the constant output expressions 
        __output__('foo')
        __output__('bar')
    into
        __output__('foobar')
    """

    class OutputCoalescer(NodeVisitor):
        def visit(self, node):
            if hasattr(node, 'body'):
                # coalesce continuous string output nodes
                new_body = []
                str_output_node = None

                for i in node.body:
                    if hasattr(i, 'output_args') and \
                            isinstance(i.output_args[0], Str):

                        if str_output_node:
                            str_output_node.output_args[0].s += \
                                i.output_args[0].s

                            continue

                        else:
                            str_output_node = i
                    else:
                        str_output_node = None

                    new_body.append(i)

                node.body = new_body

            NodeVisitor.visit(self, node)

        def check(self, node):
            print("check 0\n")
            if not ast_equals(node.func, NameX('__tk__output__')):
                return

            print("check 1\n")
            if len(node.args) != 1:
                return

            print("check 1\n")
            arg1 = node.args[0]
            if not arg1.__class__.__name__ == 'Call':
                return

            if not ast_equals(arg1.func, NameX('__tk__escape__')):
                return

            if len(arg1.args) != 1:
                return

            print("check 2\n")
            arg2 = arg1.args[0]
            if not arg2.__class__.__name__ == 'Call':
                return

            if not ast_equals(arg2.func, NameX('literal')):
                return

            if len(arg2.args) != 1:
                return

            node.args = arg2.args

        def visit_Call(self, node):
            self.check(node)
            self.generic_visit(node)

    OutputCoalescer().visit(tree)

class PyRootNode(PyComplexNode):
    def __init__(self):
        super(PyRootNode, self).__init__()


    def generate_ast(self):
        free_variables = self.get_free_variables()
        free_variables.difference_update(ALWAYS_BUILTINS)

        code  = 'def __tk__mkbuffer__():\n'
        code += '    buffer = __tonnikala__.Buffer()\n'
        code += '    return buffer.output, buffer\n'
        code += '__tk__escape__ = __tk__escape_g__ = __tonnikala__.escape\n'
        code += '__tk__output_attrs__ = __tonnikala__.output_attrs\n'
        code += 'def __tk__binder__(__tk__context__):\n'

        for i in free_variables:
            code += '    if "%s" in __tk__context__:\n' % i
            code += '        %s = __tk__context__["%s"]\n' % (i, i)

        code += '    class __tk__template__(object):\n'
        code += '        def __main__(__tk__self__):\n'
        code += '            __tk__escape__ = __tk__escape_g__\n'
        code += '            __tk__output__, __tk__buffer__ = __tk__mkbuffer__()\n'
        code += '            return "template_placeholder"\n'
        code += '            return __tk__buffer__\n'
        code += '    return __tk__template__()\n'

        tree = ast.parse(code)

        class MainLocator(ast.NodeVisitor):
            main   = None
            binder = None
            template_class = None

            def visit_FunctionDef(self, node):
                if node.name == '__main__':
                    self.main = node

                if node.name == '__tk__binder__':
                    self.binder = node

                self.generic_visit(node)

            def visit_ClassDef(self, node):
                if node.name == '__tk__template__':
                    self.template_class = node

                self.generic_visit(node)

        locator = MainLocator()
        locator.visit(tree)

        main_body = self.generate_child_ast()

        pydef_funcs = [ i for i in main_body
            if getattr(i, 'is_pydef', False) ]

        main_body = [ i for i in main_body
            if not getattr(i, 'is_pydef', False) ]

        # inject the main body in the main func
        main_func = locator.main
        main_func.body[2:3] = main_body

        # inject the other top level funcs in the binder
        binder = locator.binder
        binder.body[:0] = pydef_funcs

        pydef_func_names = [ i.name for i in pydef_funcs ]
        template_class = locator.template_class

        function_injections = []

        # create injections within class body
        for i in pydef_func_names:
            function_injections.append(
                Assign(
                    [Attribute(
                        value=NameX('__tk__template__'),
                        attr=i,
                        ctx=Store()
                    )],
                    SimpleCall(
                        NameX('staticmethod'),
                        [NameX(i)]
                    )
                )
            )

        binder.body[-1:-1] = function_injections

        coalesce_outputs(tree)
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
