# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__docformat__ = "epytext"

from tonnikala.exceptions import ParseError
from tonnikala.ir.nodes import InterpolatedExpression

from tonnikala.languages.javascript.jslex import JsLexer
import re

class JavascriptExpression(InterpolatedExpression):
    pass

identifier_match = re.compile(r'[a-zA-Z_$][a-zA-Z_$0-9]*')

def parse_expression(text, start_pos=0):
    lex = JsLexer()
    nodes = []

    if text[start_pos + 1] != '{':
        m = identifier_match.match(text, start_pos + 1)
        identifier = m.group(0)
        return JavascriptExpression('$' + identifier, identifier, [('id', identifier)])

    braces = 0
    length = 2
    valid  = False
    tokens = lex.lex(text, start_pos + 2)
    for type, content in tokens:
        if content == '}':
            if braces <= 0:
                length += 1
                valid = True
                break

            braces -= 1

        if content == '{':
            braces += 1

        length += len(content)
        nodes.append((type, content))

    if not valid:
        raise ParseError("Not finished javascript expression", charpos=length)

    return JavascriptExpression(text[start_pos:start_pos + length], text[start_pos + 2: start_pos + length - 1], nodes)
