# -*- coding: utf-8 -*-

# notice: this module cannot be sanely written to take use of
# unicode_literals, bc some of the arguments need to be str on
# both python2 and 3
from __future__ import absolute_import, division, print_function

import warnings
from tonnikala.languages.base import LanguageNode, ComplexNode, BaseGenerator
from tonnikala.languages.python.astalyzer import FreeVarFinder
from ast import *
from collections import Iterable
import ast
from six import string_types

HAS_ASSERT = False
try:
    import sysconfig
    HAS_ASSERT = bool(sysconfig.get_config_var('Py_DEBUG'))
except:
    pass

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

def SimpleFunctionDef(name, arguments=()):
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


    def generate_output_ast(self, code, generator, parent, escape=False):
        func = Name(id='_TK_output', ctx=Load())

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
                 NameX('_TK_output', store=True),
            ],
            value=SimpleCall(
                NameX('_TK_mkbuffer')
            )
        ))

        new_body.extend(body)
        new_body.append(Return(value=NameX('_TK_output')))
        return new_body


    def make_function(self, name, body, add_buffer=False, arguments=()):
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
                arguments=['_TK_output', '_TK_escape']),
            Expr(SimpleCall(NameX(name), [ NameX('_TK_output'), NameX('_TK_escape') ]))
        ]
        return rv


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


class PyTranslatableOutputNode(PyOutputNode):
    def __init__(self, text, needs_escape=False):
        super(PyTranslatableOutputNode, self).__init__(text)
        self.needs_escape = needs_escape


    def get_expressions(self):
        return [ self.get_expression() ]


    def get_expression(self):
        name = 'gettext'
        if self.needs_escape:
            name = 'egettext'

        expr = SimpleCall(
            NameX(name),
            [Str(s=self.text)],
        )
        return expr


class PyExpressionNode(PythonNode):
    def __init__(self, expression, tokens):
        super(PyExpressionNode, self).__init__()
        self.expr = expression
        self.tokens = tokens


    def get_expressions(self):
        return [ self.get_expression() ]


    def get_expression(self):
        return SimpleCall(
            NameX('_TK_escape'),
            [ self.get_unescaped_expression() ]
        )


    def get_unescaped_expression(self):
        return get_expression_ast(self.expr)


    def generate_ast(self, generator, parent):
        return self.generate_output_ast(self.get_expression(), generator, parent)


class PyCodeNode(PythonNode):

    def __init__(self, source):
        super(PyCodeNode, self).__init__()
        self.source = source

    def generate_ast(self, generator, parent):
        return get_expression_ast(self.source, mode='exec')


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


