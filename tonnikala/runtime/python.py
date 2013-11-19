from __future__ import absolute_import, division, print_function, unicode_literals

NoneType = type(None)

from ..helpers import escape as strescape
from six import text_type, PY3
from collections import deque

from markupsafe import escape


class Buffer(object):
    def __init__(self):
        self._buffer = buffer = []
        e = buffer.extend
        a = buffer.append

        def do_output(obj, Buffer=Buffer):
            if obj.__class__ is Buffer:
                e(obj._buffer)
            else:
                a(text_type(obj))

        self.output = do_output
        def output_boolean_attr(name, value):
            t = type(value)
            if t in (bool, NoneType):
                if bool(value):
                    do_output(' ' + name + '="' + name + '"')

                # skip on false, None
                return

            do_output(' ' + name + '="')
            do_output(escape(value))
            do_output('"')

        self.output_boolean_attr = output_boolean_attr


    def __html__(self):
        return self


    def join(self):
        return ''.join(self._buffer)


    if PY3:
        __str__ = join

    else:
        __unicode__ = join
        def __str__(self):
            return self.join().encode('UTF-8')


def output_attrs(values):
    if not values:
        return ''

    values = dict(values)
    rv = Buffer()
    for k, v in values.items():
        if isinstance(v, (bool, NoneType)):
            if v:
                v = k
            else:
                continue

        rv(' ')
        rv(k)
        rv('="')
        rv(escape(v))
        rv('"')

    return rv


def import_defs(href):
    return {}

