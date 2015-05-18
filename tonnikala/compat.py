import sys

if sys.version_info < (3,):
    PY2 = True
    PY3 = False

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

else:
    PY3 = True
    PY2 = False

    text_type = str
    string_types = (str,)
    unichr = chr

    def next_method(obj):
        return obj.__next__

    def reraise(tp, value, tb=None):
        if value is None:
            value = tp()
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value

    from io import StringIO, BytesIO
    from html.entities import entitydefs as html_entity_defs
    from html import parser as html_parser
