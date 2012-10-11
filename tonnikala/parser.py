# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__docformat__ = "epytext"

"""XML parser"""

from six import StringIO
from six.moves import html_entities

entitydefs = html_entities.entitydefs

from xml import sax
from xml.dom import minidom as dom

impl = dom.getDOMImplementation(' ')

class Parser(sax.ContentHandler):
    def __init__(self, filename, source):
        self._filename = filename
        self._source = source
        self._doc = None
        self._els = []
        self._chrs = None

    def parse(self):
        self._parser = parser = sax.make_parser()
        parser.setFeature(sax.handler.feature_external_pes, False)
        parser.setFeature(sax.handler.feature_external_ges, False)
        parser.setFeature(sax.handler.feature_namespaces, False)
        parser.setProperty(sax.handler.property_lexical_handler, self)
        parser.setContentHandler(self)
        source = sax.xmlreader.InputSource()
        source.setByteStream(StringIO(self._source))
        source.setSystemId(self._filename)
        parser.parse(source)
        return self._doc

    ## ContentHandler implementation
    def startDocument(self):
        self._doc = dom.Document()
        self._els.append(self._doc)

    def _checkAndClearChrs(self):
        if self._chrs:
            node = self._doc.createTextNode(''.join(self._chrs[1]))
            node.lineno = self._chrs[0]
            self._els[-1].appendChild(node)

        self._chrs = None

    def startElement(self, name, attrs):
        self._checkAndClearChrs()
        el = self._doc.createElement(name)
        el.lineno = self._parser.getLineNumber()
        for k,v in attrs.items():
            el.setAttribute(k,v)
        self._els[-1].appendChild(el)
        self._els.append(el)

    def endElement(self, name):
        self._checkAndClearChrs()
        popped = self._els.pop()
        assert name == popped.tagName

    def characters(self, content):
        if not self._chrs:
            self._chrs = (self._parser.getLineNumber(), [])

        self._chrs[1].append(content)

    def processingInstruction(self, target, data):
        self._checkAndClearChrs()
        node = self._doc.createProcessingInstruction(target, data)
        node.lineno = self._parser.getLineNumber()
        self._els[-1].appendChild(node)

    def skippedEntity(self, name):
        # Encoding?
        content = unicode(entitydefs.get(name))
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
        self._checkAndClearChrs()
        node = self._doc.createComment(text)
        node.lineno = self._parser.getLineNumber()
        self._els[-1].appendChild(node)

    def startCDATA(self): pass
    def endCDATA(self):
        pass

    def startDTD(self, name, pubid, sysid):
        self._doc.doctype = impl.createDocumentType(name, pubid, sysid)

    def endDTD(self):
        pass
