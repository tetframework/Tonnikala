# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, \
    unicode_literals


"""XML parser"""

from xml.dom.minidom import Node
from tonnikala.ir.nodes import Element, If, For, Define, Import, \
    EscapedText, Block, Extends, \
    Expression, Code, With
from ..expr import handle_text_node  # TODO: move this elsewhere.
from ..ir.generate import BaseDOMIRGenerator
from .docparser import TonnikalaHTMLParser


class TonnikalaIRGenerator(BaseDOMIRGenerator):
    control_prefix = 'py:'

    TRANSLATABLE_ATTRS = {'title', 'alt', 'placeholder', 'value', 'caption'}

    def __init__(self, translatable=False, *a, **kw):
        if 'control_prefix' in kw:
            self.control_prefix = kw.pop('control_prefix') + ':'

        self.xmlns = 'xmlns:' + self.control_prefix.replace(':', '')

        super(TonnikalaIRGenerator, self).__init__(*a, **kw)
        self.state['translatable'] = translatable

    def is_translatable(self):
        return bool(self.state.get('translatable'))

    def set_translatable(self, is_translatable):
        self.push_state()['translatable'] = is_translatable

    def get_guard_expression(self, dom_node):
        return self.grab_and_remove_control_attr(dom_node, 'strip')

    def generate_attributes_for_node(self, dom_node, ir_node):
        attrs_node = self.grab_and_remove_control_attr(dom_node, 'attrs')
        if dom_node.hasAttribute(self.xmlns):
            dom_node.removeAttribute(self.xmlns)

        # if there are control nodes present at this stage, complain aloud
        for k, v in dom_node.attributes.items():
             if k.startswith(self.control_prefix):
                 self.syntax_error("Unknown control attribute {}".format(k),
                     node=v)

        attrs = [
            (k, handle_text_node(v, translatable=self.is_attr_translatable(k)))
            for (k, v)
            in dom_node.attributes.items()
        ]

        self.generate_attributes(ir_node, attrs=attrs, dynamic_attrs=attrs_node)

    def control_name(self, name):
        if name.startswith(self.control_prefix):
            return name.replace(self.control_prefix, '', 1)

        return None

    # noinspection PyMethodMayBeStatic
    def is_control_name(self, name, to_match):
        return self.control_name(name) == to_match

    # noinspection PyMethodMayBeStatic
    def grab_and_remove_control_attr(self, dom_node, name):
        name = self.control_prefix + name
        if dom_node.hasAttribute(name):
            value = dom_node.getAttribute(name)
            dom_node.removeAttribute(name)
            return value

        return None

    def syntax_error(self, message, node=None, lineno=None):
        if lineno is None:
            if node:
                lineno = getattr(node, 'position', (0, 0))[0]
            else:
                lineno = 0

        BaseDOMIRGenerator.syntax_error(
            self,
            message=message,
            lineno=lineno)

    def grab_mandatory_attribute(self, dom_node, name):
        if not dom_node.hasAttribute(name):
            self.syntax_error(
                message="<{}> does not have the required attribute '{}'"
                        .format(dom_node.name, name),
                node=dom_node)
        return dom_node.getAttribute(name)

    def create_control_nodes(self, dom_node):
        name = dom_node.tagName

        ir_node_stack = []

        def make_control_node(node_name, irtype, *attrs):
            if not self.is_control_name(name, node_name):
                return

            args = [self.grab_mandatory_attribute(dom_node, i) for i in attrs]
            irnode = irtype(*args)
            irnode.position = dom_node.position
            ir_node_stack.append(irnode)

        make_control_node('extends', Extends, 'href')
        make_control_node('block', Block, 'name')
        make_control_node('if', If, 'test')
        make_control_node('for', For, 'each')
        make_control_node('def', Define, 'function')
        make_control_node('import', Import, 'href', 'alias')
        make_control_node('with', With, 'vars')
        make_control_node('vars', With, 'names')

        # TODO: add all node types in order
        generate_element = not bool(ir_node_stack)

        def make_control_node_of_attr(irtype, name):
            attr = self.grab_and_remove_control_attr(dom_node, name)
            if attr is not None:
                irnode = irtype(attr)
                irnode.position = getattr(attr, 'position', (0, 0))
                ir_node_stack.append(irnode)

        make_control_node_of_attr(Block, 'block')
        make_control_node_of_attr(If, 'if')
        make_control_node_of_attr(For, 'for')
        make_control_node_of_attr(Define, 'def')
        make_control_node_of_attr(With, 'with')
        make_control_node_of_attr(With, 'vars')

        # TODO: add all control attrs in order
        if not ir_node_stack:
            return True, None, None

        top = ir_node_stack[0]
        bottom = ir_node_stack[-1]

        # link children
        while True:
            current = ir_node_stack.pop()

            if not ir_node_stack:
                break

            ir_node_stack[-1].add_child(current)

        return generate_element, top, bottom

    def generate_element_node(self, dom_node):
        generate_element, topmost, bottom = self.create_control_nodes(dom_node)

        guard_expression = self.get_guard_expression(dom_node)

        # on :strip="" the expression is to be set to "1"
        if guard_expression is not None and not guard_expression.strip():
            guard_expression = '1'

        # facility to replace children for content control attr
        overridden_children = None
        content = self.grab_and_remove_control_attr(dom_node, 'content')
        if content:
            overridden_children = [Expression(content)]

        if self.is_control_name(dom_node.tagName, 'replace'):
            replace = self.grab_mandatory_attribute(dom_node, 'value')
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

        # raise syntax error for unknown control node names
        if generate_element and self.control_name(dom_node.tagName):
            self.syntax_error('Unknown control element <{}>'
                              .format(dom_node.tagName), node=dom_node)

        return topmost

    def generate_ir_node(self, dom_node):
        node_t = dom_node.nodeType

        if node_t == Node.ELEMENT_NODE:
            return self.generate_element_node(dom_node)

        if node_t == Node.TEXT_NODE:
            ir_node = handle_text_node(
                dom_node.nodeValue,
                is_cdata=self.is_cdata,
                translatable=self.is_translatable()
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

        self.syntax_error('Unhandled node type %d' % node_t, node=dom_node)

    def is_attr_translatable(self, attr_name):
        return bool(self.state.get(
            'translatable')) and attr_name in self.TRANSLATABLE_ATTRS


def parse(filename, string, translatable=False):
    parser = TonnikalaHTMLParser(filename, string)
    parsed = parser.parse()
    generator = TonnikalaIRGenerator(document=parsed, translatable=translatable,
                                     filename=filename, source=string)
    tree = generator.generate_tree()
    tree = generator.flatten_element_nodes(tree)
    tree = generator.merge_text_nodes(tree)
    return tree


def parse_js(filename, string, translatable=False):
    parser = TonnikalaHTMLParser(filename, string)
    parsed = parser.parse()
    generator = TonnikalaIRGenerator(document=parsed, translatable=translatable,
                                     control_prefix='js', filename=filename,
                                     source=string)
    tree = generator.generate_tree()
    tree = generator.flatten_element_nodes(tree)
    tree = generator.merge_text_nodes(tree)
    return tree
