# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

python3 = False
try:
    unicode
    strtype = unicode
except:
    strtype = str
    python3 = True

class Rope(object):
    def __init__(self, initial=None):
        self._buffer = []
        if initial:
            self.buffer.append(initial)

    def __call__(self, obj):
        self._buffer.append(obj)

    def join(self):
        return u''.join(strtype(i) for i in self._buffer)

    if python3:
        __str__ = join

    else:
        __unicode__ = join
