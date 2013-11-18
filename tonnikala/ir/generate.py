# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from tonnikala.ir.nodes import Element, Text, If, For, Define, Import, EscapedText, MutableAttribute, ContainerNode, EscapedText, Root, DynamicAttributes, Unless, Expression, Comment

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
    link
    meta
    param
    command
    keygen
    source
'''.split())

try:
    unicode
    def u(s):
        return unicode(s)
except:
    def u(s):
        return s

class all_set(object):
    def __contains__(self, value):
        return True

class IRGenerator(object):
    def __init__(self, document, mode='html5'):
        self.dom_document = document
        self.tree = IRTree()
        self.mode = mode

        if mode in [ 'html', 'html5', 'xhtml' ]:
            self.empty_elements = html5_empty_tags
            self.empty_tag_closing_string = ' />'

        elif mode == 'xml':
            self.empty_elements = all_set()
            self.empty_tag_closing_string = '/>'

        else:
            raise ValueError("Unknown render mode '%s'" % mode)


    def child_iter(self, node):
        if not node.firstChild:
            return

        current = node.firstChild
        while current:
            yield current
            current = current.nextSibling


    def get_guard_expression(self, dom_node):
        return self.grab_and_remove_control_attr(dom_node, 'strip')


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


    def create_control_nodes(self, dom_node):
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
            self.generate_attributes(dom_node, el_ir_node)

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
            ir_node = handle_text_node(dom_node.nodeValue)
            return ir_node

        if node_t == Node.COMMENT_NODE:
            ir_node = EscapedText(u('<!--') + dom_node.nodeValue + u('-->'))
            return ir_node

        raise ValueError("Unhandled node type %d" % node_t)


    def add_children(self, children, ir_node):
        for dom_node in children:
            node = self.generate_ir_node(dom_node)
            if node != None:
                ir_node.add_child(node)


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
                        start_tag_nodes.append(EscapedText(self.empty_tag_closing_string))

                    else:
                        start_tag_nodes.append(EscapedText('></%s>' % i.name))

                else:
                    start_tag_nodes.append(EscapedText('>'))
                    end_tag_nodes = [ EscapedText('</%s>' % i.name) ]

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
                    start_tag_nodes = [ start_tag ]

                    if end_tag_nodes:
                        end_tag = Unless(guard)
                        end_tag.children = end_tag_nodes
                        end_tag_nodes = [ end_tag ]

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
