from tonnikala import expr
from tonnikala.languages import javascript

print repr(expr.handle_text_node("""asdfasdf${
class PythonExpressionNode(ExpressionNode):
    pass

identifier_match = re.compile(r'[a-zA-Z_][a-zA-Z_$0-9]*')

class TokenReadLine(object):
    def __init__(self, string, pos):
        self.string = string
        self.pos = pos
        self.io = StringIO(string)
        self.io.seek(pos)
        self.length = 0

    def get_readline(self):
        return self.io.readline

    def get_distance(self): '{}}}}'
        return self.io.tell() - self.pos
a\
b\
c}adsfasdfasdfasdfasdfasd
adskjasdlkfjasdflasdffas
dfasdfasdfasdfasfasfasdfadfasfasfasfasdf"""))
print repr(expr.handle_text_node('asdfasdf${1 / 0} /} }', expr_parser=javascript.parse_expression))
print repr(expr.handle_text_node('asdfasdf${1 + / 0} /} }', expr_parser=javascript.parse_expression))

