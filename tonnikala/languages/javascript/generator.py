# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals

import json
import warnings
from tonnikala.languages.base import LanguageNode, ComplexNode, BaseGenerator

from slimit.parser import Parser
from slimit import ast
from slimit.ast import *
from collections import Iterable
from slimit.scope import SymbolTable
from slimit.parser import Parser
from slimit.visitors.scopevisitor import (
    Visitor,
    ScopeTreeVisitor,
    fill_scope_references,
    mangle_scope_tree,
    NameManglerVisitor,
    )
from ...compat import string_types
from ...runtime.debug import TemplateSyntaxError


class FreeVariableAnalyzerVisitor(Visitor):
    """Mangles names.

    Walks over a parsed tree and changes ID values to corresponding
    mangled names.
    """

    def __init__(self):
        self.free_variables = set()

    @staticmethod
    def _is_mangle_candidate(id_node):
        """Return True if Identifier node is a candidate for mangling.

        There are 5 cases when Identifier is a mangling candidate:
        1. Function declaration identifier
        2. Function expression identifier
        3. Function declaration/expression parameter
        4. Variable declaration identifier
        5. Identifier is a part of an expression (primary_expr_no_brace rule)
        """
        return getattr(id_node, '_mangle_candidate', False)

    def visit_Identifier(self, node):
        """Mangle names."""

        if not self._is_mangle_candidate(node):
            return

        name = node.value
        symbol = node.scope.resolve(node.value)
        if symbol is None:
            self.free_variables.add(name)


try:
    import sysconfig
    HAS_ASSERT = bool(sysconfig.get_config_var('Py_DEBUG'))
    del sysconfig
except ImportError:
    HAS_ASSERT = False

name_counter = 0
ALWAYS_BUILTINS = '''
    undefined
'''.split()


def Str(s):
    return String(json.dumps(s, ensure_ascii=False))

def Name(id, ctx=None):
    return Identifier(id)

def Load():
    pass

Store = Load
Expr = ExprStatement


def Attribute(value, attr, ctx=None):
    return DotAccessor(value, Name(attr))


def SimpleCall(func, args=None):
    # bad naming?
    return FunctionCall(identifier=func, args=args)

JSAssign = Assign
def Assign(targets, value):
    if len(targets) != 1:
        raise TypeError("Only single assignments supported")

    return JSAssign(op='=', left=targets[0], right=value)

def AssignNewVariable(targets, value):
    return VarStatement([VarDecl(targets[0], value)])

JSReturn = Return
def Return(value=None):
    return JSReturn(expr=value)


def SimpleFunctionDef(name, arguments=()):
    arguments = list(arguments)
    return FuncDecl(
        identifier=Name(name),
        parameters=arguments,
        elements=[]
    )


def assign_func_body(funcdecl, new_body=None):
    funcdecl.elements = [] if new_body is None else new_body
    return new_body


def get_body(funcdecl):
    return funcdecl.elements


def NameX(id, store=False):
    return Name(id=id, ctx=Load() if not store else Store())


class FreeVarFinder(object):
    def __init__(self, tree):
        self.tree = tree

    @classmethod
    def for_ast(cls, tree):
        return cls(tree)

    def get_free_variables(self):
        sym_table = SymbolTable()
        visitor = ScopeTreeVisitor(sym_table)
        visitor.visit(self.tree)
        fill_scope_references(self.tree)

        free_var_analysis = FreeVariableAnalyzerVisitor()
        free_var_analysis.visit(self.tree)
        return free_var_analysis.free_variables


def parse(expression, mode='eval'):
    if mode == 'eval':
        return Parser().parse(expression).children()[0].expr
    elif mode == 'exec':
        return Parser().parse(expression).children()

    raise TypeError("Only eval, exec modes allowed")


def get_fragment_ast(expression, mode='eval'):
    if not isinstance(expression, string_types):
        return expression

    tree = parse(expression, mode=mode)
    return tree


def get_func_name(func):
    return func.identifier.value


def gen_name():
    global name_counter
    name_counter += 1
    return "__TK__%d__" % name_counter


def static_eval(expr):
    if isinstance(expr, UnaryOp) and isinstance(expr.op, Not):
        return not static_eval(expr.operand)

    return literal_eval(expr)


def static_expr_to_bool(expr):
    try:
        return bool(static_eval(expr))
    except:
        return None


