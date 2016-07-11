# -*- coding: utf-8 -*-

# notice: this module cannot be sanely written to take use of
# unicode_literals, bc some of the arguments need to be str on
# both python2 and 3
from __future__ import absolute_import, division, print_function

import ast
from ast import *

from collections import Iterable

from .astalyzer import FreeVarFinder
from ..base import LanguageNode, ComplexNode, BaseGenerator
from ...compat import string_types, PY2
from ...helpers import StringWithLocation
from ...runtime.debug import TemplateSyntaxError

try:  # pragma: no cover
    import sysconfig

    HAS_ASSERT = bool(sysconfig.get_config_var('Py_DEBUG'))
    del sysconfig
except ImportError:  # pragma: no cover
    HAS_ASSERT = False

name_counter = 0
ALWAYS_BUILTINS = '''
    False
    True
    None
'''.split()


def simple_call(func, args=None):
    return Call(func=func, args=args or [], keywords=[], starargs=None,
                kwargs=None)


if PY2:  # pragma: python2
    def create_argument_list(arguments):
        return [Name(id=id, ctx=Param()) for id in arguments]

else:  # pragma: python 3
    def create_argument_list(arguments):
        return [arg(arg=id, annotation=None) for id in arguments]


def simple_function_def(name, arguments=()):
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


def adjust_locations(ast_node, first_lineno, first_offset):
    """
    Adjust the locations of the ast nodes, offsetting them
    to the new lineno and column offset
    """

    line_delta = first_lineno - 1

    def _fix(node):
        if 'lineno' in node._attributes:
            lineno = node.lineno
            col = node.col_offset

            # adjust the offset on the first line
            if lineno == 1:
                col += first_offset

            lineno += line_delta

            node.lineno = lineno
            node.col_offset = col

        for child in iter_child_nodes(node):
            _fix(child)

    _fix(ast_node)


def get_fragment_ast(expression, mode='eval', adjust=(0, 0)):
    if not isinstance(expression, string_types):
        return expression

    t = None
    position = getattr(expression, 'position', (1, 0))
    position = position[0] + adjust[0], position[1] + adjust[1]
    try:
        exp = expression
        if expression[-1:] != '\n':
            exp = expression + '\n'
        tree = ast.parse(exp, mode=mode)
    except SyntaxError as e:
        lineno = e.lineno
        lineno += position[0] - 1
        t = TemplateSyntaxError(e.msg, lineno=lineno)

    if t:
        raise t

    adjust_locations(tree, position[0], position[1])
    return tree.body


def gen_name(typename=None):
    global name_counter
    name_counter += 1
    if typename:
        return "__TK__typed__%s__%d__" % (typename, name_counter)
    else:
        return "__TK_%d__" % (name_counter)


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

    def generate_output_ast(self, code, generator, parent, escape=False,
                            position=None):
        func = Name(id='__TK__output', ctx=Load())

        if not isinstance(code, list):
            code = [code]

        rv = []
        for i in code:
            if position is not None:
                i.lineno, i.col_offset = position

            e = Expr(simple_call(func, [i]))
            e.output_args = [i]
            rv.append(e)

        return rv

    def make_buffer_frame(self, body):
        new_body = []
        new_body.append(Assign(
            targets=[
                NameX('__TK__output', store=True),
            ],
            value=simple_call(
                NameX('__TK__mkbuffer')
            )
        ))

        new_body.extend(body)
        new_body.append(Return(value=NameX('__TK__output')))
        return new_body

    def make_function(self, name, body, add_buffer=False, arguments=()):
        # ensure that the function name is an str
        func = simple_function_def(str(name), arguments=arguments)
        new_body = func.body = []

        if add_buffer:
            new_body.extend(self.make_buffer_frame(body))

        else:
            new_body.extend(body)

        if not new_body:
            new_body.append(Pass())

        return func

    def generate_varscope(self, body):
        name = gen_name('variable_scope')
        rv = [
            self.make_function(name, body,
                               arguments=['__TK__output', '__TK__escape']),
            Expr(simple_call(NameX(name),
                             [NameX('__TK__output'), NameX('__TK__escape')]))
        ]
        return rv


