# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals
from six import text_type, PY3

class Rope(object):
    def __init__(self, initial_contents=None):
        self._buffer = initial_contents or []

    def __call__(self, *objs):
        for obj in objs:
            if isinstance(obj, Rope):
                self._buffer.extend(obj._buffer)
            else:
                self._buffer.append(text_type(obj))

        return self

    def join(self):
        return ''.join(self._buffer)

    if PY3:
        __str__ = join

    else:
        __unicode__ = join
        def __str__(self):
            return self.join().encode('UTF-8')
