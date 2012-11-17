# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from tonnikala.ir.nodes import Element, Text, If, For, Define, Import, EscapedText, MutableAttribute, ContainerNode, EscapedText, Root, DynamicAttributes
from tonnikala.expr     import handle_text_node # TODO: move this elsewhere.
from xml.dom.minidom    import Node
from tonnikala.ir.tree  import IRTree

__docformat__ = "epytext"

"""Generates IR nodes from XML parsetree"""

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
    meta
    param
    command
    keygen
    source
'''.split())



class IRGenerator(object):
    def __init__(self, document):
        self.dom_document = document
        self.tree = IRTree()
        self.empty_elements = html5_empty_tags

    def child_iter(self, node):
        if not node.firstChild:
            return

        current = node.firstChild
        while current:
            yield current
            current = current.nextSibling


    def map_guards(self, dom_node, ir_node):
        return ir_node


    def generate_attributes(self, dom_node, ir_node):
        attrs_node = self.grab_and_remove_control_attr(dom_node, 'attrs')
        if attrs_node:
            ir_node.set_dynamic_attrs(attrs_node)

        attrs = dict(dom_node.attributes)
        for name, attr in attrs.items():
            ir_node.set_attribute(name, handle_text_node(attr.nodeValue))



    def is_control_name(self, name, to_match):
        return 'py:' + to_match == name


    def grab_and_remove_control_attr(self, dom_node, name):
        name = 'py:' + name
        if dom_node.hasAttribute(name):
            value = dom_node.getAttribute(name)
            dom_node.removeAttribute(name)
            return value

        return None

    def create_control_node(self, dom_node):
        name = dom_node.tagName

        ir_node_stack = []

        if self.is_control_name(name, 'if'):
            ir_node_stack.append(If(dom_node.getAttribute('test')))

        if self.is_control_name(name, 'for'):
            ir_node_stack.append(For(dom_node.getAttribute('each')))

        if self.is_control_name(name, 'def'):
            ir_node_stack.append(Define(dom_node.getAttribute('function')))

        if self.is_control_name(name, 'import'):
            ir_node_stack.append(Import(dom_node.getAttribute('href'), dom_node.getAttribute('alias')))


        # TODO: add all node types in order
        generate_element = not bool(ir_node_stack)

        attr = self.grab_and_remove_control_attr(dom_node, 'if')
        if attr is not None:
            ir_node_stack.append(If(attr))

        attr = self.grab_and_remove_control_attr(dom_node, 'for')
        if attr is not None:
            ir_node_stack.append(For(attr))

        attr = self.grab_and_remove_control_attr(dom_node, 'def')
        if attr is not None:
            ir_node_stack.append(Define(attr))

        # TODO: add all control attrs in order
        if not ir_node_stack:
            return True, None, None

        top = ir_node_stack[0]
        bottom = ir_node_stack[-1]

        # link children
        while ir_node_stack:
            current = ir_node_stack.pop()

            if not ir_node_stack:
                break

            ir_node_stack[-1].add_child(current)

        return generate_element, top, bottom


    def generate_element_node(self, dom_node):
        generate_element, top_control, bottom_control = self.create_control_node(dom_node)

        bottom_node = bottom_control
        top_node = top_control

        if generate_element:
            el_ir_node = Element(dom_node.tagName)

            el_ir_node = self.map_guards(dom_node, el_ir_node)
            self.generate_attributes(dom_node, el_ir_node)

            if not top_node:
                top_node = el_ir_node

            if bottom_node:
                bottom_node.add_child(el_ir_node)

            bottom_node = el_ir_node
        
        self.add_children(self.child_iter(dom_node), bottom_node)
        return top_node


    def generate_ir_node(self, dom_node):
        node_t = dom_node.nodeType

        if node_t == Node.ELEMENT_NODE:
            return self.generate_element_node(dom_node)

        if node_t == Node.TEXT_NODE:
            ir_node = handle_text_node(dom_node.nodeValue)
            return ir_node

        if node_t == Node.COMMENT_NODE:
            # strip all ;)
            return None

        raise ValueError("Unhandled node type %d" % node_t)


    def add_children(self, children, ir_node):
        for dom_node in children:
            ir_node.add_child(self.generate_ir_node(dom_node))


    def generate_tree(self):
        root = Root()
        self.tree.add_child(root)
        self.add_children(self.child_iter(self.dom_document), root)
        return self.tree

    def render_constant_attributes(self, element):
        cattr = element.get_constant_attributes()
        code = []
        for name, value in cattr.items():
            code.append(' %s="%s"' % (name, value.escaped()))

        return ''.join(code)

    def flatten_element_nodes_on(self, node):
        new_children = []
        recurse = False
        for i in node.children:
            if not isinstance(i, Element):
                new_children.append(i)

            else:
                pre_text_node = '<%s' % i.name
                if i.attributes:
                    pre_text_node += self.render_constant_attributes(i)

                new_children.append(EscapedText(pre_text_node))
                if i.mutable_attributes:
                    for n, v in i.mutable_attributes.items():
                        new_children.append(MutableAttribute(n, v))

                if i.dynamic_attrs:
                    new_children.append(DynamicAttributes(i.dynamic_attrs))

                if not i.children:
                    if i.name in self.empty_elements:
                        new_children.append(EscapedText('/>'))
                        continue

                new_children.append(EscapedText('>'))
                merged = i.children
                for j in merged:
                    new_children.append(j)
                    if isinstance(j, Element):
                        recurse = True

                new_children.append(EscapedText('</%s>' % i.name))

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

    def _merge_text_nodes_on(self, node):
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
            self._merge_text_nodes_on(i)

    def merge_text_nodes(self, tree):
        root = tree.root
        self._merge_text_nodes_on(root)
        return tree
