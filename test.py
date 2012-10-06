from __future__ import absolute_import, division, print_function, unicode_literals

from tonnikala import expr
from tonnikala.languages import javascript
from tonnikala import parser
from os import path
from tonnikala.ir.generate import IRGenerator
from tonnikala.languages.python.generator import Generator as PythonGenerator

print(repr(expr.handle_text_node('${a\n+\n"}"}')))
print(repr(expr.handle_text_node('asdfasdf${1 / 0} /} }', expr_parser=javascript.parse_expression)))
print(repr(expr.handle_text_node('asdfasdf${1 + / 0} /} }', expr_parser=javascript.parse_expression)))


input = path.join(path.dirname(__file__), 'not_found.html')
x = parser.Parser(input, open(input).read())
y = x.parse()

generator = IRGenerator(y)
z = generator.generate_tree()

print(repr(z))

print(PythonGenerator(z).generate())

