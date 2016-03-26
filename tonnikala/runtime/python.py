from __future__ import absolute_import, division, print_function, \
    unicode_literals

from collections import Mapping
from markupsafe import escape

from ..compat import text_type, PY3

NoneType = type(None)


class _TKPythonBufferImpl(object):
    def __init__(self):
        self._buffer = buffer = []
        e = buffer.extend
        a = buffer.append

        def do_output(*objs):
            for obj in objs:
                if obj.__class__ is self.__class__:
                    e(obj._buffer)
                else:
                    a(text_type(obj))

        self.output = do_output

        def output_boolean_attr(name, value):
            t = type(value)
            if t in (bool, NoneType):
                value and do_output(' ' + name + '="' + name + '"')

                # skip on false, None
                return

            do_output(' ' + name + '="')
            do_output(escape(value))
            do_output('"')

        self.output_boolean_attr = output_boolean_attr

    def __call__(self, *a):
        self.output(*a)

    def __html__(self):
        return self

    def join(self):
        return ''.join(self._buffer)

    if PY3:  # pragma: no cover
        __str__ = join

    else:  # pragma: no cover
        __unicode__ = join

        def __str__(self):
            return self.join().encode('UTF-8')


try:  # pragma: no cover
    from ._buffer import Buffer, _set_escape_method

    _set_escape_method(escape)
except ImportError as e:  # pragma: no cover
    Buffer = _TKPythonBufferImpl
    _set_escape_method = None

del _set_escape_method


def output_attrs(values):
    if not values:
        return ''

    if not isinstance(values, Mapping):
        values = iter(values)
    else:
        values = values.items()

    rv = Buffer()
    for k, v in values:
        rv.output_boolean_attr(k, v)

    return rv


def bind(context, block=False):
    """
    Given the context, returns a decorator wrapper;
    the binder replaces the wrapped func with the
    value from the context OR puts this function in
    the context with the name.
    """

    if block:
        def decorate(func):
            name = func.__name__.replace('__TK__block__', '')
            if name not in context:
                context[name] = func
            return context[name]

        return decorate

    def decorate(func):
        name = func.__name__
        if name not in context:
            context[name] = func
        return context[name]

    return decorate


class ImportedTemplate(object):
    def __init__(self, name):
        self._name = name

    def __repr__(self):  # pragma: no cover
        return "<ImportedTemplate '%r'>" % self._name


class TonnikalaRuntime(object):
    bind = staticmethod(bind)
    Buffer = staticmethod(Buffer)
    output_attrs = staticmethod(output_attrs)
    escape = staticmethod(escape)

    def __init__(self):
        self.loader = None

    def load(self, href):
        return self.loader.load(href)

    def import_defs(self, context, href):
        modified_context = context.copy()
        self.loader.load(href).bind(modified_context)
        container = ImportedTemplate(href)

        for k, v in modified_context.items():
            # modified
            if k in context and context[k] is v:
                continue

            setattr(container, k, v)

        return container