class PyOutputNode(PythonNode):
    def __init__(self, text):
        super(PyOutputNode, self).__init__()
        self.text = text

    def get_expressions(self):
        return [self.get_expression()]

    def get_expression(self):
        return Str(s=self.text)

    def generate_ast(self, generator, parent):
        return self.generate_output_ast(self.get_expression(), generator,
                                        parent)


class PyTranslatableOutputNode(PyOutputNode):
    def __init__(self, text, needs_escape=False):
        super(PyTranslatableOutputNode, self).__init__(text)
        self.needs_escape = needs_escape

    def get_expressions(self):
        return [self.get_expression()]

    def get_expression(self):
        name = 'gettext'
        if self.needs_escape:
            name = 'egettext'

        expr = simple_call(
            NameX(name),
            [Str(s=self.text)],
        )
        return expr


class PyExpressionNode(PythonNode):
    def __init__(self, expression):
        super(PyExpressionNode, self).__init__()
        self.expr = expression

    def get_expressions(self):
        return [self.get_expression()]

    def get_expression(self):
        return simple_call(
            NameX('__TK__escape'),
            [self.get_unescaped_expression()]
        )

    def get_unescaped_expression(self):
        return get_fragment_ast(self.expr)

    def generate_ast(self, generator, parent):
        return self.generate_output_ast(self.get_expression(), generator,
                                        parent)


class PyCodeNode(PythonNode):
    def __init__(self, source):
        super(PyCodeNode, self).__init__()
        self.source = source

    def generate_ast(self, generator, parent):
        return get_fragment_ast(self.source, mode='exec')


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
        test = get_fragment_ast(self.expression)
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
        return [node]


def PyUnlessNode(self, expression):
    expression = get_fragment_ast(expression)
    expression = UnaryOp(op=Not(), operand=expression)
    return PyIfNode(expression)


class PyImportNode(PythonNode):
    def __init__(self, href, alias):
        super(PyImportNode, self).__init__()
        self.href = str(href)
        self.alias = str(alias)

    def generate_ast(self, generator, parent):
        node = Assign(
            targets=[NameX(str(self.alias), store=True)],
            value=
            simple_call(
                func=
                Attribute(value=NameX('__TK__runtime', store=False),
                          attr='import_defs', ctx=Load()),
                args=[
                    NameX('__TK__original_context'),
                    Str(s=self.href)
                ]
            )
        )

        if parent.is_top_level:
            generator.add_top_level_import(str(self.alias), node)
            return []

        return [node]


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
            # __TK__output.output_boolean_attr,
            # given the name, and unescaped expression!
            return [Expr(simple_call(
                func=Attribute(
                    value=NameX('__TK__output'),
                    attr='output_boolean_attr',
                    ctx=Load()
                ),
                args=[
                    Str(s=self.name),
                    self.children[0].get_unescaped_expression()
                ]
            ))]

        # otherwise just return the output for the attribute code
        # like before
        return self.generate_output_ast(
            [Str(s=' %s="' % self.name)] +
            self.get_expressions() +
            [Str(s='"')],
            generator, parent
        )


class PyAttrsNode(PythonNode):
    def __init__(self, expression):
        super(PyAttrsNode, self).__init__()
        self.expression = expression

    def generate_ast(self, generator, parent):
        expression = get_fragment_ast(self.expression)

        output = simple_call(
            NameX('__TK__output_attrs'),
            args=[expression]
        )

        return self.generate_output_ast(output, generator, parent)


class PyForNode(PyComplexNode):
    def __init__(self, target_and_expression, parts):
        super(PyForNode, self).__init__()
        self.target_and_expression = target_and_expression

    def generate_contents(self, generator, parent):
        lineno, col = getattr(self.target_and_expression, 'position', (1, 0))

        body = get_fragment_ast(
            StringWithLocation('for %s: pass' % self.target_and_expression,
                               lineno, col - 4),
            'exec',
        )
        for_node = body[0]
        for_node.body = self.generate_child_ast(generator, self)
        return [for_node]

    def generate_ast(self, generator, parent):
        # TODO: this could be needed to be reinstantiated
        # return self.generate_varscope(self.generate_contents())
        return self.generate_contents(generator, parent)


