# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__docformat__ = "epytext"


class IRTree(object):
    def __init__(self):
        self.root = None
        self.functions = {}


    def add_child(self, root):
        self.root = root


    def get_root(self):
        return self.root


    def add_function(self, name, argspec, function):
        self.functions[name] = (argspec, function)


    def __str__(self):
        return repr(self)


    def __repr__(self):
        return 'IRTree(%r)' % self.root
