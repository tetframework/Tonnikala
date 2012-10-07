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


template = """<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml"
        xmlns:py="http://genshi.edgewall.org/"
        xmlns:fb="http://www.facebook.com/2008/fbml" py:foo="barf">
        <py:import href="includes.html" alias="includes"/>
        <body>
        <py:def function="the_body"><ul><li py:for="i in ['1', '2', '3']">$i</li></ul></py:def>
        <py:def function="output_body(body_func)"><div>${the_body()}</div></py:def>
        ${output_body(the_body)}
        </body>
</html>"""

x = parser.Parser("<string>", template)
y = x.parse()

generator = IRGenerator(y)
z = generator.generate_tree()
z = generator.flatten_element_nodes(z)
z = generator.merge_text_nodes(z)

print(repr(z))

x = PythonGenerator(z).generate()

print(x)


from tonnikala.runtime import python

glob = {
    '__tonnikala_runtime__': python,
    'literal':               lambda x: x
}

exec x in glob, glob
template = glob['__Template']
output = template().render({})

print(output)