class PyDefineNode(PyComplexNode):
    def __init__(self, funcspec):
        super(PyDefineNode, self).__init__()

        self.position = getattr(funcspec, 'position', (1, 0))

        if '(' not in funcspec:
            funcspec += '()'

        self.funcspec = funcspec

    def generate_ast(self, generator, parent):
        body = get_fragment_ast(
            StringWithLocation('def %s: pass' % self.funcspec,
                               self.position[0], self.position[1] - 4),
            "exec"
        )
        def_node = body[0]
        name = self.funcspec.partition('(')[0]
        def_node.body = self.make_buffer_frame(
            self.generate_child_ast(generator, self)
        )

        # move the function out of the closure
        if parent.is_top_level:
            generator.add_top_def(def_node.name, def_node)
            return []

        return [def_node]


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
        return self.generate_output_ast(self.get_expressions(),
                                        generator, parent)


class PyBlockNode(PyComplexNode):
    def __init__(self, name):
        super(PyBlockNode, self).__init__()
        self.name = name

    def generate_ast(self, generator, parent):
        is_extended = isinstance(parent, PyExtendsNode)

        name = self.name
        blockfunc_name = '__TK__block__%s' % name
        position = getattr(name, 'position', (1, 0))
        body = get_fragment_ast(
            StringWithLocation(
                'def %s():pass' % blockfunc_name,
                position[0], position[1] - 4),
            'exec'
        )
        def_node = body[0]
        def_node.body = self.make_buffer_frame(
            self.generate_child_ast(generator, self)
        )

        if not isinstance(name, str):  # pragma: python2
            name = name.encode('UTF-8')

        generator.add_block(str(name), def_node, blockfunc_name)

        if not is_extended:
            # call the block in place
            return self.generate_output_ast(
                [simple_call(NameX(str(self.name)), [])],
                self,
                parent,
                position=position
            )

        else:
            return []


class PyWithNode(PyComplexNode):
    def __init__(self, vars):
        super(PyWithNode, self).__init__()
        self.vars = vars

    def generate_ast(self, generator, parent=None):
        var_defs = get_fragment_ast(self.vars, 'exec')
        body = var_defs + self.generate_child_ast(generator, self)
        return self.generate_varscope(body)


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
                            if len(output_node.value.args) + len(i.output_args) > 250:
                                coalesce_strs()
                                output_node = i
                            else:
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
            Coalesce __TK__output(__TK__escape(literal(x))) into
            __TK__output(x).
            """
            if not ast_equals(node.func, NameX('__TK__output')):
                return

            for i in range(len(node.args)):
                arg1 = node.args[i]
                if not arg1.__class__.__name__ == 'Call':
                    continue

                if not ast_equals(arg1.func, NameX('__TK__escape')):
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
    Removes locations from the given AST tree completely
    """

    def fix(node):
        if 'lineno' in node._attributes and hasattr(node, 'lineno'):
            del node.lineno

        if 'col_offset' in node._attributes and hasattr(node, 'col_offset'):
            del node.col_offset

        for child in iter_child_nodes(node):
            fix(child)

    fix(node)


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
            main_func = self.make_function('__main__', main_body,
                                           add_buffer=True)
            generator.add_bind_decorator(main_func)

            toplevel_funcs = [main_func] + toplevel_funcs

        # analyze the set of free variables
        free_variables = set()
        for i in toplevel_funcs:
            fv_info = FreeVarFinder.for_ast(i)
            free_variables.update(fv_info.get_free_variables())

        # discard __TK__ variables, always builtin names True, False, None
        # from free variables.
        for i in list(free_variables):
            if i.startswith('__TK__') or i in ALWAYS_BUILTINS:
                free_variables.discard(i)

        # discard the names of toplevel funcs from free variables
        free_variables.difference_update(generator.top_level_names)

        code = '__TK__mkbuffer = __TK__runtime.Buffer\n'
        code += '__TK__escape = __TK__escape_g = __TK__runtime.escape\n'
        code += '__TK__output_attrs = __TK__runtime.output_attrs\n'

        if extended:
            code += '__TK__parent_template = __TK__runtime.load(%r)\n' % \
                    extended

        code += 'def __TK__binder(__TK__context):\n'
        code += '    __TK__original_context = __TK__context.copy()\n'
        code += '    __TK__bind = __TK__runtime.bind(__TK__context)\n'
        code += '    __TK__bindblock = __TK__runtime.bind(__TK__context, ' \
                'block=True)\n'

        if extended:
            # an extended template does not have a __main__ (it is inherited)
            code += '    __TK__parent_template.binder_func(__TK__context)\n'

        for i in ['egettext']:
            if i in free_variables:
                free_variables.add('gettext')
                free_variables.discard(i)

        if 'gettext' in free_variables:
            code += '    def egettext(msg):\n'
            code += '        return __TK__escape(gettext(msg))\n'

        for i in free_variables:
            code += '    if "%s" in __TK__context:\n' % i
            code += '        %s = __TK__context["%s"]\n' % (i, i)

        code += '    return __TK__context\n'

        tree = ast.parse(code)
        remove_locations(tree)

        class LocatorAndTransformer(ast.NodeTransformer):
            binder = None

            def visit_FunctionDef(self, node):
                if node.name == '__TK__binder' and not self.binder:
                    self.binder = node

                self.generic_visit(node)
                return node

        locator = LocatorAndTransformer()
        locator.visit(tree)

        # inject the other top level funcs in the binder
        binder = locator.binder
        binder.body[3:3] = toplevel_funcs
        binder.body[3:3] = generator.imports

        coalesce_outputs(tree)
        return tree


