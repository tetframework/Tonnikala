# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__docformat__ = "epytext"

from tonnikala.exceptions import ParseError
from tonnikala.ir.nodes import InterpolatedExpression
from tokenize import generate_tokens

try:
    from StringIO import StringIO
except:
    from io import StringIO

import re

class PythonExpression(InterpolatedExpression):
    pass

identifier_match = re.compile(r'[a-zA-Z_][a-zA-Z_$0-9]*')

class TokenReadLine(object):
    def __init__(self, string, pos):
        self.string = string
        self.pos = pos
        self.io = StringIO(string)
        self.io.seek(pos)
        self.length = 0

    def get_readline(self):
        return self.io.readline

    def get_distance(self):
        return self.io.tell() - self.pos

def parse_expression(text, start_pos=0):
    nodes = []

    if text[start_pos + 1] != '{':
        m = identifier_match.match(text, start_pos + 1)
        identifier = m.group(0)
        return PythonExpression('$' + identifier, identifier, [('id', identifier)])

    braces = 0
    length = 2
    valid  = False
    io = TokenReadLine(text, start_pos + 2)
    readline = io.get_readline()
    tokens = generate_tokens(readline)
    binary = False

    for type, content, start, end, line in tokens:
        if content in [ 'b', 'B' ]:
            binary = True
            binary_pos = end

        elif binary and content[-1:] in '"\'':
            binary = False

            if binary_pos == start and line[binary_pos - 1] in 'bB':
                nodes.pop()
                nodes.append((type, line[binary_pos - 1] + content))

        else:
            binary = False

        if content == '}':
            if braces <= 0:
                length += io.get_distance() - len(line) + end[1]
                valid = True
                break

            braces -= 1

        elif content == '{':
            braces += 1

        nodes.append((type, content))

    if not valid:
        raise ParseError("Not finished python expression", charpos=length)

    return PythonExpression(text[start_pos:start_pos + length], text[start_pos + 2: start_pos + length - 1], nodes)
