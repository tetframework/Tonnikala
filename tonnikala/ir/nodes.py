# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals
from tonnikala.helpers import escape
import re

__docformat__ = "epytext"

try:
    unicode
except:
    unicode = str


class BaseNode(object):
    def __repr__(self):
        return self.__class__.__name__ + '(%s)' % str(self)


class Text(BaseNode):
    translatable = False

    def __init__(self, string):
        self.string = string

    def __str__(self):
        return self.string

    def escaped(self):
        return escape(self.string)


class EscapedText(Text):
    def __init__(self, string):
        super(EscapedText, self).__init__(string)

    def __str__(self):
        return self.string
    
    def escaped(self):
        return self.string


class Expression(BaseNode):
    def __init__(self, full_string, expression, tokens):
        self.string = full_string
        self.expression = expression
        self.tokens = tokens

    def __str__(self):
        return self.expression


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

    def __str__(self):
        return str(self.children)


class Root(ContainerNode):
    pass


class MutableAttribute(ContainerNode):
    def __init__(self, name, value):
        super(MutableAttribute, self).__init__()
        self.name = name
        self.value = value
        self.children.append(value)

    def __str__(self):
        return str({ self.name: self.value })


class DynamicAttributes(BaseNode):
    def __init__(self, expression):
        super(DynamicAttributes, self).__init__()
        self.expression = expression

    def __str__(self):
        return str(expression)


class ComplexExpression(ContainerNode):
    def __init__(self):
        super(ComplexExpression, self).__init__()
        pass

    def __str__(self):
        return str(self.children)


class Element(ContainerNode):
    def __init__(self, name, guard_expression=None):
        super(Element, self).__init__()
        self.name       = name
        self.guard_expression = guard_expression
        self.constant_attributes = {}
        self.mutable_attributes  = {}
        self.dynamic_attrs       = None

    def __str__(self):
        attrs = str(self.attributes)
        children = str(self.children)
        
        return ', '.join([self.name, 'guard=%s' % self.guard_expression, attrs, children])

    def get_guard_expression(self):
        return self.guard_expression

    def set_attribute(self, name, value):
        if isinstance(value, Text):
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


class Unless(ContainerNode):
    def __init__(self, expression):
        super(Unless, self).__init__()

        self.expression = expression

    def __str__(self):
        children = str(self.children)
        return ', '.join([("(%s)" % self.expression), children])