class JavascriptNode(LanguageNode):
    is_top_level = False

    def generate_output_ast(self, code, generator, parent, escape=False):
        func = Name(id='__TK__output', ctx=Load())

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
        new_body.append(AssignNewVariable(
            targets=[
                 NameX('__TK__output', store=True),
            ],
            value=SimpleCall(
                NameX('__TK__mkbuffer')
            )
        ))

        new_body.extend(body)
        new_body.append(Return(value=NameX('__TK__output')))
        return new_body


    def make_function(self, name, body, add_buffer=False, arguments=()):
        func = SimpleFunctionDef(name, arguments=arguments)
        new_body = assign_func_body(func, [])

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
            self.make_function(name, body),
            Expr(SimpleCall(NameX(name), []))
        ]
        return rv


class JsOutputNode(JavascriptNode):
    def __init__(self, text):
        super(JsOutputNode, self).__init__()
        self.text = text


    def get_expressions(self):
        return [ self.get_expression() ]


    def get_expression(self):
        return Str(s=(self.text))


    def generate_ast(self, generator, parent):
        return self.generate_output_ast(self.get_expression(), generator, parent)


class JsTranslatableOutputNode(JsOutputNode):
    def __init__(self, text, needs_escape=False):
        super(JsTranslatableOutputNode, self).__init__(text)
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


class JsExpressionNode(JavascriptNode):
    def __init__(self, expression):
        super(JsExpressionNode, self).__init__()
        self.expr = expression


    def get_expressions(self):
        return [ self.get_expression() ]


    def get_expression(self):
        return SimpleCall(
            NameX('__TK__escape'),
            [ self.get_unescaped_expression() ]
        )


    def get_unescaped_expression(self):
        return get_fragment_ast(self.expr)


    def generate_ast(self, generator, parent):
        return self.generate_output_ast(self.get_expression(), generator, parent)


class JsCodeNode(JavascriptNode):
    def __init__(self, source):
        super(JsCodeNode, self).__init__()
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


class JsComplexNode(ComplexNode, JavascriptNode):
    def generate_child_ast(self, generator, parent_for_children):
        rv = []
        for i in self.children:
            rv.extend(i.generate_ast(generator, parent_for_children))

        return rv


class JsIfNode(JsComplexNode):
    def __init__(self, expression):
        super(JsIfNode, self).__init__()
        self.expression = expression


    def generate_ast(self, generator, parent):
        test = get_fragment_ast(self.expression)
        boolean = static_expr_to_bool(test)

        if boolean == False:
            return []

        if boolean == True:
            return self.generate_child_ast(generator, parent)

        node = If(
           test,
           Block(self.generate_child_ast(generator, self)),
        )
        return [ node ]


def JsUnlessNode(self, expression):
    expression = get_fragment_ast(expression)
    expression = UnaryOp(op='!', value=expression)
    return JsIfNode(expression)


class JsImportNode(JavascriptNode):
    def __init__(self, href, alias):
        super(JsImportNode, self).__init__()
        self.alias = alias
        self.href = href


    def generate_ast(self, generator, parent):
        node = Assign(
            targets = [NameX(str(self.alias), store=True)],
            value =
                SimpleCall(
                    func=
                        Attribute(value=NameX('__TK__', store=False),
                                  attr='importDefs', ctx=Load()),
                    args=[
                        NameX('__TK__context'),
                        Str(s=self.href)
                    ]
                )
        )

        generator.add_import_source(self.href)
        if parent.is_top_level:
            generator.add_top_level_import(str(self.alias), node)
            return []

        return [ node ]


