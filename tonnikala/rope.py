# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

class Rope(object):
    def __init__(self, initial=None):
        self._buffer = []
        if initial:
            if isinstance(initial, Rope):
                self.buffer.append(initial)

    def __call__(self, obj):
        self._buffer.append(obj)

