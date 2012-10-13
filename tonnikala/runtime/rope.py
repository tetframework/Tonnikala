# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals
from six import text_type, PY3

class Rope(object):
    def __init__(self, initial=None):
        self._buffer = []
        if initial:
            self._buffer.append(initial)

    def __call__(self, obj):
        self._buffer.append(obj)

    def join(self):
        return ''.join(text_type(i) for i in self._buffer)

    if PY3:
        __str__ = join

    else:
        __unicode__ = join
        def __str__(self):
            return self.join().encode('UTF-8')
