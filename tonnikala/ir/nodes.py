class Node(object):
    def __repr__(self):
        return self.__class__.__name__ + '(%r)' % str(self)

class TextNode(Node):
    def __init__(self, string):
        self.string = string

    def __str__(self):
        return self.string

class ComplexExprNode(Node):
    def __init__(self, parts):
        self.parts = parts

    def __repr__(self):
        return self.__class__.__name__ + '(%s)' % ', '.join(repr(i) for i in self.parts)

    def __str__(self):
        return ''.join(str(i) for i in self.parts)

class ExpressionNode(Node):
    def __init__(self, string, tokens):
        self.string = string
        self.tokens = tokens

    def __str__(self):
        return self.string

