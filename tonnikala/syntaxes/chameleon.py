# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, \
    unicode_literals

"""XML parser"""

from tonnikala.ir.nodes import Element, If, For, EscapedText, Expression
from xml.dom.minidom import Node

from tonnikala.expr import handle_text_node  # TODO: move this elsewhere.
from tonnikala.ir.generate import BaseDOMIRGenerator
from tonnikala.syntaxes.docparser import \
    TonnikalaHTMLParser


# noinspection PyMethodMayBeStatic
class ChameleonIRGenerator(BaseDOMIRGenerator):
    def __init__(self, *a, **kw):
        super(ChameleonIRGenerator, self).__init__(*a, **kw)

    def get_guard_expression(self, dom_node):
        return self.grab_and_remove_control_attr(dom_node, 'omit-tag')

    def generate_attributes_for_node(self, dom_node, ir_node):
        attrs_node = self.grab_and_remove_control_attr(dom_node, 'attrs')
        attrs = [(k, handle_text_node(v)) for (k, v) in
                 dom_node.attributes.items()]
        self.generate_attributes(ir_node, attrs=attrs, dynamic_attrs=attrs_node)

    def is_control_name(self, name, to_match):
        return 'tal:' + to_match == name

    def grab_and_remove_control_attr(self, dom_node, name):
        name = 'tal:' + name
        if dom_node.hasAttribute(name):
            value = dom_node.getAttribute(name)
            dom_node.removeAttribute(name)
            return value

        return None

    def create_control_nodes(self, dom_node):
        name = dom_node.tagName

        ir_node_stack = []

        # if self.is_control_name(name, 'import'):
        #    ir_node_stack.append(Import(dom_node.getAttribute('href'),
        # dom_node.getAttribute('alias')))

        # TODO: add all node types in order
        generate_element = not bool(ir_node_stack)
        attr = self.grab_and_remove_control_attr(dom_node, 'condition')
        if attr is not None:
            ir_node_stack.append(If(attr))

        attr = self.grab_and_remove_control_attr(dom_node, 'repeat')
        if attr is not None:
            ir_node_stack.append(For(attr))

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
        generate_element, topmost, bottom = self.create_control_nodes(dom_node)

        guard_expression = self.get_guard_expression(dom_node)

        # on py:strip="" the expression is to be set to "1"
        if guard_expression is not None and not guard_expression.strip():
            guard_expression = '1'

        # facility to replace children for content control attr
        overridden_children = None
        content = self.grab_and_remove_control_attr(dom_node, 'content')
        if content:
            overridden_children = [Expression(content)]

        if self.is_control_name(dom_node.tagName, 'replace'):
            replace = dom_node.getAttribute('value')
            if replace is None:
                raise ValueError("No value attribute specified for replace tag")
        else:
            replace = self.grab_and_remove_control_attr(dom_node, 'replace')

        add_children = True
        el_ir_node = None
        if replace is not None:
            el_ir_node = Expression(replace)
            add_children = False
            generate_element = False

        if generate_element:
            el_ir_node = Element(dom_node.tagName,
                                 guard_expression=guard_expression)
            self.generate_attributes_for_node(dom_node, el_ir_node)

        if not topmost:
            topmost = el_ir_node

        if el_ir_node:
            if bottom:
                bottom.add_child(el_ir_node)

            bottom = el_ir_node

        if add_children:
            if overridden_children:
                bottom.children = overridden_children
            else:
                self.add_children(self.child_iter(dom_node), bottom)

        return topmost

    def generate_ir_node(self, dom_node):
        node_t = dom_node.nodeType

        if node_t == Node.ELEMENT_NODE:
            return self.generate_element_node(dom_node)

        if node_t == Node.TEXT_NODE:
            ir_node = handle_text_node(dom_node.nodeValue,
                                       is_cdata=self.is_cdata)
            return ir_node

        if node_t == Node.COMMENT_NODE:
            ir_node = EscapedText(u'<!--' + dom_node.nodeValue + u'-->')
            return ir_node

        raise ValueError("Unhandled node type %d" % node_t)


def parse(filename, string, translatable=False):
    if translatable:
        raise ValueError("L10n not implemented for Chameleon templates")

    parser = TonnikalaHTMLParser(filename, string)
    parsed = parser.parse()
    generator = ChameleonIRGenerator(parsed)
    tree = generator.generate_tree()

    tree = generator.flatten_element_nodes(tree)
    tree = generator.merge_text_nodes(tree)
    return tree
