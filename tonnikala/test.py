from tonnikala import expr
from tonnikala.languages import javascript

print repr(expr.handle_text_node('asdfasdf${asdfasdfasdfasdf(r"asdfasdfasdf}")}}'))
print repr(expr.handle_text_node('asdfasdf${1 / 0} /} }', expr_parser=javascript.parse_expression))
print repr(expr.handle_text_node('asdfasdf${1 + / 0} /} }', expr_parser=javascript.parse_expression))

