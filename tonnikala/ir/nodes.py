# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals


import collections

import re

from tonnikala.helpers import escape
from ..compat import text_type
from collections import OrderedDict


class BaseNode(object):
    position = (None, None)

    def __repr__(self):
        return self.__class__.__name__ + '(%s)' % str(self)

    def validate(self, validator):
        pass

    def get_children(self):
        return []


class Text(BaseNode):
    is_cdata = False
    translatable = False

    def __init__(self, text, is_cdata=False):
        self.text = text
        self.is_cdata = is_cdata

    def __str__(self):  # pragma: no cover
        return self.text

    def escaped(self):
        if self.is_cdata:
            return self.text

        return escape(self.text)


class TranslatableText(Text):
    translatable = True

    def __init__(self, text, is_cdata=False):
        super(TranslatableText, self).__init__(text, is_cdata=is_cdata)

    def __str__(self):  # pragma: no cover
        return '_t(%s)' % self.text

    @property
    def needs_escape(self):
        return not self.is_cdata

    def escaped(self):
        if self.is_cdata:
            return self.text

        return escape(self.text)


def escape_comment(text):
    if text.startswith('>'):
        text = text.replace('>', '&gt', 1)

    if text.endswith('-'):
        text = text[:-1] + '&#45;'

    return text.replace('--', '&#45;&#45;')


class Comment(BaseNode):
    def __init__(self, text):
        self.text = text

    def escaped(self):
        return escape_comment(self.text)

    def __str__(self):  # pragma: no cover
        return self.text


class EscapedText(Text):
    def __init__(self, string):
        super(EscapedText, self).__init__(string)

    def __str__(self):  # pragma: no cover
        return self.text

    def escaped(self):
        return self.text


class Expression(BaseNode):
    is_cdata = False

    def __init__(self, expression):
        self.expression = expression

    def __str__(self):  # pragma: no cover
        return self.expression


class Code(BaseNode):
    is_cdata = False

    def __init__(self, source):
        self.source = source

    def __str__(self):  # pragma: no cover
        return self.source


class InterpolatedExpression(Expression):
    def __init__(self, full_string, expression):
        super(InterpolatedExpression, self).__init__(expression)
        self.string = full_string


class ContainerNode(BaseNode):
    def __init__(self):
        self.attributes = OrderedDict()
        self.children   = []

    def add_child(self, child):
        """
        Add a child to the tree. Subclasses may raise SyntaxError
        """
        self.children.append(child)

    def set_attribute(self, name, value):
        self.attributes[name] = value

    def __repr__(self):
        return self.__class__.__name__ + '(%s)' % str(self)

    def __str__(self):  # pragma: no cover
        return str(self.children)

    def validate(self, validator):
        for i in self.children:
            i.validate(validator)

        super(ContainerNode, self).validate(validator)


class Root(ContainerNode):
    pass


class MutableAttribute(ContainerNode):
    def __init__(self, name, value):
        super(MutableAttribute, self).__init__()
        self.name = name
        self.value = value
        self.children.append(value)

    def __str__(self):  # pragma: no cover
        return str({self.name: self.value})

    def get_children(self):
        return self.children


class DynamicAttributes(BaseNode):
    def __init__(self, expression):
        super(DynamicAttributes, self).__init__()
        self.expression = expression

    def __str__(self):  # pragma: no cover
        return str(self.expression)

    def get_children(self):
        return [self.expression]


class DynamicText(ContainerNode):
    def __init__(self):
        super(DynamicText, self).__init__()
        pass

    def __str__(self):  # pragma: no cover
        return str(self.children)


