# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__docformat__ = "epytext"

"""XML parser"""

import six
from six.moves import html_entities
from six import text_type

entitydefs = html_entities.entitydefs

from xml import sax

from tonnikala.ir.nodes import Element, Text, If, For, Define, Import, \
    EscapedText, MutableAttribute, ContainerNode, Block, Extends, \
    Root, DynamicAttributes, Unless, Expression, Comment, Code

from tonnikala.expr     import handle_text_node  # TODO: move this elsewhere.
from xml.dom.minidom    import Node
from tonnikala.ir.tree  import IRTree
from tonnikala.ir.generate import BaseDOMIRGenerator
from tonnikala.syntaxes.docparser import TonnikalaXMLParser, TonnikalaHTMLParser


class TonnikalaIRGenerator(BaseDOMIRGenerator):
    TRANSLATABLE_ATTRS = set([
        'title',
        'alt',
        'placeholder',
    ])
    def __init__(self, *a, **kw):
        super(TonnikalaIRGenerator, self).__init__(*a, **kw)
        self.state['translatable'] = True


    def is_translatable(self):
        return bool(self.state.translatable.get('translatable'))


    def set_translatable(self, is_translatable):
        self.push_state()['translatable'] = is_translatable

    def __init__(self, translatable=True, **kw):
        super(TonnikalaIRGenerator, self).__init__(**kw)

        self.translate = translatable

    def get_guard_expression(self, dom_node):
        return self.grab_and_remove_control_attr(dom_node, 'strip')

    def generate_attributes_for_node(self, dom_node, ir_node):
        attrs_node = self.grab_and_remove_control_attr(dom_node, 'attrs')
        attrs = [
            (k, handle_text_node(v, translatable=self.is_attr_translatable(k)))
            for (k, v)
            in dom_node.attributes.items()
        ]

        self.generate_attributes(ir_node, attrs=attrs, dynamic_attrs=attrs_node)

    # noinspection PyMethodMayBeStatic
    def is_control_name(self, name, to_match):
        return 'py:' + to_match == name

    # noinspection PyMethodMayBeStatic
    def grab_and_remove_control_attr(self, dom_node, name):
        name = 'py:' + name
        if dom_node.hasAttribute(name):
            value = dom_node.getAttribute(name)
            dom_node.removeAttribute(name)
            return value

        return None

    def create_control_nodes(self, dom_node):
        name = dom_node.tagName

        ir_node_stack = []

        if self.is_control_name(name, 'extends'):
            ir_node_stack.append(Extends(dom_node.getAttribute('href')))

        elif self.is_control_name(name, 'block'):
            ir_node_stack.append(Block(dom_node.getAttribute('name')))

        elif self.is_control_name(name, 'if'):
            ir_node_stack.append(If(dom_node.getAttribute('test')))

        elif self.is_control_name(name, 'for'):
            ir_node_stack.append(For(dom_node.getAttribute('each')))

        elif self.is_control_name(name, 'def'):
            ir_node_stack.append(Define(dom_node.getAttribute('function')))

        elif self.is_control_name(name, 'import'):
            ir_node_stack.append(Import(dom_node.getAttribute('href'), dom_node.getAttribute('alias')))

        # TODO: add all node types in order
        generate_element = not bool(ir_node_stack)
        attr = self.grab_and_remove_control_attr(dom_node, 'block')
        if attr is not None:
            ir_node_stack.append(Block(attr))

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
        generate_element, topmost, bottom = self.create_control_nodes(dom_node)

        guard_expression = self.get_guard_expression(dom_node)


        # on py:strip="" the expression is to be set to "1"
        if guard_expression is not None and not guard_expression.strip():
            guard_expression = '1'


        # facility to replace children for content control attr
        overridden_children = None
        content = self.grab_and_remove_control_attr(dom_node, 'content')
        if content:
            overridden_children = [ Expression(content) ]

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
            el_ir_node = Element(dom_node.tagName, guard_expression=guard_expression)
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
            ir_node = handle_text_node(
                dom_node.nodeValue,
                is_cdata=self.is_cdata,
                translatable=self.translate
            )
            return ir_node

        if node_t == Node.COMMENT_NODE:
            ir_node = EscapedText(u'<!--' + dom_node.nodeValue + u'-->')
            return ir_node

        if node_t == Node.PROCESSING_INSTRUCTION_NODE:
            ir_node = Code(dom_node.nodeValue.strip())
            return ir_node

        if node_t == Node.DOCUMENT_TYPE_NODE:
            ir_node = EscapedText(dom_node.toxml())
            return ir_node

        raise ValueError("Unhandled node type %d" % node_t)

    def is_attr_translatable(self, attr_name):
        return attr_name in self.TRANSLATABLE_ATTRS


def parse(filename, string):
    parser = TonnikalaHTMLParser(filename, string)
    parsed = parser.parse()
    generator = TonnikalaIRGenerator(document=parsed, translatable=True)
    tree = generator.generate_tree()
    tree = generator.flatten_element_nodes(tree)
    tree = generator.merge_text_nodes(tree)
    return tree
