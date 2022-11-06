"Test expressions"

import unittest

from tonnikala import expr
from tonnikala.languages import javascript


class TestExpressions(unittest.TestCase):
    def test_python_expression(self):
        content = repr(expr.handle_text_node('${a\n+\n"}"}'))
        self.assertEqual(content, 'PythonExpression(a\n+\n"}")')

        content = repr(expr.handle_text_node('foo$a.baz["bar]"].xyz("ham)"))...'))
        expected = 'DynamicText([Text(foo), PythonExpression(a.baz["bar]"].xyz("ham)")), Text()...)])'
        self.assertEqual(content, expected)

    def test_javascript_expression(self):
        # a divide operator
        content = repr(
            expr.handle_text_node(
                "a ${1 / 0} /} }", expr_parser=javascript.parse_expression
            )
        )

        self.assertEqual(
            content, "DynamicText([Text(a ), JavascriptExpression(1 / 0), Text( /} })])"
        )

        # a regexp literal
        content = repr(
            expr.handle_text_node(
                "a ${1 + / 0} /} }", expr_parser=javascript.parse_expression
            )
        )

        self.assertEqual(
            content,
            "DynamicText([Text(a ), JavascriptExpression(1 + / 0} /), Text( })])",
        )

        content = repr(
            expr.handle_text_node(
                'foo$a.baz["bar]"].xyz("ham)"))...',
                expr_parser=javascript.parse_expression,
            )
        )
        expected = 'DynamicText([Text(foo), JavascriptExpression(a.baz["bar]"].xyz("ham)")), Text()...)])'
        self.assertEqual(content, expected)
