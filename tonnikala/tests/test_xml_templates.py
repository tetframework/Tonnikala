from __future__ import absolute_import, division, print_function, unicode_literals

import unittest
import six

from tonnikala import parser
from tonnikala.ir.generate import IRGenerator
from tonnikala.loader import Loader

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

def render(template, **args):
    compiled = Loader().load_string(template)
    return six.text_type(compiled.render(args))

class TestXmlTemplates(unittest.TestCase):
    def are(self, result, template, **args):
        """assert rendered equals"""
        
        self.assertEquals(render(template, **args), result)
 
    def test_simple(self):
        self.are('<html></html>', '<html></html>')
        self.are('<html attr="&amp;&lt;&quot;">&amp;&lt;&quot;</html>', 
            '<html attr="&amp;&lt;&quot;">&amp;&lt;&quot;</html>')
        self.are('<html></html>', '<html ></html >')
        fragment = '<html><nested>a</nested>b<nested>c</nested></html>'
        self.are(fragment, fragment)

    def test_if(self):
        fragment = '<html><py:if test="flag">was true</py:if></html>'
        self.are('<html>was true</html>', fragment, flag=True)
        self.are('<html></html>', fragment, flag=False)
        self.are('<html>was true</html>', fragment, flag=dict(something=1))
        self.are('<html></html>', fragment, flag={})
        self.are('<html></html>', fragment, flag=None)

        fragment = '<html><div id="a" py:if="flag">was true</div></html>'
        self.are('<html><div id="a">was true</div></html>', fragment, flag=True)
        self.are('<html></html>', fragment, flag=False)
        self.are('<html><div id="a">was true</div></html>', fragment, flag=dict(something=1))
        self.are('<html></html>', fragment, flag={})
        self.are('<html></html>', fragment, flag=None)

    def test_escapes_in_expression(self):
        self.are('<html>&lt;&amp;&quot;</html>', '<html>${i}</html>', i='<&"')

    def test_for(self):
        fragment = '<html><py:for each="i in values">${i}</py:for></html>'
        self.are('<html></html>', fragment, values=[])
        self.are('<html>01234</html>', fragment, values=xrange(5))
        self.are('<html>&lt;</html>', fragment, values=['<'])

        fragment = '<html><div py:for="i in values">${i}</div></html>'
        self.are('<html><div>0</div><div>1</div></html>', fragment, values=range(2))

    def test_def(self):
        fragment = '<html><py:def function="foo(bar)">bar: ${bar}</py:def>' \
            '-${foo("baz")}-</html>'

        self.are('<html>-bar: baz-</html>', fragment)

    def test_closures(self):
        fragment = '<html><a py:def="embed(func)">${func()}</a>' \
            '<py:for each="i in range(3)"><py:def function="callable()">${i}</py:def>' \
            '${embed(callable)}</py:for></html>'

        self.are('<html><a>0</a><a>1</a><a>2</a></html>', fragment)
