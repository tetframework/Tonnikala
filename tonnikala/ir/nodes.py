# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__docformat__ = "epytext"


class BaseNode(object):
    def __repr__(self):
        return self.__class__.__name__ + '(%r)' % str(self)


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


class Element(BaseNode):
    def __init__(self, name):
        self.name       = name
        self.attributes = {}
        self.guard      = None
        self.children   = []

    def add_child(self, child):
        self.children.append(child)

    def set_attribute(self, name, value):
        self.attributes[name] = value
    
    def __str__(self):
        return ',\n'.join(repr(i) for i in self.children)