class PyIfNode(PyComplexNode):
    def __init__(self, expression):
        super(PyIfNode, self).__init__()
        self.expression = expression


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


    def generate_ast(self, generator, parent):
        node = Assign(
            targets = [NameX(str(self.alias), store=True)],
            value =
                SimpleCall(
                    func=
                        Attribute(value=NameX('_TK_runtime', store=False),
                                  attr='import_defs', ctx=Load()),
                    args=[
                        NameX('_TK_original_context'),
                        Str(s=self.href)
                    ]
                )
        )

        if parent.is_top_level:
            generator.add_top_level_import(str(self.alias), node)
            return []

        return [ node ]


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
            # _TK_output.output_boolean_attr,
            # given the name, and unescaped expression!
            return [ Expr(SimpleCall(
                func=Attribute(
                    value=NameX('_TK_output'),
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


    def generate_ast(self, generator, parent):
        expression = get_expression_ast(self.expression)

        output = SimpleCall(
            NameX('_TK_output_attrs'),
            args=[expression]
        )

        return self.generate_output_ast(output, generator, parent)


class PyForNode(PyComplexNode):
    def __init__(self, vars, expression):
        super(PyForNode, self).__init__()
        self.vars = vars
        self.expression = expression


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
            generator.add_top_def(def_node.name, def_node)
            return []

        return [ def_node ]


class PyComplexExprNode(PyComplexNode):
    def get_expressions(self):
        rv = []
        for i in self.children:
            if hasattr(i, 'get_expression'):
                rv.append(i.get_expression())

            else:
                rv.extend(i.get_expressions())

        return rv


    def generate_ast(self, generator, parent=None):
        return self.generate_output_ast(self.get_expressions(), generator, parent)


class PyBlockNode(PyComplexNode):
    def __init__(self, name):
        super(PyBlockNode, self).__init__()
        if not isinstance(name, str):
            name = name.encode('UTF-8') # python 2

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

        generator.add_block(self.name, def_node)

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
        generator.make_extended_template(self.href)
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
            # if - else expression also has a body! it is not we want, though.
            if hasattr(node, 'body') and isinstance(node.body, Iterable):
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
            """
            Coalesce _TK_output(_TK_escape(literal(x))) into
            _TK_output(x).
            """
            if not ast_equals(node.func, NameX('_TK_output')):
                return

            for i in range(len(node.args)):
                arg1 = node.args[i]
                if not arg1.__class__.__name__ == 'Call':
                    continue

                if not ast_equals(arg1.func, NameX('_TK_escape')):
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


def remove_locations(node):
    """
    When you compile a node tree with compile(), the compiler expects lineno and
    col_offset attributes for every node that supports them.  This is rather
    tedious to fill in for generated nodes, so this helper adds these attributes
    recursively where not already set, by setting them to the values of the
    parent node.  It works recursively starting at *node*.
    """

    def _fix(node):
        if 'lineno' in node._attributes:
            node.lineno = 1

        if 'col_offset' in node._attributes:
            node.col_offset = 0

        for child in iter_child_nodes(node):
            _fix(child)

    _fix(node)


class PyRootNode(PyComplexNode):
    def __init__(self):
        super(PyRootNode, self).__init__()


    is_top_level = True

    def generate_ast(self, generator, parent=None):
        main_body = self.generate_child_ast(generator, self)

        extended = generator.extended_href

        toplevel_funcs = generator.blocks + generator.top_defs
        # do not generate __main__ for extended templates
        if not extended:
            main_func = self.make_function('__main__', main_body, add_buffer=True)
            generator.add_bind_decorator(main_func)

            toplevel_funcs = [ main_func ] + toplevel_funcs

        # analyze the set of free variables
        free_variables = set()
        for i in toplevel_funcs:
            fv_info = FreeVarFinder.for_ast(i)
            free_variables.update(fv_info.get_free_variables())

        # discard _TK_ variables, always builtin names True, False, None
        # from free variables.
        for i in list(free_variables):
            if i.startswith('_TK_') or i in ALWAYS_BUILTINS:
                free_variables.discard(i)

        # discard the names of toplevel funcs from free variables
        free_variables.difference_update(generator.top_level_names)

        code  = '_TK_mkbuffer = _TK_runtime.Buffer\n'
        code += '_TK_escape = _TK_escape_g = _TK_runtime.escape\n'
        code += '_TK_output_attrs = _TK_runtime.output_attrs\n'

        if extended:
            code += '_TK_parent_template = _TK_runtime.load(%r)\n' % extended

        code += 'def _TK_binder(_TK_context):\n'
        code += '    _TK_original_context = _TK_context.copy()\n'
        code += '    _TK_bind = _TK_runtime.bind(_TK_context)\n'

        if extended:
            # an extended template does not have a __main__ (it is inherited)
            code += '    _TK_parent_template.binder_func(_TK_context)\n'

        for i in [ 'egettext' ]:
            if i in free_variables:
                free_variables.add('gettext')
                free_variables.discard(i)

        if 'gettext' in free_variables:
            code += '    def egettext(msg):\n'
            code += '        return _TK_escape(gettext(msg))\n'

        for i in free_variables:
            code += '    if "%s" in _TK_context:\n' % i
            code += '        %s = _TK_context["%s"]\n' % (i, i)

        code += '    return _TK_context\n'

        tree = ast.parse(code)

        class LocatorAndTransformer(ast.NodeTransformer):
            main   = None
            binder = None

            def visit_FunctionDef(self, node):
                if node.name == '__main__' and not self.main:
                    self.main = node

                if node.name == '_TK_binder' and not self.binder:
                    self.binder = node

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
        binder.body[2:2] = toplevel_funcs
        binder.body[2:2] = generator.imports

        coalesce_outputs(tree)
        if HAS_ASSERT:
            remove_locations(tree)
        else:
            fix_missing_locations(tree)

        return tree


class Generator(BaseGenerator):
    OutputNode             = PyOutputNode
    TranslatableOutputNode = PyTranslatableOutputNode

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
    CodeNode        = PyCodeNode

    def __init__(self, ir_tree):
        super(Generator, self).__init__(ir_tree)
        self.blocks          = []
        self.top_defs        = []
        self.top_level_names = set()
        self.extended_href   = None
        self.imports         = []

    def add_bind_decorator(self, block):
        binder_call = NameX('_TK_bind')
        decors = [ binder_call ]
        block.decorator_list = decors

    def add_block(self, name, block):
        self.top_level_names.add(name)
        self.add_bind_decorator(block)
        self.blocks.append(block)

    def add_top_def(self, name, defblock):
        self.top_level_names.add(name)
        self.add_bind_decorator(defblock)
        self.top_defs.append(defblock)

    def add_top_level_import(self, name, node):
        self.top_level_names.add(name)
        self.imports.append(node)

    def make_extended_template(self, href):
        self.extended_href = href

