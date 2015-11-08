# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import re
import token
from tokenize import generate_tokens, TokenError
from ...ir.nodes import InterpolatedExpression
from ...runtime.debug import TemplateSyntaxError
from ...compat import PY2, next_method, StringIO


class PythonExpression(InterpolatedExpression):
    pass


if PY2:  # pragma: no cover
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
        self.last_line = ''

    def readline(self):
        for l in self.io:
            self.last_line = l
            yield l

    def tell(self):
        return self.io.tell()

    def get_readline(self):
        return next_method(self.readline())


def gen_tokens(text, pos):
    """
    Generate position-adjusted python tokens from the given source text

    :param text: the source code
    :param pos: the adjusted position
    :return: a generator yielding the tokens
    """
    io = TokenReadLine(text, pos)
    readline = io.get_readline()
    tokens = generate_tokens(readline)

    try:
        for t_type, content, start, end, line in tokens:
            end_pos = io.tell() - len(io.last_line) + end[1]
            yield t_type, content, end_pos

    # tokenize will *throw* an exception at the end instead
    # of returning an error token under certain circumstances
    except TokenError as e:
        pos = len(text[:end_pos].rstrip())
        s = text[pos:]
        raise TemplateSyntaxError(e.args[0], node=s)


braces = {
    '(': ')',
    '[': ']',
}


def parse_brace_enclosed_expression(text, start_pos, position):
    n_braces = 0
    valid = False

    tokens = gen_tokens(text, start_pos + 2)
    for t_type, content, end_pos in tokens:
        if content == '}':
            if n_braces <= 0:
                valid = True
                break

            n_braces -= 1

        elif content == '{':
            n_braces += 1

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
        for t_type, content, end_pos in gen_tokens(text, pos):
            if content in braces:
                pars.append(content)

            elif content in braces.values():
                last = pars.pop()
                if braces[last] != content:
                    raise TemplateSyntaxError(
                        "Syntax error parsing interpolated expression",
                        node=text[end_pos - 1:])

                if not pars:
                    pos = end_pos
                    break

            elif token.ISEOF(t_type) or t_type == token.ERRORTOKEN:
                raise TemplateSyntaxError(
                    "Syntax error parsing interpolated expression",
                    node=text[end_pos:])

    expr = text[start_pos + 1:pos]
    return PythonExpression('$' + expr, expr)


def parse_expression(text, start_pos=0, position=(0, 0)):
    if text[start_pos + 1] != '{':
        return parse_unenclosed_expression(text, start_pos, position)

    return parse_brace_enclosed_expression(text, start_pos, position)
