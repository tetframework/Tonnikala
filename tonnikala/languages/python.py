# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__docformat__ = "epytext"

from tonnikala.exceptions import ParseError
from tonnikala.ir.nodes import ExpressionNode
from tokenize import generate_tokens
import re

class PythonExpressionNode(ExpressionNode):
    pass

identifier_match = re.compile(r'[a-zA-Z_][a-zA-Z_$0-9]*')

class TokenReadLine(object):
    def __init__(self, string, pos):
        self.string = string
        self.pos = pos
        self.lines = string[pos:].splitlines(True)
        self.lineiter = iter(self.lines)

    def __call__(self):
        return next(self.lineiter)

def parse_expression(text, start_pos=0):
    nodes = []

    if text[start_pos + 1] != '{':
        m = identifier_match.match(text, start_pos + 1)
        identifier = m.group(0)
        return PythonExpressionNode('$' + identifier, [('id', identifier)])

    braces = 0
    length = 2
    valid  = False
    tokens = generate_tokens(TokenReadLine(text, start_pos + 2))
    for type, content, start, end, line in tokens:
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
        raise ParseError("Not finished python expression", charpos=length)

    return PythonExpressionNode(text[start_pos:start_pos + length], nodes)
