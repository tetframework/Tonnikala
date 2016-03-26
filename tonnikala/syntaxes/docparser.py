# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, \
    unicode_literals


"""XML parser"""

import sys
from xml import sax
from xml.dom import minidom as dom

from ..compat import (html_entity_defs, html_parser,
                      text_type, unichr, BytesIO, StringIO)
from ..helpers import StringWithLocation
from ..runtime.exceptions import TemplateSyntaxError

impl = dom.getDOMImplementation(' ')

html_parser_extra_kw = {}
if sys.version_info >= (3, 4):
    html_parser_extra_kw['convert_charrefs'] = False


class TonnikalaXMLParser(sax.ContentHandler):
    def __init__(self, filename, source):
        super(TonnikalaXMLParser, self).__init__()
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

        if isinstance(self.source, bytes):
            stream = BytesIO(self.source)
        else:
            stream = StringIO(self.source)

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
        content = html_entity_defs.get(name)
        if not content:
            raise RuntimeError("Unknown HTML entity &%s;" % name)

        return self.characters(text_type(content))

    def startElementNS(self, name, qname, attrs):  # pragma no cover
        raise NotImplementedError('startElementNS')

    def endElementNS(self, name, qname):  # pragma no cover
        raise NotImplementedError('startElementNS')

    def startPrefixMapping(self, prefix, uri):  # pragma no cover
        raise NotImplementedError('startPrefixMapping')

    def endPrefixMapping(self, prefix):  # pragma no cover
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


if hasattr(html_parser, 'attrfind_tolerant'):  # pragma: no cover
    attrfind = html_parser.attrfind_tolerant
else:
    attrfind = html_parser.attrfind

if hasattr(html_parser, 'tagfind_tolerant'):  # pragma: no cover
    tagfind = html_parser.tagfind_tolerant
else:
    tagfind = html_parser.tagfind


# object to force a new-style class!
class TonnikalaHTMLParser(html_parser.HTMLParser, object):
    void_elements = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
                     'keygen', 'link', 'meta', 'param', 'source', 'track',
                     'wbr'}

    def __init__(self, filename, source):
        super(TonnikalaHTMLParser, self).__init__(**html_parser_extra_kw)
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
        self.flush_character_data()
        return self.doc

    def flush_character_data(self):
        if self.characters:
            text = ''.join(self.characters)

            if isinstance(self.elements[-1], dom.Document):
                # Special case: just skip adding whitespace to document root,
                # but raise hell, if trying to add other characters
                if len(text.strip()) > 0:
                    self.syntax_error(
                        "Text data outside of root element",
                        lineno=self.characters_start[0])

                else:
                    self.characters = None
                    return

            line, offset = self.characters_start
            text = StringWithLocation(text, line, offset)
            node = self.doc.createTextNode(text)
            node.position = line, offset
            self.elements[-1].appendChild(node)

        self.characters = None

    def delta(self, row, col):
        orow, ocol = self.getpos()
        if row:
            orow += row
            ocol = col
        else:
            ocol += col

        return orow, ocol

    def find_attr_positions(self, attrs):
        if not attrs:
            return {}

        source = self.get_starttag_text()
        match = tagfind.match(source, 1)
        start = match.end()
        attr_pos = {}

        lineoffset = source[:start].count('\n')
        colpos = start - source[:start].rfind('\n') if lineoffset else start + 1

        for m in attrfind.finditer(source, start, len(source) - 1):
            if not m.group(2):
                continue

            attrstart = m.start(3)
            if source[attrstart] in ("'", '"'):
                attrstart += 1

            advance = source[start:attrstart]
            linedelta = advance.count('\n')
            if linedelta:
                colpos = len(advance) - advance.rfind('\n')
            else:
                colpos += len(advance)

            lineoffset += linedelta

            attrname = m.group(1).lower()
            attr_pos[attrname] = self.delta(lineoffset, colpos)
            start = attrstart

        return attr_pos

    def getlineno(self):
        return self.getpos()[0]

    def handle_starttag(self, name, attrs, self_closing=False):
        self.flush_character_data()

        attr_pos = self.find_attr_positions(attrs)
        el = self.doc.createElement(name)
        el.name = name
        el.position = self.getpos()

        for k, v in attrs:
            if k in attr_pos:
                l, o = attr_pos[k]
                v = StringWithLocation(v, l, o)

            el.setAttribute(k, v)

        self.elements[-1].appendChild(el)
        self.elements.append(el)

        if self_closing or name.lower() in self.void_elements:
            self.handle_endtag(name)

    def handle_endtag(self, name):
        self.flush_character_data()
        popped = self.elements.pop()

        if name.lower() != popped.name.lower():
            self.syntax_error(
                "Invalid end tag </%s> (expected </%s>)" % (name, popped.name))

    def handle_startendtag(self, name, attrs):
        self.handle_starttag(name, attrs, self_closing=True)

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

    def syntax_error(self, message, lineno=None):
        raise TemplateSyntaxError(
            message,
            lineno or self.getlineno(),
            source=self.source,
            filename=self.filename)

    def handle_entityref(self, name):
        # Encoding?
        try:
            content = text_type(html_entity_defs[name])
        except KeyError:
            self.syntax_error("Unknown HTML entity &%s;" % name)

        self.handle_data(content)

    def handle_charref(self, code):
        # Encoding?
        try:
            if code.startswith('x'):
                cp = int(code[1:], 16)
            else:
                cp = int(code, 10)

            content = unichr(cp)
            return self.handle_data(content)
        except Exception as e:
            self.syntax_error("Invalid HTML charref &#%s;: %s" % (code, e))

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
        self.syntax_error("Unknown declaration: %s" % decl)
