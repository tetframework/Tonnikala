from __future__ import absolute_import, division, print_function, unicode_literals

"Test expressions"

import unittest

from tonnikala import expr
from tonnikala.languages import javascript
from tonnikala import parser
from os import path
from tonnikala.ir.generate import IRGenerator
from tonnikala.languages.python.generator import Generator as PythonGenerator
from tonnikala.languages.javascript.generator import Generator as JavascriptGenerator
from tonnikala.loader import Loader

class TestExpressions(unittest.TestCase):
    def test_python_expression(self):
        content = repr(expr.handle_text_node('${a\n+\n"}"}'))
        self.assertEquals(content, 'PythonExpression(a\n+\n"}")')

    def test_javascript_expression(self):
        # a divide operator
        content = repr(expr.handle_text_node('a ${1 / 0} /} }',
            expr_parser=javascript.parse_expression))

        self.assertEquals(content,
            'ComplexExpression([Text(a ), JavascriptExpression(1 / 0), Text( /} })])')

        # a regexp literal
        content = repr(expr.handle_text_node('a ${1 + / 0} /} }',
            expr_parser=javascript.parse_expression))

        self.assertEquals(content,
            'ComplexExpression([Text(a ), JavascriptExpression(1 + / 0} /), Text( })])')
