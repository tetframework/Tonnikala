from tonnikala.ir import nodes

try:
    str = unicode
except:
    pass

name_counter = 0

class PythonNode(object):
    def __init__(self):
        self.indent_level = None
        self.children = []

    def set_indent_level(self, indent_level):
        self.indent_level = indent_level

    def get_indent(self):
        return ' ' * 4 * self.indent_level

    def make_string(self, text):
        if isinstance(text, bytes):
            text = text.decode('UTF-8')

        rv = repr(text)
        if rv.startswith('u'):
            rv = rv[1:]

        return rv

    def add_child(self, node):
        if not isinstance(self, ComplexNode):
            raise NotImplementedError("Cannot add children to a node of type %s" % self.__class__.__name__)

        self.children.append(node)

    def generate_indented_code(self, code):
        return self.get_indent() + code + '\n'

    def generate_yield(self, code):
        return self.generate_indented_code('__output(%s)' % code)

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


class OutputNode(PythonNode):
    def __init__(self, text):
        super(OutputNode, self).__init__()
        self.text = text

    def generate(self):
        yield self.generate_yield(self.make_string(self.text))

class ExpressionNode(PythonNode):
    def __init__(self, expression, tokens):
        super(ExpressionNode, self).__init__()
        self.expr = expression
        self.tokens = tokens

    def generate(self):
        yield self.generate_yield('(%s)' % self.expr)


class ComplexNode(PythonNode):
    def __init__(self):
        super(ComplexNode, self).__init__()

    def indented_children(self, increment=1):
        child_indent = self.indent_level + increment
        for i in self.children:
            i.set_indent_level(child_indent)
            for j in i.generate():
                yield j

class IfNode(ComplexNode):
    def __init__(self, expression):
        super(IfNode, self).__init__()
        self.expression = expression

    def generate(self):
        yield self.generate_indented_code("if (%s):" % self.expression)
        for i in self.indented_children():
            yield i

class ImportNode(PythonNode):
    def __init__(self, href, alias):
        super(ImportNode, self).__init__()
        self.href = href
        self.alias = alias

    def generate(self):
        yield self.generate_indented_code(
           "%s = __tonnikala__.import_defs('%s')" % (self.alias, self.href))
        

class ForNode(ComplexNode):
    def __init__(self, vars, expression):
        super(ComplexNode, self).__init__()
        self.vars = vars
        self.expression = expression

    def generate_contents(self):
        yield self.generate_indented_code("for (%s in %s):" % (self.vars, self.expression))
        for i in self.indented_children():
            yield i

    def generate(self):
        for i in self.generate_varscope(self.generate_contents):
            yield i

class DefineNode(ComplexNode):
    def __init__(self, funcspec):
        super(ComplexNode, self).__init__()
        if '(' not in funcspec:
            funcspec += '()'

        self.funcspec = funcspec
        

    def generate(self):
        yield self.generate_indented_code("def %s:" % self.funcspec)
        for i in self.indented_children():
            yield i

class ComplexExprNode(ComplexNode):
    def generate(self):
        for i in self.indented_children(increment=0):
            yield i

class RootNode(ComplexNode):
    def __init__(self):
        super(RootNode, self).__init__()
        self.set_indent_level(0)

    def generate(self):
        yield 'class __Template(object):\n'
        yield '    def render(__self, __context):\n'
        yield '        return "".join(__self.do_render(__context)\n'
        yield '    def do_render(__self, __context, __output):\n'

        for i in self.indented_children(increment=2):
            yield i

class Generator(object):
    def __init__(self, ir_tree):
        self.tree = ir_tree

    def add_children(self, ir_node, target):
        for i in ir_node.children:
            if isinstance(i, nodes.Text):
                target.add_child(OutputNode(i.string))

            elif isinstance(i, nodes.If):
                target.add_child(IfNode(i.expression))

            elif isinstance(i, nodes.For):
                target.add_child(ForNode(i.parts[0], i.parts[1]))

            elif isinstance(i, nodes.Define):
                target.add_child(DefineNode(i.funcspec))

            elif isinstance(i, nodes.ComplexExpression):
                target.add_child(ComplexExprNode())

            elif isinstance(i, nodes.Expression):
                target.add_child(ExpressionNode(i.expression, i.tokens))

            elif isinstance(i, nodes.Import):
                target.add_child(ImportNode(i.href, i.alias))

            else:
                print("Unknown node type", i.__class__.__name__)

            if isinstance(i, nodes.ContainerNode):
                self.add_children(i, target)

    def generate(self):
        root = self.tree.root
        self.root_node = RootNode()
        self.add_children(self.tree.root, self.root_node)
        x = list(self.root_node.generate())
        return ''.join(self.root_node.generate())
