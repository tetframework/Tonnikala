# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

__docformat__ = "epytext"

import token

from ...exceptions import ParseError
from ...ir.nodes import InterpolatedExpression
from tokenize import generate_tokens
from ...runtime.debug import TemplateSyntaxError
from ...compat import PY2


try:
    from StringIO import StringIO
except:
    from io import StringIO

import re

class PythonExpression(InterpolatedExpression):
    pass


if PY2:
    identifier_match = re.compile(r'[^\d\W]\w*')
    expr_continuation = re.compile(r'[{([]|(\.[^\d\W]\w*)')
else:
    identifier_match = re.compile(r'[^\d\W]\w*', re.UNICODE)
    expr_continuation = re.compile(r'[([]|(\.[^\d\W]\w*)', re.UNICODE)


class TokenReadLine(object):
    def __init__(self, string, pos):
        self.string = string
        self.pos = pos
        self.io = StringIO(string)
        self.io.seek(pos)

    def readline(self):
        for l in self.io:
            self.last_line = l
            yield l

    def tell(self):
        return self.io.tell()

    def get_readline(self):
        return self.readline().__next__


def gen_tokens(text, pos):
    io = TokenReadLine(text, pos)
    readline = io.get_readline()
    tokens = generate_tokens(readline)

    for type, content, start, end, line in tokens:
        end_pos = io.tell() - len(io.last_line) + end[1]
        yield type, content, end_pos


braces = {
    '(': ')',
    '[': ']', 
}


def parse_brace_enclosed_expression(text, start_pos, position):
    braces = 0
    length = 2
    valid  = False

    tokens = gen_tokens(text, start_pos + 2)
    for type, content, end_pos in tokens:
        if content == '}':
            if braces <= 0:
                valid = True
                break

            braces -= 1

        elif content == '{':
            braces += 1

    if not valid:
        pos = len(text[:end_pos].rstrip())
        s = text[pos:]
        raise TemplateSyntaxError("Unclosed braced Python expression", node=s)

    return PythonExpression(text[start_pos:end_pos],
                            text[start_pos + 2: end_pos - 1])


def parse_unenclosed_expression(text, start_pos, position):
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

        # a braced expression is started, consume it
        for type, content, end_pos in gen_tokens(text, pos):
            if content in braces:
                pars.append(content)
 
            elif content in braces.values():
                last = pars.pop()
                if braces[last] != content:
                    raise TemplateSyntaxError(
                        "Syntax error parsing interpolated expression",
                        node=text[end_pos-1:])
                    
                if not pars:
                    pos = end_pos
                    break

            elif token.ISEOF(type) or type == token.ERRORTOKEN:
                raise TemplateSyntaxError(
                    "Syntax error parsing interpolated expression",
                    node=text[end_pos:])

    expr = text[start_pos + 1:pos]
    return PythonExpression('$' + expr, expr)


def parse_expression(text, start_pos=0, position=(0, 0)):
    nodes = []

    if text[start_pos + 1] != '{':
        return parse_unenclosed_expression(text, start_pos, position)

    return parse_brace_enclosed_expression(text, start_pos, position)
