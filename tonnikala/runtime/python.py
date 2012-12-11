NoneType = type(None)

from .rope import Rope
from ..helpers import escape as strescape
from six import text_type

def escape(obj):
    if isinstance(obj, Buffer):
        return obj

    return strescape(text_type(obj))

class Buffer(Rope):
    def __init__(self):
        super(Buffer, self).__init__()

    def escape(self, obj):
        Rope.__call__(self, escape(obj))

class AttrBuffer(Rope):
    def __init__(self):
        super(AttrBuffer, self).__init__()
        self.boolean_value = None
        self.count = 0

    def escape(self, obj):
        self.count += 1
        self.boolean_value = None
        if self.count == 1 and isinstance(obj, (bool, NoneType)):
            self.boolean_value = bool(obj)

        Rope.__call__(self, escape(obj))

    def __call__(self, obj):
        Rope.__call__(self, obj)
        self.count += 1
        self.boolean_value = None

def make_buffer(*args):
    rv = Buffer()
    for i in args:
        rv(i)
    return rv

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

def output_attr(name, value_func):
    contents = value_func()
    if contents.boolean_value != None:
        if not contents.boolean_value:
            return ''
        else:
            contents = name

    return make_buffer(' ', name, '="', contents, '"')

def import_defs(href):
    return {}
