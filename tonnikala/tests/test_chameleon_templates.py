from __future__ import absolute_import, division, print_function, unicode_literals

import unittest
import six

from tonnikala.loader import Loader

def render(template, **args):
    compiled = Loader(syntax='chameleon').load_string(template)
    return six.text_type(compiled.render(args))

class TestHtmlTemplates(unittest.TestCase):
    def are(self, result, template, **args):
        """assert rendered equals"""

        self.assertEqual(render(template, **args), result)

    def test_simple(self):
        self.are('<html></html>', '<html></html>')
        self.are('<html attr="&amp;&lt;&#34;">&amp;&lt;&#34;</html>',
            '<html attr="&amp;&lt;&#34;">&amp;&lt;&#34;</html>')
        self.are('<html></html>', '<html ></html >')
        fragment = '<html><nested>a</nested>b<nested>c</nested></html>'
        self.are(fragment, fragment)

    def test_if(self):
        fragment = '<html><div id="a" tal:condition="flag">was true</div></html>'
        self.are('<html><div id="a">was true</div></html>', fragment, flag=True)
        self.are('<html></html>', fragment, flag=False)
        self.are('<html><div id="a">was true</div></html>', fragment, flag=dict(something=1))
        self.are('<html></html>', fragment, flag={})
        self.are('<html></html>', fragment, flag=None)

    def test_escapes_in_expression(self):
        self.are('<html>&lt;&amp;&#34;</html>', '<html>${i}</html>', i='<&"')

    def test_for(self):
        fragment = '<html><div tal:repeat="i in values">${i}</div></html>'
        self.are('<html><div>0</div><div>1</div></html>', fragment, values=range(2))

    def test_strip(self):
        fragment = '<html><div tal:omit-tag="foo()">bar</div></html>'
        self.are('<html>bar</html>', fragment, foo=lambda: True)
        self.are('<html><div>bar</div></html>', fragment, foo=lambda: False)

        fragment = '<html><div tal:omit-tag="">bar</div></html>'
        self.are('<html>bar</html>', fragment)

    def test_top_level_strip(self):
        fragment = '<html tal:omit-tag="True">content</html>'
        self.are('content', fragment)

    def disabled_test_strip_evalled_expression(self):
        # the strip expression should not be evalled twice, but currently is
        # TODO: enable.

        fragment = '<html><div tal:omit-tag="foo()">bar</div></html>'
        self.are('<html>bar</html>',           fragment,
            foo=lambda x=iter([ True, False ]): next(x))

        self.are('<html><div>bar<div></html>', fragment,
            foo=lambda x=iter([ False, True ]): next(x))

    def test_comments(self):
        fragment = '<html><!-- some comment here, passed verbatim <html></html> --></html>'
        self.are('<html><!-- some comment here, passed verbatim <html></html> --></html>', fragment)

    def test_comments_stripped(self):
        fragment = '<html><!--! some comment here, stripped --></html>'
        self.are('<html></html>', fragment)

    def test_replace(self):
        fragment = '<html><div tal:replace="foo">bar</div></html>'
        self.are('<html>baz</html>', fragment, foo='baz')
        self.are('<html>&lt;</html>', fragment, foo='<')

    def test_content(self):
        fragment = '<html><div tal:content="foo">bar</div></html>'
        self.are('<html><div>baz</div></html>', fragment, foo='baz')

    def test_empty_tags(self):
        fragment = '<html><script/><script></script><br/><br></br></html>'
        self.are('<html><script></script><script></script><br /><br /></html>', fragment)

    def test_attribute_expressions(self):
        fragment = '<html a="$foo"></html>'
        self.are('<html></html>', fragment, foo=None)
        self.are('<html></html>', fragment, foo=False)
        self.are('<html a="a"></html>', fragment, foo=True)
        self.are('<html a=""></html>', fragment, foo="")
        self.are('<html a="abc"></html>', fragment, foo="abc")
        self.are('<html a="&lt;&amp;&#34;&gt;"></html>', fragment, foo='<&">')

        fragment = '<html a="abc$foo&lt;"></html>'
        self.are('<html a="abcab&lt;&lt;"></html>', fragment, foo='ab<')
        self.are('<html a="abcFalse&lt;"></html>', fragment, foo=False)
        self.are('<html a="abcNone&lt;"></html>', fragment, foo=None)
        self.are('<html a="abcTrue&lt;"></html>', fragment, foo=True)

    def test_dollars(self):
        fragment = '<html><script>$.fn $(abc) $$a $a</script></html>'
        self.are('<html><script>$.fn $(abc) $a foobar</script></html>',
            fragment, a='foobar')

    def test_script_tags(self):
        fragment = '<html><script>alert(1 < 3)</script></html>'
        self.are('<html><script>alert(1 < 3)</script></html>', fragment)
