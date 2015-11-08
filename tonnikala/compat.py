import sys

PY2 = sys.version_info < (3,)
PY3 = not PY2


if PY2:  # pragma: python2
    text_type = unicode
    string_types = basestring
    unichr = unichr

    def next_method(obj):
        return obj.next

    exec("""
def reraise(tp, value, tb=None):
    raise tp, value, tb
""")

    from StringIO import StringIO
    BytesIO = StringIO
    from htmlentitydefs import entitydefs as html_entity_defs
    import HTMLParser as html_parser

else:  # pragma: python3
    text_type = str
    string_types = (str,)
    unichr = chr

    def next_method(obj):
        return obj.__next__

    def reraise(tp, value, tb=None):  # pragma: no cover
        if value is None:
            value = tp()
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value

    from io import StringIO, BytesIO
    from html.entities import entitydefs as html_entity_defs
    from html import parser as html_parser

try:  # pragma: no cover
    from collections import OrderedDict
except ImportError:  #  pragma: no cover
    from ordereddict import OrderedDict
