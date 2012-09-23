# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from tonnikala.ir.nodes import Element, Text, If, For
from tonnikala.expr     import handle_text_node # TODO: move this elsewhere.
from xml.dom.minidom    import Node

__docformat__ = "epytext"

"""Generates IR nodes from XML parsetree"""


def child_iter(node):
    if not node.firstChild:
        return

    current = node.firstChild
    while current:
        yield current
        current = current.nextSibling


def map_guards(dom_node, ir_node):
    return ir_node


def generate_attributes(dom_node, ir_node):
    attrs = dict(dom_node.attributes)
    for name, attr in attrs.iteritems():
        ir_node.set_attribute(name, handle_text_node(attr.nodeValue))


def create_control_node(dom_node):
    name = dom_node.tagName

    ir_node_stack = []

    if name == 'py:if':
        ir_node_stack.append(If(dom_node.getAttribute('test')))

    if name == 'py:for':
        ir_node_stack.append(For(dom_node.getAttribute('each')))

    # TODO: add all node types in order
    generate_element = not bool(ir_node_stack)

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

def generate_element_node(dom_node):
    generate_element, top_control, bottom_control = create_control_node(dom_node)

    bottom_node = bottom_control
    top_node = top_control

    print(generate_element, top_control, bottom_control)
    if generate_element:
        el_ir_node = Element(dom_node.tagName)
        el_ir_node = map_guards(dom_node, el_ir_node)
        generate_attributes(dom_node, el_ir_node)

        if not top_node:
            top_node = el_ir_node

        if bottom_node:
            bottom_node.add_child(el_ir_node)

        bottom_node = el_ir_node
    
    add_children(child_iter(dom_node), bottom_node)
    return top_node


def generate_ir_node(dom_node):
    node_t = dom_node.nodeType

    if node_t == Node.ELEMENT_NODE:
        return generate_element_node(dom_node)

    if node_t == Node.TEXT_NODE:
        ir_node = handle_text_node(dom_node.nodeValue)
        return ir_node

    if node_t == Node.COMMENT_NODE:
        # strip all ;)
        return None

    raise ValueError("Unhandled node type %d" % node_t)


def add_children(children, ir_node):
    for dom_node in children:
        ir_node.add_child(generate_ir_node(dom_node))


def generate_ir_tree(dom_document):
    root = Element('root')
    add_children(child_iter(dom_document), root)
    return root

