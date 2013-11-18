from __future__ import absolute_import, division, print_function, unicode_literals

NoneType = type(None)

from .rope import Rope
from ..helpers import escape as strescape
from six import text_type

def escape(obj):
    if isinstance(obj, Buffer):
        return obj

    return strescape(text_type(obj))


class Buffer(Rope):
    def __init__(self, initial_contents=None):
        super(Buffer, self).__init__(initial_contents or [])
        self.rope_call = super(Buffer, self).__call__


    def escape(self, obj):
        self.rope_call(escape(obj))
        return self


    def output_boolean_attr(self, name, value):
        if isinstance(value, (bool, NoneType)):
            if bool(value):
                self.rope_call(' ', name, '="', name, '"')

            # skip on false, None
            return

        self.rope_call(' ', name, '="', escape(value), '"')
        return self


def make_buffer(*args):
    return Buffer(list(args))


def make_buffer_from_list(thelist):
    return Buffer(thelist)


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
