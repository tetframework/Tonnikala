# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__docformat__ = "epytext"

"""Tonnikala compiler. Produces source code from XML."""

import re

from tonnikala.ir.nodes import Text, ComplexExpression
from tonnikala.languages import javascript, python
from tonnikala.exceptions import ParseError

_dollar_strip_re = re.compile(r"\$([a-zA-Z_{])|(\$\$)|\$", re.DOTALL)

class HasExprException(Exception):
    pass

def _strip_dollars_fast(text):
    def _sub(m):
        if m.group(2) is not None:
            return '$'

        if m.group(1) is not None:
            raise HasExprException()

        raise ParseError("Unescaped $ in content", charpos=m.start())

    return _dollar_strip_re.sub(_sub, text)

_expr_find_code = re.compile(r"""
  ([^$]+)        # match any chars except \n or $ (group 1)
| \$(\$)         # match double dollars (group 2)
| (\$[{a-zA-Z_]) # match beginning of expressions (group 3)
| (\$)           # match stray $ (group 4)

""", re.VERBOSE | re.DOTALL)


def create_text_node(text):
    return Text(text)

def handle_text_node(text, expr_parser=python.parse_expression):
    try:
        return create_text_node(_strip_dollars_fast(text))

    except HasExprException:
        pass

    nodes = []
    stringrun = []
    max_index = len(text)
    pos = 0

    while pos < len(text):
        m = _expr_find_code.match(text, pos)
        pos = m.end()

        if m.group(1) != None: # any
            stringrun.append(m.group(1))

        elif m.group(2): # $$
            stringrun.append('$')

        elif m.group(3):
            if stringrun:
                nodes.append(create_text_node(''.join(stringrun)))

            stringrun = []
            expr = expr_parser(text, m.start(3))
            pos = m.start(3) + len(expr.string)
            nodes.append(expr)

        else:
            pos -= 1
            raise ParseError("Unescaped $ in content", pos)

    if stringrun:
        nodes.append(create_text_node(''.join(stringrun)))

    if len(nodes) == 1:
        return nodes[0]

    node = ComplexExpression()
    for i in nodes:
        node.add_child(i)

    return node