class Element(ContainerNode):
    def __init__(self, name, guard_expression=None):
        super(Element, self).__init__()
        self.name = name
        self.guard_expression = guard_expression
        self.constant_attributes = OrderedDict()
        self.mutable_attributes  = OrderedDict()
        self.dynamic_attrs       = None

    def __str__(self):  # pragma: no cover
        attrs = str(self.attributes)
        children = str(self.children)

        return ', '.join([self.name, 'guard=%s' % self.guard_expression, attrs, children])

    def get_guard_expression(self):
        return self.guard_expression

    def set_attribute(self, name, value):
        if isinstance(value, Text) and not value.translatable:
            self.constant_attributes[name] = value
        else:
            self.mutable_attributes[name] = value

        self.attributes[name] = value

    def set_dynamic_attrs(self, expression):
        self.dynamic_attrs = expression

    def get_constant_attributes(self):
        return self.constant_attributes

    def get_mutable_attributes(self):
        return self.mutable_attributes


class For(ContainerNode):
    IN_RE = re.compile('\s+in\s+')

    def __init__(self, expression):
        super(For, self).__init__()

        self.expression = expression
        self.parts = self.IN_RE.split(self.expression, 1)

    def validate(self, validator):
        if len(self.parts) != 2:
            validator.syntax_error(
                "for does not have proper format: var[, var...] in expression",
                node=self)

        super(For, self).validate(validator)

    def __str__(self):  # pragma: no cover
        children = str(self.children)
        return ', '.join([("(%s in %s)" % tuple(self.parts)), children])


class Define(ContainerNode):
    def __init__(self, funcspec):
        super(Define, self).__init__()

        self.funcspec = funcspec

    def __str__(self):  # pragma: no cover
        return ', '.join([self.funcspec, text_type(self.children)])


class Import(BaseNode):
    def __init__(self, href, alias):
        super(Import, self).__init__()

        self.href = href
        self.alias = alias

    def __str__(self):  # pragma: no cover
        return ', '.join([self.href, self.alias])


class If(ContainerNode):
    def __init__(self, expression):
        super(If, self).__init__()

        self.expression = expression

    def __str__(self):  # pragma: no cover
        children = str(self.children)
        return ', '.join([("(%s)" % self.expression), children])


class Unless(ContainerNode):
    def __init__(self, expression):
        super(Unless, self).__init__()

        self.expression = expression

    def __str__(self):  # pragma: no cover
        children = str(self.children)
        return ', '.join([("(%s)" % self.expression), children])


class Block(ContainerNode):
    def __init__(self, name):
        super(Block, self).__init__()
        self.name = name

    def __str__(self):  # pragma: no cover
        children = str(self.children)
        return "%s, %s" % (repr(self.name), children)


class With(ContainerNode):
    def __init__(self, vars):
        super(With, self).__init__()
        self.vars = vars

    def __str__(self):  # pragma: no cover
        children = str(self.children)
        return "%s, %s" % (repr(self.vars), children)


class Extends(ContainerNode):
    def __init__(self, href):
        super(Extends, self).__init__()

        self.href = href

    def __str__(self):  # pragma: no cover
        children = str(self.children)
        return ', '.join([("(%s)" % self.expression), children])

    def add_child(self, child):
        """
        Add a child to the tree. Extends discards all comments
        and whitespace Text. On non-whitespace Text, and any
        other nodes, raise a syntax error.
        """

        if isinstance(child, Comment):
            return

        # ignore Text nodes with whitespace-only content
        if isinstance(child, Text) and not child.text.strip():
            return

        super(Extends, self).add_child(child)

    def validate(self, validator):
        for child in self.children:
            if isinstance(child, Text):
                validator.syntax_error(
                    "No Text allowed within an Extends block", node=child)

            if not isinstance(child, (Block, Define, Import)):
                validator.syntax_error(
                    "Only nodes of type Block, Import or Define "
                    "allowed within an Extends block, not %s" %
                        child.__class__.__name__,
                    child
                )

        super(Extends, self).validate(validator)


class IRTree(object):
    def __init__(self):
        self.root = None

    def add_child(self, root):
        self.root = root

    def get_root(self):
        return self.root

    def __str__(self):  # pragma: no cover
        return repr(self)

    def __repr__(self):
        return 'IRTree(%r)' % self.root

    def __iter__(self):
        stack = collections.deque()
        stack.append(self.root)
        while stack:
            item = stack.popleft()
            if hasattr(item, 'children'):
                stack.extendleft(item.children or [])
            yield item