class JsAttributeNode(JsComplexNode):
    def __init__(self, name, value):
        super(JsAttributeNode, self).__init__()
        self.name = name


    def get_expressions(self):
        rv = []
        for i in self.children:
            rv.extend(i.get_expressions())

        return rv


    def generate_ast(self, generator, parent):
        if len(self.children) == 1 and \
                isinstance(self.children[0], JsExpressionNode):

            # special case, the attribute contains a single
            # expression, these are handled by
            # _TK_output.output_boolean_attr,
            # given the name, and unescaped expression!
            return [ Expr(SimpleCall(
                func=Attribute(
                    value=NameX('__TK__output'),
                    attr='attr',
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


class JsAttrsNode(JavascriptNode):
    def __init__(self, expression):
        super(JsAttrsNode, self).__init__()
        self.expression = expression


    def generate_ast(self, generator, parent):
        expression = get_fragment_ast(self.expression)

        output = SimpleCall(
            NameX('__TK__output_attrs'),
            args=[expression]
        )

        return self.generate_output_ast(output, generator, parent)


class JsForNode(JsComplexNode):
    def __init__(self, expression, parts):
        super(JsForNode, self).__init__()
        self.vars = parts[0]
        self.expression = parts[1]


    def generate_contents(self, generator, parent):
        body = get_fragment_ast(
            "__TK__foreach(%s, function (%s) { });" %
            (self.expression, self.vars),
            'exec'
        )

        for_node   = body[0]
        func_frame = for_node.expr.args[1]
        func_frame.elements = self.generate_child_ast(generator, self)
        return [ for_node ]


    def generate_ast(self, generator, parent):
        return self.generate_contents(generator, parent)


class JsDefineNode(JsComplexNode):
    def __init__(self, funcspec):
        super(JsDefineNode, self).__init__()
        if '(' not in funcspec:
            funcspec += '()'

        self.funcspec = funcspec

    def generate_ast(self, generator, parent):
        body = get_fragment_ast(
            "function %s{}" % self.funcspec,
            "exec"
        )

        def_node = body[0]
        assign_func_body(def_node, self.make_buffer_frame(
            self.generate_child_ast(generator, self),
        ))

        # move the function out of the closure
        if parent.is_top_level:
            generator.add_top_def(get_func_name(def_node), def_node)
            return []

        return [ def_node ]


class JsWithNode(JsComplexNode):
    def __init__(self, vars):
        super(JsWithNode, self).__init__()
        self.vars = vars

    def generate_ast(self, generator, parent):
        var_defs = get_fragment_ast(self.vars, 'exec')
        for i in var_defs:
            if not isinstance(i, ast.ExprStatement):
                raise TemplateSyntaxError("Only assignment statements allowed in With; not %s" % self.vars)

        body = var_defs + self.generate_child_ast(generator, self)
        return self.generate_varscope(body)


class JsComplexExprNode(JsComplexNode):
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


class JsBlockNode(JsComplexNode):
    def __init__(self, name):
        super(JsBlockNode, self).__init__()
        self.name = name


    def generate_ast(self, generator, parent):
        is_extended = isinstance(parent, JsExtendsNode)

        body = get_fragment_ast(
            "function %s () {}" % self.name,
            "exec"
        )

        def_node = body[0]
        assign_func_body(def_node, self.make_buffer_frame(
            self.generate_child_ast(generator, self),
        ))

        generator.add_block(self.name, def_node)

        if not is_extended:
            # call the block in place
            return self.generate_output_ast(
                [ SimpleCall(NameX(self.name), []) ],
                self, parent
            )

        else:
            return [ ]


class JsExtendsNode(JsComplexNode):
    is_top_level = True

    def __init__(self, href):
        super(JsExtendsNode, self).__init__()
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

    return tree
    #
    # coalesce_all_outputs = True
    # if coalesce_all_outputs:
    #     should_coalesce = lambda n: True
    # else:
    #     should_coalesce = lambda n: n.output_args[0].__class__ is Str
    #
    # class OutputCoalescer(NodeVisitor):
    #     def visit(self, node):
    #         # if - else expression also has a body! it is not we want, though.
    #         if hasattr(node, 'body') and isinstance(node.body, Iterable):
    #             # coalesce continuous string output nodes
    #             new_body = []
    #             output_node = None
    #
    #             def coalesce_strs():
    #                 if output_node:
    #                     output_node.value.args[:] = \
    #                         coalesce_strings(output_node.value.args)
    #
    #             for i in node.body:
    #                 if hasattr(i, 'output_args') and should_coalesce(i):
    #                     if output_node:
    #                         output_node.value.args.extend(i.output_args)
    #                         continue
    #
    #                     output_node = i
    #
    #                 else:
    #                     coalesce_strs()
    #                     output_node = None
    #
    #                 new_body.append(i)
    #
    #             coalesce_strs()
    #             node.body[:] = new_body
    #
    #         NodeVisitor.visit(self, node)
    #
    #     def check(self, node):
    #         """
    #         Coalesce _TK_output(_TK_escape(literal(x))) into
    #         _TK_output(x).
    #         """
    #         if not ast_equals(node.func, NameX('__TK__output')):
    #             return
    #
    #         for i in range(len(node.args)):
    #             arg1 = node.args[i]
    #             if not arg1.__class__.__name__ == 'Call':
    #                 continue
    #
    #             if not ast_equals(arg1.func, NameX('__TK__escape')):
    #                 continue
    #
    #             if len(arg1.args) != 1:
    #                 continue
    #
    #             arg2 = arg1.args[0]
    #             if not arg2.__class__.__name__ == 'Call':
    #                 continue
    #
    #             if not ast_equals(arg2.func, NameX('literal')):
    #                 continue
    #
    #             if len(arg2.args) != 1:
    #                 continue
    #
    #             node.args[i] = arg2.args[0]
    #
    #     def visit_Call(self, node):
    #         self.check(node)
    #         self.generic_visit(node)
    #
    # OutputCoalescer().visit(tree)


class JsRootNode(JsComplexNode):
    def __init__(self):
        super(JsRootNode, self).__init__()

    is_top_level = True

    def generate_ast(self, generator, parent=None):
        main_body = self.generate_child_ast(generator, self)

        extended = generator.extended_href

        # do not generate __main__ for extended templates
        if not extended:
            main_func = self.make_function('__main__', main_body, add_buffer=True)
            generator.add_top_def('__main__', main_func)

        toplevel_funcs = generator.blocks + generator.top_defs

        # analyze the set of free variables
        free_variables = set()
        for i in toplevel_funcs:
            fv_info = FreeVarFinder.for_ast(i)
            free_variables.update(fv_info.get_free_variables())

        free_variables |= generator.top_level_names

        # discard _TK_ variables, always builtin names undefined
        # from free variables.
        for i in list(free_variables):
            if i.startswith('__TK__') or i in ALWAYS_BUILTINS:
                free_variables.discard(i)

        # discard the names of toplevel funcs from free variables
        # free_variables.difference_update(generator.top_level_names)

        modules = ['tonnikala/runtime'] + list(generator.import_sources)

        if extended:
            modules.append(extended)

        # var_statement_vars = set(free_variables)|set(

        code = 'define(%s, function(__TK__) {\n' % json.dumps(modules)
        code += '    "use strict";\n'
        code += '    var __TK__mkbuffer = __TK__.Buffer,\n'
        code += '        __TK__escape = __TK__.escape,\n'
        code += '        __TK__foreach = __TK__.foreach,\n'
        code += '        literal = __TK__.literal,\n'

        if extended:
            code += '        __TK__parent_template = __TK__.load(%s),\n' % json.dumps(extended)

        code += '        __TK__output_attrs = __TK__.outputAttrs,\n'
        code += '        __TK__ctxadd = __TK__.addToContext,\n'
        code += '        __TK__ctxbind = __TK__.bindFromContext;\n'
        code += '    return function __TK__binder (__TK__context) {\n'
        code += '        var %s;\n' % ',\n            '.join(free_variables)

        if extended:
            # an extended template does not have a __main__ (it is inherited)
            code += '        __TK__parent_template(__TK__context)\n'

        for i in free_variables:
            code += '        %s = __TK__ctxbind(__TK__context, "%s");\n' % (i, i)

        code += '        return new __TK__.BoundTemplate(__TK__context);\n'
        code += '    };\n'
        code += '});\n'

        tree = parse(code)

        class LocatorAndTransformer(Visitor):
            binder = None

            def visit_FuncExpr(self, node):
                if not node.identifier:
                    self.generic_visit(node)
                    return

                name = node.identifier.value
                if name == '__TK__binder' and not self.binder:
                    self.binder = node
                    return

                self.generic_visit(node)
                return node

        locator = LocatorAndTransformer()
        locator.visit(tree)

        # inject the other top level funcs in the binder
        binder = locator.binder
        get_body(binder)[1:1] = toplevel_funcs
        get_body(binder)[1:1] = generator.imports

        coalesce_outputs(tree)
        return tree.to_ecma()


class Generator(BaseGenerator):
    OutputNode             = JsOutputNode
    TranslatableOutputNode = JsTranslatableOutputNode

    IfNode          = JsIfNode
    ForNode         = JsForNode
    DefineNode      = JsDefineNode
    ComplexExprNode = JsComplexExprNode
    ExpressionNode  = JsExpressionNode
    ImportNode      = JsImportNode
    RootNode        = JsRootNode
    AttributeNode   = JsAttributeNode
    AttrsNode       = JsAttrsNode
    UnlessNode      = JsUnlessNode
    ExtendsNode     = JsExtendsNode
    BlockNode       = JsBlockNode
    CodeNode        = JsCodeNode
    WithNode        = JsWithNode

    def __init__(self, ir_tree):
        super(Generator, self).__init__(ir_tree)
        self.blocks          = []
        self.top_defs        = []
        self.top_level_names = set()
        self.extended_href   = None
        self.imports         = []
        self.import_sources  = []

    def add_bind_decorator(self, block):
        name = block.identifier.value
        return Expr(SimpleCall(Name('__TK__ctxadd'), [ Name('__TK__context'), Str(name), block ]))

    def add_block(self, name, block):
        self.top_level_names.add(name)
        block = self.add_bind_decorator(block)
        self.blocks.append(block)

    def add_top_def(self, name, defblock):
        self.top_level_names.add(name)
        defblock = self.add_bind_decorator(defblock)
        self.top_defs.append(defblock)

    def add_top_level_import(self, name, node):
        self.top_level_names.add(name)
        self.imports.append(node)

    def make_extended_template(self, href):
        self.extended_href = href

    def add_import_source(self, href):
        self.import_sources.append(href)
