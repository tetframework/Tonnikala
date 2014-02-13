# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__docformat__ = "epytext"

"""XML parser"""

import six
from six.moves import html_entities, html_parser
from six import text_type

entitydefs = html_entities.entitydefs

from xml import sax
from xml.dom import minidom as dom

impl = dom.getDOMImplementation(' ')


class TonnikalaXMLParser(sax.ContentHandler):
    def __init__(self, filename, source):
        self.filename = filename
        self.source = source
        self.doc = None
        self.elements = []
        self._characters = None

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
        if self._characters:
            node = self.doc.createTextNode(''.join(self._characters[1]))
            node.lineno = self._characters[0]
            self.elements[-1].appendChild(node)

        self._characters = None

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
        if not self._characters:
            self._characters = (self._parser.getLineNumber(), [])

        self._characters[1].append(content)

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
            text = ''.join(self.characters)

            if isinstance(self.elements[-1], dom.Document):
                # Special case: just skip adding whitespace to document root,
                # but raise hell, if trying to add other characters
                if len(text.strip()) > 0:
                    raise RuntimeError("Text data outside of elements: %s"
                                       % text)

                else:
                    self.characters = None
                    return

            node = self.doc.createTextNode(text)
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

        # The HTMLParser spits processing instructions as is with type and all
        # (python 2 split does not take keyword arguments :( )
        type_, data = data.split(None, 1)

        if data.endswith('?'):
            # XML syntax parsed as SGML, remove trailing '?'
            data = data[:-1]

        node = self.doc.createProcessingInstruction(type_, data)
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
        dt = dom.parseString("<!%s><html/>" % decl).doctype
        self.elements[-1].appendChild(dt)

    def unknown_decl(self, decl):
        raise RuntimeError("Unknown declaration: %s" % decl)
