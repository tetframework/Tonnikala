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
    is_top_level = False

    def __init__(self, *a, **kw):
        super(PythonNode, self).__init__(*a, **kw)
        self.free_variables = set()
        self.masked_variables = set()
        self.generated_variables = set()


    def generate_output_ast(self, code, generator, parent, escape=False):
        func = Name(id='__tk__output__', ctx=Load())

        if not isinstance(code, list):
            code = [ code ]

        rv = []
        for i in code:
            e = Expr(SimpleCall(func, [i]))
            e.output_args = [i]
            rv.append(e)
        return rv


    def make_buffer_frame(self, body):
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


    def make_function(self, name, body, add_buffer=False, arguments=None):
        func = SimpleFunctionDef(name, arguments=arguments)
        new_body = func.body = [ ]
             
        if add_buffer:
            new_body.extend(self.make_buffer_frame(body))

        else:
            new_body.extend(body)

        if not new_body:
            new_body.append(Pass())

        return func


    def generate_varscope(self, body):
        name = gen_name()
        rv = [
            self.make_function(name, body, 
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


    def generate_ast(self, generator, parent):
        return self.generate_output_ast(self.get_expression(), generator, parent)


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


    def generate_ast(self, generator, parent):
        return self.generate_output_ast(self.get_expression(), generator, parent)


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
    def generate_child_ast(self, generator, parent_for_children):
        rv = []
        for i in self.children:
            rv.extend(i.generate_ast(generator, parent_for_children))

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


    def generate_ast(self, generator, parent):
        test = get_expression_ast(self.expression)
        boolean = static_expr_to_bool(test)

        if boolean == False:
            return []

        if boolean == True:
            return self.generate_child_ast(generator, parent)

        node = If(
           test=test,
           body=self.generate_child_ast(generator, self),
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


    def generate_ast(self, generator, parent):
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


    def generate_ast(self, generator, parent):
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
            [ Str(s='"') ],
            generator, parent
        )


class PyAttrsNode(PythonNode):
    def __init__(self, expression):
        super(PyAttrsNode, self).__init__()
        self.expression = expression
        self.free_variables = FreeVarFinder.for_expression(expression).get_free_variables()


    def generate_ast(self, generator, parent):
        expression = get_expression_ast(self.expression)

        output = SimpleCall(
            NameX('__tk__output_attrs__'),
            args=[expression]
        )

        return self.generate_output_ast(output, generator, parent)


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


    def generate_contents(self, generator, parent):
        body = get_expression_ast(
            "for %s in %s: pass" %
            (self.vars, self.expression),
            'exec'
        )
        for_node      = body[0]
        for_node.body = self.generate_child_ast(generator, self)
        return [ for_node ]


    def generate_ast(self, generator, parent):
        # return self.generate_varscope(self.generate_contents())
        return self.generate_contents(generator, parent)


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


    def generate_ast(self, generator, parent):
        body = get_expression_ast(
            "def %s:pass" % self.funcspec,
            "exec"
        )
        def_node = body[0]
        def_node.body = self.make_buffer_frame(
            self.generate_child_ast(generator, self),
        )

        # move the function out of the closure
        if parent.is_top_level:
            generator.add_top_def(def_node)
            return []           

        return [ def_node ]


class PyComplexExprNode(PyComplexNode):
    def get_expressions(self):
        return [ i.get_expression() for i in self.children ]


    def generate_ast(self, generator, parent=None):
        return self.generate_output_ast(self.get_expressions(), generator, parent)


class PyBlockNode(PyComplexNode):
    def __init__(self, name):
        super(PyBlockNode, self).__init__()
        self.name = name


    def generate_ast(self, generator, parent):
        is_extended = isinstance(parent, PyExtendsNode)

        body = get_expression_ast(
            "def %s():pass" % self.name,
            "exec"
        )
        def_node = body[0]
        def_node.body = self.make_buffer_frame(
            self.generate_child_ast(generator, self)
        )

        generator.add_block(def_node)

        if not is_extended:
            # call the block in place
            return self.generate_output_ast(
                [ SimpleCall(NameX(self.name), []) ],
                self, parent
            )

        else:
            return [ ]


class PyExtendsNode(PyComplexNode):
    is_top_level = True

    def __init__(self, href):
        super(PyExtendsNode, self).__init__()
        self.href = href

    def generate_ast(self, generator, parent=None):
        return self.generate_child_ast(generator, self)


def ast_equals(tree1, tree2):
    x1 = ast.dump(tree1)
    x2 = ast.dump(tree2)
    return x1 == x2


def coalesce_outputs(tree):
    """
    Coalesce the constant output expressions

        __output__('foo')
        __output__('bar')
        __output__(baz)
        __output__('xyzzy')

    into

        __output__('foobar', baz, 'xyzzy')
    """

    coalesce_all_outputs = True
    if coalesce_all_outputs:
        should_coalesce = lambda n: True
    else:
        should_coalesce = lambda n: n.output_args[0].__class__ is Str

    class OutputCoalescer(NodeVisitor):
        def visit(self, node):
            if hasattr(node, 'body'):
                # coalesce continuous string output nodes
                new_body = []
                output_node = None

                def coalesce_strs():
                    if output_node:
                        output_node.value.args[:] = \
                            coalesce_strings(output_node.value.args)

                for i in node.body:
                    if hasattr(i, 'output_args') and should_coalesce(i):
                        if output_node:
                            output_node.value.args.extend(i.output_args)                            
                            continue

                        output_node = i

                    else:
                        coalesce_strs()
                        output_node = None

                    new_body.append(i)

                coalesce_strs()
                node.body[:] = new_body

            NodeVisitor.visit(self, node)

        def check(self, node):
            if not ast_equals(node.func, NameX('__tk__output__')):
                return

            for i in range(len(node.args)):
                arg1 = node.args[i]
                if not arg1.__class__.__name__ == 'Call':
                    continue

                if not ast_equals(arg1.func, NameX('__tk__escape__')):
                    continue

                if len(arg1.args) != 1:
                    continue

                arg2 = arg1.args[0]
                if not arg2.__class__.__name__ == 'Call':
                    continue

                if not ast_equals(arg2.func, NameX('literal')):
                    continue

                if len(arg2.args) != 1:
                    continue

                node.args[i] = arg2.args[0]

        def visit_Call(self, node):
            self.check(node)
            self.generic_visit(node)

    OutputCoalescer().visit(tree)


class PyRootNode(PyComplexNode):
    def __init__(self):
        super(PyRootNode, self).__init__()


    is_top_level = True


    def get_extends_node(self):
        if len(self.children) == 1 and \
                isinstance(self.children[0], PyExtendsNode):
            return self.children[0]

        return None


    def generate_ast(self, generator, parent=None):
        main_body = self.generate_child_ast(generator, self)

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

        extended = self.get_extends_node()
        if extended:
            code += '    __tk__base_template__ = __tk__load__(%s)' % repr(extended.href)
            code += '    class __tk__template__(__tk__base_template__):'
            code += '        pass'
        else:
            code += '    class __tk__template__(object):\n'
            code += '        def __main__(__tk__self__):\n'
            code += '            __tk__escape__ = __tk__escape_g__\n'
            code += '            __tk__output__, __tk__buffer__ = __tk__mkbuffer__()\n'
            code += '            "template_placeholder"\n'
            code += '            return __tk__buffer__\n'

        code += '    return __tk__template__()\n'

        tree = ast.parse(code)

        class LocatorAndTransformer(ast.NodeTransformer):
            main   = None
            binder = None
            template_class = None

            def visit_FunctionDef(self, node):
                if node.name == '__main__' and not self.main:
                    self.main = node

                if node.name == '__tk__binder__' and not self.binder:
                    self.binder = node

                self.generic_visit(node)
                return node

            def visit_ClassDef(self, node):
                if node.name == '__tk__template__':
                    self.template_class = node

                self.generic_visit(node)
                return node

        locator = LocatorAndTransformer()
        locator.visit(tree)

        if main_body and locator.main:
            # inject the main body in the main func
            main_func = locator.main
            main_func.body[2:3] = main_body

        # inject the other top level funcs in the binder
        binder = locator.binder
        toplevel_funcs = generator.blocks + generator.top_defs
        binder.body[:0] = toplevel_funcs

        pydef_func_names = [ i.name for i in toplevel_funcs ]
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
    ExtendsNode     = PyExtendsNode
    BlockNode       = PyBlockNode

    def __init__(self, ir_tree):
        super(Generator, self).__init__(ir_tree)
        self.blocks        = []
        self.top_defs      = []
        self.extended_href = None

    def add_block(self, block):
        self.blocks.append(block)

    def add_top_def(self, defblock):
        self.top_defs.append(defblock)

    def make_extended_template(self, href):
        self.extended_href = href
