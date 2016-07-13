import io

from lingua.extractors import Extractor
from lingua.extractors import Message
from lingua.extractors.python import _extract_python
from tonnikala.ir.nodes import TranslatableText, Expression
from tonnikala.loader import parsers


class TonnikalaExtractor(Extractor):
    "Extract strings from tonnikala templates, defaulting to Python expressions"

    extensions = ['.tk']
    syntax = 'tonnikala'

    def parse_python(self, node, filename, lineno, options):
        start_line = (node.position[0] or 1) + lineno
        for message in _extract_python(
            filename,
            node.expression,
            options,
            start_line
        ):
            yield Message(*message[:6],
                          location=(
                              filename,
                              lineno +
                              message.location[1]))

    def __call__(self, filename, options, fileobj=None, lineno=0):
        self.filename = filename
        if fileobj is None:
            fileobj = io.open(filename, encoding='utf-8')

        parser_func = parsers.get(self.syntax)
        source = fileobj.read()
        if isinstance(source, bytes):
            source = source.decode('UTF-8')

        tree = parser_func(filename, source, translatable=True)

        for node in tree:
            if isinstance(node, TranslatableText):
                yield Message(None, node.text, None, [], u'', u'',
                              (filename, lineno + (node.position[0] or 1)))
            elif isinstance(node, Expression):
                for m in self.parse_python(node, filename, lineno, options):
                    yield m


class Options:
    keywords = {}
    comment_tag = None
    domain = None


def extract_tonnikala(fileobj, keywords, comment_tags, options):
    """Extract messages from Tonnikala files.

    :param fileobj: the file-like object the messages should be extracted
                    from
    :param keywords: a list of keywords (i.e. function names) that should
                     be recognized as translation functions
    :param comment_tags: a list of translator tags to search for and
                         include in the results
    :param options: a dictionary of additional options (optional)
    :return: an iterator over ``(lineno, funcname, message, comments)``
             tuples
    :rtype: ``iterator``
    """
    extractor = TonnikalaExtractor()
    for msg in extractor(filename=None, fileobj=fileobj, options=Options()):
        msgid = msg.msgid,

        prefix = ''
        if msg.msgid_plural:
            msgid = (msg.msgid_plural,) + msgid
            prefix = 'n'

        if msg.msgctxt:
            msgid = (msg.msgctxt,) + msgid
            prefix += 'p'

        yield (msg.location[1], prefix + 'gettext', msgid, msg.comment)
