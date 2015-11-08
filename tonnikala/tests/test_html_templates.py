from __future__ import absolute_import, division, print_function, unicode_literals
import unittest
import os.path
import codecs
from tonnikala.runtime import python
from tonnikala.runtime.exceptions import TemplateSyntaxError
from ..compat import text_type, OrderedDict
from tonnikala.loader import Loader, FileLoader


def render(template, debug=False, **args):
    compiled = FileLoader(debug=debug).load_string(template)
    return text_type(compiled.render(args))


data_dir = os.path.abspath(os.path.dirname(__file__))
data_dir = os.path.join(data_dir, 'files')
output_dir = os.path.join(data_dir, 'output')


def get_loader(debug=False):
    rv = FileLoader(debug=debug)
    rv.add_path(os.path.join(data_dir, 'input'))
    return rv


def get_reference_output(name):
    path = os.path.join(output_dir, name)
    with codecs.open(path, 'r', encoding='UTF-8') as f:
        return f.read()


class TestHtmlTemplates(unittest.TestCase):
    def are(self, result, template, **args):
        """assert rendered equals"""

        self.assertEqual(render(template, **args), result)

    def assert_loader_throws(self, exception_class, template, debug=False, **args):
        try:
            FileLoader(debug=debug).load_string(template)
        except exception_class:
            return

        raise AssertionError('loading the template {} did not throw a {}'
                             .format(template, exception_class.__name__))

    def assert_render_throws(self, exception_class, template, debug=False, **args):
        try:
            render(template, **args)
        except exception_class:
            return

        raise AssertionError('rendering the template {} did not throw a {}'
                             .format(template, exception_class.__name__))

    def test_simple(self):
        self.are('<html></html>', '<html></html>')
        self.are('<html attr="&amp;&lt;&#34;">&amp;&lt;&#34;</html>',
                 '<html attr="&amp;&lt;&#34;">&amp;&lt;&#34;</html>')
        self.are('<html></html>', '<html ></html >')
        fragment = '<html><nested>a</nested>b<nested>c</nested></html>'
        self.are(fragment, fragment)

    def test_text_outside_root(self):
        self.are('<html></html>', '<html></html>       ')
        self.assert_render_throws(TemplateSyntaxError, '<html></html>   a   ')

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

    def test_constant_if(self):
        fragment = '<html><py:if test="True">a</py:if></html>'
        self.are('<html>a</html>', fragment)
        fragment = '<html><py:if test="False">a</py:if></html>'
        self.are('<html></html>', fragment)
        fragment = '<html><span py:if="True">a</span></html>'
        self.are('<html><span>a</span></html>', fragment)
        fragment = '<html><span py:if="False">a</span></html>'
        self.are('<html></html>', fragment)

    def test_escapes_in_expression(self):
        self.are('<html>&lt;&amp;&#34;</html>', '<html>${i}</html>', i='<&"')

    def test_expressions_with_dollars_and_unescaped(self):
        self.are('<html>value $ $.jquery $</html>',
                 '<html>${i} $$ $.jquery $</html>', i='value')

    def test_nested_braces(self):
        self.are('<html>a</html>', "<html>${{'1': 'a'}[i]}</html>", i='1')

    def test_unclosed_expression(self):
        self.assert_loader_throws(TemplateSyntaxError, "<html>${'1'</html>")

    def test_mismatched_brackets(self):
        self.assert_loader_throws(TemplateSyntaxError, "<html>$foo[)]</html>")

    def test_unbraced_not_ending(self):
        self.assert_loader_throws(TemplateSyntaxError, "<html>$foo(</html>")

    def test_unbraced_line_continuation_not_ending(self):
        self.assert_loader_throws(TemplateSyntaxError, "<html>$foo(\</html>")

    def test_if_else_expression(self):
        """
        There was a bug in Tonnikala that caused the expression to not work
        This test is to make sure that there will be no regression
        """

        self.are('<html>foo</html>', '<html>${"foo" if True else "bar"}</html>')

    def test_for(self):
        fragment = '<html><py:for each="i in values">${i}</py:for></html>'
        self.are('<html></html>', fragment, values=[])
        self.are('<html>01234</html>', fragment, values=range(5))
        self.are('<html>&lt;</html>', fragment, values=['<'])

        fragment = '<html><div py:for="i in values">${i}</div></html>'
        self.are('<html><div>0</div><div>1</div></html>', fragment, values=range(2))

    def test_def(self):
        fragment = '<html><py:def function="foo(bar)">bar: ${bar}</py:def>' \
                   '-${foo("baz")}-</html>'

        self.are('<html>-bar: baz-</html>', fragment)
        self.assert_loader_throws(TemplateSyntaxError, '<html><py:def bar="foobar"></py:def></html>')

    def test_empty_def(self):
        fragment = '<html><py:def function="foo"></py:def>${foo()}</html>'
        self.are('<html></html>', fragment);

    def test_strip(self):
        fragment = '<html><div py:strip="foo()">bar</div></html>'
        self.are('<html>bar</html>', fragment, foo=lambda: True)
        self.are('<html><div>bar</div></html>', fragment, foo=lambda: False)

    def test_empty_strip(self):
        fragment = '<html><div py:strip=""></div></html>'
        self.are('<html></html>', fragment)

    def test_top_level_strip(self):
        fragment = '<html py:strip="True">content</html>'
        self.are('content', fragment, foo=lambda: True)

    def disabled_test_strip_evalled_expression(self):
        # the strip expression should not be evalled twice, but currently is
        # TODO: enable.

        fragment = '<html><div py:strip="foo()">bar</div></html>'
        self.are('<html>bar</html>', fragment,
                 foo=lambda x=iter([True, False]): next(x))

        self.are('<html><div>bar<div></html>', fragment,
                 foo=lambda x=iter([False, True]): next(x))

    def test_comments(self):
        fragment = '<html><!-- some comment here, passed verbatim <html></html> --></html>'
        self.are('<html><!-- some comment here, passed verbatim <html></html> --></html>', fragment)

    def test_comments_stripped(self):
        fragment = '<html><!--! some comment here, stripped --></html>'
        self.are('<html></html>', fragment)

    def test_replace(self):
        fragment = '<html><div py:replace="foo">bar</div></html>'
        self.are('<html>baz</html>', fragment, foo='baz')
        self.are('<html>&lt;</html>', fragment, foo='<')

        fragment = '<html><py:replace value="foo">bar</py:replace></html>'
        self.are('<html>baz</html>', fragment, foo='baz')
        self.are('<html>&lt;</html>', fragment, foo='<')

    def test_content(self):
        fragment = '<html><div py:content="foo">bar</div></html>'
        self.are('<html><div>baz</div></html>', fragment, foo='baz')

    def test_empty_tags(self):
        fragment = '<html><script/><script></script><br/><br></html>'
        self.are('<html><script></script><script></script><br /><br /></html>', fragment)

    def test_closures(self):
        fragment = '<html><a py:def="embed(func)">${func()}</a>' \
                   '<py:for each="i in range(3)"><py:def function="callable()">${i}</py:def>' \
                   '${embed(callable)}</py:for></html>'

        self.are('<html><a>0</a><a>1</a><a>2</a></html>', fragment)

    def test_exception_in_rendering(self):
        self.assert_render_throws(ZeroDivisionError, '<html>${1 / 0}</html>')

    def test_literal(self):
        self.are('<html><br/></html>', '<html>$literal(val)</html>', val='<br/>')

    def test_literal_only_1_argument(self):
        self.assert_render_throws(TypeError, '<html>$literal(val, val)</html>', val='<br/>')

    def test_invalid_expression_raises_template_syntax_error_and_multiline(self):
        self.assert_loader_throws(TemplateSyntaxError, '<html><py:for each="i in i i\n"></py:for></html>')

    def test_attribute_expressions(self):
        fragment = '<html a="$foo"></html>'
        self.are('<html></html>', fragment, foo=None)
        self.are('<html></html>', fragment, foo=False)

        # these must not be confused with boolean vars :)
        self.are('<html a="1"></html>', fragment, foo=1)
        self.are('<html a="0"></html>', fragment, foo=0)
        self.are('<html a="a"></html>', fragment, foo=True)
        self.are('<html></html>', fragment, foo=False)
        self.are('<html></html>', fragment, foo=None)
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

    def test_block(self):
        fragment = '<html><py:block name="foo">a block</py:block></html>'
        self.are('<html>a block</html>', fragment, debug=False)

        fragment = '<html><div py:block="foo">a block</div></html>'
        self.are('<html><div>a block</div></html>', fragment)

    def test_with(self):
        fragment = '<html><py:with vars="a = 5; b = 6">${a * b}</py:with></html>'
        self.are('<html>30</html>', fragment)

        fragment = '<html><div py:with="a = 5; b = 6">${a * b}</div></html>'
        self.are('<html><div>30</div></html>', fragment)

    def test_multiple_control_attributes(self):
        fragment = '<html><div py:if="u" py:for="v in range(1, 3)">$v</div>'
        self.are('<html><div>1</div><div>2</div></html>', fragment, u=True)

    def test_translation(self):
        fragment = '<html alt="foo"> abc </html>'
        self.are('<html alt="foo"> abc </html>', fragment, debug=False, translateable=True)

        def gettext(x):
            return '<"%s&>' % x

        self.are('<html alt="&lt;&#34;foo&amp;&gt;"> &lt;&#34;abc&amp;&gt; </html>',
                 fragment, debug=False, translateable=True, gettext=gettext)

        def gettext(x):
            return '<%s' % x

        self.are('<html>&lt;&gt;</html>', '<html>&gt;</html>', debug=False, translateable=True, gettext=gettext)

    def test_attrs(self):
        fragment = '<html><div py:attrs="foo"></div></html>'
        attrs = OrderedDict([('foo', 'bar'), ('baz', 42)])
        self.are('<html><div foo="bar" baz="42"></div></html>', fragment, debug=False, foo=attrs)

        attrs = [('foo', 'bar'), ('baz', 42)]
        self.are('<html><div foo="bar" baz="42"></div></html>', fragment, debug=False, foo=attrs)

        attrs = None
        self.are('<html><div></div></html>', fragment, debug=False, foo=attrs)

    def test_case_folding(self):
        self.are('<html></html>', '<html></HTML>', debug=False)

    def test_void_elements(self):
        self.are('<html><img title="foo" /></html>', '<html><img title="foo"></html>', debug=False)

    def assert_file_rendering_equals(self, input_file, output_file, debug=False, **context):
        loader = get_loader(debug=debug)
        template = loader.load(input_file)
        output = template.render(context)
        reference = get_reference_output(output_file)
        self.assertEqual(str(output), reference.rstrip('\n'))

    def test_file_loader(self):
        self.assert_file_rendering_equals('simple.tk', 'simple.tk', foo='bar')

    def test_extension(self):
        self.assert_file_rendering_equals('base.tk', 'base.tk', title='the base')
        self.assert_file_rendering_equals('child.tk', 'child.tk', title='the child')

    def test_import(self):
        self.assert_file_rendering_equals('importing.tk', 'importing.tk', foo='bar')

    def test_python_processing_instruction(self):
        result = []

        def bar(arg):
            result.append(arg)

        self.are(
            '<html></html>',
            '<html><?python foo("baz")?></html>',
            debug=False,
            foo=bar
        )
        self.assertEqual(['baz'], result)


if python.Buffer != python._TK_python_buffer_impl:
    class TestHtmlTemplatesWithoutSpeedups(TestHtmlTemplates):
        def setUp(self):
            self.saved_buffer_cls = python.Buffer
            python.Buffer = python._TK_python_buffer_impl
            python.TonnikalaRuntime.Buffer = staticmethod(python.Buffer)

        def tearDown(self):
            python.Buffer = self.saved_buffer_cls
            python.TonnikalaRuntime.Buffer = staticmethod(python.Buffer)
