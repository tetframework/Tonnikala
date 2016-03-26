# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, \
    unicode_literals

"""Generates IR nodes from DOM tree"""

from .nodes import (Element, Text,
                    MutableAttribute, ContainerNode, EscapedText, Root,
                    DynamicAttributes, Unless, Comment, IRTree)

from ..runtime.exceptions import TemplateSyntaxError

html5_empty_tags = frozenset('''
    br
    hr
    input
    area
    base
    br
    col
    hr
    img
    link
    meta
    param
    command
    keygen
    source
'''.split())

html5_cdata_elements = frozenset('''
    script
    style
'''.split())


class all_set(object):
    def __contains__(self, value):
        return True


class BaseIRGenerator(object):
    def __init__(self, filename=None, source=None, *a, **kw):
        super(BaseIRGenerator, self).__init__(*a, **kw)
        self.filename = filename
        self.source = source
        self.states = [{}]
        self.tree = IRTree()

    def syntax_error(self, message, lineno=None):
        raise TemplateSyntaxError(
            message,
            lineno,
            source=self.source,
            filename=self.filename)

    def merge_text_nodes_on(self, node):
        """Merges all consecutive non-translatable text nodes into one"""

        if not isinstance(node, ContainerNode) or not node.children:
            return

        new_children = []
        text_run = []
        for i in node.children:
            if isinstance(i, Text) and not i.translatable:
                text_run.append(i.escaped())
            else:
                if text_run:
                    new_children.append(EscapedText(''.join(text_run)))
                    text_run = []

                new_children.append(i)

        if text_run:
            new_children.append(EscapedText(''.join(text_run)))

        node.children = new_children
        for i in node.children:
            self.merge_text_nodes_on(i)

    def merge_text_nodes(self, tree):
        root = tree.root
        self.merge_text_nodes_on(root)
        return tree

    @property
    def state(self):
        """
        Return the current state from the state stack
        """

        return self.states[-1]

    def push_state(self):
        """
        Push a copy of the topmost state on top of the state stack,
        returns the new top.
        """

        new = dict(self.states[-1])
        self.states.append(new)
        return self.state

    def pop_state(self):
        """
        Pop the topmost state from the state stack, return
        the *new* top
        """

        self.states.pop()
        return self.state


class Validator(object):
    def __init__(self, domirgen):
        self.domirgen = domirgen

    def syntax_error(self, message, node=None, lineno=None):
        source = self.domirgen.source
        filename = self.domirgen.filename
        lineno = node.position[0]
        raise TemplateSyntaxError(message=message, source=source,
                                  filename=filename, lineno=lineno)


class BaseDOMIRGenerator(BaseIRGenerator):
    def __init__(self, document=None, mode='html5', *a, **kw):
        super(BaseDOMIRGenerator, self).__init__(*a, **kw)
        self.dom_document = document
        self.mode = mode
        self.is_cdata = False

        if mode in ['html', 'html5', 'xhtml']:
            self.empty_elements = html5_empty_tags
            self.cdata_elements = html5_cdata_elements
            self.empty_tag_closing_string = ' />'

        elif mode == 'xml':
            self.empty_elements = all_set()
            self.empty_tag_closing_string = '/>'
            self.cdata_elements = set()

        else:  # pragma: no cover
            raise ValueError("Unknown render mode '%s'" % mode)

    def child_iter(self, node):
        current = node.firstChild
        while current:
            yield current
            current = current.nextSibling

    def generate_attributes(self, ir_node, attrs=[], dynamic_attrs=None):
        if dynamic_attrs:
            ir_node.set_dynamic_attrs(dynamic_attrs)

        for name, value in attrs:
            ir_node.set_attribute(name, value)

    def generate_ir_node(self, dom_node):  # pragma: no cover
        raise NotImplementedError('abstract method not implemented')

    def add_children(self, children, ir_node):
        is_cdata_save = self.is_cdata
        if isinstance(ir_node, Element) \
                and ir_node.name in self.cdata_elements:

            self.is_cdata = True

        for dom_node in children:
            node = self.generate_ir_node(dom_node)
            if node:
                ir_node.add_child(node)

        self.is_cdata = is_cdata_save

    def render_constant_attributes(self, element):
        cattr = element.get_constant_attributes()
        code = []
        for name, value in cattr.items():
            code.append(' %s="%s"' % (name, value.escaped()))

        return ''.join(code)

    def get_start_tag_nodes(self, element):
        start_tag_nodes = []
        pre_text_node = '<%s' % element.name
        if element.attributes:
            pre_text_node += self.render_constant_attributes(element)

        start_tag_nodes.append(EscapedText(pre_text_node))
        if element.mutable_attributes:
            for n, v in element.mutable_attributes.items():
                start_tag_nodes.append(MutableAttribute(n, v))

        if element.dynamic_attrs:
            start_tag_nodes.append(DynamicAttributes(element.dynamic_attrs))

        return start_tag_nodes

    def flatten_element_nodes_on(self, node):
        new_children = []
        recurse = False
        for i in node.children:
            if not isinstance(i, (Element, Comment)):
                new_children.append(i)
                continue

            elif isinstance(i, Comment):
                new_children.append(EscapedText('<!--'))
                new_children.append(EscapedText(i.escaped()))
                new_children.append(EscapedText('-->'))

            else:
                # this is complicated because of the stupid strip syntax :)
                start_tag_nodes = self.get_start_tag_nodes(i)
                end_tag_nodes = []

                # if no children, then 1 guard is enough
                if not i.children:
                    if i.name in self.empty_elements:
                        start_tag_nodes.append(
                            EscapedText(self.empty_tag_closing_string))

                    else:
                        start_tag_nodes.append(EscapedText('></%s>' % i.name))

                else:
                    start_tag_nodes.append(EscapedText('>'))
                    end_tag_nodes = [EscapedText('</%s>' % i.name)]

                child_nodes = []
                for j in i.children:
                    child_nodes.append(j)
                    if isinstance(j, Element):
                        recurse = True

                # if there is a guard...
                guard = i.get_guard_expression()
                if guard is not None:
                    start_tag = Unless(guard)
                    start_tag.children = start_tag_nodes
                    start_tag_nodes = [start_tag]

                    if end_tag_nodes:
                        end_tag = Unless(guard)
                        end_tag.children = end_tag_nodes
                        end_tag_nodes = [end_tag]

                new_children.extend(start_tag_nodes)
                new_children.extend(child_nodes)
                new_children.extend(end_tag_nodes)

        node.children = new_children

        if recurse:
            self.flatten_element_nodes_on(node)

        for i in node.children:
            if hasattr(i, 'children') and i.children:
                self.flatten_element_nodes_on(i)

    def flatten_element_nodes(self, tree):
        root = tree.root
        self.flatten_element_nodes_on(root)
        return tree

    def generate_tree(self):
        root = Root()
        self.tree.add_child(root)
        self.add_children(self.child_iter(self.dom_document), root)
        validator = Validator(self)
        root.validate(validator)
        return self.tree
