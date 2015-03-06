from __future__ import absolute_import, division, print_function, unicode_literals

from tonnikala.loader import Loader, JSLoader

template = """<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml"
        xmlns:py="http://genshi.edgewall.org/"
        xmlns:fb="http://www.facebook.com/2008/fbml" py:foo="barf">
        <js:import href="includes.html" alias="includes"/>
        <body>
        <js:def function="the_body"><ul><li js:for="i in ['1', '2', '3']">$i ${str(int(i))}</li></ul></js:def>
        <js:def function="output_body(body_func)"><div>${body_func()}</div></js:def>
        ${output_body(the_body)}
        <div id="foo">$foo</div>
        <div id="bar">$bar</div>
        </body>
</html>"""

print(JSLoader(debug=True, minify=True).load_string(template))
