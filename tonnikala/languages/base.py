from tonnikala.ir import nodes

name_counter = 0

class LanguageNode(object):
    def __init__(self):
        self.indent_level = None
        self.children = []

    def set_indent_level(self, indent_level):
        self.indent_level = indent_level

    def get_indent(self):
        return ' ' * 4 * self.indent_level

    def add_child(self, node):
        if not isinstance(self, ComplexNode):
            raise NotImplementedError("Cannot add children to a node of type %s" % self.__class__.__name__)

        self.children.append(node)

    def generate_indented_code(self, code):
        return self.get_indent() + code + '\n'

    def gen_name(self):
        global name_counter
        name_counter += 1
        return "__tk_%d__" % name_counter


class ComplexNode(LanguageNode):
    def indented_children(self, increment=1):
        child_indent = self.indent_level + increment
        for i in self.children:
            i.set_indent_level(child_indent)
            for j in i.generate():
                yield j

def unimplemented(self, *a, **kw):
    raise NotImplementedError("Error: unimplemented")

class BaseGenerator(object):
    OutputNode      = unimplemented
    IfNode          = unimplemented
    ForNode         = unimplemented
    DefineNode      = unimplemented
    ComplexExprNode = unimplemented
    ExpressionNode  = unimplemented
    ImportNode      = unimplemented
    Node            = unimplemented

    def __init__(self, ir_tree):
        self.tree = ir_tree

    def add_children(self, ir_node, target):
        for i in ir_node.children:
            self.add_child(i, target)

    def add_child(self, ir_node, target):
        if   isinstance(ir_node, nodes.Text):
            new_node = (self.OutputNode(ir_node.escaped()))

        elif isinstance(ir_node, nodes.If):
            new_node = (self.IfNode(ir_node.expression))

        elif isinstance(ir_node, nodes.For):
            new_node = (self.ForNode(ir_node.parts[0], ir_node.parts[1]))

        elif isinstance(ir_node, nodes.Define):
            new_node = (self.DefineNode(ir_node.funcspec))

        elif isinstance(ir_node, nodes.ComplexExpression):
            new_node = (self.ComplexExprNode())

        elif isinstance(ir_node, nodes.Expression):
            new_node = (self.ExpressionNode(ir_node.expression, ir_node.tokens))

        elif isinstance(ir_node, nodes.Import):
            new_node = (self.ImportNode(ir_node.href, ir_node.alias))

        else:
            raise ValueError("Unknown node type", ir_node.__class__.__name__)

        target.add_child(new_node)

        if isinstance(ir_node, nodes.ContainerNode):
            self.add_children(ir_node, new_node)

    def generate(self):
        root = self.tree
        self.root_node = self.RootNode()
        self.add_children(self.tree.root, self.root_node)
        x = list(self.root_node.generate())
        return ''.join(self.root_node.generate())
