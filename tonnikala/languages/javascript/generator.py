from tonnikala.ir import nodes
from tonnikala.languages.base import LanguageNode, ComplexNode, BaseGenerator
from slimit.scope import SymbolTable
from slimit.parser import Parser
from slimit.visitors.scopevisitor import (
    Visitor,
    ScopeTreeVisitor,
    fill_scope_references,
    mangle_scope_tree,
    NameManglerVisitor,
    )


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


name_counter = 0

class JavascriptNode(LanguageNode):
    def make_string(self, text):
        if isinstance(text, bytes):
            text = text.decode('UTF-8')

        rv = repr(text)
        if rv.startswith('u'):
            rv = rv[1:]

        return rv

    def generate_yield(self, code):
        return self.generate_indented_code('__tonnikala__output__(%s);' % code)

    def generate_escaped_yield(self, code):
        return self.generate_indented_code('__tonnikala__output__.escape(%s);' % code)

    def gen_name(self):
        global name_counter
        name_counter += 1
        return "__tk_%d__" % name_counter

    def generate_varscope(self, generator):
        yield self.generate_indented_code('(function(){')
        self.indent_level += 1

        for i in generator():
            yield i

        self.indent_level -= 1
        yield self.generate_indented_code('());')


class JsOutputNode(JavascriptNode):
    def __init__(self, text):
        super(JsOutputNode, self).__init__()
        self.text = text

    def generate(self):
        yield self.generate_yield(self.make_string(self.text))


class JsExpressionNode(JavascriptNode):
    def __init__(self, expression, tokens):
        super(JsExpressionNode, self).__init__()
        self.expr = expression
        self.tokens = tokens

    def get_unescaped_expression(self):
        return self.expr

    def generate(self):
        yield self.generate_escaped_yield('(%s)' % self.expr)


class JsComplexNode(ComplexNode, JavascriptNode):
    pass


class JsIfNode(JsComplexNode):
    def __init__(self, expression):
        super(JsIfNode, self).__init__()
        self.expression = expression

    def generate(self):
        yield self.generate_indented_code("if (%s) {" % self.expression)
        for i in self.indented_children():
            yield i

        yield self.generate_indented_code("}")


class JsImportNode(JavascriptNode):
    def __init__(self, href, alias):
        super(JsImportNode, self).__init__()
        self.href = href
        self.alias = alias

    def generate(self):
        yield self.generate_indented_code(
           "%s = __tonnikala__import_defs(%s);" % (self.alias, self.make_string(self.href)))


class JsForNode(JsComplexNode):
    def __init__(self, vars, expression):
        super(JsForNode, self).__init__()
        self.vars = vars
        self.expression = expression

    def generate(self):
        yield self.generate_indented_code("__tonnikala__.foreach(%s, function (%s) {" % (self.expression, self.vars))
        for i in self.indented_children():
            yield i

        yield self.generate_indented_code("});")


class JsDefineNode(JsComplexNode):
    def __init__(self, funcspec):
        super(JsDefineNode, self).__init__()
        if '(' not in funcspec:
            funcspec += '()'

        self.funcspec = funcspec
        self.funcname = funcspec[:funcspec.index('(')]

    def generate(self):
        yield self.generate_indented_code("function %s {" % (self.funcspec))
        yield self.generate_indented_code("    var __tonnikala__output__ = __tonnikala__Buffer();")

        for i in self.indented_children():
            yield i

        yield self.generate_indented_code("    return __tonnikala__output__;")
        yield self.generate_indented_code("};")

class JsComplexExprNode(JsComplexNode):
    def generate(self):
        for i in self.indented_children(increment=0):
            yield i

class JsAttributeNode(JsComplexNode):
    def __init__(self, name, value):
        super(JsAttributeNode, self).__init__()
        self.name = name

    def get_expressions(self):
        rv = []
        for i in self.children:
            rv.extend(i.get_expressions())

        return rv

    def generate(self):
        if len(self.children) == 1 and \
                isinstance(self.children[0], JsExpressionNode):

            expr = self.children[0].get_unescaped_expression()
            yield self.generate_indented_code('__tonnikala__output__.attr(%r, (%s));' % (self.name, expr))

        # otherwise just return the output for the attribute code
        # like before

        yield self.generate_yield(
            '\' %s="\'' % self.name
        )
        for i in self.indented_children(increment=0):
            yield i

        yield self.generate_yield('\'"\'')


class JsRootNode(JsComplexNode):
    def __init__(self):
        super(JsRootNode, self).__init__()
        self.set_indent_level(0)

    def create_code(self):
        return ''.join(self.indented_children(increment=3))

    def do_generate(self):
        code = self.create_code()
        parser = Parser()
        tree = parser.parse(code)

        sym_table = SymbolTable()
        visitor = ScopeTreeVisitor(sym_table)
        visitor.visit(tree)
        fill_scope_references(tree)

        free_var_analysis = FreeVariableAnalyzerVisitor()
        free_var_analysis.visit(tree)
        free_vars = [ i for i in free_var_analysis.free_variables if not i.startswith('__tonnikala__') ]

        var_items = [('__tonnikala__output__ = __tonnikala__Buffer()')]
        for i in free_vars:
            var_items.append('%s = __tonnikala__ctxbind(__tonnikala__context, "%s")' % (i, i))

        yield 'define(["tonnikala/runtime"], function(__tonnikala__) {\n'
        yield '    "use strict";\n'
        yield '    var __tonnikala__Buffer = __tonnikala__.Buffer,\n'
        yield '        literal = __tonnikala__.literal,\n'
        yield '        __tonnikala__ctxbind = __tonnikala__.ctxbind;\n'
        yield '    return function (__tonnikala__context) {\n'
        yield '        return new __tonnikala__.renderer(function() {\n'
        yield '            var ' + ',\n                '.join(var_items) + ';\n';

        yield code

        yield '            return __tonnikala__output__;\n'
        yield '        });\n'
        yield '    };\n'
        yield '});\n'

    def generate(self):
        return [''.join(self.do_generate())]


class Generator(BaseGenerator):
    OutputNode      = JsOutputNode
    IfNode          = JsIfNode
    ForNode         = JsForNode
    DefineNode      = JsDefineNode
    ComplexExprNode = JsComplexExprNode
    ExpressionNode  = JsExpressionNode
    ImportNode      = JsImportNode
    RootNode        = JsRootNode
    AttributeNode   = JsAttributeNode
