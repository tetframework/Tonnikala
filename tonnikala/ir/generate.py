# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from tonnikala.ir.nodes import Element, Text
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


def generate_ir_node(dom_node):
    node_t = dom_node.nodeType
    if node_t == Node.ELEMENT_NODE:
        ir_node = Element(dom_node.tagName)
        ir_node = map_guards(dom_node, ir_node)
        generate_attributes(dom_node, ir_node)
        add_children(child_iter(dom_node), ir_node)
        return ir_node

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

