# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

"""Tonnikala compiler. Produces source code from XML."""

import re
from tonnikala.ir.nodes import Text, DynamicText, TranslatableText
from tonnikala.languages import python

_dollar_strip_re = re.compile(r'\$[a-zA-Z_{$]')


class HasExprException(Exception):
    pass


def _strip_dollars_fast(text):
    """
    Replace `$$` with `$`. raise immediately
    if `$` starting an interpolated expression is found.
    @param text: the source text
    @return: the text with dollars replaced, or raise
        HasExprException if there are interpolated expressions
    """

    def _sub(m):
        if m.group(0) == '$$':
            return '$'

        raise HasExprException()

    return _dollar_strip_re.sub(_sub, text)


_expr_find_code = re.compile(r"""
  ([^$]+)        # match any chars except \n or $ (group 1)
| (\$\$)         # match double dollars (group 2)
| (\$[{a-zA-Z_]) # match beginning of expressions (group 3)
| (\$)
""", re.VERBOSE | re.DOTALL)

_strip_ws_re = re.compile(r"""
    (\s*)
    (.*?)
    (\s*)$
""", re.VERBOSE | re.DOTALL)


def partition_translatable_text(text):
    m = _strip_ws_re.match(text)
    return m.groups()


def create_text_nodes(text, is_cdata=False, translatable=False):
    if not translatable:
        rv = Text(text)
        rv.is_cdata = is_cdata
        return rv

    prefix, this, suffix = partition_translatable_text(text)

    rv = []
    if prefix:
        rv.append(Text(prefix, is_cdata=is_cdata))

    if this:
        rv.append(TranslatableText(this, is_cdata=is_cdata))

    if suffix:
        rv.append(Text(suffix, is_cdata=is_cdata))

    if len(rv) == 1:
        return rv[0]

    node = DynamicText()
    for i in rv:
        node.add_child(i)

    return node


def handle_text_node(text, expr_parser=python.parse_expression, is_cdata=False,
                     translatable=False,
                     whole_translatable=False):
    try:
        text = _strip_dollars_fast(text)
        return create_text_nodes(text, is_cdata=is_cdata,
                                 translatable=translatable)

    except HasExprException:
        pass

    nodes = []
    stringrun = []
    max_index = len(text)
    pos = 0

    while pos < len(text):
        m = _expr_find_code.match(text, pos)
        pos = m.end()

        if m.group(1) != None:  # any
            stringrun.append(m.group(1))

        elif m.group(2):  # $$
            stringrun.append('$')

        elif m.group(3):
            if stringrun:
                nodes.append(create_text_nodes(''.join(stringrun),
                                               translatable=translatable))

            stringrun = []
            expr = expr_parser(text, m.start(3))
            pos = m.start(3) + len(expr.string)
            nodes.append(expr)

        else:  # group 4, a sole $
            stringrun.append('$')

    if stringrun:
        nodes.append(
            create_text_nodes(''.join(stringrun), translatable=translatable))

    if len(nodes) == 1:
        return nodes[0]

    node = DynamicText()
    for i in nodes:
        node.add_child(i)

    node.is_cdata = is_cdata
    for i in nodes:
        i.is_cdata = is_cdata
        i.translatable = translatable

    if whole_translatable:
        node.translatable = True

    return node
