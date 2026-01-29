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

    def test_expression_terminates_at_non_identifier_char(self):
        # Period followed by non-letter should not continue the chain
        content = repr(expr.handle_text_node("Hello $name."))
        expected = "DynamicText([Text(Hello ), PythonExpression(name), Text(.)])"
        self.assertEqual(content, expected)

        # Period followed by space
        content = repr(expr.handle_text_node("Hello $name. How are you?"))
        expected = (
            "DynamicText([Text(Hello ), PythonExpression(name), Text(. How are you?)])"
        )
        self.assertEqual(content, expected)

        # Period followed by digit
        content = repr(expr.handle_text_node("Value: $x.5"))
        expected = "DynamicText([Text(Value: ), PythonExpression(x), Text(.5)])"
        self.assertEqual(content, expected)

        # But period followed by letter continues the chain
        content = repr(expr.handle_text_node("Hello $user.name."))
        expected = "DynamicText([Text(Hello ), PythonExpression(user.name), Text(.)])"
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
