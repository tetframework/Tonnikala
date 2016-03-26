import sys

PY2 = sys.version_info < (3,)
PY3 = not PY2

if PY2:  # pragma: python2
    # noinspection PyUnresolvedReferences
    text_type = unicode
    # noinspection PyUnresolvedReferences
    string_types = basestring
    # noinspection PyUnresolvedReferences
    unichr = unichr

    def next_method(obj):
        return obj.next


    # noinspection PyCompatibility
    exec(
"""
def reraise(tp, value, tb=None):
    raise tp, value, tb
""")

    # noinspection PyUnresolvedReferences,PyCompatibility
    from StringIO import StringIO
    BytesIO = StringIO
    # noinspection PyUnresolvedReferences,PyCompatibility
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
    # noinspection PyUnresolvedReferences,PyCompatibility
    from html.entities import entitydefs as html_entity_defs
    # noinspection PyUnresolvedReferences,PyCompatibility
    from html import parser as html_parser
