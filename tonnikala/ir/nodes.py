# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals
import re
__docformat__ = "epytext"


class BaseNode(object):
    def __repr__(self):
        return self.__class__.__name__ + '(%s)' % str(self)


class Text(BaseNode):
    def __init__(self, string):
        self.string = string

    def __str__(self):
        return self.string


class ComplexExpression(BaseNode):
    def __init__(self, parts):
        self.parts = parts

    def __repr__(self):
        return self.__class__.__name__ + '(%s)' % ', '.join(repr(i) for i in self.parts)

    def __str__(self):
        return ''.join(str(i) for i in self.parts)


class Expression(BaseNode):
    def __init__(self, string, tokens):
        self.string = string
        self.tokens = tokens

    def __str__(self):
        return self.string


class ContainerNode(BaseNode):
    def __init__(self):
        self.attributes = {}
        self.children   = []

    def add_child(self, child):
        self.children.append(child)

    def set_attribute(self, name, value):
        self.attributes[name] = value

    def __repr__(self):
        return self.__class__.__name__ + '(%s)' % str(self)


class Element(ContainerNode):
    def __init__(self, name):
        super(Element, self).__init__()
        self.name       = name
        self.guard      = None

    def __str__(self):
        attrs = str(self.attributes)
        children = str(self.children)
        
        return ', '.join([self.name, attrs, children])


class For(ContainerNode):
    IN_RE = re.compile('\s+in\s+')

    def __init__(self, expression):
        super(For, self).__init__()

        self.expression = expression
        self.parts = self.IN_RE.split(self.expression, 1)

        if len(self.parts) != 2:
            raise ValueError("for does not have proper format: var[, var...] in expression")

    def __str__(self):
        children = str(self.children)
        return ', '.join([("(%s in %s)" % tuple(self.parts)), children])


class Define(ContainerNode):
    def __init__(self, funcspec):
        super(Define, self).__init__()

        self.funcspec = funcspec

    def __str__(self):
        return ', '.join([self.funcspec, unicode(self.children)])

class Import(BaseNode):
    def __init__(self, href, alias):
        super(Import, self).__init__()

        self.href = href
        self.alias = alias

    def __str__(self):
        return ', '.join([self.href, self.alias])


class If(ContainerNode):
    def __init__(self, expression):
        super(If, self).__init__()

        self.expression = expression

    def __str__(self):
        children = str(self.children)
        return ', '.join([("(%s)" % self.expression), children])