# noinspection PyProtectedMember
class LocationMapper(object):
    def __init__(self):
        self.lineno_map = {1: 1}
        self.prev_original_line = 1
        self.prev_mapped_line = 1
        self.prev_column = 0

    def map_linenos(self, node):
        if 'lineno' in node._attributes:
            if hasattr(node, 'lineno'):
                if node.lineno != self.prev_original_line:
                    self.prev_mapped_line += 1
                    self.lineno_map[self.prev_mapped_line] = node.lineno
                    self.prev_original_line = node.lineno

            node.lineno = self.prev_mapped_line

        if 'col_offset' in node._attributes:
            if hasattr(node, 'col_offset'):
                self.prev_column = node.col_offset

            node.col_offset = self.prev_column

        for child in iter_child_nodes(node):
            self.map_linenos(child)


class Generator(BaseGenerator):
    OutputNode = PyOutputNode
    TranslatableOutputNode = PyTranslatableOutputNode

    IfNode = PyIfNode
    ForNode = PyForNode
    DefineNode = PyDefineNode
    ComplexExprNode = PyComplexExprNode
    ExpressionNode = PyExpressionNode
    ImportNode = PyImportNode
    RootNode = PyRootNode
    AttributeNode = PyAttributeNode
    AttrsNode = PyAttrsNode
    UnlessNode = PyUnlessNode
    ExtendsNode = PyExtendsNode
    BlockNode = PyBlockNode
    CodeNode = PyCodeNode
    WithNode = PyWithNode

    def __init__(self, ir_tree):
        super(Generator, self).__init__(ir_tree)
        self.blocks = []
        self.top_defs = []
        self.top_level_names = set()
        self.extended_href = None
        self.imports = []
        self.lnotab = None

    def add_bind_decorator(self, func, block=True):
        binder_call = NameX('__TK__bind' + ('block' if block else ''))
        decors = [binder_call]
        func.decorator_list = decors

    def add_block(self, name, blockfunc, blockfunc_name):
        self.top_level_names.add(blockfunc_name)
        self.add_bind_decorator(blockfunc, block=True)
        self.blocks.append(blockfunc)

    def add_top_def(self, name, defblock):
        self.top_level_names.add(name)
        self.add_bind_decorator(defblock)
        self.top_defs.append(defblock)

    def add_top_level_import(self, name, node):
        self.top_level_names.add(name)
        self.imports.append(node)

    def make_extended_template(self, href):
        self.extended_href = href

    def lnotab_info(self):
        return self.lnotab

    def generate_ast(self):
        tree = super(Generator, self).generate_ast()
        loc_mapper = LocationMapper()
        loc_mapper.map_linenos(tree)
        self.lnotab = loc_mapper.lineno_map
        return tree
