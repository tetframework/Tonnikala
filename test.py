from __future__ import absolute_import, division, print_function, unicode_literals

from tonnikala import expr
from tonnikala.languages import javascript
from tonnikala import parser
from os import path
from tonnikala.ir.generate import IRGenerator
from tonnikala.languages.python.generator import Generator as PythonGenerator
from tonnikala.languages.javascript.generator import Generator as JavascriptGenerator
from tonnikala.loader import Loader

print(repr(expr.handle_text_node('${a\n+\n"}"}')))
print(repr(expr.handle_text_node('asdfasdf${1 / 0} /} }', expr_parser=javascript.parse_expression)))
print(repr(expr.handle_text_node('asdfasdf${1 + / 0} /} }', expr_parser=javascript.parse_expression)))

template = """<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml"
        xmlns:py="http://genshi.edgewall.org/"
        xmlns:fb="http://www.facebook.com/2008/fbml" py:foo="barf">
        <py:import href="includes.html" alias="includes"/>
        <body>
        <py:def function="the_body"><ul><li py:for="i in ['1', '2', '3']">$i ${str(int(i))}</li></ul></py:def>
        <py:def function="output_body(body_func)"><div>${body_func()}</div></py:def>
        ${output_body(the_body)}
        <div id="foo">$foo</div>
        <div id="bar">$bar</div>
        </body>
</html>"""

compiled = Loader(debug=True).load_string(template)
print("Rendered python template >>>")
print(compiled.render(dict(foo=1, bar='asdf')))
print("<<< ends here")
