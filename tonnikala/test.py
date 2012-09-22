from tonnikala import expr
from tonnikala.languages import javascript
from tonnikala import parser
from os import path
from tonnikala.ir.generate import generate_ir_tree

print repr(expr.handle_text_node('${a\n+\n"}"}'))
print repr(expr.handle_text_node('asdfasdf${1 / 0} /} }', expr_parser=javascript.parse_expression))
print repr(expr.handle_text_node('asdfasdf${1 + / 0} /} }', expr_parser=javascript.parse_expression))


input = path.join(path.dirname(__file__), 'not_found.html')
x = parser.Parser(input, open(input).read())
y = x.parse()
z = generate_ir_tree(y)
