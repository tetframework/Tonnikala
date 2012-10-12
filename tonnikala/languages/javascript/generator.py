from tonnikala.ir import nodes
from tonnikala.languages.base import LanguageNode, ComplexNode, BaseGenerator

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

    def generate(self):
        yield self.generate_yield('(%s)' % self.expr)


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
        yield self.generate_indented_code("__tonnikala__foreach(%s, function (%s) {" % (self.expression, self.vars))
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
        yield self.generate_indented_code("var %s = function %s {" % (self.funcname, self.funcspec))
        yield self.generate_indented_code("    var __tonnikala__output__ = __tonnikala__Rope();")

        for i in self.indented_children():
            yield i

        yield self.generate_indented_code("    return __tonnikala__output__;")
        yield self.generate_indented_code("};")

class JsComplexExprNode(JsComplexNode):
    def generate(self):
        for i in self.indented_children(increment=0):
            yield i

class JsRootNode(JsComplexNode):
    def __init__(self):
        super(JsRootNode, self).__init__()
        self.set_indent_level(0)

    def generate(self):
        yield 'define(["tonnikala/runtime"], function(__tonnikala__) {\n'
        yield '    var __tonnikala__Rope = __tonnikala__.Rope\n'
        yield '    return function (__context) {\n'
        yield '        __tonnikala__output__ = __tonnikala__Rope()\n'

        for i in self.indented_children(increment=2):
            yield i

        yield '        return __tonnikala__output__\n'
        yield '    };\n'
        yield '});\n'

class Generator(BaseGenerator):
    OutputNode      = JsOutputNode
    IfNode          = JsIfNode
    ForNode         = JsForNode
    DefineNode      = JsDefineNode
    ComplexExprNode = JsComplexExprNode
    ExpressionNode  = JsExpressionNode
    ImportNode      = JsImportNode
    RootNode        = JsRootNode
