# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__docformat__ = "epytext"

"""XML parser"""

import six
from six.moves import html_entities
from six import text_type

entitydefs = html_entities.entitydefs

from xml import sax
from xml.dom import minidom as dom

from tonnikala.ir.nodes import Element, Text, If, For, Define, Import, EscapedText, MutableAttribute, ContainerNode, EscapedText, Root, DynamicAttributes, Unless, Expression, Comment

from tonnikala.expr     import handle_text_node # TODO: move this elsewhere.
from xml.dom.minidom    import Node
from tonnikala.ir.tree  import IRTree
from tonnikala.ir.generate import BaseDOMIRGenerator


impl = dom.getDOMImplementation(' ')

from six.moves import html_parser

class TonnikalaXMLParser(sax.ContentHandler):
    def __init__(self, filename, source):
        self.filename = filename
        self.source = source
        self.doc = None
        self.elements = []
        self.characters = None

    def parse(self):
        self._parser = parser = sax.make_parser()
        parser.setFeature(sax.handler.feature_external_pes, False)
        parser.setFeature(sax.handler.feature_external_ges, False)
        parser.setFeature(sax.handler.feature_namespaces, False)
        parser.setProperty(sax.handler.property_lexical_handler, self)
        parser.setContentHandler(self)
        source = sax.xmlreader.InputSource()

        if isinstance(self.source, six.binary_type):
            stream = six.BytesIO(self.source)
        else:
            stream = six.StringIO(self.source)

        source.setByteStream(stream)
        source.setSystemId(self.filename)
        parser.parse(source)
        return self.doc

    ## ContentHandler implementation
    def startDocument(self):
        self.doc = dom.Document()
        self.elements.append(self.doc)

    def _checkAndClearChrs(self):
        if self.characters:
            node = self.doc.createTextNode(''.join(self.characters[1]))
            node.lineno = self.characters[0]
            self.elements[-1].appendChild(node)

        self.characters = None

    def startElement(self, name, attrs):
        self.flush_character_data()
        el = self.doc.createElement(name)
        el.lineno = self._parser.getLineNumber()
        for k, v in attrs.items():
            el.setAttribute(k, v)

        self.elements[-1].appendChild(el)
        self.elements.append(el)

    def endElement(self, name):
        self.flush_character_data()
        popped = self.elements.pop()
        assert name == popped.tagName

    def characters(self, content):
        if not self.characters:
            self.characters = (self._parser.getLineNumber(), [])

        self.characters[1].append(content)

    def processingInstruction(self, target, data):
        self.flush_character_data()
        node = self.doc.createProcessingInstruction(target, data)
        node.lineno = self._parser.getLineNumber()
        self.elements[-1].appendChild(node)

    def skippedEntity(self, name):
        # Encoding?
        content = text_type(entitydefs.get(name))
        if not content:
            raise RuntimeError("Unknown HTML entity &%s;" % name)

        return self.characters(content)

    def startElementNS(self, name, qname, attrs): # pragma no cover
        raise NotImplementedError('startElementNS')

    def endElementNS(self, name, qname):# pragma no cover
        raise NotImplementedError('startElementNS')

    def startPrefixMapping(self, prefix, uri):# pragma no cover
        raise NotImplementedError('startPrefixMapping')

    def endPrefixMapping(self, prefix):# pragma no cover
        raise NotImplementedError('endPrefixMapping')

    # LexicalHandler implementation
    def comment(self, text):
        self.flush_character_data()

        if not text.strip().startswith('!'):
            node = self.doc.createComment(text)
            node.lineno = self._parser.getLineNumber()
            self.elements[-1].appendChild(node)

    def startCDATA(self):
        pass

    def endCDATA(self):
        pass

    def startDTD(self, name, pubid, sysid):
        self.doc.doctype = impl.createDocumentType(name, pubid, sysid)

    def endDTD(self):
        pass


# object to force a new-style class!
class TonnikalaHTMLParser(html_parser.HTMLParser, object):
    def __init__(self, filename, source):
        super(TonnikalaHTMLParser, self).__init__()
        self.filename = filename
        self.source = source
        self.doc = None
        self.elements = []
        self.characters = None
        self.characters_start = None


    def parse(self):
        self.doc = dom.Document()
        self.elements.append(self.doc)

        self.feed(self.source)
        self.close()
        return self.doc


    def flush_character_data(self):
        if self.characters:
            node = self.doc.createTextNode(''.join(self.characters))
            node.lineno = self.getpos()
            self.elements[-1].appendChild(node)

        self.characters = None


    def handle_starttag(self, name, attrs):
        self.flush_character_data()

        el = self.doc.createElement(name)
        el.name = name
        el.position = self.getpos()

        for k, v in attrs:
            el.setAttribute(k, v)

        self.elements[-1].appendChild(el)
        self.elements.append(el)


    def handle_endtag(self, name):
        self.flush_character_data()
        popped = self.elements.pop()

        if name != popped.name:
            raise RuntimeError("Invalid end tag </%s> (expected </%s>)" % (name, popped.name))


    def handle_data(self, content):
        if not self.characters:
            self.characters = []
            self.characters_start = self.getpos()

        self.characters.append(content)


    def handle_pi(self, data):
        self.flush_character_data()

        node = self.doc.createProcessingInstruction(data)
        node.position = self.getpos()
        self.elements[-1].appendChild(node)


    def handle_entityref(self, name):
        # Encoding?
        content = text_type(entitydefs.get(name))
        if not content:
            raise RuntimeError("Unknown HTML entity &%s;" % name)

        self.handle_data(content)


    def handle_charref(self, code):
        # Encoding?
        try:
            if code.startswith('x'):
                cp = int(code[1:], 16)
            else:
                cp = int(code, 10)

            content = six.unichr(cp)
            return self.handle_data(content)
        except Exception as e:
            raise RuntimeError("Invalid HTML charref &#%s;: %s" % (code, e))


    # LexicalHandler implementation
    def handle_comment(self, text):
        self.flush_character_data()

        if not text.strip().startswith('!'):
            node = self.doc.createComment(text)
            node.position = self.getpos()
            self.elements[-1].appendChild(node)


    def handle_decl(self, decl):
        self.doc.doctype = decl


class TonnikalaIRGenerator(BaseDOMIRGenerator):
    def __init__(self, *a, **kw):
        super(TonnikalaIRGenerator, self).__init__(*a, **kw)


    def get_guard_expression(self, dom_node):
        return self.grab_and_remove_control_attr(dom_node, 'strip')


    def generate_attributes_for_node(self, dom_node, ir_node):
        attrs_node = self.grab_and_remove_control_attr(dom_node, 'attrs')
        attrs = [ (k, handle_text_node(v)) for (k, v) in dom_node.attributes.items() ]
        self.generate_attributes(ir_node, attrs=attrs, dynamic_attrs=attrs_node)


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
            ir_node = handle_text_node(dom_node.nodeValue, is_cdata=self.is_cdata)
            return ir_node

        if node_t == Node.COMMENT_NODE:
            ir_node = EscapedText(u'<!--' + dom_node.nodeValue + u'-->')
            return ir_node

        raise ValueError("Unhandled node type %d" % node_t)


def parse(filename, string):
    parser = TonnikalaHTMLParser(filename, string)
    parsed = parser.parse()
    generator = TonnikalaIRGenerator(parsed)
    tree = generator.generate_tree()

    tree = generator.flatten_element_nodes(tree)
    tree = generator.merge_text_nodes(tree)
    return tree
