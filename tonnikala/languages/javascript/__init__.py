# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, \
    unicode_literals

import re

from tonnikala.exceptions import ParseError
from tonnikala.ir.nodes import InterpolatedExpression
from tonnikala.languages.javascript.jslex import JsLexer
from tonnikala.runtime.exceptions import TemplateSyntaxError


class JavascriptExpression(InterpolatedExpression):
    pass


identifier_match = re.compile(r'[^\d\W][\w$]*', re.UNICODE)
expr_continuation = re.compile(r'[([]|(\.[^\d\W][\w$]*)', re.UNICODE)

braces = {
    '[': ']',
    '(': ')'
}


def parse_unenclosed_expression(text, start_pos):
    m = identifier_match.match(text, start_pos + 1)
    pos = m.end(0)
    pars = []
    while True:
        m = expr_continuation.match(text, pos)
        if not m:
            break

        # it was a dotted part; continue
        if m.group(1):
            pos = m.end(0)
            continue

        lex = JsLexer()
        # a braced expression is started, consume it
        for type, content in lex.lex(text, pos):
            pos += len(content)
            if content in braces:
                pars.append(content)

            elif content in braces.values():
                last = pars.pop()
                if braces[last] != content:
                    raise TemplateSyntaxError(
                        "Syntax error parsing interpolated expression",
                        node=text[pos - 1:])

                if not pars:
                    break

    expr = text[start_pos + 1:pos]
    return JavascriptExpression('$' + expr, expr)


def parse_expression(text, start_pos=0):
    if text[start_pos + 1] != '{':
        return parse_unenclosed_expression(text, start_pos)

    lex = JsLexer()
    braces = 0
    length = 2
    valid = False
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

    if not valid:
        raise ParseError("Unclosed braced Javascript expression",
                         charpos=length)

    return JavascriptExpression(text[start_pos:start_pos + length],
                                text[start_pos + 2: start_pos + length - 1])
